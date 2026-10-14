# Producción de SIMEF en Vercel

Stack: **Vercel (función Python) → Django + WhiteNoise → Postgres en Neon**

El 12 de octubre de 2026 se decidió que producción corre en **Vercel**, con la
base en **Neon**. Era el único camino que ya funcionaba y el único que se podía
dejar listo en el Sprint 3. Los otros dos quedan como alternativa para cuando el
instituto tenga un servidor propio:

- Docker en un servidor por SSH: `.github/workflows/deploy-docker.yml`, apagado
  y con el paso por SSH pendiente de arreglo.
- Apache + Gunicorn en Debian, a mano: [DESPLIEGUE.md](DESPLIEGUE.md).

---

## 1. Cómo se publica

La publicación la hace la **integración de Vercel con GitHub** (proyecto
`isfdyt210s-projects/simef`), no un workflow de Actions:

| Evento en GitHub | Qué hace Vercel |
|---|---|
| Push a `main` (en la práctica, el merge de un PR) | Despliega a **producción**: `www.pulqui-simef210.com.ar` |
| PR abierto o actualizado | Arma una **vista previa** con su propia URL, que aparece como check "Vercel" en el PR |

A `main` solo se llega por PR con el CI en verde: lo exige el ruleset de la
rama. Por eso no hay que desplegar a mano, y `deploy-vercel.yml` queda
desactivado, porque si no cada deploy saldría dos veces.

`vercel.json` manda todas las rutas a `gestionInstituto/wsgi.py`, que corre como
una función Python (`@vercel/python`). Los estáticos los sirve WhiteNoise desde
adentro de esa función.

### Lo que esto implica

- **No corre `entrypoint.sh` ni `build.sh`.** `vercel.json` usa la clave
  `builds`, y con esa clave Vercel no aplica el *Build Command* que esté
  configurado en el panel del proyecto. Por lo tanto:
  - **Las migraciones no se aplican solas.** Hay que correrlas aparte (ver la
    sección 3).
  - **Los estáticos salen de la carpeta `staticfiles/` del repo**, tal cual
    está commiteada. Si se agrega o cambia un CSS, JS o imagen en
    `inscripcionFinales/static/`, hay que correr
    `python manage.py collectstatic --noinput` y commitear `staticfiles/`.
    Por eso esa carpeta está versionada y no se borra.
- **El disco es de solo lectura.** Lo que la app guarda en `media/`, como las
  fotos de perfil, no se puede escribir. Para tener fotos de perfil en
  producción hace falta un almacenamiento externo (por ejemplo, Vercel Blob o
  un bucket S3 con `django-storages`).
- **Cada pedido corre en una función con límite de tiempo.** Las tareas largas,
  como un PDF muy pesado, tienen que entrar en ese límite.

## 2. Variables de entorno

Se cargan en Vercel → Project → Settings → **Environment Variables**, separadas
por entorno (*Production*, *Preview*). El repo no las tiene, y `.env` nunca se
sube.

