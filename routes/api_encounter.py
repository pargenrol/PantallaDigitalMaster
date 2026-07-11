import random
from collections import Counter
from flask import Blueprint, jsonify, request, session
from systems.registry import get_system, DEFAULT_SYSTEM
from utils.markdown_content import load_markdown_content

bp = Blueprint("api_encounter", __name__)

# DMG 5e — XP thresholds per character per level
XP_THRESHOLDS = {
    1:  {"easy": 25,   "medium": 50,   "hard": 75,   "deadly": 100},
    2:  {"easy": 50,   "medium": 100,  "hard": 150,  "deadly": 200},
    3:  {"easy": 75,   "medium": 150,  "hard": 225,  "deadly": 400},
    4:  {"easy": 125,  "medium": 250,  "hard": 375,  "deadly": 500},
    5:  {"easy": 250,  "medium": 500,  "hard": 750,  "deadly": 1100},
    6:  {"easy": 300,  "medium": 600,  "hard": 900,  "deadly": 1400},
    7:  {"easy": 350,  "medium": 750,  "hard": 1100, "deadly": 1700},
    8:  {"easy": 450,  "medium": 900,  "hard": 1400, "deadly": 2100},
    9:  {"easy": 550,  "medium": 1100, "hard": 1600, "deadly": 2400},
    10: {"easy": 600,  "medium": 1200, "hard": 1900, "deadly": 2800},
    11: {"easy": 800,  "medium": 1600, "hard": 2400, "deadly": 3600},
    12: {"easy": 1000, "medium": 2000, "hard": 3000, "deadly": 4500},
    13: {"easy": 1100, "medium": 2200, "hard": 3400, "deadly": 5100},
    14: {"easy": 1250, "medium": 2500, "hard": 3800, "deadly": 5700},
    15: {"easy": 1400, "medium": 2800, "hard": 4300, "deadly": 6400},
    16: {"easy": 1600, "medium": 3200, "hard": 4800, "deadly": 7200},
    17: {"easy": 2000, "medium": 3900, "hard": 5900, "deadly": 8800},
    18: {"easy": 2100, "medium": 4200, "hard": 6300, "deadly": 9500},
    19: {"easy": 2400, "medium": 4900, "hard": 7300, "deadly": 10900},
    20: {"easy": 2800, "medium": 5700, "hard": 8500, "deadly": 12700},
}

CR_TO_XP = {
    "0": 10, "1/8": 25, "1/4": 50, "1/2": 100,
    "1": 200, "2": 450, "3": 700, "4": 1100,
    "5": 1800, "6": 2300, "7": 2900, "8": 3900,
    "9": 5000, "10": 5900, "11": 7200, "12": 8400,
    "13": 10000, "14": 11500, "15": 13000, "16": 15000,
    "17": 18000, "18": 20000, "19": 22000, "20": 25000,
    "21": 33000, "22": 41000, "23": 50000, "24": 62000,
    "25": 75000, "26": 90000, "27": 105000, "28": 120000,
    "29": 135000, "30": 155000,
}

CR_FLOAT = {
    "0": 0, "1/8": 0.125, "1/4": 0.25, "1/2": 0.5,
    **{str(i): float(i) for i in range(1, 31)},
}

DIFFICULTY_LABELS = {
    "easy": "Fácil", "medium": "Media", "hard": "Difícil", "deadly": "Mortal"
}

# Prefijos de tipo de criatura que aplican a cada ecología.
# Se compara contra el inicio del campo "tipo" (case-insensitive).
ECOLOGY_TIPOS = {
    "bosque":     {"bestia", "monstruosidad", "planta", "feérica", "feérico", "hada", "humanoide", "gigante"},
    "pradera":    {"bestia", "monstruosidad", "humanoide", "gigante", "dragón"},
    "montana":    {"bestia", "monstruosidad", "gigante", "dragón", "elemental"},
    "pantano":    {"bestia", "monstruosidad", "planta", "muerto", "no-muerto", "aberración"},
    "costa":      {"bestia", "monstruosidad", "elemental", "dragón", "humanoide"},
    "artico":     {"bestia", "monstruosidad", "gigante", "elemental"},
    "desierto":   {"bestia", "monstruosidad", "humanoide", "elemental", "muerto", "no-muerto"},
    "urbano":     {"humanoide", "monstruosidad", "constructo", "muerto", "no-muerto", "infernal", "demonio", "autómata"},
    "mazmorra":   {"aberración", "monstruosidad", "constructo", "muerto", "no-muerto", "semiliche", "infernal",
                   "demonio", "humanoide", "dragón", "elemental", "autómata"},
    "paramo":     {"monstruosidad", "gigante", "dragón", "muerto", "no-muerto", "humanoide", "infernal", "aberración"},
    "inframundo": {"aberración", "monstruosidad", "infernal", "demonio", "elemental", "dragón", "humanoide",
                   "muerto", "no-muerto", "constructo"},
}

ECOLOGY_LABELS = {
    "bosque":     "Bosque",
    "pradera":    "Pradera / Llanura",
    "montana":    "Montaña",
    "pantano":    "Pantano",
    "costa":      "Costa / Acuático",
    "artico":     "Ártico",
    "desierto":   "Desierto",
    "urbano":     "Urbano",
    "mazmorra":   "Mazmorra / Subterráneo",
    "paramo":     "Páramo / Colinas",
    "inframundo": "Planos / Inframundo",
}


