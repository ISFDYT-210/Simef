<div align="center">

<img src="inscripcionFinales/static/imagenes/SIMEF.png" alt="SIMEF" width="140">

# SIMEF

**Sistema de inscripción a mesas de examen final del ISFDyT N.º 210**

Inscripciones a cursadas y finales, actas, notas y constancias, con las reglas
académicas del instituto aplicadas en el servidor.

[![CI](https://github.com/ISFDYT-210/Simef/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/ISFDYT-210/Simef/actions/workflows/ci.yml)
![Django 5.2 LTS](https://img.shields.io/badge/Django-5.2_LTS-0C4B33?logo=django&logoColor=white)
![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql&logoColor=white)
![Vercel](https://img.shields.io/badge/deploy-Vercel-000000?logo=vercel&logoColor=white)

[Qué hace](#qué-hace) · [Cómo funciona](#cómo-funciona) · [Levantarlo](#levantarlo-en-tu-máquina) · [Documentación](#documentación) · [Contribuir](#cómo-contribuir) · [Seguridad](#seguridad-y-datos-personales)

</div>

---

## Qué hace

SIMEF reemplaza las planillas y las inscripciones en papel del instituto. Cada rol
ve solo lo que le corresponde:

| Rol | Puede |
|---|---|
| **Estudiante** | Inscribirse a cursadas y a mesas de final. Ver por qué no puede rendir una materia: correlativas, nota de cursada, oportunidades agotadas o mesa cerrada. Descargar su constancia académica en PDF. |
| **Preceptor** | Crear y habilitar mesas, con tribunal, aula y sede. Consultar la nómina de inscriptos, generar el acta volante y transcribir los resultados del acta: nota o Ausente, número de acta y folio. |
| **Profesor** | Cargar las notas de sus materias y ver los reportes de sus alumnos. |
| **Secretario** y **Directivo** | Administrar usuarios (alta individual o carga masiva), carreras y materias, abrir y cerrar inscripciones, y ver reportes. Dirección consulta además el registro de auditoría. |

**Reglas que el sistema hace cumplir, no solo muestra:**
- correlativas y nota mínima de cursada;
- plazo de inscripción de cada mesa;
- una sola inscripción por mesa, sin cancelación por parte del estudiante;
- un **máximo de cuatro oportunidades** por materia, en las que Ausente cuenta como una;
- promoción sin final con nota de cursada 7 o más;
- superposición de horarios al cursar.

## En números

Cifras medidas sobre `develop`, no objetivos:

| | |
|---|---|
| Tests automatizados | **249**, con PostgreSQL en cada PR |
| Dependencias con vulnerabilidades conocidas | **0** (`pip-audit` frena el PR si aparece una) |
| Avisos de `manage.py check --deploy` | **0** con `DEBUG=False` |
| Controles obligatorios para llegar a `main` | **4**: lint, tests, checklist de despliegue y build de Docker (`develop` suma `pip-audit`) |
| Dependencia de servicios externos para los PDF | **ninguna**: la constancia y el listado de mesas se generan dentro del sistema |

## Cómo funciona

El circuito de un final, de punta a punta:

<p align="center">
  <img src="docs/img/circuito-de-un-final.gif" width="880" alt="Animación del circuito de un final, en siete pasos: el preceptor crea y habilita la mesa; el estudiante se inscribe, y SIMEF valida correlativas, plazo y oportunidades; el preceptor consulta la nómina de la mesa; se genera el acta volante; el presidente de mesa firma el acta en papel, fuera de SIMEF; el preceptor transcribe los resultados; y SIMEF conserva el resultado y actualiza las oportunidades.">
</p>

La firma del acta y el libro de actas son procedimientos en papel, fuera de SIMEF.
El sistema registra lo que el preceptor transcribe del acta firmada.

**Arquitectura:**

<p align="center">
  <img src="docs/img/arquitectura.gif" width="880" alt="Animación de la arquitectura: el navegador se conecta por HTTPS a Vercel, que corre Django 5.2 con WhiteNoise y usa la base PostgreSQL de Neon. Una versión nueva pasa por los controles obligatorios de GitHub Actions (lint, tests, checklist de despliegue, pip-audit y build de Docker), entra a la rama main protegida de GitHub y cada merge a main se publica en Vercel.">
</p>

| Pieza | Para qué |
|---|---|
| Django 5.2 LTS | Aplicación, reglas académicas y permisos por rol |
| PostgreSQL en Neon | Base de datos. Producción y vistas previas usan ramas separadas |
| Vercel | Publica `main` en producción y arma una vista previa de cada PR |
| WhiteNoise | Sirve los estáticos con nombres con hash y compresión |
| reportlab | Genera la constancia y los listados en PDF |
| django-axes | Límite de intentos de inicio de sesión, con bloqueo progresivo |
| Tailwind CSS + Alpine.js | Interfaz |

## Levantarlo en tu máquina

Con Docker no hace falta instalar Python ni PostgreSQL:

```bash
git clone https://github.com/ISFDYT-210/Simef.git
cd Simef
cat .env.example > .env          # trae DEBUG=True para desarrollo; ver docs/ENV.md
docker compose up -d --build
```

La app queda en **http://localhost:8000**. El entorno local usa su propia base, así
que la del instituto no se toca. Para probar con una copia de los datos reales,
seguí [docs/COPIA_DATOS.md](docs/COPIA_DATOS.md).

Sin Docker (Linux o Windows, con `venv`): [docs/INSTALACION_MANUAL.md](docs/INSTALACION_MANUAL.md).

**Correr los tests:**

```bash
docker compose exec web python manage.py test --settings=gestionInstituto.settings_TEST
```

## Documentación

| Para | Documento |
|---|---|
| Levantar el proyecto con Docker | [docs/DOCKER.md](docs/DOCKER.md) |
| Instalarlo sin Docker (Linux y Windows) | [docs/INSTALACION_MANUAL.md](docs/INSTALACION_MANUAL.md) |
| Entender cada variable del `.env` | [docs/ENV.md](docs/ENV.md) |
| Copiar los datos de producción a tu base local | [docs/COPIA_DATOS.md](docs/COPIA_DATOS.md) |
| Cómo entra un cambio: ramas y Pull Requests | [docs/GITFLOW.md](docs/GITFLOW.md) |
| Cargar tarjetas de trabajo al tablero | [docs/TARJETAS_GH.md](docs/TARJETAS_GH.md) |
| Operar producción: publicar, migrar, respaldar, volver atrás | [docs/MOP.md](docs/MOP.md) |
| Cómo funciona producción en Vercel | [docs/PRODUCCION_VERCEL.md](docs/PRODUCCION_VERCEL.md) |
| Alternativa: un servidor Debian propio | [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md) |
| Compilar el CSS de Tailwind | [docs/tailwind.md](docs/tailwind.md) |
| Historial de cambios de los sprints anteriores | [docs/INFORME_MODIFICACIONES.md](docs/INFORME_MODIFICACIONES.md) |

## Cómo contribuir

1. Tomá una tarjeta del [tablero](https://github.com/orgs/ISFDYT-210/projects/1), o creá
   una con el prefijo del sprint (por ejemplo `SP3-BACK: …`).
2. Creá una rama desde `develop` (`feature/…`, `fix/…`, `docs/…`).
3. Abrí un Pull Request hacia `develop`. El CI tiene que quedar en verde, y la
   vista previa de Vercel del PR sirve para probarlo funcionando.
4. A `main`, que es producción, solo se llega con un PR desde `develop` y con todos
   los controles en verde.

Detalle completo en [docs/GITFLOW.md](docs/GITFLOW.md).

## Seguridad y datos personales

SIMEF guarda datos personales de estudiantes, protegidos por la Ley 25.326 de
Protección de Datos Personales. Por eso:

- **No se suben credenciales al repositorio.** El `.env` está ignorado, y el repo
  tiene activados el escaneo de secretos y la protección contra pushes que los
  incluyan.
- **No se usan datos reales fuera de producción,** salvo en la copia local de
  desarrollo, que no se comparte.
- **Si encontrás una vulnerabilidad, no abras un issue público:** avisale en privado
  a un integrante del equipo, para que se corrija antes de que se conozca.

---

<div align="center">

Proyecto de **Prácticas Profesionalizantes** de la Tecnicatura Superior en Análisis
de Sistemas · ISFDyT N.º 210 · 2026

[Contribuidores](https://github.com/ISFDYT-210/Simef/graphs/contributors)

</div>
