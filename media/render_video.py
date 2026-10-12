"""Render media/video.html to MP4 (LinkedIn) and GIF (README).

    python media/render_video.py              # full render
    python media/render_video.py --stills     # a few still frames for review

Needs: playwright (with Chromium) and ffmpeg on PATH.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
FPS = 24


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", action="store_true")
    args = ap.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1080}, device_scale_factor=1)
        page.goto((HERE / "video.html").as_uri())
        page.wait_for_function("document.fonts.ready.then(() => true)")
        duration = page.evaluate("window.DURATION")
        if args.stills:
            for t in [3.5, 9.5, 19.0, 25.5, 32.5, 39.0]:
                page.evaluate(f"render({t})")
                page.screenshot(path=str(HERE / f"still_{t:04.1f}.png"))
            print("stills written")
            return
        tmp = Path(tempfile.mkdtemp(prefix="frames_"))
        n = int(duration * FPS)
        for i in range(n):
            page.evaluate(f"render({i / FPS})")
            page.screenshot(path=str(tmp / f"f{i:05d}.png"))
        browser.close()
    mp4 = HERE / "semantic_layer_results.mp4"
    gif = HERE / "semantic_layer_results.gif"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
                    "-movflags", "+faststart", str(mp4)], check=True)
    pal = tmp / "palette.png"
    vf = "fps=12,scale=600:-1:flags=lanczos"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%05d.png"),
                    "-vf", f"{vf},palettegen=stats_mode=diff", str(pal)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%05d.png"),
                    "-i", str(pal), "-lavfi", f"{vf}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5",
                    str(gif)], check=True)
    shutil.rmtree(tmp)
    print(f"Wrote {mp4.name} and {gif.name}")


if __name__ == "__main__":
    main()
