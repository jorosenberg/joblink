from flask import Flask, render_template, jsonify, request
import os
import json
import logging
import threading
from datetime import datetime

app = Flask(__name__)
logger = logging.getLogger(__name__)

API_GATEWAY_URL = os.environ.get('API_GATEWAY_URL', 'http://localhost:5000')


def get_db():
    from database import JobDatabase
    import boto3
    client = boto3.client('secretsmanager')
    secret_arn = os.environ.get('DB_SECRET_ARN', '')
    if secret_arn:
        response = client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response['SecretString'])
        return JobDatabase(
            host=secret['host'],
            dbname=secret['dbname'],
            user=secret['username'],
            password=secret['password']
        )
    return JobDatabase(
        host=os.environ.get('DB_HOST', 'localhost'),
        dbname=os.environ.get('DB_NAME', 'jobscraper'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', '')
    )


def get_scrape_password():
    import boto3
    secret_arn = os.environ.get('SCRAPE_PASSWORD_ARN', '')
    if secret_arn:
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId=secret_arn)
        return response['SecretString']
    return os.environ.get('SCRAPE_PASSWORD', '')


@app.route('/')
def index():
    return render_template('index.html', api_gateway_url=API_GATEWAY_URL)


@app.route('/internal/selenium-scrape', methods=['POST'])
def internal_selenium_scrape():
    data = request.json
    scrape_id = data.get('scrape_id', '')
    url = data.get('url', '')
    limit = int(data.get('limit', 10))
    location = data.get('location', '')
    skills = data.get('skills', '')

    if not scrape_id or not url:
        return jsonify({'error': 'Missing parameters'}), 400

    thread = threading.Thread(
        target=run_selenium_scrape,
        args=(scrape_id, url, limit, location, skills)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'message': 'Selenium scraping started'})


def run_selenium_scrape(scrape_id, url, limit, location, skills):
    db = get_db()

    try:
        from selenium_scraper import SeleniumJobScraper
        from parser import JobParser

        filters = {
            'skills': skills.split(',') if skills else [],
            'location': location if location else None
        }

        db.update_scrape_status(scrape_id, message='Starting Selenium scraper...')

        scraper = SeleniumJobScraper(base_url=url, limit=limit, filters=filters)
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
                import boto3
                lambda_client = boto3.client('lambda')
                analysis_fn = os.environ.get('ANALYSIS_LAMBDA_NAME', 'jobscraper-analysis')
                lambda_client.invoke(
                    FunctionName=analysis_fn,
                    InvocationType='Event',
                    Payload=json.dumps({'scrape_id': scrape_id})
                )
            except Exception as e:
                logger.error(f"Failed to invoke analysis Lambda: {e}")
                db.update_scrape_status(
                    scrape_id,
                    status='complete',
                    message=f'Added {jobs_added} jobs (similarity analysis unavailable)'
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
        logger.error(f"Selenium scrape error: {str(e)}")
        db.update_scrape_status(scrape_id, status='error', message=f'Error: {str(e)}')


if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
