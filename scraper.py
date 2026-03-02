from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlencode, urlparse, parse_qs

class JobScraper:
    def __init__(self, base_url, limit=10, filters=None):
        self.base_url = base_url
        self.limit = limit
        self.filters = filters or {}
        self.skills = [s.strip().lower() for s in self.filters.get('skills', [])]
        self.session = cffi_requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
        }
        self.session.headers.update(self.headers)
        self.job_links = []
        self.job_pages = []

    def fetch_page(self, url):
        try:
            response = self.session.get(url, headers=self.headers, impersonate="chrome110")
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def parse_job_board(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')

        company_match = re.search(r'greenhouse\.io/([^/?]+)', self.base_url)
        if not company_match:
            print("Could not extract company name from URL")
            return []

        company = company_match.group(1)

        all_links = soup.find_all('a', href=True)

        job_data = []
        seen_urls = set()

        for link_tag in all_links:
            href = link_tag.get('href')

            job_match = re.search(r'/jobs/(\d+)', href)

            if job_match:
                job_id = job_match.group(1)

                if href.startswith('http'):
                    full_url = href
                else:
                    full_url = f"https://job-boards.greenhouse.io/{company}/jobs/{job_id}"

                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                title = link_tag.get_text(strip=True)

                if title and full_url:
                    job_data.append({
                        'title': title,
                        'url': full_url
                    })

        return job_data

    def build_search_url(self):
        if not self.skills or self.skills == ['']:
            return self.base_url

        keyword = '+'.join(self.skills)

        separator = '&' if '?' in self.base_url else '?'
        search_url = f"{self.base_url}{separator}keyword={keyword}"

        return search_url

    def scrape(self):
        search_url = self.build_search_url()

        print(f"[2] Fetching job board with keywords: {self.skills}")
        print(f"    URL: {search_url}")
        html_content = self.fetch_page(search_url)

        if not html_content:
            print("Failed to fetch job board")
            return []

        print("[3] Parsing job listings...")
        jobs = self.parse_job_board(html_content)
        print(f"    Found {len(jobs)} jobs matching keywords")

        jobs_to_scrape = jobs[:self.limit]
        self.job_links = [job['url'] for job in jobs_to_scrape]

        print(f"[4] Fetching {len(jobs_to_scrape)} job pages...")
        for i, job in enumerate(jobs_to_scrape, 1):
            print(f"    [{i}/{len(jobs_to_scrape)}] {job['title']}")
            job_html = self.fetch_page(job['url'])
            if job_html:
                self.job_pages.append({
                    'url': job['url'],
                    'title': job['title'],
                    'html': job_html
                })

        print(f"[5] Successfully scraped {len(self.job_pages)} job pages")
        return self.job_pages