def _multiplier(n, party_size):
    """DMG XP multiplier for n monsters, adjusted for party size."""
    if n == 1:
        base = 1.0
    elif n == 2:
        base = 1.5
    elif n <= 6:
        base = 2.0
    elif n <= 10:
        base = 2.5
    elif n <= 14:
        base = 3.0
    else:
        base = 4.0

    steps = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
    idx = steps.index(base)
    if party_size < 3:
        idx = min(idx + 1, len(steps) - 1)
    elif party_size > 5:
        idx = max(idx - 1, 0)
    return steps[idx]


def _parse_cr(challenge_str):
    """Return (cr_key, xp) from a challenge field value, or (None, None)."""
    if not challenge_str:
        return None, None
    s = str(challenge_str).strip().strip("\"'")
    cr = s.split("(")[0].strip().split()[0]
    xp = CR_TO_XP.get(cr)
    return (cr, xp) if xp is not None else (None, None)


def _matches_ecology(tipo_str, ecology_key):
    """True if the creature type prefix matches the ecology."""
    if not ecology_key or ecology_key not in ECOLOGY_TIPOS:
        return True  # no filter
    if not tipo_str:
        return True  # unknown type — include by default
    allowed = ECOLOGY_TIPOS[ecology_key]
    tipo_lower = str(tipo_str).lower()
    return any(tipo_lower.startswith(t) for t in allowed)


@bp.route("/api/encounter/generate")
def generate_encounter():
    system = get_system(session.get("active_system", DEFAULT_SYSTEM))
    res = system["resources"]

    try:
        level = max(1, min(20, int(request.args.get("level", 1))))
        party_size = max(1, min(10, int(request.args.get("size", 4))))
    except (ValueError, TypeError):
        return jsonify({"error": "Parámetros inválidos"}), 400

    difficulty = request.args.get("difficulty", "medium")
    if difficulty not in XP_THRESHOLDS[1]:
        difficulty = "medium"

    max_cr_str = request.args.get("max_cr", "").strip()
    max_cr_float = CR_FLOAT.get(max_cr_str) if max_cr_str else None

    ecology = request.args.get("ecology", "").strip().lower()

    # XP budgets
    xp_budget = XP_THRESHOLDS[level][difficulty] * party_size
    diff_order = ["easy", "medium", "hard", "deadly"]
    next_diff = diff_order[diff_order.index(difficulty) + 1] if difficulty != "deadly" else None
    upper_budget = (XP_THRESHOLDS[level][next_diff] * party_size) if next_diff else None

    # Load and filter monsters
    all_monsters = load_markdown_content(res["monsters"])
    candidates = []
    for m in all_monsters:
        raw = m.get("challenge") or m.get("cr") or m.get("desafio")
        cr, xp = _parse_cr(raw)
        if cr is None:
            continue
        if max_cr_float is not None and CR_FLOAT.get(cr, 999) > max_cr_float:
            continue
        tipo = m.get("tipo") or m.get("type") or ""
        if not _matches_ecology(tipo, ecology):
            continue
        candidates.append({**m, "_cr": cr, "_xp": xp})

    if not candidates:
        return jsonify({"error": "No hay monstruos disponibles con los filtros indicados"}), 400

    # Build encounter
    encounter = []
    total_raw_xp = 0

    for _ in range(300):
        if not candidates:
            break

        monster = random.choice(candidates)
        test_raw = total_raw_xp + monster["_xp"]
        test_n = len(encounter) + 1
        adjusted = int(test_raw * _multiplier(test_n, party_size))

        if upper_budget and adjusted > upper_budget:
            continue

        encounter.append(monster)
        total_raw_xp += monster["_xp"]

        adjusted = int(total_raw_xp * _multiplier(len(encounter), party_size))
        if adjusted >= xp_budget:
            break

    if not encounter:
        return jsonify({"error": "No se pudo generar un encuentro con el presupuesto indicado"}), 400

    multiplier = _multiplier(len(encounter), party_size)
    adjusted_xp = int(total_raw_xp * multiplier)

    # Actual difficulty
    actual_diff = "easy"
    for d in diff_order:
        if adjusted_xp >= XP_THRESHOLDS[level][d] * party_size:
            actual_diff = d

    # Group by name for display
    name_counts = Counter(m["nombre"] for m in encounter)
    seen = set()
    grouped = []
    for m in encounter:
        if m["nombre"] not in seen:
            seen.add(m["nombre"])
            grouped.append({
                "nombre": m["nombre"],
                "slug": m["slug"],
                "cr": m["_cr"],
                "xp_unit": m["_xp"],
                "xp_total": m["_xp"] * name_counts[m["nombre"]],
                "count": name_counts[m["nombre"]],
                "tipo": m.get("tipo") or m.get("type") or "",
                "hp": m.get("hp") or 10,
            })

    return jsonify({
        "encounter": grouped,
        "total_raw_xp": total_raw_xp,
        "adjusted_xp": adjusted_xp,
        "multiplier": multiplier,
        "difficulty": DIFFICULTY_LABELS[actual_diff],
        "difficulty_key": actual_diff,
        "xp_budget": xp_budget,
        "level": level,
        "party_size": party_size,
    })


@bp.route("/api/encounter/ecologies")
def list_ecologies():
    return jsonify(ECOLOGY_LABELS)
