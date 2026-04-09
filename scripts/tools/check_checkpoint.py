import sqlite3

conn = sqlite3.connect('logs/pipeline_checkpoints.db')
cur = conn.cursor()

# List tables and schema
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()

for t in tables:
    cur.execute(f"PRAGMA table_info([{t[0]}])")
    cols = cur.fetchall()
    print(f"\n{t[0]} columns: {[c[1] for c in cols]}")
    cur.execute(f"SELECT COUNT(*) FROM [{t[0]}]")
    print(f"  rows: {cur.fetchone()[0]}")

# Get recent checkpoints
try:
    cur.execute("SELECT * FROM checkpoints ORDER BY rowid DESC LIMIT 3")
    rows = cur.fetchall()
    for r in rows:
        # Print first 200 chars of each field
        print(f"\nCheckpoint (rowid recent):")
        for i, val in enumerate(r):
            s = str(val)[:200]
            print(f"  col[{i}]: {s}")
except Exception as e:
    print(f"Error: {e}")

conn.close()
