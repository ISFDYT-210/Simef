@echo off
:: ══════════════════════════════════════════════════════════════
:: SIMEF - Arranque sin runserver (Windows)
:: Usa Waitress como servidor WSGI (reemplazo de Gunicorn para Windows).
::
:: Uso:  doble click en este archivo, o desde la terminal:
::       iniciar_simef.bat
::
:: Primera vez:  pip install waitress
:: ══════════════════════════════════════════════════════════════

:: Ir a la carpeta del proyecto (ajustá esta ruta si lo movés)
cd /d "%~dp0"

echo.
echo  ╔═══════════════════════════════════════════════╗
echo  ║   SIMEF - ISFDyT N°210 - La Plata            ║
echo  ║   Servidor arrancando en http://127.0.0.1:8000║
echo  ╚═══════════════════════════════════════════════╝
echo.

:: Collectstatic (junta los archivos estáticos, solo si hace falta)
python manage.py collectstatic --noinput 2>nul

:: Arrancar Waitress en el puerto 8000
echo [%date% %time%] Levantando SIMEF con Waitress...
echo Abrí http://127.0.0.1:8000 en el navegador.
echo Para detenerlo, cerrá esta ventana o presioná Ctrl+C.
echo.

python -m waitress --host=127.0.0.1 --port=8000 gestionInstituto.wsgi:application

pause
