# Cómo cargar tarjetas de trabajo con `gh`

Guía del equipo para pasar trabajo pendiente (bugs, features, tareas técnicas) al tablero de GitHub usando la CLI `gh`, en lugar de cargarlo a mano desde la web. Sirve para cualquier tanda de tarjetas, no solo para una entrega puntual.

El orden importa: las etiquetas y el milestone tienen que existir **antes** de crear las incidencias, o los comandos de creación fallan al referenciarlos.

## 0. Instalar y autenticar la CLI

Si `gh` no está instalado en la máquina:

```bash
sudo apt update && sudo apt install -y gh
gh auth login
```

Si alguien del equipo prefiere no instalarlo, todo lo que sigue también se puede hacer desde la web copiando el contenido de cada tarjeta (título, contexto y definición de terminado).

## 1. Definir las etiquetas y el milestone

Antes de escribir la primera tarjeta, conviene tener claro:

- **Etiquetas**: categorías cortas y reutilizables (área, tipo de trabajo). Ejemplos: `bug`, `feature`, `docs`, `seguridad`, `refactor`, `ci`, `db`. No hace falta crear una etiqueta nueva por tarjeta; reusar las que ya existen en el repo cuando aplican.
- **Milestone**: agrupa la entrega o el sprint en el que van a resolverse esas tarjetas (ej. "Sprint 4", "Release 1.2").

```bash
# Crear (o actualizar el color de) las etiquetas que vayas a usar
for l in "bug:d73a4a" "feature:0d5a4a" "docs:0075ca" \
         "seguridad:b60205" "refactor:5b6763" "decisión:fbca04"; do
  gh label create "${l%:*}" --color "${l#*:}" --force
done

# Crear el milestone de la entrega
gh api repos/<ORG>/<REPO>/milestones -f title="<Nombre del milestone>" \
  -f description="<Qué agrupa esta entrega>"
```

Antes de correr esto, revisá qué etiquetas ya existen en el repo con `gh label list`, para no duplicar con otro nombre o color.

## 2. Escribir cada tarjeta antes de cargarla

Por cada trabajo pendiente, conviene tener resuelto de antemano:

- **ID o título corto**, si el equipo usa una convención de nombres (ej. `PROYECTO-ÁREA-N`).
- **Contexto**: qué problema existe o qué falta, en 1-3 líneas.
- **Definición de terminado**: checklist concreto y verificable de cuándo se puede cerrar la tarjeta.
- **Etiquetas** y **tamaño/estimación**, si el equipo estima esfuerzo.

Ese formato es el que después se pasa directo al `--body` de `gh issue create`.

## 3. Crear la incidencia

```bash
gh issue create \
  --title "<Título de la tarjeta>" \
  --label "<etiqueta1>" --label "<etiqueta2>" \
  --milestone "<Nombre del milestone>" \
  --body "## Contexto
<Qué problema existe o qué falta, en pocas líneas.>

## Definición de terminado
- [ ] <Criterio verificable 1>
- [ ] <Criterio verificable 2>
- [ ] <Criterio verificable 3>"
```

Para cargar varias tarjetas seguidas, guardar cada `--body` en un archivo `.md` aparte y pasarlo con `--body-file <archivo>` en lugar de escribirlo inline; es más cómodo de mantener y revisar antes de crear la incidencia.

Si el trabajo ya está hecho y solo se está dejando registro (por ejemplo, cargando tarjetas para algo que ya se implementó), se puede crear la incidencia igual y cerrarla al mismo tiempo con `gh issue close <N>`, o dejar que la cierre el PR correspondiente (ver paso 5).

## 4. Sumar la incidencia al tablero (proyecto de GitHub) y ubicar la columna

El número de proyecto sale de:

```bash
gh project list --owner <ORG>
```

Luego, por cada issue creado:

```bash
gh project item-add <NUMERO> --owner <ORG> \
  --url https://github.com/<ORG>/<REPO>/issues/<N>
```

Por defecto la tarjeta entra a la primera columna del proyecto; moverla a la columna que corresponda (**Backlog**, **Todo**, **In progress**, **In review**, **Done**) desde la web o con `gh project item-edit`.

> Si el proyecto todavía no existe, crearlo primero desde la pestaña **Projects** de la organización, definiendo las columnas que use el equipo.

## 5. Referenciar las tarjetas desde el PR que las resuelve

Cuando el trabajo de una o varias tarjetas está listo, el PR que lo implementa las cierra automáticamente si el cuerpo incluye `Closes #N` por cada una:

```bash
git switch -c <nombre-de-rama>
git add <archivos>
git commit -m "<mensaje del commit>"
gh pr create --base <rama-base> \
  --title "<título del PR>" \
  --body "Closes #1, #2, #3"
```

Los números de incidencia deben ser los que devolvió `gh issue create` en el paso 3, no un placeholder.

## Referencia rápida de comandos

| Acción | Comando |
|---|---|
| Ver etiquetas existentes | `gh label list` |
| Crear/actualizar etiqueta | `gh label create "<nombre>" --color "<hex>" --force` |
| Crear milestone | `gh api repos/<ORG>/<REPO>/milestones -f title="<nombre>"` |
| Crear incidencia | `gh issue create --title "..." --label "..." --milestone "..." --body "..."` |
| Ver proyectos del org | `gh project list --owner <ORG>` |
| Sumar incidencia al proyecto | `gh project item-add <NUM> --owner <ORG> --url <URL del issue>` |
| Cerrar incidencia desde un PR | Incluir `Closes #N` en el body del PR |
