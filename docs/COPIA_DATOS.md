# Copiar los datos de Neon a tu base local

La base de datos real de SIMEF vive en Neon y es **una sola para todo el
instituto**. Este documento explica cómo trabajar con una copia local de esos
datos, para que probar no signifique tocar el sistema que usan las personas.

El script es [`scripts/copiar_neon_a_local.sh`](../scripts/copiar_neon_a_local.sh).

---

## 1. Por qué existe

Los contenedores de desarrollo apuntan a la Postgres que levanta el propio
`docker-compose` (ver [DOCKER.md](DOCKER.md)), no a Neon. Eso es a propósito: el
`entrypoint.sh` corre `migrate` en **cada arranque** del contenedor, así que si
apuntara a Neon, cada `docker compose up` le aplicaría a la base del instituto
las migraciones de la rama en la que estuvieras parado.

El efecto secundario es que esa base local arranca **vacía**, y con una base
vacía no se puede probar casi nada: no hay alumnos, ni materias, ni mesas. Este
script la llena con una copia de los datos reales.

---

## 2. Qué necesitás

Si recién clonaste el repositorio, cuatro cosas:

1. **El `.env` creado y completo.** El script toma de ahí `DATABASE_URL` como
   origen y `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` como destino.
   Si falta alguna, te la nombra en vez de fallar con un error críptico.

   > **El `.env.example` no alcanza.** Su `DATABASE_URL` apunta a la base local,
   > no a Neon. La cadena de conexión real te la tiene que pasar alguien del
   > equipo por un canal privado: no está en el repositorio y no debe estarlo.

2. **El contenedor de la base levantado.**

   ```bash
   docker compose up -d db
   ```

3. **`python3`.** Nada más: el script lee el `.env` con la biblioteca estándar,
   así que **no hace falta el entorno virtual armado ni `pip install`**.

4. **Salida de red al puerto 5432 de Neon.** Si tu red lo bloquea, el script
   aborta en 15 segundos y te lo explica, en lugar de quedarse colgado
   indefinidamente (ver [sección 6](#6-problemas-comunes)).

Fijate que **no** necesitás `postgresql-client` instalado: `pg_dump` corre dentro
del contenedor de la base, que ya lo trae.

---

## 3. Cómo se usa

### Bajar los datos y cargarlos

```bash
./scripts/copiar_neon_a_local.sh
```

Tarda unos 20 segundos. Al terminar te muestra qué quedó:

```
==> Destino verificado: socket-local (dentro del contenedor)
==> Bajando dump de ep-xxxx.sa-east-1.aws.neon.tech (solo lectura)
    backups/neon-2026-10-07-0149.sql  (160K)
==> Recreando la base local 'simef'
==> Restaurando
==> Listo. Contenido de la copia local:
    usuarios:  138
    materias:  307
    mesas:     6
    migracion: 0015_alter_usuario_telefono_1_alter_usuario_telefono_2
```

Después, para que la app tome la base recargada:

```bash
docker compose restart web
```

### Volver a cargar un dump que ya tenés

```bash
./scripts/copiar_neon_a_local.sh backups/neon-2026-10-07-0149.sql
```

Esta es la forma que vas a usar más seguido. **No toca la red ni Neon**: recarga
la base local desde el archivo en segundos. Sirve para volver al estado inicial
después de una prueba que ensució los datos, y funciona aunque no tengas
conexión.

---

## 4. Qué hace, paso a paso

Conviene saberlo, porque el script **borra** una base de datos.

1. **Lee las credenciales del `.env`.** Lo hace con Python y no con `grep` por un
   motivo concreto: la contraseña puede traer caracteres que rompen tanto el
   parseo a mano como el analizador de URI de `psql`. Pasándole la URL completa,
   `psql` no da un error: se queda esperando que le escribas la contraseña por
   teclado, que en un script es un cuelgue infinito.

2. **Verifica el destino.** Antes de borrar nada, le pregunta al servidor de
   destino dónde está (`inet_server_addr()`) y aborta si la dirección no es un
   socket local ni una IP privada. Es el seguro contra el peor accidente posible:
   restaurar sobre la base de producción.

3. **Baja el dump**, con `pg_dump` corriendo dentro del contenedor de la base.
   Va con `--no-owner --no-privileges` porque en Neon el dueño de los objetos es
   `neondb_owner` y en local es otro usuario; sin eso, la restauración falla con
   errores de rol inexistente.

4. **Recrea la base local.** Primero cierra las conexiones abiertas con
   `pg_terminate_backend` —la app mantiene varias, y `DROP DATABASE` falla si hay
   alguna— y después la borra y la vuelve a crear vacía.

5. **Restaura y cuenta.** Te muestra cuántos usuarios, materias y mesas quedaron,
   y hasta qué migración llega la copia. Ese último dato es útil para notar si la
   copia trae un esquema distinto al de tu rama.

---

## 5. Qué es seguro y qué no

**A Neon lo lee y nada más.** `pg_dump` no escribe. No hay ninguna instrucción en
el script que modifique el origen.

**Lo que borra y recrea es tu base local**, y sólo después de verificar que el
destino es local. Si la verificación no puede determinarlo, aborta en vez de
seguir adelante.

**El dump tiene datos personales de alumnos.** Queda en `backups/`, que está en
el `.gitignore` justamente por eso.

> **No lo commitees, no lo mandes por chat y no lo dejes en una carpeta
> sincronizada.** Son nombres, DNI, correos y notas de personas reales. Si no lo
> necesitás más, borralo.

---

## 6. Problemas comunes

**`ERROR: no hay salida al puerto 5432 de ...neon.tech`**

Tu red no llega a Neon. Pasa en algunos Codespaces y en redes con egreso
restringido; el síntoma típico es que el host resuelve y responde en el puerto
443, pero el 5432 queda sin respuesta. No es un problema de Neon ni del script.

Dos salidas: correr el script desde una máquina con salida al 5432, o conseguir
el dump por otro medio —la consola de Neon permite exportarlo— y pasarlo como
argumento.

**`ERROR: el contenedor 'db' no esta corriendo`**

```bash
docker compose up -d db
```

**`ERROR: faltan variables en .env: ...`**

Te dice cuáles. Revisá el paso 2 de [DOCKER.md](DOCKER.md) y, si te falta la
cadena de Neon, pedila al equipo.

**`ERROR: el destino (...) no es local`**

El seguro del paso 2 se activó. No lo desactives: significa que el script estaba
por borrar una base que no es la tuya.

---

## 7. Cada cuánto conviene actualizar la copia

No hay regla fija, pero sirven dos criterios:

- **Cuando necesites datos recientes** para reproducir algo que pasa en
  producción.
- **Cuando tu rama agregue migraciones.** Conviene bajar una copia fresca y
  correr `migrate` contra ella: es la forma más parecida a lo que va a pasar en
  producción, sin riesgo. El resumen del paso 5 te dice hasta qué migración llega
  la copia.

Para el trabajo del día a día no hace falta: con el dump que ya tenés en
`backups/` podés recargar la base cuantas veces quieras.
