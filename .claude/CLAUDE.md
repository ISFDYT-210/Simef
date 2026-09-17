# CLAUDE.md — Runbook: merge `Simef_2.0_` → `feature/back_leo`

> Este archivo es un runbook para un agente que va a ejecutar el merge/rescate de
> funcionalidad entre las ramas `feature/back_leo` (rama de trabajo actual) y
> `Simef_2.0_` (rama paralela con features y documentación propias). Fue generado
> a partir de un análisis comparativo completo hecho el 2026-09-16. Antes de tocar
> nada, leé completo este documento: contiene decisiones ya tomadas (qué traer, qué
> descartar) para no tener que re-investigar desde cero.

## 0. Contexto del proyecto (por si no lo sabías)

- Django + Tailwind **sin pipeline de build**: las clases de utilidad nuevas deben
  existir ya en `inscripcionFinales/static/css/simef.css` (compilado y commiteado),
  si no, no van a tener estilo. No asumas que `npm run build` o similar corre solo.
- `docker compose up` **no monta el código fuente** (usa lo que quedó "horneado" en
  la imagen). Para iterar rápido en local, usar `venv/bin/python manage.py runserver`,
  no depender de docker-compose para ver cambios.
- Roles y permisos: single source of truth es `CAPACIDADES_POR_ROL` en
  `inscripcionFinales/models.py`. Es igual en ambas ramas (viene de antes de la
  divergencia), no es un punto de conflicto.

## 1. Estado de las ramas (relevado 2026-09-16)

