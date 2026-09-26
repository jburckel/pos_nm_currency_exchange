"""Assembly of the store screenshots: raw captures -> static/description.

Two screenshots shown side by side on the store page must have the same aspect
ratio, otherwise the headings under them are not aligned. The raw captures
(modals, receipts, clips of a view) have all kinds of ratios: each one listed in
``LAYOUT`` with a ``ratio`` is trimmed of its white margins when asked, then placed
on a neutral background of the ratio of its row, with a thin border and a soft
shadow. A ``crop`` entry keeps only the top of a full-screen capture (a list view
leaves most of the screen empty). Files not listed are copied as they are.

Usage::

    python tools/screenshots/shots_assemble.py <raw captures dir>

The raw directory is the output of ``shots_capture.py``; never run it on
``static/description`` itself (the images would be framed twice).
"""
import pathlib
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "pos_nm_currency_exchange" / "static" / "description"
BACKGROUND = (238, 242, 247)
BORDER = (208, 215, 226)
MARGIN = 40

# file -> {"ratio": width/height of its row, "trim": white margins removed first}
#      or {"crop": height kept from the top of the capture}
LAYOUT = {
    # Exchange popup beside the commissions of a currency.
    "screenshot_exchange_popup.png": {"ratio": 1.45},
    "screenshot_exchange_commissions.png": {"ratio": 1.45},
    # Receipt beside the closing popup: white margins of the frame removed.
    "screenshot_exchange_receipt.png": {"ratio": 0.9, "trim": True},
    "screenshot_exchange_closing.png": {"ratio": 0.9},
    # Full-width views: the empty part of the screen is cut.
    "screenshot_exchange_list.png": {"crop": 450},
    "screenshot_exchange_pivot.png": {"crop": 400},
}


def trim_white(image):
    """Crop the white (or near white) margins of a capture (receipt frames)."""
    rgb = image.convert("RGB")
    diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, (255, 255, 255)))
    box = diff.convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
    if not box:
        return image
    pad = 24
    left, top, right, bottom = box
    return image.crop((max(0, left - pad), max(0, top - pad),
                       min(image.width, right + pad), min(image.height, bottom + pad)))


def frame(image, ratio):
    """Center ``image`` on a canvas of ``ratio`` with a margin, border and shadow."""
    image = image.convert("RGB")
    width, height = image.width + 2 * MARGIN, image.height + 2 * MARGIN
    if width / height < ratio:
        width = round(height * ratio)
    else:
        height = round(width / ratio)
    canvas = Image.new("RGB", (width, height), BACKGROUND)
    x, y = (width - image.width) // 2, (height - image.height) // 2
    shadow = Image.new("L", (width, height), 0)
    ImageDraw.Draw(shadow).rectangle((x + 2, y + 6, x + image.width + 2, y + image.height + 6), fill=70)
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    canvas.paste(Image.new("RGB", (width, height), (120, 130, 150)), (0, 0), shadow)
    canvas.paste(image, (x, y))
    ImageDraw.Draw(canvas).rectangle((x - 1, y - 1, x + image.width, y + image.height), outline=BORDER)
    return canvas


def main(raw_dir):
    raw_dir = pathlib.Path(raw_dir).resolve()
    if raw_dir == OUT.resolve():
        sys.exit("Give the directory of the raw captures, not static/description.")
    for path in sorted(raw_dir.glob("screenshot_*.png")):
        image = Image.open(path)
        spec = LAYOUT.get(path.name)
        if spec and spec.get("crop"):
            image = image.crop((0, 0, image.width, min(image.height, spec["crop"])))
        elif spec:
            if spec.get("trim"):
                image = trim_white(image)
            image = frame(image, spec["ratio"])
        image.save(OUT / path.name, optimize=True)
        print(path.name, image.size)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "tools" / "screenshots" / "shots")
