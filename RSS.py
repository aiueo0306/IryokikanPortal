from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re

BASE_URL = "https://iryohokenjyoho.service-now.com/csm?id=csm_index"
DEFAULT_LINK = "https://iryohokenjyoho.service-now.com/csm?id=kb_search&kb_knowledge_base=2ef0c56bdb6c3110c34095e3f3961948,e7b62343c3240a50cdbad24115013123,d211706cdb0ba11068e07845f396195c,8bb9a747c3240a50cdbad2411501310a,444a6787c3240a50cdbad24115013113,02b6539e1b2be110c3efea8ee54bcb37,47065541932d3150b298388efaba1041,d1ff4bd21b2be110c3efea8ee54bcb90,f2541f5a1b2be110c3efea8ee54bcb4c,bacaa7c7c3240a50cdbad24115013106,121babc7c3240a50cdbad241150131c4,8243dd4fdbe3091094889082f396193d,6351882b1be7e510c3efea8ee54bcb70,b0d57c20db4ba11068e07845f3961956,4f8b270bc3240a50cdbad24115013172,fbe9d5be93309e10b8eef4fe3bba1001,873b913293709e10b8eef4fe3bba1077&spa=1&language=ja"

def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title("医療機関向等総合ポータルサイト")
    fg.link(href=DEFAULT_LINK)
    fg.description("医療機関向等総合ポータルサイトページの更新履歴")
    fg.language("ja")
    fg.generator("python-feedgen")
    fg.docs("http://www.rssboard.org/rss-specification")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])

        # GUIDはユニークにする（リンク＋日付で）
        guid_value = f"{item['link']}#{item['pub_date'].strftime('%Y%m%d')}"
        entry.guid(guid_value, permalink=False)

        entry.pubDate(item['pub_date'])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")

def extract_items(page):
    page.goto(DEFAULT_LINK, timeout=30000)
    page.wait_for_load_state("networkidle")  # or 'domcontentloaded'
    page.wait_for_selector("div.summary-templates", timeout=10000)
    
    selector = "div.summary-templates > div.kb-template.ng-scope > div:nth-child(2) > div > div > div"
    rows = page.locator(selector)
    count = rows.count()
    print(f"📦 発見した更新情報行数: {count}")
    import sys
    print("一時停止（デバッグ用）")
    sys.exit()
    
    items = []

    for i in range(count):
        row = rows.nth(i)
        try:
            date_text = row.locator("td:nth-child(1)").inner_text().strip()
            content_html = row.locator("td:nth-child(2)").inner_html().strip()
            a_links = row.locator("td:nth-child(2) a")
            first_link = None
            if a_links.count() > 0:
                href = a_links.first.get_attribute("href")
                if href:
                    first_link = urljoin(BASE_URL, href)
            else:
                first_link = DEFAULT_LINK

            # description内の相対パスを絶対パスに変換
            content_html = content_html.replace('href="/', f'href="{BASE_URL}')

            try:
                pub_date = parse_date_text(date_text)
            except Exception as e:
                print(f"⚠ 日付の変換に失敗: {e}")
                pub_date = datetime.now(timezone.utc)

            items.append({
                "title": f"更新情報: {date_text}",
                "link": first_link,
                "description": content_html,  # CDATA不要
                "pub_date": pub_date
            })

        except Exception as e:
            print(f"⚠ 行{i+1}の解析に失敗: {e}")
            continue

    return items

def parse_date_text(text):
    text = text.replace("　", " ").replace("\u3000", " ")
    match = re.search(r"令和\s*(\d)年\s*(\d{1,2})月\s*(\d{1,2})日?", text)
    if match:
        r_year, month, day = map(int, match.groups())
        year = 2018 + r_year  # 令和元年＝2019年
        return datetime(year, month, day, tzinfo=timezone.utc)
    else:
        raise ValueError(f"日付変換失敗: {text}")

# ===== 実行ブロック =====
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
        print("⚠ ページの読み込みに失敗しました。")
        browser.close()
        exit()

    print("▶ 更新情報を抽出しています...")
    items = extract_items(page)

    if not items:
        print("⚠ 抽出できた更新情報がありません。HTML構造が変わっている可能性があります。")

    rss_path = "rss_output/shinryohoshu.xml"
    generate_rss(items, rss_path)
    browser.close()
