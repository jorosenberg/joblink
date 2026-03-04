from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Tuple
import pickle
import logging

logger = logging.getLogger()


class JobSimilarityAnalyzer:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        logger.info(f"Loading sentence transformer model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        logger.info("Model loaded successfully")

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
            parts.append(f"Required Skills: {', '.join(job['skills_required'])}")
        if job.get('skills_optional'):
            parts.append(f"Preferred Skills: {', '.join(job['skills_optional'])}")
        if job.get('description'):
            parts.append(f"Description: {job['description'][:500]}")

        return ' | '.join(parts)

    def compute_embedding(self, job: Dict) -> np.ndarray:
        job_text = self.create_job_text(job)
        return self.model.encode(job_text, convert_to_numpy=True)

    def compute_embeddings_batch(self, jobs: List[Dict]) -> List[np.ndarray]:
        job_texts = [self.create_job_text(job) for job in jobs]
        return self.model.encode(job_texts, convert_to_numpy=True, show_progress_bar=False)

    def cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def compute_pairwise_similarities_vectorized(self, embeddings: np.ndarray) -> np.ndarray:
        try:
            from scipy.spatial.distance import pdist, squareform
            distances = pdist(embeddings, metric='cosine')
            similarities = 1 - squareform(distances)
            return similarities
        except ImportError:
            logger.warning("scipy not available, falling back to manual computation")
            return None

    def compute_batch_similarities(self, db, batch_job_ids: List[int]):
        logger.info(f"Computing batch similarities for {len(batch_job_ids)} new jobs...")
        
        batch_embeddings = []
        batch_mapping = []
        
        for job_id in batch_job_ids:
            embedding_bytes = db.get_embedding(job_id)
            if embedding_bytes:
                embedding = pickle.loads(embedding_bytes)
                batch_embeddings.append(embedding)
                batch_mapping.append(job_id)
        
        if not batch_embeddings:
            logger.warning("No embeddings found for batch jobs")
            return
        
        all_jobs = db.get_all_jobs()
        all_embeddings = []
        all_job_ids = []
        
        for job in all_jobs:
            embedding_bytes = db.get_embedding(job['id'])
            if embedding_bytes:
                embedding = pickle.loads(embedding_bytes)
                all_embeddings.append(embedding)
                all_job_ids.append(job['id'])
        
        if not all_embeddings:
            logger.warning("No embeddings available")
            return
        
        similarities_computed = 0
        for i, batch_job_id in enumerate(batch_mapping):
            batch_emb = batch_embeddings[i]
            for j, all_job_id in enumerate(all_job_ids):
                if batch_job_id != all_job_id:
                    all_emb = all_embeddings[j]
                    similarity = self.cosine_similarity(batch_emb, all_emb)
                    db.save_similarity(batch_job_id, all_job_id, similarity)
                    similarities_computed += 1
        
        logger.info(f"Computed {similarities_computed} similarity pairs for batch")

    def compute_all_similarities(self, db):
        logger.info("Computing job similarities...")

        jobs_without_embeddings = db.get_jobs_without_embeddings()

        if jobs_without_embeddings:
            logger.info(f"Computing embeddings for {len(jobs_without_embeddings)} jobs...")

            for job in jobs_without_embeddings:
                job['skills_required'] = db.get_job_skills(job['id'], required=True)
                job['skills_optional'] = db.get_job_skills(job['id'], required=False)

            embeddings = self.compute_embeddings_batch(jobs_without_embeddings)

            for job, embedding in zip(jobs_without_embeddings, embeddings):
                embedding_bytes = pickle.dumps(embedding)
                db.save_embedding(job['id'], embedding_bytes, self.model_name)

            logger.info(f"Saved {len(embeddings)} embeddings")

        all_jobs = db.get_all_jobs()
        logger.info(f"Computing similarities for {len(all_jobs)} jobs...")

        job_embeddings = []
        for job in all_jobs:
            embedding_bytes = db.get_embedding(job['id'])
            if embedding_bytes:
                embedding = pickle.loads(embedding_bytes)
                job_embeddings.append((job['id'], embedding))

        similarities_computed = 0
        for i, (job_id_1, emb_1) in enumerate(job_embeddings):
            for job_id_2, emb_2 in job_embeddings[i+1:]:
                similarity = self.cosine_similarity(emb_1, emb_2)
                db.save_similarity(job_id_1, job_id_2, similarity)
                similarities_computed += 1

        logger.info(f"Computed {similarities_computed} similarity pairs")

