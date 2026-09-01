"""
Datos estructurados de AD&D 2ª edición para los formularios de creación de
personajes: razas (con ajustes de característica y límites de nivel), clases,
y pericias no-armas con su coste en casillas según la categoría del personaje.

Fuente: resources/adnd2e/rules/razas_adnd.md, clases_adnd.md, proficiencias_adnd.md
(ya verificadas contra el Manual del Jugador real en sesiones anteriores), más
la Tabla 38 "Grupos Cruzados de Pericias en No Armas" (pág. 56 del PHB, vía RAG/OCR).

Nota de terminología: el manual real usa "Pericias", no "Proficiencias" — se
mantiene el nombre de fichero/rutas existentes por compatibilidad, pero los
textos nuevos de cara al usuario dicen "Pericias".
"""

# ── Razas ──────────────────────────────────────────────────────────────────
# mods: ajuste de característica (se suma al valor base)
# limites_nivel: {clase: nivel_max}; una clase ausente de este dict = no disponible
#                para esa raza; valor None = sin límite de nivel
RAZAS_ADND2E = {
    "Humano": {
        "mods": {},
        "infravision": 0,
        "limites_nivel": None,  # None = todas las clases, sin límite
        "habilidades": [
            "Única raza que puede hacer doble clase (cambiar de clase y empezar de cero en la nueva)",
            "Acceso completo a todas las clases sin límite de nivel",
        ],
    },
    "Elfo": {
        "mods": {"des": 1, "sab": -1},
        "infravision": 60,
        "limites_nivel": {"Guerrero": 7, "Mago": None, "Ladrón": None, "Clérigo": 7, "Bardo": None},
        "habilidades": [
            "Resistencia a magia de encantamiento y sueño (+90% inmunidad a hechizos de sueño, +30% a encantamiento)",
            "Detectar puertas secretas: 1 en 6 al pasar / 2 en 6 si busca activamente",
            "Movimiento silencioso en terreno natural (sorpresa en 4 de 6)",
            "No deja rastro en terreno natural salvo para otro elfo o explorador experto",
        ],
    },
    "Semielfo": {
        "mods": {},
        "infravision": 60,
        "limites_nivel": {"Guerrero": 12, "Mago": 8, "Clérigo": None, "Ladrón": None, "Bardo": None, "Druida": None},
        "habilidades": [
            "Resistencia parcial a sueño y encantamiento (30%)",
            "Detectar puertas secretas: 1 en 6 al pasar, 3 en 6 si busca",
        ],
    },
    "Enano": {
        "mods": {"con": 1, "car": -1},
        "infravision": 60,
        "limites_nivel": {"Guerrero": 15, "Ladrón": None},
        "habilidades": [
            "Bonificación a salvaciones por Constitución y tamaño",
            "Detectar trampas/puertas secretas/pendientes en subterráneos (1 en 6 pasivo, 2 en 6 activo)",
            "Conocimiento de piedra: detecta trabajo reciente, tipo de muro, etc.",
            "Odio a orcos, goblinoides y gigantes",
        ],
    },
    "Halfling": {
        "mods": {"des": 1, "fue": -1},
        "infravision": 0,
        "limites_nivel": {"Guerrero": 6, "Ladrón": None},
        "habilidades": [
            "Ocultarse en terreno natural: 90% de éxito",
            "Sorprende en 4 de 6, prácticamente silencioso",
            "+3 a ataques con honda, +1 con arco",
        ],
    },
    "Gnomo": {
        "mods": {"int": 1, "sab": -1},
        "infravision": 60,
        "limites_nivel": {"Guerrero": 6, "Mago": None, "Ladrón": None, "Clérigo": None},
        "habilidades": [
            "Especialista natural en Ilusión: +1 a CD de conjuros de ilusión",
            "Detectar maquinaria, trampas mecánicas y trabajo en gema/joya",
            "Comunicación con mamíferos pequeños del bosque",
        ],
    },
    "Semiorco": {
        "mods": {"fue": 1, "con": 1, "int": -2, "car": -1},
        "infravision": 60,
        "limites_nivel": {"Guerrero": 10, "Ladrón": 8},
        "habilidades": [
            "Sin habilidades especiales — compensado por atributos físicos",
        ],
    },
}

# ── Clases ─────────────────────────────────────────────────────────────────
# grupo: Combatiente/Sacerdote/Pícaro/Hechicero (usado para THAC0, XP, slots de pericia)
CLASES_ADND2E = {
    "Guerrero":    {"grupo": "Combatiente", "dado_golpe": "d10", "requisito": {"fue": 9}},
    "Paladín":     {"grupo": "Combatiente", "dado_golpe": "d10", "requisito": {"fue": 12, "des": 9, "con": 9, "sab": 13, "car": 17}},
    "Explorador":  {"grupo": "Combatiente", "dado_golpe": "d10", "requisito": {"fue": 13, "des": 13, "con": 14, "sab": 14}},
    "Mago":        {"grupo": "Hechicero",   "dado_golpe": "d4",  "requisito": {"int": 9}},
    "Ilusionista": {"grupo": "Hechicero",   "dado_golpe": "d4",  "requisito": {"des": 16, "int": 15}},
    "Clérigo":     {"grupo": "Sacerdote",   "dado_golpe": "d8",  "requisito": {"sab": 9}},
    "Druida":      {"grupo": "Sacerdote",   "dado_golpe": "d8",  "requisito": {"sab": 12, "car": 15}},
    "Ladrón":      {"grupo": "Pícaro",      "dado_golpe": "d6",  "requisito": {"des": 9}},
    "Bardo":       {"grupo": "Pícaro",      "dado_golpe": "d6",  "requisito": {"des": 12, "int": 13, "car": 15}},
}

