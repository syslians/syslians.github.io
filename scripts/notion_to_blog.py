#!/usr/bin/env python3
"""Export a Notion page to a new Jekyll post, including local image assets."""
import argparse
import datetime
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse
import requests

API = "https://api.notion.com/v1"
S = requests.Session()
EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif", "image/svg+xml": ".svg"}
TICK = chr(96)

def api(path):
    for attempt in range(5):
        r = S.get(API + path, timeout=40)
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 4:
            time.sleep(min(int(r.headers.get("Retry-After", "2")), 15) + attempt)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Notion request failed")

def blocks(identifier):
    cursor = None
    while True:
        path = "/blocks/" + identifier + "/children?page_size=100"
        if cursor:
            path += "&start_cursor=" + cursor
        data = api(path)
        yield from data["results"]
        if not data["has_more"]:
            break
        cursor = data["next_cursor"]

def plain(items):
    return "".join(i.get("plain_text", "") for i in items or [])

def rich(items):
    result = []
    for item in items or []:
        s = item.get("plain_text", "").replace("|", "\\|")
        a = item.get("annotations", {})
        if a.get("code"):
            s = TICK + s + TICK
        if a.get("bold"):
            s = "**" + s + "**"
        if a.get("italic"):
            s = "*" + s + "*"
        if a.get("strikethrough"):
            s = "~~" + s + "~~"
        if (item.get("href") or "").startswith(("https://", "http://")):
            s = "[" + s + "](" + item["href"] + ")"
        result.append(s)
    return "".join(result)

def render(items, image_dir, image_url, count):
    output = []
    for b in items:
        kind = b["type"]
        data = b.get(kind, {})
        text = rich(data.get("rich_text", []))
        if kind == "paragraph":
            output.append(text)
        elif kind.startswith("heading_"):
            output.append("#" * int(kind[-1]) + " " + text)
        elif kind in ("bulleted_list_item", "numbered_list_item", "to_do"):
            prefix = "1. " if kind == "numbered_list_item" else "- "
            if kind == "to_do":
                prefix = "- [x] " if data.get("checked") else "- [ ] "
            output.append(prefix + text)
        elif kind == "quote":
            output.append("> " + text)
        elif kind == "code":
            code = plain(data.get("rich_text", []))
            fence = TICK * (max([len(x) for x in re.findall(TICK + "+", code)] or [2]) + 1)
            output.append(fence + data.get("language", "text") + "\n" + code + "\n" + fence)
        elif kind == "image":
            count[0] += 1
            source = data.get(data["type"], {})
            url = source.get("url", "")
            if not url.startswith("https://"):
                raise ValueError("Missing HTTPS image URL: " + b["id"])
            response = requests.get(url, timeout=90, stream=True)
            response.raise_for_status()
            mime = response.headers.get("Content-Type", "").split(";")[0].lower()
            if mime not in EXT:
                raise ValueError("Unsupported image MIME: " + mime)
            name = f"{count[0]:02d}-{b['id'][:8]}" + EXT[mime]
            total = 0
            with (image_dir / name).open("wb") as handle:
                for chunk in response.iter_content(65536):
                    total += len(chunk)
                    if total > 20 * 1024 * 1024:
                        raise ValueError("Image exceeds 20 MB")
                    handle.write(chunk)
            if not total:
                raise ValueError("Empty image: " + name)
            caption = plain(data.get("caption", [])) or f"Notion 이미지 {count[0]}"
            output.append("![" + caption.replace("]", "\\]") + "]({{ '" + image_url + "/" + name + "' | relative_url }})")
        elif kind == "table":
            rows = [x["table_row"]["cells"] for x in blocks(b["id"]) if x["type"] == "table_row"]
            if rows:
                width = max(map(len, rows))
                cells = [[rich(c).replace("\n", " ") for c in row] for row in rows]
                cells = [row + [""] * (width - len(row)) for row in cells]
                output.append("| " + " | ".join(cells[0]) + " |")
                output.append("| " + " | ".join(["---"] * width) + " |")
                output.extend("| " + " | ".join(row) + " |" for row in cells[1:])
        elif kind == "divider":
            output.append("---")
        elif kind in ("bookmark", "embed", "link_preview"):
            url = data.get("url", "")
            if url.startswith(("https://", "http://")):
                output.append("[참고 링크](" + url + ")")
        elif kind not in ("column_list", "column", "toggle", "synced_block"):
            print("Unsupported block type:", kind, b["id"])
        if b.get("has_children") and kind not in ("table", "child_page", "child_database"):
            nested = render(blocks(b["id"]), image_dir, image_url, count)
            if nested:
                output.append(nested)
    return "\n\n".join(x for x in output if x)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--date", default="")
    p.add_argument("--slug", default="")
    args = p.parse_args()
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        p.error("NOTION_TOKEN secret is required")
    S.headers.update({"Authorization": "Bearer " + token, "Notion-Version": "2022-06-28"})
    match = re.search(r"([a-f0-9]{32})(?:[^a-f0-9]|$)", args.url.replace("-", ""), re.I)
    if not match:
        p.error("Invalid Notion URL or page ID")
    raw = match.group(1)
    identifier = "-".join((raw[:8], raw[8:12], raw[12:16], raw[16:20], raw[20:]))
    page = api("/pages/" + identifier)
    title = next((plain(v.get("title", [])) for v in page["properties"].values() if v["type"] == "title"), "Notion post")
    date = args.date or page["created_time"][:10]
    datetime.date.fromisoformat(date)
    slug = args.slug or re.sub(r"[^a-z0-9가-힣]+", "-", title.lower()).strip("-")[:65]
    if not re.fullmatch(r"[a-z0-9가-힣-]+", slug):
        p.error("Invalid slug")
    stem = date + "-" + slug
    post = Path("_posts") / (stem + ".md")
    directory = Path("assets/images/posts") / stem
    if post.exists() or directory.exists():
        p.error("Refusing to overwrite existing post or image directory: " + stem)
    directory.mkdir(parents=True)
    count = [0]
    body = render(blocks(identifier), directory, "/" + directory.as_posix(), count)
    if not body.strip():
        raise ValueError("Notion page has no supported content")
    categories = []
    for prop in page["properties"].values():
        if prop["type"] == "multi_select":
            categories.extend(x["name"] for x in prop.get("multi_select", []))
    front = ["---", "layout: post", "title: " + json.dumps(title, ensure_ascii=False),
             "date: " + date, "categories: " + json.dumps(categories, ensure_ascii=False),
             "notion_source: " + json.dumps(page.get("url", args.url)), "---", ""]
    post.parent.mkdir(exist_ok=True)
    post.write_text("\n".join(front) + body + "\n\n원본: [Notion](" + page.get("url", args.url) + ")\n", encoding="utf-8")
    print(json.dumps({"post": str(post), "images": count[0]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
