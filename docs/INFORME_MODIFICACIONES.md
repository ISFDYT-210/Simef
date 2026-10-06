# Informe de Modificaciones — SIMEF 2.0

> Última actualización: 24 de agosto de 2026
> Generado a partir del historial de commits del repositorio (rama `Simef_2.0_`, 46 commits desde el 26/03/2026).

Este documento resume, en orden cronológico, las modificaciones realizadas sobre el proyecto SIMEF desde su primera versión hasta la fecha. Está pensado como bitácora de avance del proyecto, no como changelog técnico línea por línea (para eso está el historial de Git).

---

## 1. Resumen general

| Ítem | Detalle |
|---|---|
| Período cubierto | 26/03/2026 → 24/08/2026 (5 meses) |
| Commits totales | 46 |
| Colaboradores | mdilauro39, Marcos Ariel Di Lauro, Felipe Morales, profeleo15, joaquinrc26, Melany Diaz Marquez, Elias Merlo, galoruiiz, Leonardo Gomez |
| Ramas activas en el remoto | `main`, `develop`, `Simef_2.0_`, `feature/SIMEF-ci-cd`, `testing`, `EliasMerloQ` |

El proyecto pasó por tres grandes etapas:
1. **Puesta en marcha** (marzo–abril): importación del proyecto base y adaptación del entorno de desarrollo.
2. **Configuración y despliegue** (mayo): variables de entorno, ajustes de `settings.py` y primer despliegue en Vercel.
3. **Funcionalidades y hardening** (junio–agosto): roles y permisos, gestión de usuarios, reportes, mejoras de diseño responsive, y finalmente contenerización con Docker, CI/CD y migración a base de datos Neon (Postgres).

---

## 2. Marzo 2026 — Importación del proyecto base

- **26/03** — `se copio el contenido del repositorio de catriel, rama main`: primera carga del proyecto completo (app Django `gestionInstituto` + `inscripcionFinales`), con modelos, vistas, templates, estáticos e imágenes institucionales. Punto de partida del repositorio (~1000 archivos).
- **27/03** — Serie de commits de Marcos Ariel Di Lauro para adaptar el entorno a Windows:
  - Se agregó el `__init__.py` faltante en `migrations/` y se ajustó `requirements.txt` para seleccionar versiones de paquetes según la versión de Python instalada.
  - Se corrigió la URL de clonado documentada en el README.
  - Varias iteraciones de ajuste del README y `requirements` para que la instalación funcionara correctamente en Windows.
  - Commit final "Finalizando adaptación del readme a sistemas Windows".

## 3. Abril 2026 — Correcciones menores

- **04/04** — Felipe Morales corrige el comando de migración documentado en el README.
- **17/04** — profeleo15 realiza tres commits de ajuste (`first commit`), pequeños cambios puntuales de arranque de su participación en el proyecto.

## 4. Mayo 2026 — Configuración de entorno y primer despliegue

- **13/05** — joaquinrc26:
  - `Allowed agregado`: incorporación masiva de dependencias (entorno virtual, ~5100 archivos), reflejo de la instalación local de paquetes.
  - `Settings modificado`: ajuste de `ALLOWED_HOSTS`/configuración en `settings.py`.
  - `Se agregaron archivos estáticos para lectura en Vercel`: se agregan los estáticos recolectados (`staticfiles/`) para que Vercel pudiera servirlos.
- **15/05** — Melany Diaz Marquez cambia `DEBUG` a `False`, preparando el proyecto para un entorno más cercano a producción.

## 5. Fin de mayo / junio 2026 — Limpieza del repositorio

- **28/05** — Elias Merlo crea su rama de trabajo personal.
- **16/06** — Se agrega `diagramaClases.png` (diagrama de clases del sistema) y se actualiza `.gitignore` para excluir `venv/` y `__pycache__/`.
- **23/06** — Serie de commits de limpieza:
  - Ajustes adicionales a `.gitignore`.
  - `delete venv environment`: se eliminan del control de versiones los ~5100 archivos del entorno virtual que habían sido incorporados por error el 13/05 (corrige el commit "Allowed agregado").
  - `Changes in .gitignore`: consolidación final de las reglas de exclusión.

Esta etapa deja el repositorio limpio de dependencias versionadas indebidamente, estableciendo buenas prácticas de control de versiones para el resto del proyecto.

## 6. Junio–julio 2026 — Roles, usuarios y reportes

