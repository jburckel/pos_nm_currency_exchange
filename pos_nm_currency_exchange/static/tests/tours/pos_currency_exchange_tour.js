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
 * The next quote of 50 received is lost with the connection; the quotes of
 * 50 requested afterwards are counted (posmodel.nmTourQuotesRetried).
 */
function loseNextQuote() {
    return {
        content: "lose the next quote of 50 with the connection",
        trigger: ".modal .nm-currency-exchange",
        run: () => {
            const call = posmodel.data.call.bind(posmodel.data);
            posmodel.nmTourQuotesRetried = 0;
            let lost = false;
            posmodel.data.call = async (model, method, args = [], ...rest) => {
                if (method === "get_quote" && args[2] === 50) {
                    if (!lost) {
                        lost = true;
                        throw new ConnectionLostError("/web/dataset/call_kw");
                    }
                    posmodel.nmTourQuotesRetried++;
                }
                return call(model, method, args, ...rest);
            };
            posmodel.nmTourRestoreCall = () => {
                posmodel.data.call = call;
            };
        },
    };
}

/**
 * The next ``confirmMethod`` call (create_from_ui of an exchange) is
 * recorded by the server but its response is lost, as when the connection
 * drops right after the commit.
 */
function loseNextConfirmResponse(confirmMethod = "create_from_ui", popup = ".modal .nm-currency-exchange") {
    return {
        content: "lose the response of the next confirmation",
        trigger: popup,
        run: () => {
            const call = posmodel.data.call.bind(posmodel.data);
            posmodel.data.call = async (model, method, ...args) => {
                const result = await call(model, method, ...args);
                if (method === confirmMethod) {
                    posmodel.data.call = call;
                    throw new ConnectionLostError("/web/dataset/call_kw");
                }
                return result;
            };
        },
    };
}

/**
 * The quotes shown hand back 1 more than the server would (as when the
 * manager changes a rate after the quote was shown) until the next
 * create_from_ui, which the server refuses as a changed quote. The quotes
 * requested afterwards are counted.
 */
