@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===== NAVBATCHI =====

where python >nul 2>nul
if errorlevel 1 (
  echo Python topilmadi. https://www.python.org/downloads/ dan o'rnating va "Add Python to PATH" ni belgilang.
  pause
  exit /b 1
)

if not exist venv (
  echo Virtual muhit yaratilmoqda...
  python -m venv venv
)
call venv\Scripts\activate.bat
echo Kutubxonalar o'rnatilmoqda...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
  echo Kutubxonalarni o'rnatishda xatolik. Internetni tekshiring.
  pause
  exit /b 1
)

if not exist .env copy .env.example .env >nul

python -c "import sqlite3,config,db; db.init_db(config.settings.DB_PATH); c=sqlite3.connect(str(config.settings.DB_PATH)); print(c.execute('select count(*) from admins').fetchone()[0])" > "%TEMP%\nav_admins.txt"
set /p ADMINS=<"%TEMP%\nav_admins.txt"
if "%ADMINS%"=="0" (
  echo.
  echo Administrator hali yaratilmagan. Hozir yarating:
  python create_admin.py
)

echo.
echo Dastur ishga tushmoqda: http://127.0.0.1:5000   (administrator: http://127.0.0.1:5000/admin)
echo To'xtatish uchun Ctrl+C bosing.
python run.py
pause
