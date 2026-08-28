# Proyecto Gestión de Inscripciones a Final - Instituto 210

## Proyecto de articulación de materias de la carrera
**Tecnicatura Superior en Análisis de Sistemas**

---

## Descripción

Este proyecto corresponde al sistema de **Gestión de Inscripciones a Mesas de Examen Final** del **Instituto 210**.

Su objetivo es facilitar la administración de inscripciones, el acceso de usuarios y la gestión interna mediante un panel de administración (*backoffice*).

---

## Quick start (Docker, recomendado)

La forma más rápida de levantar el proyecto es con Docker: no requiere
instalar Python ni Postgres en tu máquina.

```bash
cp .env.example .env      # completar con tus datos, ver docs/ENV.md
docker compose up -d --build
```

La app queda en **http://localhost:8000**. Guía completa paso a paso en
[docs/DOCKER.md](docs/DOCKER.md).

---

## Documentación

| Documento | Contenido |
|---|---|
| [docs/DOCKER.md](docs/DOCKER.md) | Levantar el proyecto completo (Django + Postgres) con Docker Compose. |
| [docs/ENV.md](docs/ENV.md) | Qué es cada variable de `.env.example` y cómo armar tu `.env`. |
| [docs/INSTALACION_MANUAL.md](docs/INSTALACION_MANUAL.md) | Instalación sin Docker (venv + Python), Linux y Windows. |
| [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md) | Despliegue en producción (Apache + Gunicorn + Django + MariaDB) en Debian. |
| [docs/README-tailwind.md](docs/README-tailwind.md) | Kit de build de Tailwind CSS del proyecto. |
| [docs/TARJETAS_GH.md](docs/TARJETAS_GH.md) | Cómo cargar tarjetas de trabajo (issues) al tablero con la CLI `gh`. |


---

## Acceso al sistema

Una vez levantado el servidor (por cualquiera de los métodos de arriba):

- Panel de administración (backoffice): `/admin/`
- Pantalla de login: `/`

## Redirección luego del login

Si querés que, luego de iniciar sesión, el usuario sea redirigido a la vista
`inicio`, agregá la siguiente línea en `settings.py`:

```python
LOGIN_REDIRECT_URL = 'inicio'
```

---

## Notas

- Para desarrollo local, Docker ([docs/DOCKER.md](docs/DOCKER.md)) es el camino recomendado.
- Para producción, ver [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md).