# ── Habilidades especiales por clase ────────────────────────────────────
# Fuente: resources/adnd2e/rules/clases_adnd.md (ya verificado vía RAG contra
# el Manual del Jugador, capítulos 3 y 4).
HABILIDADES_CLASE = {
    "Guerrero": [
        "Especialización y maestría en armas (única clase que puede)",
        "Ataques múltiples por asalto según nivel (ver tabla de combate)",
        "Puede usar cualquier arma y armadura",
        "Doble daño en la carga con arma apropiada",
    ],
    "Paladín": [
        "Todas las habilidades de Guerrero",
        "+2 a todas las tiradas de salvación",
        "Detectar el mal en un radio de 60 pies (pasivo, constante)",
        "Imponer manos: cura 2 PG/nivel, 1 vez al día",
        "Turno de no-muertos (como clérigo, 2 niveles menos)",
        "Inmune a enfermedades; cura enfermedades 1×/semana desde nivel 3",
        "Montura especial (corcel élfico) desde nivel 4",
        "Conjuros de clérigo (niveles 1-4) desde nivel 9",
        "Requiere alineamiento Legal Bueno y comportamiento impecable",
    ],
    "Explorador": [
        "Todas las habilidades de Guerrero",
        "Rastrear sin magia",
        "Lucha con dos armas con penalizadores reducidos",
        "Bonificador de reacción y sorpresa en exteriores",
        "Conjuros de druida (niveles 1-2) desde nivel 8",
        "Pierde sus habilidades si usa armadura mayor que cota de malla",
    ],
    "Mago": [
        "Lanza conjuros arcanos memorizados de su libro de conjuros",
        "Acceso a conjuros de nivel 1 a 9",
        "Sin límite de nivel de personaje",
        "Puede crear objetos mágicos desde nivel 9",
        "Puede investigar y escribir nuevos conjuros",
        "Solo puede usar armas simples (daga, bastón, dardo, ballesta, honda)",
        "No puede llevar armadura",
    ],
    "Ilusionista": [
        "Mago especialista en la escuela de Ilusión",
        "+1 conjuro adicional de Ilusión por nivel de conjuro",
        "No puede aprender conjuros de Evocación ni Nigromancia",
        "El resto de reglas de Mago le aplican igual",
    ],
    "Clérigo": [
        "Lanza conjuros sacerdotales concedidos por su deidad (no necesita libro)",
        "Acceso a conjuros de nivel 1 a 7",
        "Turno de no-muertos (ver tabla de turno)",
        "Puede usar cualquier armadura",
        "Limitado a armas contundentes (varía según deidad)",
    ],
    "Druida": [
        "Lanza conjuros de naturaleza (no necesita libro)",
        "Cambio de forma en animal desde nivel 7 (3 veces al día)",
        "Inmune a hechizos feéricos de control mental a nivel alto",
        "Comprende el idioma druídico secreto",
        "Solo armadura de cuero o madera; sin metal",
        "Armas limitadas: porra, hoz, jabalina, lanza, honda, bastón, daga",
    ],
    "Ladrón": [
        "Habilidades de ladrón por %: Escalar superficies, Detectar ruidos, "
        "Encontrar/quitar trampas, Esconderse en las sombras, Moverse en silencio, "
        "Abrir cerraduras, Leer idiomas, Recoger bolsillos",
        "60 puntos por nivel para repartir entre sus habilidades (modificados por DES y raza)",
        "Ataque furtivo (golpe por la espalda): +4 a impactar; daño ×2 (nivel 1-4), "
        "×3 (5-8), ×4 (9-12), ×5 (13+)",
    ],
    "Bardo": [
        "Versión reducida de habilidades de ladrón (escalar, detectar, esconderse, "
        "moverse en silencio, abrir cerraduras)",
        "Magia arcana propia (nivel 1-6 máximo, sin libro)",
        "Canción de bardo: inspiración en combate o exploración",
        "Puede leer pergaminos arcanos desde nivel 5",
        "Conocimiento de leyendas y mitología",
        "Bonificador a reacciones de PNJ",
    ],
}

# ── Conjuros: casillas disponibles por nivel de clase ──────────────────────
# Fuente: resources/adnd2e/rules/magia_adnd.md, tablas 2 y 3 (ya verificadas).
# Cada valor es una lista de casillas [nivel de conjuro 1, 2, 3...].
CONJUROS_SLOTS_MAGO = {
    1: [1, 0, 0, 0, 0, 0, 0, 0, 0], 2: [2, 0, 0, 0, 0, 0, 0, 0, 0],
    3: [2, 1, 0, 0, 0, 0, 0, 0, 0], 4: [3, 2, 0, 0, 0, 0, 0, 0, 0],
    5: [4, 2, 1, 0, 0, 0, 0, 0, 0], 6: [4, 2, 2, 0, 0, 0, 0, 0, 0],
    7: [4, 3, 2, 1, 0, 0, 0, 0, 0], 8: [4, 3, 3, 2, 0, 0, 0, 0, 0],
    9: [4, 3, 3, 2, 1, 0, 0, 0, 0], 10: [4, 4, 3, 2, 2, 0, 0, 0, 0],
    11: [4, 4, 4, 3, 3, 0, 0, 0, 0], 12: [4, 4, 4, 4, 4, 1, 0, 0, 0],
    13: [5, 5, 4, 4, 4, 2, 0, 0, 0], 14: [5, 5, 5, 4, 4, 2, 1, 0, 0],
    15: [5, 5, 5, 5, 5, 2, 1, 0, 0], 16: [5, 5, 5, 5, 5, 3, 2, 1, 0],
    17: [5, 5, 5, 5, 5, 3, 3, 2, 0], 18: [5, 5, 5, 5, 5, 3, 3, 2, 1],
    19: [5, 5, 5, 5, 5, 4, 3, 3, 1],  # 19+
}
CONJUROS_SLOTS_CLERIGO = {
    1: [1, 0, 0, 0, 0, 0, 0], 2: [2, 0, 0, 0, 0, 0, 0], 3: [2, 1, 0, 0, 0, 0, 0],
    4: [3, 2, 0, 0, 0, 0, 0], 5: [3, 3, 1, 0, 0, 0, 0], 6: [3, 3, 2, 0, 0, 0, 0],
    7: [3, 3, 2, 1, 0, 0, 0], 8: [3, 3, 3, 2, 0, 0, 0], 9: [4, 4, 3, 2, 1, 0, 0],
    10: [4, 4, 3, 3, 2, 0, 0], 11: [5, 4, 4, 3, 2, 1, 0], 12: [6, 5, 5, 3, 2, 2, 0],
    13: [6, 6, 6, 4, 2, 2, 0], 14: [6, 6, 6, 5, 3, 2, 1], 15: [6, 6, 6, 6, 4, 2, 1],
    16: [7, 7, 7, 6, 4, 3, 1], 17: [7, 7, 7, 7, 5, 3, 2],  # 17+
}


