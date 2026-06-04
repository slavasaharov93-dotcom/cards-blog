@echo off
chcp 65001 >nul
cd /d "%~dp0"
title CardsAbroad - сайт зарубежных карт

echo.
echo ====================================================
echo   Запуск сайта CardsAbroad
echo ====================================================
echo.

rem --- Ищем Python (py или python) ---
set PY=
where py >nul 2>nul && set PY=py
if not defined PY ( where python >nul 2>nul && set PY=python )

if not defined PY (
  echo [!] Python не найден.
  echo     Установите Python с https://python.org
  echo     ВАЖНО: при установке поставьте галочку "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

echo [1/2] Собираю сайт...
%PY% build.py
if errorlevel 1 (
  echo.
  echo [!] Ошибка при сборке. Скриншот этого окна пришлите помощнику.
  pause
  exit /b 1
)

echo.
echo [2/2] Открываю сайт в браузере...
start "" http://127.0.0.1:8000/

echo.
echo ====================================================
echo   Сайт работает: http://127.0.0.1:8000/
echo   Это окно НЕ закрывайте, пока смотрите сайт.
echo   Чтобы остановить — закройте окно или нажмите Ctrl+C.
echo ====================================================
echo.

%PY% serve.py 8000
