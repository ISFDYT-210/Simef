# Despliegue de SIMEF en producción (Debian)

Stack: **Apache → Gunicorn → Django (Python) + Tailwind → MariaDB**

Este documento describe cómo se sirve SIMEF en un servidor Debian y cómo
desplegar/actualizar el sistema. Está pensado para el instituto (ISFDyT N°210).

---

## 1. Cómo se conecta cada pieza

El recorrido de una petición del navegador hasta la base de datos:

```
  Navegador
     │  HTTP/HTTPS  (puerto 80/443)
     ▼
 ┌─────────────────────────────────────────────────────────┐
 │ APACHE  (servidor web / "puerta de entrada")            │
 │  • Recibe la conexión, termina HTTPS (certificado)       │
 │  • Sirve DIRECTO los archivos estáticos (/static, /media)│
 │  • El resto lo reenvía a Gunicorn (proxy inverso)        │
 └───────────────┬─────────────────────────────────────────┘
                 │  proxy interno  (127.0.0.1:8001)
                 ▼
 ┌─────────────────────────────────────────────────────────┐
 │ GUNICORN  (servidor de aplicación WSGI)                 │
 │  • Corre varios "workers" (procesos) de Django           │
 │  • Traduce la petición HTTP al formato que entiende Django│
 └───────────────┬─────────────────────────────────────────┘
                 │  WSGI
                 ▼
 ┌─────────────────────────────────────────────────────────┐
 │ DJANGO  (Python)   ← la aplicación SIMEF                 │
 │  • Lógica, vistas, plantillas, permisos                  │
 │  • El CSS lo genera Tailwind en un paso previo (build)   │
 └───────────────┬─────────────────────────────────────────┘
                 │  SQL
                 ▼
 ┌─────────────────────────────────────────────────────────┐
 │ MARIADB  (base de datos)                                │
 │  • Usuarios, materias, mesas, inscripciones, notas       │
 └─────────────────────────────────────────────────────────┘
```

**Tailwind** no está "en línea" en cada petición: es un paso de **compilación**
que se corre al desplegar. Genera un único `simef.css` que después Apache sirve
como archivo estático. Por eso no depende de internet ni del CDN (importante en
la red del instituto, que bloquea CDNs externos).

Reparto de responsabilidades, en una frase cada uno:

- **Apache**: atiende al público, hace HTTPS y sirve archivos estáticos rápido.
- **Gunicorn**: mantiene la app Python viva y maneja varias peticiones a la vez.
- **Django/Tailwind**: es SIMEF; Tailwind arma el CSS antes de arrancar.
- **MariaDB**: guarda todos los datos.

---

## 2. Requisitos del sistema

En Debian 12 (bookworm), como root:

```bash
apt update
apt install -y apache2 mariadb-server \
               python3 python3-venv python3-dev \
               build-essential pkg-config libmariadb-dev \
               git curl
```

- `apache2` → servidor web.
- `mariadb-server` → base de datos.
- `python3-venv` → entornos virtuales de Python.
- `build-essential`, `pkg-config`, `libmariadb-dev` → necesarios para compilar
  el conector `mysqlclient` de Python.

---

## 3. Base de datos (MariaDB)

Asegurar la instalación y crear la base + usuario:

```bash
mysql_secure_installation      # poné contraseña de root, quitá accesos anónimos
```

Entrar como root y crear todo (usá utf8mb4 para acentos y emojis):

```sql
sudo mysql -u root -p

CREATE DATABASE simef CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'simef_user'@'localhost' IDENTIFIED BY 'PONER_UNA_CLAVE_FUERTE';
GRANT ALL PRIVILEGES ON simef.* TO 'simef_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

---

## 4. La aplicación (Django + Tailwind)

### 4.1 Traer el código y crear el entorno

```bash
# Ubicación sugerida del proyecto en el server
sudo mkdir -p /opt/simef
sudo chown $USER:$USER /opt/simef
cd /opt/simef

git clone <URL_DE_TU_REPO> .        # o copiar el proyecto acá

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt      # Django, etc.
pip install gunicorn mysqlclient     # si no están en requirements
```

### 4.2 Conectar Django a MariaDB

En `gestionInstituto/settings.py`, el bloque `DATABASES`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'simef',
        'USER': 'simef_user',
        'PASSWORD': 'PONER_UNA_CLAVE_FUERTE',
        'HOST': '127.0.0.1',
        'PORT': '3306',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}
```

Y para producción, en el mismo `settings.py`:

```python
DEBUG = False
ALLOWED_HOSTS = ['tu-dominio-o-ip', 'localhost', '127.0.0.1']

STATIC_URL = '/static/'
STATIC_ROOT = '/opt/simef/staticfiles'     # donde collectstatic junta todo
# Si usás subidas de archivos (imágenes de perfil, etc.):
MEDIA_URL = '/media/'
MEDIA_ROOT = '/opt/simef/media'
```

> Consejo: no dejes `SECRET_KEY`, la clave de la base ni credenciales de correo
> escritas en el código. Pasalas por variables de entorno.