function staleQuotesUntilConfirm() {
    return {
        content: "show stale quotes until the next confirmation",
        trigger: ".modal .nm-currency-exchange",
        run: () => {
            const call = posmodel.data.call.bind(posmodel.data);
            posmodel.nmTourQuotesAfterRefusal = 0;
            let refused = false;
            posmodel.data.call = async (model, method, args = [], kwargs = {}, ...rest) => {
                if (method === "get_quote" && !refused) {
                    const quote = await call(model, method, args, kwargs, ...rest);
                    return { ...quote, amount_out: quote.amount_out + 1 };
                }
                if (method === "create_from_ui" && !refused) {
                    refused = true;
                    posmodel.nmTourConfirmedAmountOut = kwargs.amount_out;
                } else if (method === "create_from_ui") {
                    posmodel.nmTourConfirmedAmountOut = kwargs.amount_out;
                    posmodel.data.call = call;
                } else if (method === "get_quote") {
                    posmodel.nmTourQuotesAfterRefusal++;
                }
                return call(model, method, args, kwargs, ...rest);
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
            loseNextQuote(),
            {
                content: "type the amount received",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-in",
                run: "edit 50",
            },
            {
                content: "the quote is lost with the connection: explained, Confirm disabled",
                trigger:
                    ".modal .nm-currency-exchange:has(.nm-exchange-error:contains('connection to the server was lost'):contains('requested again')) .nm-exchange-confirm[disabled]",
            },
            {
                content: "no quote is shown meanwhile",
                trigger: ".modal .nm-currency-exchange:not(:has(.nm-exchange-quote))",
            },
            {
                content: "the quote is requested again a few seconds later, once: the error is gone",
                trigger:
                    ".modal .nm-currency-exchange:not(:has(.nm-exchange-error)) input.nm-exchange-amount-out:value(56.32)",
                timeout: 15000,
                run: () => {
                    if (posmodel.nmTourQuotesRetried !== 1) {
                        throw new Error(`Quotes requested again: ${posmodel.nmTourQuotesRetried}`);
                    }
                    posmodel.nmTourRestoreCall();
                },
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
                content: "the closing popup shows the Currency Exchange block",
                trigger: ".modal .close-pos-popup .nm-exchange-closing > div:first-child:contains('Currency Exchange')",
            },
            {
                content: "with the Rate Margin line: none at the rate of Odoo, 0.00",
                trigger:
                    ".modal .close-pos-popup .nm-exchange-closing-rate-margin:contains('Rate Margin') > span:last-child:contains(/^\\D*0[.,]00\\D*$/)",
            },
            {
                content: "and the number of operations: 1",
                trigger:
                    ".modal .close-pos-popup .nm-exchange-closing > div:contains('Operations') > span:last-child:contains(/^1$/)",
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
                run: "edit 200",
            },
            {
                content: "wait for the debounced input of the main currency",
                trigger: ".modal .opening-cash-section:not(.nm-multicurrency-opening-section) input:value(200)",
                run: () => new Promise((resolve) => setTimeout(resolve, 500)),
            },
            Dialog.confirm("Open Register"),
            ProductScreen.isShown(),
            stubPrinting(),
            Chrome.clickMenuOption("Currency Exchange"),
            staleQuotesUntilConfirm(),
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
                content: "tick No expiry date",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-document-no-expiry",
                run: "click",
            },
            {
                content: "the expiry date is no longer asked and the document is accepted",
                trigger:
                    ".modal .nm-currency-exchange:not(:has(input.nm-exchange-document-expiry)):not(:has(.nm-exchange-document-error))",
            },
            {
                content: "untick No expiry date",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-document-no-expiry:checked",
                run: "click",
            },
            {
                content: "the expiry date is required again",
                trigger: ".modal .nm-currency-exchange .nm-exchange-document-error:contains('expiry date')",
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
                content: "the stale quote is shown: 58.47 handed back",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-out:value(58.47)",
            },
            {
                content: "confirm the operation with the stale quote",
                trigger: ".modal .nm-currency-exchange .nm-exchange-confirm:not([disabled])",
                run: "click",
            },
            {
                content: "the popup explains that the quote changed and stays open",
                trigger: ".modal .nm-currency-exchange .nm-exchange-quote-changed",
            },
            {
                content: "a fresh quote is shown: Confirm is enabled again, without the error of the server",
                trigger:
                    ".modal .nm-currency-exchange:not(:has(.nm-exchange-error)) .nm-exchange-confirm:not([disabled])",
                run: () => {
                    if (posmodel.nmTourConfirmedAmountOut !== 58.47) {
                        throw new Error(`Stale amount confirmed: ${posmodel.nmTourConfirmedAmountOut}`);
                    }
                    if (posmodel.nmTourQuotesAfterRefusal !== 1) {
                        throw new Error(`Quotes requested after the refusal: ${posmodel.nmTourQuotesAfterRefusal}`);
                    }
                },
            },
            {
                content: "the fresh quote of the server is shown: 57.47 handed back",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-out:value(57.47)",
            },
            {
                content: "nothing is confirmed without the cashier: the popup is still open",
                trigger: ".modal .nm-currency-exchange .nm-exchange-quote-changed",
                run: () => new Promise((resolve) => setTimeout(resolve, 500)),
            },
            {
                content: "confirm the operation again",
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
                    if (posmodel.nmTourConfirmedAmountOut !== 57.47) {
                        throw new Error(`Amount confirmed again: ${posmodel.nmTourConfirmedAmountOut}`);
                    }
                    if (!html.includes("****4567") || html.includes("X1234567")) {
                        throw new Error("Identity document not masked on the receipt: " + html.slice(0, 400));
                    }
                },
            },
            Chrome.clickMenuOption("Currency Exchange"),
            {
                content: "type the amount received of a second operation",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-in",
                run: "edit 50",
            },
            {
                content: "select the customer again",
                trigger: ".modal .nm-currency-exchange .nm-exchange-customer.btn-outline-danger",
                run: "click",
            },
            PartnerList.clickPartner("Partner Test 1"),
            {
                content: "the expiry date saved by the first operation is prefilled",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-document-expiry:value(2099-12-31)",
            },
            {
                content: "the document is accepted",
                trigger:
                    ".modal .nm-currency-exchange:not(:has(.nm-exchange-document-error)) input.nm-exchange-document-no-expiry:not(:checked)",
            },
            {
                content: "the new document of the customer has no expiry date: tick No expiry date",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-document-no-expiry",
                run: "click",
            },
            {
                content: "the expiry date is hidden and the document accepted",
                trigger:
                    ".modal .nm-currency-exchange:not(:has(input.nm-exchange-document-expiry)):not(:has(.nm-exchange-document-error)) input.nm-exchange-document-no-expiry:checked",
            },
            {
                content: "confirm the second operation",
                trigger: ".modal .nm-currency-exchange .nm-exchange-confirm:not([disabled])",
                run: "click",
            },
            {
                content: "the second operation is recorded and the popup closed",
                trigger: "body:not(:has(.modal .nm-currency-exchange))",
            },
            ProductScreen.isShown(),
        ].flat(),
});

