from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# 定数設定
BASE_URL = "https://www.daiichisankyo.co.jp"
DEFAULT_LINK = "https://www.daiichisankyo.co.jp/media/press_release/"

# RSSフィード生成関数
def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title("第一三共")
    fg.link(href=DEFAULT_LINK)
    fg.description("第一三共プレスリリースの更新履歴")
    fg.language("ja")
    fg.generator("python-feedgen")
    fg.docs("http://www.rssboard.org/rss-specification")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])
        guid_value = f"{item['link']}#{item['pub_date'].strftime('%Y%m%d')}"
        entry.guid(guid_value, permalink=False)
        entry.pubDate(item['pub_date'])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")

# 情報抽出関数
def extract_items(page):
    try:
        page.goto(DEFAULT_LINK, timeout=30000)
        page.wait_for_selector("ul.newslist > li", timeout=10000)
    except PlaywrightTimeoutError:
        print("⚠️ ページの読み込みまたは要素の検出に失敗しました")
        return []

    rows = page.locator("ul.newslist > li")
    count = rows.count()
    print(f"📦 発見した更新情報行数: {count}")
    items = []

    max_items = 10  # 必要に応じて変更（デバッグ中は1でもOK）

    for i in range(min(count, max_items)):
        row = rows.nth(i)
        try:
            # 日付取得とパース
            date_text = row.locator("div.newsDate").inner_text(timeout=5000).strip()
            pub_date = datetime.strptime(date_text, "%Y年%m月%d日").replace(tzinfo=timezone.utc)

            # タイトル取得
            title = row.locator("div.newsTitle a").inner_text(timeout=5000).strip()

            # リンク取得
            href = row.locator("div.newsTitle a").get_attribute("href")
            link = urljoin(BASE_URL, href) if href else DEFAULT_LINK

            # カテゴリと説明
            category = row.locator("div.newsCategory").inner_text(timeout=5000).strip()
            description = f"{category}：{title}"

            items.append({
                "title": title,
                "link": link,
                "description": description,
                "pub_date": pub_date
            })

        except Exception as e:
            print(f"⚠️ 行{i+1}の解析に失敗: {e}")
            continue

    return items

# ===== メイン実行ブロック =====
with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        print("▶ ページにアクセス中...")
        page.goto(DEFAULT_LINK, timeout=30000)
        page.wait_for_load_state("load", timeout=30000)
    except PlaywrightTimeoutError:
        print("⚠️ ページの読み込みに失敗しました。")
        browser.close()
        exit()

    print("▶ 更新情報を抽出しています...")
    items = extract_items(page)

    if not items:
        print("⚠️ 抽出できた更新情報がありません。HTML構造が変わっている可能性があります。")

    rss_path = "rss_output/DaiichiSankyo.xml"
    generate_rss(items, rss_path)
    browser.close()
