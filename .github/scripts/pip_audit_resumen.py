"""
Arma el resumen del job de pip-audit del CI a partir de su salida JSON.

Escribe en stdout una tabla en Markdown (va al resumen del job) y en stderr una
línea con el total (va al aviso del PR). El código de salida separa los casos
que el workflow tiene que tratar distinto:

    0  pip-audit corrió y no encontró vulnerabilidades
    1  pip-audit corrió y encontró vulnerabilidades
    2  no hay un JSON válido: pip-audit no llegó a correr, y eso es un error

Uso: python .github/scripts/pip_audit_resumen.py pip-audit.json
"""
import json
import sys


def main(ruta):
    try:
        with open(ruta, encoding='utf-8') as archivo:
            datos = json.load(archivo)
        dependencias = datos['dependencies']
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'No se pudo leer la salida de pip-audit ({ruta}): {error}', file=sys.stderr)
        return 2

    vulnerables = [d for d in dependencias if d.get('vulns')]
    print('## Dependencias vulnerables (pip-audit)\n')
    if not vulnerables:
        print(f'Sin vulnerabilidades conocidas en las {len(dependencias)} dependencias revisadas.')
        print('Sin vulnerabilidades conocidas.', file=sys.stderr)
        return 0

    total = sum(len(d['vulns']) for d in vulnerables)
    print('| Paquete | Versión | Vulnerabilidades | Versión mínima que corrige todas |')
    print('|---|---|---|---|')
    for dep in sorted(vulnerables, key=lambda d: -len(d['vulns'])):
        destino = _version_minima_que_corrige_todas(dep['vulns']) or 'no hay una que corrija todas'
        print(f"| {dep['name']} | {dep['version']} | {len(dep['vulns'])} | {destino} |")
    print(f'\n**Total: {total} vulnerabilidades en {len(vulnerables)} paquetes.**')
    print(f'{total} vulnerabilidades conocidas en {len(vulnerables)} paquetes '
          f"({', '.join(d['name'] for d in vulnerables)}).", file=sys.stderr)
    return 1


def _version_minima_que_corrige_todas(vulns):
    """
    Cada vulnerabilidad trae las versiones que la corrigen, a veces una por rama
    (por ejemplo 4.2.25 y 5.2.7). Una versión V la corrige si es posterior a un
    arreglo de su misma rama, o a todos los arreglos publicados. Devuelve la
    menor V, entre esos arreglos, que corrige todas.
    """
    def corrige(version, arreglos):
        v = _clave_version(version)
        if v >= max(_clave_version(a) for a in arreglos):
            return True
        return any(_clave_version(a)[:2] == v[:2] and v >= _clave_version(a) for a in arreglos)

    listas = [vuln.get('fix_versions') or [] for vuln in vulns]
    if any(not arreglos for arreglos in listas):
        return None  # hay al menos una sin arreglo publicado
    candidatas = sorted({a for arreglos in listas for a in arreglos}, key=_clave_version)
    for candidata in candidatas:
        if all(corrige(candidata, arreglos) for arreglos in listas):
            return candidata
    return None


def _clave_version(version):
    partes = []
    for parte in version.split('.'):
        numero = ''.join(c for c in parte if c.isdigit())
        partes.append(int(numero) if numero else 0)
    return partes


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'pip-audit.json'))
