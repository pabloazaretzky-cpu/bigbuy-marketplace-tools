import pandas as pd
import os
import urllib.parse
from bol_scraper import buscar_en_bol
from excel_colores import colorear_excel, agregar_leyenda
from deep_translator import GoogleTranslator

def traducir_nl(nombres, chunk_size=40):
    """Translates a list of Spanish product names to Dutch using chunked requests."""
    translator = GoogleTranslator(source='es', target='nl')
    result = []
    for i in range(0, len(nombres), chunk_size):
        chunk = nombres[i:i + chunk_size]
        try:
            traducido = translator.translate('\n'.join(chunk))
            partes = traducido.split('\n')
            result.extend(partes if len(partes) == len(chunk) else chunk)
        except Exception:
            result.extend(chunk)
    return result

# --- CONFIGURACIÓN ---
ARCHIVO_LOCAL = "C:/Users/Admin/Python/Bol/product_2399_es.csv"
ARCHIVO_SALIDA = "C:/Users/Admin/Python/Bol/NOVEDADES_rentables_bol.xlsx"

# Poner en True para consultar precios reales en Bol.com (~2 seg por producto)
COMPARAR_BOL = True
LIMITE_COMPARACION = 300

def clasificar(row):
    if pd.notna(row.get('Margen_vs_Mercado')):
        m = row['Margen_vs_Mercado']
        return 'GANADOR' if m > 10 else ('POTENCIAL' if m > 0 else 'MARGINAL')
    g = row['Ganancia_Neta']
    return 'GANADOR' if g >= 18 else ('POTENCIAL' if g >= 12 else 'MARGINAL')

def ejecutar_analisis_novedades():
    if not os.path.exists(ARCHIVO_LOCAL):
        print(f"❌ No se encuentra el archivo en: {ARCHIVO_LOCAL}")
        return

    print("--- 🚀 Analizando NOVEDADES de BigBuy ---")

    try:
        df = pd.read_csv(ARCHIVO_LOCAL, sep=';', encoding='utf-8', low_memory=False)
        df.columns = [c.strip().lower() for c in df.columns]

        df['id_num'] = pd.to_numeric(df['id'].astype(str).str.extract('(\d+)', expand=False), errors='coerce')

        for col in ['pvd', 'stock', 'weight']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df_novedades = df[(df['stock'] > 30) & (df['pvd'] > 15)].sort_values(by='id_num', ascending=False)
        df_top = df_novedades.head(1000)

        total = len(df_top)
        comparar_hasta = min(total, LIMITE_COMPARACION) if COMPARAR_BOL else 0

        if COMPARAR_BOL:
            print(f"🔍 Consultando precios en Bol.com para los primeros {comparar_hasta} productos (~{comparar_hasta * 2 // 60} min)...")

        resultados = []

        for i, (_, item) in enumerate(df_top.iterrows()):
            pvd = item['pvd']

            ganancia = 5.00 if pvd < 25 else (12.00 if pvd < 60 else 18.00)
            envio = 5.95 if item['weight'] < 2 else (8.50 if item['weight'] < 10 else 14.00)

            pvp_sin_iva = (pvd + envio + ganancia + 1.00) / 0.88
            precio_final = round(pvp_sin_iva * 1.21, 2)
            comision_bol = round((pvp_sin_iva * 0.12) + 1.00, 2)
            iva_btw = round(precio_final - pvp_sin_iva, 2)

            pvp_min_sin_iva = (pvd + envio + 1.00) / 0.88
            precio_minimo = round(pvp_min_sin_iva * 1.21, 2)
            total_gastos = round(pvd + envio + comision_bol + iva_btw, 2)

            if COMPARAR_BOL and i < comparar_hasta:
                ean = str(item['ean13']).strip()
                precio_bol, link_bol = buscar_en_bol(ean)
                if (i + 1) % 10 == 0:
                    print(f"  → {i + 1}/{comparar_hasta} consultados...")
            else:
                precio_bol = None
                query = urllib.parse.quote(f"{item['id']} {item['name']}")
                link_bol = f"https://www.bol.com/nl/s/?searchtext={query}"

            margen_vs_mercado = round(precio_bol - precio_minimo, 2) if precio_bol else None

            resultados.append({
                'ID_Novedad': item['id'],
                'EAN': item['ean13'],
                'Nombre': item['name'],
                'Stock': item['stock'],
                'Costo_PVD': round(pvd, 2),
                'Envio': envio,
                'Comision_Bol': comision_bol,
                'IVA_21': iva_btw,
                'Total_Gastos': total_gastos,
                'Precio_Minimo_Venta': precio_minimo,
                'Ganancia_Neta': ganancia,
                'PVP_Bol_Sugerido': precio_final,
                'Precio_Actual_Bol': precio_bol,
                'Margen_vs_Mercado': margen_vs_mercado,
                'Link_Bol': link_bol,
                'Imagen1': item['image1'] if pd.notna(item['image1']) else '',
                'Imagen2': item['image2'] if pd.notna(item['image2']) else '',
                'Imagen3': item['image3'] if pd.notna(item['image3']) else '',
                'Imagen4': item['image4'] if pd.notna(item['image4']) else '',
            })

        if not resultados:
            print("⚠️ No se encontraron novedades que cumplan los requisitos.")
            return

        df_final = pd.DataFrame(resultados)
        df_final['Estado'] = df_final.apply(clasificar, axis=1)

        # Traducción al holandés
        print("🌐 Traduciendo nombres al holandés...")
        df_final.insert(
            df_final.columns.get_loc('Nombre') + 1,
            'Nombre_NL',
            traducir_nl(df_final['Nombre'].tolist())
        )

        # Actualizar links de búsqueda para usar el nombre en holandés
        # Los links directos al producto (con /p/) se mantienen intactos
        df_final['Link_Bol'] = df_final.apply(
            lambda row: row['Link_Bol'] if '/p/' in str(row['Link_Bol'])
            else f"https://www.bol.com/nl/s/?searchtext={urllib.parse.quote(str(row['Nombre_NL']))}",
            axis=1
        )

        # Estado como primera columna
        cols = ['Estado'] + [c for c in df_final.columns if c != 'Estado']
        df_final = df_final[cols]

        # Ordenar: GANADOR primero, luego POTENCIAL, luego MARGINAL
        orden = {'GANADOR': 0, 'POTENCIAL': 1, 'MARGINAL': 2}
        df_final['_orden'] = df_final['Estado'].map(orden)
        df_final = df_final.sort_values('_orden').drop(columns='_orden').reset_index(drop=True)

        with pd.ExcelWriter(ARCHIVO_SALIDA, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Novedades')
            colorear_excel(writer.sheets['Novedades'], df_final)
            agregar_leyenda(writer.book)

        print(f"✅ ¡Éxito! Excel generado en: {ARCHIVO_SALIDA}")
        print(f"   🟢 GANADORES:  {(df_final['Estado'] == 'GANADOR').sum()}")
        print(f"   🟡 POTENCIAL:  {(df_final['Estado'] == 'POTENCIAL').sum()}")
        print(f"   🔴 MARGINAL:   {(df_final['Estado'] == 'MARGINAL').sum()}")
        if COMPARAR_BOL:
            encontrados = df_final['Precio_Actual_Bol'].notna().sum()
            print(f"   📊 Precios encontrados en Bol: {encontrados}/{comparar_hasta}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    ejecutar_analisis_novedades()