def conjuros_disponibles(clase: str, nivel: int) -> list[int] | None:
    grupo = (CLASES_ADND2E.get(clase) or {}).get("grupo")
    if grupo == "Hechicero":
        tabla, tope = CONJUROS_SLOTS_MAGO, 19
    elif grupo == "Sacerdote":
        tabla, tope = CONJUROS_SLOTS_CLERIGO, 17
    else:
        return None
    return tabla.get(min(max(1, int(nivel or 1)), tope))


# ── Listas de conjuros seleccionables (lista práctica de referencia, NO el
# listado exhaustivo del manual — el usuario puede añadir cualquier otro
# conjuro a mano). Nombres de conjuros clásicos e inequívocos de AD&D2e. ────
CONJUROS_ADND2E = {
    "Mago": {
        1: ["Proyectil mágico", "Detectar magia", "Escudo", "Dormir", "Luz",
            "Manos ardientes", "Identificar", "Lectura de magia", "Ventriloquia", "Encantar persona"],
        2: ["Fuerza fantasmal mejorada", "Invisibilidad", "Levitar", "Rayo de escarcha",
            "Telaraña", "Sordera-mudez", "Detectar el pensamiento", "Espejismo"],
        3: ["Bola de fuego", "Relámpago", "Contraconjuro", "Volar", "Velocidad",
            "Invisibilidad al 10%", "Bola de fuego retardada"],
        4: ["Muro de fuego", "Muro de hielo", "Confusión", "Polimorfar otros",
            "Ojo arcano", "Encantar monstruo"],
        5: ["Telequinesis", "Muro de piedra", "Nube mortal", "Contactar otro plano",
            "Bola de fuego mejorada"],
        6: ["Desintegrar", "Piel de piedra", "Muro de hierro", "Invisibilidad global"],
        7: ["Prisión de fuerza", "Cadena de relámpagos"],
        8: ["Símbolo de la muerte", "Antipatía/Simpatía"],
        9: ["Deseo limitado", "Meteoros"],
    },
    "Clérigo": {
        1: ["Curar heridas leves", "Bendecir", "Protección contra el mal", "Luz",
            "Detectar magia", "Purificar comida y agua", "Comando"],
        2: ["Curar heridas moderadas", "Silencio radio 5 metros", "Tranquilizar animales",
            "Resistencia al fuego", "Detectar mentiras", "Conocer alineamiento"],
        3: ["Curar ceguera/sordera", "Remover maldición", "Caminar sobre el agua",
            "Oración", "Crear comida y agua"],
        4: ["Curar heridas graves", "Neutralizar veneno",
            "Protección contra el mal radio 3 metros", "Liberación"],
        5: ["Restaurar", "Plaga de insectos", "Curar heridas críticas", "Verdadera visión"],
        6: ["Curar (grupo)", "Palabra de poder: aturdir", "Encontrar el camino"],
        7: ["Resurrección", "Restauración completa"],
    },
}

# Clases con acceso a conjuros y de qué lista/tabla se sirven.
CLASES_CONJURADORAS = {
    "Mago":        {"lista": "Mago", "desde_nivel": 1},
    "Ilusionista": {"lista": "Mago", "desde_nivel": 1},
    "Clérigo":     {"lista": "Clérigo", "desde_nivel": 1},
    "Druida":      {"lista": "Clérigo", "desde_nivel": 1},
    "Paladín":     {"lista": "Clérigo", "desde_nivel": 9, "nivel_max_conjuro": 4},
    "Bardo":       {"lista": "Mago", "desde_nivel": 1, "nivel_max_conjuro": 3},
}


# ── Grupos de pericias accesibles por clase (Tabla 38 del PHB) ─────────────
# "General" es accesible para todas las clases (coste 1 casilla siempre).
GRUPOS_PERICIA_POR_CLASE = {
    "Guerrero":    ["Luchador", "General"],
    "Paladín":     ["Luchador", "Sacerdote", "General"],
    "Explorador":  ["Hechicero", "Luchador", "General"],
    "Mago":        ["Hechicero", "General"],
    "Ilusionista": ["Hechicero", "General"],
    "Clérigo":     ["Sacerdote", "General"],
    "Druida":      ["Luchador", "Sacerdote", "General"],
    "Ladrón":      ["Bribón", "General"],
    "Bardo":       ["Bribón", "Hechicero", "Luchador", "General"],
}

