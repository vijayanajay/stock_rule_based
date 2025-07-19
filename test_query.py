import sqlite3

conn = sqlite3.connect('data/kiss_signal.db')
cursor = conn.execute('''
SELECT s.symbol, s.rule_stack, s.edge_score, s.win_pct, s.sharpe,
       s.avg_return as total_return, s.total_trades, s.config_hash, s.run_timestamp,
       s.config_snapshot
FROM strategies s
INNER JOIN (
    SELECT symbol, rule_stack, config_hash, MAX(id) as max_id
    FROM strategies 
    GROUP BY symbol, rule_stack, config_hash
) latest ON s.id = latest.max_id
ORDER BY s.symbol, s.edge_score DESC
LIMIT 5
''')
results = cursor.fetchall()
print('Results count:', len(results))
if results:
    print('First result symbol:', results[0][0])
else:
    print('No results found')
conn.close()
