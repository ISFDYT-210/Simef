# Política de seguridad

SIMEF guarda datos personales de estudiantes y docentes del ISFDyT N.º 210, protegidos
por la Ley 25.326 de Protección de Datos Personales. Si encontrás una vulnerabilidad,
avisanos en privado: así se corrige antes de que alguien pueda aprovecharla.

## Versiones con soporte

| Versión | Con soporte |
|---|---|
| 1.0.x (la que está en producción, rama `main`) | ✅ |
| `develop` (próxima versión) | ✅ |
| Anteriores a 1.0.0 | ❌ |

Las correcciones de seguridad se publican en una versión nueva (por ejemplo, `v1.0.1`).
La lista está en [Releases](https://github.com/ISFDYT-210/Simef/releases).

## Cómo reportar una vulnerabilidad

**No abras un issue, un pull request ni una discusión pública.** Usá el reporte privado
de GitHub:

1. Entrá a la pestaña **Security** del repositorio.
2. Elegí **Report a vulnerability**, o entrá directo a
   <https://github.com/ISFDYT-210/Simef/security/advisories/new>.
3. Completá el formulario. Solo lo ven quienes mantienen el repositorio.

Si no tenés cuenta de GitHub, avisale en persona a Preceptoría o a Secretaría del
instituto, que se lo hacen llegar al equipo. No mandes el detalle por correo ni por
redes sociales.

Para que podamos reproducirlo, incluí:

- qué parte del sistema está afectada (página, ruta, archivo o versión);
- los pasos para reproducirlo, con el rol de la cuenta que usaste (estudiante,
  preceptor, etc.);
- qué se puede lograr con la falla: ver datos de otra persona, cambiar notas,
  entrar sin sesión, etc.;
- si la encontraste en producción, en una copia local o leyendo el código.

**No incluyas datos personales reales** (nombres, DNI, notas) en el reporte. Si para
mostrar la falla hace falta un ejemplo, describí el dato sin copiarlo.

## Qué podés esperar

- **Acuse de recibo:** dentro de los 5 días hábiles.
- **Evaluación inicial:** dentro de los 10 días hábiles, con la gravedad que le
  asignamos y si la confirmamos.
- **Corrección:** según la gravedad. Lo que expone datos personales o permite cambiar
  notas tiene prioridad sobre todo lo demás.
- **Seguimiento:** te avisamos en el mismo reporte cuando la corrección esté en
  producción.

Cuando la corrección está publicada, el reporte se puede publicar como aviso de
seguridad de GitHub (*security advisory*), con tu nombre si querés aparecer.

## Alcance

**Entra:**

- el código de este repositorio;
- el sitio en producción, <https://www.pulqui-simef210.com.ar>;
- la configuración de CI/CD del repositorio (`.github/`);
- los diagramas publicados en <https://isfdyt-210.github.io/Simef/>.

**No entra** (reportalo al proveedor correspondiente):

- fallas propias de Vercel, Neon, GitHub o Gmail;
- engaños a personas (*phishing*, ingeniería social) o acceso físico a equipos del
  instituto;
- ataques de denegación de servicio y pruebas de carga;
- falta de encabezados o configuraciones que no permiten un ataque concreto.

## Cómo probar sin causar daño

Estas reglas existen para proteger los datos de estudiantes y docentes:

- Usá solo tu propia cuenta. No entres con cuentas de otras personas, aunque tengas la
  contraseña.
- Si llegás a ver datos de otra persona, **frená ahí**: no los copies, no los guardes y
  no sigas explorando. Avisanos y contanos qué viste.
- No modifiques ni borres datos de otras personas. En particular, no cambies
  inscripciones, notas ni actas.
- No uses escáneres automáticos ni herramientas que manden muchas peticiones contra
  producción: el sistema se usa en período de inscripciones.
- Siempre que puedas, probá en una copia local (ver «Levantarlo en tu máquina» en el
  [README](README.md)), con los datos de prueba de
  `python manage.py generar_datos_sinteticos`.
- No hagas pública la vulnerabilidad hasta que esté corregida y lo hayamos acordado.

## Qué ya está en marcha

- Escaneo de secretos y protección contra pushes que incluyan credenciales.
- `pip-audit` obligatorio en el CI: no entra a `main` una dependencia con
  vulnerabilidades conocidas.
- Dependabot revisa cada semana las dependencias de Python, las GitHub Actions y la
  imagen de Docker.
- `main` y `develop` solo cambian por pull request, con controles obligatorios.
- La aplicación se conecta a la base con un usuario que no puede cambiar su estructura.
