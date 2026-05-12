# Notas — Carpeta MercadoLibre

## Archivos

| Archivo | Rol |
|---|---|
| `ml_api.py` | Librería de utilidades — no se corre directamente |
| `excel_colores.py` | Librería de formato Excel — no se corre directamente |
| `analizar_ml_global.py` | El único script que se ejecuta |

---

## Qué hace `analizar_ml_global.py`

1. Lee el CSV de BigBuy (`Bol/product_2399_es.csv`) — depende de que el catálogo esté descargado primero
2. Filtra productos europeos: stock ≥10, PVD ≥€10, peso ≤3kg, dimensiones <60cm — descarta marcas asiáticas (Samsung, Xiaomi, Apple, etc.)
3. Consulta la API pública de MercadoLibre por EAN, buscando precio actual en México (configurable a Colombia, Argentina, Chile, Perú)
4. Calcula rentabilidad: precio mínimo, margen neto, comisión ML (17% total = 15% comisión + 2% conversión de moneda)
5. Genera Excel `analisis_ml_global.xlsx` con precios en MXN y EUR, margen neto y links

---

## Orden correcto de ejecución

```
1. python Bol/descargar_catalogo.py           ← PRIMERO siempre (baja el CSV de BigBuy)
2. python MercadoLibre/analizar_ml_global.py  ← usa ese CSV
```

Los scripts de Bol (analizar_novedades, analizador_bundles, etc.) también dependen del paso 1
pero son independientes entre sí.

---

## Parámetros clave (analizar_ml_global.py)

| Variable | Valor actual | Descripción |
|---|---|---|
| `PAIS_COMPARACION` | `'mexico'` | País donde se buscan precios en ML (mexico/colombia/argentina/chile/peru) |
| `LIMITE_CONSULTA_ML` | `300` | Máx productos a consultar — a 0.5 seg c/u son ~2.5 min |
| `COMISION_ML_TOTAL` | `0.17` | 15% comisión ML + 2% conversión de moneda |
| `GANANCIA_OBJETIVO` | `€12` | Ganancia neta mínima para calcular precio objetivo |
| `MAX_PESO_KG` | `3.0` | Límite de peso para que el envío internacional sea rentable |
| `MIN_PVD` | `€10` | Precio de compra mínimo (filtra productos demasiado baratos) |

---

## Clasificación del Excel resultante

| Color | Estado | Criterio |
|---|---|---|
| Verde | GANADOR | Margen neto > €15 |
| Amarillo | POTENCIAL | Margen neto €5–€15 |
| Rojo | MARGINAL | Margen < €5 o negativo |
| Gris | SIN_DATOS | No se encontró el producto en ML |

---

## Advertencia

Los productos que superen el límite de 300 consultas quedan como SIN_DATOS
sin haber sido buscados en ML. Si el catálogo filtrado es grande, subir
LIMITE_CONSULTA_ML o acotar más los filtros de peso/precio.
