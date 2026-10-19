@echo off
echo Checking port 8000...
netstat -ano | findstr :8000
echo.
echo If any processes are listed above, kill them with:
echo taskkill /PID [PID_NUMBER] /F
