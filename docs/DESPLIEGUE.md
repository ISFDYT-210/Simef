# Despliegue de SIMEF en producción (Debian)

Stack: **Apache → Gunicorn → Django (Python) + Tailwind → Postgres en Neon**

Este documento describe cómo se sirve SIMEF en un servidor Debian y cómo
desplegar/actualizar el sistema. Está pensado para el instituto (ISFDyT N°210).

La base de datos **no vive en el servidor**: es una Postgres gestionada en
[Neon](https://neon.tech). El servidor solo corre la aplicación y se conecta
por red a Neon. Eso implica dos cosas que conviene tener presentes desde el
principio:

- No hay que instalar, respaldar ni actualizar un motor de base de datos en el
  server. Ese trabajo lo hace Neon.
- Si el servidor se queda sin internet, SIMEF deja de funcionar aunque Apache
  siga levantado. No es como tener la base en la misma máquina.

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
                 │  SQL sobre TLS  (puerto 5432, sale a internet)
                 ▼
 ┌─────────────────────────────────────────────────────────┐
 │ NEON  (Postgres gestionada, región sa-east-1)           │
 │  • Usuarios, materias, mesas, inscripciones, notas       │
 │  • Backups, réplicas y actualizaciones: las hace Neon    │
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
- **Neon**: guarda todos los datos, fuera del servidor.

---

## 2. Requisitos del sistema

En Debian 12 (bookworm), como root:

```bash
apt update
apt install -y apache2 \
               python3 python3-venv python3-dev \
               git curl ca-certificates
```

- `apache2` → servidor web.
- `python3-venv` → entornos virtuales de Python.
- `ca-certificates` → certificados raíz; sin esto falla el TLS contra Neon.

> No hace falta instalar Postgres ni compilar un conector: `requirements.txt`
> trae `psycopg2-binary`, que viene como *wheel* precompilada, y `gunicorn`.
> No instales `postgresql-server` en esta máquina: la base es la de Neon y
> tener otra al lado solo genera confusión sobre cuál es la buena.

---

## 3. Base de datos (Neon)

### 3.1 Obtener la cadena de conexión

En la consola de Neon, dentro del proyecto de SIMEF: **Connect** → copiar la
*connection string* de la rama `main` (la de producción). Tiene esta forma:

```
postgresql://USUARIO:CONTRASEÑA@ep-xxxx-xxxx.sa-east-1.aws.neon.tech/neondb?sslmode=require
```

Tres detalles que importan:

- **`?sslmode=require` no es opcional.** Neon solo acepta conexiones cifradas.
  Todo lo que venga después del `?` en la URL, `settings.py` se lo pasa tal cual
  a psycopg2 como `OPTIONS`, así que la cadena se copia entera, sin recortar.
- **Endpoint directo vs *pooled*.** Neon ofrece además un host con `-pooler` en
  el nombre. Para este despliegue usamos el **directo**: Gunicorn mantiene una
  cantidad chica y fija de procesos, que es justamente el caso donde el pooler
  no aporta. El pooler está pensado para entornos serverless que abren cientos
  de conexiones efímeras.
- **Ramas de Neon.** Neon permite crear ramas de la base. Es la forma prolija de
  tener una base de pruebas con datos realistas sin tocar producción: se crea
  una rama, se usa *su* cadena de conexión en el `.env` de la máquina de
  desarrollo, y lo que se rompa ahí no afecta a `main`.

### 3.2 Cuidado con apuntar a producción desde una máquina de desarrollo

La base es accesible desde cualquier lado con esa URL. Un `python manage.py
migrate` o un `flush` corrido desde una notebook con el `.env` de producción
pega contra los datos reales del instituto, sin red de contención. Dos reglas:

- En las máquinas de desarrollo, el `.env` apunta a una **rama** de Neon o a
  SQLite (basta con no definir `DATABASE_URL`), nunca a `main`.
- Los tests se corren siempre con `--settings=gestionInstituto.settings_TEST`,
  que usa SQLite en memoria. Sin ese parámetro, Django intenta crear una base
  `test_neondb` **en Neon**. Ver [INSTALACION_MANUAL.md](INSTALACION_MANUAL.md).

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
pip install -r requirements.txt      # Django, psycopg2, gunicorn, etc.
```

### 4.2 Configurar el `.env` (no se toca `settings.py`)

**`settings.py` está versionado y ya sirve para producción**: lee todo de
variables de entorno. No hay que editarlo ni copiarle encima un `settings_*.py`
—hacerlo rompería justamente esa lectura—. Toda la configuración del despliegue
vive en `/opt/simef/.env`:

```ini
SECRET_KEY=<una clave larga y secreta, distinta de la del repo>
DEBUG=False
ALLOWED_HOSTS=simef.tu-dominio.edu.ar,127.0.0.1

DATABASE_URL=postgresql://USUARIO:CONTRASEÑA@ep-xxxx.sa-east-1.aws.neon.tech/neondb?sslmode=require

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=<cuenta que envía los mails>
EMAIL_HOST_PASSWORD=<contraseña de aplicación>
EMAIL_USE_TLS=True
```

Para generar una `SECRET_KEY` nueva:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Comprobaciones que vale la pena hacer una sola vez, con calma:

- `DEBUG` se compara como texto contra `'True'`. Cualquier otra cosa
  (`False`, `false`, `0`, o la variable ausente) deja `DEBUG` apagado, que es lo
  que queremos; pero escribir `DEBUG=true` en minúscula también apaga el modo
  debug, no lo enciende. Si alguna vez necesitás encenderlo, va `True` exacto.
- `ALLOWED_HOSTS` se parte por comas y **sin espacios** alrededor de cada host.
  Si queda vacío y `DEBUG=False`, Django rechaza todas las peticiones con
  `DisallowedHost`.
- Si `DATABASE_URL` falta, la app **no falla**: cae silenciosamente a un SQLite
  local vacío y parece que se perdieron todos los datos. Ante un "desapareció
  todo" después de un deploy, esto es lo primero a revisar.

El archivo tiene la contraseña de la base, así que no queda legible para todo
el mundo:

```bash
sudo chown www-data:www-data /opt/simef/.env
sudo chmod 640 /opt/simef/.env
```

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
> `./tailwindcss.exe`. **No lo commitees**: son ~40 MB que quedarían para
> siempre en el historial del repo.

> Hay que recompilar cada vez que se agregan **clases nuevas** de Tailwind en las
> plantillas. Si no cambiaste plantillas, no hace falta.

### 4.4 Migraciones, estáticos y superusuario

```bash
source venv/bin/activate
python manage.py migrate                    # corre CONTRA NEON
python manage.py collectstatic --noinput    # junta todo en staticfiles/
python manage.py createsuperuser            # primer usuario admin
```

`STATIC_ROOT` y `MEDIA_ROOT` ya vienen definidos en `settings.py`
(`/opt/simef/staticfiles` y `/opt/simef/media` con la ubicación sugerida), no
hay que agregarlos.

> `collectstatic` no es opcional ni siquiera "para probar": el proyecto usa
> `CompressedManifestStaticFilesStorage`, que resuelve cada `{% static %}`
> contra un manifiesto generado en ese paso. Si no se corre —o si se corre
> antes del build de Tailwind— las páginas revientan con
> `ValueError: Missing staticfiles manifest entry`.

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
# La base es remota: esperamos a tener red de verdad, no solo la interfaz
After=network-online.target
Wants=network-online.target

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

> **`WorkingDirectory` tiene que ser la raíz del proyecto.** El `.env` lo lee
> `python-dotenv` desde ahí; si el directorio de trabajo es otro, Gunicorn
> arranca igual pero sin `DATABASE_URL`, y la app termina hablándole a un
> SQLite vacío en vez de a Neon.

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

> **El paso 4 modifica la base real.** Antes de una migración que borre o
> transforme columnas, conviene sacar una rama en Neon (sección 8): tarda
> segundos y deja un punto exacto al que volver.

---

## 8. Copias de seguridad

Neon guarda un historial de la base y permite **restaurar a un momento
anterior** (*point-in-time restore*) dentro de la ventana de retención del
plan. Eso cubre el accidente típico: un borrado masivo o una migración que
salió mal.

Dos cosas que ese historial **no** cubre, y conviene resolver aparte:

1. **Antes de tocar la estructura de la base**, crear una rama desde `main` en
   la consola de Neon. Queda como una copia consistente e independiente del
   momento previo, con nombre propio.
2. **Una copia fuera de Neon.** Si se pierde el acceso a la cuenta, el historial
   no sirve de nada. Un volcado periódico a un disco del instituto:

   ```bash
   pg_dump "postgresql://USUARIO:CONTRASEÑA@ep-xxxx.sa-east-1.aws.neon.tech/neondb?sslmode=require" \
     --no-owner --format=custom \
     --file=/ruta/al/backup/simef-$(date +%F).dump
   ```

   Requiere `postgresql-client` (`apt install -y postgresql-client`), que es
   solo el cliente: no levanta ningún servidor de base en la máquina.

Aparte de la base, hay un directorio que Neon no ve y que también hay que
respaldar: **`/opt/simef/media`**, donde van los archivos subidos.

---

## 9. Diagnóstico rápido

- **App caída / error 502** → `sudo systemctl status simef` y
  `sudo journalctl -u simef -n 50` (logs de Gunicorn/Django).
- **Estilos rotos o `Missing staticfiles manifest entry`** → ¿corriste el build
  de Tailwind y después `collectstatic`? ¿`STATIC_ROOT` y el `Alias /static/`
  apuntan al mismo directorio?
- **"Se perdieron todos los datos"** → casi siempre es que la app no está viendo
  `DATABASE_URL` y cayó al SQLite de respaldo. Revisar que exista
  `/opt/simef/.env`, que `www-data` pueda leerlo y que `WorkingDirectory` del
  servicio sea `/opt/simef`. Para confirmar a qué base está hablando:

  ```bash
  sudo -u www-data /opt/simef/venv/bin/python /opt/simef/manage.py shell \
    -c "from django.db import connection; print(connection.settings_dict['ENGINE'], connection.settings_dict['HOST'])"
  ```

- **Error de conexión a la base** → probar la salida a internet desde el server
  (`curl -sS https://neon.tech > /dev/null && echo ok`) y la conexión en sí:

  ```bash
  sudo -u www-data /opt/simef/venv/bin/python /opt/simef/manage.py shell \
    -c "from django.db import connection; connection.ensure_connection(); print('conexion OK')"
  ```

  Si el error menciona el certificado, falta `ca-certificates`. Si menciona
  SSL, revisar que la URL conserve `?sslmode=require`.
- **La primera visita del día tarda unos segundos** → es normal si el proyecto
  de Neon tiene el *autosuspend* activo: la base se apaga cuando no se usa y
  tarda en despertar. Se desactiva en la configuración del proyecto en Neon.
- **Lentitud pareja en todas las páginas** → la base está en São Paulo, así que
  cada consulta cruza internet. Hoy `settings.py` no define `CONN_MAX_AGE`, con
  lo cual Django **abre y cierra una conexión nueva en cada petición** (nuevo
  handshake TLS incluido). Si el uso crece, definir `CONN_MAX_AGE` (por ejemplo
  60 segundos) es la mejora más barata disponible.
- **Logs de Apache** → `/var/log/apache2/simef_error.log`.
