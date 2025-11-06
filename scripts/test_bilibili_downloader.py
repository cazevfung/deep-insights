import sys
from pathlib import Path

from scrapers.bilibili_downloader import download_bilibili_480p, mp4_to_mp3
from core.config import Config


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.test_bilibili_downloader <BV_URL> [out_dir]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    # Basic validation to avoid placeholder mistakes
    if "<BV_ID>" in url or "BV_ID" in url or "<" in url or ">" in url:
        print("Error: Replace <BV_ID> with a real Bilibili BV ID, e.g. https://www.bilibili.com/video/BV1xx411c7mD", file=sys.stderr)
        sys.exit(1)
    if "BV" not in url:
        print("Error: Provide a BV URL or a b23.tv short link that resolves to a BV page.", file=sys.stderr)
        sys.exit(1)
    cfg = Config()
    out_dir = Path(sys.argv[2]) if len(sys.argv) >= 3 else Path(cfg.get("scrapers.bilibili.download_dir", "downloads"))

    print(f"Downloading: {url}")
    result = download_bilibili_480p(url, out_dir)
    mp4_path = Path(result["merged_mp4"]) if isinstance(result["merged_mp4"], str) else result["merged_mp4"]
    print(f"Saved MP4: {mp4_path}")

    # MP3 conversion
    mp3_path = mp4_path.with_suffix(".mp3")
    ok = mp4_to_mp3(mp4_path, mp3_path)
    if ok:
        print(f"Saved MP3: {mp3_path}")
    else:
        print("MP3 conversion failed (see stderr for details)")


if __name__ == "__main__":
    main()


