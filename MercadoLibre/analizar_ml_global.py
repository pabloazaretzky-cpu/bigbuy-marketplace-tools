import pandas as pd
import os
import sys
from ml_api import (
    calcular_envio_ml, es_marca_eu, get_tipo_cambio_eur, buscar_en_ml, ML_SITES
)
from excel_colores import colorear_excel, agregar_leyenda

# --- CONFIGURACIÓN ---
from pathlib import Path
_DIR = Path(__file__).parent
ARCHIVO_CSV    = str(_DIR.parent / 'Bol' / 'product_2399_es.csv')
ARCHIVO_SALIDA = str(_DIR / 'analisis_ml_global.xlsx')

# Comisión ML + spread de conversión de moneda (~2%)
COMISION_ML_TOTAL = 0.17  # 15% comisión + ~2% conversión

# Ganancia mínima que queremos en euros
GANANCIA_OBJETIVO = 12.00

# País principal para comparar precios
PAIS_COMPARACION = 'mexico'  # opciones: mexico, colombia, argentina, chile, peru

# Límite de productos a consultar en ML (cada uno tarda ~0.5 seg)
LIMITE_CONSULTA_ML = 300

# Filtros de producto
MAX_PESO_KG   = 3.0   # Máx peso para que el envío internacional sea rentable
MIN_STOCK     = 10
MIN_PVD       = 10.0

def clasificar(row):
    m = row.get('Margen_Neto_EUR')
    if pd.isna(m):
        return 'SIN_DATOS'
    if m > 15:
        return 'GANADOR'
    if m > 5:
        return 'POTENCIAL'
    return 'MARGINAL'

