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

    def fetch_page(self, url, indent=1):
        indent_str = "    " * indent
        try:
            print(f"{indent_str}Connecting to {url[:80]}...")
            response = self.session.get(url, headers=self.headers, impersonate="chrome110")

            print(f"{indent_str}[OK] Connected (Status: {response.status_code})")

            response.raise_for_status()

            content_length = len(response.text)
            print(f"{indent_str}[OK] Received {content_length:,} bytes")

            return response.text
        except Exception as e:
            print(f"{indent_str}[FAIL] Connection failed: {e}")
            return None

    def parse_greenhouse_board(self, html_content):
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
                job_data.append({
                    'title': title,
                    'url': full_url
                })

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

        return search_url

    def scrape(self):
        is_greenhouse = "greenhouse.io" in self.base_url.lower()
        is_lever = "jobs.lever.co" in self.base_url.lower()

        if not is_greenhouse and not is_lever:
            print("Not a greenhouse.io or Lever URL, using Selenium scraper...")
            from selenium_scraper import SeleniumJobScraper

            selenium_scraper = SeleniumJobScraper(
                base_url=self.base_url,
                limit=self.limit,
                filters=self.filters
            )
            return selenium_scraper.scrape()

        if is_lever:
            board_type = "Lever"
        else:
            board_type = "Greenhouse.io"
        print(f"Detected {board_type} job board, using fast HTTP scraper...")

        search_url = self.build_search_url()

        filter_info = []
        if self.skills and self.skills != ['']:
            if is_lever:
                filter_info.append(f"keywords: {self.skills} (will filter during parsing)")
            else:
                filter_info.append(f"keywords: {self.skills}")
        if self.location:
            filter_info.append(f"location: {self.location}")

        filter_str = ', '.join(filter_info) if filter_info else 'no filters'
        print(f"[2] Fetching job board with {filter_str}")
        print(f"    URL: {search_url}")
        html_content = self.fetch_page(search_url, indent=1)

        if not html_content:
            print("Failed to fetch job board")
            return []

        print("[3] Parsing job listings...")
        if is_lever:
            jobs = self.parse_lever_board(html_content)
        else:
            jobs = self.parse_greenhouse_board(html_content)

        if is_lever and not self.skills:
            print(f"    Found {len(jobs)} jobs (Lever has no search - all jobs scraped)")
        else:
            print(f"    Found {len(jobs)} jobs")

        jobs_to_scrape = jobs
        self.job_links = [job['url'] for job in jobs_to_scrape]

        if len(jobs_to_scrape) == 0:
            print("[!] No jobs found to scrape")
            return []

        print(f"[4] Fetching {len(jobs_to_scrape)} job pages (will add {self.limit} new jobs or until exhausted)...")
        for i, job in enumerate(jobs_to_scrape, 1):
            print(f"    [{i}/{len(jobs_to_scrape)}] {job['title']}")
            job_html = self.fetch_page(job['url'], indent=2)
            if job_html:
                self.job_pages.append({
                    'url': job['url'],
                    'title': job['title'],
                    'html': job_html
                })

        print(f"[5] Successfully scraped {len(self.job_pages)} job pages")
        print(f"    Processing will continue until {self.limit} new jobs are added or all pages are processed")
        return self.job_pages
