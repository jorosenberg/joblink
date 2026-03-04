from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger()


class JobScraper:
    def __init__(self, base_url, limit=10, filters=None):
        self.base_url = base_url
        self.limit = limit
        self.filters = filters or {}
        self.skills = [s.strip().lower() for s in self.filters.get('skills', [])]
        self.location = self.filters.get('location', '').strip() if self.filters.get('location') else None
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
            logger.info(f"Fetching {url[:80]}...")
            response = self.session.get(url, headers=self.headers, impersonate="chrome110")
            response.raise_for_status()
            logger.info(f"Received {len(response.text):,} bytes")
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch {url[:80]}: {e}")
            return None

    def parse_greenhouse_board(self, html_content):
        next_page = False
        soup = BeautifulSoup(html_content, 'html.parser')
        company_match = re.search(r'greenhouse\.io/([^/?]+)', self.base_url)
        if not company_match:
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
                    job_data.append({'title': title, 'url': full_url})
    
        if soup.find('button', attrs={'aria-label': 'Next page', 'aria-disabled': 'false'}): next_page = True

        return job_data, next_page

    def parse_lever_board(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        parsed_url = urlparse(self.base_url)
        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

        company_match = re.search(r'jobs\.lever\.co/([^/?]+)', self.base_url)
        company = company_match.group(1) if company_match else None

        all_links = soup.find_all('a', href=True)
        job_data = []
        seen_urls = set()

        for link_tag in all_links:
            href = link_tag.get('href')
            is_job_url = False

            if company and href.startswith(f'/{company}/') and len(href) > len(f'/{company}/') + 10:
                is_job_url = True

            uuid_pattern = r'/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
            if re.search(uuid_pattern, href.lower()):
                is_job_url = True

            if not is_job_url:
                continue

            if href.startswith('http'):
                full_url = href
            elif href.startswith('/'):
                full_url = f"{base_domain}{href}"
            else:
                continue

            if 'jobs.lever.co' not in full_url:
                continue

            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            title = link_tag.get_text(strip=True)
            if title and full_url and len(title) > 3:
                job_data.append({'title': title, 'url': full_url})

        return job_data

    def build_search_url(self):
        search_url = self.base_url
        params = []

        is_lever = 'jobs.lever.co' in self.base_url.lower()
        if is_lever:
            return search_url

        if self.skills and self.skills != ['']:
            keyword = '+'.join(self.skills)
            params.append(f"keyword={keyword}")

        if self.location:
            location_encoded = self.location.replace(' ', '+')
            params.append(f"location={location_encoded}")

        if params:
            separator = '&' if '?' in self.base_url else '?'
            search_url = f"{self.base_url}{separator}{'&'.join(params)}"
            if not is_lever:
                search_url += "&page=1"

        return search_url

    def scrape(self):
        is_greenhouse = "greenhouse.io" in self.base_url.lower()
        is_lever = "jobs.lever.co" in self.base_url.lower()

        if not is_greenhouse and not is_lever:
            logger.error(f"Unsupported URL for Lambda scraping: {self.base_url}")
            return []

        search_url = self.build_search_url()
        logger.info(f"Fetching job board: {search_url}")
        html_content = self.fetch_page(search_url)

        if not html_content:
            return []

        if is_lever:
            jobs = self.parse_lever_board(html_content)
        else:
            jobs = []
            next_page = True
            while next_page:
                jobs_page, next_page = self.parse_greenhouse_board(html_content)
                jobs.extend(jobs_page)
                logger.info("Fetching next page of Greenhouse board...")
                page_number = search_url[-1]
                search_url = f"{search_url[:-1]}{int(page_number) + 1}"
                html_content = self.fetch_page(search_url)

        logger.info(f"Found {len(jobs)} jobs")

        self.job_links = [job['url'] for job in jobs]

        if not jobs:
            return []

        logger.info(f"Fetching {len(jobs)} job pages...")
        for i, job in enumerate(jobs, 1):
            logger.info(f"[{i}/{len(jobs)}] {job['title']}")
            job_html = self.fetch_page(job['url'])
            if job_html:
                self.job_pages.append({
                    'url': job['url'],
                    'title': job['title'],
                    'html': job_html
                })

        logger.info(f"Successfully scraped {len(self.job_pages)} job pages")
        return self.job_pages