- Ancestro común: commit `fc3aaa7` (16-ago-2026, merge del PR #22 CI/CD).
- `feature/back_leo`: 8 commits propios desde el ancestro común.
- `origin/Simef_2.0_`: 21 commits propios desde el ancestro común. **Importante**:
  la rama local `Simef_2.0_` está desactualizada respecto a `origin/Simef_2.0_`
  (le faltan 8 commits) — trabajar siempre contra `origin/Simef_2.0_`, o antes de
  empezar hacer `git fetch origin && git branch -f Simef_2.0_ origin/Simef_2.0_`.

### El problema central de este merge

**Ambas ramas reescribieron TODO el frontend a Tailwind de forma independiente**,
cada una con su propio commit gigante (`84d5149` en back_leo, y el trabajo detrás
de `c151bd2`/commits de docs en Simef_2.0_). Son ~60 templates que lucen parecidos
pero son reescrituras distintas del mismo Bootstrap original. Un `git merge` directo
va a generar conflictos masivos en casi todos los templates, y en la mayoría de los
casos **no hay nada real que reconciliar línea a línea** — hay que decidir "me quedo
con la versión de esta rama" por archivo, no resolver conflicto por conflicto.

**Recomendación de estrategia: NO hacer un merge de rama completo.** En su lugar,
usar `feature/back_leo` como base (su UI es la que sigue en desarrollo activo) y
**portar selectivamente** desde `Simef_2.0_` las piezas de lógica de negocio e
infraestructura listadas en la sección 2, aplicándolas a mano sobre los templates/
vistas ya existentes en `feature/back_leo`. Si en algún punto se prefiere sí hacer
`git merge origin/Simef_2.0_`, usar `git checkout --ours <archivo>` para todos los
templates en conflicto (nos quedamos con la versión de back_leo) y resolver a mano
solo los archivos de lógica listados abajo.

## 2. Qué portar de `Simef_2.0_` a `feature/back_leo`

Todo esto es funcionalidad real que `feature/back_leo` NO tiene. Priorizado por valor:

### 2.1 Auto-inscripción a materias de 1er año (alto valor)
En `Simef_2.0_`, `inscripcionFinales/models.py` (final del archivo) tiene una señal
`m2m_changed` sobre `Usuario.carrera.through`: al agregarle una carrera a un
estudiante, se lo inscribe automáticamente (`usuarios_materia.objects.get_or_create`)
en todas las materias de año 1 de esa carrera. Cubre alta individual, carga masiva,
edición desde admin, etc. Portar tal cual (revisar que no choque con el flujo de
carga masiva de estudiantes de `feature/back_leo`, que también podría estar
enrolando materias por su cuenta — comparar antes de aplicar).

Ver: `git show origin/Simef_2.0_:inscripcionFinales/models.py | tail -25`

### 2.2 Fix de `telefono_1`/`telefono_2` (bajo riesgo, alto valor)
`Simef_2.0_` cambió esos dos campos de `IntegerField` a `CharField(max_length=15)`
en `Usuario` (evita perder ceros a la izquierda / signos `+`). Requiere nueva
migración en `feature/back_leo` (la de `Simef_2.0_` se llama
`0004_alter_usuario_telefonos.py`, pero el número de migración va a chocar porque
las ramas divergieron el árbol de migraciones — generar una migración nueva con
`makemigrations` en vez de copiar el archivo).

### 2.3 Filtro cliente por carrera/año en alta de mesa final (valor medio)
`MateriaConFiltroSelect` en `inscripcionFinales/forms.py` de `Simef_2.0_`: un
`forms.Select` custom que agrega `data-carrera`/`data-anio` a cada `<option>` de
materia, poblado con una sola query (`Materia.objects.values_list('id',
'carrera_id', 'anio')`) para que el template pueda filtrar opciones en el cliente
sin volver a pegarle a la DB. Se usa en `MesaFinalForm`. Portar el widget + su uso,
y el JS del template `finales/alta_mesa_final.html` que lo consume (mirar cómo lo
usa esa rama y adaptarlo al template equivalente de `feature/back_leo`).

### 2.4 Refactor a endpoints API para listados (valor medio, evaluar esfuerzo)
`Simef_2.0_` tiene `api_lista_inscripciones`, `api_lista_mesas`,
`api_finales_inscriptos_adm` en `views.py`: mueven la carga de datos de listados de
mesas/finales a JSON + fetch en vez de renderizar todo server-side. Evaluar si vale
la pena portarlo ahora o dejarlo para después — es refactor de arquitectura, no fix
de bug ni feature crítica.

### 2.5 Integración con Neon / Postgres (evaluar si aplica al roadmap actual)
Management command `cargar_datos_neon.py` (en `Simef_2.0_` vive dentro de
`inscripcionFinales/management/commands/`). `feature/back_leo` ya tiene su propio
`neon_sync.py` en la raíz del repo — **comparar ambos antes de decidir cuál usar**,
no asumir que hay que traer el de `Simef_2.0_` porque sí. Puede que sean dos
intentos distintos de resolver lo mismo.

### 2.6 Documentación de despliegue/infra (bajo riesgo, valor alto para onboarding)
Archivos nuevos en `Simef_2.0_`, sin equivalente en `feature/back_leo`:
- `docs/DESPLIEGUE.md`, `docs/DOCKER.md`, `docs/ENV.md`, `docs/INSTALACION_MANUAL.md`
- `docker-compose.override.yml`, ajuste de `Dockerfile` (ENTRYPOINT con `sh`),
  `.gitattributes` (normaliza line endings)
- `iniciar_simef.bat` (script de arranque para Windows)

Se pueden traer casi sin fricción (son archivos nuevos, no tocan código de la app).
Revisar que las instrucciones de esos docs coincidan con la estructura real de
`feature/back_leo` antes de copiarlos (pueden referenciar rutas o pasos que ya
cambiaron).

## 3. Qué NO traer bajo ningún concepto

`Simef_2.0_` tiene bastante basura commiteada por error. **No copiar estos archivos
ni sus equivalentes**, y si se hace un `git merge` real, excluirlos explícitamente:

- `inscripcionFinales/views.py.bak`, `inscripcionFinales/models.py.bak`,
  `inscripcionFinales/views - copia.py` (nombre con espacios)
- Cualquier `*.html.bak` (hay ~10, en `finales/`, `materias/`, `registration/`)
- Cualquier `*_viejo.html` (`index_viejo.html`, `login_viejo.html`,
  `list_user_viejo.html`, `profile_viejo.html`, `register_viejo.html`,
  `edit_profile_viejo.html`, `constancia_estudiante_viejo.html`,
  `mesas_finales_cartel_pdf_viejo.html`)
- Accesos directos de Windows: `*.lnk` (`delete_user.html - Acceso directo.lnk`,
  `lista_materias.html - Acceso directo.lnk`, etc. — quedaron commiteados por
  accidente, seguramente por trabajar desde una carpeta sincronizada de Windows)
- `tailwindcss.exe` — **binario de 40 MB** commiteado a git. Si termina en el
  historial del merge, el repo va a quedar inflado para siempre. Verificar con
  `git log --all --oneline -- tailwindcss.exe` después del merge que no haya
  quedado colado.
- Ramas de templates duplicados `base.html` (raíz), `base/base_1.html`,
  `base/base_vieja.html`, `templates/base.html` (fuera de `inscripcionFinales/`) —
  son versiones intermedias del rediseño Tailwind de esa rama, no sirven una vez
  que ya tenemos el `base/base.html` de `feature/back_leo`.
- Scripts sueltos de un solo uso en la raíz: `aplicar_inscripcion_primer_anio.py`,
  `aplicar_permisos_vistas.py`, `corregir_guard_usuarios.py`,
  `corregir_guards_materias_finales.py`, `corregir_tablas_alpine.py` — son scripts
  de migración de datos de esa rama específica (probablemente ya corridos una vez
  contra su propia base de datos). Si alguno resulta necesario, revisar qué hace
  exactamente antes de correrlo — no ejecutar a ciegas contra la base de datos real.

## 4. Bug ya conocido y CONFIRMADO en ambas ramas

`validar_inscripcion_materias` en `Simef_2.0_` (línea ~1336 de su `views.py`) tiene
el **mismo bug de correlativas que ya se corrigió en `feature/back_leo`**: exige
`nota_final >= 4` en la materia correlativa (final aprobado) en vez de
`nota_cursada >= 4` (cursada aprobada, con el final aprobado si ya fue rendido).

**No portar esa función desde `Simef_2.0_`** — usar la versión ya corregida que
está en `feature/back_leo` (pendiente de commit al momento de escribir esto, ver
sección 6). Si en el proceso de merge Git propone la versión de `Simef_2.0_` como
"entrante", rechazarla y quedarse con la de `feature/back_leo`.

La misma regla corregida aplica a `lista_materias_user` (el listado de materias
disponibles del estudiante).

## 5. Checklist de verificación post-merge

Después de portar cualquier pieza de la sección 2, correr:

1. `python manage.py check` — sin errores.
2. `python manage.py makemigrations --check --dry-run` — no debería haber
   migraciones pendientes sin generar (si tocaste modelos, generá la migración).
3. Probar manualmente (server local con `venv/bin/python manage.py runserver`,
   no docker-compose):
   - Asignar una carrera a un estudiante nuevo → si se portó 2.1, verificar que
     quedó inscripto en las materias de 1er año.
   - Cargar una nota de cursada/final y confirmar que las correlativas de otra
     materia se habilitan con la regla correcta (cursada >=4, no final).
   - Flujo de "dar de baja" de materia como estudiante (ya validado en la sesión
     anterior — no debería haber cambiado, pero confirmar que el merge no lo pisó).
   - Si se portó 2.3, el alta de mesa de final con el filtro carrera/año.
4. Revisar `git log --all --oneline -- tailwindcss.exe '*.bak' '*viejo*' '*copia*'`
   para confirmar que nada de la sección 3 quedó colado en el historial.
5. `git status` limpio, sin archivos `.lnk` ni `- copia` ni `.bak` en el working tree.

## 6. Trabajo pendiente sin commitear en `feature/back_leo` (al momento de este análisis)

Al momento de escribir este runbook, `feature/back_leo` tiene cambios **sin
commitear** en el working tree que ya corrigen el bug de la sección 4 y agregan:
- Regla de correlativas corregida (`validar_inscripcion_materias`,
  `lista_materias_user` en `views.py`).
- Filtro de materias por carrera del estudiante (`lista_materias_user`,
  `obtener_materias_estudiante`).
- Validación server-side + fix de template en "dar de baja" de materia
  (`eliminar_inscripcion_materia`, `lista_materias_inscriptas_user.html`).
- Fix de typo `.exist()` → `.exists()` en `listarMateriasFinal`.
- Cierre automático de la sidebar al hacer click afuera en mobile (`base.html`).

**Confirmar con el usuario si esos cambios ya se commitearon antes de empezar el
merge.** Si siguen sin commitear, commitealos primero (o al menos congelalos en un
stash con nombre) para no perderlos ni mezclarlos accidentalmente con el trabajo de
este runbook.
