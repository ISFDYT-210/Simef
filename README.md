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

- Este entorno está pensado para **desarrollo local**.
- Para un entorno de **producción**, se recomienda:
  - usar variables de entorno para datos sensibles,
  - configurar `DEBUG = False`,
  - definir `ALLOWED_HOSTS`,
  - utilizar un servidor como **Gunicorn** o **uWSGI** detrás de **Nginx** o **Apache**.

---
## Instalación en Windows

### Requisitos previos

Antes de comenzar, asegurate de tener instalado en tu sistema:

- **Python 3**
- **Git**

> **Importante:** durante la instalación de Python en Windows, marcá la opción  
> **“Add Python to PATH”** antes de hacer clic en **Install Now**.

---

### 1. Clonar el repositorio

Podés clonar el proyecto usando **Git Bash**, **PowerShell** o **Símbolo del sistema (CMD)**.

#### Usando HTTPS

```powershell
git clone https://github.com/ISFDYT-210/Simef.git
```

#### Usando SSH (si ya tenés tu clave configurada)

```powershell
git clone git@github.com:ISFDYT-210/Simef.git
```

---

### 2. Ingresar al directorio del proyecto

```powershell
cd Simef
```

---

### 3. Crear el entorno virtual

```powershell
python -m venv env
```

> Si `python` no funciona, probá con:

```powershell
py -m venv env
```

---

### 4. Activar el entorno virtual

#### En PowerShell

```powershell
.\env\Scripts\Activate.ps1
```

#### En CMD

```cmd
env\Scripts\activate.bat
```

#### En Git Bash

```bash
source env/Scripts/activate
```

---

### 5. Instalar las dependencias

```powershell
pip install -r requirements.txt
```

> Si `pip` no responde correctamente, podés usar:

```powershell
python -m pip install -r requirements.txt
```

o

```powershell
py -m pip install -r requirements.txt
```

---

### 6. Configurar el archivo de settings

Ingresar a la carpeta principal del proyecto Django:

```powershell
cd gestionInstituto
```

Copiar el archivo de configuración de desarrollo:

#### En PowerShell

```powershell
Copy-Item settings_DEV.py settings.py
```

#### En CMD

```cmd
copy settings_DEV.py settings.py
```

---

### 7. Ejecutar las migraciones

```powershell
python manage.py migrate
```

> Si fuera necesario:

```powershell
py manage.py migrate
```

---

### 8. Crear un usuario administrador

Para acceder al panel de administración (*backoffice*), es necesario crear un usuario con permisos de superusuario:

```powershell
python manage.py createsuperuser
```

---

### 9. Ejecutar el servidor de desarrollo

```powershell
python manage.py runserver
```

---

## Acceso al sistema

### Panel de administración (Backoffice)

Una vez iniciado el servidor, podés acceder al panel de administración desde:

```text
http://127.0.0.1:8000/admin
```

---

### Pantalla de login

Para ingresar al sistema desde el navegador:

```text
http://127.0.0.1:8000/
```

---

## Redirección luego del login

Si querés que, luego de iniciar sesión, el usuario sea redirigido a la vista `inicio`, agregá la siguiente línea en el archivo `settings.py`:

```python
LOGIN_REDIRECT_URL = 'inicio'
```

---

## Problemas comunes en Windows

### Error GTK

En sistemas windows es necesario instalar el software GTK. El siguiente link los deriva al archivo .exe que se debe bajar : (https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2022-01-04/gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe)

### Error de ejecución de scripts en PowerShell

Si PowerShell bloquea la activación del entorno virtual, ejecutá:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Luego cerrá y abrí nuevamente PowerShell, y volvé a activar el entorno:

```powershell
.\env\Scripts\Activate.ps1
```

---

### Python no reconocido como comando

Si aparece un error como:

```text
'python' no se reconoce como un comando interno o externo
```

probá con:

```powershell
py
```

Si tampoco funciona, reinstalá Python y asegurate de marcar:

- **Add Python to PATH**

---

### Error al instalar dependencias con pip

Actualizá `pip` con:

```powershell
python -m pip install --upgrade pip
```

o

```powershell
py -m pip install --upgrade pip
```

---

## Notas

- Este entorno está pensado para **desarrollo local**.
- Para un entorno de **producción**, se recomienda:
  - usar variables de entorno para datos sensibles,
  - configurar `DEBUG = False`,
  - definir `ALLOWED_HOSTS`,
  - utilizar un servidor como **Gunicorn** o **uWSGI** detrás de **Nginx** o **Apache**.
