@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo   GENERANDO MiTienda.exe PARA WINDOWS
echo ============================================
python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python no esta instalado o no esta en PATH.
  echo Instala Python 3.11 o superior y vuelve a ejecutar.
  pause
  exit /b 1
)
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :error
python -m PyInstaller --noconfirm --clean --onefile --windowed --name MiTienda main.py
if errorlevel 1 goto :error
echo.
echo LISTO: dist\MiTienda.exe
pause
exit /b 0
:error
echo.
echo Ocurrio un error durante la compilacion.
pause
exit /b 1
