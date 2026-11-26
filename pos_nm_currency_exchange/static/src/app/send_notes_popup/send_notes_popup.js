import { Dialog } from "@web/core/dialog/dialog";
import { Component, useProps, proxy, t, onWillStart } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError } from "@web/core/network/rpc";
import { formatCurrency } from "@web/core/currency";
import { NumericInput } from "@point_of_sale/app/components/inputs/numeric_input/numeric_input";
import { uuidv4 } from "@point_of_sale/utils";
import { formatAmountInput, parseAmountInput } from "@pos_nm_multicurrencies/overrides/utils/change_currency";

// Coins and notes in whole units of 1/NOTE_UNITS, as the server counts them
// (NOTE_UNITS and NOTE_SEARCH_BUDGET of pos_exchange.py).
const NOTE_UNITS = 10000;
const NOTE_SEARCH_BUDGET = 20000;

/**
 * Quantities of the coins and notes ``units`` (integers, the largest first)
 * adding up exactly to ``target``, the largest first, at most ``limits`` of
 * each when given; null when there is none (or when the search budget is
 * spent). Same search as _nm_decompose on the server.
 */
export function decomposeNotes(units, target, limits = null) {
    const count = units.length;
    const gcd = (a, b) => (b ? gcd(b, a % b) : a);
    if (target < 0 || !count || target % units.reduce(gcd)) {
        return null;
    }
    const result = new Array(count).fill(0);
    const reach = new Array(count + 1).fill(0);
    if (limits) {
        for (let index = count - 1; index >= 0; index--) {
            reach[index] = reach[index + 1] + units[index] * limits[index];
        }
    }
    let budget = NOTE_SEARCH_BUDGET;
    const search = (index, remaining) => {
        if (remaining === 0) {
            return true;
        }
        if (index === count || (limits && remaining > reach[index])) {
            return false;
        }
        if (--budget < 0) {
            return false;
        }
        if (index === count - 1) {
            // The smallest coin settles the rest at once.
            const quantity = Math.floor(remaining / units[index]);
            if (remaining % units[index] || (limits && quantity > limits[index])) {
                return false;
            }
            result[index] = quantity;
            return true;
        }
        let top = Math.floor(remaining / units[index]);
        if (limits) {
            top = Math.min(top, limits[index]);
        }
        for (let quantity = top; quantity >= 0; quantity--) {
            result[index] = quantity;
            if (search(index + 1, remaining - quantity * units[index])) {
                return true;
            }
        }
        result[index] = 0;
        return false;
    };
    return search(0, target) ? result : null;
}

/**
 * Notes sent to another counter of the exchange office: the amount leaves
 * the drawer of its currency at once (statement line on the transit account
 * of the office) and is in transit until the receiving counter receives it.
 *
 * When the notes of the currency are tracked by denomination at this
 * counter, the cashier counts the notes sent in a grid, prefilled with a
 * breakdown of the amount from the stock of the drawer; the notes must add
 * up to the amount.
 *
 * Lost connection: as for an exchange operation, the inputs are frozen
 * until the transfer is confirmed again with the same identifier (the
 * server returns the transfer already recorded) or the popup is discarded.
 */
export class SendNotesPopup extends Component {
    static template = "pos_nm_currency_exchange.SendNotesPopup";
    static components = { Dialog, NumericInput };
    props = useProps({
        getPayload: t.function().optional(),
        close: t.function(),
    });

    setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.state = proxy({
            counters: [],
            currencies: [],
            configToId: null,
            currencyId: null,
            amount: "",
            note: "",
            // Notes sent by denomination ({key: qty}) when the currency is
            // tracked, prefilled for each new amount or currency.
            notes: {},
            notesKey: "",
            loadError: "",
            error: "",
            pending: false,
            saving: false,
        });
        // Sent with the transfer: confirmed again after a lost response, the
        // transfer is not recorded twice.
        this.uuid = uuidv4();
        onWillStart(() => this.loadTargets());
    }

    async loadTargets() {
        try {
            const targets = await this.pos.data.call("pos.nm.exchange.transfer", "get_transfer_targets", [
                this.pos.config.id,
            ]);
            this.state.counters = targets.targets || [];
            this.state.currencies = targets.currencies || [];
            this.state.configToId = this.state.counters[0]?.id || null;
            this.state.currencyId =
                (this.state.currencies.find((currency) => currency.id === this.pos.currency.id) ||
                    this.state.currencies[0])?.id || null;
        } catch (error) {
            this.state.loadError =
                error instanceof ConnectionLostError
                    ? _t("The connection to the server was lost: the counters of the office could not be loaded.")
                    : error?.data?.message || _t("The counters of the office could not be loaded.");
        }
    }

    get counterTo() {
        return this.state.counters.find((counter) => counter.id === this.state.configToId);
    }
    get currency() {
        return this.state.currencies.find((currency) => currency.id === this.state.currencyId);
    }
    get amount() {
        const amount = parseAmountInput(this.state.amount);
        return this.pos.isValidFloat(this.state.amount) && amount > 0 ? amount : 0;
    }
    /**
     * Coins and notes of the currency sent with their stock in the drawer,
     * when its notes are tracked at this counter, else null.
     */
    get notesGrid() {
        const currency = this.currency;
        return currency?.tracked ? { currency_id: currency.id, rows: currency.rows || [] } : null;
    }
    get notesTotal() {
        const grid = this.notesGrid;
        if (!grid) {
            return 0;
        }
        return grid.rows.reduce((total, row) => total + row.value * this.noteQuantity(this.state.notes, row.key), 0);
    }
    /**
     * The notes proposed for the amount from the stock of the drawer: an
     * exact breakdown within the stock, else whatever the stock (the notes
     * the drawer lacks are named: the cash sales move the drawer without
     * denominations), else nothing.
     */
    get proposal() {
        const grid = this.notesGrid;
        const amount = this.amount;
        if (!grid || !amount || !grid.rows.length) {
            return null;
        }
        const units = grid.rows.map((row) => Math.round(row.value * NOTE_UNITS));
        const target = Math.round(amount * NOTE_UNITS);
        const stocks = grid.rows.map((row) => Math.max(row.stock, 0));
        let quantities = decomposeNotes(units, target, stocks);
        let shortfall = "";
        if (!quantities) {
            quantities = decomposeNotes(units, target);
            if (quantities) {
                shortfall = _t("The drawer is short of %(notes)s: check the notes before sending them.", {
                    notes: grid.rows
                        .map((row, index) => [row, quantities[index] - stocks[index]])
                        .filter(([, missing]) => missing > 0)
                        .map(([row, missing]) => `${missing} x ${row.label}`)
                        .join(", "),
                });
            }
        }
        return quantities && { quantities, shortfall };
    }
    get notesShortfall() {
        return this.proposal?.shortfall || "";
    }
    /**
     * The amount cannot be made up with the coins and notes of its currency,
     * a quantity is negative or the notes do not add up to the amount, else
     * an empty string.
     */
    get notesError() {
        const grid = this.notesGrid;
        const amount = this.amount;
        if (!grid || !amount) {
            return "";
        }
        const currency = this.currency;
        if (!this.proposal) {
            return _t("%(amount)s cannot be made up with the coins and notes of %(currency)s.", {
                amount: this.format(amount, currency),
                currency: currency.name,
            });
        }
        if (grid.rows.some((row) => this.noteQuantity(this.state.notes, row.key) < 0)) {
            return _t("The quantities of notes cannot be negative.");
        }
        const total = this.notesTotal;
        if (Math.round((total - amount) * NOTE_UNITS)) {
            return _t("The notes sent add up to %(total)s instead of %(amount)s.", {
                total: this.format(total, currency),
                amount: this.format(amount, currency),
            });
        }
        return "";
    }
    get isValid() {
        return Boolean(this.counterTo && this.currency && this.amount > 0 && !this.notesError);
    }

    // Helpers of the grid sub-template CurrencyExchangeNotes.
    noteQuantity(quantities, key) {
        const quantity = quantities[key];
        return Number.isInteger(quantity) ? quantity : 0;
    }
    notesCurrency(notes) {
        return this.state.currencies.find((currency) => currency.id === notes.currency_id);
    }
    format(amount, currency) {
        return formatCurrency(amount, currency.id);
    }
    amountPlaceholder() {
        return this.state.currencyId ? formatAmountInput(0, this.state.currencyId) : "";
    }

    /**
     * Prefill the grid with the notes proposed, once per amount and currency:
     * the quantities typed by the cashier are kept until either changes.
     */
    proposeNotes() {
        const grid = this.notesGrid;
        const key = `${this.state.currencyId}|${this.amount}`;
        if (!grid) {
            this.state.notes = {};
            this.state.notesKey = "";
            return;
        }
        if (this.state.notesKey === key) {
            return;
        }
        const quantities = this.proposal?.quantities;
        this.state.notes = Object.fromEntries(
            grid.rows.map((row, index) => [row.key, quantities ? quantities[index] : 0])
        );
        this.state.notesKey = key;
    }
    onCounterChange(ev) {
        this.state.configToId = parseInt(ev.target.value);
        this.state.error = "";
    }
    onCurrencyChange(ev) {
        this.state.currencyId = parseInt(ev.target.value);
        this.state.error = "";
        this.proposeNotes();
    }
    onAmountInput(ev) {
        this.state.amount = ev.target.value;
        this.state.error = "";
        this.proposeNotes();
    }
    onAmountBlur() {
        if (this.amount && !this.state.pending) {
            this.state.amount = formatAmountInput(this.amount, this.state.currencyId);
        }
    }
    notesPayload() {
        const grid = this.notesGrid;
        return grid
            ? Object.fromEntries(grid.rows.map((row) => [row.key, this.noteQuantity(this.state.notes, row.key)]))
            : undefined;
    }

    async confirm() {
        if (!this.isValid || this.state.saving) {
            return;
        }
        this.state.saving = true;
        try {
            // The popup cannot be closed (Discard, Escape) while recording.
            this.ui.block();
            let transfer;
            try {
                transfer = await this.pos.data.call(
                    "pos.nm.exchange.transfer",
                    "send_from_ui",
                    [this.pos.session.id, this.state.configToId, this.state.currencyId, this.amount],
                    {
                        notes: this.notesPayload(),
                        note: this.state.note.trim() || false,
                        // Confirmed again after a lost response: the transfer
                        // already recorded is returned, not recorded twice.
                        uuid: this.uuid,
                    }
                );
            } finally {
                this.ui.unblock();
            }
            await this.pos.logEmployeeMessage(
                _t("Note transfer %(name)s: %(amount)s sent to %(counter)s", {
                    name: transfer.name,
                    amount: transfer.amount_formatted,
                    counter: transfer.config_to,
                }),
                "CASH_DRAWER_ACTION"
            );
            await printTransferSlip(this.pos, this.notification, transfer);
            this.notification.add(
                _t("%(name)s: %(amount)s sent to %(counter)s.", {
                    name: transfer.name,
                    amount: transfer.amount_formatted,
                    counter: transfer.config_to,
                }),
                { type: "success" }
            );
            this.props.getPayload?.(transfer);
            this.props.close();
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                this.state.pending = true;
            } else {
                // Refused by the server: nothing was recorded with this
                // identifier, the inputs can be changed again.
                this.state.pending = false;
                this.state.error = error?.data?.message || _t("The transfer could not be recorded.");
            }
        } finally {
            this.state.saving = false;
        }
    }
}

/**
 * Open the cash drawer and print the slip of a transfer, sent or received.
 */
export async function printTransferSlip(pos, notification, transfer) {
    try {
        await pos.openCashbox();
    } catch {
        notification.add(_t("The cash drawer could not be opened."), { type: "warning" });
    }
    try {
        await pos.nmPrintReceipt("pos_nm_currency_exchange.pos_exchange_transfer_receipt", transfer);
    } catch {
        notification.add(_t("The slip of %(name)s could not be printed.", { name: transfer.name }), {
            type: "warning",
        });
    }
}
