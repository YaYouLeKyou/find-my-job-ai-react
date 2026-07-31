@echo off
cd /d "D:\ai find a job"
set PYTHONPATH=%CD%;%CD%\backend
python -m uvicorn app.main:app --reload --port 8000
pause
