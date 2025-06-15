@echo off
REM CI check for duplicate rule configuration files
echo.
echo Running duplicate rule files check...
echo.

python scripts\check_duplicate_rules.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo CI CHECK FAILED: Multiple rule configuration files detected!
    exit /b 1
)

echo.
echo CI CHECK PASSED: No duplicate rule files found.
