@echo off
rem KPSS İş İlanları programını açar (siyah pencere kendiliğinden kapanır).
cd /d "%~dp0uygulama"
start "" pythonw sunucu.py