def ejecutar_analisis():
    if not os.path.exists(ARCHIVO_CSV):
        print(f"❌ No se encuentra: {ARCHIVO_CSV}")
        return

    print("--- 🌎 Análisis ML Global Selling ---")
    print(f"País de comparación: {PAIS_COMPARACION.upper()}")

    # Tipo de cambio
    print("💱 Obteniendo tipo de cambio...")
    tasas = get_tipo_cambio_eur()
    moneda_pais = {'mexico': 'MXN', 'colombia': 'COP', 'argentina': 'ARS',
                   'chile': 'CLP', 'peru': 'PEN'}[PAIS_COMPARACION]
    tipo_cambio = tasas.get(moneda_pais, 20.5)
    print(f"   1 EUR = {tipo_cambio:.2f} {moneda_pais}")

    # Cargar CSV
    df = pd.read_csv(ARCHIVO_CSV, sep=';', encoding='utf-8', low_memory=False)
    df.columns = [c.strip().lower() for c in df.columns]

    for col in ['pvd', 'stock', 'weight', 'width', 'height', 'depth']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Filtros base
    df = df[
        (df['stock'] >= MIN_STOCK) &
        (df['pvd'] >= MIN_PVD) &
        (df['weight'] > 0) &
        (df['weight'] <= MAX_PESO_KG) &
        (df['width'] < 60) &
        (df['height'] < 60)
    ].copy()

    # Filtro origen europeo
    df['origen_eu'] = df['brand'].apply(es_marca_eu)
    df = df[df['origen_eu']].copy()

    print(f"📦 Productos europeos elegibles tras filtros: {len(df)}")

    site_id = ML_SITES[PAIS_COMPARACION]
    consultar_hasta = min(len(df), LIMITE_CONSULTA_ML)
    print(f"🔍 Consultando ML {PAIS_COMPARACION.capitalize()} para {consultar_hasta} productos (~{consultar_hasta // 2} seg)...")

    resultados = []

    for i, (_, item) in enumerate(df.iterrows()):
        pvd    = item['pvd']
        peso   = item['weight']
        brand  = str(item.get('brand', '')).strip()

        envio_ml = calcular_envio_ml(peso)

        # Precio mínimo para no perder dinero (en EUR)
        # seller_net = precio_venta * (1 - COMISION_ML_TOTAL)
        # seller_net >= pvd + envio_ml  →  precio_min_eur = (pvd + envio_ml) / (1 - comision)
        precio_min_eur = round((pvd + envio_ml) / (1 - COMISION_ML_TOTAL), 2)

        # Precio objetivo (con ganancia deseada)
        precio_obj_eur = round((pvd + envio_ml + GANANCIA_OBJETIVO) / (1 - COMISION_ML_TOTAL), 2)

        # Total gastos reales (PVD + envío + comisión al precio objetivo)
        comision_en_obj = round(precio_obj_eur * COMISION_ML_TOTAL, 2)
        total_gastos    = round(pvd + envio_ml + comision_en_obj, 2)

        # Precios mínimos en moneda local
        precio_min_local = round(precio_min_eur * tipo_cambio, 0)
        precio_obj_local = round(precio_obj_eur * tipo_cambio, 0)

        # Consultar ML
        precio_ml_local = None
        precio_ml_eur   = None
        margen_neto     = None
        link_ml         = None

        if i < consultar_hasta:
            ean = str(item['ean13']).strip()
            p_local, moneda, link = buscar_en_ml(ean, item['name'], site_id)
            if p_local:
                precio_ml_local = p_local
                precio_ml_eur   = round(p_local / tipo_cambio, 2)
                # Cuánto recibe el vendedor después de comisión ML
                seller_net_eur  = round(p_local * (1 - COMISION_ML_TOTAL) / tipo_cambio, 2)
                margen_neto     = round(seller_net_eur - pvd - envio_ml, 2)
                link_ml         = link

            if (i + 1) % 20 == 0:
                print(f"  → {i + 1}/{consultar_hasta} consultados...")

        resultados.append({
            'ID':                item['id'],
            'EAN':               item['ean13'],
            'Marca':             brand,
            'Nombre':            item['name'],
            'Stock':             int(item['stock']),
            'Peso_kg':           peso,
            'Costo_PVD_EUR':     round(pvd, 2),
            'Envio_ML_EUR':      envio_ml,
            'Comision_ML_EUR':   comision_en_obj,
            'Total_Gastos_EUR':  total_gastos,
            'Precio_Min_EUR':    precio_min_eur,
            f'Precio_Min_{moneda_pais}': precio_min_local,
            f'Precio_Obj_{moneda_pais}': precio_obj_local,
            f'Precio_ML_{moneda_pais}':  precio_ml_local,
            'Precio_ML_EUR':     precio_ml_eur,
            'Margen_Neto_EUR':   margen_neto,
            'Link_ML':           link_ml,
            'Imagen1':           item['image1'] if pd.notna(item['image1']) else '',
            'Imagen2':           item['image2'] if pd.notna(item['image2']) else '',
            'Imagen3':           item['image3'] if pd.notna(item['image3']) else '',
            'Imagen4':           item['image4'] if pd.notna(item['image4']) else '',
        })

    if not resultados:
        print("⚠️ No se encontraron productos que cumplan los criterios.")
        return

    df_final = pd.DataFrame(resultados)
    df_final['Estado'] = df_final.apply(clasificar, axis=1)

    cols = ['Estado'] + [c for c in df_final.columns if c != 'Estado']
    df_final = df_final[cols]

    orden = {'GANADOR': 0, 'POTENCIAL': 1, 'MARGINAL': 2, 'SIN_DATOS': 3}
    df_final['_orden'] = df_final['Estado'].map(orden)
    df_final = df_final.sort_values('_orden').drop(columns='_orden').reset_index(drop=True)

    with pd.ExcelWriter(ARCHIVO_SALIDA, engine='openpyxl') as writer:
        df_final.to_excel(writer, index=False, sheet_name='ML_Global')
        colorear_excel(writer.sheets['ML_Global'], df_final)
        agregar_leyenda(writer.book)

    print(f"\n✅ Excel generado: {ARCHIVO_SALIDA}")
    print(f"   🟢 GANADORES:  {(df_final['Estado'] == 'GANADOR').sum()}")
    print(f"   🟡 POTENCIAL:  {(df_final['Estado'] == 'POTENCIAL').sum()}")
    print(f"   🔴 MARGINAL:   {(df_final['Estado'] == 'MARGINAL').sum()}")
    print(f"   ⚪ SIN DATOS:  {(df_final['Estado'] == 'SIN_DATOS').sum()}")
    print(f"   💱 Tipo de cambio usado: 1 EUR = {tipo_cambio:.2f} {moneda_pais}")

if __name__ == "__main__":
    ejecutar_analisis()
