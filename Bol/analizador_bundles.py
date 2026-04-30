import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import os
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

from pathlib import Path
_DIR = Path(__file__).parent
ARCHIVO_LOCAL  = str(_DIR / 'product_2399_es.csv')
ARCHIVO_SALIDA = str(_DIR / 'propuestas_IA_TRANSPARENTE.xlsx')

def clasificar_bundle(row):
    ganancia = row['Ganancia_Neta']
    if ganancia > 10:
        return 'GANADOR'
    if ganancia > 5:
        return 'POTENCIAL'
    return 'MARGINAL'

def ejecutar_ia_transparente():
    if not os.path.exists(ARCHIVO_LOCAL):
        print("❌ Archivo no encontrado.")
        return

    print("--- 🧠 Motor IA: Filtrado de Volumen y Transparencia Financiera ---")

    try:
        df = pd.read_csv(ARCHIVO_LOCAL, sep=';', encoding='utf-8', low_memory=False)
        df.columns = [c.strip().lower() for c in df.columns]

        for col in ['pvd', 'stock', 'weight', 'width', 'height', 'depth']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df = df[(df['weight'] < 10) & (df['width'] < 60) & (df['height'] < 60)]
        df = df[df['stock'] > 15]

        # Pares de afinidad: (keywords producto estrella, keywords accesorio)
        PARES_AFINIDAD = [
            # Cocina
            (['fryer', 'cook', 'robot', 'oven', 'grill', 'blender', 'mixer', 'coffee', 'microwave', 'toaster'],
             ['mold', 'papel', 'guante', 'pinza', 'cuchillo', 'peeler', 'rallador', 'espatula', 'baking', 'silicona']),
            # Belleza / cuidado personal
            (['massage', 'sonic', 'facial', 'hair', 'nail', 'beauty', 'depiladora', 'epilator', 'secar', 'brush'],
             ['gel', 'aceite', 'crema', 'limpiador', 'serum', 'mask', 'algodon', 'esponja', 'cotton', 'cleanser']),
            # Electrónica / tech
            (['led', 'smart', 'watch', 'speaker', 'headphone', 'earphone', 'tablet', 'lamp', 'projector'],
             ['soporte', 'cable', 'funda', 'protector', 'cargador', 'hub', 'case', 'stand', 'holder']),
            # Fitness / deporte
            (['fitness', 'yoga', 'gym', 'sport', 'running', 'cycling', 'exercise', 'training', 'jump'],
             ['bottle', 'towel', 'bag', 'mat', 'band', 'glove', 'botella', 'toalla', 'mochila']),
            # Jardín / exterior
            (['garden', 'plant', 'outdoor', 'patio', 'terraza', 'jardin', 'cesped', 'irrigation'],
             ['tool', 'glove', 'watering', 'guante', 'herramienta', 'spray', 'pot', 'maceta']),
            # Limpieza del hogar
            (['vacuum', 'aspiradora', 'cleaner', 'mop', 'sweep', 'steamer'],
             ['bag', 'filter', 'brush', 'bolsa', 'filtro', 'cepillo', 'mop']),
            # Seguridad / vigilancia
            (['camera', 'alarm', 'sensor', 'vigilancia', 'security', 'doorbell'],
             ['mount', 'cable', 'battery', 'soporte', 'bateria', 'bracket', 'hub']),
            # Bebé / niños
            (['baby', 'bebe', 'nino', 'infant', 'child', 'kids'],
             ['toy', 'cream', 'wipe', 'juguete', 'crema', 'toalla', 'cotton']),
            # Mascotas
            (['pet', 'dog', 'cat', 'perro', 'gato', 'mascota'],
             ['toy', 'feed', 'brush', 'collar', 'juguete', 'cepillo', 'snack']),
            # Climatización
            (['fan', 'ventilador', 'heater', 'calefactor', 'humidifier', 'purifier', 'aire'],
             ['filter', 'filtro', 'timer', 'temporizador', 'cover', 'funda']),
        ]

        # Accesorios universales: combinan bien con casi cualquier producto
        KEYWORDS_UNIVERSAL = [
            'organizador', 'organizer', 'storage', 'bolsa', 'bag', 'light', 'luz',
            'timer', 'temporizador', 'soporte', 'stand', 'holder', 'rack',
        ]

        MAX_COMBOS = 4  # Máximo de accesorios por producto estrella

        keywords_fuerte = [
            'robot', 'smart', 'led', 'pro', 'fryer', 'massage', 'sonic', 'electric',
            'cook', 'oven', 'grill', 'blender', 'mixer', 'coffee', 'hair', 'nail',
            'beauty', 'fitness', 'yoga', 'vacuum', 'aspiradora', 'camera', 'speaker',
            'headphone', 'projector', 'fan', 'ventilador', 'heater', 'calefactor',
        ]
        estrellas = df[(df['pvd'] > 25) & (df['name'].str.contains('|'.join(keywords_fuerte), case=False))].copy()
        accesorios = df[(df['pvd'] < 15) & (df['pvd'] > 3)].copy()

        propuestas = []
        nombres_principal_es = []
        nombres_acc_es = []

        for _, est in estrellas.iterrows():
            combos = 0
            for _, acc in accesorios.iterrows():
                if combos >= MAX_COMBOS:
                    break

                n_est, n_acc = est['name'].lower(), acc['name'].lower()

                match = any(
                    any(x in n_est for x in kw_est) and any(y in n_acc for y in kw_acc)
                    for kw_est, kw_acc in PARES_AFINIDAD
                )
                if not match:
                    match = any(y in n_acc for y in KEYWORDS_UNIVERSAL)

                if match:
                    costo_pvd = est['pvd'] + acc['pvd']
                    envio = 8.50

                    # Ganancia objetivo según costo del bundle
                    if costo_pvd < 20:
                        ganancia_obj = 8.00
                    elif costo_pvd < 40:
                        ganancia_obj = 12.00
                    elif costo_pvd < 70:
                        ganancia_obj = 18.00
                    else:
                        ganancia_obj = 25.00

                    pvp_sin_iva = (costo_pvd + envio + ganancia_obj + 1) / 0.88
                    pvp_final = round(pvp_sin_iva * 1.21, 2)
                    comision = round((pvp_sin_iva * 0.12) + 1, 2)
                    iva_bundle = round(pvp_sin_iva * 0.21, 2)

                    pvp_min_sin_iva = (costo_pvd + envio + 1.00) / 0.88
                    precio_minimo = round(pvp_min_sin_iva * 1.21, 2)
                    total_gastos = round(costo_pvd + envio + comision + iva_bundle, 2)

                    nombres_principal_es.append(est['name'])
                    nombres_acc_es.append(acc['name'])
                    propuestas.append({
                        'Pack': f"{est['name']} + {acc['name']}",
                        'ID_Principal': est['id'],
                        'EAN_Principal': est['ean13'],
                        'Link_Principal_Bol': f"https://www.bol.com/nl/s/?searchtext={est['ean13']}",
                        'ID_Acc': acc['id'],
                        'EAN_Acc': acc['ean13'],
                        'Link_Acc_Bol': f"https://www.bol.com/nl/s/?searchtext={acc['ean13']}",
                        'PVD_Pack': round(costo_pvd, 2),
                        'Envio_Est': envio,
                        'Comision_Bol': comision,
                        'Total_Gastos': total_gastos,
                        'Precio_Minimo_Venta': precio_minimo,
                        'PVP_Bol_Final': pvp_final,
                        'Ganancia_Neta': ganancia_obj,
                        'Peso_Total_Kg': round(est['weight'] + acc['weight'], 2),
                        'Imagen1': est['image1'] if pd.notna(est['image1']) else '',
                        'Imagen2': est['image2'] if pd.notna(est['image2']) else '',
                        'Imagen3': est['image3'] if pd.notna(est['image3']) else '',
                        'Imagen4': est['image4'] if pd.notna(est['image4']) else '',
                    })
                    combos += 1

        if not propuestas:
            print("⚠️ No hubo matches con estos filtros. Intentá bajando el PVD de estrellas.")
            return

        df_final = pd.DataFrame(propuestas)
        df_final['Estado'] = df_final.apply(clasificar_bundle, axis=1)

        # Traducción al holandés usando las listas recolectadas en el loop
        print("🌐 Traduciendo nombres al holandés...")
        nombres_nl_principal = traducir_nl(nombres_principal_es)
        nombres_nl_acc       = traducir_nl(nombres_acc_es)
        df_final.insert(
            df_final.columns.get_loc('Pack') + 1,
            'Pack_NL',
            [f"{p} + {a}" for p, a in zip(nombres_nl_principal, nombres_nl_acc)]
        )

        cols = ['Estado'] + [c for c in df_final.columns if c != 'Estado']
        df_final = df_final[cols]

        orden = {'GANADOR': 0, 'POTENCIAL': 1, 'MARGINAL': 2}
        df_final['_orden'] = df_final['Estado'].map(orden)
        df_final = df_final.sort_values('_orden').drop(columns='_orden').reset_index(drop=True)

        with pd.ExcelWriter(ARCHIVO_SALIDA, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Bundles')
            colorear_excel(writer.sheets['Bundles'], df_final)
            agregar_leyenda(writer.book)

        print(f"✅ ¡LISTO! Excel generado en: {ARCHIVO_SALIDA}")
        print(f"   🟢 GANADORES:  {(df_final['Estado'] == 'GANADOR').sum()}")
        print(f"   🟡 POTENCIAL:  {(df_final['Estado'] == 'POTENCIAL').sum()}")
        print(f"   🔴 MARGINAL:   {(df_final['Estado'] == 'MARGINAL').sum()}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    ejecutar_ia_transparente()
