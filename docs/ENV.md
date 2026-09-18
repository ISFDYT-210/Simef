# Configurar el archivo .env

Guía rápida sobre el archivo `.env.example` y cómo crear tu propio `.env`
local a partir de él.

---

## 1. Qué es `.env.example`

`.env.example` es la plantilla de variables de entorno del proyecto. Trae
todas las claves que la app necesita, con valores de ejemplo (no reales).
Se versiona en el repo para que cualquiera sepa qué variables hacen falta.

`.env` es el archivo real que lee Django y Docker Compose en tiempo de
ejecución. **No se versiona** (está en `.gitignore`) porque ahí van
credenciales reales: cada persona/entorno tiene el suyo.

| Variable | Para qué sirve |
|---|---|
| `SECRET_KEY` | Clave secreta de Django. Para uso local cualquier valor sirve; en producción tiene que ser una clave real y secreta. |
| `DEBUG` | `True` en desarrollo, `False` en producción. |
| `ALLOWED_HOSTS` | Hosts/dominios permitidos, separados por coma. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Credenciales de la base Postgres que levanta Docker. |
| `DATABASE_URL` | URL de conexión a la base. Tiene que coincidir con los `POSTGRES_*` de arriba. |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Credenciales SMTP, solo necesarias si vas a probar el envío de mails (recuperar contraseña, etc.). |

## 2. Crear tu `.env`

Copiá la plantilla al archivo real con `cat`:

```bash
cat .env.example > .env
```

(`archivo_origen.txt > archivo_destino.txt`: `cat` vuelca el contenido del
primero dentro del segundo, creándolo si no existe. En este caso el origen es
`.env.example` y el destino `.env`.)

## 3. Completar los datos clave

`.env.example` trae valores de ejemplo, no reales. Después de crear `.env`,
abrilo y reemplazá los valores por los datos clave que te hayan sido enviados
(por el equipo, por chat, etc.): `SECRET_KEY`, `POSTGRES_PASSWORD`,
`EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD`, y cualquier otro que corresponda.

> Si `.env` falta o le faltan las variables de `POSTGRES_*`, el contenedor de
> la base falla al arrancar con un error de "superuser password is not
> specified" (ver [DOCKER.md](DOCKER.md)).

Con `.env` ya completo, seguí con los pasos de [DOCKER.md](DOCKER.md) para
levantar el stack.