# ── Pericias no-armas ────────────────────────────────────────────────────
# grupo: a qué lista pertenece "de origen" (determina si cuesta 1 o 2 casillas
# según la clase — ver GRUPOS_PERICIA_POR_CLASE). Solo Curación, Herbología y
# Navegación están confirmadas contra el manual real (Tabla 38 y descripciones,
# pág. 56); el resto se ha dejado en "General" por defecto al no tener
# confirmación 1:1 de cada pericia contra la tabla original — es una asunción
# conservadora (nunca deja una pericia "más cara" de lo que debería, como
# mucho más barata).
PERICIAS_NO_ARMA = [
    {"nombre": "Equitación (terrestre)", "caract": "DES", "mod": 3, "slots": 1, "grupo": "General", "descripcion": "Montar caballos y bestias de monta."},
    {"nombre": "Natación", "caract": "FUE", "mod": 0, "slots": 1, "grupo": "General", "descripcion": "Nadar sin ahogarse."},
    {"nombre": "Escalada", "caract": "FUE", "mod": 0, "slots": 1, "grupo": "General", "descripcion": "Escalar superficies."},
    {"nombre": "Rastreo", "caract": "SAB", "mod": 0, "slots": 1, "grupo": "General", "descripcion": "Seguir huellas (los Exploradores tienen +1 y no la necesitan como pericia aparte)."},
    {"nombre": "Sigilo", "caract": "DES", "mod": -1, "slots": 1, "grupo": "General", "descripcion": "Moverse silenciosamente (distinto de la habilidad de Ladrón)."},
    {"nombre": "Curación", "caract": "SAB", "mod": -2, "slots": 1, "grupo": "Sacerdote", "descripcion": "Primeros auxilios y curación básica."},
    {"nombre": "Herbología", "caract": "INT", "mod": -2, "slots": 1, "grupo": "Hechicero", "descripcion": "Identificar plantas medicinales y venenos vegetales."},
    {"nombre": "Cocina", "caract": "INT", "mod": 0, "slots": 1, "grupo": "General", "descripcion": "Preparar alimentos; sobrevivir en la naturaleza."},
    {"nombre": "Artesanía (variada)", "caract": "INT", "mod": 0, "slots": 1, "grupo": "General", "descripcion": "Carpintería, herrería, cerámica, etc."},
    {"nombre": "Música", "caract": "CAR", "mod": 0, "slots": 1, "grupo": "General", "descripcion": "Tocar un instrumento."},
    {"nombre": "Navegación", "caract": "INT", "mod": -2, "slots": 1, "grupo": "Hechicero", "descripcion": "Guiar barcos por las estrellas."},
    {"nombre": "Historia Local", "caract": "INT", "mod": 0, "slots": 1, "grupo": "General", "descripcion": "Conocer leyendas e historia de una región."},
    {"nombre": "Idiomas Modernos", "caract": "INT", "mod": 0, "slots": 1, "grupo": "General", "descripcion": "Hablar/leer un idioma adicional por casilla."},
    {"nombre": "Lectura/Escritura", "caract": "INT", "mod": 1, "slots": 1, "grupo": "General", "descripcion": "Leer y escribir el propio idioma."},
    {"nombre": "Lectura de Labios", "caract": "INT", "mod": -2, "slots": 2, "grupo": "General", "descripcion": "Entender lo que dice alguien sin oírlo."},
    {"nombre": "Percepción de Peligro", "caract": "SAB", "mod": 0, "slots": 2, "grupo": "General", "descripcion": "Detectar trampas y peligros ocultos."},
    {"nombre": "Lanzamiento de Runas", "caract": "INT", "mod": -3, "slots": 2, "grupo": "General", "descripcion": "Lanzar y leer runas como método de adivinación."},
]


# ── GAC0 (antes THAC0) por nivel y grupo de clase ──────────────────────────
# Fuente: resources/adnd2e/rules/thac0_por_nivel.md (ya verificado). El término
# oficial en el manual español es "GAC0", no "THAC0" (confirmado vía RAG/OCR:
# "Su GACO es 4, modificado a 12 por su Fuerza..." — Manual del Jugador, pág. 91).
GAC0_POR_NIVEL = {
    "Combatiente": {1: 20, 2: 19, 3: 18, 4: 17, 5: 16, 6: 15, 7: 14, 8: 13, 9: 12, 10: 11,
                    11: 10, 12: 9, 13: 8, 14: 7, 15: 6, 16: 5, 17: 4, 18: 3, 19: 2, 20: 1},
    "Sacerdote":   {1: 20, 2: 20, 3: 20, 4: 18, 5: 18, 6: 18, 7: 16, 8: 16, 9: 16, 10: 14,
                    11: 14, 12: 14, 13: 12, 14: 12, 15: 12, 16: 10, 17: 10, 18: 10, 19: 8, 20: 8},
    "Pícaro":      {1: 20, 2: 20, 3: 19, 4: 19, 5: 18, 6: 18, 7: 17, 8: 17, 9: 16, 10: 16,
                    11: 15, 12: 15, 13: 13, 14: 13, 15: 12, 16: 12, 17: 11, 18: 11, 19: 10, 20: 10},
    "Hechicero":   {1: 20, 2: 20, 3: 20, 4: 20, 5: 20, 6: 19, 7: 18, 8: 18, 9: 18, 10: 17,
                    11: 16, 12: 16, 13: 16, 14: 15, 15: 14, 16: 14, 17: 14, 18: 13, 19: 12, 20: 12},
}


def gac0_para(grupo: str, nivel: int) -> int | None:
    tabla = GAC0_POR_NIVEL.get(grupo)
    if not tabla:
        return None
    nivel = max(1, min(20, int(nivel or 1)))
    return tabla[nivel]


# ── Puntos de golpe por nivel y grupo de clase ─────────────────────────────
# corte: último nivel que todavía tira dado; a partir de corte+1 se suma un
# bonus fijo por nivel en vez de tirar. con_completo: si el modificador de PG
# por CON se aplica entero (solo Combatientes) o tope +2/nivel (el resto).
# Fuente: resources/adnd2e/rules/experiencia_y_niveles.md (ya verificado).
PG_INFO_POR_GRUPO = {
    "Combatiente": {"dado": 10, "corte": 9, "bonus_tras_corte": 3, "con_completo": True},
    "Sacerdote":   {"dado": 8,  "corte": 9, "bonus_tras_corte": 2, "con_completo": False},
    "Pícaro":      {"dado": 6,  "corte": 9, "bonus_tras_corte": 2, "con_completo": False},
    "Hechicero":   {"dado": 4,  "corte": 10, "bonus_tras_corte": 1, "con_completo": False},
}

