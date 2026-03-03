import json
import os
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_db = None
_scrape_password = None


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
    return _db


def get_scrape_password():
    global _scrape_password
    if _scrape_password is None:
        _scrape_password = get_secret(os.environ['SCRAPE_PASSWORD_ARN'])
    return _scrape_password


def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body)
    }


def handler(event, context):
    method = event.get('requestContext', {}).get('http', {}).get('method', '')
    path = event.get('rawPath', '')
    params = event.get('queryStringParameters') or {}

    logger.info(f"{method} {path}")

    try:
        if path == '/api/jobs' and method == 'GET':
            return get_jobs(params)
        elif path.startswith('/api/job/') and method == 'GET':
            job_id = int(path.split('/')[-1])
            return get_job(job_id)
        elif path.startswith('/api/job/') and method == 'DELETE':
            password = event.get('headers', {}).get('x-scrape-password', '')
            return delete_job(int(path.split('/')[-1]), password)
        elif path == '/api/graph' and method == 'GET':
            return get_graph(params)
        elif path == '/api/job-boards' and method == 'GET':
            return get_job_boards()
        elif path == '/api/scrape/status' and method == 'GET':
            scrape_id = params.get('scrape_id', '')
            return get_scrape_status(scrape_id)
        else:
            return response(404, {'error': 'Not found'})
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return response(500, {'error': str(e)})


def get_jobs(params):
    db = get_db()
    jobs = db.get_all_jobs()

    skills_filter = [s.strip().lower() for s in params.get('skills', '').split(',') if s.strip()] if params.get('skills') else []
    location_filter = params.get('location', '').lower()
    pay_min_filter = float(params.get('pay_min', 0))
    pay_max_filter = float(params.get('pay_max', 0))
    years_min_filter = int(params['years_min']) if params.get('years_min') else None
    years_max_filter = int(params['years_max']) if params.get('years_max') else None

    jobs_list = []
    for job in jobs:
        if skills_filter:
            job_skills = [s.lower() for s in job.get('skills_required', []) + job.get('skills_optional', [])]
            if not any(skill in ' '.join(job_skills) for skill in skills_filter):
                continue

        if location_filter and location_filter not in job.get('location', '').lower():
            continue

        if pay_min_filter and (not job.get('pay_min') or job.get('pay_min') < pay_min_filter):
            continue

        if pay_max_filter and (not job.get('pay_max') or job.get('pay_max') > pay_max_filter):
            continue

        job_years = job.get('years_experience')
        if years_min_filter is not None and (job_years is None or job_years < years_min_filter):
            continue
        if years_max_filter is not None and (job_years is None or job_years > years_max_filter):
            continue

        jobs_list.append({
            'id': job['id'],
            'title': job['title'],
            'company': job.get('company', 'Unknown'),
            'location': job.get('location', 'Unknown'),
            'employment_type': job.get('employment_type', 'Unknown'),
            'experience_level': job.get('experience_level', 'Unknown'),
            'pay_min': job.get('pay_min'),
            'pay_max': job.get('pay_max'),
            'pay_currency': job.get('pay_currency', 'USD'),
            'pay_period': job.get('pay_period', 'year'),
            'years_experience': job.get('years_experience'),
            'date_posted': job.get('date_posted'),
            'date_scraped': str(job.get('date_scraped', '')),
            'skills_required': job.get('skills_required', []),
            'skills_optional': job.get('skills_optional', []),
            'url': job['url']
        })

    return response(200, jobs_list)


def get_job(job_id):
    db = get_db()
    job = db.get_job(job_id)

    if not job:
        return response(404, {'error': 'Job not found'})

    similar_jobs = db.get_similar_jobs(job_id, top_n=10)

    return response(200, {
        'job': {
            'id': job['id'],
            'title': job['title'],
            'company': job.get('company', 'Unknown'),
            'location': job.get('location', 'Unknown'),
            'employment_type': job.get('employment_type', 'Unknown'),
            'experience_level': job.get('experience_level', 'Unknown'),
            'pay_min': job.get('pay_min'),
            'pay_max': job.get('pay_max'),
            'pay_currency': job.get('pay_currency', 'USD'),
            'pay_period': job.get('pay_period', 'year'),
            'years_experience': job.get('years_experience'),
            'date_posted': job.get('date_posted'),
            'date_scraped': str(job.get('date_scraped', '')),
            'skills_required': job.get('skills_required', []),
            'skills_optional': job.get('skills_optional', []),
            'url': job['url'],
            'description': (job.get('description') or '')[:500]
        },
        'similar_jobs': [
            {'id': sid, 'title': title, 'similarity': score}
            for sid, title, score in similar_jobs
        ]
    })


def delete_job(job_id, password):
    expected = get_scrape_password()
    if password != expected:
        return response(403, {'error': 'Invalid password'})

    db = get_db()
    db.delete_job(job_id)
    return response(200, {'message': f'Job {job_id} deleted'})


def get_graph(params):
    db = get_db()
    jobs = db.get_all_jobs()

    nodes = []
    for job in jobs:
        nodes.append({
            'id': job['id'],
            'label': job['title'],
            'company': job.get('company', 'Unknown'),
            'title': f"{job['title']}\n{job.get('company', 'Unknown')}"
        })

    edges = db.get_all_similarities(min_score=0.5)

    return response(200, {
        'nodes': nodes,
        'edges': [
            {
                'from': edge['job_id_1'],
                'to': edge['job_id_2'],
                'value': edge['similarity_score'],
                'title': f"Similarity: {edge['similarity_score']:.3f}"
            }
            for edge in edges
        ]
    })


def get_job_boards():
    db = get_db()
    boards = db.get_all_job_boards()
    return response(200, boards)


def get_scrape_status(scrape_id):
    if not scrape_id:
        return response(200, {
            'is_running': False,
            'progress': 0,
            'total': 0,
            'current_job': '',
            'message': 'Ready to scrape',
            'jobs_added': 0,
            'duplicates_skipped': 0
        })

    db = get_db()
    status = db.get_scrape_status(scrape_id)
    if not status:
        return response(404, {'error': 'Scrape job not found'})

    return response(200, {
        'is_running': status['status'] in ('running', 'analyzing'),
        'progress': status.get('jobs_added', 0) + status.get('duplicates_skipped', 0),
        'total': status.get('total', 0),
        'current_job': status.get('current_job', ''),
        'message': status.get('message', ''),
        'jobs_added': status.get('jobs_added', 0),
        'duplicates_skipped': status.get('duplicates_skipped', 0),
        'scrape_id': scrape_id
    })
