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
cp .env.example .env      # completar con tus datos, ver ENV.md
docker compose up -d --build
```

La app queda en **http://localhost:8000**. Guía completa paso a paso en
[DOCKER.md](DOCKER.md).

---

## Documentación

| Documento | Contenido |
|---|---|
| [DOCKER.md](DOCKER.md) | Levantar el proyecto completo (Django + Postgres) con Docker Compose. |
| [ENV.md](ENV.md) | Qué es cada variable de `.env.example` y cómo armar tu `.env`. |
| [INSTALACION_MANUAL.md](INSTALACION_MANUAL.md) | Instalación sin Docker (venv + Python), Linux y Windows. |
| [DESPLIEGUE.md](DESPLIEGUE.md) | Despliegue en producción (Apache + Gunicorn + Django + MariaDB) en Debian. |
| [README-tailwind.md](README-tailwind.md) | Kit de build de Tailwind CSS del proyecto. |
| [TARJETAS_GH.md](TARJETAS_GH.md) | Cómo cargar tarjetas de trabajo (issues) al tablero con la CLI `gh`. |


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

- Para desarrollo local, Docker ([DOCKER.md](DOCKER.md)) es el camino recomendado.
- Para producción, ver [DESPLIEGUE.md](DESPLIEGUE.md).
