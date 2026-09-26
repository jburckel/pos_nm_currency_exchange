"""Banner and icon of pos_nm_currency_exchange, in the Natimai Solutions style of
pos_nm_multicurrencies (blue gradient, faded currency symbols, white text).

Rendered with headless Chrome from HTML, with Open Sans (close to the Segoe UI of the
parent banner). Usage::

    FONTS=<dir with OpenSans-400.ttf and OpenSans-700.ttf> \
    CHROME=/opt/pw-browsers/chromium-1194/chrome-linux/chrome \
    python tools/branding/build_branding.py
"""
import base64
import os
import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "pos_nm_currency_exchange" / "static" / "description"
FONTS = pathlib.Path(os.environ.get("FONTS", ROOT / "tools" / "branding" / "fonts")).resolve()
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")



def _font(weight):
    data = base64.b64encode((FONTS / f"OpenSans-{weight}.ttf").read_bytes()).decode()
    return f"@font-face {{ font-family: 'NM'; font-weight: {weight}; src: url(data:font/ttf;base64,{data}) format('truetype'); }}"


FONT_FACES = _font(400) + "\n" + _font(700)

# Two opposite arrows (swap), drawn as strokes: the arrow glyphs of the fonts differ.
ARROWS = """<svg viewBox="0 0 100 80" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor"
    stroke-width="9" stroke-linecap="round" stroke-linejoin="round">
    <path d="M8 24 H88 M68 6 L88 24 L68 42"/>
    <path d="M92 56 H12 M32 38 L12 56 L32 74"/>
</svg>"""

BANNER = f"""<!doctype html><html><head><meta charset="utf-8"><style>
{FONT_FACES}
html, body {{ margin: 0; }}
.banner {{
    position: relative; width: 1440px; height: 600px; overflow: hidden;
    background: linear-gradient(160deg, rgb(59, 92, 166) 0%, rgb(34, 137, 185) 55%, rgb(22, 159, 194) 100%);
    font-family: 'NM', sans-serif; color: #fff;
}}
.sym {{ position: absolute; font-weight: 700; color: rgba(255, 255, 255, 0.09); line-height: 1; }}
.content {{ position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }}
h1 {{ margin: 0; font-size: 92px; font-weight: 700; line-height: 1.18; letter-spacing: -0.5px; }}
p {{ margin: 34px 0 0; font-size: 38px; font-weight: 400; }}
</style></head><body><div class="banner">
<span class="sym" style="left: 160px; top: 4px; font-size: 170px;">&pound;</span>
<span class="sym" style="left: 30px; top: 400px; font-size: 230px;">&yen;</span>
<span class="sym" style="left: 1080px; top: 140px; font-size: 420px;">&euro;</span>
<span class="sym" style="left: 1335px; top: 380px; font-size: 220px;">$</span>
<span class="sym" style="left: 440px; top: 470px; width: 190px;">{ARROWS}</span>
<div class="content">
    <h1>POS Currency<br/>Exchange Counter</h1>
    <p>Buy and sell foreign notes at your Point of Sale</p>
</div>
</div></body></html>"""

ICON = f"""<!doctype html><html><head><meta charset="utf-8"><style>
{FONT_FACES}
html, body {{ margin: 0; }}
.icon {{
    position: relative; width: 512px; height: 512px; overflow: hidden; font-family: 'NM', sans-serif; color: #fff;
    background: linear-gradient(to top right, rgb(74, 107, 181) 49.2%, #fff 49.2%, #fff 50.8%, rgb(31, 185, 220) 50.8%);
}}
/* Inside the ring the two halves meet without the white line, as on the parent icon. */
.circle {{
    position: absolute; left: 106px; top: 76px; width: 300px; height: 300px; border: 12px solid #fff; border-radius: 50%;
    box-sizing: border-box;
    background: linear-gradient(to top right, rgb(74, 107, 181) 50%, rgb(31, 185, 220) 50%);
    background-size: 512px 512px; background-position: -106px -76px; background-origin: border-box;
}}
.sym {{ position: absolute; font-weight: 700; line-height: 1; }}
.label {{ position: absolute; left: 0; right: 0; top: 422px; text-align: center; font-weight: 700; font-size: 44px; letter-spacing: 0.5px; }}
</style></head><body><div class="icon">
<div class="circle"></div>
<span class="sym" style="left: 168px; top: 116px; font-size: 96px;">$</span>
<span class="sym" style="left: 290px; top: 116px; font-size: 96px;">&euro;</span>
<span class="sym" style="left: 196px; top: 248px; width: 120px;">{ARROWS}</span>
<div class="label">EXCHANGE</div>
</div></body></html>"""


def render(page, html, selector, path):
    page.set_content(html)
    page.evaluate("document.fonts.ready.then(() => document.fonts.size)")
    page.wait_for_timeout(300)
    page.locator(selector).screenshot(path=str(path))
    print("saved", path)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 600}, device_scale_factor=1)
    render(page, BANNER, ".banner", OUT / "banner.png")
    render(page, ICON, ".icon", OUT / "icon.png")
    browser.close()
