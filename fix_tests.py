import re

# Read the file
with open('tests/test_backtester.py', 'r') as f:
    content = f.read()

# Simple pattern to find and replace the keyword calls 
# This will handle cases like:
# backtester.find_optimal_strategies(
#     rules_config=sample_rules_config,
#     price_data=sample_price_data,
#     symbol="TEST.NS"
# )

# Find all instances and fix them manually
replacements = [
    # Pattern for test calls with rules_config first
    (
        r'(\s+)backtester\.find_optimal_strategies\(\s*rules_config=([^,]+),\s*price_data=([^,]+),\s*symbol=([^)]+)\s*\)',
        r'\1backtester.find_optimal_strategies(\n\1    price_data=\3,\n\1    rules_config=\2,\n\1    symbol=\4,\n\1    market_data=None\n\1)'
    )
]

new_content = content
for pattern, replacement in replacements:
    new_content = re.sub(pattern, replacement, new_content, flags=re.MULTILINE)

# Write back to file
with open('tests/test_backtester.py', 'w') as f:
    f.write(new_content)

print('Fixed test file')
