from bs4 import BeautifulSoup
import re
from typing import Dict, Optional
from urllib.parse import urlparse
from datetime import datetime, timedelta

class JobParser:
    def __init__(self):
        self.common_skills = [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go', 'rust', 'php',
            'react', 'angular', 'vue', 'node', 'django', 'flask', 'spring', 'express',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins',
            'sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'git', 'linux', 'bash', 'ci/cd', 'agile', 'scrum',
            'machine learning', 'deep learning', 'ai', 'nlp', 'computer vision',
            'rest', 'graphql', 'api', 'microservices', 'distributed systems',
            'html', 'css', 'sass', 'webpack', 'babel',
            'pytest', 'junit', 'jest', 'selenium', 'cypress',
            'spark', 'hadoop', 'kafka', 'airflow', 'pandas', 'numpy'
        ]

        self.employment_types = ['full-time', 'part-time', 'contract', 'internship', 'temporary']
        self.experience_levels = ['entry', 'junior', 'mid', 'senior', 'lead', 'principal', 'staff']

    def parse_job(self, html: str, url: str, title: str, date_scraped: str = None) -> Dict:
        soup = BeautifulSoup(html, 'html.parser')

        company = self.extract_company(soup, url)
        location = self.extract_location(soup)
        description = self.extract_description(soup)

        pay_min, pay_max, pay_currency, pay_period = self.extract_pay_range(soup, description)

        skills_required, skills_optional = self.extract_skills(soup, description)

        employment_type = self.extract_employment_type(soup, description)
        experience_level = self.extract_experience_level(soup, description, title)
        years_experience = self.extract_years_experience(soup, description, title)
        date_posted = self.extract_date_posted(soup, description)

        if date_scraped is None:
            date_scraped = datetime.now().isoformat()

        return {
            'url': url,
            'title': title,
            'company': company,
            'location': location,
            'description': description,
            'pay_min': pay_min,
            'pay_max': pay_max,
            'pay_currency': pay_currency,
            'pay_period': pay_period,
            'employment_type': employment_type,
            'experience_level': experience_level,
            'years_experience': years_experience,
            'date_posted': date_posted,
            'date_scraped': date_scraped,
            'skills_required': skills_required,
            'skills_optional': skills_optional,
            'raw_html': html
        }

    def extract_company(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        if 'greenhouse.io' in url:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split('/') if p]
            if path_parts:
                company = path_parts[0].replace('-', ' ').title()
                return company

        if 'myworkdayjobs.com' in url:
            domain_match = re.search(r'([a-zA-Z0-9-]+)\.wd\d+\.myworkdayjobs\.com', url)
            if domain_match:
                company = domain_match.group(1).replace('-', ' ').title()
                return company

        if 'jobs.lever.co' in url:
            path_match = re.search(r'jobs\.lever\.co/([^/?]+)', url)
            if path_match:
                company = path_match.group(1).replace('-', ' ').title()
                return company

        company_selectors = [
            {'name': 'meta', 'attrs': {'property': 'og:site_name'}},
            {'name': 'meta', 'attrs': {'name': 'company'}},
            {'class': re.compile(r'company', re.I)},
            {'class': re.compile(r'employer', re.I)},
            {'itemprop': 'hiringOrganization'},
        ]

        for selector in company_selectors:
            elements = soup.find_all(**selector)
            for elem in elements:
                if elem.name == 'meta':
                    company = elem.get('content', '').strip()
                else:
                    company = elem.get_text(strip=True)

                if company and len(company) < 100:
                    return company

        domain = urlparse(url).netloc
        if domain:
            parts = domain.split('.')
            if len(parts) >= 2:
                company = parts[-2].capitalize()
                return company

        return None

    def extract_location(self, soup: BeautifulSoup) -> Optional[str]:
        location_selectors = [
            {'class': re.compile(r'location', re.I)},
            {'itemprop': 'jobLocation'},
            {'class': re.compile(r'address', re.I)},
            {'name': 'meta', 'attrs': {'property': 'og:locality'}},
        ]

        for selector in location_selectors:
            elements = soup.find_all(**selector, limit=5)
            for elem in elements:
                if elem.name == 'meta':
                    location = elem.get('content', '').strip()
                else:
                    location = elem.get_text(strip=True)

                if location and 5 < len(location) < 100:
                    return location

        return None

    def extract_description(self, soup: BeautifulSoup) -> str:
        description_selectors = [
            {'class': re.compile(r'description', re.I)},
            {'class': re.compile(r'job-detail', re.I)},
            {'itemprop': 'description'},
            {'id': re.compile(r'description', re.I)},
            {'role': 'main'},
            {'name': 'main'},
        ]

        for selector in description_selectors:
            elem = soup.find(**selector)
            if elem:
                text = elem.get_text(separator=' ', strip=True)
                if len(text) > 100:
                    return text

        body = soup.find('body')
        if body:
            return body.get_text(separator=' ', strip=True)

        return soup.get_text(separator=' ', strip=True)

    def extract_pay_range(self, _soup: BeautifulSoup, description: str) -> tuple:
        hourly_patterns = [
            r'\$\s*(\d{1,3}(?:\.\d{2})?)\s*/\s*hr\s+.*?up to\s+\$\s*(\d{1,3}(?:\.\d{2})?)\s*/\s*hr',
            r'\$\s*(\d{1,3}(?:\.\d{2})?)\s*/\s*hr\s*-\s*\$\s*(\d{1,3}(?:\.\d{2})?)\s*/\s*hr',
            r'\$\s*(\d{1,3}(?:\.\d{2})?)\s*/\s*hour\s*-\s*\$\s*(\d{1,3}(?:\.\d{2})?)\s*/\s*hour',
            r'\$\s*(\d{1,3}(?:\.\d{2})?)\s+per hour\s*-\s*\$\s*(\d{1,3}(?:\.\d{2})?)\s+per hour',
            r'(\d{1,3}(?:\.\d{2})?)\s*-\s*(\d{1,3}(?:\.\d{2})?)\s+(?:USD|usd)?\s*/\s*(?:hr|hour)',
        ]

        annual_patterns = [
            r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*-\s*\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*)\s*-\s*(\d{1,3}(?:,\d{3})*)\s*(?:USD|usd|\$)',
            r'salary.*?(\d{1,3}(?:,\d{3})*)\s*-\s*(\d{1,3}(?:,\d{3})*)',
        ]

        text = description[:5000]

        for pattern in hourly_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    pay_min = float(match.group(1).replace(',', ''))
                    pay_max = float(match.group(2).replace(',', ''))

                    if pay_min < pay_max and pay_min >= 10:
                        return pay_min, pay_max, 'USD', 'hour'
                except:
                    continue

        for pattern in annual_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    pay_min = float(match.group(1).replace(',', ''))
                    pay_max = float(match.group(2).replace(',', ''))

                    if pay_min < pay_max and pay_min >= 1000:
                        return pay_min, pay_max, 'USD', 'year'
                except:
                    continue

        return None, None, None, None

    def extract_skills(self, soup: BeautifulSoup, description: str) -> tuple:
        text_lower = description.lower()

        skills_section = None

        lever_requirements = soup.find(class_='posting-requirements plain-list')
        if lever_requirements:
            skills_section = lever_requirements.get_text(separator=' ', strip=True).lower()

        if not skills_section:
            skill_headers = ['required skills', 'qualifications', 'requirements', 'must have', 'technical skills']

            for header in skill_headers:
                header_elem = soup.find(string=re.compile(header, re.I))
                if header_elem:
                    parent = header_elem.find_parent(['div', 'section', 'ul', 'ol'])
                    if parent:
                        skills_section = parent.get_text(separator=' ', strip=True).lower()
                        break

        if not skills_section:
            skills_section = text_lower[:3000]

        found_skills = []
        for skill in self.common_skills:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, skills_section):
                found_skills.append(skill)

        required_keywords = ['required', 'must', 'minimum', 'essential']
        optional_keywords = ['preferred', 'nice to have', 'bonus', 'plus']

        skills_required = []
        skills_optional = []

        for skill in found_skills:
            skill_context = self._get_skill_context(text_lower, skill)

            if any(keyword in skill_context for keyword in required_keywords):
                skills_required.append(skill)
            elif any(keyword in skill_context for keyword in optional_keywords):
                skills_optional.append(skill)
            else:
                skills_required.append(skill)

        return skills_required, skills_optional

    def _get_skill_context(self, text: str, skill: str, window: int = 100) -> str:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        match = re.search(pattern, text)

        if match:
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            return text[start:end]

        return ''

    def extract_employment_type(self, _soup: BeautifulSoup, description: str) -> Optional[str]:
        text_lower = description.lower()

        for emp_type in self.employment_types:
            if emp_type in text_lower:
                return emp_type

        return None

    def extract_experience_level(self, _soup: BeautifulSoup, description: str, title: str) -> Optional[str]:
        combined_text = (title + ' ' + description).lower()

        for level in self.experience_levels:
            if level in combined_text:
                return level

        years_match = re.search(r'(\d+)\+?\s*years?', combined_text)
        if years_match:
            years = int(years_match.group(1))
            if years == 0:
                return 'entry'
            elif years <= 2:
                return 'junior'
            elif years <= 5:
                return 'mid'
            elif years <= 8:
                return 'senior'
            else:
                return 'lead'

        return None

    def extract_years_experience(self, _soup: BeautifulSoup, description: str, title: str) -> Optional[int]:
        """Extract years of experience required - returns the maximum found"""
        combined_text = (title + ' ' + description).lower()

        patterns = [
            r'(\d+)\+?\s*(?:to|-)\s*(\d+)\s*years?',  # "3-5 years" or "3 to 5 years"
            r'minimum\s+(?:of\s+)?(\d+)\s*years?',     # "minimum 3 years" or "minimum of 3 years"
            r'at least\s+(\d+)\s*years?',              # "at least 2 years"
            r'(\d+)\+\s*years?',                       # "5+ years"
            r'(\d+)\s*years?\s+(?:of\s+)?experience', # "3 years experience"
        ]

        all_years = []

        for pattern in patterns:
            for match in re.finditer(pattern, combined_text):
                if match.lastindex >= 2:
                    all_years.append(int(match.group(2)))
                else:
                    all_years.append(int(match.group(1)))

        return max(all_years) if all_years else None

    def extract_date_posted(self, soup: BeautifulSoup, description: str) -> Optional[str]:
        """Extract the date the job was posted"""
        date_selectors = [
            {'class': re.compile(r'posted|date', re.I)},
            {'itemprop': 'datePosted'},
            {'name': 'meta', 'attrs': {'property': 'article:published_time'}},
            {'name': 'time'},
        ]

        for selector in date_selectors:
            elements = soup.find_all(**selector, limit=5)
            for elem in elements:
                if elem.name == 'meta':
                    date_str = elem.get('content', '').strip()
                elif elem.name == 'time':
                    date_str = elem.get('datetime', elem.get_text(strip=True))
                else:
                    date_str = elem.get_text(strip=True)

                if date_str and len(date_str) < 50:
                    try:
                        if 'T' in date_str or '-' in date_str:
                            parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            return parsed_date.date().isoformat()
                    except:
                        pass

                    relative_match = re.search(r'(\d+)\s+(day|week|month)s?\s+ago', date_str, re.I)
                    if relative_match:
                        amount = int(relative_match.group(1))
                        unit = relative_match.group(2).lower()

                        today = datetime.now()
                        if unit == 'day':
                            posted_date = today - timedelta(days=amount)
                        elif unit == 'week':
                            posted_date = today - timedelta(weeks=amount)
                        elif unit == 'month':
                            posted_date = today - timedelta(days=amount * 30)
                        else:
                            continue

                        return posted_date.date().isoformat()

        date_patterns = [
            r'posted.*?(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, description[:1000], re.I)
            if match:
                date_str = match.group(1) if match.lastindex == 1 else match.group(0)
                try:
                    if '/' in date_str:
                        parsed_date = datetime.strptime(date_str, '%m/%d/%Y')
                    elif '-' in date_str:
                        parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                    else:
                        for fmt in ['%b %d, %Y', '%B %d, %Y', '%b %d %Y', '%B %d %Y']:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt)
                                break
                            except:
                                continue
                        else:
                            continue
                    return parsed_date.date().isoformat()
                except:
                    continue

        return None
