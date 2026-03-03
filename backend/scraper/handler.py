import json
import os
import uuid
import boto3
import logging
from datetime import datetime

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
        _db.initialize_tables()
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
    if event.get('source') == 'async_scrape':
        return run_scrape_pipeline(event)

    body = json.loads(event.get('body', '{}'))
    url = body.get('url', '').strip()
    limit = int(body.get('limit', 10))
    password = body.get('password', '')
    location = body.get('location', '')
    skills = body.get('skills', '')

    if not url:
        return response(400, {'error': 'URL is required'})

    expected = get_scrape_password()
    if password != expected:
        return response(403, {'error': 'Invalid password'})

    scrape_id = str(uuid.uuid4())
    db = get_db()
    db.create_scrape_status(scrape_id, 'running', 'Starting scraper...')

    is_greenhouse = 'greenhouse.io' in url.lower()
    is_lever = 'jobs.lever.co' in url.lower()
    needs_selenium = not is_greenhouse and not is_lever

    if needs_selenium:
        ec2_url = os.environ.get('EC2_SCRAPE_URL', '')
        if ec2_url:
            try:
                import urllib.request
                req_data = json.dumps({
                    'scrape_id': scrape_id,
                    'url': url,
                    'limit': limit,
                    'location': location,
                    'skills': skills
                }).encode('utf-8')
                req = urllib.request.Request(
                    ec2_url,
                    data=req_data,
                    headers={'Content-Type': 'application/json'}
                )
                urllib.request.urlopen(req, timeout=5)
                return response(200, {
                    'message': 'Scraping started (Selenium on EC2)',
                    'scrape_id': scrape_id
                })
            except Exception as e:
                logger.error(f"Failed to delegate to EC2: {e}")
                db.update_scrape_status(scrape_id, status='error', message=f'EC2 delegation failed: {str(e)}')
                return response(500, {'error': 'Failed to start Selenium scraping'})
        else:
            db.update_scrape_status(scrape_id, status='error', message='Selenium not available in Lambda')
            return response(400, {'error': 'This URL requires Selenium (only Greenhouse/Lever supported via Lambda)'})

    lambda_client = boto3.client('lambda')
    lambda_client.invoke(
        FunctionName=context.function_name,
        InvocationType='Event',
        Payload=json.dumps({
            'source': 'async_scrape',
            'scrape_id': scrape_id,
            'url': url,
            'limit': limit,
            'location': location,
            'skills': skills
        })
    )

    return response(200, {
        'message': 'Scraping started',
        'scrape_id': scrape_id
    })


def run_scrape_pipeline(event):
    scrape_id = event['scrape_id']
    url = event['url']
    limit = event['limit']
    location = event.get('location', '')
    skills = event.get('skills', '')

    db = get_db()

    try:
        from scraper import JobScraper
        from parser import JobParser

        filters = {
            'skills': skills.split(',') if skills else [],
            'location': location if location else None
        }

        db.update_scrape_status(scrape_id, message='Scraping job pages...', total=limit)

        scraper = JobScraper(base_url=url, limit=limit, filters=filters)
        job_pages = scraper.scrape()

        db.update_scrape_status(scrape_id, message='Parsing job details...')

        parser = JobParser()
        date_scraped = datetime.now().isoformat()
        jobs_added = 0
        duplicates_skipped = 0
        company_name = None

        for i, job in enumerate(job_pages):
            if jobs_added >= limit:
                break

            parsed_job = parser.parse_job(
                html=job['html'],
                url=job['url'],
                title=job['title'],
                date_scraped=date_scraped
            )

            if not company_name and parsed_job.get('company'):
                company_name = parsed_job.get('company')

            job_id = db.insert_job(parsed_job)
            if job_id:
                jobs_added += 1
            else:
                duplicates_skipped += 1

            db.update_scrape_status(
                scrape_id,
                message=f'Processing jobs... ({jobs_added} added, {duplicates_skipped} duplicates)',
                jobs_added=jobs_added,
                duplicates_skipped=duplicates_skipped,
                current_job=job['title']
            )

        if (jobs_added + duplicates_skipped) > 0 and company_name:
            db.save_job_board(company_name, url, jobs_added)

        if jobs_added >= 2:
            db.update_scrape_status(scrape_id, status='analyzing', message='Computing similarities...')
            try:
                lambda_client = boto3.client('lambda')
                lambda_client.invoke(
                    FunctionName=os.environ['ANALYSIS_LAMBDA_NAME'],
                    InvocationType='Event',
                    Payload=json.dumps({'scrape_id': scrape_id})
                )
            except Exception as e:
                logger.error(f"Failed to invoke analysis: {e}")
                db.update_scrape_status(
                    scrape_id,
                    status='complete',
                    message=f'Added {jobs_added} jobs (similarity analysis failed: {str(e)})'
                )
        else:
            message_parts = [f'Complete! Added {jobs_added} new jobs']
            if jobs_added < limit:
                message_parts[0] = f'Complete! Added {jobs_added}/{limit} jobs (no more available)'
            if duplicates_skipped > 0:
                message_parts.append(f'{duplicates_skipped} duplicates skipped')
            db.update_scrape_status(
                scrape_id,
                status='complete',
                message=', '.join(message_parts)
            )

    except Exception as e:
        logger.error(f"Scrape error: {str(e)}")
        db.update_scrape_status(scrape_id, status='error', message=f'Error: {str(e)}')

    return {'statusCode': 200}
