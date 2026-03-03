from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Tuple
import pickle
from database import JobDatabase

class JobSimilarityAnalyzer:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        print(f"Loading sentence transformer model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        print(f"Model loaded successfully")

    def create_job_text(self, job: Dict) -> str:
        parts = []

        if job.get('title'):
            parts.append(f"Title: {job['title']}")

        if job.get('company'):
            parts.append(f"Company: {job['company']}")

        if job.get('location'):
            parts.append(f"Location: {job['location']}")

        if job.get('employment_type'):
            parts.append(f"Type: {job['employment_type']}")

        if job.get('experience_level'):
            parts.append(f"Level: {job['experience_level']}")

        if job.get('skills_required'):
            skills_text = ', '.join(job['skills_required'])
            parts.append(f"Required Skills: {skills_text}")

        if job.get('skills_optional'):
            skills_text = ', '.join(job['skills_optional'])
            parts.append(f"Preferred Skills: {skills_text}")

        if job.get('description'):
            desc = job['description'][:500]
            parts.append(f"Description: {desc}")

        return ' | '.join(parts)

    def compute_embedding(self, job: Dict) -> np.ndarray:
        job_text = self.create_job_text(job)
        embedding = self.model.encode(job_text, convert_to_numpy=True)
        return embedding

    def compute_embeddings_batch(self, jobs: List[Dict]) -> List[np.ndarray]:
        job_texts = [self.create_job_text(job) for job in jobs]
        embeddings = self.model.encode(job_texts, convert_to_numpy=True, show_progress_bar=True)
        return embeddings

    def cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    def compute_all_similarities(self, db: JobDatabase):
        print("\n=== Computing Job Similarities ===")

        jobs_without_embeddings = db.get_jobs_without_embeddings()

        if jobs_without_embeddings:
            print(f"\nComputing embeddings for {len(jobs_without_embeddings)} jobs...")

            for job in jobs_without_embeddings:
                job['skills_required'] = db.get_job_skills(job['id'], required=True)
                job['skills_optional'] = db.get_job_skills(job['id'], required=False)

            embeddings = self.compute_embeddings_batch(jobs_without_embeddings)

            print("Saving embeddings to database...")
            for job, embedding in zip(jobs_without_embeddings, embeddings):
                embedding_bytes = pickle.dumps(embedding)
                db.save_embedding(job['id'], embedding_bytes, self.model_name)

            print(f"✓ Saved {len(embeddings)} embeddings")

        all_jobs = db.get_all_jobs()
        print(f"\nComputing similarities for {len(all_jobs)} jobs...")

        job_embeddings = []
        for job in all_jobs:
            embedding_bytes = db.get_embedding(job['id'])
            if embedding_bytes:
                embedding = pickle.loads(embedding_bytes)
                job_embeddings.append((job['id'], embedding))

        print(f"Computing pairwise similarities for {len(job_embeddings)} jobs...")
        similarities_computed = 0

        for i, (job_id_1, emb_1) in enumerate(job_embeddings):
            for job_id_2, emb_2 in job_embeddings[i+1:]:
                similarity = self.cosine_similarity(emb_1, emb_2)
                db.save_similarity(job_id_1, job_id_2, similarity)
                similarities_computed += 1

            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(job_embeddings)} jobs...")

        print(f"✓ Computed {similarities_computed} similarity pairs")

    def find_similar_jobs(self, db: JobDatabase, job_id: int, top_n: int = 5) -> List[Tuple[int, str, float]]:
        return db.get_similar_jobs(job_id, top_n)

    def print_similar_jobs(self, db: JobDatabase, job_id: int, top_n: int = 5):
        job = db.get_job(job_id)
        if not job:
            print(f"Job {job_id} not found")
            return

        print(f"\n=== Similar Jobs to: {job['title']} ===")
        print(f"Company: {job.get('company', 'Unknown')}")
        print(f"Location: {job.get('location', 'Unknown')}")

        similar_jobs = self.find_similar_jobs(db, job_id, top_n)

        if not similar_jobs:
            print("No similar jobs found")
            return

        print(f"\nTop {len(similar_jobs)} Most Similar Jobs:")
        for i, (similar_job_id, title, score) in enumerate(similar_jobs, 1):
            similar_job = db.get_job(similar_job_id)
            print(f"\n{i}. {title} (Similarity: {score:.3f})")
            print(f"   Company: {similar_job.get('company', 'Unknown')}")
            print(f"   Location: {similar_job.get('location', 'Unknown')}")

            if similar_job.get('skills_required'):
                print(f"   Skills: {', '.join(similar_job['skills_required'][:5])}")
