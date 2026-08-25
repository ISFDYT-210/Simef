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

Con esto, para iterar alcanza con guardar el archivo — no hace falta volver
a correr `--build`. Reconstruir (`docker compose up -d --build`) sigue siendo
necesario solo cuando cambia `requirements.txt` o el `Dockerfile`.

> Si tocás archivos estáticos (CSS/JS/imágenes), corré igual
> `docker compose exec web python manage.py collectstatic --noinput` para
> que Django los vuelva a juntar.

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
