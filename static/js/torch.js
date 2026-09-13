/**
 * Overlay de la "🔥 Antorcha" en la pantalla de jugador (AD&D2e y
 * derivados). Consulta /api/torch/state cada segundo y decide sola si se
 * muestra y qué fase de consumo dibuja (5 fotogramas de llena a apagada) —
 * sin número de tiempo, el contador exacto solo se ve en el máster, para
 * no romper la inmersión con una cifra en pantalla. Independiente del
 * sistema de comandos de pantalla (screen_command.json) — se superpone a
 * cualquier otro contenedor sin sustituirlo.
 */
(function () {
  const overlay = document.getElementById('torch-overlay');
  const svgWrap = document.getElementById('torch-svg-wrap');
  if (!overlay || !svgWrap) return;

  // 5 fases de consumo, de llena a apagada. `min` es el % de tiempo
  // restante (0-1) a partir del cual se usa esa fase.
  const STAGES = [
    { min: 0.76, color: '#ffce54', color2: '#ff8c1a', height: 70, label: 'llena' },
    { min: 0.51, color: '#ffb347', color2: '#ff7518', height: 55, label: 'fuerte' },
    { min: 0.26, color: '#ff9d42', color2: '#e8590c', height: 40, label: 'media' },
    { min: 0.01, color: '#e84118', color2: '#a11607', height: 22, label: 'casi-apagada' },
    { min: 0, color: null, color2: null, height: 0, label: 'apagada' },
  ];

  function pickStage(pct) {
    for (const s of STAGES) {
      if (pct >= s.min) return s;
    }
    return STAGES[STAGES.length - 1];
  }

  function flameSvg(stage) {
    if (!stage.color) {
      // Apagada: solo el palo y un hilo de humo.
      return `
        <svg width="110" height="200" viewBox="0 0 110 200">
          <rect x="47" y="90" width="16" height="105" rx="4" fill="#4a3323"/>
          <path d="M55 90 Q45 70 55 55 Q65 40 53 20" stroke="#999" stroke-width="4"
                fill="none" stroke-linecap="round" opacity="0.5" class="torch-smoke"/>
        </svg>`;
    }
    const h = stage.height;
    return `
      <svg width="110" height="200" viewBox="0 0 110 200">
        <rect x="47" y="90" width="16" height="105" rx="4" fill="#6b4423"/>
        <rect x="43" y="82" width="24" height="14" rx="3" fill="#3a2814"/>
        <g class="torch-flame">
          <path d="M55 ${90 - h} C 25 ${90 - h * 0.4}, 29 ${90 - h * 0.05}, 55 90
                   C 81 ${90 - h * 0.05}, 85 ${90 - h * 0.4}, 55 ${90 - h}Z"
                fill="${stage.color2}"/>
          <path d="M55 ${90 - h * 0.72} C 37 ${90 - h * 0.32}, 39 ${90 - h * 0.04}, 55 90
                   C 71 ${90 - h * 0.04}, 73 ${90 - h * 0.32}, 55 ${90 - h * 0.72}Z"
                fill="${stage.color}"/>
        </g>
      </svg>`;
  }

  let lastLabel = null;

  function render(state) {
    if (!state || (!state.is_running && state.remaining_seconds <= 0)) {
      overlay.style.display = 'none';
      lastLabel = null;
      return;
    }
    overlay.style.display = 'flex';
    const pct = state.duration_seconds > 0 ? state.remaining_seconds / state.duration_seconds : 0;
    const stage = pickStage(pct);
    if (stage.label !== lastLabel) {
      svgWrap.innerHTML = flameSvg(stage);
      lastLabel = stage.label;
    }
  }

  async function poll() {
    try {
      const res = await fetch('/api/torch/state');
      const data = await res.json();
      if (data.success) render(data);
    } catch (e) {
      console.error('torch poll error', e);
    }
  }

  poll();
  setInterval(poll, 1000);
})();
