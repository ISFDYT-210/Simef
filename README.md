# Proyecto Gestión de Inscripciones a Final - Instituto 210

## Proyecto de articulación de materias de la carrera  
**Tecnicatura Superior en Análisis de Sistemas**

---

## Descripción

Este proyecto corresponde al sistema de **Gestión de Inscripciones a Mesas de Examen Final** del **Instituto 210**.

Su objetivo es facilitar la administración de inscripciones, el acceso de usuarios y la gestión interna mediante un panel de administración (*backoffice*).

---

## Requisitos previos

Antes de comenzar, asegurate de tener instalado en tu sistema:

- Python 3
- `pip`
- `venv`
- Git

En GNU/Linux Debian podés instalarlos con:

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv
```

---

## Instalación en GNU/Linux Debian

### 1. Clonar el repositorio

Podés clonar el proyecto usando **SSH** o **HTTPS**.

#### Usando SSH

```bash
git clone git@github.com:ISFDYT-210/Simef.git
```

#### Usando HTTPS

```bash
git clone https://github.com/ISFDYT-210/Simef.git
```

---

### 2. Ingresar al directorio del proyecto

```bash
cd Simef
```

---

### 3. Crear el entorno virtual

```bash
python3 -m venv env
```

---

### 4. Activar el entorno virtual

```bash
source env/bin/activate
```

---

### 5. Instalar las dependencias

```bash
pip3 install -r requirements.txt
```

---

### 6. Configurar el archivo de settings

Ingresar a la carpeta principal del proyecto Django:

```bash
cd gestionInstituto
```

Copiar el archivo de configuración de desarrollo:

```bash
cp settings_DEV.py settings.py
```

---

### 7. Ejecutar las migraciones

```bash
python manage.py migrate
```

---

### 8. Crear un usuario administrador

Para acceder al panel de administración (*backoffice*), es necesario crear un usuario con permisos de superusuario:

```bash
python manage.py createsuperuser
```

---

### 9. Ejecutar el servidor de desarrollo

```bash
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
cd Instituto210
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
