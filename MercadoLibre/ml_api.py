import requests
import time

# Sitios ML por país
ML_SITES = {
    'mexico':    'MLM',
    'colombia':  'MCO',
    'argentina': 'MLA',
    'chile':     'MLC',
    'peru':      'MPE',
}

# Marcas claramente no europeas (no aptas para reventa en global selling)
MARCAS_NO_EU = {
    'amazon', 'apple', 'blink', 'ring', 'arlo', 'wyze', 'ezviz',
    'samsung', 'lg', 'xiaomi', 'huawei', 'oppo', 'oneplus', 'realme',
    'tp-link', 'asus', 'acer', 'lenovo', 'msi', 'corsair', 'razer',
    'google', 'nest', 'microsoft', 'anker', 'baseus', 'ugreen', 'jbl',
}

# Costo de envío ML Global Selling EU → LATAM (estimado por peso en kg)
ENVIO_ML = [
    (0.5,  8.00),
    (1.0, 12.00),
    (2.0, 16.00),
    (3.0, 20.00),
    (5.0, 25.00),
    (10.0, 32.00),
]

def calcular_envio_ml(peso_kg):
    for limite, costo in ENVIO_ML:
        if peso_kg <= limite:
            return costo
    return 40.00

def es_marca_eu(brand):
    if not brand or str(brand).lower() in ('nan', 'none', ''):
        return True
    return str(brand).strip().lower() not in MARCAS_NO_EU

def get_tipo_cambio_eur():
    """Returns dict of rates relative to EUR (e.g. {'MXN': 20.5, 'COP': 4400, ...})"""
    try:
        resp = requests.get('https://open.er-api.com/v6/latest/EUR', timeout=10)
        data = resp.json()
        return data.get('rates', {})
    except Exception:
        # Fallback con valores aproximados
        return {'MXN': 20.5, 'COP': 4400.0, 'ARS': 1050.0, 'CLP': 1000.0, 'PEN': 38.0}

def buscar_en_ml(ean, nombre='', site_id='MLM', delay=0.5):
    """
    Searches MercadoLibre by EAN using the public API.
    Returns (precio_local: float|None, moneda: str|None, link: str|None)
    """
    time.sleep(delay)
    try:
        url = f'https://api.mercadolibre.com/search?site_id={site_id}&q={ean}&limit=5'
        resp = requests.get(url, timeout=12)
        if resp.status_code != 200:
            return None, None, None
        results = resp.json().get('results', [])
        if not results:
            # Fallback: search by name if EAN gives no results
            if nombre:
                url2 = f'https://api.mercadolibre.com/search?site_id={site_id}&q={nombre[:60]}&limit=3'
                resp2 = requests.get(url2, timeout=12)
                if resp2.status_code == 200:
                    results = resp2.json().get('results', [])
        if not results:
            return None, None, None
        item = results[0]
        return item.get('price'), item.get('currency_id'), item.get('permalink')
    except Exception:
        return None, None, None
