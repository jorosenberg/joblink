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
    
    if event.get('source') == 'async_batch_scrape':
        return run_batch_scrape_pipeline(event)

    body = json.loads(event.get('body', '{}'))
    
    # Support both single URL and batch URLs
    urls_input = body.get('urls', [])
    url = body.get('url', '').strip()
    password = body.get('password', '')
    
    if not urls_input and not url:
        return response(400, {'error': 'URL or URLs array is required'})
    
    # Handle batch URLs
    if urls_input and isinstance(urls_input, list):
        expected = get_scrape_password()
        if password != expected:
            return response(403, {'error': 'Invalid password'})
        
        batch_id = str(uuid.uuid4())
        db = get_db()
        
        # Start batch scraping async
        lambda_client = boto3.client('lambda')
        lambda_client.invoke(
            FunctionName=context.function_name,
            InvocationType='Event',
            Payload=json.dumps({
                'source': 'async_batch_scrape',
                'batch_id': batch_id,
                'urls': urls_input
            })
        )
        
        return response(200, {
            'message': 'Batch scraping started',
            'batch_id': batch_id,
            'total_urls': len(urls_input)
        })
    
    # Handle single URL (existing logic)
    limit = int(body.get('limit', 10))
    location = body.get('location', '')
    skills = body.get('skills', '')

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


def run_batch_scrape_pipeline(event):
    batch_id = event['batch_id']
    urls_data = event['urls']
    
    db = get_db()
    total_jobs_added = 0
    total_duplicates = 0
    all_new_job_ids = []
    
    try:
        from scraper import JobScraper
        from parser import JobParser
        
        for idx, url_config in enumerate(urls_data):
            url = url_config.get('url', '').strip()
            limit = int(url_config.get('limit', 10))
            location = url_config.get('location', '')
            skills = url_config.get('skills', '')
            
            if not url:
                logger.warning(f"Skipping invalid URL at index {idx}")
                continue
            
            logger.info(f"[{idx+1}/{len(urls_data)}] Scraping {url}")
            
            try:
                filters = {
                    'skills': skills.split(',') if skills else [],
                    'location': location if location else None
                }
                
                scraper = JobScraper(base_url=url, limit=limit, filters=filters)
                job_pages = scraper.scrape()
                
                parser = JobParser()
                date_scraped = datetime.now().isoformat()
                company_name = None
                new_job_ids = []
                
                for job in job_pages:
                    if total_jobs_added >= sum(int(u.get('limit', 10)) for u in urls_data):
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
                        total_jobs_added += 1
                        new_job_ids.append(job_id)
                    else:
                        total_duplicates += 1
                
                all_new_job_ids.extend(new_job_ids)
                
                if company_name:
                    db.save_job_board(company_name, url, len(new_job_ids))
                
                logger.info(f"Added {len(new_job_ids)} jobs from {url}")
                
            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                continue
        
        if all_new_job_ids:
            logger.info(f"Batch complete: {total_jobs_added} jobs added. Starting analysis...")
            try:
                lambda_client = boto3.client('lambda')
                lambda_client.invoke(
                    FunctionName=os.environ['ANALYSIS_LAMBDA_NAME'],
                    InvocationType='Event',
                    Payload=json.dumps({'batch_id': batch_id, 'job_ids': all_new_job_ids})
                )
            except Exception as e:
                logger.error(f"Failed to invoke analysis: {e}")
        
        logger.info(f"Batch scraping complete. Total: {total_jobs_added} added, {total_duplicates} duplicates")
        
    except Exception as e:
        logger.error(f"Batch scrape error: {str(e)}")
    
    return {'statusCode': 200}

