# Proyecto Gestión de Inscripciones a Final del **Instituto 210**

## Proyecto de articulación de materias de la Carrera Tecnicatura Superior en Analisís de Sistemas

## Instalación

### Debian

Clonar el repostorio

Usando  ssh
`git clone git@gitlab.com:Naueru2/Instituto210.git`

Usando https

`https://gitlab.com/Naueru2/Instituto210.git`

Creamos el entorno Virtual

`python3 -m venv env`

Activamos el entorno Virtual
`source env/bin/activate`

Instalamos los paquetes 

`pip3 install -r requirements.txt `

Copiamos el Settings de desarrollo situado en la carpeta del proyecto (gestionInstituto)
`cd gestionInstituto`

`cp settings_DEV.py settings.py`

Corremos las migraciones

`python manage.py migrate`

Para acceder al backoffice http://127.0.0.1:8000/admin se deberá crear un usuario superadmin de la forma:

`python manage.py createsuperuser`

Para ejecutar el proyecto se debe:

`python manage.py runserver`

Para acceder al login, ingresar a http://127.0.0.1:8000 desde el navegador.

Para redireccionar al index luego del login agregar en settings.py

`LOGIN_REDIRECT_URL = 'inicio'`
<!-- Fin -->
"# Instituto210Proyecto"