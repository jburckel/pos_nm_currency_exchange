import { Dialog } from "@web/core/dialog/dialog";
import { Component, useProps, proxy, t, onWillUnmount } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatCurrency } from "@web/core/currency";
import { parseFloat } from "@web/views/fields/parsers";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { getForeignCashCurrencies } from "@pos_nm_multicurrencies/overrides/utils/change_currency";

/**
 * Currency exchange counter: the customer hands notes in one cash currency
 * of the point of sale and receives notes in another. The amounts come
 * from the server (get_quote): cash rates, commission and rounding of the
 * notes handed back are computed there, and the operation is recorded by
 * create_from_ui with its two statement lines.
 */
export class CurrencyExchangePopup extends Component {
    static template = "pos_nm_currency_exchange.CurrencyExchangePopup";
    static components = { Dialog };
    props = useProps({
        getPayload: t.function().optional(),
        close: t.function(),
    });

    setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.currencies = [this.pos.currency, ...getForeignCashCurrencies(this.pos).currencies];
        const foreign = this.currencies.find((currency) => currency.id !== this.pos.currency.id);
        this.state = proxy({
            currencyInId: foreign ? foreign.id : this.pos.currency.id,
            currencyOutId: this.pos.currency.id,
            amountIn: "",
            note: "",
            partner: null,
            quote: null,
            loading: false,
            error: "",
            saving: false,
        });
        this.quoteTimer = null;
        this.quoteSequence = 0;
        onWillUnmount(() => clearTimeout(this.quoteTimer));
    }

    get currencyIn() {
        return this.currencies.find((currency) => currency.id === this.state.currencyInId);
    }
    get currencyOut() {
        return this.currencies.find((currency) => currency.id === this.state.currencyOutId);
    }
    get amountIn() {
        return this.pos.isValidFloat(this.state.amountIn) ? parseFloat(this.state.amountIn) : 0;
    }
    get isValid() {
        return (
            this.amountIn > 0 &&
            this.state.currencyInId !== this.state.currencyOutId &&
            !!this.state.quote &&
            !this.state.loading &&
            !this.state.error &&
            (!this.state.quote.customer_required || !!this.state.partner)
        );
    }
    get customerLabel() {
        return this.state.partner ? this.state.partner.name : _t("Customer");
    }
    get customerRequired() {
        return !!this.state.quote?.customer_required && !this.state.partner;
    }

    format(amount, currency) {
        return formatCurrency(amount, currency.id);
    }

    onCurrencyInChange(ev) {
        this.state.currencyInId = parseInt(ev.target.value);
        if (this.state.currencyOutId === this.state.currencyInId) {
            const other = this.currencies.find((currency) => currency.id !== this.state.currencyInId);
            this.state.currencyOutId = other ? other.id : this.state.currencyOutId;
        }
        this.scheduleQuote();
    }
    onCurrencyOutChange(ev) {
        this.state.currencyOutId = parseInt(ev.target.value);
        this.scheduleQuote();
    }
    onAmountInput(ev) {
        this.state.amountIn = ev.target.value;
        this.scheduleQuote();
    }
    onAmountBlur() {
        if (this.pos.isValidFloat(this.state.amountIn)) {
            this.state.amountIn = formatCurrency(this.amountIn, this.currencyIn.id, { noSymbol: true });
        }
    }
    swap() {
        const inId = this.state.currencyInId;
        this.state.currencyInId = this.state.currencyOutId;
        this.state.currencyOutId = inId;
        this.scheduleQuote();
    }

    scheduleQuote() {
        clearTimeout(this.quoteTimer);
        this.state.quote = null;
        this.state.error = "";
        if (!(this.amountIn > 0) || this.state.currencyInId === this.state.currencyOutId) {
            return;
        }
        this.state.loading = true;
        this.quoteTimer = setTimeout(() => this.fetchQuote(), 300);
    }
    async fetchQuote() {
        const sequence = ++this.quoteSequence;
        try {
            const quote = await this.pos.data.call("pos.nm.exchange", "get_quote", [
                this.pos.config.id,
                this.state.currencyInId,
                this.amountIn,
                this.state.currencyOutId,
            ]);
            if (sequence === this.quoteSequence) {
                this.state.quote = quote;
            }
        } catch (error) {
            if (sequence === this.quoteSequence) {
                this.state.error = error?.data?.message || error?.message || _t("The quote could not be computed.");
            }
        } finally {
            if (sequence === this.quoteSequence) {
                this.state.loading = false;
            }
        }
    }

    async selectCustomer() {
        const partner = await makeAwaitable(this.pos.dialog, PartnerList, {
            partner: this.state.partner || undefined,
        });
        if (partner) {
            this.state.partner = partner;
        }
    }
    clearCustomer() {
        this.state.partner = null;
    }

    async confirm() {
        if (!this.isValid || this.state.saving) {
            return;
        }
        this.state.saving = true;
        try {
            const receipt = await this.pos.data.call("pos.nm.exchange", "create_from_ui", [
                this.pos.session.id,
                this.state.currencyInId,
                this.amountIn,
                this.state.currencyOutId,
                this.state.partner ? this.state.partner.id : false,
                this.pos.accessRight?.cashier?.name || "",
                this.state.note.trim() || false,
            ]);
            await this.pos.logEmployeeMessage(
                _t("Currency exchange %(name)s: %(received)s for %(handed)s", {
                    name: receipt.name,
                    received: receipt.amount_in,
                    handed: receipt.amount_out,
                }),
                "CASH_DRAWER_ACTION"
            );
            await this.printReceipt(receipt);
            this.notification.add(
                _t("%(name)s: %(received)s received, %(handed)s handed back.", {
                    name: receipt.name,
                    received: receipt.amount_in,
                    handed: receipt.amount_out,
                }),
                { type: "success" }
            );
            this.props.getPayload?.(receipt);
            this.props.close();
        } catch (error) {
            this.state.error = error?.data?.message || error?.message || _t("The operation could not be recorded.");
        } finally {
            this.state.saving = false;
        }
    }

    async printReceipt(receipt) {
        const printer = this.pos.ticketPrinter;
        const generator = printer.getGenerator({ models: this.pos.models });
        const data = {
            company: generator.company.raw,
            config: generator.config.raw,
            image: { logo: generator.config.receiptLogoUrl },
            extra_data: { ...generator.commonExtraData, ...receipt },
        };
        try {
            await this.pos.openCashbox(_t("Currency exchange"));
            const iframe = await printer.generateIframe("pos_nm_currency_exchange.pos_exchange_receipt", data);
            await printer.printWithFallback({ iframe, webFallback: true });
        } catch (error) {
            console.warn("Exchange receipt not printed", error);
        }
    }
}