# Modificador de PG por Constitución (Tabla de caracteristicas_adnd.md, ya verificada)
CON_MOD_PG = {
    3: -2, 4: -1, 5: -1, 6: -1, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0, 14: 0,
    15: 1, 16: 2, 17: 3, 18: 4, 19: 5,
}


def con_mod_pg(con: int) -> int:
    con = max(3, min(19, int(con or 10)))
    return CON_MOD_PG[con]


# ── Casillas de pericia en armas por grupo de clase ────────────────────────
# Fuente: resources/adnd2e/rules/proficiencias_adnd.md, sección 1 (ya verificada).
SLOTS_ARMA_POR_GRUPO = {
    "Combatiente": {"iniciales": 4, "cada_niveles": 3},
    "Sacerdote":   {"iniciales": 2, "cada_niveles": 4},
    "Pícaro":      {"iniciales": 2, "cada_niveles": 4},
    "Hechicero":   {"iniciales": 1, "cada_niveles": 6},
}


def slots_arma_disponibles(grupo: str, nivel: int) -> int | None:
    info = SLOTS_ARMA_POR_GRUPO.get(grupo)
    if not info:
        return None
    nivel = max(1, int(nivel or 1))
    extra = (nivel - 1) // info["cada_niveles"]
    return info["iniciales"] + extra


# ── Lista de armas (para autocompletar el nombre al añadir una pericia) ───
# Fuente: resources/adnd2e/rules/tablas_armas_adnd.md (ya verificada).
ARMAS_ADND2E = [
    "Bastón de combate", "Daga", "Daga (mano izquierda)", "Espada bastarda (1 mano)",
    "Espada bastarda (2 manos)", "Espada corta", "Espada larga", "Espada ancha",
    "Espadón (2 manos)", "Estoque", "Cimitarra", "Hacha de mano", "Hacha de guerra",
    "Hacha de batalla", "Mazo (a pie)", "Mazo (montado)", "Maza con bola",
    "Mangual (a pie)", "Pico (a pie)", "Pica", "Lanza", "Tridente", "Alabarda",
    "Guja", "Rompecabezas",
    "Arco largo", "Arco corto", "Arco largo compuesto", "Arco corto compuesto",
    "Ballesta pesada", "Ballesta ligera", "Ballesta de mano", "Jabalina",
    "Martillo de guerra", "Dardo", "Honda",
]

# ── Idiomas adicionales gratuitos según Inteligencia ───────────────────────
# Fuente: resources/adnd2e/rules/proficiencias_adnd.md, sección 3 (ya verificada).
IDIOMAS_POR_INT = [
    (0, 7, 0), (8, 8, 1), (9, 11, 2), (12, 13, 3), (14, 15, 4), (16, 99, 5),
]


def idiomas_adicionales(int_score: int) -> int:
    int_score = int(int_score or 0)
    for lo, hi, n in IDIOMAS_POR_INT:
        if lo <= int_score <= hi:
            return n
    return 5 if int_score > 16 else 0


def slots_pericia_para_clase(pericia: dict, clase: str) -> int:
    """Coste real en casillas de una pericia para una clase dada (1 si es de su
    grupo o General, 2 si es de un grupo al que no tiene acceso directo)."""
    grupos_clase = GRUPOS_PERICIA_POR_CLASE.get(clase, ["General"])
    coste_base = pericia["slots"]
    if pericia["grupo"] in grupos_clase:
        return coste_base
    return coste_base * 2


# ── Alineamientos ───────────────────────────────────────────────────────────
ALINEAMIENTOS_ADND2E = [
    "Legal Bueno", "Neutral Bueno", "Caótico Bueno",
    "Legal Neutral", "Neutral Puro", "Caótico Neutral",
    "Legal Malvado", "Neutral Malvado", "Caótico Malvado",
]

