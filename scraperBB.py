import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import re
import time
import concurrent.futures

DB_FOLDER = "bigbang_db"

CATEGORIES = [
    "https://www.bigbang.si/izdelki/racunalnistvo/prenosni-racunalniki/",  "https://www.bigbang.si/izdelki/racunalnistvo/namizni-racunalniki/",
     "https://www.bigbang.si/izdelki/racunalnistvo/tablicni-racunalnik/", "https://www.bigbang.si/izdelki/racunalnistvo/monitorji/",
     "https://www.bigbang.si/izdelki/racunalnistvo/tiskalniki-in-3d-tiskalniki/", "https://www.bigbang.si/izdelki/racunalnistvo/e-bralniki-in-graficne-tablice/",
     "https://www.bigbang.si/izdelki/racunalnistvo/racunalniska-oprema/", "https://www.bigbang.si/izdelki/racunalnistvo/racunalniske-komponente/",
     "https://www.bigbang.si/izdelki/racunalnistvo/shranjevanje-podatkov/", "https://www.bigbang.si/izdelki/racunalnistvo/racunalniski-pribor/"
]


def sanitize_category_name(name):
    return name.replace(" ", "_"). replace("/", "_").replace(":", "_"). replace("&", "_")

def imeKat(session, category_url):
    response = session.get(category_url)
    if response.status_code != 200:
        print(f"neki je slo narob: {category_url}")
        return None
    soup = BeautifulSoup(response.text, 'html.parser')
    category_name_tag = soup.find("h1", class_="category-page-title")
    if category_name_tag:
        return category_name_tag.text.strip()
    else:
        print(f"Nisem nasel kategorije: {category_url}")
        return None 
    
def nared_db(category_name):
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)
    cist_ime = sanitize_category_name(category_name)
    db_name = os.path.join(DB_FOLDER, f"{cist_ime}.db")

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS izdelki (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ime TEXT,
            cena REAL,
            url TEXT,
            slika TEXT
        )
    """)
    conn.commit()
    conn.close()

    return db_name

def extract_price(price_text):
    price_text = price_text.replace(",", ".").replace(".", ".")
    numbers = re.findall(r"\d+\.\d+", price_text)
    if not numbers:
        return None
    
    price = float(numbers[0])
    return price

def scrape_page(session, category_url, page):
    url = f"{category_url}?page={page}"
    response = session.get(url)
    if response.status_code != 200:
        print(f"nismo najdl paga za {page} v kategoriji {category_url}")
        return []
    soup = BeautifulSoup(response.text, 'html.parser')

    products = soup.find_all("article", class_ = "cp")

    data = []
    for product in products:
        name_tag = product.find("h2", class_ = "cp-title")
        price_tag_current = product.find("div", class_ = "cp-current-price")
        price_tag_old = product.find("div", class_ = "cp-old-price")

        if name_tag and price_tag_current:
            name = name_tag.get_text(strip=True)
            current_price = extract_price(price_tag_current.get_text(strip=True))

            old_price = None
            if price_tag_old:
                old_price = extract_price(price_tag_old.get_text(strip=True))

            link_tag = product.find("a", href=True)
            if link_tag:
                link = "https://www.bigbang.si" + link_tag["href"]
                data.append(name, current_price, old_price, link)
    return data