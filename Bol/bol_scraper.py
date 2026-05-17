import requests
from bs4 import BeautifulSoup
import json
import re
import time
import urllib.parse

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}


def _parse_dutch_price(text):
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


def _similitud_nombre(a, b):
    """Token overlap similarity between two product names, 0.0–1.0."""
    stopwords = {'de', 'het', 'een', 'en', 'van', 'voor', 'met', 'in', 'the', 'a', 'an', 'of', 'and', 'for', 'with'}
    tokens_a = set(re.sub(r'[^\w\s]', '', a.lower()).split()) - stopwords
    tokens_b = set(re.sub(r'[^\w\s]', '', b.lower()).split()) - stopwords
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))


def _extraer_resultado(soup, fallback_url):
    """Extract price, url, and title from a Bol.com search results page."""
    precio = None
    url = fallback_url
    titulo = ''

    # Method 1: JSON-LD structured data (most reliable)
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
                    titulo = item.get('name', '')
                    return precio, url, titulo
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
        if el:
            if el.get('href'):
                href = el['href']
                url = f"https://www.bol.com{href}" if href.startswith('/') else href
            titulo = el.get_text(strip=True)
            break

    return precio, url, titulo


def buscar_en_bol(ean=None, nombre=None, marca=None, delay=2.0):
    """
    Searches Bol.com by EAN first, then by name as fallback.
    Validates the result against the expected product name to avoid false matches.

    Returns dict:
        precio     float | None
        url        str
        titulo_bol str
        confianza  'ALTA' | 'MEDIA' | 'BAJA' | 'NO_ENCONTRADO'

    Confianza:
        ALTA  — EAN match, name similarity >= 0.6 (or no name to compare)
        MEDIA — EAN match with similarity 0.4–0.6, or name-search with similarity >= 0.5
        BAJA  — Low similarity; likely a false match, treat with caution
        NO_ENCONTRADO — No price found
    """
    resultado_vacio = {'precio': None, 'url': '', 'titulo_bol': '', 'confianza': 'NO_ENCONTRADO'}

    # Step 1: Search by EAN
    if ean:
        search_url = f"https://www.bol.com/nl/s/?searchtext={ean}"
        try:
            time.sleep(delay)
            resp = requests.get(search_url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                precio, url, titulo = _extraer_resultado(soup, search_url)
                if precio:
                    if nombre and titulo:
                        sim = _similitud_nombre(nombre, titulo)
                        if sim >= 0.6:
                            confianza = 'ALTA'
                        elif sim >= 0.4:
                            confianza = 'MEDIA'
                        else:
                            confianza = 'BAJA'
                    else:
                        confianza = 'ALTA'
                    if confianza in ('ALTA', 'MEDIA'):
                        return {'precio': precio, 'url': url, 'titulo_bol': titulo, 'confianza': confianza}
        except Exception:
            pass

    # Step 2: Fallback to name search
    if nombre:
        query = urllib.parse.quote(nombre[:80])
        search_url = f"https://www.bol.com/nl/s/?searchtext={query}"
        try:
            time.sleep(delay)
            resp = requests.get(search_url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                precio, url, titulo = _extraer_resultado(soup, search_url)
                if precio and titulo:
                    sim = _similitud_nombre(nombre, titulo)
                    if sim >= 0.5:
                        confianza = 'MEDIA'
                    elif sim >= 0.3:
                        confianza = 'BAJA'
                    else:
                        return resultado_vacio
                    return {'precio': precio, 'url': url, 'titulo_bol': titulo, 'confianza': confianza}
        except Exception:
            pass

    return resultado_vacio
