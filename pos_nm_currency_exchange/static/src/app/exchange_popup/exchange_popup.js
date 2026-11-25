import { Dialog } from "@web/core/dialog/dialog";
import { Component, useProps, proxy, t, onWillUnmount } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError } from "@web/core/network/rpc";
import { formatCurrency } from "@web/core/currency";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { uuidv4 } from "@point_of_sale/utils";
import {
    formatAmountInput,
    getCoinStepWarning,
    getForeignCashCurrencies,
    getPaymentStep,
    parseAmountInput,
} from "@pos_nm_multicurrencies/overrides/utils/change_currency";

/**
 * Currency exchange counter: the customer hands notes in one cash currency
 * of the point of sale and receives notes in another. The amounts come
 * from the server (get_quote): cash rates, commission and rounding of the
 * notes handed back are computed there, and the operation is recorded by
 * create_from_ui with its two statement lines.
 *
 * Reverse quote: the cashier may type the amount the customer wants in the
 * "handed back" field instead; the server then computes the amount to
 * receive (get_reverse_quote) and the operation is quoted and recorded from
 * that amount received, as any other.
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
            // Amount typed in the "handed back" field: reverse quote.
            amountOut: "",
            reverse: false,
            note: "",
            partner: null,
            quote: null,
            loading: false,
            error: "",
            saving: false,
        });
        this.quoteTimer = null;
        this.quoteSequence = 0;
        // Sent with the operation: confirmed again after a lost response,
        // the operation is not recorded twice.
        this.uuid = uuidv4();
        onWillUnmount(() => clearTimeout(this.quoteTimer));
    }

    get currencyIn() {
        return this.currencies.find((currency) => currency.id === this.state.currencyInId);
    }
    get currencyOut() {
        return this.currencies.find((currency) => currency.id === this.state.currencyOutId);
    }
    get amountIn() {
        return this.pos.isValidFloat(this.state.amountIn) ? parseAmountInput(this.state.amountIn) : 0;
    }
    get amountOut() {
        return this.pos.isValidFloat(this.state.amountOut) ? parseAmountInput(this.state.amountOut) : 0;
    }
    /**
     * Value of the "handed back" field: the amount typed for a reverse
     * quote, else the amount of the quote.
     */
    get amountOutValue() {
        if (this.state.reverse) {
            return this.state.amountOut;
        }
        return this.state.quote ? formatAmountInput(this.state.quote.amount_out, this.state.currencyOutId) : "";
    }
    /**
     * The amount received cannot be made up with the coins and notes of its
     * currency (not a multiple of its Payment Rounding, else of its Change
     * Rounding): a warning, the operation stays possible.
     */
    get coinStepWarning() {
        const currency = this.currencyIn;
        if (!currency || currency.id === this.pos.config.currency_id.id) {
            return "";
        }
        return getCoinStepWarning(this.amountIn, currency, getPaymentStep(currency));
    }
    /**
     * The quote shown is the one of the currencies and the amount received
     * in the popup: a quote still pending or of other inputs is not.
     */
    get isQuoteCurrent() {
        return (
            !!this.state.quote &&
            !this.state.loading &&
            this.state.quote.key === this.quoteKey(this.state.currencyInId, this.state.currencyOutId, this.amountIn)
        );
    }
    get isValid() {
        return (
            this.amountIn > 0 &&
            this.isQuoteCurrent &&
            !this.errorMessage &&
            (!this.state.quote.customer_required || !!this.state.partner)
        );
    }
    /**
     * The error of the last request, or the refusal of the drawer of the
     * currency handed back, shown before Confirm.
     */
    get errorMessage() {
        return this.state.error || this.state.quote?.drawer_error || "";
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
    quoteKey(currencyInId, currencyOutId, amountIn) {
        return `${currencyInId}|${currencyOutId}|${amountIn}`;
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
        if (this.state.currencyInId === this.state.currencyOutId) {
            const other = this.currencies.find((currency) => currency.id !== this.state.currencyOutId);
            this.state.currencyInId = other ? other.id : this.state.currencyInId;
        }
        this.scheduleQuote();
    }
    onAmountInput(ev) {
        this.state.amountIn = ev.target.value;
        this.state.reverse = false;
        this.scheduleQuote();
    }
    onAmountOutInput(ev) {
        this.state.amountOut = ev.target.value;
        this.state.reverse = true;
        this.scheduleQuote();
    }
    /**
     * Reverse quote: once the field is left, it shows the amount actually
     * handed back, at least the one typed (rounded up to the coins and
     * notes).
     */
    onAmountOutBlur() {
        if (this.state.reverse && this.isQuoteCurrent) {
            this.state.amountOut = formatAmountInput(this.state.quote.amount_out, this.state.currencyOutId);
        }
    }
    onAmountBlur() {
        if (this.pos.isValidFloat(this.state.amountIn)) {
            this.state.amountIn = formatAmountInput(this.amountIn, this.currencyIn.id);
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
        // A response to an earlier request is dropped.
        this.quoteSequence++;
        this.state.quote = null;
        this.state.error = "";
        this.state.loading = false;
        if (this.state.reverse) {
            this.state.amountIn = "";
        }
        const amount = this.state.reverse ? this.amountOut : this.amountIn;
        if (!(amount > 0) || this.state.currencyInId === this.state.currencyOutId) {
            return;
        }
        this.state.loading = true;
        this.quoteTimer = setTimeout(() => this.fetchQuote(), 300);
    }
    async fetchQuote() {
        const sequence = this.quoteSequence;
        const { currencyInId, currencyOutId, reverse } = this.state;
        let amountIn = this.amountIn;
        try {
            const quote = reverse
                ? await this.pos.data.call("pos.nm.exchange", "get_reverse_quote", [
                      this.pos.config.id,
                      currencyInId,
                      currencyOutId,
                      this.amountOut,
                  ])
                : await this.pos.data.call("pos.nm.exchange", "get_quote", [
                      this.pos.config.id,
                      currencyInId,
                      amountIn,
                      currencyOutId,
                  ]);
            if (sequence === this.quoteSequence) {
                if (reverse) {
                    this.state.amountIn = formatAmountInput(quote.amount_in, currencyInId);
                    amountIn = this.amountIn;
                }
                // The inputs of the quote: Confirm only for these.
                this.state.quote = { ...quote, key: this.quoteKey(currencyInId, currencyOutId, amountIn) };
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
            // The popup cannot be closed (Discard, Escape) while recording.
            this.ui.block();
            let receipt;
            try {
                receipt = await this.pos.data.call(
                    "pos.nm.exchange",
                    "create_from_ui",
                    [
                        this.pos.session.id,
                        this.state.currencyInId,
                        this.amountIn,
                        this.state.currencyOutId,
                        this.state.partner ? this.state.partner.id : false,
                        this.state.note.trim() || false,
                        // The cashier is decided by the server: the user, and
                        // with pos_hr the employee logged in, checked there.
                        (this.pos.config.module_pos_hr && this.pos.accessRight.loggedCashier?.id) || false,
                        // Refused by the server when the quote changed since.
                        this.state.quote.amount_out,
                    ],
                    { uuid: this.uuid }
                );
            } finally {
                this.ui.unblock();
            }
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
            if (error instanceof ConnectionLostError) {
                this.state.error = _t(
                    "The connection was lost: the operation may have been recorded. Confirm again once the connection is back: an operation already recorded is not recorded twice."
                );
            } else {
                this.state.error =
                    error?.data?.message || error?.message || _t("The operation could not be recorded.");
            }
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
        // confirm() logged the operation as the drawer action.
        try {
            await this.pos.openCashbox();
        } catch {
            this.notification.add(_t("The cash drawer could not be opened."), { type: "warning" });
        }
        try {
            const iframe = await printer.generateIframe("pos_nm_currency_exchange.pos_exchange_receipt", data);
            await printer.printWithFallback({ iframe, webFallback: true });
        } catch {
            this.notification.add(
                _t("The receipt of %(name)s could not be printed.", { name: receipt.name }),
                { type: "warning" }
            );
        }
    }
}
