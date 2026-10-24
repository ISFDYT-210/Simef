# Manual de Operaciones y Procedimientos (MOP)

**SIMEF · Módulo de Inscripción a Mesas de Finales · ISFDyT N.º 210**

| | |
|---|---|
| Estado | **Borrador.** Faltan los responsables de la sección 2 (pendiente P-04 del decision log) y la comprobación de QA de la sección 8. |
| Versión del documento | 0.3 · 18/10/2026 |
| Coordina | Backend, con Frontend y el responsable del entorno |
| Comprueba | QA, ejecutando cada procedimiento (sección 8) |
| Revisa los límites | Análisis Funcional (sección 7) |

Este documento dice **cómo se opera SIMEF en producción**: quién publica una
versión, cómo se migra la base, cómo se respalda y se restaura, cómo se vuelve
atrás y qué hacer ante un incidente. La explicación técnica de fondo (por qué
cada variable, cómo funciona el despliegue) está en
[PRODUCCION_VERCEL.md](PRODUCCION_VERCEL.md). Acá van los pasos.

**Qué no hay en este documento, a propósito:** contraseñas, cadenas de conexión,
claves ni detalles de vulnerabilidades abiertas. El repositorio es público.

---

## 1. Destino y versión desplegada

| | |
|---|---|
| Aplicación | Vercel, proyecto `isfdyt210s-projects/simef` (función Python con `@vercel/python`) |
| Dominios | `www.pulqui-simef210.com.ar` y `pulqui-simef210.com.ar` |
| Base de datos | Postgres en Neon: rama principal (producción) y rama `preview` (vistas previas) |
| Qué se publica | La rama `main` del repositorio `ISFDYT-210/Simef`. Cada push a `main` se publica solo. |
| Cómo se identifica la versión | El commit de `main` que muestra el deploy en Vercel (Deployments → el deploy de *Production* → *Source*). Cada publicación se anota en el build log del sprint. |
| Stack | Django 5.2 LTS, Python 3.11 en el CI, WhiteNoise para los estáticos, django-axes para el límite de intentos de login. |

El único destino de producción es este (decision log, D-05). Las guías de Docker
por SSH y de Debian ([DESPLIEGUE.md](DESPLIEGUE.md)) son alternativas para un
servidor propio, y no se usan.

## 2. Roles y responsables

El lineamiento pide asignar un responsable para cada área. **Completar antes de la
primera publicación.** Cada rol necesita además un suplente, para cuando el
titular no esté.

| Rol | Qué hace | Titular | Suplente |
|---|---|---|---|
| Responsable de publicación | Ejecuta OP-01 y decide si se publica o se vuelve atrás | *a definir* | *a definir* |
| Responsable de la base (Neon) | Ejecuta OP-02, OP-03 y OP-06; administra la consola de Neon | *a definir* | *a definir* |
| Responsable del panel (Vercel) | Variables de entorno, deploys, reversión (OP-05) | *a definir* | *a definir* |
| Responsable de la cuenta de correo | Rota la contraseña de aplicación (OP-07) | *a definir* | *a definir* |
| Validación (QA) | Comprueba cada procedimiento y la versión publicada (OP-04) | *a definir* | *a definir* |
| Referente funcional (AF) | Decide sobre reglas y datos ante un incidente funcional | *a definir* | *a definir* |

**Escalamiento:** si un procedimiento falla y el titular no lo puede resolver en
el tiempo indicado, avisa al suplente y al responsable de publicación. Si afecta
datos de estudiantes, también al referente funcional y a la dirección del
instituto (ver OP-10).

## 3. Prerrequisitos

Para operar hace falta:

- **Accesos:** miembro del repositorio en GitHub; acceso al proyecto en Vercel; acceso
  al proyecto en la consola de Neon. Cada uno con su propia cuenta y verificación en
  dos pasos.
- **En la máquina de quien migra o respalda:** git, Docker y Python 3; el repositorio
  clonado; la imagen de desarrollo construida (`docker compose build web`); y un
  `.env` local, que no se sube nunca, con:
  - `DATABASE_URL`: la cadena de la rama principal de Neon (producción);
  - `PREVIEW_DATABASE_URL`: la cadena de la rama `preview`.

  Las dos son del dueño de la base y se copian desde la consola de Neon, con
  **Connect** y eligiendo la rama en el selector *Branch*. OP-12 agrega al `.env`
  `APP_DATABASE_URL` y `PREVIEW_APP_DATABASE_URL`, las cadenas del usuario acotado
  de la app, que son las que van en Vercel.

