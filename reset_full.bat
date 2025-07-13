@echo off
echo WARNING: This will delete all historical data and analysis files!
echo This creates a completely fresh start with empty database.
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
echo Deleting analysis files...
if exist test_analysis.csv (
    del test_analysis.csv
    echo ✓ test_analysis.csv deleted
)
if exist strategy_performance_report.csv (
    del strategy_performance_report.csv
    echo ✓ strategy_performance_report.csv deleted
)
if exist analyze_strategies_log.txt (
    del analyze_strategies_log.txt
    echo ✓ analyze_strategies_log.txt deleted
)
if exist clear_and_recalculate_log.txt (
    del clear_and_recalculate_log.txt
    echo ✓ clear_and_recalculate_log.txt deleted
)

echo.
echo Running fresh backtesting...
python run.py run
if %errorlevel% neq 0 (
    echo ❌ Backtesting failed!
    pause
    exit /b 1
)

echo.
echo Generating fresh analysis...
python run.py analyze-strategies
if %errorlevel% neq 0 (
    echo ❌ Analysis generation failed!
    pause
    exit /b 1
)

echo.
echo ✅ Complete reset finished successfully!
echo.
echo Summary:
echo - Database: Completely recreated
echo - Analysis files: Deleted and regenerated
echo - Backup: Available at data\kiss_signal.db.backup
echo.
pause
