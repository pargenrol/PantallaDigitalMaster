# Cómo contribuir

¡Gracias por querer mejorar el DM Command Center! Aquí tienes cómo puedes ayudar.

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