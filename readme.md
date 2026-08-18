# 🐉 DM Command Center (Pantalla de Máster Digital)

Una aplicación web diseñada para **Game Masters de Rol** que buscan gestionar sus partidas de forma fluida. Combina un panel de control privado para el Máster con una "Pantalla de Jugador" que se proyecta en un monitor secundario o TV.

> **v2.0 — Rama `multisistema`.** Esta rama es una versión sustancialmente ampliada respecto a la última versión mergeada en `main` (marzo 2026): ha pasado de un único sistema de juego a **9 sistemas** distintos, con un asistente de IA propio por sistema (RAG sobre una biblioteca de PDFs), gestión completa de fichas de personaje, y varias pantallas nuevas. Ver la sección **"Novedades de esta rama"** más abajo para el detalle completo de qué es nuevo respecto a lo que ya existía.

## ✨ Características Principales

* **🎲 9 sistemas de juego**, cada uno con tema visual, asistente IA y esquema de reglas propios: D&D 5ª Edición, AD&D 2ª Edición, Dark Sun, Ravenloft (en versión 5e y AD&D2e), Greyhawk, Reinos Olvidados, Mothership RPG y un sistema Agnóstico para cualquier otro juego.
* **📺 Pantalla Dual:**
    * **Vista de Máster:** control total de iniciativa, pizarra táctica, grimorio, reglas y fichas de personaje.
    * **Vista de Jugador:** interfaz limpia para mostrar imágenes, mapas y "tarjetas" de hechizos/monstruos cuando el Máster lo decide.
* **📱 Vistas táctiles para tablet** (`/view`): dashboard, rastreador de iniciativa, grimorio con filtros, pizarra y control de audio — pensadas para llevarlas aparte de la pantalla principal, con sincronización en tiempo real con el máster.
* **⚔️ Gestión de Iniciativa:** turnos, vida/estrés y estados de forma dinámica, con calculadora de puntos de experiencia de combate.
* **📇 Fichas de personaje jugables**, con esquema propio por sistema — en AD&D 2ª Edición incluye selector de raza/clase con bonus automáticos, cálculo de GAC0 y puntos de golpe, pericias, idiomas, conjuros y ficha imprimible con retrato.
* **🎨 Pizarra Interactiva (Whiteboard):** dibuja bocetos rápidos o diagramas de combate en tiempo real (Fabric.js).
* **📚 Grimorio Auto-gestionado:** carga monstruos, hechizos, reglas y jugadores desde archivos locales `.md` (Markdown), con filtros de clasificación por sistema (nivel/escuela en conjuros, Dados de Golpe en monstruos de AD&D2e).
* **🤖 Asistente IA con RAG:** un asistente conversacional por sistema (streaming en tiempo real) que responde con contexto de una biblioteca de PDFs indexada — requiere tu propia biblioteca y un servidor Ollama local (ver más abajo).
* **🗺️ Explorador de campañas:** navega y fija notas/campañas de tu vault de Obsidian directamente desde el panel de máster.

## 📂 Estructura del Proyecto

* `app.py`: servidor Flask principal, registra los blueprints de `routes/`.
* `systems/registry.py`: registro de los 9 sistemas de juego y sus esquemas de campos.
* `routes/`: blueprints de la aplicación (vistas, combate, jugadores, asistente IA, campañas, encuentros, etc.).
* `templates/`: HTML de las vistas (`master.html`, `player.html`, fichas de personaje, vistas de tablet).
* `static/`: CSS (un tema por sistema), JavaScript del cliente y assets.
* `resources/{sistema}/{monsters,spells,rules,players}/`: el grimorio en Markdown — **no se incluye en el repositorio** por derechos de autor de los manuales; cada instalación añade el suyo (ver más abajo).
* `utils/`: indexador y consulta del RAG, utilidades de carga de contenido.

## 🚀 Instalación y Uso

### Requisitos Previos
* Python 3.11 o superior.
* Con el instalador, se instalan tanto Python como las librerías necesarias.
* (Opcional, solo para el asistente IA) [Ollama](https://ollama.ai) corriendo en local con los modelos `nomic-embed-text` y `qwen2.5:7b-instruct-q4_K_M`.

### Instalación Rápida
1. **Clona el repositorio.**
2. Ejecuta el script de instalación automática:
    * **Windows:** doble clic en `install.bat`.
    * **Mac/Linux:** ejecuta `./install.sh` en la terminal (`chmod +x install.sh` si hace falta permisos).
3. Añade tu propio contenido de grimorio en `resources/{sistema}/` — el repo no trae ninguno por defecto (ver "Nota Legal").

### Ejecución
1. Ejecuta `run.bat` (Windows) o `./run.sh` (Mac/Linux).
2. El navegador abrirá el **Panel del Máster** (por defecto en `http://localhost:5000/master`, configurable por variable de entorno `PORT`).
3. Se abren 2 ventanas: la de máster en el monitor principal y la de jugador en el monitor secundario.

### Sin biblioteca de PDFs ni Ollama
La aplicación funciona igual sin ninguna de las dos cosas — gestión de partida, iniciativa, fichas, pizarra y vistas de tablet no dependen del RAG. Lo único que no funciona sin Ollama corriendo es el asistente de IA (sin fallback); sin PDFs propios indexados, el asistente simplemente no tendrá contexto de manuales sobre el que responder.

---

## 🆕 Novedades de esta rama (`multisistema`) respecto a `main`

La versión en `main` era de un único sistema de juego (D&D 5e/SRD). Esta rama añade:

- **8 sistemas de juego más** (AD&D 2ª Edición, Dark Sun, Ravenloft en dos versiones, Greyhawk, Reinos Olvidados, Mothership, Agnóstico), cada uno con tema visual, asistente y esquema de campos propio.
- **Sistema completo de fichas de personaje AD&D 2ª Edición**: raza/clase con bonus automáticos, GAC0 (el nombre real del THAC0 en el manual español) y puntos de golpe calculados por nivel, pericias en armas/no-armas, idiomas, selector de conjuros, habilidades de clase, ficha imprimible con retrato.
- **Retratos ligados a monstruos y jugadores** (pegar/recortar imagen desde el portapapeles).
- **Asistente IA por sistema con RAG** sobre una biblioteca de PDFs propia, con memoria persistente por asistente.
- **Clasificación y filtros del grimorio**: por Dados de Golpe en Bestiario (AD&D2e no tiene "nivel de desafío" como 5e) y por Clase/Nivel/Escuela en Conjuros.
- **Calculadora de puntos de experiencia de combate**: suma el PX real de los monstruos de la iniciativa y lo reparte entre los jugadores.
- **5 vistas para tablet** (`/view/*`) con sincronización en tiempo real con la pantalla de máster.
- **Explorador de campañas** contra un vault de Obsidian, con filtro de campaña fijada.
- **Generador de encuentros** (D&D 5e, tablas de PX del DMG).

---

**Nota Legal:** Este proyecto utiliza contenido del SRD bajo la Open Game License (OGL) allá donde aplica. El resto del contenido de manuales (`resources/`) **no se incluye en este repositorio** por tratarse de material con derechos de autor — cada usuario debe añadir el suyo propio tras clonar. Lo mismo aplica a cualquier biblioteca de PDFs usada para el asistente de IA.
