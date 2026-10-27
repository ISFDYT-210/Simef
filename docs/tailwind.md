# Kit de build de Tailwind — SIMEF

Genera `inscripcionFinales/static/css/simef.css` a partir de las plantillas.
No usa CDN (la red del instituto lo bloquea): el CSS se compila localmente.

## Archivos

- `tailwind.config.js` — paleta (tinta/celeste), fuente y **dónde** buscar clases.
- `input.css` — entrada: directivas de Tailwind + ajustes base (x-cloak, fuente).
- `tailwindcss` — binario del CLI (se descarga, ver abajo; **no** se versiona).

## 1. Descargar el CLI (una sola vez, por máquina)

No requiere Node. **Usá la versión v3.4.17** (fija, no `latest`): la última es
Tailwind v4, que cambió el formato de configuración y NO funciona con este
`tailwind.config.js` ni con las directivas `@tailwind` de `input.css`.

Linux 64 bits (server Debian):

```bash
curl -L -o tailwindcss \
  https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-linux-x64
chmod +x tailwindcss
```

Windows (máquina de desarrollo, en Git Bash):

```bash
curl -L -o tailwindcss.exe \
  https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-windows-x64.exe
```

> Para ARM (ej. Raspberry) usá `...-linux-arm64`. Verificá que el archivo pese
> ~40 MB (`ls -lh tailwindcss*`); si pesa unos KB, la descarga falló.

Agregá el binario al `.gitignore` (es grande y depende del sistema operativo):

```
# .gitignore
tailwindcss
tailwindcss.exe
```

> En Windows, en los comandos de abajo usá `./tailwindcss.exe` en lugar de
> `./tailwindcss`.

## 2. Compilar el CSS (producción)

```bash
./tailwindcss -c tailwind.config.js -i input.css \
  -o inscripcionFinales/static/css/simef.css --minify
```

Después, en el server: `python manage.py collectstatic --noinput`.

## 3. Modo desarrollo (recompila solo al guardar)

```bash
./tailwindcss -c tailwind.config.js -i input.css \
  -o inscripcionFinales/static/css/simef.css --watch
```

## ¿Cuándo hay que recompilar?

Cada vez que **agregás o cambiás clases de Tailwind** en una plantilla. Tailwind
solo incluye en el CSS las clases que "ve" en los archivos de `content`. Si una
pantalla se ve sin estilos, casi siempre es que faltó recompilar (o correr
`collectstatic`).

## Nota sobre la fuente

`input.css` referencia `Archivo-Variable.woff2` en
`inscripcionFinales/static/fonts/`. Si no colocás ese archivo, no pasa nada:
el sistema usa `system-ui` como fallback (ya está previsto en la config).
