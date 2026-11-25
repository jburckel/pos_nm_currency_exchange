/* global posmodel */

import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import { registry } from "@web/core/registry";

function stubPrinting() {
    return {
        content: "stub the receipt printing",
        trigger: ".pos",
        run: () => {
            // Keep the generated receipt: its content is checked below.
            posmodel.ticketPrinter.printWithFallback = async ({ iframe }) => {
                posmodel.nmTourReceiptHtml = iframe?.contentDocument?.body?.innerHTML || "";
                return { successful: true };
            };
        },
    };
}

function selectCurrency(side, name) {
    const selector = `.modal .nm-currency-exchange select.nm-exchange-currency-${side}`;
    return {
        content: `select ${name} as the currency ${side === "in" ? "received" : "handed back"}`,
        trigger: selector,
        run: () => {
            const select = document.querySelector(selector);
            const option = [...select.options].find((opt) => opt.textContent.trim() === name);
            select.value = option.value;
            select.dispatchEvent(new Event("change"));
        },
    };
}

/**
 * Exchange counter: 50 EUR received, handed back in the main currency.
 * The receipt printing is stubbed (headless runs have no printer and the
 * web fallback opens the print dialog).
 */
registry.category("web_tour.tours").add("PosCurrencyExchangeTour", {
    steps: () =>
        [
            {
                content: "fill the counted amount of the main currency at opening: the drawer hands back the notes",
                trigger:
                    ".modal .opening-cash-section:not(.nm-multicurrency-opening-section) .cash-input-sub-section input",
                run: "edit 100",
            },
            {
                content: "wait for the debounced input of the main currency",
                trigger: ".modal .opening-cash-section:not(.nm-multicurrency-opening-section) input:value(100)",
                run: () => new Promise((resolve) => setTimeout(resolve, 500)),
            },
            {
                content: "fill the counted amount of the foreign currency at opening",
                trigger: ".nm-multicurrency-opening-section input",
                run: "edit 100",
            },
            Dialog.confirm("Open Register"),
            ProductScreen.isShown(),
            stubPrinting(),
            Chrome.clickMenuOption("Currency Exchange"),
            {
                content: "the exchange popup proposes the foreign currency as received",
                trigger: ".modal .nm-currency-exchange select.nm-exchange-currency-in",
            },
            {
                content: "type an amount the EUR notes cannot make up (1 EUR coins)",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-in",
                run: "edit 50.5",
            },
            {
                content: "a warning says the amount cannot be made up with the coins",
                trigger: ".modal .nm-currency-exchange .nm-exchange-step-warning",
            },
            {
                content: "type the amount received",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-in",
                run: "edit 50",
            },
            {
                content: "no warning for 50",
                trigger: ".modal .nm-currency-exchange:not(:has(.nm-exchange-step-warning))",
            },
            {
                content: "the amount handed back is quoted: 56.32",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-out:value(56.32)",
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
            Chrome.clickMenuOption("Close Register"),
            {
                content: "the closing popup shows the commission of the operation: 1.15",
                trigger: ".modal .close-pos-popup .nm-exchange-closing-commission:contains(/1[.,]15/)",
            },
            {
                content: "the closing popup shows the rate margin of the operation",
                trigger: ".modal .close-pos-popup .nm-exchange-closing-rate-margin",
            },
            {
                content: "the closing popup lists the operation",
                trigger: ".modal .close-pos-popup .nm-exchange-closing:contains('EXC/'):contains(/56[.,]32/)",
            },
            {
                content: "close the register; the register redirects to the login page",
                trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains('Close Register')",
                run: "click",
                expectUnloadPage: true,
            },
        ].flat(),
});

/**
 * Exchange counter with EUR and XPF (no decimals) in cash, 300 counted in
 * the main drawer, none in the foreign drawers:
 * - 25000 XPF typed and blurred stays 25000 (not 25), 209.50 handed back;
 * - swapped to main -> EUR: the empty EUR drawer is shown and refused
 *   before Confirm;
 * - reverse quote: the customer wants 10000 XPF, 83.81 to receive.
 */
registry.category("web_tour.tours").add("PosCurrencyExchangeReverseTour", {
    steps: () =>
        [
            {
                content: "fill the counted amount of the main currency at opening",
                trigger:
                    ".modal .opening-cash-section:not(.nm-multicurrency-opening-section) .cash-input-sub-section input",
                run: "edit 300",
            },
            {
                content: "wait for the debounced input of the main currency",
                trigger: ".modal .opening-cash-section:not(.nm-multicurrency-opening-section) input:value(300)",
                run: () => new Promise((resolve) => setTimeout(resolve, 500)),
            },
            Dialog.confirm("Open Register"),
            ProductScreen.isShown(),
            stubPrinting(),

            Chrome.clickMenuOption("Currency Exchange"),
            selectCurrency("in", "XPF"),
            {
                content: "type 25000 XPF",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-in",
                run: "edit 25000",
            },
            {
                content: "leave the amount field",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-note",
                run: "click",
            },
            {
                content: "the amount stays 25000, without thousands separator",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-in:value(/^25000$/)",
            },
            {
                content: "25000 XPF at 119.33: 209.50 handed back",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-out:value(209.50)",
            },
            {
                content: "the main drawer is shown: 300",
                trigger: ".modal .nm-currency-exchange .nm-exchange-drawer:contains(/300[.,]00/)",
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

            Chrome.clickMenuOption("Currency Exchange"),
            selectCurrency("in", "EUR"),
            {
                content: "swap the currencies: main currency received, EUR handed back",
                trigger: ".modal .nm-currency-exchange .nm-exchange-swap",
                run: "click",
            },
            {
                content: "type 50",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-in",
                run: "edit 50",
            },
            {
                content: "the empty EUR drawer is shown",
                trigger: ".modal .nm-currency-exchange .nm-exchange-drawer.text-danger",
            },
            {
                content: "the drawer refusal is shown before Confirm",
                trigger: ".modal .nm-currency-exchange .nm-exchange-error:contains('cannot be handed back')",
            },
            {
                content: "Confirm is disabled",
                trigger: ".modal .nm-currency-exchange .nm-exchange-confirm[disabled]",
            },
            selectCurrency("out", "XPF"),
            {
                content: "the customer wants 10000 XPF",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-out",
                run: "edit 10000",
            },
            {
                content: "the amount to receive is computed: 83.81",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-in:value(83.81)",
            },
            {
                content: "the reverse quote is explained",
                trigger: ".modal .nm-currency-exchange .nm-exchange-reverse-hint",
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
        ].flat(),
});

/**
 * Identity document above 20: 50 EUR received (worth 57.47). The customer
 * is required, then its document, prefilled from the contact, is refused
 * as expired until a valid expiry date is typed.
 */
registry.category("web_tour.tours").add("PosCurrencyExchangeDocumentTour", {
    steps: () =>
        [
            {
                content: "fill the counted amount of the main currency at opening",
                trigger:
                    ".modal .opening-cash-section:not(.nm-multicurrency-opening-section) .cash-input-sub-section input",
                run: "edit 100",
            },
            {
                content: "wait for the debounced input of the main currency",
                trigger: ".modal .opening-cash-section:not(.nm-multicurrency-opening-section) input:value(100)",
                run: () => new Promise((resolve) => setTimeout(resolve, 500)),
            },
            Dialog.confirm("Open Register"),
            ProductScreen.isShown(),
            stubPrinting(),
            Chrome.clickMenuOption("Currency Exchange"),
            {
                content: "type the amount received",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-in",
                run: "edit 50",
            },
            {
                content: "a customer with an identity document is required",
                trigger: ".modal .nm-currency-exchange .nm-exchange-customer.btn-outline-danger",
            },
            {
                content: "the requirement is explained",
                trigger: ".modal .nm-currency-exchange .nm-exchange-customer-required:contains('identity document')",
            },
            {
                content: "Confirm is disabled without customer",
                trigger: ".modal .nm-currency-exchange .nm-exchange-confirm[disabled]",
            },
            {
                content: "select the customer",
                trigger: ".modal .nm-currency-exchange .nm-exchange-customer",
                run: "click",
            },
            PartnerList.clickPartner("Partner Test 1"),
            {
                content: "the document of the customer is prefilled",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-document-number:value(X1234567)",
            },
            {
                content: "the expired document is refused",
                trigger: ".modal .nm-currency-exchange .nm-exchange-document-error:contains('expired')",
            },
            {
                content: "Confirm is disabled with an expired document",
                trigger: ".modal .nm-currency-exchange .nm-exchange-confirm[disabled]",
            },
            {
                content: "type a valid expiry date",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-document-expiry",
                run: function () {
                    this.anchor.value = "2099-12-31";
                    this.anchor.dispatchEvent(new Event("change"));
                },
            },
            {
                content: "the document is accepted",
                trigger: ".modal .nm-currency-exchange:not(:has(.nm-exchange-document-error))",
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
            {
                content: "the receipt shows the type and the end of the number only",
                trigger: ".pos",
                run: () => {
                    const html = posmodel.nmTourReceiptHtml || "";
                    if (!html.includes("****4567") || html.includes("X1234567")) {
                        throw new Error("Identity document not masked on the receipt: " + html.slice(0, 400));
                    }
                },
            },
        ].flat(),
});
