@echo off
echo Validating KISS Signal database and configuration...
echo.

echo Checking database file...
if exist data\kiss_signal.db (
    echo ✓ Database file exists
) else (
    echo ❌ Database file missing!
    goto end
)

echo.
echo Checking configuration files...
python -c "import yaml; yaml.safe_load(open('config.yaml')); print('✓ config.yaml is valid')" 2>nul
if %errorlevel% neq 0 (
    echo ❌ config.yaml has errors!
    goto end
)

python -c "import yaml; yaml.safe_load(open('config/rules.yaml')); print('✓ rules.yaml is valid')" 2>nul
if %errorlevel% neq 0 (
    echo ❌ rules.yaml has errors!
    goto end
)

echo.
echo Checking database content...
python -c "import sqlite3; conn = sqlite3.connect('data/kiss_signal.db'); count = conn.execute('SELECT COUNT(*) FROM strategies').fetchone()[0]; print(f'✓ Total strategies: {count}'); conn.close()" 2>nul
if %errorlevel% neq 0 (
    echo ❌ Database query failed!
    goto end
)

python -c "import sqlite3; conn = sqlite3.connect('data/kiss_signal.db'); configs = conn.execute('SELECT DISTINCT config_hash FROM strategies').fetchall(); hashes = [c[0] for c in configs]; print(f'✓ Config hashes: {hashes}'); legacy_count = len([h for h in hashes if h == \"legacy\"]); print(f'✓ Legacy configs: {legacy_count}'); conn.close()" 2>nul
if %errorlevel% neq 0 (
    echo ❌ Config hash check failed!
    goto end
)

echo.
echo Checking analysis files...
if exist test_analysis.csv (
    echo ✓ test_analysis.csv exists
) else (
    echo ℹ test_analysis.csv not found (run 'python run.py analyze-strategies')
)

if exist strategy_performance_report.csv (
    echo ✓ strategy_performance_report.csv exists
) else (
    echo ℹ strategy_performance_report.csv not found
)

echo.
echo ✅ Validation complete!

:end
echo.
pause
