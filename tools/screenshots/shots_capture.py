"""Screenshots of pos_nm_currency_exchange on the ``shots`` database.

Usage: venv/bin/python shots_capture.py <config_id> <session_id> <eur_setting_id>
"""
import os
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8069"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
os.makedirs(OUT, exist_ok=True)
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

config_id = int(sys.argv[1])
session_id = int(sys.argv[2])
eur_setting_id = int(sys.argv[3])


def shot(page, name, locator=None, full_page=False, clip=None):
    path = os.path.join(OUT, f"screenshot_{name}.png")
    if locator is not None:
        locator.screenshot(path=path)
    else:
        page.screenshot(path=path, full_page=full_page, clip=clip)
    print("saved", path)


def open_menu_option(page, label):
    page.locator(".pos-rightheader button:has([data-icon='menu'])").click()
    page.wait_for_selector(".o_pos_burger_menu_buttons > button.btn", timeout=10000)
    page.locator(".o_pos_burger_menu_buttons > button.btn", has_text=label).first.click()


def block_rect(page, heading):
    page.evaluate("""(heading) => {
        const h2 = [...document.querySelectorAll('h2')].find(h => h.textContent.includes(heading));
        h2.scrollIntoView({block: 'start'});
    }""", heading)
    time.sleep(0.8)
    return page.evaluate("""(heading) => {
        const h2 = [...document.querySelectorAll('h2')].find(h => h.textContent.includes(heading));
        const container = h2.nextElementSibling;
        const a = h2.getBoundingClientRect(), b = container.getBoundingClientRect();
        return {x: Math.min(a.left, b.left), y: a.top, width: Math.max(a.right, b.right) - Math.min(a.left, b.left), height: Math.min(b.bottom, window.innerHeight) - a.top};
    }""", heading)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    page = context.new_page()
    page.goto(BASE + "/web/login")
    page.fill("input[name='login']", "admin")
    page.fill("input[name='password']", "admin")
    page.click("button[type='submit']")
    page.wait_for_selector(".o_action_manager, .o_home_menu, .o_web_client", timeout=30000)
    time.sleep(1)

    # ---------------- Back-office
    page.goto(BASE + "/odoo/action-point_of_sale.action_pos_configuration")
    page.wait_for_selector(".o_action_manager", timeout=30000)
    time.sleep(3)
    try:
        rect = block_rect(page, "Currency Exchange")
        shot(page, "exchange_settings", clip=rect)
    except Exception as e:
        print("settings block not found:", e)
    # Commission fields on the cash currency setting form
    page.goto(BASE + f"/odoo/action-pos_nm_multicurrencies.action_pos_nm_currency_setting/{eur_setting_id}")
    page.wait_for_selector(".o_form_view", timeout=30000)
    time.sleep(2.5)
    shot(page, "exchange_commissions", locator=page.locator(".o_form_view .o_form_sheet").first)
    # Exchange operations list and pivot
    page.goto(BASE + "/odoo/action-pos_nm_currency_exchange.action_pos_nm_exchange")
    page.wait_for_selector(".o_list_view", timeout=30000)
    time.sleep(2.5)
    shot(page, "exchange_list")
    page.goto(BASE + "/odoo/action-pos_nm_currency_exchange.action_pos_nm_exchange?view_type=pivot")
    page.wait_for_selector(".o_pivot_view", timeout=30000)
    time.sleep(2.5)
    shot(page, "exchange_pivot")
    # Session form with the stat button
    page.goto(BASE + f"/odoo/action-point_of_sale.action_pos_session/{session_id}")
    page.wait_for_selector(".o_form_view", timeout=30000)
    time.sleep(3)
    shot(page, "exchange_session")
    # Sales details report: the exchange block
    page.goto(BASE + f"/report/html/point_of_sale.report_saledetails/{session_id}")
    page.wait_for_selector("body", timeout=30000)
    time.sleep(3)
    block = page.locator("#nm_exchange")
    if block.count():
        shot(page, "exchange_sale_details", locator=block.first)
    else:
        shot(page, "exchange_sale_details", full_page=True)

    # ---------------- Point of sale
    page.goto(BASE + f"/pos/ui/{config_id}?from_backend=True")
    page.wait_for_selector("input[placeholder*='Search']", timeout=60000)
    time.sleep(2.5)
    # Keep the printed receipt in the page instead of the print dialog.
    page.evaluate("""() => {
        posmodel.ticketPrinter.printWithFallback = async ({iframe}) => { window.__nmReceiptIframe = iframe; return true; };
    }""")
    open_menu_option(page, "Currency Exchange")
    page.wait_for_selector(".modal .nm-currency-exchange", timeout=15000)
    time.sleep(1)
    page.locator(".modal .nm-exchange-currency-in").select_option(label="USD")
    time.sleep(0.5)
    page.locator(".modal .nm-exchange-currency-out").select_option(label="EUR")
    time.sleep(0.5)
    amount = page.locator(".modal .nm-exchange-amount-in")
    amount.fill("100")
    time.sleep(1.5)
    page.locator(".modal .nm-exchange-note").fill("Hotel guest")
    page.wait_for_selector(".modal .nm-exchange-rate", timeout=10000)
    time.sleep(1)
    shot(page, "exchange_popup", locator=page.locator(".modal-content:has(.nm-currency-exchange), .modal .nm-currency-exchange").first)
    page.locator(".modal .nm-exchange-confirm").click()
    page.wait_for_selector("body:not(:has(.modal .nm-currency-exchange))", timeout=20000)
    time.sleep(2)
    # Show the receipt iframe
    page.evaluate("""() => {
        const container = document.getElementById("receipt-iframe-container");
        container.setAttribute("style", "display:block !important;position:fixed;top:0;left:0;width:620px;height:900px;background:white;z-index:99999;visibility:visible;opacity:1;");
        container.classList.remove("d-none");
        const iframe = container.querySelector("iframe");
        iframe.style.width = "620px";
        iframe.style.height = "900px";
    }""")
    time.sleep(1.5)
    page.evaluate("""() => {
        const iframe = document.querySelector("#receipt-iframe-container iframe");
        const doc = iframe.contentDocument;
        const receipt = doc.querySelector(".pos-receipt");
        if (receipt) { receipt.style.margin = "0 auto"; receipt.style.padding = "16px"; }
        const h = Math.min(doc.documentElement.scrollHeight + 8, 1400);
        iframe.style.height = h + "px"; iframe.parentElement.style.height = h + "px";
        const w = Math.min(Math.max(doc.documentElement.scrollWidth + 8, 420), 620);
        iframe.style.width = w + "px"; iframe.parentElement.style.width = w + "px";
    }""")
    time.sleep(1)
    shot(page, "exchange_receipt", locator=page.locator("#receipt-iframe-container iframe"))
    page.evaluate("document.getElementById('receipt-iframe-container').setAttribute('style', 'display:none')")
    time.sleep(0.5)
    # Closing popup with the exchange block
    open_menu_option(page, "Close Register")
    page.wait_for_selector(".close-pos-popup .nm-exchange-closing", timeout=20000)
    time.sleep(2)
    shot(page, "exchange_closing", locator=page.locator(".modal-content:has(.close-pos-popup), .close-pos-popup").first)
    page.locator(".modal-footer button", has_text="Discard").first.click()
    time.sleep(1)
    browser.close()
