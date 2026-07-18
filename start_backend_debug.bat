@echo off
cd /d "D:\ai find a job"
set PYTHONPATH=%CD%
python -m uvicorn backend.api:app --reload --port 8000
pause