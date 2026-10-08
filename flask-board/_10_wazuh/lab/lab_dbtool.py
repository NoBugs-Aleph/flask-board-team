import sys, os, re, pymysql
from dotenv import dotenv_values

BOARD = r'C:\Users\user\Desktop\Python-aleph-sh\Python-Lab-ALeph-T\_7_board_test'
cfg = dotenv_values(os.path.join(BOARD, '.env'))
url = cfg.get('DATABASE_URL', '')
m = re.match(r'mysql\+pymysql://([^:]+):([^@]*)@([^:/]+):(\d+)/(\S+)', url)
us, pw, h, po, db = m.groups()
conn = pymysql.connect(host=h, user=us, password=pw, port=int(po), database=db)
cur = conn.cursor()

cmd = sys.argv[1] if len(sys.argv) > 1 else 'list'
if cmd == 'list':
    cur.execute("SELECT ip, reason, blocked_at FROM blocked_ips")
    rows = cur.fetchall()
    print("blocked_ips count:", len(rows))
    for r in rows:
        print(" ", r)
elif cmd == 'clear':
    cur.execute("DELETE FROM blocked_ips")
    conn.commit()
    print("cleared blocked_ips, rows affected:", cur.rowcount)
elif cmd == 'unlock':
    uname = sys.argv[2] if len(sys.argv) > 2 else 'wz_test'
    cur.execute("UPDATE users SET is_locked=0, failed_logins=0, locked_at=NULL, "
                "lock_reason=NULL WHERE username=%s", (uname,))
    conn.commit()
    print("unlocked user:", uname, "rows:", cur.rowcount)
elif cmd == 'reset':
    cur.execute("DELETE FROM blocked_ips")
    cur.execute("UPDATE users SET is_locked=0, failed_logins=0, locked_at=NULL, "
                "lock_reason=NULL WHERE username='wz_test'")
    conn.commit()
    print("reset done: blocked_ips cleared + wz_test unlocked")
elif cmd == 'mkuser':
    from werkzeug.security import generate_password_hash
    uname, pwd = sys.argv[2], sys.argv[3]
    cur.execute("SELECT id FROM users WHERE username=%s", (uname,))
    if cur.fetchone():
        print("user exists:", uname)
    else:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)",
                    (uname, generate_password_hash(pwd)))
        conn.commit()
        print("created user:", uname)
conn.close()