/**
 * The counter is enabled but cannot record an operation: Currency Exchange
 * explains why (``message``) instead of opening the popup.
 */
function blockedCounterTour(message) {
    return {
        steps: () =>
            [
                Dialog.confirm("Open Register"),
                ProductScreen.isShown(),
                Chrome.clickMenuOption("Currency Exchange"),
                {
                    content: "the reason is shown instead of the exchange popup",
                    trigger: `.modal .modal-title:contains('Currency Exchange')`,
                },
                {
                    content: `the message says: ${message}`,
                    trigger: `.modal .modal-body:contains("${message}")`,
                },
                {
                    content: "the exchange popup is not opened",
                    trigger: "body:not(:has(.nm-currency-exchange))",
                },
                Dialog.confirm(),
                {
                    content: "the message is closed",
                    trigger: "body:not(:has(.modal))",
                },
                ProductScreen.isShown(),
            ].flat(),
    };
}

registry
    .category("web_tour.tours")
    .add(
        "PosCurrencyExchangeNoAccountTour",
        blockedCounterTour("Set the exchange commission account of the Point of Sale")
    );
registry
    .category("web_tour.tours")
    .add(
        "PosCurrencyExchangeNoCurrencyTour",
        blockedCounterTour("Add a foreign currency to the cash payment method of the Point of Sale")
    );

/**
 * With the Employees module (pos_hr): the employee logged in at the
 * register records the operation. No import of pos_hr here: this file is
 * loaded without it too.
 */
registry.category("web_tour.tours").add("PosCurrencyExchangeEmployeeTour", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            {
                content: "log in",
                trigger: ".login-overlay .select-cashier",
                run: "click",
            },
            {
                content: "select the employee",
                trigger: ".cashier-selection-item:contains('NM Tour Employee')",
                run: "click",
            },
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
            {
                content: "the employee is the cashier",
                trigger: ".pos",
                run: () => {
                    const cashier = posmodel.accessRight.loggedCashier;
                    if (cashier?.name !== "NM Tour Employee") {
                        throw new Error(`Cashier logged in: ${cashier?.name}`);
                    }
                },
            },
            stubPrinting(),
            Chrome.clickMenuOption("Currency Exchange"),
            {
                content: "type the amount received",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-in",
                run: "edit 50",
            },
            {
                content: "the amount handed back is quoted: 57.47",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-out:value(57.47)",
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
                content: "the receipt names the employee",
                trigger: "body.nm-tour-printed",
                run: () => {
                    const html = posmodel.nmTourReceiptHtml || "";
                    if (!html.includes("NM Tour Employee")) {
                        throw new Error("Employee not on the receipt: " + html.slice(0, 400));
                    }
                },
            },
            ProductScreen.isShown(),
        ].flat(),
});

/**
 * Quantity of the coin/note of ``value`` in the money details popup of a
 * foreign currency (largest first).
 */
