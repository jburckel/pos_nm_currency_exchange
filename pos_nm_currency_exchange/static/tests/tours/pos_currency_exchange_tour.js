/* global posmodel */

import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import { registry } from "@web/core/registry";

/**
 * Exchange counter: 50 EUR received, handed back in the main currency.
 * The receipt printing is stubbed (headless runs have no printer and the
 * web fallback opens the print dialog).
 */
registry.category("web_tour.tours").add("PosCurrencyExchangeTour", {
    steps: () =>
        [
            {
                content: "fill the counted amount of the foreign currency at opening",
                trigger: ".nm-multicurrency-opening-section input",
                run: "edit 100",
            },
            Dialog.confirm("Open Register"),
            ProductScreen.isShown(),
            {
                content: "stub the receipt printing",
                trigger: ".pos",
                run: () => {
                    // Keep the generated receipt: its content is checked below.
                    posmodel.ticketPrinter.printWithFallback = async ({ iframe }) => {
                        posmodel.nmTourReceiptHtml = iframe?.contentDocument?.body?.innerHTML || "";
                        return { successful: true };
                    };
                },
            },
            Chrome.clickMenuOption("Currency Exchange"),
            {
                content: "the exchange popup proposes the foreign currency as received",
                trigger: ".modal .nm-currency-exchange select.nm-exchange-currency-in",
            },
            {
                content: "type the amount received",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-in",
                run: "edit 50",
            },
            {
                content: "the amount handed back is quoted: 56.32",
                trigger: ".modal .nm-currency-exchange .nm-exchange-amount-out:contains(/56[.,]32/)",
            },
            {
                content: "the commission is shown: 1.15",
                trigger: ".modal .nm-currency-exchange .nm-exchange-commission:contains(/1[.,]15/)",
            },
            {
                content: "add a note",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-note",
                run: "edit Tour",
            },
            {
                content: "confirm the operation",
                trigger: ".modal .nm-currency-exchange .nm-exchange-confirm:not([disabled])",
                run: "click",
            },
            {
                content: "the operation is recorded and the popup closed",
                trigger: "body:not(:has(.modal .nm-currency-exchange))",
            },
            ProductScreen.isShown(),
            {
                content: "the exchange receipt was rendered and printed",
                trigger: ".pos",
                run: () => {
                    const html = posmodel.nmTourReceiptHtml || "";
                    if (!html.includes("CURRENCY EXCHANGE") || !html.includes("56.32")) {
                        throw new Error("Exchange receipt not rendered: " + html.slice(0, 200));
                    }
                },
            },
        ].flat(),
});
