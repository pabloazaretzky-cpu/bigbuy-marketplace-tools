def calcular_envio_es_nl(peso_kg, width=0, height=0, depth=0):
    """
    Shipping cost from BigBuy Valencia, Spain to Netherlands.
    Uses billable weight = max(actual weight, volumetric weight).
    Volumetric weight = (cm³) / 5000 — standard carrier formula.
    """
    vol_weight = (width * height * depth) / 5000 if width and height and depth else 0
    peso_facturable = max(peso_kg, vol_weight)

    if peso_facturable <= 0.5:  return 5.50
    if peso_facturable <= 1.0:  return 7.50
    if peso_facturable <= 2.0:  return 9.50
    if peso_facturable <= 3.0:  return 11.50
    if peso_facturable <= 5.0:  return 14.00
    if peso_facturable <= 10.0: return 19.00
    return 28.00