function countNote(value, quantity) {
    return {
        content: `count ${quantity} x ${value}`,
        trigger: `.modal .nm-currency-money-details div.d-flex:has(> label:contains(/^\\D*${value}[.,]00\\D*$/)) input`,
        run: `edit ${quantity}`,
    };
}

function noteSelector(side, key) {
    return `.modal .nm-currency-exchange .nm-exchange-notes-${side} tr.nm-exchange-note[data-key='${key}']`;
}

/**
 * Notes of EUR tracked by denomination (50, 20, 10 and 5), no commission:
 * - opening counted by coins/notes: 1 x 50, 2 x 20, 1 x 10 (100 EUR);
 * - 50 EUR received: the grid of the notes received is required, 1 x 50;
 * - main currency -> 70 EUR (reverse quote): 1 x 50 and 1 x 20 proposed
 *   from the drawer, confirmed;
 * - Note Stock: 1 x 50, 1 x 20, 1 x 10;
 * - closing count: the quantities expected are shown by denomination.
 */
registry.category("web_tour.tours").add("PosCurrencyExchangeNoteStockTour", {
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
            {
                content: "count the EUR notes at opening by coins/notes",
                trigger: ".modal .nm-multicurrency-opening-section .btn:has([data-icon='payments'])",
                run: "click",
            },
            countNote(50, 1),
            countNote(20, 2),
            countNote(10, 1),
            {
                content: "confirm the count of the EUR notes",
                trigger: ".modal .nm-currency-money-details .modal-footer .btn-primary:contains('Confirm')",
                run: "click",
            },
            {
                content: "100 EUR counted",
                trigger: ".modal .nm-multicurrency-opening-section input.nm-currency-count:value(100)",
            },
            Dialog.confirm("Open Register"),
            ProductScreen.isShown(),
            stubPrinting(),

            Chrome.clickMenuOption("Currency Exchange"),
            {
                content: "type 50 EUR received",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-in",
                run: "edit 50",
            },
            {
                content: "the grid of the notes received lists the EUR notes with their stock",
                trigger: `${noteSelector("in", "20")} .nm-exchange-note-stock:contains(/^2$/)`,
            },
            {
                content: "no grid for the notes of the main currency, not tracked",
                trigger: ".modal .nm-currency-exchange:not(:has(.nm-exchange-notes-out))",
            },
            {
                content: "the notes received are not counted yet: Confirm disabled",
                trigger:
                    ".modal .nm-currency-exchange:has(.nm-exchange-notes-in .nm-exchange-notes-error) .nm-exchange-confirm[disabled]",
            },
            {
                content: "1 x 50 received",
                trigger: `${noteSelector("in", "50")} .nm-exchange-note-qty input`,
                run: "edit 1",
            },
            {
                content: "the notes received add up to 50",
                trigger: ".modal .nm-currency-exchange .nm-exchange-notes-in .nm-exchange-notes-total:contains(/50[.,]00/)",
            },
            {
                content: "confirm the operation",
                trigger:
                    ".modal .nm-currency-exchange:not(:has(.nm-exchange-notes-error)) .nm-exchange-confirm:not([disabled])",
                run: "click",
            },
            {
                content: "the operation is recorded and the popup closed",
                trigger: "body:not(:has(.modal .nm-currency-exchange))",
            },

            Chrome.clickMenuOption("Currency Exchange"),
            {
                content: "swap the currencies: main currency received, EUR handed back",
                trigger: ".modal .nm-currency-exchange .nm-exchange-swap",
                run: "click",
            },
            {
                content: "the customer wants 70 EUR",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-out",
                run: "edit 70",
            },
            {
                content: "leave the field",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-note",
                run: "click",
            },
            {
                content: "70 EUR handed back",
                trigger: ".modal .nm-currency-exchange input.nm-exchange-amount-out:value(/^70[.,]00$/)",
            },
            {
                content: "the stock of the 50 notes counts the one received: 2",
                trigger: `${noteSelector("out", "50")} .nm-exchange-note-stock:contains(/^2$/)`,
            },
            {
                content: "1 x 50 proposed",
                trigger: `${noteSelector("out", "50")} .nm-exchange-note-qty input:value(/^1$/)`,
            },
            {
                content: "1 x 20 proposed",
                trigger: `${noteSelector("out", "20")} .nm-exchange-note-qty input:value(/^1$/)`,
            },
            {
                content: "no 10 proposed",
                trigger: `${noteSelector("out", "10")} .nm-exchange-note-qty input:value(/^0$/)`,
            },
            {
                content: "the notes handed back add up to 70, no shortfall",
                trigger:
                    ".modal .nm-currency-exchange:not(:has(.nm-exchange-notes-shortfall)) .nm-exchange-notes-out .nm-exchange-notes-total:contains(/70[.,]00/)",
            },
            {
                content: "no grid for the notes of the main currency, not tracked",
                trigger: ".modal .nm-currency-exchange:not(:has(.nm-exchange-notes-in))",
            },
            {
                content: "confirm the operation",
                trigger:
                    ".modal .nm-currency-exchange:not(:has(.nm-exchange-notes-error)) .nm-exchange-confirm:not([disabled])",
                run: "click",
            },
            {
                content: "the operation is recorded and the popup closed",
                trigger: "body:not(:has(.modal .nm-currency-exchange))",
            },

            Chrome.clickMenuOption("Note Stock"),
            {
                content: "the EUR notes counted at opening",
                trigger: ".modal .nm-note-stock .nm-note-stock-currency:not(:has(.nm-note-stock-uncounted))",
            },
            {
                content: "50: 1 at opening, 1 received and 1 handed back, 1 in the drawer",
                trigger:
                    ".modal .nm-note-stock tr.nm-note-stock-row[data-key='50']:has(.nm-note-stock-opening:contains(/^1$/)) .nm-note-stock-quantity:contains(/^1$/)",
            },
            {
                content: "20: 2 at opening, 1 handed back, 1 in the drawer",
                trigger:
                    ".modal .nm-note-stock tr.nm-note-stock-row[data-key='20']:has(.nm-note-stock-moves:contains(/^-1$/)) .nm-note-stock-quantity:contains(/^1$/)",
            },
            {
                content: "10: 1 in the drawer",
                trigger: ".modal .nm-note-stock tr.nm-note-stock-row[data-key='10'] .nm-note-stock-quantity:contains(/^1$/)",
            },
            Dialog.cancel(),

            Chrome.clickMenuOption("Close Register"),
            {
                content: "count the EUR notes at closing by coins/notes",
                trigger: ".modal .close-pos-popup .nm-multicurrency-count button[data-icon='payments']",
                run: "click",
            },
            {
                content: "1 x 50 expected",
                trigger:
                    ".modal .nm-currency-money-details div.d-flex:has(> label:contains(/^\\D*50[.,]00\\D*$/)) .nm-expected-notes:contains(/expected 1$/)",
            },
            {
                content: "no 5 expected",
                trigger:
                    ".modal .nm-currency-money-details div.d-flex:has(> label:contains(/^\\D*5[.,]00\\D*$/)) .nm-expected-notes:contains(/expected 0$/)",
            },
            countNote(50, 1),
            countNote(20, 1),
            countNote(10, 1),
            {
                content: "confirm the count of the EUR notes",
                trigger: ".modal .nm-currency-money-details .modal-footer .btn-primary:contains('Confirm')",
                run: "click",
            },
            {
                content: "80 EUR counted",
                trigger: ".modal .close-pos-popup .nm-multicurrency-count input.nm-currency-count:value(80)",
            },
            {
                content: "close the register; the register redirects to the login page",
                trigger: ".modal:not(.o_inactive_modal) .modal-footer .btn-primary:contains('Close Register')",
                run: "click",
                expectUnloadPage: true,
            },
        ].flat(),
});

