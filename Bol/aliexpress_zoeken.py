"""
aliexpress_zoeken.py
Searches AliExpress for a product by name and returns price + supplier info.
Uses the mobile AliExpress search page (easier to parse than desktop).
Falls back to None values if blocked or product not found.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
from bs4 import BeautifulSoup
import re
import time
import json
import urllib.parse

HEADERS_ALI = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www.aliexpress.com/',
}


def _parse_ali_price(text: str) -> float | None:
    """Extracts the lowest price from strings like 'US $1.23 - 4.56' or '€2.99'."""
    nums = re.findall(r'\d+[.,]\d+', text or '')
    if not nums:
        nums = re.findall(r'\d+', text or '')
    if not nums:
        return None
    # Take the lowest (first) price
    try:
        return float(nums[0].replace(',', '.'))
    except ValueError:
        return None


def _usd_to_eur(usd: float) -> float:
    """Rough USD → EUR conversion. Update rate as needed."""
    return round(usd * 0.93, 2)


def buscar_en_aliexpress(nombre_producto: str, max_resultados: int = 3,
                         delay: float = 3.0) -> dict:
    """
    Searches AliExpress mobile site for a product.

    Returns dict with:
        precio_min_eur: lowest unit price found (EUR)
        precio_max_eur: highest unit price in range (EUR)
        moq:            minimum order quantity (default 1 if not found)
        url_producto:   link to cheapest listing
        titulo_ali:     product title on AliExpress
        encontrado:     bool
    """
    resultado = {
        'precio_min_eur': None,
        'precio_max_eur': None,
        'moq': 1,
        'url_producto': '',
        'titulo_ali': '',
        'encontrado': False,
    }

    query = urllib.parse.quote(nombre_producto[:80])  # truncate long names
    url = f"https://www.aliexpress.com/wholesale?SearchText={query}&SortType=total_tranexn_desc"

    time.sleep(delay)
    try:
        r = requests.get(url, headers=HEADERS_ALI, timeout=20)
        if r.status_code != 200:
            return resultado
    except Exception:
        return resultado

    soup = BeautifulSoup(r.text, 'html.parser')

    # Method 1: JSON data embedded in page scripts (most reliable)
    for script in soup.find_all('script'):
        text = script.string or ''
        if 'window.runParams' in text or '_init_data_' in text:
            # Try to extract product array from JS
            match = re.search(r'"items"\s*:\s*(\[.*?\])', text, re.DOTALL)
            if match:
                try:
                    items = json.loads(match.group(1))
                    if items:
                        item = items[0]
                        price_text = str(item.get('price', '') or item.get('salePrice', ''))
                        precio = _parse_ali_price(price_text)
                        if precio:
                            # AliExpress prices are usually in USD
                            precio_eur = _usd_to_eur(precio)
                            resultado.update({
                                'precio_min_eur': precio_eur,
                                'precio_max_eur': precio_eur,
                                'url_producto': item.get('productDetailUrl', url),
                                'titulo_ali': item.get('title', ''),
                                'encontrado': True,
                            })
                            return resultado
                except Exception:
                    pass

    # Method 2: Parse product cards from HTML
    cards = (soup.select('.search-item-card-wrapper-gallery') or
             soup.select('[class*="manhattan--container"]') or
             soup.select('[class*="product-item"]'))

    precios = []
    for card in cards[:max_resultados]:
        # Price
        el_price = (card.select_one('[class*="price--current"]') or
                    card.select_one('[class*="price_current"]') or
                    card.select_one('[class*="manhattan--price"]'))
        if el_price:
            p = _parse_ali_price(el_price.get_text(strip=True))
            if p:
                precios.append(p)

        # Get first product link if we don't have one
        if not resultado['url_producto']:
            el_link = card.select_one('a[href*="aliexpress.com/item"]')
            if not el_link:
                el_link = card.select_one('a[href*="/item/"]')
            if el_link:
                href = el_link.get('href', '')
                if href.startswith('//'):
                    href = 'https:' + href
                resultado['url_producto'] = href

            el_title = card.select_one('[class*="title"]')
            if el_title:
                resultado['titulo_ali'] = el_title.get_text(strip=True)[:100]

    if precios:
        min_usd = min(precios)
        max_usd = max(precios)
        resultado.update({
            'precio_min_eur': _usd_to_eur(min_usd),
            'precio_max_eur': _usd_to_eur(max_usd),
            'encontrado': True,
        })

    return resultado


def estimar_envio_china_nl(peso_kg: float = 0.5) -> float:
    """
    Estimates AliExpress Standard Shipping / ePacket cost to Netherlands.
    Based on typical rates for small packages.
    """
    if peso_kg <= 0.1:
        return 1.50
    elif peso_kg <= 0.3:
        return 2.50
    elif peso_kg <= 0.5:
        return 3.50
    elif peso_kg <= 1.0:
        return 5.00
    elif peso_kg <= 2.0:
        return 8.00
    elif peso_kg <= 5.0:
        return 15.00
    else:
        return round(peso_kg * 4.0, 2)  # ~€4/kg for heavier items


if __name__ == '__main__':
    test = buscar_en_aliexpress("bluetooth earbuds wireless")
    print(f"Encontrado: {test['encontrado']}")
    print(f"Precio min: €{test['precio_min_eur']}")
    print(f"URL: {test['url_producto']}")
    print(f"Envío estimado (0.1kg): €{estimar_envio_china_nl(0.1)}")
