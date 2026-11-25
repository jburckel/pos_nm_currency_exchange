import { Dialog } from "@web/core/dialog/dialog";
import { Component, useProps, proxy, t, onWillStart } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError } from "@web/core/network/rpc";

/**
 * Exchange operations of the session, the latest first, with a Reprint
 * button: the receipt is printed again as a copy, with its cancellation
 * when the operation was cancelled since.
 */
export class ExchangeOperationsPopup extends Component {
    static template = "pos_nm_currency_exchange.ExchangeOperationsPopup";
    static components = { Dialog };
    props = useProps({
        close: t.function(),
    });

    setup() {
        super.setup();
        this.pos = usePos();
        this.notification = useService("notification");
        this.state = proxy({ operations: [], error: "", printing: false });
        onWillStart(async () => {
            try {
                this.state.operations = await this.pos.data.call("pos.nm.exchange", "get_session_operations", [
                    this.pos.session.id,
                ]);
            } catch (error) {
                this.state.error =
                    error instanceof ConnectionLostError
                        ? _t("The connection to the server was lost: the exchange operations could not be loaded.")
                        : error?.data?.message || _t("The exchange operations could not be loaded.");
            }
        });
    }

    async reprint(operation) {
        if (this.state.printing) {
            return;
        }
        this.state.printing = true;
        try {
            const receipt = await this.pos.data.call("pos.nm.exchange", "get_receipt", [operation.id]);
            await this.pos.nmPrintReceipt("pos_nm_currency_exchange.pos_exchange_receipt", receipt);
        } catch {
            this.notification.add(
                _t("The receipt of %(name)s could not be printed.", { name: operation.name }),
                { type: "warning" }
            );
        } finally {
            this.state.printing = false;
        }
    }
}
