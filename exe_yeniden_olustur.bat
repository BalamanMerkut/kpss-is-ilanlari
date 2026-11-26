@echo off
rem Programda değişiklik yapıldıktan sonra arkadaşlara gönderilecek .exe'yi yeniden oluşturur.
chcp 65001 >nul
cd /d "%~dp0uygulama"
python -m PyInstaller --noconfirm --clean --onefile --noconsole --name "KPSS-Is-Ilanlari" ^
  --icon "%~dp0uygulama\simge.ico" --add-data "%~dp0uygulama\arayuz.html;." --paths "%~dp0uygulama" ^
  --hidden-import osym --hidden-import pdf_tablo --hidden-import pymupdf --collect-all pymupdf ^
  --distpath "%~dp0derleme\dist" --workpath "%~dp0derleme\build" --specpath "%~dp0derleme" "%~dp0uygulama\sunucu.py"
if errorlevel 1 ( echo DERLEME BASARISIZ & pause & exit /b 1 )
copy /y "%~dp0derleme\dist\KPSS-Is-Ilanlari.exe" "%~dp0Arkadaslara Gonder\KPSS İş İlanları.exe" >nul
echo Tamam: "Arkadaslara Gonder" klasorundeki exe guncellendi.
pause
