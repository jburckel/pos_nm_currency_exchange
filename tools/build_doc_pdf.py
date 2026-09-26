# -*- coding: utf-8 -*-
"""Build the documentation PDFs shipped with the module.

Renders ``doc/index.rst`` (English) and its translations ``doc/index_<lang>.rst``
to ``static/description/documentation_<lang>.pdf``, which is the only directory
whose links stay clickable on the Odoo Store product page.

Chain: docutils (RST -> standalone HTML with an embedded stylesheet), then
headless Chrome (HTML -> PDF). Chrome is already required to run the POS tours,
so the only extra dependency is docutils::

    pip install docutils
    python tools/build_doc_pdf.py            # all languages
    python tools/build_doc_pdf.py fr de      # only these ones

Chrome is looked up in the usual places (see ``CHROME_CANDIDATES``); point the
``CHROME`` environment variable at the binary when it lives elsewhere, for
instance the Chromium that Playwright installs on a build machine::

    CHROME=/opt/pw-browsers/chromium-1194/chrome-linux/chrome python tools/build_doc_pdf.py

The build fails on any docutils warning: a title underline shorter than its
title (the usual trap when translating) must never reach a customer as a
silently broken document.
"""
import ast
import base64
import io
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from docutils.core import publish_string

ROOT = Path(__file__).resolve().parent.parent
ADDON = ROOT / "pos_nm_currency_exchange"
DOC_DIR = ADDON / "doc"
OUT_DIR = ADDON / "static" / "description"
CSS = Path(__file__).resolve().parent / "doc_pdf.css"
LOGO = OUT_DIR / "Logo-SQ.png"

LANGUAGES = {
    "en": ("English", "index.rst"),
    "fr": ("Francais", "index_fr.rst"),
    "de": ("Deutsch", "index_de.rst"),
    "es": ("Espanol", "index_es.rst"),
}

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
]


def find_chrome():
    """Locate a Chrome/Chromium binary. CHROME=<path> wins over the guesses."""
    override = os.environ.get("CHROME")
    if override:
        if not Path(override).exists():
            raise SystemExit("CHROME points at %s, which does not exist." % override)
        return override
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    raise SystemExit(
        "Chrome not found. Set CHROME=<path to chrome> or edit "
        "CHROME_CANDIDATES in this script.")


def module_version():
    manifest = ast.literal_eval((ADDON / "__manifest__.py").read_text(encoding="utf-8"))
    return manifest["version"], manifest["name"]


def render_html(source_path, lang, language_label, version, module_name):
    """RST -> standalone HTML. Raises on any docutils warning."""
    warnings = io.StringIO()
    html = publish_string(
        source=source_path.read_text(encoding="utf-8"),
        writer_name="html5",
        settings_overrides={
            "stylesheet_path": str(CSS),
            "embed_stylesheet": True,
            "input_encoding": "utf-8",
            "output_encoding": "utf-8",
            "report_level": 2,      # info -> silence, warning -> collected
            "halt_level": 4,        # let us collect warnings instead of raising
            "warning_stream": warnings,
            "doctitle_xform": True,
            "syntax_highlight": "none",
            # Localises the labels docutils generates itself (the title of a
            # .. warning:: block) and the quotation marks of that language.
            "language_code": lang,
            # ASCII sources (the store serves doc/index.rst undecoded), but the
            # PDF deserves real dashes and curly quotes.
            "smart_quotes": True,
        },
    ).decode("utf-8")

    complaints = [line for line in warnings.getvalue().splitlines() if line.strip()]
    if complaints:
        raise SystemExit(
            f"docutils rejected {source_path.name}:\n  " + "\n  ".join(complaints))

    # docutils renders a .. warning:: as "Avis" in French, which reads as a
    # mere notice: ours are about falsified accounting history.
    stronger_title = {"fr": "Avertissement", "es": "Advertencia",
                      "de": "Warnung"}.get(lang)
    if stronger_title:
        html = re.sub(r'(<p class="admonition-title">)[^<]*(</p>)',
                      r"\1" + stronger_title + r"\2", html)

    # Cover metadata right under the title banner.
    meta = (f'<p class="doc-meta"><span>{module_name}</span>'
            f'<span>Version {version}</span><span>{language_label}</span></p>')
    html = re.sub(r"(</h1>)", r"\1" + meta, html, count=1)

    # Company logo on the right of the cover banner, embedded as a data URI:
    # Chrome renders the HTML from a temporary directory, so a file path
    # would not survive the trip.
    if not LOGO.exists():
        raise SystemExit(f"Logo not found: {LOGO}")
    logo_uri = "data:image/png;base64," + base64.b64encode(LOGO.read_bytes()).decode("ascii")
    html = html.replace(
        '<h1 class="title">',
        f'<h1 class="title"><img class="doc-logo" src="{logo_uri}" alt="Natimai Solutions">',
        1,
    )
    return html


def html_to_pdf(chrome, html, pdf_path):
    # Remove the previous PDF first: Chrome fails silently when the target is
    # locked (a PDF viewer holding it open), and checking existence only would
    # then validate a stale document as a fresh build.
    if pdf_path.exists():
        try:
            pdf_path.unlink()
        except OSError as error:
            raise SystemExit(f"Cannot replace {pdf_path.name} ({error}) - "
                             f"close the file if it is open in a viewer.")

    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "doc.html"
        html_path.write_text(html, encoding="utf-8")
        profile = Path(tmp) / "profile"
        result = subprocess.run(
            [
                chrome,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--no-pdf-header-footer",
                f"--user-data-dir={profile}",       # never touch the real profile
                "--virtual-time-budget=5000",       # let the layout settle
                f"--print-to-pdf={pdf_path}",
                html_path.as_uri(),
            ],
            capture_output=True, text=True,
        )
        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            raise SystemExit(f"Chrome produced no PDF for {pdf_path.name}:\n"
                             f"{result.stdout}\n{result.stderr}")


def page_count(pdf_path):
    data = pdf_path.read_bytes()
    return len(re.findall(rb"/Type\s*/Page[^s]", data)) or None


def main():
    wanted = sys.argv[1:] or list(LANGUAGES)
    unknown = [lang for lang in wanted if lang not in LANGUAGES]
    if unknown:
        raise SystemExit(f"Unknown language(s): {', '.join(unknown)}")

    chrome = find_chrome()
    version, module_name = module_version()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for lang in wanted:
        label, filename = LANGUAGES[lang]
        source = DOC_DIR / filename
        if not source.exists():
            print(f"{lang}: {filename} missing - skipped")
            continue
        pdf_path = OUT_DIR / f"documentation_{lang}.pdf"
        html_to_pdf(chrome, render_html(source, lang, label, version, module_name), pdf_path)
        size_kb = pdf_path.stat().st_size / 1024
        pages = page_count(pdf_path)
        print(f"{lang}: {pdf_path.relative_to(ROOT)} "
              f"({size_kb:.0f} kB{', ' + str(pages) + ' pages' if pages else ''})")


if __name__ == "__main__":
    main()
