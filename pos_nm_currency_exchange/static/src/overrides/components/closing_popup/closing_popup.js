import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";

/**
 * Closing control: the exchange operations of the session and the total of
 * their commissions, after the drawers.
 */
patch(ClosePosPopup.prototype, {
    get nmExchangeSummary() {
        const summary = this.pos.nmExchangeSummary;
        return summary && summary.count ? summary : null;
    },
});
