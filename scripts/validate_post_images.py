#!/usr/bin/env python3
"""Validate locally hosted images in a Jekyll post and optionally its deployed HTML."""
import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
import requests

RAW_PREFIX = "https://raw.githubusercontent.com/"
IMAGE = re.compile(r"!\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)")
HTML_IMAGE = re.compile(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\']', re.I)

def check_source(post):
    content = post.read_text(encoding="utf-8")
    urls = IMAGE.findall(content)
    if not urls:
        raise ValueError("No Markdown images found")
    paths = []
    for url in urls:
        if "{{" in url or "{%" in url:
            raise ValueError("Liquid in image URL breaks GitHub Markdown preview: " + url)
        if url.startswith(RAW_PREFIX):
            parsed = urlparse(url)
            pieces = parsed.path.lstrip("/").split("/", 3)
            if len(pieces) != 4 or pieces[2] != "main":
                raise ValueError("Unexpected GitHub raw URL: " + url)
            path = Path(pieces[3])
        elif url.startswith("/"):
            path = Path(url.lstrip("/"))
        else:
            path = post.parent / url
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError("Missing/empty image: " + str(path))
        if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"):
            raise ValueError("Unexpected image extension: " + str(path))
        paths.append(path)
    print(f"PASS: {len(urls)} Markdown images, all local assets exist and GitHub preview-compatible")
    return urls

def check_live(page_url, expected_count, attempts):
    session = requests.Session()
    last_error = ""
    for attempt in range(attempts):
        try:
            page = session.get(page_url, timeout=25)
            page.raise_for_status()
            srcs = HTML_IMAGE.findall(page.text)
            if len(srcs) < expected_count:
                raise ValueError(f"Rendered HTML contains {len(srcs)} img tags; expected >= {expected_count}")
            matched = [s for s in srcs if "/assets/images/posts/" in s]
            if len(matched) < expected_count:
                raise ValueError(f"Only {len(matched)} post images rendered; expected {expected_count}")
            for src in matched[:expected_count]:
                absolute = requests.compat.urljoin(page_url, src)
                image = session.get(absolute, timeout=25)
                image.raise_for_status()
                if not image.headers.get("Content-Type", "").lower().startswith("image/"):
                    raise ValueError("Not an image response: " + absolute)
                if not image.content:
                    raise ValueError("Empty deployed image: " + absolute)
            print(f"PASS: deployed HTML and {expected_count} image URLs render successfully: {page_url}")
            return
        except (requests.RequestException, ValueError) as exc:
            last_error = str(exc)
            if attempt + 1 < attempts:
                time.sleep(20)
    raise RuntimeError("Deployed render check failed: " + last_error)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--post", required=True, type=Path)
    parser.add_argument("--live-url", default="")
    parser.add_argument("--attempts", type=int, default=1)
    args = parser.parse_args()
    try:
        images = check_source(args.post)
        if args.live_url:
            check_live(args.live_url, len(images), args.attempts)
    except Exception as exc:
        print("FAIL:", exc, file=sys.stderr)
        sys.exit(1)