| Variable | Production | Comentario |
|---|---|---|
| `DEBUG` | `False` | Si falta, ya vale `False`; conviene cargarla igual para que se vea. Con `True` se muestran errores con código y datos. |
| `SECRET_KEY` | Clave larga y aleatoria, propia de producción | **Obligatoria:** con `DEBUG=False` la app no arranca sin ella. Generarla con `python -c "import secrets; print(secrets.token_urlsafe(50))"`. |
| `ALLOWED_HOSTS` | `www.pulqui-simef210.com.ar,pulqui-simef210.com.ar` | **Obligatoria:** con `DEBUG=False` la app no arranca sin ella. Sin espacios. Para que también abran las vistas previas, agregar `.vercel.app` solo en *Preview*. |
| `CSRF_TRUSTED_ORIGINS` | `https://www.pulqui-simef210.com.ar,https://pulqui-simef210.com.ar` | Con esquema. |
| `DATABASE_URL` | Cadena de conexión de Neon con `?sslmode=require` | **Obligatoria:** con `DEBUG=False` la app no arranca sin ella, en vez de caer a un SQLite vacío. Ver [DESPLIEGUE.md §3.1](DESPLIEGUE.md) para obtenerla. |
| `ADMIN_HABILITADO` | **No definirla** | Sin la variable, con `DEBUG=False` el panel `/admin/` de Django no existe: la ruta redirige al inicio. Solo para una corrección puntual: `True`, redeploy, y después quitarla y redeployar de nuevo. |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` y el resto de `EMAIL_*` | Cuenta de correo del instituto | Para recuperar la contraseña y avisos. |

### HTTPS

Con `DEBUG=False`, `settings.py` activa solo lo que pide el checklist de
despliegue de Django: redirección de http a https, cookies de sesión y CSRF
marcadas `Secure`, y HSTS por una hora (`SECURE_HSTS_SECONDS=3600`). En
desarrollo, con `DEBUG=True`, todo eso queda apagado. Cada ajuste se puede pisar
desde el entorno, sin tocar el código:

| Variable | Por defecto con `DEBUG=False` | Cuándo cambiarla |
|---|---|---|
| `SECURE_HSTS_SECONDS` | `3600` (una hora) | Cuando producción lleve unos días andando bien por HTTPS, subirla a `31536000` (un año). El navegador recuerda el valor y no se puede acortar antes de que venza. |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `False` | Solo después de verificar que **todos** los subdominios del dominio se sirven por HTTPS. |
| `SECURE_HSTS_PRELOAD` | `False` | No activarla sin una decisión explícita: inscribe el dominio en la lista que traen los navegadores, y en la práctica no se puede deshacer. |
| `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` | `True` | Solo para diagnosticar. Por ejemplo, si apareciera un bucle de redirecciones, `SECURE_SSL_REDIRECT=False` lo corta sin un deploy de código. |

Django sabe que el pedido llegó por HTTPS por la cabecera `X-Forwarded-Proto`,
que pone Vercel (`SECURE_PROXY_SSL_HEADER`). Fuera de un proxy que pise esa
cabecera, ese ajuste no es seguro.

**Las vistas previas no tienen que usar la base de producción.** Una vista
previa corre el código de un PR que todavía no se revisó del todo. Si su
`DATABASE_URL` apunta a la base de producción, ese código lee y escribe datos
reales de estudiantes. Para *Preview* conviene usar una rama de Neon aparte.

Después de cambiar una variable hay que volver a desplegar (Deployments → ⋯ →
*Redeploy*): Vercel no la aplica a los deploys que ya existen.

## 3. Migraciones

Como Vercel no corre `migrate`, las migraciones nuevas se aplican a mano, **antes
de mergear a `main`** el PR que las trae, con el script del MOP (procedimiento
OP-03 de [MOP.md](MOP.md)):

```bash
./scripts/migrar_neon.sh preview      # rama preview de Neon (PREVIEW_DATABASE_URL del .env)
./scripts/migrar_neon.sh produccion   # base del instituto (DATABASE_URL del .env)
```

El script no muestra la cadena de conexión, se niega a seguir si la de `preview` es
la de producción, muestra el plan antes de escribir y, en producción, pide confirmar
que existe la rama de respaldo de hoy (OP-02).

Cuidado: la base de producción es la del instituto. **Nunca correr `migrate`
contra Neon desde una rama de trabajo**, porque se aplicarían migraciones que
todavía no están en `develop`. Así apareció la columna `ausente` (#103).
`docker compose` no corre este riesgo, porque su `DATABASE_URL` apunta a la base
local (ver [DOCKER.md](DOCKER.md)).

## 4. Volver atrás

Si un deploy a producción sale mal:

1. **En Vercel**, Deployments → elegir el deploy anterior que funcionaba → ⋯ →
   *Promote to Production* (o *Instant Rollback*). Producción vuelve en segundos.
2. **En el repo**, revertir el merge en `main` con un PR, para que el próximo
   push no vuelva a publicar el cambio roto.
3. **Si el deploy traía migraciones**, la base no vuelve atrás sola: restaurar
   desde la rama de Neon que se creó en el paso 1 de la sección 3.

## 5. Antes de cada salida a producción

- [ ] CI en verde en el PR a `main`.
- [ ] Job *Dependencias vulnerables (pip-audit)* sin vulnerabilidades. Hoy es
      informativo: aunque pase en verde, hay que mirar su resumen.
- [ ] Migraciones nuevas: rama de Neon creada, `migrate --plan` revisado y
      migraciones aplicadas.
- [ ] Estáticos nuevos o modificados: `python manage.py collectstatic --noinput --clear`
      y `staticfiles/` commiteado. El CI falla si no coincide.
- [ ] Variables de *Production* revisadas (sección 2).
- [ ] Después del deploy: entrar, iniciar sesión, inscribirse a un final y
      generar una constancia.
