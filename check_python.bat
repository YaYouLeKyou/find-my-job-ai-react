@echo off
echo Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo Python not found in PATH
    echo Checking py launcher...
    py --version
)
echo.
echo Checking dependencies...
cd "D:\ai find a job"
pip list | findstr fastapi
pip list | findstr uvicorn
pip list | findstr PyPDF2
pip list | findstr groq
pause