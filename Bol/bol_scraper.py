import requests
from bs4 import BeautifulSoup
import json
import re
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

def _parse_dutch_price(text):
    """Converts Dutch price string like '€ 1.249,99' to float 1249.99"""
    clean = re.sub(r'[^\d,.]', '', text)
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

def buscar_en_bol(ean, delay=2.0):
    """
    Searches Bol.com for a product by EAN13.
    Returns (precio: float|None, url: str)
    Falls back to search URL if product not found or scraping fails.
    """
    search_url = f"https://www.bol.com/nl/s/?searchtext={ean}"
    try:
        time.sleep(delay)
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None, search_url

        soup = BeautifulSoup(resp.text, 'html.parser')
        precio = None
        url = search_url

        # Method 1: JSON-LD structured data (most reliable when present)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get('@type') == 'Product':
                        offers = item.get('offers', {})
                        if isinstance(offers, list):
                            offers = offers[0]
                        p = offers.get('price')
                        if p:
                            precio = float(str(p).replace(',', '.'))
                        link = item.get('url') or offers.get('url')
                        if link:
                            url = link if link.startswith('http') else f"https://www.bol.com{link}"
                        return precio, url
            except Exception:
                pass

        # Method 2: HTML selectors fallback
        for sel in ['[data-test="price"]', '.prijs-incl-btw', '[class*="price--incl"]']:
            el = soup.select_one(sel)
            if el:
                p = _parse_dutch_price(el.get_text(strip=True))
                if p:
                    precio = p
                    break

        for sel in ['a[data-test="product-title"]', 'a.product-title', 'article a[href*="/p/"]']:
            el = soup.select_one(sel)
            if el and el.get('href'):
                href = el['href']
                url = f"https://www.bol.com{href}" if href.startswith('/') else href
                break

        return precio, url

    except Exception:
        return None, search_url
