# Carga masiva de usuarios (CSV)

**Usuarios → Carga masiva.** La usan Directivo y Secretario. Crea usuarios desde un archivo
CSV y, en la misma carga, inscribe estudiantes con sus notas o asigna a cada docente las
materias que dicta (#285).

## El archivo

- CSV separado por comas o por punto y coma (Excel en castellano guarda con punto y coma).
  Máximo 5 MB.
- Los encabezados se reconocen sin importar acentos ni mayúsculas.
- Obligatorias: una columna con el nombre y otra con el DNI. Las demás son opcionales.

| Columna | También se acepta | Qué es |
|---|---|---|
| Nombre estudiante | Nombre, Nombre y Apellido, Apellido y nombre | Nombre completo. Si nombre y apellido vienen en dos columnas (Nombre, Apellido), se juntan. |
| Documento estudiante | DNI, Documento | Solo números; se aceptan puntos y espacios. Es el usuario para entrar y no se cambia después. |
| Correo electrónico | mail, email, correo | Si viene, tiene que ser único. |
| Rol | | Estudiante, Profesor, Preceptor, Secretario o Directivo. Si no viene, se usa el rol elegido al subir el archivo. |
| Carrera | | Tiene que existir en el sistema. |
| Año | | Año de la materia (1 a 4). Se aceptan "2", "2°" o "2º año". |
| Materia | | Para un estudiante, la materia en que se lo inscribe. Para un docente, la materia que dicta. |
| Modalidad, Nota de cursada, Nota de final | | Solo para estudiantes, con la columna Materia. |

También se aceptan Username, Fecha nacimiento, Dirección, Localidad, Ciudad, Nacionalidad,
Teléfono 1, Teléfono 2, Estado civil, Sexo, Matrícula, Especialidad, Cargo y Área.

## El rol de las filas sin columna Rol

Al subir el archivo se elige con qué rol se crean las filas que no traen Rol. **Por defecto
es Estudiante.** Para la planilla de docentes, elegir **Profesor/a**.

## Estudiantes

Con Materia, se inscribe al estudiante en esa materia y se le cargan la modalidad y las
notas de la fila. Si el estudiante ya existe, no se duplica: se le carga lo que trae la fila.

## Docentes

Se puede subir la planilla de la planta docente tal como la tiene la institución:

```
Nombre y Apellido;DNI;mail;Carrera;Año;Materia
Ana Pérez;20.111.222;ana@ejemplo.com;Profesorado de Matemática;1;Álgebra I
;;;Profesorado de Matemática;2;Geometría
Beto Gómez;20333444;beto@ejemplo.com;Profesorado de Matemática;1;Análisis I
```

- **Una fila por materia.** En las filas siguientes del mismo docente, el nombre (y el DNI y
  el mail) pueden quedar vacíos: son del docente de la fila anterior.
- **Materia es la materia que dicta:** se lo asigna como profesor de esa materia. Un docente
  nunca queda inscripto como estudiante.
- **Las materias tienen que existir.** Se buscan por nombre, en la carrera y el año de la
  fila, sin importar acentos ni mayúsculas. Si hay más de una con ese nombre, hace falta la
  Carrera y el Año para saber cuál es.
- **Si una materia ya tiene otro profesor, no se cambia.** Se avisa, y se cambia a mano desde
  la materia si corresponde. Una que tenía un profesor dado de baja sí se reasigna.
- **Si la carrera no existe**, el docente se crea igual y se avisa.
- Cada materia asignada queda en la auditoría.

Al terminar, la pantalla muestra:
- cada docente con las materias que dicta;
- los docentes que quedaron sin materias;
- las materias y las carreras que no se encontraron;
- las materias que ya tenían otro profesor.

Corregido el archivo (o creadas las materias que faltaban), **se puede volver a cargar**: los
docentes que ya existen no se recrean y las materias que ya dictan no se vuelven a asignar.

## Usuarios que ya existen

Si el DNI o el email ya están cargados, no se crea otro usuario:
- a un estudiante se le cargan la materia, las notas y la carrera de la fila;
- a un docente se le asignan las materias de la fila;
- si la fila no coincide con el rol que ya tiene, por ejemplo una fila de Profesor para alguien
  que es Estudiante, no se cambia nada y se avisa.

## Texto para el Manual de Usuario (punto 4.b)

> **4.b. Carga Masiva vía CSV**
>
> 1. Acceda a **Usuarios → Carga masiva**.
> 2. Prepare un archivo .csv (separado por comas o por punto y coma, máximo 5 MB) con al menos
>    una columna con el nombre (*Nombre*, *Nombre y Apellido* o *Nombre estudiante*) y otra con
>    el DNI (*DNI*, *Documento* o *Documento estudiante*).
> 3. Elija el rol para las filas que no traen la columna *Rol*. Por defecto es **Estudiante**.
> 4. **Estudiantes:** si el archivo trae *Carrera*, *Materia*, *Modalidad* y notas, el sistema
>    registra al alumno, lo inscribe y carga la nota en una sola acción.
> 5. **Docentes:** suba la planilla de la planta docente (*Nombre y Apellido, DNI, mail,
>    Carrera, Año, Materia*), con una fila por materia, eligiendo **Profesor/a** en el paso 3.
>    En las filas siguientes del mismo docente el nombre puede quedar vacío. Cada docente queda
>    asignado como profesor de las materias que dicta; nunca se lo inscribe como estudiante.
>    Las materias tienen que estar creadas antes.
> 6. Presione **Cargar usuarios**. El informe final muestra los usuarios creados, las
>    contraseñas generadas (se ven una sola vez) y, para los docentes, las materias asignadas,
>    los docentes sin materias y las materias o carreras que no se encontraron.
