# Levantar SIMEF con Docker

Guía rápida para cualquiera con acceso al repo: levantar la app completa
(Django + Postgres) en su máquina con dos comandos, sin instalar Python,
Postgres ni nada más que Docker.

---

## 1. Requisitos

- [Docker](https://docs.docker.com/get-docker/) con el plugin **Docker Compose**
  (se prueba con `docker compose version`; si da error, instalar `docker-compose-plugin`).
- Haber clonado el repo y estar parado en su raíz.

### Instalar Docker

**Ubuntu**

```bash
# Quitar versiones viejas si existieran
sudo apt-get remove docker docker-engine docker.io containerd runc

# Instalar dependencias y el repo oficial de Docker
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker Engine + plugin de Compose
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# (opcional) usar docker sin sudo
sudo usermod -aG docker $USER
```

**Debian** (incluye Debian 13 "trixie")

Usar el repo de Ubuntu en Debian falla (404) porque el código de la distro
(`$VERSION_CODENAME`) no existe ahí. Hay que apuntar al repo propio de Debian:

```bash
# Quitar versiones viejas si existieran
sudo apt-get remove docker docker-engine docker.io containerd runc

# Instalar dependencias y el repo oficial de Docker
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker Engine + plugin de Compose
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# (opcional) usar docker sin sudo
sudo usermod -aG docker $USER
```

> Si el `apt-get update` falla con un 404 porque el repo de Docker todavía no
> publicó paquetes para `trixie`, forzá el código de la versión estable
> anterior editando `/etc/apt/sources.list.d/docker.list` y reemplazando
> `trixie` por `bookworm` (funciona igual, son binarios compatibles), luego
> repetí `sudo apt-get update`.

Después de agregarte al grupo `docker` (en cualquiera de los dos casos),
cerrá sesión y volvé a entrar (o corré `newgrp docker`) para que tome efecto.

**Fedora / RHEL / CentOS**

```bash
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

**macOS**

```bash
brew install --cask docker
```

Abrí la app Docker Desktop una vez para que termine de inicializarse (incluye
Docker Compose, no hace falta instalarlo aparte).

**Windows**

Instalar [Docker Desktop](https://docs.docker.com/desktop/install/windows-install/)
(requiere WSL2). También se puede instalar con `winget`:

```powershell
winget install Docker.DockerDesktop
```

**Verificar la instalación** (en cualquier plataforma):

```bash
docker --version
docker compose version
```

## 2. Configurar las variables de entorno

Docker Compose lee las variables desde un archivo `.env` en la raíz del repo
(no se versiona, cada uno tiene el suyo). Copiá la plantilla y completá los valores:

```bash
cp .env.example .env
```

Como mínimo revisá/completá:

| Variable | Para qué sirve |
|---|---|
| `SECRET_KEY` | Clave secreta de Django. Para uso local cualquier valor sirve. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Credenciales de la base. Si las cambiás, actualizá también `DATABASE_URL` para que coincida. |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Solo necesarios si vas a probar el envío de mails (recuperar contraseña, etc.). Se pueden dejar vacíos para levantar la app igual. |

> Si `.env` falta o le faltan las variables de `POSTGRES_*`, el contenedor de
> la base falla al arrancar con un error de "superuser password is not specified".

> ### El `DATABASE_URL` del `.env` NO es el que usan los contenedores
>
> `docker-compose.override.yml` lo pisa a proposito, apuntando al servicio `db`
> de este mismo compose. Es una proteccion, no un descuido.
>
> `entrypoint.sh` corre `migrate` en **cada arranque** del contenedor. Si el
> `DATABASE_URL` del `.env` apunta a la base compartida de Neon —y el de varios
> de nosotros apunta ahi, porque es el mismo archivo que usa `runserver`—
> entonces cada `docker compose up` le aplica a la base del instituto las
> migraciones de la rama en la que estes parado. Ya paso: el 2026-10-06 se le
> aplicaron a Neon dos migraciones que existian unicamente en una rama de
> integracion sin mergear.
>
> Al arrancar, el contenedor imprime contra que base va a migrar:
>
> ```
> ==> base de datos: postgres://***:***@db:5432/simef
> ```
>
> Si ahi ves un host `...neon.tech`, **cortalo**: el override no se esta
> aplicando (ver seccion 7).

### Entonces, ¿cómo me conecto a Neon?

Los contenedores ya no lo hacen, pero **todo lo que corrés fuera de Docker sí**:
`settings.py` lee el `DATABASE_URL` del `.env`, que apunta a Neon. Así que
`manage.py runserver`, `manage.py shell` y `manage.py dbshell` desde el venv ya
están hablándole a la base compartida, sin configurar nada.

```bash
# Una consulta rápida con el ORM
python manage.py shell -c "from inscripcionFinales.models import Usuario; print(Usuario.objects.count())"

# SQL crudo (requiere el cliente: sudo apt install postgresql-client)
python manage.py dbshell
```

Si necesitás llegar a Neon **desde un contenedor**, pasale el `DATABASE_URL` por
`-e` y **salteá el entrypoint**, porque si no corre `migrate`:

```bash
docker compose run --rm --no-deps \
  -e DATABASE_URL="$(grep -o '^DATABASE_URL=.*' .env | cut -d= -f2-)" \
  --entrypoint sh web -c "python manage.py shell"
```

> **Lo peligroso no es conectarse, es migrar.** Leer, y hasta usar la app contra
> Neon, no rompe nada. El problema es `migrate`, que aplica lo que tenga tu rama.
> Si vas a correr migraciones contra la base con datos reales, sacá antes una
> rama en la consola de Neon: tarda segundos y te deja un punto exacto al que
> volver (ver [DESPLIEGUE.md](DESPLIEGUE.md), sección 8).
>
> Para trabajar seguido contra datos realistas, lo prolijo es usar una **rama de
> Neon** en tu `.env` en vez de `main`: los mismos datos, aislados de producción.

### Traer los datos de Neon a la base local

Para probar contra datos reales sin tocar la base del instituto, hay un script
que copia Neon a la Postgres del compose:

```bash
./scripts/copiar_neon_a_local.sh
```

A Neon lo **lee y nada más** (`pg_dump` no escribe). Lo que borra y recrea es la
base local. Deja el dump en `backups/`, que está en el `.gitignore` —
**importante, porque son datos personales de alumnos: no los commitees**.

Para volver a cargar un dump que ya tenés, sin bajarlo de nuevo:

```bash
./scripts/copiar_neon_a_local.sh backups/neon-2026-10-07-1030.sql
```

Después, `docker compose restart web` para que la app tome la base recargada.

> `pg_dump` corre **dentro del contenedor `db`**, que ya trae el cliente de
> Postgres 16. No hace falta instalar `postgresql-client` en tu máquina.

## 3. Levantar el stack

```bash
docker compose up -d --build
```

Esto construye la imagen de `web`, y levanta dos contenedores:

- **`db`**: Postgres 16. Tiene un healthcheck; `web` espera a que esté sano antes de arrancar.
- **`web`**: Django servido con Gunicorn. Al arrancar corre automáticamente
  `migrate` y `collectstatic` (ver `entrypoint.sh`), así que la base y los
  estáticos siempre quedan al día.

La app queda disponible en **http://localhost:8000**.

Para ver los logs en vivo:

```bash
docker compose logs -f web
```

## 4. Crear un usuario administrador

```bash
docker compose exec web python manage.py createsuperuser
```

El panel de admin queda en http://localhost:8000/admin/.

## 5. Modo desarrollo: cambios en vivo sin reconstruir

El repo incluye `docker-compose.override.yml`, que Docker Compose carga
**automáticamente** (no hace falta ningún flag extra) cuando corrés
`docker compose up` desde la raíz del repo. Este archivo:

- Monta tu código local dentro del contenedor `web`, así los cambios en
  archivos `.py` se reflejan sin reconstruir la imagen.
- Corre Gunicorn con `--reload`, que reinicia el worker solo cuando detecta
  un archivo modificado.
- **Apunta `DATABASE_URL` al servicio `db` de este compose**, para que el
  desarrollo local no le escriba a la base compartida (ver sección 2).

Con esto, para iterar alcanza con guardar el archivo — no hace falta volver
a correr `--build`. Reconstruir (`docker compose up -d --build`) sigue siendo
necesario solo cuando cambia `requirements.txt` o el `Dockerfile`.

> Si tocás archivos estáticos (CSS/JS/imágenes), corré igual
> `docker compose exec web python manage.py collectstatic --noinput` para
> que Django los vuelva a juntar. Reiniciar el contenedor también sirve: el
> `entrypoint.sh` lo corre al arrancar.
>
> Con `DEBUG=True` los estáticos se sirven en vivo desde el código montado, así
> que un archivo nuevo parece funcionar sin `collectstatic`. **Con `DEBUG=False`
> no**: ahí se sirve únicamente lo que esté en `staticfiles/`. Si agregás un CSS
> nuevo, corré `collectstatic` antes de dar por bueno que anda.

## 6. Comandos útiles

```bash
docker compose ps                              # ver estado de los contenedores
docker compose logs -f web                      # logs de la app en vivo
docker compose exec web python manage.py shell   # shell de Django
docker compose exec web bash                     # entrar al contenedor
docker compose exec db psql -U simef -d simef    # entrar a la base (usa tus valores de .env)
docker compose down                              # apagar todo (conserva los datos)
docker compose down -v                           # apagar y BORRAR los datos de la base (⚠️ irreversible)
```

## 7. Problemas comunes

- **`POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD` "is not set"** al hacer
  `up`: falta el archivo `.env` o le faltan esas variables. Ver paso 2.
- **Veo la versión vieja de la app** después de bajar cambios nuevos: si el
  `docker-compose.override.yml` no está presente o no se está usando, la
  imagen quedó fija en el código de cuando se construyó — corré
  `docker compose up -d --build`.
- **`db` no arranca / `web` no conecta**: `docker compose logs db` para ver el
  motivo; lo más común es una contraseña vacía o inconsistente entre
  `POSTGRES_PASSWORD` y `DATABASE_URL` en `.env`.
- **Puerto 8000 ocupado**: cambiá el mapeo de puertos en `docker-compose.yml`
  (`"8000:8000"` → por ejemplo `"8001:8000"`) o liberá el puerto.
- **`failed to resolve source metadata for docker.io/library/python:3.11-slim`**,
  con `i/o timeout` hacia `registry-1.docker.io`: no es el `Dockerfile`, es que
  tu red no llega a Docker Hub. Pasa en algunos Codespaces y en redes con
  egreso restringido.

  La salida es traer la imagen base desde un espejo y etiquetarla con el nombre
  que espera el `Dockerfile`. `mirror.gcr.io` espeja Docker Hub y suele estar
  alcanzable:

  ```bash
  docker pull mirror.gcr.io/library/python:3.11-slim
  docker tag  mirror.gcr.io/library/python:3.11-slim python:3.11-slim
  docker compose build web
  ```

  Con la imagen ya etiquetada localmente, BuildKit la resuelve sin salir a la
  red. **No cambies el `FROM` del `Dockerfile`**: sería meter al repositorio un
  arreglo que sólo le hace falta a una red en particular.

  Antes de hacer todo esto, fijate si realmente necesitás reconstruir: con el
  `docker-compose.override.yml` activo el código va montado, así que para
  cambios en `.py` o en plantillas **no hace falta** (ver sección 5). Reconstruir
  sólo es necesario cuando cambia `requirements.txt` o el `Dockerfile`.
