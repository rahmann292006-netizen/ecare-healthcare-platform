from dotenv import load_dotenv
load_dotenv(dotenv_path=r'C:\Projects\ecare\apps\api\.env', override=True)
import os, psycopg

for dbname in ['ecare', 'ecare_test']:
    url = os.environ.get('DATABASE_URL', '').replace('/ecare', f'/{dbname}')
    try:
        conn = psycopg.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
        tables = [t[0] for t in cur.fetchall()]
        cur.execute("SELECT version_num FROM alembic_version")
        ver = cur.fetchone()
        print(f"\n=== {dbname} ===")
        print(f"Alembic version: {ver[0] if ver else 'none'}")
        print(f"Tables ({len(tables)}): {tables}")
        # Count key tables
        for t in ['users', 'hospitals', 'doctors', 'diagnostic_labs', 'packages', 'package_inclusions', 'family_members', 'reminders', 'appointments', 'invoices']:
            if t in tables:
                cur.execute(f"SELECT count(*) FROM {t}")
                print(f"  {t}: {cur.fetchone()[0]}")
        conn.close()
    except Exception as e:
        print(f"\n=== {dbname} === ERROR: {e}")