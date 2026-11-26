import { Dialog } from "@web/core/dialog/dialog";
import { Component, useProps, proxy, t, onWillStart } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError } from "@web/core/network/rpc";

/**
 * Rate board of the counter (pos.config._nm_rate_board): for each foreign
 * cash currency, what the counter pays for the notes it buys and asks for
 * the notes it sells, computed by the quote of the counter, and the
 * commission rule. Printed on the receipt printer.
 */
export class ExchangeRatesPopup extends Component {
    static template = "pos_nm_currency_exchange.ExchangeRatesPopup";
    static components = { Dialog };
    props = useProps({
        close: t.function(),
    });

    setup() {
        super.setup();
        this.pos = usePos();
        this.notification = useService("notification");
        this.state = proxy({ board: null, error: "", printing: false });
        onWillStart(async () => {
            try {
                this.state.board = await this.pos.data.call("pos.nm.exchange", "get_rate_board", [
                    this.pos.config.id,
                ]);
            } catch (error) {
                this.state.error =
                    error instanceof ConnectionLostError
                        ? _t("The connection to the server was lost: the exchange rates could not be loaded.")
                        : error?.data?.message || _t("The exchange rates could not be loaded.");
            }
        });
    }

    async print() {
        if (!this.state.board || this.state.printing) {
            return;
        }
        this.state.printing = true;
        try {
            await this.pos.nmPrintReceipt("pos_nm_currency_exchange.pos_exchange_rates_receipt", this.state.board);
        } catch {
            this.notification.add(_t("The exchange rates could not be printed."), { type: "warning" });
        } finally {
            this.state.printing = false;
        }
    }
}