## 4. Configuración

Las variables de producción se cargan en **Vercel → Settings → Environment
Variables**, por separado para *Production* y para *Preview*. Las secretas van con
tipo **Secret**: Vercel no deja volver a verlas, así que si hace falta el valor, se
vuelve a generar o se copia de Neon.

| Variable | Tipo | Production | Preview |
|---|---|---|---|
| `DEBUG` | Config | `False` | `False` |
| `SECRET_KEY` | **Secret** | clave propia, de 50 caracteres o más | otra clave, distinta de la de Production |
| `ALLOWED_HOSTS` | Config | los dos dominios del instituto | `.vercel.app` |
| `CSRF_TRUSTED_ORIGINS` | Config | los dos dominios, con `https://` | `https://*.vercel.app` |
| `DATABASE_URL` | **Secret** | rama principal de Neon, con el usuario `simef_app` (OP-12) | rama `preview` de Neon, con el usuario `simef_app` |
| `EMAIL_HOST_USER`, `EMAIL_PORT` (`587`) | Config | cuenta de correo del sistema | igual |
| `EMAIL_HOST_PASSWORD` | **Secret** | contraseña de aplicación del correo | igual |
| `ADMIN_HABILITADO` | Config | **no definirla** (ver OP-08) | no definirla |

Con `DEBUG=False`, la app **no arranca** si falta `SECRET_KEY`, `ALLOWED_HOSTS` o
`DATABASE_URL`, y el log de Vercel dice cuál falta. Un cambio de variable se aplica
recién en el próximo deploy: después de cambiarla hay que redeployar.

## 5. Controles de CI/CD

A `main` solo se llega por Pull Request. El ruleset "Proteger main" de GitHub no
tiene excepciones y exige estos checks en verde:

| Check | Qué controla |
|---|---|
| Lint (flake8) | Errores de sintaxis y nombres indefinidos |
| Tests (Django + PostgreSQL) | Toda la suite; que no falten migraciones; que `staticfiles/` coincida con `collectstatic` |
| Django deployment checklist | `check --deploy` con `DEBUG=False`, sin ningún aviso |
| Build imagen Docker | Que el Dockerfile construya |

El job **Dependencias vulnerables (pip-audit)** corre en cada PR y frena el PR si
hay una dependencia vulnerable. Todavía no es obligatorio en el ruleset de `main`
(pendiente P-08 del decision log).

**Vercel no corre migraciones ni `collectstatic`.** Las migraciones se aplican a
mano con OP-03, y los estáticos se sirven tal como están commiteados en
`staticfiles/`, controlados por el CI.

---

## 6. Procedimientos

