@echo off
echo WARNING: This will delete the database but preserve existing analysis files!
echo Use this when you want fresh backtesting but keep analysis reports for comparison.
echo.
set /p confirm="Are you sure you want to proceed? Type 'yes' to continue: "
if /i "%confirm%" NEQ "yes" (
    echo Reset cancelled.
    pause
    exit /b 1
)

echo.
echo Creating backup...
if exist data\kiss_signal.db (
    copy data\kiss_signal.db data\kiss_signal.db.backup > nul 2>&1
    echo ✓ Database backed up to kiss_signal.db.backup
)

echo.
echo Deleting database...
if exist data\kiss_signal.db (
    del data\kiss_signal.db
    echo ✓ Database deleted
) else (
    echo ℹ No database file found
)

echo.
echo Running fresh backtesting...
python run.py run --verbose
if %errorlevel% neq 0 (
    echo ❌ Backtesting failed!
    pause
    exit /b 1
)

echo.
echo ✅ Database reset completed successfully!
echo.
echo Summary:
echo - Database: Completely recreated
echo - Analysis files: Preserved (not deleted)
echo - Backup: Available at data\kiss_signal.db.backup
echo.
echo You can now run 'python run.py analyze-strategies' to generate fresh analysis.
echo.
pause
