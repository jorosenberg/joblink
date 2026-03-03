from flask import Flask, render_template, jsonify, request
from database import JobDatabase
from scraper import JobScraper
from parser import JobParser
from analysis import JobSimilarityAnalyzer
import threading

app = Flask(__name__)

scraping_status = {
    'is_running': False,
    'progress': 0,
    'total': 0,
    'current_job': '',
    'message': 'Ready to scrape',
    'jobs_added': 0,
    'duplicates_skipped': 0
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/jobs')
def get_jobs():
    skills_filter = request.args.get('skills', '').lower().split(',') if request.args.get('skills') else []
    location_filter = request.args.get('location', '').lower()
    pay_min_filter = float(request.args.get('pay_min', 0))
    pay_max_filter = float(request.args.get('pay_max', 0))
    years_min_filter = int(request.args.get('years_min', 0)) if request.args.get('years_min') else None
    years_max_filter = int(request.args.get('years_max', 0)) if request.args.get('years_max') else None

    with JobDatabase() as db:
        jobs = db.get_all_jobs()

        jobs_list = []
        for job in jobs:
            if skills_filter and skills_filter[0]:
                job_skills = [s.lower() for s in job.get('skills_required', []) + job.get('skills_optional', [])]
                if not any(skill.strip() in ' '.join(job_skills) for skill in skills_filter if skill.strip()):
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
                'date_scraped': job.get('date_scraped'),
                'skills_required': job.get('skills_required', []),
                'skills_optional': job.get('skills_optional', []),
                'url': job['url']
            })

        return jsonify(jobs_list)

@app.route('/api/job/<int:job_id>')
def get_job(job_id):
    with JobDatabase() as db:
        job = db.get_job(job_id)

        if not job:
            return jsonify({'error': 'Job not found'}), 404

        similar_jobs = db.get_similar_jobs(job_id, top_n=10)

        return jsonify({
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
                'date_scraped': job.get('date_scraped'),
                'skills_required': job.get('skills_required', []),
                'skills_optional': job.get('skills_optional', []),
                'url': job['url'],
                'description': job.get('description', '')[:500]
            },
            'similar_jobs': [
                {
                    'id': similar_id,
                    'title': title,
                    'similarity': score
                }
                for similar_id, title, score in similar_jobs
            ]
        })

@app.route('/api/graph')
def get_graph():
    with JobDatabase() as db:
        jobs = db.get_all_jobs()

        nodes = []
        for job in jobs:
            nodes.append({
                'id': job['id'],
                'label': job['title'],
                'company': job.get('company', 'Unknown'),
                'title': f"{job['title']}\n{job.get('company', 'Unknown')}"
            })

        db.cursor.execute('''
            SELECT job_id_1, job_id_2, similarity_score
            FROM job_similarities
            WHERE similarity_score > 0.5
            ORDER BY similarity_score DESC
        ''')

        edges = []
        for row in db.cursor.fetchall():
            edges.append({
                'from': row[0],
                'to': row[1],
                'value': row[2],
                'title': f"Similarity: {row[2]:.3f}"
            })

        return jsonify({
            'nodes': nodes,
            'edges': edges
        })

def run_scraper_job(url, limit, location, skills):
    """Background task for scraping"""
    global scraping_status

    try:
        scraping_status['is_running'] = True
        scraping_status['message'] = 'Starting scraper...'
        scraping_status['total'] = limit
        scraping_status['progress'] = 0
        scraping_status['jobs_added'] = 0
        scraping_status['duplicates_skipped'] = 0

        filters = {
            'skills': skills.split(',') if skills else [],
            'location': location if location else None
        }
        scraper = JobScraper(base_url=url, limit=limit, filters=filters)
        parser = JobParser()

        scraping_status['message'] = 'Scraping job pages...'
        job_pages = scraper.scrape()

        scraping_status['message'] = 'Parsing job details...'
        from datetime import datetime
        date_scraped = datetime.now().isoformat()

        company_name = None
        with JobDatabase() as db:
            for i, job in enumerate(job_pages):
                if scraping_status['jobs_added'] >= limit:
                    remaining = len(job_pages) - i
                    if remaining > 0:
                        scraping_status['message'] = f'Target reached: added {limit} new jobs ({remaining} remaining jobs not processed)'
                    break

                scraping_status['current_job'] = job['title']
                scraping_status['progress'] = i + 1

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
                    scraping_status['jobs_added'] += 1
                else:
                    scraping_status['duplicates_skipped'] += 1

            scraping_status['message'] = 'Computing job similarities...'
            if scraping_status['jobs_added'] >= 2:
                analyzer = JobSimilarityAnalyzer()
                analyzer.compute_all_similarities(db)

            if scraping_status['jobs_added'] > 0 and company_name:
                db.save_job_board(company_name, url, scraping_status['jobs_added'])

        total_processed = scraping_status['jobs_added'] + scraping_status['duplicates_skipped']

        message_parts = [f'Complete! Added {scraping_status["jobs_added"]} new jobs']
        if scraping_status['jobs_added'] < limit:
            message_parts[0] = f'Complete! Added {scraping_status["jobs_added"]}/{limit} jobs (no more available)'
        if scraping_status['duplicates_skipped'] > 0:
            message_parts.append(f'{scraping_status["duplicates_skipped"]} duplicates skipped')
        scraping_status['message'] = ', '.join(message_parts)
        scraping_status['is_running'] = False

    except Exception as e:
        scraping_status['message'] = f'Error: {str(e)}'
        scraping_status['is_running'] = False

@app.route('/api/scrape', methods=['POST'])
def start_scrape():
    global scraping_status

    if scraping_status['is_running']:
        return jsonify({'error': 'Scraping already in progress'}), 400

    data = request.json
    url = data.get('url', '')
    limit = int(data.get('limit', 10))
    location = data.get('location', '')
    skills = data.get('skills', '')

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    thread = threading.Thread(target=run_scraper_job, args=(url, limit, location, skills))
    thread.daemon = True
    thread.start()

    return jsonify({'message': 'Scraping started'})

@app.route('/api/scrape/status')
def get_scrape_status():
    return jsonify(scraping_status)

@app.route('/api/job-boards')
def get_job_boards():
    """Get all saved job boards"""
    with JobDatabase() as db:
        boards = db.get_all_job_boards()
        return jsonify(boards)

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
