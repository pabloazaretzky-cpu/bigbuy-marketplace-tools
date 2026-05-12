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

# Marcas europeas conocidas — dan prioridad en el análisis
MARCAS_EU = {
    # Alemanas
    'adidas', 'puma', 'braun', 'bosch', 'siemens', 'nivea', 'zwilling',
    'wmf', 'leitz', 'stabilo', 'faber-castell', 'faber castell', 'lamy',
    'melitta', 'ritter sport', 'haribo',
    # Italianas
    'chicco', 'bialetti', 'alessi', 'guzzini', 'lagostina', 'guardini',
    'rosti mepal', 'valtur', 'picard', 'mandarina duck', 'invicta',
    'ferrino', 'zenith',
    # Españolas
    'taurus', 'jata', 'solac', 'orbegozo', 'ufesa', 'fagor', 'balay',
    'valira', 'monix', 'lacor', 'bra', 'nespresso',
    'camper', 'tous', 'lladro',
    # Francesas
    'tefal', 'moulinex', 'rowenta', 'bic', 'lacoste', 'peugeot',
    'opinel', 'laguiole', 'sabatier',
    # Nórdicas / Holandesas
    'philips', 'maped', 'fiskars',
    # Otras EU
    'lego', 'victorinox', 'wenger',
}

# Palabras clave en el nombre que sugieren origen o material europeo/mediterráneo típico
KEYWORDS_EU = {
    # Cuero y piel (resistentes al envío)
    'leather', 'cuero', 'piel', 'nappa', 'suede', 'ante', 'calf',
    'vachetta', 'saffiano', 'full grain',
    # Textiles europeos y turcos
    'linen', 'lino', 'wool', 'lana', 'cashmere', 'merino',
    'jacquard', 'damask', 'tapiz', 'tapestry', 'kilim',
    'peshtemal', 'hammam', 'hamam', 'fouta', 'turkish towel',
    'toalla turca', 'alfombra turca', 'turkish rug',
    # Corcho y madera (no frágiles)
    'cork', 'corcho', 'olive wood', 'madera de olivo',
    'beech wood', 'haya', 'walnut wood',
    # Aceites y cosméticos naturales de origen mediterráneo/africano
    'argan', 'aceite de argan', 'argan oil',
    'rosehip', 'rosa mosqueta',
    'olive oil soap', 'jabon de oliva', 'aleppo', 'castile soap', 'jabon de castilla',
    'natural oil', 'aceite natural', 'essential oil', 'aceite esencial',
    # Origen declarado
    'made in italy', 'hecho en italia', 'italian',
    'made in spain', 'hecho en españa', 'made in germany',
    'made in france', 'made in europe', 'hecho en europa',
    'turkish', 'turco', 'ottoman',
    # Artesanal
    'artisan', 'artesanal', 'handmade', 'handcrafted', 'hecho a mano',
    'hand painted', 'pintado a mano',
    # Mediterráneo / Gourmet (no líquidos frágiles)
    'iberico', 'ibérico', 'manchego',
    # Acero europeo / cuchillería
    'solingen', 'forged', 'forjado',
}


def es_marca_eu(brand):
    if not brand or str(brand).lower() in ('nan', 'none', ''):
        return True
    return str(brand).strip().lower() not in MARCAS_NO_EU


def clasificar_origen_eu(nombre, brand=''):
    """
    Identifica si un producto es típicamente europeo.
    Retorna: 'Marca EU', 'Tipico EU', o '' (genérico)
    """
    brand_lower = str(brand).strip().lower()
    nombre_lower = str(nombre).lower()

    # Verificar si es marca EU conocida
    for marca in MARCAS_EU:
        if marca in brand_lower or marca in nombre_lower:
            return 'Marca EU'

    # Verificar si el nombre sugiere producto típicamente europeo
    for kw in KEYWORDS_EU:
        if kw in nombre_lower:
            return 'Tipico EU'

    return ''


# Costo de envío ML Global Selling EU → LATAM (estimado por peso en kg)
ENVIO_ML = [
    (0.5,   8.00),
    (1.0,  12.00),
    (2.0,  16.00),
    (3.0,  20.00),
    (5.0,  25.00),
    (10.0, 32.00),
]


def calcular_envio_ml(peso_kg):
    for limite, costo in ENVIO_ML:
        if peso_kg <= limite:
            return costo
    return 40.00


def get_tipo_cambio_eur():
    """Returns dict of rates relative to EUR (e.g. {'MXN': 20.5, ...})"""
    try:
        resp = requests.get('https://open.er-api.com/v6/latest/EUR', timeout=10)
        data = resp.json()
        return data.get('rates', {})
    except Exception:
        return {'MXN': 20.5, 'COP': 4400.0, 'ARS': 1050.0, 'CLP': 1000.0, 'PEN': 38.0}


def buscar_en_ml(ean, nombre='', site_id='MLM', delay=0.5):
    """
    Busca en MercadoLibre por EAN y, si no hay resultados, por nombre.
    Retorna (precio_local, moneda, link) o (None, None, None).
    """
    time.sleep(delay)
    try:
        # Intento 1: búsqueda por EAN
        url = f'https://api.mercadolibre.com/search?site_id={site_id}&q={ean}&limit=5'
        resp = requests.get(url, timeout=12)
        results = resp.json().get('results', []) if resp.status_code == 200 else []

        # Intento 2: búsqueda por nombre si EAN no dio resultado
        if not results and nombre:
            url2 = f'https://api.mercadolibre.com/search?site_id={site_id}&q={nombre[:80]}&limit=5'
            resp2 = requests.get(url2, timeout=12)
            if resp2.status_code == 200:
                results = resp2.json().get('results', [])

        if not results:
            return None, None, None

        item = results[0]
        precio = item.get('price')
        if not precio:
            return None, None, None

        return float(precio), item.get('currency_id'), item.get('permalink')

    except Exception:
        return None, None, None
