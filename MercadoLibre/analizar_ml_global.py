import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import os
from pathlib import Path
from ml_api import (
    calcular_envio_ml, es_marca_eu, clasificar_origen_eu,
    get_tipo_cambio_eur, buscar_en_ml, ML_SITES
)
from excel_colores import colorear_excel, agregar_leyenda

# ── Configuración ──────────────────────────────────────────────────────────────
_DIR = Path(__file__).parent
ARCHIVO_CSV    = str(_DIR.parent / 'Bol' / 'product_2399_es.csv')
ARCHIVO_SALIDA = str(_DIR / 'analisis_ml_global.xlsx')

COMISION_ML_TOTAL  = 0.17   # 15% comisión ML + ~2% conversión de moneda
GANANCIA_OBJETIVO  = 12.00  # EUR de ganancia neta deseada por unidad
PAIS_COMPARACION   = 'mexico'  # mexico | colombia | argentina | chile | peru
LIMITE_CONSULTA_ML = 300    # productos a consultar en ML (~0.5 seg c/u)

MAX_PESO_KG = 3.0
MIN_STOCK   = 10
MIN_PVD     = 10.0

MONEDA_PAIS = {
    'mexico': 'MXN', 'colombia': 'COP', 'argentina': 'ARS',
    'chile': 'CLP',  'peru': 'PEN',
}


def clasificar(row):
    m = row.get('Margen_Neto_EUR')
    if pd.isna(m) or m is None:
        return 'SIN_DATOS'
    if m > 15: return 'GANADOR'
    if m > 5:  return 'POTENCIAL'
    return 'MARGINAL'