### 4.3 Compilar el CSS con Tailwind

Este es el paso de "build" del frontend. Genera el `simef.css` que sirve Apache.
Usamos el **CLI standalone** de Tailwind (no hace falta Node):

```bash
cd /opt/simef

# Descargar el binario del CLI una sola vez. IMPORTANTE: versión FIJA v3.4.17,
# NO 'latest' (la última es Tailwind v4, que usa otra config y rompe este setup).
curl -L -o tailwindcss \
  https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-linux-x64
chmod +x tailwindcss

# Compilar el CSS (config e input van en el repo: ver kit de build)
./tailwindcss -c tailwind.config.js -i input.css \
  -o inscripcionFinales/static/css/simef.css --minify
```

> En una máquina Windows de desarrollo (Git Bash), el binario es
> `...download/v3.4.17/tailwindcss-windows-x64.exe` y se ejecuta como
> `./tailwindcss.exe`.

> Hay que recompilar cada vez que se agregan **clases nuevas** de Tailwind en las
> plantillas. Si no cambiaste plantillas, no hace falta.

### 4.4 Migraciones, estáticos y superusuario

```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput   # junta todo en STATIC_ROOT
python manage.py createsuperuser            # primer usuario admin
```

---

## 5. Gunicorn (servicio de aplicación)

Probar a mano que arranca:

```bash
cd /opt/simef && source venv/bin/activate
gunicorn --bind 127.0.0.1:8001 gestionInstituto.wsgi:application
```

Si responde, dejarlo como servicio de systemd para que arranque solo.
Crear `/etc/systemd/system/simef.service`:

```ini
[Unit]
Description=SIMEF - Gunicorn
After=network.target mariadb.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/simef
ExecStart=/opt/simef/venv/bin/gunicorn \
          --workers 3 \
          --bind 127.0.0.1:8001 \
          gestionInstituto.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

Activarlo:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now simef
sudo systemctl status simef
```

> `--workers 3` es un punto de partida razonable (regla común: 2 × núcleos + 1).

---

## 6. Apache (proxy inverso + estáticos)

Habilitar los módulos necesarios:

```bash
sudo a2enmod proxy proxy_http headers rewrite
```

Crear `/etc/apache2/sites-available/simef.conf`:

```apache
<VirtualHost *:80>
    ServerName tu-dominio-o-ip

    # Archivos estáticos y de medios: los sirve Apache directo (rápido)
    Alias /static/ /opt/simef/staticfiles/
    <Directory /opt/simef/staticfiles>
        Require all granted
    </Directory>

    Alias /media/ /opt/simef/media/
    <Directory /opt/simef/media>
        Require all granted
    </Directory>

    # Todo lo demás va a Gunicorn
    ProxyPreserveHost On
    ProxyPass        /static/ !
    ProxyPass        /media/  !
    ProxyPass        /        http://127.0.0.1:8001/
    ProxyPassReverse /        http://127.0.0.1:8001/

    ErrorLog  ${APACHE_LOG_DIR}/simef_error.log
    CustomLog ${APACHE_LOG_DIR}/simef_access.log combined
</VirtualHost>
```

Activar el sitio y recargar:

```bash
sudo a2dissite 000-default.conf     # opcional, desactiva el sitio por defecto
sudo a2ensite simef.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

Permisos: que `www-data` pueda leer el proyecto y escribir en `media/`:

```bash
sudo chown -R www-data:www-data /opt/simef/media /opt/simef/staticfiles
```

### HTTPS (recomendado)

Con Certbot se agrega el certificado y el redirect a HTTPS:

```bash
sudo apt install -y certbot python3-certbot-apache
sudo certbot --apache -d tu-dominio
```

---

## 7. Checklist para ACTUALIZAR (cada vez que hay cambios)

```bash
cd /opt/simef
source venv/bin/activate

git pull                                   # 1. traer cambios
pip install -r requirements.txt            # 2. dependencias nuevas (si hubo)

# 3. recompilar el CSS SOLO si tocaste plantillas / clases de Tailwind
./tailwindcss -c tailwind.config.js -i input.css \
  -o inscripcionFinales/static/css/simef.css --minify

python manage.py migrate                   # 4. cambios de base de datos
python manage.py collectstatic --noinput   # 5. juntar estáticos

sudo systemctl restart simef               # 6. reiniciar la app
```

Apache normalmente no hay que reiniciarlo salvo que cambies su config.

---

## 8. Diagnóstico rápido

- App caída / error 502 → `sudo systemctl status simef` y
  `sudo journalctl -u simef -n 50` (logs de Gunicorn/Django).
- Estilos rotos → ¿corriste el build de Tailwind y `collectstatic`?
  ¿`STATIC_ROOT` y el `Alias /static/` coinciden?
- Error de base → revisar credenciales del bloque `DATABASES` y que
  `mariadb.service` esté activo.
- Logs de Apache → `/var/log/apache2/simef_error.log`.
