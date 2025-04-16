import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import re
import time
import concurrent.futures
from urllib.parse import urlparse
import logging

DB_FOLDER = "combined_db"
BIGBANG_DB = os.path.join(DB_FOLDER, "bigbang_data.db")
SHOPPSTER_DB = os.path.join(DB_FOLDER, "shoppster_data.db")

BIGBANG_DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1353057588354355272/S_xLS4wLszT5Bq-iQjxeZ-GjnOhbWlWzdh7SFO0TLjGd69uWu2yljMi5wPwTEFlx0dOo"
SHOPPSTER_DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1351619519067455528/pvAuiy1bu7ny-_iFjrPiPCOm7jh7bt_xT9PhtBdYzQH9SSA6BdgDEmJp9LiCzwYjul3P"

BIGBANG_CATEGORIES = [
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
SHOPPSTER_CATEGORIES = [
    "https://www.shoppster.si/c/F3250", "https://www.shoppster.si/c/F020631", 
    "https://www.shoppster.si/c/F040105", "https://www.shoppster.si/c/F020628", 
    "https://www.shoppster.si/c/F020630", "https://www.shoppster.si/c/F020106",
    "https://www.shoppster.si/c/F040219", "https://www.shoppster.si/c/F020208",
    "https://www.shoppster.si/c/F373", "https://www.shoppster.si/c/F1383",
    "https://www.shoppster.si/c/F136", "https://www.shoppster.si/c/F0810",
    "https://www.shoppster.si/c/F3030", "https://www.shoppster.si/c/F050216",
    "https://www.shoppster.si/c/F040201", "https://www.shoppster.si/c/F040107",
    "https://www.shoppster.si/c/F040202", "https://www.shoppster.si/c/F040301",
    "https://www.shoppster.si/c/F040211", "https://www.shoppster.si/c/F040302",
    "https://www.shoppster.si/c/F190303", "https://www.shoppster.si/c/F040210",
    "https://www.shoppster.si/c/F040230", "https://www.shoppster.si/c/F040231",
    "https://www.shoppster.si/c/F895", "https://www.shoppster.si/c/F050101",
    "https://www.shoppster.si/c/F081202", "https://www.shoppster.si/c/F040403",
    "https://www.shoppster.si/c/F957", "https://www.shoppster.si/c/F616", 
    "https://www.shoppster.si/c/F040401","https://www.shoppster.si/c/F040323",
    "https://www.shoppster.si/c/F040412", "https://www.shoppster.si/c/F040404",
    "https://www.shoppster.si/c/F040407", "https://www.shoppster.si/c/F55",    
    "https://www.shoppster.si/c/F040411", "https://www.shoppster.si/c/F040215",
    "https://www.shoppster.si/c/F040109", "https://www.shoppster.si/c/F141214",
    "https://www.shoppster.si/c/F040126","https://www.shoppster.si/c/F040113", 
    "https://www.shoppster.si/c/F040106", "https://www.shoppster.si/c/F040111",    
]

def create_db(db_path):
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)
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

def extract_price(price_text):
    price_text = price_text.replace(".", "").replace(",", ".")
    numbers = re.findall(r'\d+\.\d+|\d+', price_text)
    return float(numbers[0]) if numbers else None

def send_discord_message(webhook, name, old_price, new_price, drop_percent, link):
    message = {
        "content": f"🚨 PRICE DROP ALERT 🚨\n\n**{name}** has dropped in price!\n\n"
                   f"Old Price: €{old_price:.2f}\nNew Price: €{new_price:.2f}\n"
                   f"💰 Price Drop: **{drop_percent:.1f}%**\n\n🔗 [View Product]({link})"
    }
    requests.post(webhook, json=message)
def start_scraper():
    """Main scraper loop that runs continuously"""
    while True:
        try:
            logging.info("Starting new scraping cycle")
            scrape_all()
            logging.info("Scraping cycle completed, sleeping for 1 hour")
            time.sleep(10)  # Sleep for 10 sec
        except Exception as e:
            logging.error(f"Error in scraper: {e}")
            time.sleep(300)  # Sleep for 5 minutes on error
def check_price_drop(cursor, name, new_price, link, webhook):
    cursor.execute("SELECT price FROM products WHERE link = ?", (link,))
    row = cursor.fetchone()
    if row and row[0] > new_price:
        drop_percent = ((row[0] - new_price) / row[0]) * 100
        if drop_percent >= 40:
            send_discord_message(webhook, name, row[0], new_price, drop_percent, link)

def scrape_bigbang(session, category_url):
    category_name = category_url.split("/")[-2]
    create_db(BIGBANG_DB)
    conn = sqlite3.connect(BIGBANG_DB)
    cursor = conn.cursor()
    page = 1
    while True:
        response = session.get(f"{category_url}?page={page}")
        if response.status_code != 200:
            break
        print(f"🔄 Scraping BB {category_name} - Page {page}")

        soup = BeautifulSoup(response.text, "html.parser")
        products = soup.find_all("article", class_="cp")
        if not products:
            break
        for product in products:
            name = product.find("h2", class_="cp-title").text.strip()
            price = extract_price(product.find("div", class_="cp-current-price").text.strip())
            link = "https://www.bigbang.si" + product.find("a")["href"]
            if price:
                check_price_drop(cursor, name, price, link, BIGBANG_DISCORD_WEBHOOK)
                cursor.execute("INSERT INTO products (name, price, link, category) VALUES (?, ?, ?, ?) "
                               "ON CONFLICT(link) DO UPDATE SET price = excluded.price, last_updated = CURRENT_TIMESTAMP",
                               (name, price, link, category_name))
        conn.commit()
        page += 1
    conn.close()

def scrape_shoppster(session, category_url):
    category_name = category_url.split("/")[-1]
    create_db(SHOPPSTER_DB)
    conn = sqlite3.connect(SHOPPSTER_DB)
    cursor = conn.cursor()

    page = 1
    while True:
        response = session.get(f"{category_url}?currentPage={page}")
        if response.status_code != 200:
            break
        print(f"🔄 Scraping shoppster: {category_name} - Page {page}")

        soup = BeautifulSoup(response.text, "html.parser")
        products = soup.find_all("div", {"data-cy": "plp-item"})
        if not products:
            break
        for product in products:
            name = product.find("a", class_="plp__product-name").text.strip()
            price = extract_price(product.find("span", class_="price-value").text.strip())
            link = "https://www.shoppster.si" + product.find("a")["href"]
            if price:
                check_price_drop(cursor, name, price, link, SHOPPSTER_DISCORD_WEBHOOK)
                cursor.execute("INSERT INTO products (name, price, link, category) VALUES (?, ?, ?, ?) "
                               "ON CONFLICT(link) DO UPDATE SET price = excluded.price, last_updated = CURRENT_TIMESTAMP",
                               (name, price, link, category_name))
        conn.commit()
        page += 1
    conn.close()

def scrape_all():
    start_time = time.time()
    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        logging.info("Scraping BigBang categories...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(lambda url: scrape_bigbang(session, url), BIGBANG_CATEGORIES)
        logging.info("Scraping Shoppster categories...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(lambda url: scrape_shoppster(session, url), SHOPPSTER_CATEGORIES)
    logging.info(f"Scraping complete! Time taken: {time.time() - start_time:.2f} seconds")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scraper.log'),
            logging.StreamHandler()
        ]
    )
    start_scraper()
