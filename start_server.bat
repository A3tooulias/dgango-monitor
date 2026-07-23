@echo off
chcp 65001 >nul

echo Ξεκινάω τον server (waitress)...
start "Climate Monitor - Server" /D "%~dp0" cmd /k python -m waitress --host=0.0.0.0 --port=8000 config.wsgi:application

echo Περιμένω 3 δευτερόλεπτα να σηκωθεί ο server...
timeout /t 3 /nobreak >nul

echo Ξεκινάω το Cloudflare Tunnel...
start "Climate Monitor - Tunnel" /D "%~dp0" cmd /k "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000

echo Ξεκινάω το περιοδικό AgroMet poll...
start "Climate Monitor - AgroMet" /D "%~dp0" cmd /k python manage.py poll_agromet --loop

echo.
echo Έτοιμο! Δες το 2ο παράθυρο (Tunnel) για τη διεύθυνση https://...trycloudflare.com
echo Άφησε ΚΑΙ ΤΑ ΤΡΙΑ παράθυρα ανοιχτά όσο θες να δουλεύει το σύστημα.