def ejecutar_analisis():
    if not os.path.exists(ARCHIVO_CSV):
        print(f"❌ No se encuentra: {ARCHIVO_CSV}")
        return

    print("--- 🌎 Análisis ML Global Selling ---")
    print(f"País: {PAIS_COMPARACION.upper()}")

    # ── Tipo de cambio ─────────────────────────────────────────────────────────
    print("💱 Obteniendo tipo de cambio...")
    tasas       = get_tipo_cambio_eur()
    moneda      = MONEDA_PAIS[PAIS_COMPARACION]
    tipo_cambio = tasas.get(moneda, 20.5)
    print(f"   1 EUR = {tipo_cambio:.2f} {moneda}")

    # ── Cargar y filtrar CSV ───────────────────────────────────────────────────
    df = pd.read_csv(ARCHIVO_CSV, sep=';', encoding='utf-8', low_memory=False)
    df.columns = [c.strip().lower() for c in df.columns]

    for col in ['pvd', 'stock', 'weight', 'width', 'height', 'depth']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df = df[
        (df['stock'] >= MIN_STOCK) &
        (df['pvd']   >= MIN_PVD)   &
        (df['weight'] > 0)         &
        (df['weight'] <= MAX_PESO_KG) &
        (df['width']  < 60) &
        (df['height'] < 60)
    ].copy()

    # Filtrar marcas no europeas
    df = df[df['brand'].apply(es_marca_eu)].copy()

    # Clasificar origen EU — prioriza marcas/productos típicamente europeos
    df['_origen'] = df.apply(
        lambda r: clasificar_origen_eu(r['name'], r.get('brand', '')), axis=1
    )

    # Ordenar: Marca EU primero, luego Tipico EU, luego genéricos
    orden_origen = {'Marca EU': 0, 'Tipico EU': 1, '': 2}
    df['_ord_origen'] = df['_origen'].map(orden_origen)
    df = df.sort_values(['_ord_origen', 'pvd'], ascending=[True, False]).drop(columns='_ord_origen')

    n_marca_eu  = (df['_origen'] == 'Marca EU').sum()
    n_tipico_eu = (df['_origen'] == 'Tipico EU').sum()
    n_genericos = (df['_origen'] == '').sum()
    print(f"📦 Productos elegibles: {len(df)} total")
    print(f"   ⭐ Marca EU confirmada: {n_marca_eu}")
    print(f"   🇪🇺 Típico europeo:      {n_tipico_eu}")
    print(f"   📦 Genéricos EU:         {n_genericos}")

    site_id        = ML_SITES[PAIS_COMPARACION]
    consultar_hasta = min(len(df), LIMITE_CONSULTA_ML)
    print(f"🔍 Consultando {consultar_hasta} productos en ML {PAIS_COMPARACION.capitalize()}...")

    resultados = []

    for i, (_, item) in enumerate(df.iterrows()):
        pvd   = item['pvd']
        peso  = item['weight']
        brand = str(item.get('brand', '')).strip()

        envio_ml = calcular_envio_ml(peso)

        # Precio mínimo (breakeven) y precio objetivo — siempre en EUR
        precio_min_eur = round((pvd + envio_ml) / (1 - COMISION_ML_TOTAL), 2)
        precio_obj_eur = round((pvd + envio_ml + GANANCIA_OBJETIVO) / (1 - COMISION_ML_TOTAL), 2)

        # En moneda local
        precio_min_local = round(precio_min_eur * tipo_cambio, 0)
        precio_obj_local = round(precio_obj_eur * tipo_cambio, 0)

        # Comisión y gastos al precio objetivo
        comision_obj = round(precio_obj_eur * COMISION_ML_TOTAL, 2)
        total_gastos = round(pvd + envio_ml + comision_obj, 2)

        # ── Consulta ML ───────────────────────────────────────────────────────
        precio_ml_local = None
        precio_ml_eur   = None
        margen_neto     = None
        link_ml         = None

        if i < consultar_hasta:
            ean = str(item['ean13']).strip()
            p_local, _, link = buscar_en_ml(ean, item['name'], site_id)

            if p_local:
                precio_ml_local = round(p_local, 2)
                precio_ml_eur   = round(p_local / tipo_cambio, 2)
                seller_net_eur  = round(p_local * (1 - COMISION_ML_TOTAL) / tipo_cambio, 2)
                margen_neto     = round(seller_net_eur - pvd - envio_ml, 2)
                link_ml         = link

            if (i + 1) % 20 == 0:
                print(f"  → {i + 1}/{consultar_hasta} consultados...")

        resultados.append({
            'Estado':                  '',  # se rellena después
            'Origen_EU':               item['_origen'],
            'Marca':                   brand,
            'Nombre':                  item['name'],
            'EAN':                     item['ean13'],
            'ID_BigBuy':               item['id'],
            'Stock':                   int(item['stock']),
            'Peso_kg':                 peso,
            'Costo_PVD_EUR':           round(pvd, 2),
            'Envio_ML_EUR':            envio_ml,
            'Comision_ML_EUR':         comision_obj,
            'Total_Gastos_EUR':        total_gastos,
            # Precios de referencia en EUR — siempre calculados
            'Precio_Min_EUR':          precio_min_eur,
            'Precio_Obj_EUR':          precio_obj_eur,
            # Precios en moneda local
            f'Precio_Min_{moneda}':    precio_min_local,
            f'Precio_Obj_{moneda}':    precio_obj_local,
            # Datos de ML (solo si se encontró el producto)
            f'Precio_ML_{moneda}':     precio_ml_local,
            'Precio_ML_EUR':           precio_ml_eur,
            'Margen_Neto_EUR':         margen_neto,
            'Link_ML':                 link_ml,
            'Imagen1': item['image1'] if pd.notna(item.get('image1')) else '',
            'Imagen2': item['image2'] if pd.notna(item.get('image2')) else '',
            'Imagen3': item['image3'] if pd.notna(item.get('image3')) else '',
            'Imagen4': item['image4'] if pd.notna(item.get('image4')) else '',
        })

    if not resultados:
        print("⚠️ Sin resultados.")
        return

    df_final = pd.DataFrame(resultados)
    df_final['Estado'] = df_final.apply(clasificar, axis=1)

    # Reordenar columnas: Estado primero
    cols = ['Estado'] + [c for c in df_final.columns if c != 'Estado']
    df_final = df_final[cols]

    # Ordenar: por Estado, luego Origen_EU (marcas EU primero), luego margen desc
    orden_estado  = {'GANADOR': 0, 'POTENCIAL': 1, 'MARGINAL': 2, 'SIN_DATOS': 3}
    orden_origen2 = {'Marca EU': 0, 'Tipico EU': 1, '': 2}
    df_final['_oe'] = df_final['Estado'].map(orden_estado)
    df_final['_oo'] = df_final['Origen_EU'].map(orden_origen2)
    df_final = (df_final
                .sort_values(['_oe', '_oo', 'Margen_Neto_EUR'], ascending=[True, True, False])
                .drop(columns=['_oe', '_oo'])
                .reset_index(drop=True))

    with pd.ExcelWriter(ARCHIVO_SALIDA, engine='openpyxl') as writer:
        df_final.to_excel(writer, index=False, sheet_name='ML_Global')
        colorear_excel(writer.sheets['ML_Global'], df_final)
        agregar_leyenda(writer.book)

    g  = (df_final['Estado'] == 'GANADOR').sum()
    p  = (df_final['Estado'] == 'POTENCIAL').sum()
    m  = (df_final['Estado'] == 'MARGINAL').sum()
    sd = (df_final['Estado'] == 'SIN_DATOS').sum()

    print(f"\n✅ Excel generado: {ARCHIVO_SALIDA}")
    print(f"   🟢 GANADORES:       {g}")
    print(f"   🟡 POTENCIAL:       {p}")
    print(f"   🔴 MARGINAL:        {m}")
    print(f"   ⚪ SIN DATOS ML:    {sd}  ← precio_obj_eur siempre disponible como referencia")
    print(f"   💱 1 EUR = {tipo_cambio:.2f} {moneda}")
    print(f"\n💡 Precio_Min_EUR y Precio_Obj_EUR están en todas las filas.")
    print(f"   Precio_ML_EUR solo aparece cuando ML encontró el producto.")


if __name__ == "__main__":
    ejecutar_analisis()
