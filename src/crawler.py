"""
Crawler batdongsan.com — quận Bình Thạnh (chạy THỦ CÔNG 1 lần, không cron).

Cài 1 lần:
    pip install playwright
    playwright install chromium

Chạy:
    python src/crawler.py --pages 20 --out data/crawl_raw.json

Output: JSON list các tin thô (tiêu đề, giá, diện tích, địa chỉ, url).
Sau đó parse + nạp DB:  python src/import_data.py data/crawl_raw.json

LƯU Ý:
- batdongsan render bằng JS nên dùng Playwright (không dùng requests/Scrapy).
- Delay ngẫu nhiên 3–7s, rotate user-agent để tránh bị chặn. Nếu bị chặn IP -> đổi mạng/VPN.
- Selector của trang có thể đổi theo thời gian; chỉnh trong CONFIG bên dưới khi cần.
- Tôn trọng robots.txt và điều khoản dịch vụ; chỉ crawl lượng nhỏ cho mục đích nội bộ.
"""

import argparse
import json
import random
import time

# URL danh sách bán nhà Bình Thạnh (phân trang bằng /p{n})
BASE_URL = "https://batdongsan.com.vn/ban-nha-rieng-binh-thanh"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
]

# Selector — chỉnh ở đây nếu trang đổi cấu trúc.
CONFIG = {
    "card": ".js__card, .re__card-full",          # mỗi tin
    "title": ".js__card-title, .re__card-title",
    "price": ".re__card-config-price",
    "area": ".re__card-config-area",
    "address": ".re__card-location",
    "link": "a",
}


def crawl(pages: int, headless: bool = True, delay=(3, 7)):
    from playwright.sync_api import sync_playwright

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        for page_no in range(1, pages + 1):
            url = BASE_URL if page_no == 1 else f"{BASE_URL}/p{page_no}"
            ctx = browser.new_context(user_agent=random.choice(USER_AGENTS))
            page = ctx.new_page()
            print(f"[{page_no}/{pages}] {url}")
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                page.wait_for_selector(CONFIG["card"], timeout=15000)
                cards = page.query_selector_all(CONFIG["card"])
                print(f"   tìm thấy {len(cards)} tin")
                for c in cards:
                    results.append(_extract(c))
            except Exception as e:
                print(f"   ! lỗi trang {page_no}: {e}")
            finally:
                ctx.close()
            time.sleep(random.uniform(*delay))  # delay tránh bị chặn
        browser.close()
    return [r for r in results if r.get("title")]


def _text(card, selector):
    el = card.query_selector(selector)
    return el.inner_text().strip() if el else None


def _extract(card):
    link_el = card.query_selector(CONFIG["link"])
    href = link_el.get_attribute("href") if link_el else None
    if href and href.startswith("/"):
        href = "https://batdongsan.com.vn" + href
    title = _text(card, CONFIG["title"])
    # Gộp giá + diện tích vào title để parser xử lý chung (giá/DT trong tiêu đề thường thiếu)
    extra = " ".join(filter(None, [_text(card, CONFIG["price"]), _text(card, CONFIG["area"])]))
    return {
        "title": title,
        "raw_extra": extra,
        "dia_chi": _text(card, CONFIG["address"]),
        "url": href,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=20, help="Số trang cần crawl (mỗi trang ~20 tin)")
    ap.add_argument("--out", default="data/crawl_raw.json")
    ap.add_argument("--show", action="store_true", help="Hiện trình duyệt (debug)")
    args = ap.parse_args()

    rows = crawl(args.pages, headless=not args.show)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\nĐã lưu {len(rows)} tin -> {args.out}")
    print(f"Bước tiếp: python src/import_data.py {args.out}")


if __name__ == "__main__":
    main()
