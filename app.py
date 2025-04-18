from flask import Flask, jsonify, render_template, request
import sqlite3
import os
from scraperBB import DB_FOLDER, BIGBANG_DB, SHOPPSTER_DB, scrape_all
from threading import Thread

app = Flask(__name__)

def get_products(db_path, page=1, per_page=40, category=None):
    offset = (page - 1) * per_page
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT category FROM products")
    categories = [row[0] for row in cursor.fetchall()]
    
    query = "FROM products"
    params = []
    
    if category:
        query += " WHERE category = ?"
        params.append(category)
    
    cursor.execute(f"SELECT COUNT(*) {query}", params)
    total_count = cursor.fetchone()[0]
    
    cursor.execute(f"""
        SELECT name, price, link, category, last_updated 
        {query}
        ORDER BY last_updated DESC 
        LIMIT ? OFFSET ?""", 
        params + [per_page, offset])
    products = cursor.fetchall()
    conn.close()
    
    return products, total_count, categories

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/bigbang')
def bigbang():
    return render_template('bigbang.html')

@app.route('/shoppster')
def shoppster():
    return render_template('shoppster.html')

@app.route('/api/bigbang/products')
def get_bigbang_products():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', None)
    per_page = 40
    
    products, total, categories = get_products(BIGBANG_DB, page, per_page, category)
    
    return jsonify({
        'products': [{
            'name': p[0],
            'price': p[1],
            'link': p[2],
            'category': p[3],
            'last_updated': p[4]
        } for p in products],
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'categories': categories
    })

@app.route('/api/shoppster/products')
def get_shoppster_products():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', None)
    per_page = 40
    
    products, total, categories = get_products(SHOPPSTER_DB, page, per_page, category)
    
    return jsonify({
        'products': [{
            'name': p[0],
            'price': p[1],
            'link': p[2],
            'category': p[3],
            'last_updated': p[4]
        } for p in products],
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'categories': categories
    })

@app.route('/api/scrape', methods=['POST'])
def trigger_scrape():
    Thread(target=scrape_all).start()
    return jsonify({'status': 'Scraping started'})

if __name__ == '__main__':
    app.run(debug=True)