- **26/06** — profeleo15: `modificación models roles` — se ajusta el modelo de datos para incorporar el manejo de roles de usuario.
- **14/07** — profeleo15:
  - `crear usuarios`: alta y gestión de usuarios del sistema (10 archivos modificados).
  - `crear modificación urls`: se actualizan las rutas asociadas a la nueva funcionalidad de usuarios.
- **16/07** — profeleo15: `Reportes con control de acceso por rol` — los reportes generados por el sistema quedan restringidos según el rol del usuario autenticado.

## 7. Julio 2026 — Mejoras visuales y responsive

Serie de commits de galoruiiz enfocados en experiencia de usuario y diseño:

- **16/07** — Arreglo del diseño responsive del login.
- **17/07** — Normalización de variables de color y prolijado de botones en el listado de usuarios.
- **18/07** — Corrección del diseño de las pantallas de registro de alumnos y registro de usuarios.
- **20/07** — Arreglo general de responsive y del `navbar.html`.

## 8. Agosto 2026 — Actualización de datos, Docker, CI/CD y migración de base de datos

Etapa más intensa del período, liderada principalmente por Leonardo Gomez y Elias Merlo:

- **14/08** — Leonardo Gomez: `actualización de datos` — carga/actualización masiva de datos del sistema (145 archivos, ~15.000 líneas insertadas).
- **15/08**
  - Leonardo Gomez: `actualización de datos simef`.
  - profeleo15: `Resuelve conflicto en el README` (merge de cambios divergentes).
- **16/08** — Elias Merlo, tres commits que introducen infraestructura de desarrollo y CI/CD:
  - `Implement Docker setup and environment variable management for Django project`: se agregan `Dockerfile`, `docker-compose.yml`, `entrypoint.sh` y manejo de variables de entorno vía `.env`.
  - `Add initial test structure and remove unused test file`: se organiza la carpeta de tests y se elimina un archivo de test sin uso.
  - `Enhance CI/CD workflows: add linting, testing, and deployment configurations for Docker and Vercel`: se agregan workflows de GitHub Actions con linting, testing y despliegue automatizado tanto para Docker como para Vercel.
  - Merge de `feature/SIMEF-ci-cd` a `develop` (PR #22) y luego merge de `develop` a `Simef_2.0_`.
- **17/08** — Elias Merlo: `Add Docker setup documentation and override configuration for local development` — se agrega `DOCKER.md` y `docker-compose.override.yml` para facilitar el desarrollo local con Docker.
- **18/08** — Elias Merlo: se amplía `DOCKER.md` con instrucciones de instalación de Docker para Ubuntu, Fedora, macOS y Windows.
- **22/08** — Elias Merlo:
  - Se actualizan las instrucciones de Docker para Debian y se clarifica el uso de repositorios.
  - `Add installation guides for manual setup and environment configuration`: se agregan `INSTALACION_MANUAL.md` y `ENV.md`, documentando la instalación manual (sin Docker) y el detalle de las variables de entorno requeridas.
- **23/08** — Elias Merlo: `Update to Neon database` — se migra la configuración de base de datos para apuntar a **Neon** (Postgres serverless), reemplazando la configuración anterior.
- **24/08** — profeleo15: `cambios para carga` — ajustes finales relacionados con la carga de datos (último commit al día de la fecha).

---

## 9. Estado actual del proyecto (al 24/08/2026)

- **Backend**: Django, con modelos de roles, usuarios, inscripciones a finales y materias.
- **Base de datos**: Neon (PostgreSQL serverless), migrado desde la configuración previa.
- **Infraestructura**: soporte para ejecución vía Docker (`Dockerfile`, `docker-compose.yml`, `docker-compose.override.yml`) y para instalación manual (`INSTALACION_MANUAL.md`).
- **CI/CD**: workflows de GitHub Actions con linting, testing y despliegue (Docker + Vercel).
- **Documentación**: `README.md`, `DOCKER.md`, `DESPLIEGUE.md`, `INSTALACION_MANUAL.md`, `ENV.md`, `README-tailwind.md`.
- **Funcionalidades cubiertas**: gestión de usuarios y roles, control de acceso por rol en reportes, inscripción a finales y materias, diseño responsive del login/navbar/listados.

## 10. Pendientes / puntos a seguir observando

- No hay commits que documenten pruebas automatizadas más allá de la estructura inicial agregada el 16/08 — vale la pena revisar la cobertura de tests actual.
- Las ramas `develop`, `feature/SIMEF-ci-cd` y `EliasMerloQ` siguen existiendo en el remoto; conviene confirmar si deben eliminarse tras sus respectivos merges.
- Sería útil mantener este informe actualizado a medida que se sumen nuevos commits (puede regenerarse a partir de `git log`).
