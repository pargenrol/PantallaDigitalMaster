# Cómo contribuir

¡Gracias por querer mejorar el DM Command Center! Aquí tienes cómo puedes ayudar.

Este pequeño proyecto está pensado para ir creciendo de manera gradual. Puedes contribuir de la manera que prefieras. Ya sea sugiriendo nuevas mejoras,
creando monstruos o aportando mejoras al código. Este proyecto comenzó a gestarse con Gemini pero tambien se están uniendo inteligencias orgánicas.

## 👾 Añadir Nuevos Monstruos
El sistema lee archivos Markdown de la carpeta `data/monsters/`.
Para añadir un monstruo, crea un archivo `.md` (ej: `goblin.md`) con este formato exacto:

```markdown
---
name: "Goblin"
hp: 7
ac: 15
cr: "1/4"
type: "Humanoid (Goblinoid)"
---

### Descripción
Pequeños humanoides maliciosos y voraces.

### Acciones
**Cimitarra.** Ataque cuerpo a cuerpo: +4 al ataque, alcance 5 pies. Daño: 1d6 + 2 cortante.

**Arco Corto.** Ataque a distancia: +4 al ataque, rango 80/320 pies. Daño: 1d6 + 2 perforante.