function transferNoteSelector(key) {
    return `.modal .nm-send-notes .nm-transfer-notes tr.nm-exchange-note[data-key='${key}']`;
}

/**
 * Notes of EUR tracked by denomination at both counters of the office;
 * opening of the main counter counted by coins/notes: 1 x 50, 2 x 20,
 * 1 x 10. Send Notes: 50 EUR to NM Counter 2 (register open there), 1 x 50
 * proposed from the drawer, sent as 2 x 20 and 1 x 10 instead; the response
 * of the first Confirm is lost, Confirm again records the transfer once and
 * prints its slip.
 */
registry.category("web_tour.tours").add("PosCurrencyExchangeTransferTour", {
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
            {
                content: "count the EUR notes at opening by coins/notes",
                trigger: ".modal .nm-multicurrency-opening-section .btn:has([data-icon='payments'])",
                run: "click",
            },
            countNote(50, 1),
            countNote(20, 2),
            countNote(10, 1),
            {
                content: "confirm the count of the EUR notes",
                trigger: ".modal .nm-currency-money-details .modal-footer .btn-primary:contains('Confirm')",
                run: "click",
            },
            {
                content: "100 EUR counted",
                trigger: ".modal .nm-multicurrency-opening-section input.nm-currency-count:value(100)",
            },
            Dialog.confirm("Open Register"),
            ProductScreen.isShown(),
            stubPrinting(),

            Chrome.clickMenuOption("Send Notes"),
            {
                content: "the other counter of the office is the destination, its register is open",
                trigger:
                    ".modal .nm-send-notes:not(:has(.nm-transfer-closed)) select.nm-transfer-counter:has(option:contains('NM Counter 2'))",
            },
            {
                content: "send EUR",
                trigger: ".modal .nm-send-notes select.nm-transfer-currency",
                run: function () {
                    const option = [...this.anchor.options].find((opt) => opt.textContent.trim() === "EUR");
                    this.anchor.value = option.value;
                    this.anchor.dispatchEvent(new Event("change"));
                },
            },
            {
                content: "type 50 EUR",
                trigger: ".modal .nm-send-notes input.nm-transfer-amount",
                run: "edit 50",
            },
            {
                content: "1 x 50 proposed from the drawer",
                trigger: `${transferNoteSelector("50")} .nm-exchange-note-qty input:value(/^1$/)`,
            },
            {
                content: "the stock of the 20 notes is shown",
                trigger: `${transferNoteSelector("20")} .nm-exchange-note-stock:contains(/^2$/)`,
            },
            {
                content: "the notes add up to 50: Confirm enabled",
                trigger:
                    ".modal .nm-send-notes:not(:has(.nm-transfer-notes-error)) .nm-transfer-confirm:not([disabled])",
            },
            {
                content: "keep the 50 note",
                trigger: `${transferNoteSelector("50")} .nm-exchange-note-qty input`,
                run: "edit 0",
            },
            {
                content: "the notes do not add up to the amount: Confirm disabled",
                trigger: ".modal .nm-send-notes:has(.nm-transfer-notes-error) .nm-transfer-confirm[disabled]",
            },
            {
                content: "2 x 20",
                trigger: `${transferNoteSelector("20")} .nm-exchange-note-qty input`,
                run: "edit 2",
            },
            {
                content: "1 x 10",
                trigger: `${transferNoteSelector("10")} .nm-exchange-note-qty input`,
                run: "edit 1",
            },
            {
                content: "the notes add up to 50",
                trigger: ".modal .nm-send-notes .nm-transfer-notes .nm-exchange-notes-total:contains(/50[.,]00/)",
            },
            {
                content: "type a note",
                trigger: ".modal .nm-send-notes input.nm-transfer-note",
                run: "edit Tour",
            },
            loseNextConfirmResponse("send_from_ui", ".modal .nm-send-notes"),
            {
                content: "confirm the transfer",
                trigger:
                    ".modal .nm-send-notes:not(:has(.nm-transfer-notes-error)) .nm-transfer-confirm:not([disabled])",
                run: "click",
            },
            {
                content: "the response is lost: the inputs are frozen",
                trigger:
                    ".modal .nm-send-notes:has(.nm-transfer-retry):has(select.nm-transfer-currency[disabled]):has(input.nm-transfer-amount[readonly]):has(fieldset.nm-transfer-notes[disabled]) input.nm-transfer-note[readonly]",
            },
            {
                content: "confirm again: the transfer already recorded is returned",
                trigger: ".modal .nm-send-notes .nm-transfer-confirm:not([disabled])",
                run: "click",
            },
            {
                content: "the transfer is recorded and the popup closed",
                trigger: "body:not(:has(.modal .nm-send-notes))",
            },
            {
                content: "the slip of the transfer was printed",
                trigger: "body.nm-tour-printed",
                run: () => {
                    const html = posmodel.nmTourReceiptHtml || "";
                    if (!["TRF/", "NM Counter 2", "50"].every((text) => html.includes(text))) {
                        throw new Error("Transfer slip not rendered: " + html.slice(0, 400));
                    }
                    document.body.classList.remove("nm-tour-printed");
                },
            },
            ProductScreen.isShown(),
        ].flat(),
});

