@echo off
title Stages & PFE - Serveur Django
echo ======================================================
echo Lancement de la Plateforme de Gestion des Stages & PFE
echo ======================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=.venv\Scripts\python.exe
) else (
    set PYTHON_EXE=python
)

echo Demarrage du serveur sur http://127.0.0.1:8000/ ...
start "" http://127.0.0.1:8000/
%PYTHON_EXE% manage.py runserver

pause
