# Git flow de SIMEF

Cómo se organizan las ramas de este repositorio y cómo entra un cambio. Si vas a
trabajar en SIMEF, esto es lo único que necesitás leer antes de tu primer commit.

---

## 1. Las ramas

| Rama | Para qué sirve | Quién la mueve |
|---|---|---|
| `main` | Lo que está en producción. | Sólo por PR desde `develop`. |
| `develop` | Rama de integración: lo que ya está terminado y revisado, esperando el próximo pasaje a producción. | Sólo por PR. |
| `feature/<lo-que-hacés>` | Tu trabajo en curso. Una por tarea. | Vos, libremente. |

`develop` es la rama más actualizada y es de donde salen las features nuevas.
`main` va más atrás a propósito: es la foto de lo que está corriendo.

No hay ramas por persona. Una rama `juanperez` que acumula trabajo de todo tipo
no se puede revisar ni integrar: nadie sabe qué contiene. Una rama por tarea sí.

---

## 2. La regla: a `develop` se entra por Pull Request

**Nunca** `git push origin develop`, ni siquiera cuando el merge es trivial o
fast-forward. Siempre un PR.

No es burocracia: **el CI se dispara con el PR.** El workflow
[`ci.yml`](../.github/workflows/ci.yml) corre con `pull_request` hacia
`main`/`develop`. Si mergeás a mano, integrás código que ningún job verificó —
las ramas `feature/*` no tienen CI propio, así que el PR es literalmente la
primera vez que algo revisa tu trabajo.

---

## 3. Una feature, de principio a fin

```bash
# 1. Partir de develop actualizado, no de donde quedaste la semana pasada
git switch develop
git pull

# 2. Una rama por tarea, con un nombre que diga qué hace
git switch -c feature/filtro-mesas-por-carrera

# 3. Trabajar y commitear normalmente
git add -p
git commit

# 4. Antes de abrir el PR: correr lo que va a correr el CI
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test inscripcionFinales --settings=gestionInstituto.settings_TEST
flake8 . --count --select=E9,F63,F7,F82

# 5. Subir y abrir el PR
git push -u origin feature/filtro-mesas-por-carrera
gh pr create --base develop
```

El `--settings` del paso 4 **no es opcional**: sin él, Django intenta crear la
base de prueba en la Postgres compartida de Neon. Ver
[INSTALACION_MANUAL.md](INSTALACION_MANUAL.md).

Cuando el PR se mergea, borrá la rama. `gh pr merge --delete-branch` lo hace solo.

---

## 4. Qué revisa el CI, y por qué el lint es el portón

Los jobs de `ci.yml` no son independientes: **`lint` es el `needs:` de todos los
demás.** Si falla, los tests no se ejecutan y el PR queda rojo sin que sepas si
tu código funciona.

El lint bloqueante es acotado a propósito:

```bash
flake8 . --count --select=E9,F63,F7,F82
```

Son errores de sintaxis (`E9`) y nombres indefinidos (`F82`) — cosas que
revientan en ejecución, no cuestiones de estilo. El reporte de estilo completo
corre aparte con `--exit-zero`: informa, no bloquea.

La causa más común de que esto falle en este repo es un archivo `.py` guardado
en un lugar donde no es un módulo —por ejemplo un fragmento de código dejado
dentro de `templates/`— que flake8 igual analiza y donde todos los imports
quedan indefinidos. Si tenés que guardar un borrador de código, que no lleve
extensión `.py`.

Los tests del CI corren contra un **Postgres propio y descartable** del runner,
no contra Neon.

---

## 5. Proteger `develop` y `main` en GitHub

La regla de la sección 2 se cumple sola si GitHub la impone. Hay que
configurarlo una vez, en **Settings → Branches → Add branch ruleset**, para
`main` y para `develop`:

- **Require a pull request before merging.** Es lo que vuelve imposible el push
  directo.
- **Require status checks to pass** → elegir `Lint (flake8)` y
  `Tests (Django + PostgreSQL)`.
- **Require branches to be up to date before merging**, así nadie mergea contra
  un `develop` viejo.
- **Block force pushes**, para que no se pueda reescribir historia publicada.

> Esto se configura desde la web; no se puede hacer con el token que traen los
> Codespaces (la API de protección de ramas le responde 403).

---

## 6. Cuando el merge es grande

Si al mergear aparecen muchos conflictos, no los resuelvas sobre `develop`.
Hacelo en una rama intermedia y abrí el PR desde ahí: `develop` no se toca hasta
que alguien aprueba, y si la resolución sale mal se descarta la rama sin
consecuencias.

```bash
git switch -c integracion/mi-rama-a-develop origin/feature/mi-rama
git merge origin/develop          # resolver acá
gh pr create --base develop
```

Antes de empezar, dejá un punto de retorno. Un tag apunta a un commit y no se
mueve, así que sobrevive a cualquier cosa que le pase a la rama:

```bash
git tag backup/$(date +%F)/develop origin/develop
git push origin --tags
```

Y al resolver, dos cosas que en este repo ya pasaron:

- **Un conflicto no siempre se resuelve eligiendo un lado.** Puede que una rama
  tenga el markup nuevo y la otra el texto correcto. Mirá los dos archivos
  completos (`git show rama:archivo`), no el hunk mezclado, que engaña.
- **Lo que una rama borró y la otra no tocó desaparece sin marcar conflicto.**
  Si un archivo que esperabás no aparece después del merge, buscalo con
  `git log --all -- <archivo>`.

---

## 7. Lo que no va al repositorio

Nada de esto se commitea, y el `.gitignore` cubre la mayoría:

- Copias y borradores: `*.bak`, `* - copia.py`, `*_viejo.html`.
- Accesos directos de Windows (`*.lnk`).
- Binarios. En particular `tailwindcss` / `tailwindcss.exe`: son ~40 MB que, una
  vez en el historial, quedan para siempre. El binario se baja en cada máquina
  (ver [DESPLIEGUE.md](DESPLIEGUE.md)).
- `.env`, con credenciales reales. La plantilla `.env.example` sí se versiona.
- Scripts de un solo uso para arreglar datos. Si hacen falta, van como
  *management command* o como migración de datos, que quedan documentados y se
  corren una vez.

---

## 8. Migraciones: el error que ya nos pasó

Dos ramas que generan migraciones en paralelo producen **dos cabezas** en el
árbol, y Django se niega a arrancar con
`multiple leaf nodes in the migration graph`.

La regla: **generá la migración con `makemigrations`, no copies el archivo de
otra rama.** Copiarlo trae su número y su `dependencies`, que en tu rama apuntan
a otro lugar — así es como aparecen dos migraciones distintas con el mismo
número.

Si igual pasó, se arregla con una migración de merge, que no toca el esquema:

```bash
python manage.py makemigrations --merge --settings=gestionInstituto.settings_TEST
```

Lo que **no** arregla sola es que las dos migraciones hayan hecho cambios
contradictorios sobre el mismo campo. Ahí hay que mirar qué tiene la base de
verdad y dejar el modelo de acuerdo con eso, antes de inventar una migración
nueva contra la base compartida.
