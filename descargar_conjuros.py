import os
import requests
import zipfile
import re
import time
from deep_translator import GoogleTranslator

# URL del JSON comunitario con los conjuros del SRD 5.2 (2024)
URL_CONJUROS = "https://gist.githubusercontent.com/dmcb/4b67869f962e3adaa3d0f7e5ca8f4912/raw/"

DIRECTORIO_SALIDA = "spells"

# Diccionario forzado para escuelas (para asegurar terminología D&D)
ESCUELAS = {
    "abjuration": "Abjuración", "conjuration": "Conjuración", "divination": "Adivinación",
    "enchantment": "Encantamiento", "evocation": "Evocación", "illusion": "Ilusión",
    "necromancy": "Nigromancia", "transmutation": "Transmutación"
}

# Iniciamos el traductor
traductor = GoogleTranslator(source='en', target='es')

def corregir_terminologia(texto):
    """
    Arregla traducciones literales para que suenen a D&D.
    """
    if not texto: return ""
    t = texto
    # Correcciones comunes de la traducción automática
    t = t.replace("Tirada de salvación de destreza", "Tirada de salvación de Destreza")
    t = t.replace("espacio de hechizo", "espacio de conjuro")
    t = t.replace("spell slot", "espacio de conjuro")
    t = t.replace("hit points", "puntos de golpe")
    t = t.replace("puntos de vida", "puntos de golpe")
    t = t.replace("saving throw", "tirada de salvación")
    t = t.replace("attack roll", "tirada de ataque")
    t = t.replace("Action", "Acción").replace("Bonus Action", "Acción Adicional").replace("Reaction", "Reacción")
    t = t.replace("Instantaneous", "Instantánea").replace("Concentration", "Concentración")
    t = t.replace("Self", "Personal").replace("Touch", "Toque")
    return t

def traducir_bloque(texto):
    if not texto: return ""
    try:
        # Traducimos
        trad = traductor.translate(texto)
        # Corregimos términos de juego
        return corregir_terminologia(trad)
    except Exception as e:
        print(f"Advertencia: No se pudo traducir un bloque. {e}")
        return texto # Si falla, devuelve el original en inglés

def limpiar_nombre_archivo(nombre):
    s = nombre.lower().replace(" ", "_").replace("/", "_").replace("'", "")
    return re.sub(r'[^a-z0-9_]', '', s)

def generar_conjuros():
    print(f"📥 Descargando lista de conjuros SRD 5.2...")
    try:
        r = requests.get(URL_CONJUROS)
        r.raise_for_status()
        conjuros = r.json()
    except Exception as e:
        print(f"Error descargando: {e}")
        return

    if not os.path.exists(DIRECTORIO_SALIDA):
        os.makedirs(DIRECTORIO_SALIDA)

    total = len(conjuros)
    print(f"✨ Procesando y traduciendo {total} conjuros. Esto tomará unos minutos...")

    files_created = []

    for i, c in enumerate(conjuros):
        # Datos básicos
        nombre_original = c.get('name', 'Desconocido')
        print(f"[{i+1}/{total}] Traduciendo: {nombre_original}...")
        
        # TRADUCCIÓN DEL NOMBRE Y DESCRIPCIÓN
        nombre_es = traducir_bloque(nombre_original)
        
        # Preparar descripción completa para traducir
        desc_raw = c.get('description', '')
        if c.get('cantripUpgrade'):
            desc_raw += f"\n\n**A Niveles Superiores:** {c.get('cantripUpgrade')}"
        if c.get('higherLevelDescription'):
             desc_raw += f"\n\n**A Niveles Superiores:** {c.get('higherLevelDescription')}"
        
        descripcion_es = traducir_bloque(desc_raw)

        # Traducir otros campos
        nivel = "Truco" if c.get('level', 0) == 0 else f"Nivel {c.get('level')}"
        escuela = ESCUELAS.get(c.get('school', '').lower(), c.get('school', '').title())
        tiempo = traducir_bloque(c.get('castingTime', ''))
        alcance = traducir_bloque(c.get('range', ''))
        duracion = traducir_bloque(c.get('duration', ''))
        
        # Componentes (V, S, M...) no necesitan mucha traducción, solo formato
        comps_raw = c.get('components', [])
        componentes = ", ".join([x.upper() for x in comps_raw]) if isinstance(comps_raw, list) else str(comps_raw)

        # Generar nombre de archivo (usamos el nombre en español para el archivo)
        slug = limpiar_nombre_archivo(nombre_es)
        filename = f"{slug}.md"
        filepath = os.path.join(DIRECTORIO_SALIDA, filename)

        # Crear contenido Markdown
        md_content = f"""---
nombre: "{nombre_es}"
level: "{nivel}"
school: "{escuela}"
tiempo: "{tiempo}"
alcance: "{alcance}"
componentes: "{componentes}"
duracion: "{duracion}"
---

### Descripción
{descripcion_es}
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        files_created.append(filepath)
        
        # IMPORTANTE: Pausa pequeña para no saturar el servicio de traducción
        # Si da error de "Too many requests", aumenta este número a 1.0
        time.sleep(0.2) 

    print(f"✅ ¡Hecho! Se han traducido y creado {len(files_created)} archivos.")
    
    # Crear ZIP
    zip_name = "conjuros_srd5_2_es.zip"
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for file in files_created:
            zipf.write(file, os.path.basename(file))
    
    print(f"📦 Archivo comprimido creado: {zip_name}")

if __name__ == "__main__":
    generar_conjuros()