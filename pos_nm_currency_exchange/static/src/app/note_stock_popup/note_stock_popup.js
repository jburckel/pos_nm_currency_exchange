import { Dialog } from "@web/core/dialog/dialog";
import { Component, useProps, proxy, t, onWillStart } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError } from "@web/core/network/rpc";

/**
 * Notes in the drawer by denomination, for each currency whose notes are
 * tracked: the quantity counted at the opening, the notes received and
 * handed back by the exchange operations of the session since, and the
 * stock expected in the drawer.
 */
export class NoteStockPopup extends Component {
    static template = "pos_nm_currency_exchange.NoteStockPopup";
    static components = { Dialog };
    props = useProps({
        close: t.function(),
    });

    setup() {
        super.setup();
        this.pos = usePos();
        this.state = proxy({ currencies: [], error: "" });
        onWillStart(async () => {
            try {
                this.state.currencies = await this.pos.data.call("pos.nm.exchange", "get_note_stock", [
                    this.pos.config.id,
                ]);
            } catch (error) {
                this.state.error =
                    error instanceof ConnectionLostError
                        ? _t("The connection to the server was lost: the note stock could not be loaded.")
                        : error?.data?.message || _t("The note stock could not be loaded.");
            }
        });
    }

    formatQuantity(quantity) {
        return quantity > 0 ? `+${quantity}` : `${quantity}`;
    }
}
