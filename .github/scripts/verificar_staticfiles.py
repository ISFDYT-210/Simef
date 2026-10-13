"""
Verifica que la carpeta staticfiles/ commiteada coincida con lo que genera
collectstatic.

En Vercel no corre collectstatic (vercel.json usa `builds`, que ignora el Build
Command), así que producción sirve staticfiles/ tal como está en el repo. Si alguien
agrega o cambia un estático y no la regenera, la página que lo pide da 500 con
DEBUG apagado (el manifiesto de WhiteNoise es estricto). Este script corre
collectstatic en una carpeta temporal y compara archivo por archivo. El manifiesto
staticfiles.json se compara como JSON, no como texto, por si otra máquina lista los
archivos en otro orden.

Uso (desde la raíz del repo, con el entorno de Django disponible):
    python .github/scripts/verificar_staticfiles.py

Sale con 1 y lista las diferencias si staticfiles/ está desactualizada.
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
COMMITEADA = RAIZ / 'staticfiles'
MANIFIESTO = 'staticfiles.json'


def archivos(carpeta):
    return {str(p.relative_to(carpeta)) for p in carpeta.rglob('*') if p.is_file()}


# Carpetas que no son código de SIMEF: lo generado, dependencias y herramientas locales.
IGNORAR = {'staticfiles', 'node_modules', 'venv', 'env', 'security-audit', 'graft', 'backups'}
RUTA_ESCRITA = re.compile(r'/static/([A-Za-z0-9_./-]+\.(?:png|jpe?g|svg|gif|ico|css|js|webp|woff2?))')


def rutas_escritas_a_mano():
    """Rutas '/static/...' escritas a mano (sin {% static %}) en plantillas, JS y CSS."""
    rutas = {}
    for archivo in sorted(RAIZ.rglob('*')):
        relativo = archivo.relative_to(RAIZ)
        if archivo.suffix not in ('.html', '.js', '.css') or not archivo.is_file():
            continue
        if relativo.parts[0] in IGNORAR or any(p.startswith('.') for p in relativo.parts):
            continue
        for ruta in RUTA_ESCRITA.findall(archivo.read_text(errors='ignore')):
            rutas.setdefault(ruta, str(relativo))
    return rutas


def generar(destino):
    sys.path.insert(0, str(RAIZ))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestionInstituto.settings')
    import django
    from django.conf import settings
    django.setup()
    settings.STATIC_ROOT = str(destino)
    from django.core.management import call_command
    call_command('collectstatic', interactive=False, clear=True, verbosity=0)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        generada = Path(tmp)
        generar(generada)
        esperados, presentes = archivos(generada), archivos(COMMITEADA)
        faltan = sorted(esperados - presentes)
        sobran = sorted(presentes - esperados)
        distintos = []
        for nombre in sorted(esperados & presentes):
            a, b = generada / nombre, COMMITEADA / nombre
            if nombre == MANIFIESTO:
                iguales = json.loads(a.read_text()) == json.loads(b.read_text())
            else:
                iguales = a.read_bytes() == b.read_bytes()
            if not iguales:
                distintos.append(nombre)

    # Una ruta escrita a mano no pasa por el manifiesto: si el archivo no existe,
    # la imagen sale rota sin ningún error.
    rotas = {r: origen for r, origen in rutas_escritas_a_mano().items() if r not in esperados}

    if not (faltan or sobran or distintos or rotas):
        print(f'staticfiles/ está al día ({len(esperados)} archivos).')
        return 0

    if rotas:
        print('Rutas /static/ escritas a mano que no existen:')
        for ruta, origen in sorted(rotas.items()):
            print(f'  /static/{ruta}  (en {origen})')
        if not (faltan or sobran or distintos):
            return 1

    print('staticfiles/ no coincide con lo que genera collectstatic.')
    for titulo, lista in (('Faltan', faltan), ('Sobran', sobran), ('Distintos', distintos)):
        if lista:
            print(f'\n{titulo} ({len(lista)}):')
            for nombre in lista[:30]:
                print(f'  {nombre}')
            if len(lista) > 30:
                print(f'  … y {len(lista) - 30} más')
    print('\nPara arreglarlo: python manage.py collectstatic --noinput --clear '
          'y commitear staticfiles/.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
