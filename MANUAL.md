# Manual de instalación y uso — Pantallasistemas

Guía completa para instalar tu propia copia y usarla en tus partidas. Para la lista de características y la nota legal sobre el contenido con derechos de autor, ver [`readme.md`](readme.md); este documento se centra en el paso a paso.

## 1. Instalación

### Requisitos

* Python 3.11 o superior.
* (Opcional) [Ollama](https://ollama.ai) instalado si quieres un asistente de IA local y gratuito. Sin él, puedes usar Claude (de pago, con tu propia clave) o no usar asistente en absoluto — el resto de la app funciona igual.
* (Opcional) [rol-biblioteca](https://github.com/pargenrol/biblioteca-rol) instalada como carpeta hermana, si quieres que el asistente responda citando tus PDFs de manuales.

### Pasos

1. Clona el repositorio.
2. Instala:
   * **Windows:** doble clic en `install.bat`.
   * **Mac/Linux:** `./install.sh` (`chmod +x install.sh` si hace falta).
3. Añade tu propio contenido de grimorio en `resources/{sistema}/monsters|spells|rules|players/` — el repo no trae ninguno por defecto (ver "Nota Legal" en el readme).
4. Arranca:
   * **Windows:** `run.bat`.
   * **Mac/Linux:** `./run.sh`.
5. Se abre el navegador en `http://localhost:5001/master` (puerto configurable con la variable de entorno `PORT`).

En el primer arranque, la app te pedirá elegir un sistema de juego (D&D 5e, AD&D 2e, Mothership, etc.) — se puede cambiar luego con "⇄ Sistema" en la cabecera.

### Configuración opcional (variables de entorno)

Crea un fichero `.env` en la raíz del proyecto (o dejá que la propia app lo cree al guardar una clave desde la interfaz) con lo que necesites:

| Variable | Para qué | Si no la pones |
|---|---|---|
| `ANTHROPIC_API_KEY` | Usar Claude como modelo del asistente IA | Puedes configurarla luego desde el propio panel de Modelos, sin editar ficheros |
| `VAULT_PARTIDAS` | Ruta a una carpeta de Markdown que sirva de "campaña por defecto" en la pestaña Campañas | La pestaña Campañas arranca vacía — puedes añadir tus propias carpetas desde ahí con el botón "+ Añadir campaña" |
| `BIBLIOTECA_PATH` | Ruta a la carpeta `biblioteca/` de rol-biblioteca, para indexarla con el asistente IA | Por defecto asume que rol-biblioteca está clonada como carpeta hermana (`../rol-biblioteca/biblioteca`) |
| `BIBLIOTECA_URL` / `PORT` de rol-biblioteca | Solo si rol-biblioteca corre en un host o puerto no estándar | El botón "📚 Biblioteca" resuelve la URL automáticamente según cómo accedes a Pantallasistemas |

## 2. Uso

### Pantalla de máster (`/master`) y pantalla de jugador (`/player`)

Diseñada para un equipo con dos pantallas: la de máster (privada, con todos los controles) y la de jugador (se proyecta en un segundo monitor o TV). Desde la pantalla de máster puedes mandar imágenes, cartas de hechizo/monstruo o poner la pantalla de jugador en negro con un clic.

* **Iniciativa:** añade personajes y monstruos, gestiona turnos, vida/estrés y estados; calculadora de puntos de experiencia de combate al final.
* **Pizarra (Whiteboard):** boceta mapas o diagramas de combate en tiempo real.
* **Grimorio** (pestañas superiores, etiquetas según el sistema activo): Monstruos, Conjuros/Hechizos, Reglas — se cargan automáticamente desde `resources/{sistema}/` en formato Markdown con frontmatter.
* **⚔️ Encuentro:** generador de encuentros equilibrados por nivel/dificultad (D&D 5e).
* **👥 Jugadores:** fichas de PJ completas (con esquema propio por sistema) y sub-pestaña de PNJs guardados en el roster.
* **📖 Campañas:** explorador de notas Markdown de tus partidas. Cada campaña es una carpeta independiente:
  * **"+ Añadir campaña"** registra una carpeta nueva (ruta absoluta en el propio servidor — un navegador no puede explorar el disco del servidor, así que se escribe a mano; se crea sola si no existe).
  * Las notas se editan con vista previa en vivo; frontmatter YAML opcional, se conserva si lo tienen.
  * "✕ Quitar" junto a una campaña solo la desregistra — nunca borra los ficheros.
* **🎒 Equipo:** catálogo de objetos reutilizable por PNJs — clic en el nombre de un objeto para ver/editar su descripción y estadísticas.

### Asistente de IA (🤖, esquina inferior)

Un asistente conversacional por sistema, con contexto de tu biblioteca de PDFs (RAG) si la tienes indexada.

* **⚙️ Modelos:** configura Ollama (local, gratis) o Claude (remoto, de pago) sin tocar ficheros — instala/descarga modelos con un clic, o guarda tu clave de Anthropic con un botón de "Probar conexión".
* Si no hay ningún modelo disponible (ni Ollama con modelos instalados ni clave de Claude), el selector se deshabilita con un aviso en vez de fallar al primer mensaje.
* **📖 Memoria:** el asistente recuerda datos que le pidas explícitamente entre conversaciones (por sistema).
* Cuando cita un PDF de tu biblioteca, el enlace abre directamente esa página en rol-biblioteca (si la tienes instalada y accesible).

### Vistas para tablet (`/view`)

Pensadas para llevar aparte en una tablet, sincronizadas en tiempo real con la pantalla de máster: dashboard, iniciativa, grimorio con filtros, pizarra, audio y PNJs.

### Integración con rol-biblioteca (opcional)

Si tienes también [rol-biblioteca](https://github.com/pargenrol/biblioteca-rol) instalada:

* El botón **"📚 Biblioteca"** en la cabecera abre tu biblioteca de PDFs en una pestaña nueva.
* Desde rol-biblioteca, el botón **"🔄 Generar RAG"** le pide a Pantallasistemas que reindexe tu biblioteca sin que tengas que usar la terminal.
* Son proyectos totalmente independientes: si uno de los dos no está instalado o no está corriendo, el otro sigue funcionando igual — solo se pierden estas dos integraciones puntuales.
