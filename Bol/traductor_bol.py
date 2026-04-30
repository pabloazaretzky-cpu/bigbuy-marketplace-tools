def optimizar_para_bol(nombre_pack):
    # Diccionario de traducción estratégica
    traducciones = {
        "kit saludable": "Gezonde Keuken Set",
        "airfryer": "Heteluchtfriteuse",
        "licuadora": "Blender",
        "pulverizador de aceite": "Oliesproeier",
        "accesorios": "Accessoires"
    }
    
    nombre_nl = nombre_pack.lower()
    for es, nl in traducciones.items():
        nombre_nl = nombre_nl.replace(es, nl)
        
    return nombre_nl.title()

# Prueba rápida
print(f"Original: KIT SALUDABLE: Airfryer + Pulverizador")
print(f"Bol.com: {optimizar_para_bol('KIT SALUDABLE: Airfryer + Pulverizador')}")