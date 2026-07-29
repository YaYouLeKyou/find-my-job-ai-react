@echo off
cd /d "D:\ai find a job"
set PYTHONPATH=%CD%;%CD%\backend
python backend/app/main.py
