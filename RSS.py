import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime

# 対象のURL
url = 'https://iryohokenjyoho.service-now.com/csm?id=kb_search&kb_knowledge_base=...'

# ページを取得
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

# RSSフィードの設定
fg = FeedGenerator()
fg.title('医療保険情報ポータル｜ナレッジ更新情報')
fg.link(href=url, rel='alternate')
fg.description('医療保険情報ポータルのナレッジ記事更新情報')
fg.language('ja')

# ナレッジ記事の抽出（例として、クラス名 'kb-article' を持つ要素を対象）
for article in soup.find_all('div', class_='kb-article'):
    title = article.find('a').get_text(strip=True)
    link = article.find('a')['href']
    pub_date = datetime.utcnow()  # 実際の公開日を取得する場合は、適切な方法で取得してください

    fe = fg.add_entry()
    fe.title(title)
    fe.link(href=link)
    fe.pubDate(pub_date)

# RSSフィードをXMLとして保存
import os
os.makedirs('rss_output', exist_ok=True)
fg.rss_file('rss_output/iryohokenjoho.xml')
