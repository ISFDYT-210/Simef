# Instalación manual (sin Docker)

Esta guía es para levantar SIMEF instalando Python y Postgres directo en tu
máquina, sin Docker. Si no tenés una razón puntual para hacerlo así, es más
simple usar [DOCKER.md](DOCKER.md).

---

## Instalación en GNU/Linux Debian

### Requisitos previos

- Python 3
- `pip`
- `venv`
- Git

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv
```

### 1. Clonar el repositorio

```bash
git clone git@github.com:ISFDYT-210/Simef.git
# o por HTTPS:
git clone https://github.com/ISFDYT-210/Simef.git
```

### 2. Ingresar al directorio del proyecto

```bash
cd Simef
```

### 3. Crear el entorno virtual

```bash
python3 -m venv env
```

### 4. Activar el entorno virtual

```bash
source env/bin/activate
```

### 5. Instalar las dependencias

```bash
pip3 install -r requirements.txt
```

### 6. Ejecutar las migraciones

```bash
python manage.py migrate
```

> **No hace falta tocar `settings.py`.** El `settings.py` versionado ya sirve
> para desarrollo: `DEBUG` viene en `True` por defecto y, si no definís la
> variable `DATABASE_URL`, usa un SQLite local (`db.sqlite3`) sin que tengas
> que instalar Postgres. Si querés apuntar a una base Postgres, definí
> `DATABASE_URL` en un `.env` (ver [ENV.md](ENV.md)).
>
> El repo incluye además `settings_DEV.py`, `settings_MAIN.py` y
> `settings_TEST.py`, que son variantes históricas con valores fijos.
> **No las copies sobre `settings.py`**: pisarían un archivo versionado y
> perderías la lectura de variables de entorno.

### 7. Crear un usuario administrador

```bash
python manage.py createsuperuser
```

### 8. Ejecutar el servidor de desarrollo

```bash
python manage.py runserver
```

---

## Instalación en Windows

### Requisitos previos

- **Python 3**
- **Git**

> **Importante:** durante la instalación de Python en Windows, marcá la opción
> **"Add Python to PATH"** antes de hacer clic en **Install Now**.

### 1. Clonar el repositorio

Usando **Git Bash**, **PowerShell** o **Símbolo del sistema (CMD)**:

```powershell
git clone https://github.com/ISFDYT-210/Simef.git
# o por SSH (si ya tenés tu clave configurada):
git clone git@github.com:ISFDYT-210/Simef.git
```

### 2. Ingresar al directorio del proyecto

```powershell
cd Simef
```

### 3. Crear el entorno virtual

```powershell
python -m venv env
```

> Si `python` no funciona, probá con `py -m venv env`.

### 4. Activar el entorno virtual

```powershell
# PowerShell
.\env\Scripts\Activate.ps1

# CMD
env\Scripts\activate.bat

# Git Bash
source env/Scripts/activate
```

### 5. Instalar las dependencias

```powershell
pip install -r requirements.txt
```

> Si `pip` no responde correctamente, probá `python -m pip install -r requirements.txt`
> o `py -m pip install -r requirements.txt`.

### 6. Ejecutar las migraciones

```powershell
python manage.py migrate
# si fuera necesario: py manage.py migrate
```

> Igual que en Linux: **no copies ningún `settings_*.py` sobre `settings.py`**.
> El versionado ya funciona para desarrollo y usa SQLite si no definís
> `DATABASE_URL` (ver [ENV.md](ENV.md)).

### 7. Crear un usuario administrador

```powershell
python manage.py createsuperuser
```

### 8. Ejecutar el servidor de desarrollo

```powershell
python manage.py runserver
```

### Problemas comunes en Windows

**Error de ejecución de scripts en PowerShell**: si PowerShell bloquea la
activación del entorno virtual:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Cerrá y abrí nuevamente PowerShell, y volvé a activar el entorno.

**Python no reconocido como comando**: probá con `py`. Si tampoco funciona,
reinstalá Python y marcá **Add Python to PATH**.

**Error al instalar dependencias con pip**: actualizá pip con
`python -m pip install --upgrade pip` (o `py -m pip install --upgrade pip`).

---

## Acceso al sistema (Linux y Windows)

Una vez iniciado el servidor:

- Panel de administración (backoffice): http://127.0.0.1:8000/admin
- Pantalla de login: http://127.0.0.1:8000/

Después de iniciar sesión, el sistema redirige a la vista `inicio`; ya viene
configurado con `LOGIN_REDIRECT_URL` en `gestionInstituto/settings.py`, no hay
que agregar nada.

---

## Notas

- Este entorno está pensado para **desarrollo local**.
- Para un entorno de **producción**, ver [DESPLIEGUE.md](DESPLIEGUE.md).