# ── Modificadores derivados por característica ──────────────────────────────
# Fuente: resources/adnd2e/rules/caracteristicas_adnd.md (ya verificado). Usado
# para la tabla de la ficha imprimible (estilo hoja oficial "Player Character
# Record"). No incluye la Fuerza Excepcional 18/01-18/00 (requiere % aparte).
# Fuente de FUE/DES/CON/INT/CAR (Tablas 1-4 y 6, Manual del Jugador cap. 1):
# verificadas contra el PDF de texto el 2026-09-01 tras encontrar que FUE,
# CON, INT y CAR tenían valores incorrectos en varias filas (posible mezcla
# con otra edición/fuente al escribirlas la primera vez). DES ya era correcta.
FUE_DERIVADOS = {
    # peso_autorizado y esfuerzo_max en kg. puertas = probabilidad (X en 6)
    # de forzar una puerta atascada. barrotes = % de doblar barrotes/alzar
    # puertas trabadas. No incluye la Fuerza Excepcional 18/01-18/00 (requiere
    # % aparte) ni las filas 21+ (solo gigantes/criaturas, no PJs).
    3: {"ataque": -3, "daño": -1, "peso_autorizado": 0.25, "esfuerzo_max": 5, "puertas": 2, "barrotes": 0},
    4: {"ataque": -2, "daño": -1, "peso_autorizado": 5, "esfuerzo_max": 23, "puertas": 3, "barrotes": 0},
    5: {"ataque": -2, "daño": -1, "peso_autorizado": 5, "esfuerzo_max": 23, "puertas": 3, "barrotes": 0},
    6: {"ataque": -1, "daño": 0, "peso_autorizado": 10, "esfuerzo_max": 28, "puertas": 4, "barrotes": 0},
    7: {"ataque": -1, "daño": 0, "peso_autorizado": 10, "esfuerzo_max": 28, "puertas": 4, "barrotes": 0},
    8: {"ataque": 0, "daño": 0, "peso_autorizado": 18, "esfuerzo_max": 45, "puertas": 5, "barrotes": 1},
    9: {"ataque": 0, "daño": 0, "peso_autorizado": 18, "esfuerzo_max": 45, "puertas": 5, "barrotes": 1},
    10: {"ataque": 0, "daño": 0, "peso_autorizado": 20, "esfuerzo_max": 58, "puertas": 6, "barrotes": 2},
    11: {"ataque": 0, "daño": 0, "peso_autorizado": 20, "esfuerzo_max": 58, "puertas": 6, "barrotes": 2},
    12: {"ataque": 0, "daño": 0, "peso_autorizado": 23, "esfuerzo_max": 70, "puertas": 7, "barrotes": 4},
    13: {"ataque": 0, "daño": 0, "peso_autorizado": 23, "esfuerzo_max": 70, "puertas": 7, "barrotes": 4},
    14: {"ataque": 0, "daño": 0, "peso_autorizado": 28, "esfuerzo_max": 85, "puertas": 8, "barrotes": 7},
    15: {"ataque": 0, "daño": 0, "peso_autorizado": 28, "esfuerzo_max": 85, "puertas": 8, "barrotes": 7},
    16: {"ataque": 0, "daño": 1, "peso_autorizado": 35, "esfuerzo_max": 98, "puertas": 9, "barrotes": 10},
    17: {"ataque": 1, "daño": 1, "peso_autorizado": 43, "esfuerzo_max": 110, "puertas": 10, "barrotes": 13},
    18: {"ataque": 1, "daño": 2, "peso_autorizado": 55, "esfuerzo_max": 130, "puertas": 11, "barrotes": 16},
    19: {"ataque": 3, "daño": 7, "peso_autorizado": 245, "esfuerzo_max": 320, "puertas": "16 (8)", "barrotes": 50},
    20: {"ataque": 3, "daño": 8, "peso_autorizado": 270, "esfuerzo_max": 350, "puertas": "17 (10)", "barrotes": 60},
}
DES_DERIVADOS = {
    3: {"reaccion": -3, "ataque_proyectil": -3, "ca": 4}, 4: {"reaccion": -2, "ataque_proyectil": -2, "ca": 3},
    5: {"reaccion": -1, "ataque_proyectil": -1, "ca": 2}, 6: {"reaccion": 0, "ataque_proyectil": 0, "ca": 1},
    7: {"reaccion": 0, "ataque_proyectil": 0, "ca": 0}, 8: {"reaccion": 0, "ataque_proyectil": 0, "ca": 0},
    9: {"reaccion": 0, "ataque_proyectil": 0, "ca": 0}, 10: {"reaccion": 0, "ataque_proyectil": 0, "ca": 0},
    11: {"reaccion": 0, "ataque_proyectil": 0, "ca": 0}, 12: {"reaccion": 0, "ataque_proyectil": 0, "ca": 0},
    13: {"reaccion": 0, "ataque_proyectil": 0, "ca": 0}, 14: {"reaccion": 0, "ataque_proyectil": 0, "ca": 0},
    15: {"reaccion": 0, "ataque_proyectil": 0, "ca": -1}, 16: {"reaccion": 1, "ataque_proyectil": 1, "ca": -2},
    17: {"reaccion": 2, "ataque_proyectil": 2, "ca": -3}, 18: {"reaccion": 2, "ataque_proyectil": 2, "ca": -4},
    19: {"reaccion": 3, "ataque_proyectil": 3, "ca": -4},
}
CON_DERIVADOS = {
    # pg (Ajuste PG/dado) usa el tope general (+2 máx.) de la tabla — los
    # Guerreros ganan más con CON 17-19 (hasta +3/+4/+5) según nota al pie de
    # la Tabla 3, no reflejado aquí porque este cálculo no distingue clase.
    3: {"pg": -2, "shock": 35, "resurrec": 40}, 4: {"pg": -1, "shock": 40, "resurrec": 45},
    5: {"pg": -1, "shock": 45, "resurrec": 50}, 6: {"pg": -1, "shock": 50, "resurrec": 55},
    7: {"pg": 0, "shock": 55, "resurrec": 60}, 8: {"pg": 0, "shock": 60, "resurrec": 65},
    9: {"pg": 0, "shock": 65, "resurrec": 70}, 10: {"pg": 0, "shock": 70, "resurrec": 75},
    11: {"pg": 0, "shock": 75, "resurrec": 80}, 12: {"pg": 0, "shock": 80, "resurrec": 85},
    13: {"pg": 0, "shock": 85, "resurrec": 90}, 14: {"pg": 0, "shock": 88, "resurrec": 92},
    15: {"pg": 1, "shock": 90, "resurrec": 94}, 16: {"pg": 2, "shock": 95, "resurrec": 96},
    17: {"pg": 2, "shock": 97, "resurrec": 98}, 18: {"pg": 2, "shock": 99, "resurrec": 100},
    19: {"pg": 2, "shock": 99, "resurrec": 100},
}
INT_DERIVADOS = {
    # nivel_max_conjuro/aprender/maxconj solo aplican a lanzadores arcanos
    # (Mago/Ilusionista); con INT 3-8 la tabla real no da ninguno de estos
    # valores (no pueden lanzar magia arcana), solo "idiomas".
    3: {"idiomas": 1}, 4: {"idiomas": 1}, 5: {"idiomas": 1}, 6: {"idiomas": 1},
    7: {"idiomas": 1}, 8: {"idiomas": 1},
    9: {"idiomas": 2, "nivel_max_conjuro": 4, "aprender": 35, "maxconj": 6},
    10: {"idiomas": 2, "nivel_max_conjuro": 5, "aprender": 40, "maxconj": 7},
    11: {"idiomas": 2, "nivel_max_conjuro": 5, "aprender": 45, "maxconj": 7},
    12: {"idiomas": 3, "nivel_max_conjuro": 6, "aprender": 50, "maxconj": 7},
    13: {"idiomas": 3, "nivel_max_conjuro": 6, "aprender": 55, "maxconj": 9},
    14: {"idiomas": 4, "nivel_max_conjuro": 7, "aprender": 60, "maxconj": 9},
    15: {"idiomas": 4, "nivel_max_conjuro": 7, "aprender": 65, "maxconj": 11},
    16: {"idiomas": 5, "nivel_max_conjuro": 8, "aprender": 70, "maxconj": 11},
    17: {"idiomas": 6, "nivel_max_conjuro": 8, "aprender": 75, "maxconj": 14},
    18: {"idiomas": 7, "nivel_max_conjuro": 9, "aprender": 85, "maxconj": 18},
    19: {"idiomas": 8, "nivel_max_conjuro": 9, "aprender": 95, "maxconj": "Todos"},
}
SAB_DERIVADOS = {
    # Fuente: Tabla 5: SABIDURÍA (Manual del Jugador, cap. 1) — verificada
    # contra el PDF de texto el 2026-09-01 tras detectar que esta tabla traía
    # varios valores equivocados (posible mezcla con otra edición).
    3: {"salvacion_magica": -3, "fallo": 50}, 4: {"salvacion_magica": -2, "fallo": 45},
    5: {"salvacion_magica": -1, "fallo": 40}, 6: {"salvacion_magica": -1, "fallo": 35},
    7: {"salvacion_magica": 0, "fallo": 30}, 8: {"salvacion_magica": 0, "fallo": 25},
    9: {"salvacion_magica": 0, "fallo": 20, "conjuros_bonus": 0},
    10: {"salvacion_magica": 0, "fallo": 15, "conjuros_bonus": 0},
    11: {"salvacion_magica": 0, "fallo": 10, "conjuros_bonus": 0},
    12: {"salvacion_magica": 0, "fallo": 5, "conjuros_bonus": 0},
    13: {"salvacion_magica": 0, "fallo": 0, "conjuros_bonus": 1},
    14: {"salvacion_magica": 0, "fallo": 0, "conjuros_bonus": 1},
    15: {"salvacion_magica": 1, "fallo": 0, "conjuros_bonus": 2},
    16: {"salvacion_magica": 2, "fallo": 0, "conjuros_bonus": 2},
    17: {"salvacion_magica": 3, "fallo": 0, "conjuros_bonus": 3},
    18: {"salvacion_magica": 4, "fallo": 0, "conjuros_bonus": 4},
    19: {"salvacion_magica": 4, "fallo": 0, "conjuros_bonus": "1,4"},
}
CAR_DERIVADOS = {
    3: {"henchmen": 1, "lealtad": -6, "reaccion": -5}, 4: {"henchmen": 1, "lealtad": -5, "reaccion": -4},
    5: {"henchmen": 2, "lealtad": -4, "reaccion": -3}, 6: {"henchmen": 2, "lealtad": -3, "reaccion": -2},
    7: {"henchmen": 3, "lealtad": -2, "reaccion": -1}, 8: {"henchmen": 3, "lealtad": -1, "reaccion": 0},
    9: {"henchmen": 4, "lealtad": 0, "reaccion": 0}, 10: {"henchmen": 4, "lealtad": 0, "reaccion": 0},
    11: {"henchmen": 4, "lealtad": 0, "reaccion": 0}, 12: {"henchmen": 5, "lealtad": 0, "reaccion": 0},
    13: {"henchmen": 5, "lealtad": 0, "reaccion": 1}, 14: {"henchmen": 6, "lealtad": 1, "reaccion": 2},
    15: {"henchmen": 7, "lealtad": 3, "reaccion": 3}, 16: {"henchmen": 8, "lealtad": 4, "reaccion": 5},
    17: {"henchmen": 10, "lealtad": 6, "reaccion": 6}, 18: {"henchmen": 15, "lealtad": 8, "reaccion": 7},
    19: {"henchmen": 20, "lealtad": 10, "reaccion": 8},
}


