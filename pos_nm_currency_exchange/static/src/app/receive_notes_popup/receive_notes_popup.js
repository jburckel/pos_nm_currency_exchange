import { Dialog } from "@web/core/dialog/dialog";
import { Component, useProps, proxy, t, onWillStart } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError } from "@web/core/network/rpc";
import { formatCurrency } from "@web/core/currency";
import { NumericInput } from "@point_of_sale/app/components/inputs/numeric_input/numeric_input";
import {
    decomposeNotes,
    printTransferSlip,
} from "@pos_nm_currency_exchange/app/send_notes_popup/send_notes_popup";

// Coins and notes in whole units of 1/NOTE_UNITS, as the server counts them.
const NOTE_UNITS = 10000;

/**
 * Notes in transit to this counter, sent by the other counters of the
 * exchange office: each one is received at once into the drawer of its
 * currency (statement line from the transit account of the office), for
 * the amount sent; a difference is found by the closing count.
 *
 * When this counter tracks the notes of the currency and the sending counter
 * did not count them, the cashier counts the notes received in a grid,
 * prefilled with a breakdown of the amount, the largest first.
 */
export class ReceiveNotesPopup extends Component {
    static template = "pos_nm_currency_exchange.ReceiveNotesPopup";
    static components = { Dialog, NumericInput };
    props = useProps({
        close: t.function(),
    });

    setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.state = proxy({
            transfers: [],
            loaded: false,
            error: "",
            receiving: false,
            // Transfer whose notes are being counted, and the quantities
            // counted by denomination ({key: qty}).
            counting: null,
            notes: {},
        });
        onWillStart(() => this.loadTransfers());
    }

    async loadTransfers() {
        try {
            this.state.transfers = await this.pos.data.call("pos.nm.exchange.transfer", "get_incoming_transfers", [
                this.pos.config.id,
            ]);
            this.state.error = "";
            if (!this.state.transfers.some((transfer) => transfer.id === this.state.counting?.id)) {
                this.state.counting = null;
            }
        } catch (error) {
            this.state.error =
                error instanceof ConnectionLostError
                    ? _t("The connection to the server was lost: the notes in transit could not be loaded.")
                    : error?.data?.message || _t("The notes in transit could not be loaded.");
        }
        this.state.loaded = true;
    }

    /**
     * Coins and notes of the transfer being counted, with their stock in
     * the drawer, else null.
     */
    get notesGrid() {
        const transfer = this.state.counting;
        return transfer ? { currency_id: transfer.currency_id, rows: transfer.rows || [] } : null;
    }
    get notesTotal() {
        const grid = this.notesGrid;
        if (!grid) {
            return 0;
        }
        return grid.rows.reduce((total, row) => total + row.value * this.noteQuantity(this.state.notes, row.key), 0);
    }
    /**
     * The notes counted are negative or do not add up to the amount, else an
     * empty string.
     */
    get notesError() {
        const transfer = this.state.counting;
        const grid = this.notesGrid;
        if (!grid) {
            return "";
        }
        if (grid.rows.some((row) => this.noteQuantity(this.state.notes, row.key) < 0)) {
            return _t("The quantities of notes cannot be negative.");
        }
        const total = this.notesTotal;
        if (Math.round((total - transfer.amount) * NOTE_UNITS)) {
            return _t("The notes received add up to %(total)s instead of %(amount)s.", {
                total: this.format(total, this.notesCurrency(grid)),
                amount: transfer.amount_formatted,
            });
        }
        return "";
    }

    // Helpers of the grid sub-template CurrencyExchangeNotes.
    noteQuantity(quantities, key) {
        const quantity = quantities[key];
        return Number.isInteger(quantity) ? quantity : 0;
    }
    notesCurrency(notes) {
        return { id: notes.currency_id };
    }
    format(amount, currency) {
        return formatCurrency(amount, currency.id);
    }

    /**
     * Count the notes of a transfer the sending counter did not count: the
     * grid is prefilled with a breakdown of the amount, the largest first.
     */
    count(transfer) {
        const rows = transfer.rows || [];
        const units = rows.map((row) => Math.round(row.value * NOTE_UNITS));
        const quantities = decomposeNotes(units, Math.round(transfer.amount * NOTE_UNITS));
        this.state.notes = Object.fromEntries(rows.map((row, index) => [row.key, quantities ? quantities[index] : 0]));
        this.state.counting = transfer;
        this.state.error = "";
    }
    notesPayload(transfer) {
        if (!transfer.needs_notes) {
            return undefined;
        }
        return Object.fromEntries(
            (transfer.rows || []).map((row) => [row.key, this.noteQuantity(this.state.notes, row.key)])
        );
    }

    async receive(transfer) {
        if (this.state.receiving) {
            return;
        }
        if (transfer.needs_notes && this.state.counting?.id !== transfer.id) {
            this.count(transfer);
            return;
        }
        if (transfer.needs_notes && this.notesError) {
            return;
        }
        this.state.receiving = true;
        try {
            let received;
            try {
                this.ui.block();
                received = await this.pos.data.call(
                    "pos.nm.exchange.transfer",
                    "receive_from_ui",
                    [transfer.id, this.pos.session.id],
                    { notes: this.notesPayload(transfer) }
                );
            } finally {
                this.ui.unblock();
            }
            await this.pos.logEmployeeMessage(
                _t("Note transfer %(name)s: %(amount)s received from %(counter)s", {
                    name: received.name,
                    amount: received.amount_formatted,
                    counter: received.config_from,
                }),
                "CASH_DRAWER_ACTION"
            );
            await printTransferSlip(this.pos, this.notification, received);
            this.notification.add(
                _t("%(name)s: %(amount)s received from %(counter)s.", {
                    name: received.name,
                    amount: received.amount_formatted,
                    counter: received.config_from,
                }),
                { type: "success" }
            );
            this.state.counting = null;
            await this.loadTransfers();
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                // Received again in the same session, the transfer already
                // received is returned, not received twice.
                this.state.error = _t(
                    "The connection was lost: the transfer may have been received. Receive it again once the connection is back: a transfer already received is not received twice."
                );
            } else {
                // Refused by the server (cancelled or received meanwhile...):
                // the list is reloaded, then the refusal shown (a successful
                // load clears the error).
                await this.loadTransfers();
                this.state.error = error?.data?.message || _t("The transfer could not be received.");
            }
        } finally {
            this.state.receiving = false;
        }
    }
}
