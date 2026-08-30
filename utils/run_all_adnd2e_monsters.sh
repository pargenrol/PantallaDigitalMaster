#!/usr/bin/env bash
# Orquesta la generación completa del bestiario genérico AD&D2e:
# Manual Monstruoso Vol I (en curso al lanzar este script) -> Vol II ->
# Monstrous Compendium Annual 1-4 (inglés). Tras cada libro, propaga las
# fichas nuevas (no las que ya existan) a greyhawk, forgotten_realms y
# ravenloft_adnd, que comparten el mismo bestiario genérico que adnd2e.
set -uo pipefail
cd "$(dirname "$0")/.."

LOG_DIR="instance"
BIB="$(cd .. && pwd)/rol-biblioteca/biblioteca/Dungeons & Dragons/AD&D 2ª edición/Core y Suplementos"
CANON="resources/adnd2e/monsters"
TARGETS=(resources/greyhawk/monsters resources/forgotten_realms/monsters resources/ravenloft_adnd/monsters)

propagate() {
    echo "=== Propagando fichas nuevas de $CANON a los demás sistemas AD&D2e ==="
    for t in "${TARGETS[@]}"; do
        mkdir -p "$t"
        count=0
        for f in "$CANON"/*.md; do
            base=$(basename "$f")
            [[ "$base" == _revisar_* ]] && continue
            if [[ ! -f "$t/$base" ]]; then
                cp "$f" "$t/$base"
                count=$((count+1))
            fi
        done
        echo "  -> $t: $count fichas copiadas"
    done
}

wait_for_pid() {
    local pid=$1
    while kill -0 "$pid" 2>/dev/null; do
        sleep 10
    done
}

echo ">>> Esperando a que termine la generación del Volumen I (si sigue en curso)..."
# El proceso del Volumen I ya se lanzó fuera de este script; esperamos a que
# termine buscando su PID por línea de comandos.
VOL1_PID=$(pgrep -f "generate_monster_md_adnd2e.py$" | head -1)
if [[ -n "${VOL1_PID:-}" ]]; then
    wait_for_pid "$VOL1_PID"
fi
echo ">>> Volumen I terminado."
propagate

echo ">>> Generando Manual Monstruoso Volumen II..."
venv/bin/python3 utils/generate_monster_md_adnd2e.py \
    --pdf "$BIB/AD&D 2.2 - Manual Monstruoso Volumen II [Martinez Roca].pdf" \
    --out "$CANON" \
    > "$LOG_DIR/generate_monsters_adnd2e_vol2.log" 2>&1
echo ">>> Volumen II terminado."
propagate

ANNUALS=(
  "TSR 2145 Monstrous Compendium Annual Volume 1.pdf|annual1"
  "TSR 2158 Monstrous Compendium Annual Volume 2.pdf|annual2"
  "TSR 2166 Monstrous Compendium Annual Volume 3.pdf|annual3"
  "TSR 2173 Monstrous Compendium Annual Volume 4.pdf|annual4"
)

for entry in "${ANNUALS[@]}"; do
    fname="${entry%%|*}"
    tag="${entry##*|}"
    echo ">>> Generando $fname (inglés)..."
    venv/bin/python3 utils/generate_monster_md_adnd2e.py \
        --pdf "$BIB/$fname" \
        --out "$CANON" \
        --lang en \
        > "$LOG_DIR/generate_monsters_adnd2e_${tag}.log" 2>&1
    echo ">>> $fname terminado."
    propagate
done

echo ">>> PIPELINE COMPLETO. Resúmenes en $LOG_DIR/generate_monsters_adnd2e*.log"
