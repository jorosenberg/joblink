import json
import os
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_db = None
_analyzer = None


def get_secret(secret_arn):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_arn)
    secret = response['SecretString']
    try:
        return json.loads(secret)
    except json.JSONDecodeError:
        return secret


def get_db():
    global _db
    if _db is None:
        from database import JobDatabase
        secret = get_secret(os.environ['DB_SECRET_ARN'])
        _db = JobDatabase(
            host=os.environ['DB_HOST'],
            dbname=os.environ['DB_NAME'],
            user=secret['username'],
            password=secret['password']
        )
        _db.initialize_tables()
    return _db


def set_hf_token():
    hf_token_arn = os.environ.get('HF_TOKEN_ARN', '')
    if hf_token_arn:
        token = get_secret(hf_token_arn)
        os.environ['HUGGING_FACE_HUB_TOKEN'] = token


def get_analyzer():
    global _analyzer
    if _analyzer is None:
        set_hf_token()
        from analysis import JobSimilarityAnalyzer
        _analyzer = JobSimilarityAnalyzer()
    return _analyzer


def handler(event, context):
    scrape_id = event.get('scrape_id')
    db = get_db()

    try:
        logger.info("Starting similarity analysis...")
        analyzer = get_analyzer()
        analyzer.compute_all_similarities(db)

        if scrape_id:
            jobs_added = 0
            status = db.get_scrape_status(scrape_id)
            if status:
                jobs_added = status.get('jobs_added', 0)
            db.update_scrape_status(
                scrape_id,
                status='complete',
                message=f'Complete! Added {jobs_added} jobs with similarity analysis'
            )

        logger.info("Analysis complete")
        return {'statusCode': 200}

    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        if scrape_id:
            db.update_scrape_status(
                scrape_id,
                status='error',
                message=f'Analysis error: {str(e)}'
            )
        raise
