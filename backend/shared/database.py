import json
import boto3
import psycopg2
import psycopg2.extras
from typing import List, Dict, Optional, Tuple


def get_db_credentials():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId="job-scraper/db-credentials")
    return json.loads(response["SecretString"])


class JobDatabase:
    def __init__(self, host: str, dbname: str, user: str, password: str):
        self.host = host
        self.dbname = dbname
        self.user = user
        self.password = password
        self.conn = None
        self.cursor = None

    def connect(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(
                host=self.host,
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
            self.conn.autocommit = False
            self.cursor = self.conn.cursor()
        elif self.conn.get_transaction_status() == psycopg2.extensions.TRANSACTION_STATUS_INERROR:
            self.conn.rollback()
            self.cursor = self.conn.cursor()
        return self

    def initialize_tables(self):
        self.connect()

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                description TEXT,
                pay_min DOUBLE PRECISION,
                pay_max DOUBLE PRECISION,
                pay_currency TEXT,
                pay_period TEXT,
                employment_type TEXT,
                experience_level TEXT,
                years_experience INTEGER,
                date_posted TEXT,
                date_scraped TIMESTAMP DEFAULT NOW(),
                raw_html TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id SERIAL PRIMARY KEY,
                job_id INTEGER NOT NULL,
                skill_name TEXT NOT NULL,
                is_required BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
                UNIQUE(job_id, skill_name)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id SERIAL PRIMARY KEY,
                job_id INTEGER UNIQUE NOT NULL,
                embedding_vector BYTEA NOT NULL,
                model_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_similarities (
                id SERIAL PRIMARY KEY,
                job_id_1 INTEGER NOT NULL,
                job_id_2 INTEGER NOT NULL,
                similarity_score DOUBLE PRECISION NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (job_id_1) REFERENCES jobs(id) ON DELETE CASCADE,
                FOREIGN KEY (job_id_2) REFERENCES jobs(id) ON DELETE CASCADE,
                UNIQUE(job_id_1, job_id_2)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_boards (
                id SERIAL PRIMARY KEY,
                company_name TEXT NOT NULL,
                base_url TEXT UNIQUE NOT NULL,
                last_scraped TIMESTAMP DEFAULT NOW(),
                total_jobs_scraped INTEGER DEFAULT 0
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS scrape_status (
                id TEXT PRIMARY KEY,
                status TEXT,
                message TEXT,
                jobs_added INTEGER DEFAULT 0,
                duplicates_skipped INTEGER DEFAULT 0,
                total INTEGER DEFAULT 0,
                current_job TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_url ON jobs(url)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_skill_job ON skills(job_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_embedding_job ON embeddings(job_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_similarity_jobs ON job_similarities(job_id_1, job_id_2)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_board_url ON job_boards(base_url)")

        self.conn.commit()

    def insert_job(self, job_data: Dict) -> Optional[int]:
        self.connect()
        try:
            self.cursor.execute("""
                INSERT INTO jobs (url, title, company, location, description,
                                pay_min, pay_max, pay_currency, pay_period, employment_type,
                                experience_level, years_experience, date_posted, date_scraped, raw_html)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
                RETURNING id
            """, (
                job_data.get("url"),
                job_data.get("title"),
                job_data.get("company"),
                job_data.get("location"),
                job_data.get("description"),
                job_data.get("pay_min"),
                job_data.get("pay_max"),
                job_data.get("pay_currency", "USD"),
                job_data.get("pay_period", "year"),
                job_data.get("employment_type"),
                job_data.get("experience_level"),
                job_data.get("years_experience"),
                job_data.get("date_posted"),
                job_data.get("date_scraped"),
                job_data.get("raw_html"),
            ))

            result = self.cursor.fetchone()
            if result is None:
                self.conn.commit()
                return None

            job_id = result["id"]

            required_skills = job_data.get("skills_required", [])
            for skill in required_skills:
                self.add_skill(job_id, skill, is_required=True)

            optional_skills = job_data.get("skills_optional", [])
            for skill in optional_skills:
                self.add_skill(job_id, skill, is_required=False)

            self.conn.commit()
            return job_id

        except Exception as e:
            print(f"Error inserting job: {e}")
            self.conn.rollback()
            return None

    def add_skill(self, job_id: int, skill_name: str, is_required: bool = True):
        self.connect()
        try:
            self.cursor.execute("""
                INSERT INTO skills (job_id, skill_name, is_required)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (job_id, skill_name.strip(), is_required))
        except Exception as e:
            print(f"Error adding skill: {e}")

    def get_job(self, job_id: int) -> Optional[Dict]:
        self.connect()
        self.cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
        row = self.cursor.fetchone()

        if not row:
            return None

        job = dict(row)
        job["skills_required"] = self.get_job_skills(job_id, required=True)
        job["skills_optional"] = self.get_job_skills(job_id, required=False)

        return job

    def get_all_jobs(self) -> List[Dict]:
        self.connect()
        self.cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
        rows = self.cursor.fetchall()

        jobs = []
        for row in rows:
            job = dict(row)
            job["skills_required"] = self.get_job_skills(job["id"], required=True)
            job["skills_optional"] = self.get_job_skills(job["id"], required=False)
            jobs.append(job)

        return jobs

    def get_job_skills(self, job_id: int, required: bool = True) -> List[str]:
        self.connect()
        self.cursor.execute("""
            SELECT skill_name FROM skills
            WHERE job_id = %s AND is_required = %s
        """, (job_id, required))

        return [row["skill_name"] for row in self.cursor.fetchall()]

    def save_embedding(self, job_id: int, embedding_vector: bytes, model_name: str):
        self.connect()
        try:
            self.cursor.execute("""
                INSERT INTO embeddings (job_id, embedding_vector, model_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    embedding_vector = EXCLUDED.embedding_vector,
                    model_name = EXCLUDED.model_name,
                    created_at = NOW()
            """, (job_id, psycopg2.Binary(embedding_vector), model_name))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving embedding: {e}")
            self.conn.rollback()

    def get_embedding(self, job_id: int) -> Optional[bytes]:
        self.connect()
        self.cursor.execute("""
            SELECT embedding_vector FROM embeddings WHERE job_id = %s
        """, (job_id,))

        row = self.cursor.fetchone()
        return bytes(row["embedding_vector"]) if row else None

    def save_similarity(self, job_id_1: int, job_id_2: int, similarity_score: float):
        self.connect()
        try:
            min_id = min(job_id_1, job_id_2)
            max_id = max(job_id_1, job_id_2)

            self.cursor.execute("""
                INSERT INTO job_similarities (job_id_1, job_id_2, similarity_score)
                VALUES (%s, %s, %s)
                ON CONFLICT (job_id_1, job_id_2) DO UPDATE SET
                    similarity_score = EXCLUDED.similarity_score,
                    created_at = NOW()
            """, (min_id, max_id, similarity_score))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving similarity: {e}")
            self.conn.rollback()

    def get_similar_jobs(self, job_id: int, top_n: int = 5) -> List[Tuple[int, str, float]]:
        self.connect()
        self.cursor.execute("""
            SELECT
                CASE
                    WHEN js.job_id_1 = %s THEN js.job_id_2
                    ELSE js.job_id_1
                END as similar_job_id,
                j.title,
                js.similarity_score
            FROM job_similarities js
            JOIN jobs j ON (
                CASE
                    WHEN js.job_id_1 = %s THEN js.job_id_2
                    ELSE js.job_id_1
                END = j.id
            )
            WHERE js.job_id_1 = %s OR js.job_id_2 = %s
            ORDER BY js.similarity_score DESC
            LIMIT %s
        """, (job_id, job_id, job_id, job_id, top_n))

        return [(row["similar_job_id"], row["title"], row["similarity_score"])
                for row in self.cursor.fetchall()]
    def get_all_similarities(self, min_score: float = 0.5) -> List[Dict]:
        self.connect()
        self.cursor.execute("""
            SELECT job_id_1, job_id_2, similarity_score
            FROM job_similarities
            WHERE similarity_score >= %s
            ORDER BY similarity_score DESC
        """, (min_score,))
        return [dict(row) for row in self.cursor.fetchall()]


    def get_jobs_without_embeddings(self) -> List[Dict]:
        self.connect()
        self.cursor.execute("""
            SELECT j.* FROM jobs j
            LEFT JOIN embeddings e ON j.id = e.job_id
            WHERE e.job_id IS NULL
        """)

        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def save_job_board(self, company_name: str, base_url: str, jobs_count: int = 0):
        self.connect()
        try:
            self.cursor.execute("""
                INSERT INTO job_boards (company_name, base_url, last_scraped, total_jobs_scraped)
                VALUES (%s, %s, NOW(), %s)
                ON CONFLICT (base_url) DO UPDATE SET
                    company_name = EXCLUDED.company_name,
                    last_scraped = NOW(),
                    total_jobs_scraped = job_boards.total_jobs_scraped + EXCLUDED.total_jobs_scraped
            """, (company_name, base_url, jobs_count))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving job board: {e}")
            self.conn.rollback()

    def get_all_job_boards(self) -> List[Dict]:
        self.connect()
        self.cursor.execute("""
            SELECT company_name, base_url, last_scraped, total_jobs_scraped
            FROM job_boards
            ORDER BY last_scraped DESC
        """)
        return [dict(row) for row in self.cursor.fetchall()]

    def delete_job(self, job_id: int) -> bool:
        self.connect()
        try:
            self.cursor.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
            deleted = self.cursor.rowcount > 0
            self.conn.commit()
            return deleted
        except Exception as e:
            print(f"Error deleting job: {e}")
            self.conn.rollback()
            return False

    def create_scrape_status(self, scrape_id: str, status: str, message: str):
        self.connect()
        try:
            self.cursor.execute("""
                INSERT INTO scrape_status (id, status, message, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
            """, (scrape_id, status, message))
            self.conn.commit()
        except Exception as e:
            print(f"Error creating scrape status: {e}")
            self.conn.rollback()

    def update_scrape_status(
        self,
        scrape_id: str,
        status: Optional[str] = None,
        message: Optional[str] = None,
        jobs_added: Optional[int] = None,
        duplicates_skipped: Optional[int] = None,
        total: Optional[int] = None,
        current_job: Optional[str] = None,
    ):
        self.connect()
        try:
            fields = []
            values = []

            if status is not None:
                fields.append("status = %s")
                values.append(status)
            if message is not None:
                fields.append("message = %s")
                values.append(message)
            if jobs_added is not None:
                fields.append("jobs_added = %s")
                values.append(jobs_added)
            if duplicates_skipped is not None:
                fields.append("duplicates_skipped = %s")
                values.append(duplicates_skipped)
            if total is not None:
                fields.append("total = %s")
                values.append(total)
            if current_job is not None:
                fields.append("current_job = %s")
                values.append(current_job)

            if not fields:
                return

            fields.append("updated_at = NOW()")
            values.append(scrape_id)

            self.cursor.execute(
                f"UPDATE scrape_status SET {', '.join(fields)} WHERE id = %s",
                tuple(values),
            )
            self.conn.commit()
        except Exception as e:
            print(f"Error updating scrape status: {e}")
            self.conn.rollback()

    def get_scrape_status(self, scrape_id: str) -> Optional[Dict]:
        self.connect()
        self.cursor.execute("SELECT * FROM scrape_status WHERE id = %s", (scrape_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()
