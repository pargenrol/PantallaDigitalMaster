# Cómo contribuir

¡Gracias por querer mejorar el DM Command Center! Aquí tienes cómo puedes ayudar.

Este pequeño proyecto está pensado para ir creciendo de manera gradual. Puedes contribuir de la manera que prefieras. Ya sea sugiriendo nuevas mejoras,
creando monstruos o aportando mejoras al código. Este proyecto comenzó a gestarse con Gemini pero tambien se están uniendo inteligencias orgánicas.

## 👾 Añadir Nuevos Monstruos
El sistema lee archivos Markdown de la carpeta `resources/monsters/`.
Para añadir un monstruo, crea un archivo `.md` (ej: `goblin.md`) con el siguiente formato exacto:

```markdown
---
title: Título del montruo
nombre: Nombre del monstruo
tipo: Tipo de monstruo
tamaño: Tamaño del monstruo
alignment: Alineamiento del monstruo
ac: Valor de Clase de Armadura
hp: Puntos de vida medios
hp_roll: Dados de números de vida
desafio: Ratio de desafío
px: Puntos de experiencia
per: Percepción del monstruo
velocidad: Velocidad del monstruo
portrait_path: Ruta a vídeo de animación del monstruo: /static/uploads/videos/nombre_monstruo.mp4
---

### **Características**

| FUE | DES | CON | INT | SAB | CAR |
|:---:|:---:|:---:|:---:|:---:|:---:|
| Valor Fuerza | Valor Destreza | Valor Constitución | Valor Inteligencia | Valor Sabiduría | Valor Carisma |
|(Modificador Fuerza)|(Modificador Destreza)|(Modificador Constitución)|(Modificador Inteligencia)|(Modificador Sabiduría)|(Modificador Carisma)|

### **Sentidos y Idiomas**

**Sentidos:** Sentidos del monstruo 
**Idiomas:** Idiomas del monstruo

- **Habilidad del monstruo.*** Descripción de la habilidad.

### **Acciones**

- **Nombre de la acción.** Descripción de la acción.
```

Se pone como ejemplo la ficha del monstruo Goblin:

```markdown
---
title: Goblin
nombre: Goblin
tipo: trasgo
tamaño: Pequeño
alignment: Neutral Malvado
ac: 15
hp: 7
hp_roll: 2d6
desafio: 1 /4
px: 5O
per: 9
velocidad: 30
portrait_path: /static/uploads/videos/goblin.mp4 
---

### **Características**

| FUE | DES | CON | INT | SAB | CAR |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 8 | 14 | 10 | 10 | 8 | 8 |
|(-1)|(+2)|(+0)|(+0)|(-1)|(-1)|

### **Sentidos y Idiomas**

**Sentidos:** visión en la oscuridad 60 pies, Percepción pasiva 9  
**Idiomas:** común, goblin  

- ***Huida veloz.*** El goblin puede, en cada uno de sus turnos, usar
una acción adicional para Destrabarse o Esconderse. 

### **Acciones**

- **Cimitarra.** Ataque con arma cuerpo a cuerpo: +4 a impactar,
alcance S pies, un objetivo. Impacto: 5 (ld6 + 2) de daño
cortante.
- **Arco corto.** Ataque con arma a distancia: +4 a impactar,
alcance 80/320 pies, un objetivo. Impacto: 5 (ld6 + 2) de daño
perforante.
```

## 📖 Campañas (Markdown)

A diferencia del catálogo de monstruos (que exige el formato exacto de arriba), el explorador de la pestaña **"Campañas"** trabaja con **Markdown libre**: cualquier fichero `.md` que tengas en tu carpeta de campaña aparecerá en el árbol, sin necesidad de seguir ninguna plantilla.

Puntos a tener en cuenta:

- **Frontmatter opcional.** Si el fichero empieza con un bloque `---` en formato YAML (como los monstruos de arriba), se conserva al editar y guardar. Si no lo tiene, no pasa nada — no es obligatorio.
- **Carpetas hasta 2 niveles.** El explorador muestra subcarpetas dentro de tu campaña, pero solo baja 2 niveles de profundidad.
- **Edición con vista previa en vivo.** Al abrir una nota puedes editar el Markdown y ver el resultado renderizado (negritas, listas, tablas, código) sin salir de la pantalla.
- **Varias campañas a la vez.** Desde el botón **"+ Añadir campaña"** puedes registrar tantas carpetas como quieras, cada una en cualquier ruta de tu disco — por ejemplo, una carpeta distinta por partida o por grupo de juego. Quitar una campaña de la lista solo la desregistra: nunca borra los ficheros de esa carpeta.

Ejemplo mínimo de una nota de campaña (`sesion-01.md`):

```markdown
---
titulo: Sesión 1 — La taberna del Grifo Dorado
fecha: 2026-08-15
---

Los jugadores llegan a la taberna y conocen a **Alaric**, el tabernero.

- Pistas encontradas: mapa a medio quemar, moneda con símbolo extraño.
- Próxima sesión: seguir el rastro hacia el bosque de Kelthorne.
```