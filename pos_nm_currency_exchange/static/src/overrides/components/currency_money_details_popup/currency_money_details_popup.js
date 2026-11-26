import { patch } from "@web/core/utils/patch";
import { CurrencyMoneyDetailsPopup } from "@pos_nm_multicurrencies/overrides/components/currency_money_details_popup/currency_money_details_popup";

/**
 * Closing count of a foreign currency whose notes are tracked: the quantity
 * of each coin/note expected in the drawer (opening count and exchange
 * operations of the session) is shown next to its input.
 */
patch(CurrencyMoneyDetailsPopup.prototype, {
    get nmExpectedNotes() {
        if (this.props.context !== "Closing") {
            return null;
        }
        const detail = (this.pos.nmClosingDetails || []).find(
            (entry) => entry.currency_id === this.currency.id
        );
        return detail?.nm_expected_notes || null;
    },
    // Keys are value strings ("50", "0.5"): matched by value.
    nmExpectedQuantity(moneyValue) {
        const value = parseFloat(moneyValue);
        const key = Object.keys(this.nmExpectedNotes).find((key) => parseFloat(key) === value);
        return key === undefined ? 0 : this.nmExpectedNotes[key];
    },
});
