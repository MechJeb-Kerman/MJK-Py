import csv
import time
import requests
from bs4 import BeautifulSoup

url = "https://quotes.toscrape.com/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36"
}

resp = requests.get(url, headers=headers, timeout=10)
resp.raise_for_status()
resp.encoding = resp.apparent_encoding

soup = BeautifulSoup(resp.text, "html.parser")
rows = []

for quote in soup.select(".quote"):
    text = quote.select_one(".text").get_text(strip=True)
    author = quote.select_one(".author").get_text(strip=True)
    tags = [tag.get_text(strip=True) for tag in quote.select(".tags .tag")]
    rows.append([text, author, ",".join(tags)])

with open("quotes.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["名言", "作者", "标签"])
    writer.writerows(rows)

print(rows[:3])