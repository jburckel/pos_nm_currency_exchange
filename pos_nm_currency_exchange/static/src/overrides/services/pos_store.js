import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { getForeignCashCurrencies } from "@pos_nm_multicurrencies/overrides/utils/change_currency";
import { CurrencyExchangePopup } from "@pos_nm_currency_exchange/app/exchange_popup/exchange_popup";
import { ExchangeOperationsPopup } from "@pos_nm_currency_exchange/app/exchange_operations_popup/exchange_operations_popup";
import { ExchangeRatesPopup } from "@pos_nm_currency_exchange/app/exchange_rates_popup/exchange_rates_popup";
import { NoteStockPopup } from "@pos_nm_currency_exchange/app/note_stock_popup/note_stock_popup";
import { SendNotesPopup } from "@pos_nm_currency_exchange/app/send_notes_popup/send_notes_popup";
import { ReceiveNotesPopup } from "@pos_nm_currency_exchange/app/receive_notes_popup/receive_notes_popup";

patch(PosStore.prototype, {
    get nmShowExchangeButton() {
        return Boolean(this.config.nm_exchange_enabled);
    },
    /**
     * Why the counter cannot record an operation at this point of sale,
     * else an empty string.
     */
    get nmExchangeBlocker() {
        if (!getForeignCashCurrencies(this).currencies.length) {
            return _t(
                "Add a foreign currency to the cash payment method of the Point of Sale to exchange currencies."
            );
        }
        if (!this.config._nm_exchange_account_set) {
            return _t(
                "Set the exchange commission account of the Point of Sale (Settings > Currency Exchange) before exchanging currencies."
            );
        }
        return "";
    },
    async nmCurrencyExchange() {
        const blocker = this.nmExchangeBlocker;
        if (blocker) {
            this.dialog.add(AlertDialog, { title: _t("Currency Exchange"), body: blocker });
            return;
        }
        return makeAwaitable(this.dialog, CurrencyExchangePopup);
    },
    nmExchangeOperations() {
        this.dialog.add(ExchangeOperationsPopup);
    },
    nmExchangeRates() {
        this.dialog.add(ExchangeRatesPopup);
    },
    // The notes of a foreign currency are tracked by denomination.
    get nmShowNoteStock() {
        return Boolean(this.config._nm_note_currency_ids?.length);
    },
    nmNoteStock() {
        this.dialog.add(NoteStockPopup);
    },
    // The counter belongs to an exchange office with other counters: notes
    // are sent to and received from them.
    get nmShowTransfers() {
        return Boolean(this.config.nm_exchange_enabled && this.config._nm_transfer_enabled);
    },
    async nmSendNotes() {
        return makeAwaitable(this.dialog, SendNotesPopup);
    },
    nmReceiveNotes() {
        this.dialog.add(ReceiveNotesPopup);
    },
    /**
     * Print a receipt template of the exchange counter on the receipt
     * printer, with the data computed by the server (``extraData``).
     */
    async nmPrintReceipt(template, extraData) {
        const printer = this.ticketPrinter;
        const generator = printer.getGenerator({ models: this.models });
        const iframe = await printer.generateIframe(template, {
            company: generator.company.raw,
            config: generator.config.raw,
            image: { logo: generator.config.receiptLogoUrl },
            extra_data: { ...generator.commonExtraData, ...extraData },
        });
        return printer.printWithFallback({ iframe, webFallback: true });
    },
    // get_closing_control_data returns the exchange operations of the
    // session (nm_exchange_summary): set them aside for the closing popup,
    // whose props are validated.
    async getClosePosInfo() {
        const info = await super.getClosePosInfo(...arguments);
        if (info && "nm_exchange_summary" in info) {
            const { nm_exchange_summary, ...coreInfo } = info;
            this.nmExchangeSummary = nm_exchange_summary || null;
            return coreInfo;
        }
        this.nmExchangeSummary = null;
        return info;
    },
});
