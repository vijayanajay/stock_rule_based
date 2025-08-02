@echo off
REM Database Cleanup Script - Remove positions with invalid entry prices
REM 
REM This script cleans up data corruption where positions have zero or negative entry prices.
REM Such data breaks risk management calculations and must be removed.
REM
REM Usage:
REM   cleanup_db.bat          - Clean up the default database
REM   cleanup_db.bat --dry-run - Show what would be cleaned without deleting

echo.
echo 🧹 Database Cleanup - Invalid Entry Prices
echo ==========================================
echo.

if "%1"=="--dry-run" (
    echo Running in DRY RUN mode - no data will be deleted
    python scripts\cleanup_invalid_positions.py --dry-run
) else (
    echo Cleaning up invalid positions in the database...
    python scripts\cleanup_invalid_positions.py
)

if errorlevel 1 (
    echo.
    echo ❌ Cleanup failed! Check the error messages above.
    pause
    exit /b 1
) else (
    echo.
    echo ✅ Database cleanup completed successfully.
    echo.
    pause
)
