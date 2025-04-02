import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import re
import time
import concurrent.futures
from urllib.parse import urlparse

DB_FOLDER = "bigbang_db"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1353057588354355272/S_xLS4wLszT5Bq-iQjxeZ-GjnOhbWlWzdh7SFO0TLjGd69uWu2yljMi5wPwTEFlx0dOo"

CATEGORIES = [
    "https://www.bigbang.si/izdelki/racunalnistvo/prenosni-racunalniki/",
    "https://www.bigbang.si/izdelki/racunalnistvo/namizni-racunalniki/",
    "https://www.bigbang.si/izdelki/racunalnistvo/monitorji/",
    "https://www.bigbang.si/izdelki/racunalnistvo/e-bralniki-in-graficne-tablice/",
    "https://www.bigbang.si/izdelki/racunalnistvo/racunalniske-komponente/",
    "https://www.bigbang.si/izdelki/telefonija-in-pametne-ure/mobilni-telefoni/",
    "https://www.bigbang.si/izdelki/tv-avdio/tv-sprejemniki/",
    "https://www.bigbang.si/izdelki/tv-avdio/sistemi-za-domaci-kino/",
    "https://www.bigbang.si/izdelki/avdio-in-glasbila/slusalke/",
    "https://www.bigbang.si/izdelki/avdio-in-glasbila/zvocne-postaje/",
    "https://www.bigbang.si/izdelki/gaming/gaming-racunalniki-vr/",
    "https://www.bigbang.si/izdelki/gaming/igralne-konzole/",
    "https://www.bigbang.si/izdelki/gaming/gaming-oprema/",
    "https://www.bigbang.si/izdelki/foto-kamere/fotoaparati/",
    "https://www.bigbang.si/izdelki/foto-kamere/droni/",
    "https://www.bigbang.si/izdelki/foto-kamere/kamere/",
    "https://www.bigbang.si/izdelki/pametni-dom/pametni-nadzor-in-dostop/",
    "https://www.bigbang.si/izdelki/fitnes-zdravje-in-dobro-pocutje/nosljiva-tehnologija/pametne-ure/",
    "https://www.bigbang.si/izdelki/fitnes-zdravje-in-dobro-pocutje/nosljiva-tehnologija/sportne-ure/",
    "https://www.bigbang.si/izdelki/fitnes-zdravje-in-dobro-pocutje/nosljiva-tehnologija/pametne-zapestnice/",
    "https://www.bigbang.si/izdelki/fitnes-zdravje-in-dobro-pocutje/nosljiva-tehnologija/pametni-prstani/",
    "https://www.bigbang.si/izdelki/racunalnistvo/tablicni-racunalnik/tablicni-racunalniki/",
    "https://www.bigbang.si/izdelki/racunalnistvo/racunalniska-oprema/tipkovnice/",
    "https://www.bigbang.si/izdelki/racunalnistvo/racunalniska-oprema/miske/",
    "https://www.bigbang.si/izdelki/racunalnistvo/racunalniska-oprema/slusalke-pc/",
    "https://www.bigbang.si/izdelki/racunalnistvo/racunalniska-oprema/pc-zvocniki/",
    "https://www.bigbang.si/izdelki/racunalnistvo/racunalniska-oprema/omrezna-oprema/"
]

def sanitize_category_name(name):
    """Sanitizes the category name for database file naming."""
    return name.replace(" ", "_").replace("/", "_").replace(":", "_").replace("&", "_")

def extract_category_name(url):
    """Extracts a readable category name from the URL."""
    path_segments = urlparse(url).path.strip("/").split("/")
    return sanitize_category_name(path_segments[-1]) if path_segments else "Unknown"

def create_db():
    """Creates a single database for all categories."""
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)

    db_path = os.path.join(DB_FOLDER, "bigbang_data.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        price REAL,
                        link TEXT UNIQUE,
                        category TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()
    return db_path

def extract_price(price_text):
    """Extracts and converts price text to a float."""
    price_text = price_text.replace(".", "").replace(",", ".")
    numbers = re.findall(r'\d+\.\d+|\d+', price_text)
    return float(numbers[0]) if numbers else None

def send_discord_message(name, old_price, new_price, drop_percent, link):
    """Sends a price drop alert to Discord."""
    message = {
        "content": f"🚨 **PRICE DROP ALERT** 🚨\n\n**{name}** has dropped in price!\n\n"
                   f"Old Price: €{old_price:.2f}\nNew Price: €{new_price:.2f}\n"
                   f"💰 Price Drop: **{drop_percent:.1f}%**\n\n🔗 [View Product]({link})"
    }
    response = requests.post(DISCORD_WEBHOOK_URL, json=message)
    if response.status_code == 204:
        print(f"✅ Price drop alert sent for {name}")
    else:
        print(f"❌ Failed to send alert for {name} - {response.status_code}")

def check_price_drop(cursor, name, new_price, link):
    """Checks for price drops and triggers Discord alerts if needed."""
    cursor.execute("SELECT price FROM products WHERE link = ?", (link,))
    row = cursor.fetchone()
    if row:
        old_price = row[0]
        if old_price and old_price > new_price:
            drop_percent = ((old_price - new_price) / old_price) * 100
            if drop_percent >= 30:
                print(f"📉 **PRICE DROP DETECTED**: {name} ({drop_percent:.1f}% OFF)")
                send_discord_message(name, old_price, new_price, drop_percent, link)

def scrape_page(session, category_url, page, category_name):
    """Scrapes a single page of products from the category."""
    print(f"🔄 Scraping {category_name} - Page {page}")

    url = f"{category_url}?page={page}"
    response = session.get(url)
    
    if response.status_code != 200:
        print(f"❌ Failed to retrieve page {page} for {category_url}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    products = soup.find_all("article", class_="cp")

    data = []
    for product in products:
        name_tag = product.find("h2", class_="cp-title")
        price_tag = product.find("div", class_="cp-current-price")
        link_tag = product.find("a", href=True)

        if name_tag and price_tag and link_tag:
            name = name_tag.get_text(strip=True)
            price = extract_price(price_tag.get_text(strip=True))
            link = "https://www.bigbang.si" + link_tag["href"]

            if price is not None:
                data.append((name, price, link))

    return data

def save_to_db(data, db_path, category):
    """Saves product data to the SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for name, price, link in data:
        check_price_drop(cursor, name, price, link)
        cursor.execute('''INSERT INTO products (name, price, link, category) 
                          VALUES (?, ?, ?, ?) 
                          ON CONFLICT(link) DO UPDATE SET price = excluded.price, last_updated = CURRENT_TIMESTAMP''',
                       (name, price, link, category))

    conn.commit()
    conn.close()

def scrape_category(session, category_url):
    """Scrapes all available pages of a category."""

    category_name = extract_category_name(category_url)
    db_path = create_db()

    print(f"🔍 Scraping category: {category_name}...")

    page = 1
    while True:
        data = scrape_page(session, category_url, page, category_name)
        if not data:
            print(f"✅ No more products found in {category_name}. Stopping.")
            break
        
        save_to_db(data, db_path, category_name)
        page += 1 

    print(f"✅ Finished scraping: {category_name}")

def scrape_all_categories():
    """Scrapes all categories in parallel."""
    start_time = time.time()

    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0"})

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(scrape_category, session, url) for url in CATEGORIES]
            for future in concurrent.futures.as_completed(futures):
                future.result()

    print(f"\n🎯 Scraping complete! Total time taken: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    scrape_all_categories()