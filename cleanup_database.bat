@echo off
REM Quick database cleanup batch file
REM Run this when you need to clean corrupted database entries

echo KISS Signal Database Cleanup
echo =============================
echo.

python clean_database.py

pause