Cada procedimiento dice cuándo se usa, quién lo ejecuta y quién lo valida, los
pasos, cómo se verifica el resultado y qué hacer si falla. Al terminar uno, quien
lo ejecutó lo anota en el build log del sprint (sección "Operaciones fuera del
código").

### OP-01 · Publicar una versión

**Cuándo:** para pasar a producción lo que está en `develop`.
**Ejecuta:** responsable de publicación. **Valida:** QA.
**Ventana sugerida:** fuera del período de inscripción a finales, y con el
responsable de la base disponible.

1. **Antes**, todo esto tiene que estar cumplido:
   - CI en verde en el PR de `develop` a `main`.
   - QA aprobó la versión candidata en la vista previa de `develop` (regresión del
     módulo y verificación de los hallazgos corregidos).
   - Las variables de *Production* están revisadas (sección 4).
   - El responsable de la base está disponible durante toda la publicación.
2. **Respaldo:** OP-02, con la rama de respaldo de hoy.
3. **Migraciones:** OP-03 en **producción**. Las migraciones van **antes** del merge:
   el código nuevo necesita las columnas nuevas. Mientras tanto, la versión vieja
   sigue funcionando, porque las migraciones de este proyecto solo agregan.
4. **Publicación:** mergear el PR de `develop` a `main` en GitHub. Vercel publica solo.
   Esperar a que el deploy diga *Ready*.
5. **Comprobación:** OP-04.
6. **Registro:** anotar en el build log el commit publicado, la hora, el resultado de
   OP-04 y la rama de respaldo usada.

**Si falla:** si OP-04 encuentra un error que impide usar el sistema o compromete
datos, se vuelve atrás con OP-05 sin esperar. Un error menor se registra como
defecto y se corrige con un PR nuevo.

### OP-02 · Respaldar la base

**Cuándo:** antes de cada publicación con migraciones, antes de cualquier operación
manual sobre la base, y al menos una vez por semana durante el período de
inscripción.
**Ejecuta:** responsable de la base. **Valida:** responsable de publicación.

1. **Rama de respaldo en Neon,** el respaldo principal y el más rápido de restaurar:
   consola de Neon → **Branches → New branch** → origen: la rama principal, con los
   datos actuales → nombre `respaldo-AAAAMMDD` (por ejemplo `respaldo-20261105`) →
   sin borrado automático.
2. **Copia en archivo,** el respaldo secundario, fuera de Neon: en la máquina del
   responsable, `./scripts/copiar_neon_a_local.sh`. Baja un dump de producción a
   `backups/` (ignorada por git) y lo restaura en la base local para comprobar que
   sirve. El archivo tiene datos personales de estudiantes: no se sube a ningún lado,
   no se comparte y se borra cuando deja de hacer falta.
3. **Ventana de restauración:** anotar en la sección 8 hasta cuándo hacia atrás
   permite restaurar el plan de Neon (consola → configuración del proyecto). Ese
   dato define cuánto tiempo hay para detectar un problema y volver a un punto
   anterior sin depender de las ramas de respaldo.

**Cómo se verifica:** la rama aparece en la lista de Branches con la fecha de hoy, y
la copia local tiene los mismos usuarios que producción.

**Limpieza:** se conservan las ramas de respaldo de las dos últimas publicaciones.
Las anteriores se borran, con el ok del responsable de publicación.

### OP-03 · Aplicar migraciones en Neon

**Cuándo:** en OP-01 (producción) y cada vez que `develop` traiga migraciones nuevas
(rama `preview`, para que la vista previa funcione).
**Ejecuta:** responsable de la base. **Valida:** responsable de publicación.

```bash
./scripts/migrar_neon.sh preview      # rama preview
./scripts/migrar_neon.sh produccion   # base del instituto
```

El script lee la cadena del `.env` sin mostrarla y se niega a seguir si no es de
Neon, o si la de `preview` resulta ser la de producción. Después muestra el plan sin
escribir nada. En producción, además, pide confirmar que ya existe la rama de
respaldo de hoy (OP-02). Aplica las migraciones solo con una confirmación escrita, y
al final vuelve a mostrar el plan.

**Cómo se verifica:** el plan final dice `No planned migration operations`.

**Si falla:** **no reintentar a ciegas.** Copiar el error, sin cadenas de conexión, y
avisar al responsable de publicación. Si la base quedó a medio migrar, se restaura
desde la rama de respaldo (OP-06).

**Nunca:** correr `migrate` contra Neon desde una rama de trabajo, ni levantar
`docker compose` con el `DATABASE_URL` de Neon. El compose de desarrollo usa la base
local a propósito.

### OP-04 · Comprobar la versión publicada

**Cuándo:** después de cada publicación (OP-01) y de cada reversión (OP-05).
**Ejecuta y registra:** QA. Si QA no está, el responsable de publicación.

Con una cuenta de prueba de cada rol, en producción:

1. `https://www.pulqui-simef210.com.ar` y `https://pulqui-simef210.com.ar` cargan, y
   `http://` redirige a `https://`.
2. Iniciar sesión y cerrar sesión.
3. **Estudiante:** ver los finales disponibles y el motivo de los que no puede
   rendir. No inscribirse en una mesa real: para la inscripción usar la vista previa.
4. **Preceptor:** ver el listado de mesas y la nómina de una mesa, y generar el acta
   volante.
5. Descargar una constancia en PDF.
6. `/admin/` redirige al inicio.
7. En Vercel → el deploy → **Logs**: no aparecen errores en los minutos posteriores.

**Cómo se registra:** en el build log, con el commit publicado, quién comprobó, cada
punto en "bien" o con el problema, y la hora.

**Si falla:** ver OP-01, "Si falla".

### OP-05 · Volver a la versión anterior

**Cuándo:** una publicación dejó el sistema inutilizable o compromete datos.
**Decide:** responsable de publicación. **Ejecuta:** responsable del panel.
**Valida:** QA, con OP-04.

1. **Código, en minutos:** Vercel → **Deployments** → el último deploy de
   *Production* que funcionaba → ⋯ → **Promote to Production** (o **Instant
   Rollback**). Según el plan de Vercel, puede que solo se pueda volver al deploy
   inmediatamente anterior: verificarlo en el panel antes de la primera
   publicación.
2. **Repositorio:** abrir un PR que revierta el merge en `main`. Si no, el próximo push
   vuelve a publicar el cambio roto.
3. **Base:** las migraciones de este proyecto solo agregan columnas y tablas, y la
   versión anterior funciona con ellas. Por eso, **en general no hay que revertir la
   base.** Solo si el problema son datos dañados: OP-06.
4. OP-04 sobre la versión restaurada, y registro en el build log.

### OP-06 · Restaurar la base

**Cuándo:** datos borrados o dañados, o una migración que salió mal.
**Decide:** responsable de publicación, con el referente funcional si hay datos de
estudiantes en juego. **Ejecuta:** responsable de la base. **Valida:** QA.

1. **Frenar el daño:** si el problema sigue ocurriendo, volver atrás el código
   (OP-05).
2. **Elegir el punto de restauración:**
   - la rama de respaldo de la última publicación (`respaldo-AAAAMMDD`), o
   - un momento anterior al problema, si está dentro de la ventana de restauración de
     Neon (OP-02, punto 3).
3. **Antes de restaurar, guardar el estado actual:** crear una rama desde la principal
   llamada `antes-de-restaurar-AAAAMMDD`. Así no se pierde lo que haya pasado entre el
   respaldo y ahora.
4. **Restaurar** desde la consola de Neon: la rama principal desde la rama de
   respaldo, o hasta el momento elegido. Neon cambia los datos en el lugar, así que
   la cadena de conexión de Vercel no cambia.
5. **Recuperar** lo que haya entrado después del respaldo, comparando con la rama
   `antes-de-restaurar`, con el referente funcional.
6. OP-04, y registro en el build log de qué se restauró, hasta cuándo y qué datos se
   recuperaron.

**Prueba de restauración:** el lineamiento pide probarla. Al menos una vez antes de
la primera publicación, QA y el responsable de la base hacen el procedimiento
completo sobre una rama **de prueba** (nunca sobre la principal) y lo anotan en la
sección 8.

### OP-07 · Rotar una credencial

**Cuándo:** una credencial se expuso o se sospecha que se expuso, o se va un
integrante que la conocía.
**Ejecuta:** el responsable de esa credencial. **Valida:** responsable de publicación.

| Credencial | Cómo se rota | Efecto |
|---|---|---|
| `SECRET_KEY` | Generar una nueva (`python3 -c "import secrets; print(secrets.token_urlsafe(50))"`), reemplazarla en Vercel y redeployar | Se cierran todas las sesiones y vencen los enlaces de recuperación de contraseña pendientes |
| Contraseña de correo | En la cuenta de Google: revocar la contraseña de aplicación y generar una nueva; cargarla en Vercel (`EMAIL_HOST_PASSWORD`) y redeployar | Los correos fallan entre la revocación y el redeploy |
| Base de datos | Consola de Neon → resetear la contraseña del rol; actualizar `DATABASE_URL` en Vercel y redeployar | La app no se conecta entre el reseteo y el redeploy |

Después de una exposición: revisar la actividad de la cuenta afectada y registrar
el incidente (OP-10).

### OP-08 · Habilitar el admin de Django por un rato

**Cuándo:** una corrección puntual de datos que no se puede hacer desde SIMEF.
**Decide:** responsable de publicación. **Ejecuta:** responsable del panel.

1. Vercel → Environment Variables → *Production* → `ADMIN_HABILITADO` = `True` →
   redeployar.
2. Hacer la corrección, y anotar qué se cambió.
3. **Quitar la variable y redeployar.** Comprobar que `/admin/` vuelve a redirigir al
   inicio.

### OP-09 · Desbloquear una cuenta o blanquear una contraseña

**Cuándo:** una persona no puede entrar al sistema.
**Ejecuta:** preceptoría o dirección, desde SIMEF. **Si hace falta la base:**
responsable de la base.

- **Contraseña olvidada:** desde SIMEF, "blanquear contraseña". El sistema genera una
  contraseña aleatoria que se muestra **una sola vez**. Se entrega a la persona en
  mano o por un canal privado, nunca en un grupo, y la persona la cambia al entrar.
- **Cuenta bloqueada por intentos fallidos:** después de 5 intentos seguidos, la cuenta
  se bloquea por 10 minutos, y cada bloqueo nuevo suma 10 minutos más, hasta 2 horas.
  Lo normal es esperar a que venza. Si no se puede esperar, el responsable de la base
  la desbloquea desde su máquina, con la cadena de producción en el `.env`:
  ```bash
  docker run --rm -v "$PWD":/app:ro -w /app -e DEBUG=True -e DATABASE_URL \
    --entrypoint python simef-web manage.py axes_reset_username <email-de-la-cuenta>
  ```
  (con `DATABASE_URL` exportada en la terminal desde el `.env`, sin escribirla en el
  comando).
- **Muchas cuentas bloqueadas a la vez:** puede ser un ataque. Tratarlo como incidente
  (OP-10) antes de desbloquear.

### OP-10 · Atender un incidente

**Cuándo:** el sistema no funciona, funciona mal, o se sospecha un acceso indebido o
una exposición de datos.
**Quien lo detecta** avisa al responsable de publicación. **Coordina:** responsable
de publicación.

| Gravedad | Ejemplos | Respuesta |
|---|---|---|
| **Alta** | El sistema no carga; no se puede iniciar sesión; datos borrados o expuestos; credencial expuesta | En el momento: OP-05 o la rotación de OP-07 primero, y después se investiga |
| **Media** | Una función clave falla (inscripción, acta, carga de notas) y no hay alternativa | En el día: corrección por PR, o reversión si la corrección tarda |
| **Baja** | Un error visual o un caso borde con alternativa | Defecto registrado; entra en un PR normal |

**Pasos:**
1. **Registrar** qué se ve, desde cuándo y a quién afecta. Copiar los errores de los
   logs de Vercel, sin cadenas de conexión ni contraseñas.
2. **Contener:** según la gravedad.
3. **Comunicar:** si afecta a estudiantes o a docentes (por ejemplo, durante una
   inscripción), el referente funcional y la dirección deciden qué se les informa.
4. **Resolver** con los procedimientos de este documento, y comprobar con OP-04.
5. **Cerrar** con una tarjeta en el tablero: qué pasó, la causa, qué se hizo y qué se
   cambia para que no se repita.

**Datos personales:** si hubo acceso indebido a datos de estudiantes, la dirección del
instituto evalúa qué corresponde hacer según la Ley 25.326 de Protección de Datos
Personales.

### OP-11 · Cargar una base de prueba con datos sintéticos

**Cuándo:** para las pruebas de QA, sobre todo las negativas y las de seguridad, que
no se hacen con datos reales de estudiantes.
**Ejecuta:** responsable de la base. **Valida:** QA.

1. En la consola de Neon, crear una rama nueva **sin datos**: la opción *Schema only*
   copia la estructura de producción sin ninguna fila. Nunca sobre `main` ni sobre
   `preview`.
2. Copiar su cadena de conexión a una variable solo para esta terminal, sin
   guardarla en el `.env` ni en el repositorio.
3. Cargar el instituto ficticio:

   ```bash
   docker run --rm -v "$PWD":/app:ro -w /app -e DEBUG=True -e DATABASE_URL \
     --entrypoint python simef-web manage.py generar_datos_sinteticos
   ```

   El comando se niega a correr si la base ya tiene usuarios. Así nunca se mezcla
   con datos reales.
4. Guardar las contraseñas que muestra al final en el gestor de contraseñas del
   equipo. No se vuelven a mostrar y no van en tarjetas ni en el chat.

**Qué trae:**
- un usuario de cada rol;
- una carrera con correlativas;
- tres llamados ya rendidos con acta y folio, una mesa abierta y otra sin habilitar;
- seis estudiantes, uno por situación:
  - recién inscripta;
  - habilitado para rendir;
  - con una oportunidad restante, donde el Ausente cuenta;
  - con las cuatro agotadas;
  - con el final aprobado y la correlativa disponible;
  - recursando.

**Cómo se verifica:** con cada cuenta de estudiante, la pantalla de finales muestra
lo que dice su caso. Por ejemplo, el estudiante con las cuatro oportunidades usadas ve
el motivo y no puede inscribirse.

**Si falla:** el comando no deja nada a medias: o carga todo o no carga nada. Se
corrige la causa y se vuelve a correr sobre la misma rama vacía.

### OP-12 · Crear o renovar el usuario de base de la app

**Cuándo:** una vez por rama, y cada vez que haya que cambiar su contraseña: por
rotación (OP-07) o porque se expuso.
**Ejecuta:** responsable de la base. **Valida:** responsable de publicación.

La app no se conecta como dueña de la base, sino con `simef_app`. Ese usuario puede
leer y escribir datos, pero no crear, modificar ni borrar tablas, así que una falla en
la app no puede cambiar la estructura de la base (SEC-05). Las migraciones siguen
corriendo con el dueño (OP-03).

```bash
./scripts/crear_rol_app.sh preview      # rama preview
./scripts/crear_rol_app.sh produccion   # base del instituto
```

El script:
1. Crea el usuario, o le pone una contraseña nueva si ya existe.
2. Le da permisos solo sobre los datos y deja esos permisos por defecto para las
   tablas de futuras migraciones.
3. Se conecta como `simef_app` y comprueba que lee pero no puede crear tablas.
4. Guarda la cadena en el `.env` como `PREVIEW_APP_DATABASE_URL` o
   `APP_DATABASE_URL`, sin mostrarla.

Después, en Vercel, se pega esa cadena en `DATABASE_URL` del entorno que corresponde
y se redeploya. En producción, el cambio se hace el día de la salida, después de
aplicar las migraciones.

**Cómo se verifica:** la app inicia sesión y guarda cambios. En los logs de Vercel no
aparece `permission denied`.

**Si falla:** volver a poner en Vercel la cadena del dueño y redeployar. Copiar el
error, sin cadenas de conexión, y revisar los permisos con el responsable de la base.

---

## 7. Límites de responsabilidad

*Sección que revisa Análisis Funcional.*

- **Lo que hace SIMEF:** habilitar las mesas, inscribir a los estudiantes con los
  controles de elegibilidad, plazo y oportunidades, mostrar la nómina, generar el acta
  volante, registrar los resultados que transcribe el preceptor (nota o Ausente,
  número de acta y folio) y conservarlos.
- **Lo que no hace SIMEF, porque es un procedimiento en papel:** que el presidente de
  la mesa complete y firme el acta, el libro de actas y la entrega del acta firmada al
  preceptor. SIMEF registra lo que el preceptor transcribe de ese documento. Si hay
  diferencias, vale el acta firmada.
- **Fuera de este MOP:** la infraestructura de Vercel y de Neon (disponibilidad del
  servicio, hardware, red) es responsabilidad de esos proveedores. Este manual cubre
  lo que el equipo opera sobre ellos.

## 8. Registro de comprobación

*QA ejecuta cada procedimiento, en la vista previa o sobre ramas de prueba cuando
corresponde, y anota el resultado. Un procedimiento no se da por válido sin una
comprobación registrada.*

| Procedimiento | Fecha | Quién | Dónde | Resultado |
|---|---|---|---|---|
| OP-02 Respaldar (y ventana de restauración de Neon) | | | | |
| OP-03 Migrar (`preview`) | 14/10/2026 | Backend | rama `preview` | Script probado: sin pendientes termina sin escribir; se niega con una cadena de producción y con una que no es de Neon. Falta la comprobación de QA. |
| OP-04 Comprobar | | | | |
| OP-05 Volver atrás | | | | |
| OP-06 Restaurar (prueba sobre una rama de prueba) | | | | |
| OP-07 Rotar | | | | |
| OP-08 Habilitar el admin | | | | |
| OP-09 Desbloquear o blanquear | | | | |
| OP-12 Usuario de la app (`preview`) | 18/10/2026 | Backend | rama `preview` | Usuario creado: lee, escribe sesiones, intentos de axes y usuarios dentro de una transacción revertida, y no puede crear tablas. Falta producción y el cambio en Vercel. |
| OP-11 Datos sintéticos | 18/10/2026 | Backend | base de tests | Comando probado con tests automáticos; se niega sobre una base con usuarios. Falta cargar la rama de Neon y la comprobación de QA. |

## 9. Historial

| Versión | Fecha | Cambios |
|---|---|---|
| 0.1 | 14/10/2026 | Primera versión: destino, configuración, controles y procedimientos OP-01 a OP-10. Faltan los responsables y la comprobación de QA. |
| 0.2 | 18/10/2026 | OP-11: base de prueba con datos sintéticos. |
| 0.3 | 18/10/2026 | OP-12: usuario de base acotado para la app. |
