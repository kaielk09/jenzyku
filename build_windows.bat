@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title 321code - Budowanie EXE

echo ==========================================
echo          321code - BUILD WINDOWS
echo ==========================================
echo.
echo Folder projektu: %CD%
echo.

REM Sprawdz, czy BAT jest uruchomiony w glownym folderze repozytorium.
if not exist "code321\cli.py" (
    echo BLAD: Nie znaleziono code321\cli.py.
    echo.
    echo Ten plik BAT musi lezec w glownym folderze projektu,
    echo obok folderow code321 i installer.
    echo Nie uruchamiaj go z folderu Pobrane, jesli projekt jest gdzie indziej.
    goto :fail
)
if not exist "installer\cli_entry.py" (
    echo BLAD: Brakuje installer\cli_entry.py.
    goto :fail
)
if not exist "installer\setup.py" (
    echo BLAD: Brakuje installer\setup.py.
    goto :fail
)

REM Wymagamy konkretnej wersji Pythona, aby uniknac problemow z PyInstaller.
py -3.11 --version >nul 2>nul
if errorlevel 1 (
    echo BLAD: Nie znaleziono Python 3.11.
    echo Zainstaluj Python 3.11 64-bit z python.org i zaznacz Add Python to PATH.
    goto :fail
)

if not exist ".build-venv\Scripts\python.exe" (
    echo [1/5] Tworzenie srodowiska budowania...
    py -3.11 -m venv ".build-venv"
    if errorlevel 1 goto :fail
)

set "PY=%CD%\.build-venv\Scripts\python.exe"

echo [2/5] Instalowanie narzedzi...
"%PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%PY%" -m pip install --upgrade pyinstaller
if errorlevel 1 goto :fail

if not exist "dist" mkdir "dist"
if not exist ".build" mkdir ".build"
del /q "dist\321.exe" 2>nul
del /q "dist\321code-Setup.exe" 2>nul

echo.
echo [3/5] Budowanie interpretera 321.exe...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --console --name 321 --paths "%CD%" --collect-all code321 --distpath "%CD%\dist" --workpath "%CD%\.build\cli-work" --specpath "%CD%\.build" "installer\cli_entry.py"
if errorlevel 1 goto :fail
if not exist "dist\321.exe" (
    echo BLAD: PyInstaller zakonczyl prace, ale nie ma dist\321.exe.
    goto :fail
)

echo.
echo [4/5] Budowanie instalatora 321code-Setup.exe...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed --name 321code-Setup --add-binary "%CD%\dist\321.exe;." --distpath "%CD%\dist" --workpath "%CD%\.build\setup-work" --specpath "%CD%\.build" "installer\setup.py"
if errorlevel 1 goto :fail
if not exist "dist\321code-Setup.exe" (
    echo BLAD: Nie utworzono dist\321code-Setup.exe.
    goto :fail
)

echo.
echo [5/5] Sprawdzanie plikow...
for %%F in ("dist\321.exe") do echo Interpreter: %%~zF bajtow
for %%F in ("dist\321code-Setup.exe") do echo Instalator:  %%~zF bajtow

echo.
echo ==========================================
echo              GOTOWE!
echo ==========================================
echo.
echo Pliki EXE znajduja sie w folderze:
echo %CD%\dist
echo.
echo Uruchom dist\321code-Setup.exe.
echo Python nie jest potrzebny na komputerze uzytkownika.
echo.
pause
exit /b 0

:fail
echo.
echo ==========================================
echo BUDOWANIE NIE POWIODLO SIE.
echo Przeczytaj komunikat bledu powyzej.
echo ==========================================
echo.
pause
exit /b 1
