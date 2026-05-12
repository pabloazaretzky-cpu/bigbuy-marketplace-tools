"""
demanda_bol.py
Scrapes bol.com bestseller pages to find high-demand products.
Returns a list of dicts with name, EAN, price, review count and bol URL.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
from bs4 import BeautifulSoup
import re
import time
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

# bol.com bestseller category URLs (slug → label)
CATEGORIAS = {
    'speelgoed':           'https://www.bol.com/nl/l/bestsellers-speelgoed/N/8281/',
    'elektronica':         'https://www.bol.com/nl/l/bestsellers-elektronica/N/8274/',
    'sport-outdoor':       'https://www.bol.com/nl/l/bestsellers-sport-outdoor/N/13535/',
    'tuin':                'https://www.bol.com/nl/l/bestsellers-tuin/N/8279/',
    'wonen-slapen':        'https://www.bol.com/nl/l/bestsellers-wonen-slapen/N/8291/',
    'keuken':              'https://www.bol.com/nl/l/bestsellers-keuken/N/8280/',
    'baby':                'https://www.bol.com/nl/l/bestsellers-baby/N/8265/',
    'beauty':              'https://www.bol.com/nl/l/bestsellers-beauty/N/8266/',
    'huisdieren':          'https://www.bol.com/nl/l/bestsellers-huisdieren/N/13543/',
    'kleding-schoenen':    'https://www.bol.com/nl/l/bestsellers-kleding-dames/N/8285/',
}


def _parse_price(text: str) -> float | None:
    clean = re.sub(r'[^\d,.]', '', text or '')
    if not clean:
        return None
    if ',' in clean and '.' in clean:
        clean = clean.replace('.', '').replace(',', '.')
    elif ',' in clean:
        clean = clean.replace(',', '.')
    try:
        return float(clean)
    except ValueError:
        return None


def _parse_reviews(text: str) -> int:
    nums = re.findall(r'\d+', (text or '').replace('.', ''))
    return int(nums[0]) if nums else 0


def _scrape_pagina(url: str, categoria: str, delay: float = 2.0) -> list[dict]:
    time.sleep(delay)
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return []
    except Exception:
        return []

    soup = BeautifulSoup(r.text, 'html.parser')
    productos = []

    # Each product card on bol.com bestseller page
    for card in soup.select('li[data-test="product-item"]'):
        nombre = ''
        precio = None
        reviews = 0
        ean = ''
        link = ''

        # Name
        el_nombre = card.select_one('[data-test="product-title"]')
        if el_nombre:
            nombre = el_nombre.get_text(strip=True)

        # Price
        el_precio = card.select_one('[data-test="price"]')
        if not el_precio:
            el_precio = card.select_one('.prijs-incl-btw')
        if el_precio:
            precio = _parse_price(el_precio.get_text(strip=True))

        # Review count
        el_reviews = card.select_one('[data-test="review-count"]')
        if not el_reviews:
            el_reviews = card.select_one('.review-count')
        if el_reviews:
            reviews = _parse_reviews(el_reviews.get_text(strip=True))

        # Product link
        el_link = card.select_one('a[data-test="product-title"], a[href*="/p/"]')
        if el_link and el_link.get('href'):
            href = el_link['href']
            link = f"https://www.bol.com{href}" if href.startswith('/') else href

        # Try to extract EAN from JSON-LD in the page (not always in card)
        # We'll leave it empty here; the main script can enrich later
        if nombre and precio:
            productos.append({
                'Categoria':    categoria,
                'Nombre_NL':    nombre,
                'Precio_Bol':   precio,
                'Num_Reviews':  reviews,
                'EAN':          ean,
                'Link_Bol':     link,
            })

    return productos


def buscar_bestsellers(categorias: list[str] | None = None, paginas: int = 2,
                       delay: float = 2.5) -> list[dict]:
    """
    Scrapes bol.com bestseller pages.

    Args:
        categorias: list of category keys from CATEGORIAS dict (None = all)
        paginas:    number of pages per category to scrape
        delay:      seconds between requests

    Returns:
        list of product dicts sorted by review count descending
    """
    cats = {k: CATEGORIAS[k] for k in (categorias or CATEGORIAS.keys()) if k in CATEGORIAS}
    todos = []

    for slug, base_url in cats.items():
        print(f"  🔍 Scraping categoría: {slug}")
        for page in range(1, paginas + 1):
            url = base_url if page == 1 else f"{base_url}?page={page}"
            items = _scrape_pagina(url, slug, delay)
            todos.extend(items)
            if not items:
                break
            print(f"     página {page}: {len(items)} productos encontrados")

    # deduplicate by name+price
    seen = set()
    unique = []
    for p in todos:
        key = (p['Nombre_NL'], p['Precio_Bol'])
        if key not in seen:
            seen.add(key)
            unique.append(p)

    unique.sort(key=lambda x: x['Num_Reviews'], reverse=True)
    return unique


if __name__ == '__main__':
    resultados = buscar_bestsellers(paginas=1)
    print(f"\n✅ Total productos únicos encontrados: {len(resultados)}")
    for p in resultados[:10]:
        print(f"  [{p['Categoria']}] {p['Nombre_NL']} — €{p['Precio_Bol']} — {p['Num_Reviews']} reviews")
