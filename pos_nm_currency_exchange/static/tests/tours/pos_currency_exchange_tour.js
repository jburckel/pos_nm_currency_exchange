/* global posmodel */

import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PartnerList from "@point_of_sale/../tests/pos/tours/utils/partner_list_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import { registry } from "@web/core/registry";
import { ConnectionLostError } from "@web/core/network/rpc";

function stubPrinting() {
    return {
        content: "stub the receipt printing",
        trigger: ".pos",
        run: () => {
            // Keep the generated receipt: its content is checked below.
            posmodel.ticketPrinter.printWithFallback = async ({ iframe }) => {
                posmodel.nmTourReceiptHtml = iframe?.contentDocument?.body?.innerHTML || "";
                document.body.classList.add("nm-tour-printed");
                return { successful: true };
            };
        },
    };
}

/**
 * The next create_from_ui is recorded by the server but its response is
 * lost, as when the connection drops right after the commit.
 */
function loseNextConfirmResponse() {
    return {
        content: "lose the response of the next confirmation",
        trigger: ".modal .nm-currency-exchange",
        run: () => {
            const call = posmodel.data.call.bind(posmodel.data);
            posmodel.data.call = async (model, method, ...args) => {
                const result = await call(model, method, ...args);
                if (method === "create_from_ui") {
                    posmodel.data.call = call;
                    throw new ConnectionLostError("/web/dataset/call_kw");
                }
                return result;
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
                content: "the amount handed back is in the summary",
                trigger: ".modal .nm-currency-exchange .nm-exchange-handed-back:contains(/56[.,]32/)",
            },
            {
                content: "add a note",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-note",
                run: "edit Tour",
            },
            loseNextConfirmResponse(),
            {
                content: "confirm the operation",
                trigger: ".modal .nm-currency-exchange .nm-exchange-confirm:not([disabled])",
                run: "click",
            },
            {
                content: "the lost connection is explained",
                trigger: ".modal .nm-currency-exchange .nm-exchange-retry",
            },
            {
                content: "the amounts and currencies are frozen",
                trigger:
                    ".modal .nm-currency-exchange input.nm-exchange-amount-in[readonly]:value(50)",
            },
            {
                content: "the currency received cannot be changed",
                trigger: ".modal .nm-currency-exchange select.nm-exchange-currency-in[disabled]",
            },
            {
                content: "the note sent with the operation is frozen too",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-note[readonly]:value(Tour)",
            },
            {
                content: "confirm again: the operation already recorded is returned",
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
                    const expected = [
                        "CURRENCY EXCHANGE",
                        "56.32",
                        "Tour Header",
                        "LIC-TOUR-7",
                        "Purchase of foreign currency",
                    ];
                    if (expected.some((text) => !html.includes(text)) || html.includes("COPY")) {
                        throw new Error("Exchange receipt not rendered: " + html.slice(0, 400));
                    }
                    if (!/\d{2}:\d{2}:\d{2}/.test(html)) {
                        throw new Error("The time of the operation has no seconds: " + html.slice(0, 400));
                    }
                    posmodel.nmTourReceiptHtml = "";
                    document.body.classList.remove("nm-tour-printed");
                },
            },
            Chrome.clickMenuOption("Exchange Operations"),
            {
                content: "the operation of the session is listed",
                trigger: ".modal .nm-exchange-operations .nm-exchange-operation:contains('EXC/'):contains(/56[.,]32/)",
            },
            {
                content: "print its receipt again",
                trigger: ".modal .nm-exchange-operations .nm-exchange-reprint:not([disabled])",
                run: "click",
            },
            {
                content: "the receipt is printed again, as a copy",
                trigger: "body.nm-tour-printed",
                run: () => {
                    const html = posmodel.nmTourReceiptHtml || "";
                    if (!html.includes("COPY") || !html.includes("56.32")) {
                        throw new Error("Receipt not printed again: " + html.slice(0, 400));
                    }
                    document.body.classList.remove("nm-tour-printed");
                },
            },
            Dialog.cancel(),
            Chrome.clickMenuOption("Exchange Rates"),
            {
                content: "the rates of EUR are shown",
                trigger: ".modal .nm-exchange-rates .nm-exchange-rate-row:contains('EUR') .nm-exchange-buy-amount",
            },
            {
                content: "print the rates",
                trigger: ".modal .nm-exchange-rates .nm-exchange-rates-print:not([disabled])",
                run: "click",
            },
            {
                content: "the rates are printed",
                trigger: "body.nm-tour-printed",
                run: () => {
                    const html = posmodel.nmTourReceiptHtml || "";
                    if (!html.includes("EXCHANGE RATES") || !html.includes("EUR")) {
                        throw new Error("Exchange rates not printed: " + html.slice(0, 400));
                    }
                },
            },
            Dialog.cancel(),
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
                content: "the customer wants 9998 XPF, not a multiple of the 5 XPF coins",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-out",
                run: "edit 9998",
            },
            {
                content: "leave the field at once, before the quote",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-note",
                run: "click",
            },
            {
                content: "the amount to receive is computed: 83.81",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-in:value(83.81)",
            },
            {
                content: "the field shows the amount actually handed back: 10000",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-out:value(/^10000$/)",
            },
            {
                content: "the summary shows it too",
                trigger: ".modal .nm-currency-exchange .nm-exchange-handed-back:contains(/10[,.\u00a0\u202f ]?000/)",
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
                content: "the document of the customer is prefilled, the end of its number only",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-document-number[placeholder='****4567']",
            },
            {
                content: "its type is selected",
                trigger: ".modal .nm-currency-exchange select.nm-exchange-document-type:value(passport)",
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
