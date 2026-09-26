import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { CurrencyExchangePopup } from "@pos_nm_currency_exchange/app/exchange_popup/exchange_popup";

patch(PosStore.prototype, {
    get nmShowExchangeButton() {
        return Boolean(this.config.nm_exchange_enabled);
    },
    async nmCurrencyExchange() {
        return makeAwaitable(this.dialog, CurrencyExchangePopup);
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
