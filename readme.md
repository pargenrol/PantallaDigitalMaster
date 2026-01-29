# 🐉 DM Command Center (Pantalla de Máster Digital)

Una aplicación web diseñada para **Game Masters de Rol** que buscan gestionar sus partidas de forma fluida. Combina un panel de control privado para el Máster con una "Pantalla de Jugador" que se proyecta en un monitor secundario o TV.

## ✨ Características Principales

* **📺 Pantalla Dual:**
    * **Vista de Máster:** Control total de iniciativa, pizarra táctica, grimorio y reglas.
    * **Vista de Jugador:** Una interfaz limpia para mostrar imágenes, mapas y "tarjetas" de hechizos/monstruos cuando el Máster lo decide.
* **⚔️ Gestión de Iniciativa:** Controla turnos, vida y estados de forma dinámica.
* **🎨 Pizarra Interactiva (Whiteboard):** Dibuja bocetos rápidos o diagramas de combate en tiempo real (basado en Fabric.js).
* **📚 Grimorio Auto-gestionado:** Carga monstruos, hechizos y reglas desde archivos locales `.md` (Markdown).
* **📥 Scripts de Contenido:** Incluye herramientas para descargar contenido OGL (SRD) automáticamente.

## 📂 Estructura del Proyecto

* `app.py`: Servidor Flask principal.
* `templates/`: HTML de las vistas (`master.html`, `player.html`).
* `static/`: CSS, JavaScript del cliente y assets.
* `data/`: Base de datos en texto plano.
    * `monsters/`, `spells/`, `rules/`: Aquí viven tus archivos `.md`.
* `scripts/`: Scripts en Python para descargar contenido del SRD.

## 🚀 Instalación y Uso

### Requisitos Previos
* Python 3.8 o superior.

### Instalación Rápida
1.  **Clona el repositorio** o descarga los archivos.
2.  Ejecuta el script de instalación automática:
    * **Windows:** Doble clic en `install.bat`.
    * **Mac/Linux:** Ejecuta `./install.sh` en la terminal. **es necesario dar permisos de ejecución chmod +x**
3.  (Opcional) Ejecuta los scripts de descarga en la carpeta `scripts/` para poblar tu base de datos inicial.

### Ejecución
1.  Ejecuta `run.bat` (Windows) o `./run.sh` (Mac/Linux). **es necesario dar permisos de ejecución**
2.  El navegador abrirá el **Panel del Máster** automáticamente (usualmente en `http://localhost:5000/master`).
3.  Se abren 2 ventanas la de master en el monitor principal y la de jugador en monitor secundario.

---
**Nota Legal:** Este proyecto utiliza contenido del SRD bajo la Open Game License (OGL).