# Etiquetas en español para mostrar los sub-stats derivados en la ficha
# imprimible (estilo hoja oficial), en vez del volcado en crudo "clave:valor".
FUE_DERIVADOS_LABELS = {"ataque": "Prob. golpe", "daño": "Aj. daño", "peso_autorizado": "Peso autoriz. (kg)",
                         "esfuerzo_max": "Esfuerzo máx. (kg)", "puertas": "Abrir puertas (d6)",
                         "barrotes": "Doblar barrotes %"}
DES_DERIVADOS_LABELS = {"reaccion": "Aj. reacción", "ataque_proyectil": "Aj. ataque proyectil", "ca": "Aj. CA"}
CON_DERIVADOS_LABELS = {"pg": "Aj. PG/dado", "shock": "Superv. shock %", "resurrec": "Superv. resurrec. %"}
INT_DERIVADOS_LABELS = {"idiomas": "Idiomas adic.", "nivel_max_conjuro": "Nivel máx. conjuro",
                         "aprender": "Aprender conjuro %", "maxconj": "Máx. conjuros/nivel"}
SAB_DERIVADOS_LABELS = {"salvacion_magica": "Aj. salv. mágica", "fallo": "Fallo conjuro %",
                         "conjuros_bonus": "Conjuros bonus"}
CAR_DERIVADOS_LABELS = {"henchmen": "Nº secuaces", "lealtad": "Aj. lealtad", "reaccion": "Aj. reacción"}

DERIVADOS_LABELS = {
    "fue": FUE_DERIVADOS_LABELS, "des": DES_DERIVADOS_LABELS, "con": CON_DERIVADOS_LABELS,
    "int": INT_DERIVADOS_LABELS, "sab": SAB_DERIVADOS_LABELS, "car": CAR_DERIVADOS_LABELS,
}


