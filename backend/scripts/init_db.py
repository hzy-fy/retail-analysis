"""初始化数据库：建库（如不存在）。可通过环境变量覆盖连接信息。"""
import os
import sys

import psycopg

password = os.environ.get('PGPASSWORD', 'postgres')
try:
    conn = psycopg.connect(
        f"dbname=postgres user={os.environ.get('PGUSER', 'postgres')} password={password} "
        f"host={os.environ.get('PGHOST', '127.0.0.1')} port={os.environ.get('PGPORT', '5432')}",
        autocommit=True,
    )
except Exception as e:
    print(f'CONNECT_FAIL: {e}')
    sys.exit(1)

cur = conn.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", ('retail_analysis',))
if cur.fetchone():
    print('DB_EXISTS')
else:
    cur.execute('CREATE DATABASE retail_analysis')
    print('DB_CREATED')
conn.close()
