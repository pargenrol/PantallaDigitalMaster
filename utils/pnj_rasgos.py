"""
Catálogo de rasgos de personalidad para PNJs, agnóstico de sistema y de
campaña (contenido 100% original, no ligado a ninguna ambientación
concreta) — se usa tanto para construir el prompt de la descripción por IA
como para componer la descripción de plantilla cuando no se usa IA.
"""

RASGOS = [
    {"id": "timido", "label": "Tímido", "frase": "evita el contacto visual y responde con monosílabos"},
    {"id": "cruel", "label": "Cruel", "frase": "disfruta viendo incomodar a los demás"},
    {"id": "alto", "label": "Alto", "frase": "destaca por encima de la mayoría"},
    {"id": "bajo", "label": "Bajo", "frase": "es notablemente más bajo de lo normal"},
    {"id": "corpulento", "label": "Corpulento", "frase": "tiene una complexión ancha y fuerte"},
    {"id": "esmirriado", "label": "Esmirriado", "frase": "es delgado hasta resultar frágil a la vista"},
    {"id": "amable", "label": "Amable", "frase": "trata a cualquiera con calidez, incluso a desconocidos"},
    {"id": "arrogante", "label": "Arrogante", "frase": "habla con superioridad y corrige a los demás sin que se lo pidan"},
    {"id": "nervioso", "label": "Nervioso", "frase": "tamborilea los dedos o cambia el peso de pie constantemente"},
    {"id": "calculador", "label": "Calculador", "frase": "sopesa cada palabra antes de decirla"},
    {"id": "bromista", "label": "Bromista", "frase": "convierte casi cualquier conversación en una broma"},
    {"id": "supersticioso", "label": "Supersticioso", "frase": "lleva amuletos y evita ciertos números o gestos"},
    {"id": "avaro", "label": "Avaro", "frase": "cuenta cada moneda y regatea por costumbre"},
    {"id": "generoso", "label": "Generoso", "frase": "comparte lo que tiene sin que se lo pidan"},
    {"id": "desconfiado", "label": "Desconfiado", "frase": "duda de las intenciones de cualquier forastero"},
    {"id": "curioso", "label": "Curioso", "frase": "hace demasiadas preguntas sobre todo lo que ve"},
    {"id": "callado", "label": "Callado", "frase": "habla lo justo y necesario"},
    {"id": "hablador", "label": "Hablador", "frase": "cuesta hacerle parar de hablar una vez empieza"},
    {"id": "cicatrizado", "label": "Cicatrizado", "frase": "tiene una cicatriz visible que llama la atención"},
    {"id": "elegante", "label": "Elegante", "frase": "cuida su aspecto incluso en circunstancias humildes"},
    {"id": "desaliñado", "label": "Desaliñado", "frase": "viste con descuido, como si no le importara"},
    {"id": "valiente", "label": "Valiente", "frase": "no se arredra ante el peligro, a veces sin necesidad"},
    {"id": "cobarde", "label": "Cobarde", "frase": "busca la salida más cercana en cuanto hay tensión"},
    {"id": "leal", "label": "Leal", "frase": "antepone a los suyos por encima de casi cualquier cosa"},
    {"id": "ambicioso", "label": "Ambicioso", "frase": "siempre está calculando su siguiente paso hacia algo mejor"},
    {"id": "melancolico", "label": "Melancólico", "frase": "arrastra una tristeza de fondo que rara vez explica"},
    {"id": "jovial", "label": "Jovial", "frase": "se ríe con facilidad y contagia buen humor"},
    {"id": "obsesivo", "label": "Obsesivo", "frase": "vuelve una y otra vez sobre el mismo tema o manía"},
]


def rasgos_por_ids(ids: list[str]) -> list[dict]:
    ids = set(ids or [])
    return [r for r in RASGOS if r["id"] in ids]
