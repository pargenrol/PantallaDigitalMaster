import os
import zipfile
import re

DIRECTORIO_SALIDA = "rules"

# Base de datos de reglas SRD (Texto manual para asegurar calidad de traducción)
REGLAS_DB = [
    # === ESTADOS (CONDITIONS) ===
    {
        "nombre": "Cegado (Blinded)",
        "categoria": "Estados",
        "descripcion": """
* La criatura no puede ver y falla automáticamente cualquier prueba de característica que requiera ver.
* Las tiradas de ataque contra la criatura tienen **ventaja**.
* Las tiradas de ataque de la criatura tienen **desventaja**.
"""
    },
    {
        "nombre": "Hechizado (Charmed)",
        "categoria": "Estados",
        "descripcion": """
* La criatura no puede atacar al hechizador ni elegirlo como objetivo de habilidades dañinas o efectos mágicos.
* El hechizador tiene **ventaja** en cualquier prueba de característica para interactuar socialmente con la criatura.
"""
    },
    {
        "nombre": "Ensordecido (Deafened)",
        "categoria": "Estados",
        "descripcion": """
* La criatura no puede oír y falla automáticamente cualquier prueba de característica que requiera oír.
"""
    },
    {
        "nombre": "Asustado (Frightened)",
        "categoria": "Estados",
        "descripcion": """
* La criatura tiene **desventaja** en las pruebas de característica y tiradas de ataque mientras la fuente de su miedo esté a la vista.
* La criatura no puede moverse voluntariamente a una posición más cercana a la fuente de su miedo.
"""
    },
    {
        "nombre": "Agarrado (Grappled)",
        "categoria": "Estados",
        "descripcion": """
* La velocidad de la criatura se convierte en **0**, y no puede beneficiarse de ningún bonificador a su velocidad.
* La condición finaliza si quien agarra queda incapacitado.
* La condición finaliza si un efecto saca a la criatura agarrada del alcance de quien la agarra o del efecto que la agarra (como cuando una criatura es arrojada por el conjuro *onda atronadora*).
"""
    },
    {
        "nombre": "Incapacitado (Incapacitated)",
        "categoria": "Estados",
        "descripcion": """
* La criatura no puede realizar acciones ni reacciones.
"""
    },
    {
        "nombre": "Invisible",
        "categoria": "Estados",
        "descripcion": """
* La criatura es imposible de ver sin la ayuda de magia o un sentido especial. A efectos de esconderse, se considera que la criatura está en un área muy oscura.
* La ubicación de la criatura puede ser detectada por cualquier ruido que haga o por las huellas que deje.
* Las tiradas de ataque contra la criatura tienen **desventaja**.
* Las tiradas de ataque hechas por la criatura tienen **ventaja**.
"""
    },
    {
        "nombre": "Paralizado (Paralyzed)",
        "categoria": "Estados",
        "descripcion": """
* La criatura está **incapacitada** (no puede realizar acciones ni reacciones) y no puede moverse ni hablar.
* La criatura falla automáticamente las tiradas de salvación de **Fuerza** y **Destreza**.
* Las tiradas de ataque contra la criatura tienen **ventaja**.
* Cualquier ataque que impacte a la criatura es un **crítico** si el atacante está a 5 pies o menos de ella.
"""
    },
    {
        "nombre": "Petrificado (Petrified)",
        "categoria": "Estados",
        "descripcion": """
* La criatura, junto con cualquier objeto no mágico que vista o porte, se transforma en una sustancia sólida inanimada (generalmente piedra). Su peso se multiplica por diez y deja de envejecer.
* La criatura está **incapacitada** (no puede realizar acciones ni reacciones), no puede moverse ni hablar y no es consciente de su entorno.
* Las tiradas de ataque contra la criatura tienen **ventaja**.
* La criatura falla automáticamente las tiradas de salvación de **Fuerza** y **Destreza**.
* La criatura tiene **resistencia** a todo el daño.
* La criatura es inmune al veneno y a la enfermedad, aunque si ya sufría alguna, queda suspendida, no neutralizada.
"""
    },
    {
        "nombre": "Envenenado (Poisoned)",
        "categoria": "Estados",
        "descripcion": """
* La criatura tiene **desventaja** en tiradas de ataque y pruebas de característica.
"""
    },
    {
        "nombre": "Derribado (Prone)",
        "categoria": "Estados",
        "descripcion": """
* La única opción de movimiento que tiene la criatura es gatear, a menos que se levante y finalice así la condición.
* La criatura tiene **desventaja** en tiradas de ataque.
* Las tiradas de ataque contra la criatura tienen **ventaja** si el atacante está a 5 pies o menos. De lo contrario, tienen **desventaja**.
"""
    },
    {
        "nombre": "Apresado (Restrained)",
        "categoria": "Estados",
        "descripcion": """
* La velocidad de la criatura se convierte en **0**, y no puede beneficiarse de ningún bonificador a su velocidad.
* Las tiradas de ataque contra la criatura tienen **ventaja**.
* Las tiradas de ataque de la criatura tienen **desventaja**.
* La criatura tiene **desventaja** en las tiradas de salvación de **Destreza**.
"""
    },
    {
        "nombre": "Aturdido (Stunned)",
        "categoria": "Estados",
        "descripcion": """
* La criatura está **incapacitada** (no puede realizar acciones ni reacciones), no puede moverse y solo puede hablar balbuceando.
* La criatura falla automáticamente las tiradas de salvación de **Fuerza** y **Destreza**.
* Las tiradas de ataque contra la criatura tienen **ventaja**.
"""
    },
    {
        "nombre": "Inconsciente (Unconscious)",
        "categoria": "Estados",
        "descripcion": """
* La criatura está **incapacitada**, no puede moverse ni hablar y no es consciente de su entorno.
* La criatura deja caer cualquier cosa que estuviera sujetando y queda **derribada**.
* La criatura falla automáticamente las tiradas de salvación de **Fuerza** y **Destreza**.
* Las tiradas de ataque contra la criatura tienen **ventaja**.
* Cualquier ataque que impacte a la criatura es un **crítico** si el atacante está a 5 pies o menos de ella.
"""
    },
    {
        "nombre": "Agotamiento (Exhaustion)",
        "categoria": "Estados",
        "descripcion": """
El agotamiento se mide en 6 niveles. Un efecto puede darte uno o más niveles.

| Nivel | Efecto |
|---|---|
| 1 | Desventaja en pruebas de característica |
| 2 | Velocidad reducida a la mitad |
| 3 | Desventaja en ataques y tiradas de salvación |
| 4 | Puntos de golpe máximos reducidos a la mitad |
| 5 | Velocidad reducida a 0 |
| 6 | Muerte |

* Si tienes agotamiento, descansar largas horas reduce tu nivel de agotamiento en 1, siempre que hayas comido y bebido.
"""
    },

    # === ACCIONES EN COMBATE ===
    {
        "nombre": "Acción: Atacar",
        "categoria": "Acciones",
        "descripcion": """
Con esta acción realizas un ataque cuerpo a cuerpo o a distancia.

Algunos rasgos, como el *Ataque Extra* del guerrero, te permiten hacer más de un ataque con esta acción. 

Puedes sustituir un ataque por un intento de **Agarre** o un **Empujón**.
"""
    },
    {
        "nombre": "Acción: Lanzar un Conjuro",
        "categoria": "Acciones",
        "descripcion": """
Cada conjuro tiene un tiempo de lanzamiento, que especifica si el lanzador debe usar una acción, una reacción, minutos o incluso horas para lanzar el conjuro. 

La mayoría de los conjuros tienen un tiempo de lanzamiento de 1 acción.
"""
    },
    {
        "nombre": "Acción: Correr (Dash)",
        "categoria": "Acciones",
        "descripcion": """
Ganas movimiento adicional para el turno actual. El aumento es igual a tu velocidad, después de aplicar cualquier modificador. 

Con una velocidad de 30 pies, por ejemplo, puedes moverte hasta 60 pies en tu turno si corres.
"""
    },
    {
        "nombre": "Acción: Destrabarse (Disengage)",
        "categoria": "Acciones",
        "descripcion": """
Si realizas la acción de destrabarse, tu movimiento no provoca ataques de oportunidad durante el resto del turno.
"""
    },
    {
        "nombre": "Acción: Esquivar (Dodge)",
        "categoria": "Acciones",
        "descripcion": """
Hasta el comienzo de tu siguiente turno, cualquier tirada de ataque que se haga contra ti tiene **desventaja** si puedes ver al atacante.
Además, tienes **ventaja** en las tiradas de salvación de **Destreza**. 

Pierdes este beneficio si quedas incapacitado o si tu velocidad baja a 0.
"""
    },
    {
        "nombre": "Acción: Ayudar (Help)",
        "categoria": "Acciones",
        "descripcion": """
Puedes prestar tu ayuda a otra criatura para completar una tarea. La criatura a la que ayudas gana **ventaja** en la siguiente prueba de característica que haga para completar la tarea.

Alternativamente, puedes ayudar a una criatura aliada a atacar a otra criatura que esté a 5 pies de ti. La primera tirada de ataque de tu aliado tiene **ventaja**.
"""
    },
    {
        "nombre": "Acción: Esconderse (Hide)",
        "categoria": "Acciones",
        "descripcion": """
Realizas una prueba de **Destreza (Sigilo)** para intentar ocultarte. Si tienes éxito, ganas los beneficios de no ser visto (ver reglas de Atacantes no Vistos).
"""
    },
    {
        "nombre": "Acción: Preparar (Ready)",
        "categoria": "Acciones",
        "descripcion": """
Te permite actuar más tarde en la ronda usando tu **Reacción**.

1. Decides qué circunstancia activará tu reacción.
2. Eliges la acción que realizarás (o moverte hasta tu velocidad) cuando ocurra el desencadenante.

*Ejemplo:* "Si el goblin se acerca a esa puerta, tiraré de la palanca".
"""
    },
    {
        "nombre": "Acción: Buscar (Search)",
        "categoria": "Acciones",
        "descripcion": """
Dedicas tu atención a encontrar algo. Dependiendo de la naturaleza de tu búsqueda, el DM podría pedirte una prueba de **Sabiduría (Percepción)** o **Inteligencia (Investigación)**.
"""
    },
    {
        "nombre": "Acción: Usar Objeto",
        "categoria": "Acciones",
        "descripcion": """
Normalmente interactúas con un objeto gratis (como desenvainar una espada). Si quieres interactuar con un segundo objeto o usar un objeto que requiera una acción específica (como beber una poción o usar un kit de sanador), usas esta acción.
"""
    },

    # === REGLAS DE COMBATE Y ENTORNO ===
    {
        "nombre": "Cobertura",
        "categoria": "Reglas",
        "descripcion": """
Los muros, árboles, criaturas y otros obstáculos pueden proporcionar cobertura durante el combate, haciendo que un objetivo sea más difícil de dañar.

| Cobertura | Efecto |
|---|---|
| **Media (1/2)** | +2 a la CA y salvaciones de Destreza. (Muebles bajos, criaturas, troncos delgados). |
| **Tres Cuartos (3/4)** | +5 a la CA y salvaciones de Destreza. (Rastris, troncos gruesos, esquinas de muros). |
| **Total** | No puede ser objetivo directo de un ataque o conjuro. |
"""
    },
    {
        "nombre": "Terreno Difícil",
        "categoria": "Reglas",
        "descripcion": """
Cada pie de movimiento en terreno difícil cuesta **1 pie extra**. Esta regla es cierta incluso si múltiples cosas en un espacio cuentan como terreno difícil.

Muebles bajos, escombros, maleza, escaleras empinadas, nieve y ciénagas som ejemplos de terreno difícil. El espacio de otra criatura, sea hostil o no, también cuenta como terreno difícil.
"""
    },
    {
        "nombre": "Muerte y Estabilizar",
        "categoria": "Reglas",
        "descripcion": """
**Tiradas de Salvación de Muerte:**
Empiezas tu turno con 0 PV. Tira 1d20.
* **10 o más:** Éxito. (3 éxitos = Estabilizado).
* **9 o menos:** Fallo. (3 fallos = Muerto).
* **1:** Cuenta como 2 fallos.
* **20:** Recuperas 1 PV y te vuelves consciente.

**Daño a 0 PV:**
Si recibes daño estando a 0 PV, sufres un fallo de muerte. Si es un crítico, sufres 2 fallos. Si el daño iguala o supera tus PV máximos, mueres instantáneamente.

**Estabilizar:**
Puedes usar tu acción para administrar primeros auxilios a una criatura inconsciente. Requiere prueba de **Sabiduría (Medicina) CD 10**.
"""
    },
    {
        "nombre": "Descanso Largo y Corto",
        "categoria": "Reglas",
        "descripcion": """
**Descanso Corto (mínimo 1 hora):**
* Puedes gastar uno o más **Dados de Golpe** para recuperar vida. Por cada dado gastado, tira el dado y suma tu Constitución.

**Descanso Largo (mínimo 8 horas):**
* Recuperas todos los Puntos de Golpe perdidos.
* Recuperas la mitad de tus Dados de Golpe máximos.
* No puedes beneficiarte de más de un descanso largo en un periodo de 24 horas.
"""
    },
    {
        "nombre": "Lanzamiento: Componentes",
        "categoria": "Magia",
        "descripcion": """
**V - Verbal:** Requiere entonar sonidos místicos. No puedes hacerlo si estás amordazado o en una zona de silencio.

**S - Somático:** Requiere gestos con las manos. Necesitas al menos una mano libre.

**M - Material:** Requiere objetos específicos. Puedes usar una bolsa de componentes o un canalizador arcano en lugar de los materiales específicos, a menos que se indique un coste en oro.
"""
    },
    {
        "nombre": "Lanzamiento: Concentración",
        "categoria": "Magia",
        "descripcion": """
Algunos conjuros requieren que mantengas la concentración. Si pierdes la concentración, el conjuro termina.

**Pierdes la concentración si:**
1. Lanzas otro conjuro que requiere concentración.
2. Recibes daño. Debes superar una salvación de **Constitución**. La CD es **10** o **la mitad del daño recibido** (lo que sea mayor).
3. Quedas incapacitado o mueres.
"""
    }
]

def limpiar_nombre_archivo(nombre):
    s = nombre.lower().replace(" ", "_").replace(":", "").replace("/", "_").replace("(", "").replace(")", "").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
    return re.sub(r'[^a-z0-9_]', '', s)

def generar_ficheros():
    if not os.path.exists(DIRECTORIO_SALIDA):
        os.makedirs(DIRECTORIO_SALIDA)

    print(f"📚 Generando glosario de reglas SRD en '{DIRECTORIO_SALIDA}'...")
    
    files_created = []

    for regla in REGLAS_DB:
        slug = limpiar_nombre_archivo(regla['nombre'])
        filename = f"{slug}.md"
        filepath = os.path.join(DIRECTORIO_SALIDA, filename)

        md_content = f"""---
nombre: "{regla['nombre']}"
category: "{regla['categoria']}"
---

{regla['descripcion']}
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        files_created.append(filepath)

    print(f"✅ ¡Hecho! Se han creado {len(files_created)} reglas.")
    
    # Crear ZIP
    zip_name = "reglas_srd_es.zip"
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for file in files_created:
            zipf.write(file, os.path.basename(file))
            
    print(f"📦 Zip creado: {zip_name}")

if __name__ == "__main__":
    generar_ficheros()