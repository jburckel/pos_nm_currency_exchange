import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { getForeignCashCurrencies } from "@pos_nm_multicurrencies/overrides/utils/change_currency";
import { CurrencyExchangePopup } from "@pos_nm_currency_exchange/app/exchange_popup/exchange_popup";

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
