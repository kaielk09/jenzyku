@echo off
setlocal
cd /d "%~dp0"
title 321code - Budowanie instalatora Windows

echo ==========================================
echo        321code - BUILD WINDOWS
echo ==========================================
echo.
where py >nul 2>nul
if errorlevel 1 (
    echo BLAD: Do budowania potrzebny jest Python 3.10+ oraz launcher "py".
    echo Python jest potrzebny tylko na komputerze budujacym instalator.
    echo Uzytkownik koncowy nie musi instalowac Pythona.
    pause
    exit /b 1
)

if not exist ".build-venv\Scripts\python.exe" (
    py -3 -m venv .build-venv
    if errorlevel 1 goto :error
)

call ".build-venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install pyinstaller
if errorlevel 1 goto :error

echo.
echo [1/2] Budowanie samodzielnego 321.exe...
pyinstaller --noconfirm --clean --onefile --console --name 321 --paths . --collect-submodules code321 installer\cli_entry.py
if errorlevel 1 goto :error

echo.
echo [2/2] Budowanie instalatora 321code-Setup.exe...
pyinstaller --noconfirm --clean --onefile --windowed --name 321code-Setup --add-binary "dist\321.exe;." installer\setup.py
if errorlevel 1 goto :error

echo.
echo GOTOWE!
echo Instalator: dist\321code-Setup.exe
echo Samodzielny interpreter: dist\321.exe
echo.
echo Skopiuj 321code-Setup.exe na komputer docelowy.
echo Na komputerze docelowym Python nie jest wymagany.
pause
exit /b 0

:error
echo.
echo BLAD podczas budowania. Sprawdz komunikaty powyzej.
pause
exit /b 1
