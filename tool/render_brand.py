"""Render brand/*.svg into the PNGs Home Assistant shows (custom_components/garagebutler/brand/).

Uses headless Chrome (path in $CHROME, else the default install locations):
    python tool/render_brand.py
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "brand"
OUT = ROOT / "custom_components" / "garagebutler" / "brand"

# Home Assistant brand images: icon 256x256 (@2x 512), logo shortest side 128–256 (@2x 256–512).
IMAGES = {
    "icon": [("icon.png", 256, 256), ("icon@2x.png", 512, 512)],
    "dark_icon": [("dark_icon.png", 256, 256), ("dark_icon@2x.png", 512, 512)],
    "logo": [("logo.png", 732, 164), ("logo@2x.png", 1464, 328)],
    "dark_logo": [("dark_logo.png", 732, 164), ("dark_logo@2x.png", 1464, 328)],
}

CHROME_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome",
    "chromium",
)


def chrome() -> str:
    for candidate in (os.environ.get("CHROME"), *CHROME_PATHS):
        if candidate and (Path(candidate).exists() or shutil.which(candidate)):
            return candidate
    raise SystemExit("Chrome not found – set $CHROME")


def render(svg: str, target: Path, width: int, height: int, tmp: Path) -> None:
    sized = re.sub(r'width="\d+" height="\d+"', f'width="{width}" height="{height}"', svg, count=1)
    source = tmp / f"{target.stem}.svg"
    source.write_text(sized, encoding="utf-8")
    subprocess.run(
        [
            chrome(),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            f"--window-size={width},{height}",
            f"--screenshot={target}",
            source.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    print(f"{target.relative_to(ROOT)}  {width}x{height}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, sizes in IMAGES.items():
            svg = (SRC / f"{name}.svg").read_text(encoding="utf-8")
            for filename, width, height in sizes:
                render(svg, OUT / filename, width, height, Path(tmp))


if __name__ == "__main__":
    main()