/**
 * NM Counter 2, register open: Receive Notes lists the 50 EUR in transit
 * from the main counter; received, its slip is printed and the list is
 * empty.
 */
registry.category("web_tour.tours").add("PosCurrencyExchangeReceiveTour", {
    steps: () =>
        [
            ProductScreen.isShown(),
            stubPrinting(),
            Chrome.clickMenuOption("Receive Notes"),
            {
                content: "the notes in transit to the counter are listed",
                trigger:
                    ".modal .nm-receive-notes tr.nm-transfer-incoming:contains('TRF/'):has(.nm-transfer-incoming-amount:contains(/50[.,]00/)):has(.nm-transfer-incoming-note:contains('Tour'))",
            },
            {
                content: "receive them",
                trigger:
                    ".modal .nm-receive-notes tr.nm-transfer-incoming:has(.nm-transfer-incoming-note:contains('Tour')) .nm-transfer-receive:not([disabled])",
                run: "click",
            },
            {
                content: "the slip of the transfer was printed",
                trigger: "body.nm-tour-printed",
                run: () => {
                    const html = posmodel.nmTourReceiptHtml || "";
                    if (!["TRF/", "NM Counter 2", "50"].every((text) => html.includes(text))) {
                        throw new Error("Transfer slip not rendered: " + html.slice(0, 400));
                    }
                    document.body.classList.remove("nm-tour-printed");
                },
            },
            {
                content: "the notes the sending counter did not count are left",
                trigger:
                    ".modal .nm-receive-notes tr.nm-transfer-incoming:has(.nm-transfer-incoming-note:contains('Uncounted')) .nm-transfer-receive:not([disabled])",
                run: "click",
            },
            {
                content: "they are counted at receiving, prefilled with 20 + 5",
                trigger:
                    ".modal .nm-transfer-receive-notes:has(.nm-exchange-note[data-key='20'] input:value(1)):has(.nm-exchange-note[data-key='5'] input:value(1))",
            },
            {
                content: "a count that does not add up to the amount is refused",
                trigger: ".modal .nm-transfer-receive-notes .nm-exchange-note[data-key='5'] input",
                run: "edit 2",
            },
            {
                content: "the receipt cannot be confirmed",
                trigger: ".modal .nm-transfer-receive-notes:has(.nm-transfer-notes-error) .nm-transfer-receive-confirm[disabled]",
            },
            {
                content: "count 1 x 5 again",
                trigger: ".modal .nm-transfer-receive-notes .nm-exchange-note[data-key='5'] input",
                run: "edit 1",
            },
            {
                content: "confirm the receipt of the notes counted",
                trigger: ".modal .nm-transfer-receive-notes .nm-transfer-receive-confirm:not([disabled])",
                run: "click",
            },
            {
                content: "the slip of the second transfer was printed",
                trigger: "body.nm-tour-printed",
                run: () => document.body.classList.remove("nm-tour-printed"),
            },
            {
                content: "nothing left in transit",
                trigger: ".modal .nm-receive-notes .nm-transfer-empty",
            },
            Dialog.cancel(),
            ProductScreen.isShown(),
        ].flat(),
});