# ── Habilidades de ladrón (Tablas 26-29, Manual del Jugador) ────────────────
# Fuente: verificadas contra el PDF de texto el 2026-09-01.
PERICIAS_LADRON_LABELS = {
    "vaciar_bolsillos": "Vaciar bolsillos", "abrir_cerraduras": "Abrir cerraduras",
    "hallar_trampas": "Hallar/retirar trampas", "moverse_silencio": "Moverse en silencio",
    "ocultarse_sombras": "Ocultarse en las sombras", "detectar_ruidos": "Detectar ruidos",
    "escalar_paredes": "Escalar paredes", "leer_lenguajes": "Leer lenguajes",
}

# Tabla 26: Puntuaciones base de habilidad, Ladrón (nivel 1, antes de ajustes)
PERICIAS_LADRON_BASE = {
    "vaciar_bolsillos": 15, "abrir_cerraduras": 10, "hallar_trampas": 5,
    "moverse_silencio": 10, "ocultarse_sombras": 5, "detectar_ruidos": 15,
    "escalar_paredes": 60, "leer_lenguajes": 0,
}

# Tabla 27: Ajustes por raza. Humano y Semiorco no aparecen en la tabla del
# manual (sin ajuste racial a estas habilidades).
PERICIAS_LADRON_RAZA = {
    "Enano": {"abrir_cerraduras": 10, "hallar_trampas": 15, "escalar_paredes": -10, "leer_lenguajes": -5},
    "Elfo": {"vaciar_bolsillos": 5, "abrir_cerraduras": -5, "moverse_silencio": 5,
             "ocultarse_sombras": 10, "detectar_ruidos": 5},
    "Gnomo": {"abrir_cerraduras": 5, "hallar_trampas": 10, "moverse_silencio": 5,
              "ocultarse_sombras": 5, "detectar_ruidos": 10, "escalar_paredes": -15},
    "Semielfo": {"vaciar_bolsillos": 10, "ocultarse_sombras": 5},
    "Halfling": {"vaciar_bolsillos": 5, "abrir_cerraduras": 5, "hallar_trampas": 5,
                 "moverse_silencio": 10, "ocultarse_sombras": 15, "detectar_ruidos": 5,
                 "escalar_paredes": -15, "leer_lenguajes": -5},
}

# Tabla 28: Ajustes por Destreza. Solo estas 5 habilidades se ven afectadas
# por Destreza; 13-15 es el rango neutro (sin ajuste, como el resto de tablas
# de característica de este fichero).
_PERICIAS_LADRON_DESTREZA_TABLA = {
    9: {"vaciar_bolsillos": -15, "abrir_cerraduras": -10, "hallar_trampas": -10, "moverse_silencio": -20, "ocultarse_sombras": -10},
    10: {"vaciar_bolsillos": -10, "abrir_cerraduras": -5, "hallar_trampas": -10, "moverse_silencio": -15, "ocultarse_sombras": -5},
    11: {"vaciar_bolsillos": -5, "hallar_trampas": -5, "moverse_silencio": -10},
    12: {"moverse_silencio": -5},
    16: {"abrir_cerraduras": 5},
    17: {"vaciar_bolsillos": 5, "abrir_cerraduras": 10, "moverse_silencio": 5, "ocultarse_sombras": 5},
    18: {"vaciar_bolsillos": 10, "abrir_cerraduras": 15, "hallar_trampas": 5, "moverse_silencio": 10, "ocultarse_sombras": 10},
    19: {"vaciar_bolsillos": 15, "abrir_cerraduras": 20, "hallar_trampas": 10, "moverse_silencio": 15, "ocultarse_sombras": 15},
}

# Tabla 29: Ajustes por armadura. Son los 3 únicos estados que cubre el
# manual — cualquier armadura más pesada deja las habilidades inutilizables.
PERICIAS_LADRON_ARMADURA = {
    "Sin armadura": {"vaciar_bolsillos": 5, "moverse_silencio": 10, "ocultarse_sombras": 5, "escalar_paredes": 10},
    "Cuero acolchado o tachonado": {},  # línea base normal del ladrón — sin ajuste
    "Cota de mallas élfica": {"vaciar_bolsillos": -20, "abrir_cerraduras": -5, "hallar_trampas": -5,
                               "moverse_silencio": -10, "ocultarse_sombras": -10, "detectar_ruidos": -5,
                               "escalar_paredes": -20},
}


def _pericias_ladron_destreza(des) -> dict:
    des = int(des or 13)
    if des <= 9:
        return _PERICIAS_LADRON_DESTREZA_TABLA[9]
    if des >= 19:
        return _PERICIAS_LADRON_DESTREZA_TABLA[19]
    return _PERICIAS_LADRON_DESTREZA_TABLA.get(des, {})


def calcular_pericias_ladron(raza: str | None, des, armadura: str | None) -> dict:
    """Total por habilidad = base (Tabla 26) + ajuste racial (27) + ajuste de
    Destreza (28) + ajuste de armadura (29), en % (nivel 1 — a partir de ahí
    el jugador reparte puntos adicionales al subir de nivel, algo que esta
    tabla no cubre por sí sola; el resultado es el punto de partida correcto,
    no el valor final garantizado a niveles superiores)."""
    raza_adj = PERICIAS_LADRON_RAZA.get(raza or "", {})
    des_adj = _pericias_ladron_destreza(des)
    armadura_adj = PERICIAS_LADRON_ARMADURA.get(armadura or "Sin armadura", {})
    return {
        skill: max(0, base + raza_adj.get(skill, 0) + des_adj.get(skill, 0) + armadura_adj.get(skill, 0))
        for skill, base in PERICIAS_LADRON_BASE.items()
    }


def derivados_caracteristica(tabla: dict, valor: int) -> dict:
    valor = max(3, min(max(tabla.keys()), int(valor or 10)))
    return tabla.get(valor, {})
