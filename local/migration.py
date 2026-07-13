import sqlite3
import psycopg2
import psycopg2.extras

import os

SQLITE_PATH = os.environ.get("SQLITE_PATH", "jobs.db")

# Works against any Postgres (Neon: also set PG_SSLMODE=require).
PG_HOST     = os.environ["PG_HOST"]
PG_DBNAME   = os.environ.get("PG_DBNAME", "jobsdb")
PG_USER     = os.environ["PG_USER"]
PG_PASSWORD = os.environ["PG_PASSWORD"]
PG_PORT     = int(os.environ.get("PG_PORT", "5432"))
PG_SSLMODE  = os.environ.get("PG_SSLMODE")

sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row
sc = sqlite_conn.cursor()

pg_kwargs = dict(host=PG_HOST, dbname=PG_DBNAME, user=PG_USER, password=PG_PASSWORD, port=PG_PORT)
if PG_SSLMODE:
    pg_kwargs["sslmode"] = PG_SSLMODE
pg_conn = psycopg2.connect(**pg_kwargs)
pg_conn.autocommit = False
pc = pg_conn.cursor()

print("Clearing existing data from PostgreSQL...")
pc.execute("TRUNCATE TABLE job_similarities CASCADE")
pc.execute("TRUNCATE TABLE skills CASCADE")
pc.execute("TRUNCATE TABLE embeddings CASCADE")
pc.execute("TRUNCATE TABLE jobs CASCADE")
pc.execute("TRUNCATE TABLE job_boards CASCADE")
pg_conn.commit()
print("Database cleared.")

print("Migrating jobs...")
sc.execute("""
    SELECT id, url, title, company, location, description,
        pay_min, pay_max, pay_currency, pay_period, employment_type,
        experience_level, years_experience, date_posted, date_scraped,
        raw_html, created_at
    FROM jobs
""")
for row in sc.fetchall():
    pc.execute("""
        INSERT INTO jobs (id, url, title, company, location, description,
            pay_min, pay_max, pay_currency, pay_period, employment_type,
            experience_level, years_experience, date_posted, date_scraped,
            raw_html, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, tuple(row))

print("Migrating skills...")
sc.execute("SELECT id, job_id, skill_name, is_required FROM skills")
for row in sc.fetchall():
    pc.execute("""
        INSERT INTO skills (id, job_id, skill_name, is_required)
        VALUES (%s,%s,%s,%s)
    """, (row["id"], row["job_id"], row["skill_name"], bool(row["is_required"])))

print("Migrating embeddings...")
sc.execute("SELECT * FROM embeddings")
for row in sc.fetchall():
    pc.execute("""
        INSERT INTO embeddings (id, job_id, embedding_vector, model_name, created_at)
        VALUES (%s,%s,%s,%s,%s)
    """, (row["id"], row["job_id"], psycopg2.Binary(bytes(row["embedding_vector"])),
          row["model_name"], row["created_at"]))

print("Migrating job_similarities...")
sc.execute("SELECT id, job_id_1, job_id_2, similarity_score, created_at FROM job_similarities")
for row in sc.fetchall():
    pc.execute("""
        INSERT INTO job_similarities (id, job_id_1, job_id_2, similarity_score, created_at)
        VALUES (%s,%s,%s,%s,%s)
    """, tuple(row))

print("Migrating job_boards...")
sc.execute("SELECT id, company_name, base_url, last_scraped, total_jobs_scraped FROM job_boards")
for row in sc.fetchall():
    pc.execute("""
        INSERT INTO job_boards (id, company_name, base_url, last_scraped, total_jobs_scraped)
        VALUES (%s,%s,%s,%s,%s)
    """, tuple(row))

pg_conn.commit()

# Reset PostgreSQL sequences so new inserts after migration use correct IDs
for table in ["jobs", "skills", "embeddings", "job_similarities", "job_boards"]:
    pc.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), MAX(id)) FROM {table}")
pg_conn.commit()

sqlite_conn.close()
pg_conn.close()
print("Migration complete.")
