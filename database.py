import sqlite3
from typing import List, Dict, Optional, Tuple

class JobDatabase:
    def __init__(self, db_path='jobs.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                description TEXT,
                pay_min REAL,
                pay_max REAL,
                pay_currency TEXT,
                pay_period TEXT,
                employment_type TEXT,
                experience_level TEXT,
                raw_html TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        try:
            self.cursor.execute('ALTER TABLE jobs ADD COLUMN pay_period TEXT')
            self.conn.commit()
        except:
            pass

        try:
            self.cursor.execute('ALTER TABLE jobs ADD COLUMN date_posted TEXT')
            self.conn.commit()
        except:
            pass

        try:
            self.cursor.execute('ALTER TABLE jobs ADD COLUMN date_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            self.conn.commit()
        except:
            pass

        try:
            self.cursor.execute('ALTER TABLE jobs ADD COLUMN years_experience INTEGER')
            self.conn.commit()
        except:
            pass

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                skill_name TEXT NOT NULL,
                is_required BOOLEAN DEFAULT 1,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
                UNIQUE(job_id, skill_name)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER UNIQUE NOT NULL,
                embedding_vector BLOB NOT NULL,
                model_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_similarities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id_1 INTEGER NOT NULL,
                job_id_2 INTEGER NOT NULL,
                similarity_score REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id_1) REFERENCES jobs(id) ON DELETE CASCADE,
                FOREIGN KEY (job_id_2) REFERENCES jobs(id) ON DELETE CASCADE,
                UNIQUE(job_id_1, job_id_2)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                base_url TEXT UNIQUE NOT NULL,
                last_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_jobs_scraped INTEGER DEFAULT 0
            )
        ''')

        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_url ON jobs(url)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_skill_job ON skills(job_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_embedding_job ON embeddings(job_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_similarity_jobs ON job_similarities(job_id_1, job_id_2)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_board_url ON job_boards(base_url)')

        self.conn.commit()

    def insert_job(self, job_data: Dict) -> Optional[int]:
        try:
            self.cursor.execute('''
                INSERT INTO jobs (url, title, company, location, description,
                                pay_min, pay_max, pay_currency, pay_period, employment_type,
                                experience_level, years_experience, date_posted, date_scraped, raw_html)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_data.get('url'),
                job_data.get('title'),
                job_data.get('company'),
                job_data.get('location'),
                job_data.get('description'),
                job_data.get('pay_min'),
                job_data.get('pay_max'),
                job_data.get('pay_currency', 'USD'),
                job_data.get('pay_period', 'year'),
                job_data.get('employment_type'),
                job_data.get('experience_level'),
                job_data.get('years_experience'),
                job_data.get('date_posted'),
                job_data.get('date_scraped'),
                job_data.get('raw_html')
            ))

            job_id = self.cursor.lastrowid

            required_skills = job_data.get('skills_required', [])
            for skill in required_skills:
                self.add_skill(job_id, skill, is_required=True)

            optional_skills = job_data.get('skills_optional', [])
            for skill in optional_skills:
                self.add_skill(job_id, skill, is_required=False)

            self.conn.commit()
            return job_id

        except sqlite3.IntegrityError:
            # Silently skip duplicates - URL is unique
            return None
        except Exception as e:
            print(f"Error inserting job: {e}")
            self.conn.rollback()
            return None

    def add_skill(self, job_id: int, skill_name: str, is_required: bool = True):
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO skills (job_id, skill_name, is_required)
                VALUES (?, ?, ?)
            ''', (job_id, skill_name.strip(), is_required))
        except Exception as e:
            print(f"Error adding skill: {e}")

    def get_job(self, job_id: int) -> Optional[Dict]:
        self.cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
        row = self.cursor.fetchone()

        if not row:
            return None

        job = dict(row)
        job['skills_required'] = self.get_job_skills(job_id, required=True)
        job['skills_optional'] = self.get_job_skills(job_id, required=False)

        return job

    def get_all_jobs(self) -> List[Dict]:
        self.cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC')
        rows = self.cursor.fetchall()

        jobs = []
        for row in rows:
            job = dict(row)
            job['skills_required'] = self.get_job_skills(job['id'], required=True)
            job['skills_optional'] = self.get_job_skills(job['id'], required=False)
            jobs.append(job)

        return jobs

    def get_job_skills(self, job_id: int, required: bool = True) -> List[str]:
        self.cursor.execute('''
            SELECT skill_name FROM skills
            WHERE job_id = ? AND is_required = ?
        ''', (job_id, required))

        return [row['skill_name'] for row in self.cursor.fetchall()]

    def save_embedding(self, job_id: int, embedding_vector: bytes, model_name: str):
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO embeddings (job_id, embedding_vector, model_name)
                VALUES (?, ?, ?)
            ''', (job_id, embedding_vector, model_name))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving embedding: {e}")
            self.conn.rollback()

    def get_embedding(self, job_id: int) -> Optional[bytes]:
        self.cursor.execute('''
            SELECT embedding_vector FROM embeddings WHERE job_id = ?
        ''', (job_id,))

        row = self.cursor.fetchone()
        return row['embedding_vector'] if row else None

    def save_similarity(self, job_id_1: int, job_id_2: int, similarity_score: float):
        try:
            min_id = min(job_id_1, job_id_2)
            max_id = max(job_id_1, job_id_2)

            self.cursor.execute('''
                INSERT OR REPLACE INTO job_similarities (job_id_1, job_id_2, similarity_score)
                VALUES (?, ?, ?)
            ''', (min_id, max_id, similarity_score))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving similarity: {e}")
            self.conn.rollback()

    def get_similar_jobs(self, job_id: int, top_n: int = 5) -> List[Tuple[int, str, float]]:
        self.cursor.execute('''
            SELECT
                CASE
                    WHEN js.job_id_1 = ? THEN js.job_id_2
                    ELSE js.job_id_1
                END as similar_job_id,
                j.title,
                js.similarity_score
            FROM job_similarities js
            JOIN jobs j ON (
                CASE
                    WHEN js.job_id_1 = ? THEN js.job_id_2
                    ELSE js.job_id_1
                END = j.id
            )
            WHERE js.job_id_1 = ? OR js.job_id_2 = ?
            ORDER BY js.similarity_score DESC
            LIMIT ?
        ''', (job_id, job_id, job_id, job_id, top_n))

        return [(row['similar_job_id'], row['title'], row['similarity_score'])
                for row in self.cursor.fetchall()]

    def get_jobs_without_embeddings(self) -> List[Dict]:
        self.cursor.execute('''
            SELECT j.* FROM jobs j
            LEFT JOIN embeddings e ON j.id = e.job_id
            WHERE e.job_id IS NULL
        ''')

        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def save_job_board(self, company_name: str, base_url: str, jobs_count: int = 0):
        """Save or update a job board after successful scraping"""
        try:
            self.cursor.execute('''
                INSERT INTO job_boards (company_name, base_url, last_scraped, total_jobs_scraped)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?)
                ON CONFLICT(base_url) DO UPDATE SET
                    company_name = excluded.company_name,
                    last_scraped = CURRENT_TIMESTAMP,
                    total_jobs_scraped = total_jobs_scraped + excluded.total_jobs_scraped
            ''', (company_name, base_url, jobs_count))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving job board: {e}")
            self.conn.rollback()

    def get_all_job_boards(self) -> List[Dict]:
        """Get all saved job boards, ordered by most recently scraped"""
        self.cursor.execute('''
            SELECT company_name, base_url, last_scraped, total_jobs_scraped
            FROM job_boards
            ORDER BY last_scraped DESC
        ''')
        return [dict(row) for row in self.cursor.fetchall()]

    def close(self):
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
