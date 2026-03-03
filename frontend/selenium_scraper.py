from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from urllib.parse import urlparse, quote
import time


class SeleniumJobScraper:
    def __init__(self, base_url, limit=10, filters=None):
        self.base_url = base_url
        self.limit = limit
        self.filters = filters or {}
        self.skills = [s.strip() for s in self.filters.get('skills', [])]
        self.location = self.filters.get('location', '').strip() if self.filters.get('location') else None
        self.job_links = []
        self.job_pages = []
        self.keyword_found = None

        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--window-size=1920,1080')  # Large viewport to show d-md-block elements
        self.options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36')

    def dismiss_cookie_popup(self, driver):
        print("[2] Checking for cookie/consent popups...")

        cookie_selectors = [
            "//button[contains(translate(., 'ACCEPT', 'accept'), 'accept')]",
            "//button[contains(translate(., 'AGREE', 'agree'), 'agree')]",
            "//button[contains(translate(., 'CONSENT', 'consent'), 'consent')]",
            "//button[contains(translate(., 'OK', 'ok'), 'ok')]",
            "//button[contains(translate(., 'ALLOW', 'allow'), 'allow')]",
            "//button[contains(translate(., 'CONTINUE', 'continue'), 'continue')]",
            "//a[contains(translate(., 'ACCEPT', 'accept'), 'accept')]",
            "//a[contains(translate(., 'AGREE', 'agree'), 'agree')]",
            "//button[contains(@id, 'accept')]",
            "//button[contains(@id, 'consent')]",
            "//button[contains(@class, 'accept')]",
            "//button[contains(@class, 'consent')]",
            "//button[contains(@class, 'cookie')]",
            "//div[contains(@class, 'cookie')]//button",
            "//div[contains(@id, 'cookie')]//button",
            "//div[contains(@class, 'consent')]//button",
            "//div[contains(@id, 'consent')]//button",
        ]

        for selector in cookie_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(0.3)
                            element.click()
                            print("    Dismissed cookie popup")
                            time.sleep(1)
                            return True
                        except:
                            try:
                                driver.execute_script("arguments[0].click();", element)
                                print("    Dismissed cookie popup (JS click)")
                                time.sleep(1)
                                return True
                            except:
                                continue
            except:
                continue

        print("    No cookie popup found or already dismissed")
        return False

    def find_search_input(self, driver):
        print("[3] Looking for search input field...")

        search_keywords = ['search', 'software engineering', 'keyword', 'find', 'job title', 'skills']
        exclude_keywords = ['scroll', 'pagination', 'results', 'page', 'filter', 'location', 'city', 'place', 'where', 'area', 'region']

        try:
            inputs = driver.find_elements(By.TAG_NAME, 'input')

            for input_elem in inputs:
                name = input_elem.get_attribute('name') or ''
                element_id = input_elem.get_attribute('id') or ''
                element_class = input_elem.get_attribute('class') or ''
                placeholder = input_elem.get_attribute('placeholder') or ''

                combined = (name + ' ' + element_id + ' ' + element_class + ' ' + placeholder).lower()
                if any(exclude in combined for exclude in ['location', 'city', 'place', 'where', 'area', 'region']):
                    continue

                if any(exclude in name.lower() or exclude in element_id.lower() for exclude in ['scroll', 'pagination', 'results', 'page', 'filter']):
                    continue

                input_type = input_elem.get_attribute('type')
                if input_type and input_type.lower() == 'search':
                    print(f"    Found input with type='search' (id: '{element_id or name}')")
                    return input_elem

            for input_elem in inputs:
                name = input_elem.get_attribute('name') or ''
                element_id = input_elem.get_attribute('id') or ''
                element_class = input_elem.get_attribute('class') or ''
                placeholder = input_elem.get_attribute('placeholder') or ''

                combined = (name + ' ' + element_id + ' ' + element_class + ' ' + placeholder).lower()
                if any(exclude in combined for exclude in ['location', 'city', 'place', 'where', 'area', 'region']):
                    continue

                if any(exclude in name.lower() or exclude in element_id.lower() for exclude in ['scroll', 'pagination', 'results', 'page', 'filter']):
                    continue

                if 'search' in element_class.lower() and ('keyword' in element_class.lower() or 'input' in element_class.lower() or 'field' in element_class.lower()):
                    print(f"    Found input with search class: '{element_class}'")
                    return input_elem

            for input_elem in inputs:
                name = input_elem.get_attribute('name') or ''
                element_id = input_elem.get_attribute('id') or ''
                placeholder = input_elem.get_attribute('placeholder') or ''
                element_class = input_elem.get_attribute('class') or ''

                combined = (name + ' ' + element_id + ' ' + element_class + ' ' + placeholder).lower()
                if any(exclude in combined for exclude in ['location', 'city', 'place', 'where', 'area', 'region']):
                    continue

                if any(exclude in name.lower() or exclude in element_id.lower() for exclude in ['scroll', 'pagination', 'results', 'page', 'filter']):
                    continue

                if placeholder:
                    placeholder_lower = placeholder.lower()
                    if any(keyword in placeholder_lower for keyword in search_keywords):
                        print(f"    Found input with placeholder: '{placeholder}'")
                        return input_elem

            for input_elem in inputs:
                name = input_elem.get_attribute('name') or ''
                element_id = input_elem.get_attribute('id') or ''
                aria_label = input_elem.get_attribute('aria-label') or ''
                placeholder = input_elem.get_attribute('placeholder') or ''
                element_class = input_elem.get_attribute('class') or ''

                combined = (name + ' ' + element_id + ' ' + element_class + ' ' + placeholder + ' ' + aria_label).lower()
                if any(exclude in combined for exclude in ['location', 'city', 'place', 'where', 'area', 'region']):
                    continue

                if any(exclude in name.lower() or exclude in element_id.lower() for exclude in ['scroll', 'pagination', 'results', 'page', 'filter']):
                    continue

                if aria_label:
                    aria_label_lower = aria_label.lower()
                    if any(keyword in aria_label_lower for keyword in search_keywords):
                        print(f"    Found input with aria-label: '{aria_label}'")
                        return input_elem

            for input_elem in inputs:
                name = input_elem.get_attribute('name') or ''
                element_id = input_elem.get_attribute('id') or ''
                placeholder = input_elem.get_attribute('placeholder') or ''
                element_class = input_elem.get_attribute('class') or ''

                combined = (name + ' ' + element_id + ' ' + element_class + ' ' + placeholder).lower()
                if any(exclude in combined for exclude in ['location', 'city', 'place', 'where', 'area', 'region']):
                    continue

                if any(exclude in name.lower() or exclude in element_id.lower() for exclude in ['scroll', 'pagination', 'results', 'page', 'filter']):
                    continue

                if name:
                    name_lower = name.lower()
                    if any(keyword in name_lower for keyword in search_keywords):
                        print(f"    Found input with name: '{name}'")
                        return input_elem

            print("    No search input found")
            return None

        except Exception as e:
            print(f"    Error finding search input: {e}")
            return None

    def append_location_to_url(self, url, location_encoded):
        """Append location parameter to URL if location filter exists in URL"""
        if not location_encoded:
            return url

        location_params = ['location=', 'loc=', 'locl=', 'city=', 'where=']

        for param in location_params:
            if param in url.lower():
                if param in url:
                    base_part = url.split(param)[0]
                    after_param = url.split(param)[1]
                    if '&' in after_param:
                        rest_params = '&' + '&'.join(after_param.split('&')[1:])
                    elif '#' in after_param:
                        rest_params = '#' + '#'.join(after_param.split('#')[1:])
                    else:
                        rest_params = ''
                    return base_part + param + location_encoded + rest_params
                else:
                    base_part = url.lower().split(param)[0]
                    return base_part + param + location_encoded

        if '?' in url:
            separator = '&' if not url.endswith('?') and not url.endswith('&') else ''
            return url + separator + 'location=' + location_encoded

        return url

    def find_location_input(self, driver):
        """Find location input field. Returns None if not found (graceful handling)."""
        print("[3b] Looking for location input field...")

        location_keywords = ['location', 'city', 'place', 'where', 'area', 'region']
        exclude_keywords = ['scroll', 'pagination', 'results', 'page']

        try:
            inputs = driver.find_elements(By.TAG_NAME, 'input')

            for input_elem in inputs:
                placeholder = input_elem.get_attribute('placeholder')
                if placeholder and placeholder.lower() == 'location':
                    print(f"    Found input with placeholder='location'")
                    return input_elem

            for input_elem in inputs:
                name = input_elem.get_attribute('name') or ''
                element_id = input_elem.get_attribute('id') or ''

                if any(exclude in name.lower() or exclude in element_id.lower() for exclude in exclude_keywords):
                    continue

                placeholder = input_elem.get_attribute('placeholder')
                if placeholder:
                    placeholder_lower = placeholder.lower()
                    if any(keyword in placeholder_lower for keyword in location_keywords):
                        print(f"    Found input with placeholder: '{placeholder}'")
                        return input_elem

            for input_elem in inputs:
                name = input_elem.get_attribute('name') or ''
                element_id = input_elem.get_attribute('id') or ''

                if any(exclude in name.lower() or exclude in element_id.lower() for exclude in exclude_keywords):
                    continue

                if name:
                    name_lower = name.lower()
                    if any(keyword in name_lower for keyword in location_keywords):
                        print(f"    Found input with name: '{name}'")
                        return input_elem

                if element_id:
                    id_lower = element_id.lower()
                    if any(keyword in id_lower for keyword in location_keywords):
                        print(f"    Found input with id: '{element_id}'")
                        return input_elem

            for input_elem in inputs:
                aria_label = input_elem.get_attribute('aria-label')
                if aria_label:
                    aria_label_lower = aria_label.lower()
                    if any(keyword in aria_label_lower for keyword in location_keywords):
                        print(f"    Found input with aria-label: '{aria_label}'")
                        return input_elem

            print("    No location input found (will skip location filtering)")
            return None

        except Exception as e:
            print(f"    Error finding location input: {e} (will skip location filtering)")
            return None

    def close_popups(self, driver):
        """Detect and close common popups (resume upload, cookies, etc.)"""
        print("[Popup] Checking for popups to close...")

        try:
            dismiss_keywords = ['close', 'skip', 'dismiss', 'no thanks', 'not now', 'later', 'cancel', 'continue without', 'maybe later']

            buttons = driver.find_elements(By.TAG_NAME, 'button')

            for button in buttons:
                try:
                    button_text = button.text.lower().strip()

                    aria_label = button.get_attribute('aria-label')
                    aria_label_text = aria_label.lower() if aria_label else ''

                    title = button.get_attribute('title')
                    title_text = title.lower() if title else ''

                    combined_text = button_text + ' ' + aria_label_text + ' ' + title_text

                    if any(keyword in combined_text for keyword in dismiss_keywords):
                        if button.is_displayed() and button.is_enabled():
                            print(f"    Found popup dismiss button: '{button_text or aria_label or title}'")
                            button.click()
                            time.sleep(1)
                            print("    Popup closed successfully")
                            return True
                except Exception as e:
                    continue

            close_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '×') or contains(text(), 'X')]")
            for elem in close_elements:
                try:
                    if elem.is_displayed() and elem.is_enabled():
                        if elem.tag_name in ['button', 'a', 'span', 'div']:
                            print(f"    Found close icon ({elem.text})")
                            elem.click()
                            time.sleep(1)
                            print("    Popup closed successfully")
                            return True
                except Exception as e:
                    continue

            print("    No popups found")
            return False

        except Exception as e:
            print(f"    Error checking for popups: {e}")
            return False

    def find_pagination_button(self, driver):
        """Find the next/pagination button to navigate to the next page of results"""
        print("[Pagination] Looking for next page button...")

        next_keywords = ['next', 'siguiente', 'suivant', 'forward', 'right']
        right_indicators = ['→', '>', '»', '›']
        pagination_keywords = ['pagination', 'pager', 'page-nav']

        try:
            buttons = driver.find_elements(By.TAG_NAME, 'button') + driver.find_elements(By.TAG_NAME, 'a')

            print(f"    Checking {len(buttons)} buttons and links...")

            for button in buttons:
                try:
                    if not button.is_displayed():
                        continue

                    button_text = button.text.lower().strip()
                    if button_text and any(keyword in button_text for keyword in next_keywords + right_indicators):
                        if 'prev' not in button_text and 'back' not in button_text and '<' not in button_text and 'left' not in button_text:
                            print(f"    Found pagination button with text: '{button.text}'")
                            return button

                    aria_label = button.get_attribute('aria-label')
                    if aria_label:
                        aria_label_lower = aria_label.lower()
                        if any(keyword in aria_label_lower for keyword in next_keywords):
                            if 'prev' not in aria_label_lower and 'back' not in aria_label_lower:
                                print(f"    Found pagination button with aria-label: '{aria_label}'")
                                return button

                    data_action = button.get_attribute('data-action')
                    data_label = button.get_attribute('data-label')

                    if data_action and 'pagination' in data_action.lower():
                        button_class = button.get_attribute('class') or ''
                        if any(keyword in button_class.lower() for keyword in next_keywords + ['right']):
                            if 'left' not in button_class.lower() and 'prev' not in button_class.lower():
                                print(f"    Found pagination button with data-action='{data_action}' and class containing 'right'")
                                return button

                    if data_label and any(keyword in data_label.lower() for keyword in next_keywords + ['right']):
                        if 'left' not in (data_label or '').lower() and 'prev' not in (data_label or '').lower():
                            print(f"    Found pagination button with data-label: '{data_label}'")
                            return button

                    button_class = button.get_attribute('class') or ''
                    button_id = button.get_attribute('id') or ''
                    combined = (button_class + ' ' + button_id).lower()

                    exclude_keywords = ['filter', 'toggle', 'slider', 'dropdown', 'menu', 'modal', 'overlay', 'search-slider']
                    if any(keyword in combined for keyword in exclude_keywords):
                        continue

                    if 'right' in combined:
                        if 'left' not in combined and 'prev' not in combined:
                            if any(keyword in combined for keyword in pagination_keywords):
                                print(f"    Found pagination button with 'right' in class: '{button_class}'")
                                return button

                    if any(keyword in combined for keyword in pagination_keywords):
                        if any(keyword in combined for keyword in next_keywords):
                            print(f"    Found pagination button with class/id containing pagination keywords")
                            return button

                except Exception as btn_error:
                    continue

            pagination_containers = driver.find_elements(By.XPATH,
                "//*[contains(@class, 'pagination') or contains(@class, 'pager') or contains(@id, 'pagination')]")

            for container in pagination_containers:
                if not container.is_displayed():
                    continue

                next_buttons = container.find_elements(By.XPATH,
                    ".//*[contains(text(), 'Next') or contains(text(), 'next') or contains(text(), '→') or contains(text(), '>') or contains(@class, 'right') or contains(@aria-label, 'Next') or contains(@data-label, 'right')]")

                for btn in next_buttons:
                    try:
                        if btn.is_displayed():
                            btn_text = (btn.text or '').lower()
                            btn_class = btn.get_attribute('class') or ''
                            if 'prev' not in btn_text and 'back' not in btn_text and 'left' not in btn_class.lower():
                                print(f"    Found next button in pagination container")
                                return btn
                    except:
                        continue

            print("    No pagination button found")
            return None

        except Exception as e:
            print(f"    Error finding pagination button: {e}")
            return None

    def dismiss_autocomplete_dropdown(self, driver):
        try:
            autocomplete_selectors = [
                "//ul[contains(@class, 'ui-autocomplete')]",
                "//div[contains(@class, 'autocomplete')]",
                "//ul[contains(@class, 'autocomplete')]",
            ]

            for selector in autocomplete_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            driver.execute_script("arguments[0].style.display = 'none';", element)
                except:
                    continue
        except:
            pass

    def find_submit_button(self, driver):
        try:
            buttons = driver.find_elements(By.TAG_NAME, 'button')
            submit_inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="submit"]')

            all_submit_elements = buttons + submit_inputs

            for element in all_submit_elements:
                try:
                    button_type = element.get_attribute('type')
                    if button_type == 'submit':
                        aria_label = element.get_attribute('aria-label')
                        element_class = element.get_attribute('class') or ''

                        if aria_label and 'search' in aria_label.lower():
                            print(f"    Found type='submit' button with aria-label: '{aria_label}'")
                            return element

                        if 'search' in element_class.lower():
                            print(f"    Found type='submit' button with search in class: '{element_class}'")
                            return element
                except:
                    continue

            for element in all_submit_elements:
                data_qa = element.get_attribute('data-qa')
                if data_qa and ('search' in data_qa.lower() and ('btn' in data_qa.lower() or 'start' in data_qa.lower() or 'submit' in data_qa.lower())):
                    print(f"    Found submit button with data-qa: '{data_qa}'")
                    return element

            for element in all_submit_elements:
                element_class = element.get_attribute('class') or ''
                if 'search' in element_class.lower() and ('button' in element_class.lower() or 'btn' in element_class.lower() or 'submit' in element_class.lower()):
                    print(f"    Found submit button with class: '{element_class}'")
                    return element

            exclude_keywords = ['mode', 'menu', 'toggle', 'dropdown', 'filter', 'location']

            for element in all_submit_elements:
                aria_label = element.get_attribute('aria-label')
                if aria_label:
                    aria_lower = aria_label.lower()

                    if any(keyword in aria_lower for keyword in exclude_keywords):
                        continue

                    if aria_lower.startswith('search') or aria_lower == 'search' or 'search for' in aria_lower or 'search jobs' in aria_lower:
                        print(f"    Found submit button with aria-label: '{aria_label}'")
                        return element

            for element in all_submit_elements:
                text = element.text.strip().lower()
                if text and (text == 'search' or text.startswith('search') or 'search jobs' in text or text == 'go' or text == 'submit'):
                    print(f"    Found submit button with text: '{element.text}'")
                    return element

                value = element.get_attribute('value')
                if value and (value.lower() == 'search' or value.lower().startswith('search') or value.lower() == 'go' or value.lower() == 'submit'):
                    print(f"    Found submit button with value: '{value}'")
                    return element

            for element in all_submit_elements:
                name = element.get_attribute('name')
                if name and 'search' in name.lower() and 'submit' in name.lower():
                    print(f"    Found submit button with name: '{name}'")
                    return element

                element_id = element.get_attribute('id')
                if element_id and 'search' in element_id.lower() and ('btn' in element_id.lower() or 'submit' in element_id.lower()):
                    print(f"    Found submit button with id: '{element_id}'")
                    return element

            return None

        except Exception as e:
            print(f"    Error finding submit button: {e}")
            return None

    def find_nearest_button(self, driver, search_input):
        try:
            try:
                parent_form = search_input.find_element(By.XPATH, './ancestor::form[1]')
                buttons = parent_form.find_elements(By.TAG_NAME, 'button')
                submit_inputs = parent_form.find_elements(By.CSS_SELECTOR, 'input[type="submit"]')

                all_buttons = buttons + submit_inputs
                if all_buttons:
                    button_text = all_buttons[0].text or all_buttons[0].get_attribute('value') or 'no text'
                    print(f"    Found button in form: '{button_text}'")
                    return all_buttons[0]
            except:
                pass

            try:
                parent = search_input.find_element(By.XPATH, './ancestor::*[self::div or self::section or self::nav][1]')

                buttons = parent.find_elements(By.TAG_NAME, 'button')
                submit_inputs = parent.find_elements(By.CSS_SELECTOR, 'input[type="submit"]')

                all_buttons = buttons + submit_inputs
                if all_buttons:
                    button_text = all_buttons[0].text or all_buttons[0].get_attribute('value') or 'no text'
                    print(f"    Found button in container: '{button_text}'")
                    return all_buttons[0]
            except:
                pass

            try:
                next_button = search_input.find_element(By.XPATH, './following::button[1]')
                button_text = next_button.text or 'no text'
                print(f"    Found following button: '{button_text}'")
                return next_button
            except:
                pass

            try:
                next_submit = search_input.find_element(By.XPATH, './following::input[@type="submit"][1]')
                button_text = next_submit.get_attribute('value') or 'no text'
                print(f"    Found following submit input: '{button_text}'")
                return next_submit
            except:
                pass

            return None

        except Exception as e:
            print(f"    Error finding nearest button: {e}")
            return None

    def is_likely_job_posting(self, url_path):
        navigation_patterns = [
            '/jobs',
            '/jobs/',
            '/job',
            '/job/',
            '/careers',
            '/careers/',
            '/career',
            '/career/',
            '/jobs/search',
            '/careers/search',
            '/early-careers',
            '/internships',
            '/students',
            '/new-grad',
        ]

        url_path_normalized = url_path.rstrip('/')
        if url_path_normalized in navigation_patterns:
            return False

        segments = [s for s in url_path.split('/') if s]

        if len(segments) < 2:
            return False

        last_segment = segments[-1].lower()

        nav_keywords = ['search', 'all', 'list', 'browse', 'filter', 'results']
        if last_segment in nav_keywords:
            return False

        has_numbers = any(char.isdigit() for char in last_segment)
        has_hyphens = last_segment.count('-') >= 2
        is_long_enough = len(last_segment) > 8

        if has_numbers or (has_hyphens and is_long_enough):
            return True

        return False

    def extract_job_urls(self, driver):
        print("[5] Extracting job URLs from page...")

        job_keywords = ['job', 'jobs', 'career', 'careers', 'details']

        base_parsed = urlparse(self.base_url)
        base_domain = base_parsed.netloc.lower()
        base_path = base_parsed.path.lower()

        job_urls = []
        seen_urls = set()

        try:
            if 'netflix' in base_domain:
                print("    Detected Netflix, looking for position cards...")
                try:
                    cards = driver.find_elements(By.CSS_SELECTOR, '.position-title-container, [class*="position-card"], [id*="position-card"]')

                    if cards:
                        print(f"    Found {len(cards)} position cards")

                        for i, card in enumerate(cards):
                            try:
                                title_elem = card.find_element(By.CSS_SELECTOR, '.position-title, [class*="position-title"]')
                                title = title_elem.text.strip() if title_elem else f"Position {i+1}"

                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                                time.sleep(0.3)
                                card.click()
                                time.sleep(1)

                                current_url = driver.current_url

                                if current_url != self.base_url and '/job' in current_url.lower():
                                    if current_url not in seen_urls:
                                        seen_urls.add(current_url)
                                        job_urls.append({
                                            'url': current_url,
                                            'title': title
                                        })
                                        print(f"    ✓ Found job: {title}")

                                driver.back()
                                time.sleep(1)

                            except Exception as e:
                                print(f"    Error processing card {i+1}: {e}")
                                continue

                        if job_urls:
                            print(f"    ✓ Found {len(job_urls)} jobs from Netflix cards")
                            return job_urls
                    else:
                        print("    No Netflix position cards found, trying standard extraction...")
                except Exception as e:
                    print(f"    Netflix card extraction failed: {e}, trying standard extraction...")

            if 'google' in base_domain:
                print("    Detected Google, looking for 'Learn more' buttons...")
                try:
                    learn_more_links = driver.find_elements(By.CSS_SELECTOR, 'a[aria-label*="Learn more"]')

                    if not learn_more_links:
                        learn_more_links = driver.find_elements(By.CSS_SELECTOR, 'a[jsname="hSRGPd"]')

                    if learn_more_links:
                        print(f"    Found {len(learn_more_links)} 'Learn more' buttons")

                        for i, link in enumerate(learn_more_links):
                            try:
                                aria_label = link.get_attribute('aria-label')
                                if aria_label and 'Learn more about' in aria_label:
                                    title = aria_label.replace('Learn more about', '').strip()
                                else:
                                    title = f"Google Job {i+1}"

                                href = link.get_attribute('href')
                                if not href:
                                    continue

                                if href.startswith('/'):
                                    href = f"https://{base_domain}{href}"
                                elif not href.startswith('http'):
                                    href = f"https://{base_domain}/{href}"

                                if href not in seen_urls:
                                    seen_urls.add(href)
                                    job_urls.append({
                                        'url': href,
                                        'title': title
                                    })
                                    print(f"    ✓ Found job: {title}")

                            except Exception as e:
                                print(f"    Error processing Google link {i+1}: {e}")
                                continue

                        if job_urls:
                            print(f"    ✓ Found {len(job_urls)} jobs from Google 'Learn more' links")
                            return job_urls
                    else:
                        print("    No Google 'Learn more' buttons found, trying standard extraction...")
                except Exception as e:
                    print(f"    Google link extraction failed: {e}, trying standard extraction...")

            search_container = None
            try:
                search_container = driver.find_element(By.TAG_NAME, 'main')
                print("    Searching within <main> element")
            except:
                try:
                    search_container = driver.find_element(By.TAG_NAME, 'body')
                    print("    No <main> element found, searching within <body>")
                except:
                    print("    Searching entire page")
                    search_container = driver

            if search_container:
                links = search_container.find_elements(By.TAG_NAME, 'a')
            else:
                links = driver.find_elements(By.TAG_NAME, 'a')

            for link in links:
                href = link.get_attribute('href')
                if not href:
                    continue

                href_parsed = urlparse(href)

                if href_parsed.netloc and href_parsed.netloc.lower() != base_domain:
                    continue

                href_path = href_parsed.path.lower()

                if href.rstrip('/').lower() == self.base_url.rstrip('/').lower():
                    continue

                if not self.is_likely_job_posting(href_path):
                    continue

                if base_path:
                    common_prefix_len = 0
                    for i in range(min(len(base_path), len(href_path))):
                        if base_path[i] == href_path[i]:
                            common_prefix_len = i + 1
                        else:
                            break

                    if common_prefix_len > 0:
                        last_slash = base_path[:common_prefix_len].rfind('/')
                        if last_slash >= 0:
                            common_prefix_len = last_slash + 1

                    unique_part = href_path[common_prefix_len:]
                else:
                    unique_part = href_path

                for keyword in job_keywords:
                    if keyword in unique_part:
                        if not self.keyword_found:
                            self.keyword_found = keyword

                        if href not in seen_urls:
                            seen_urls.add(href)

                            title = link.text.strip() or "Job Posting"

                            job_urls.append({
                                'url': href,
                                'title': title
                            })
                        break

            if not job_urls:
                print("    No jobs found with path exclusion, trying simpler keyword search...")

                for link in links:
                    href = link.get_attribute('href')
                    if not href:
                        continue

                    href_parsed = urlparse(href)

                    if href_parsed.netloc and href_parsed.netloc.lower() != base_domain:
                        continue

                    if href.rstrip('/').lower() == self.base_url.rstrip('/').lower():
                        continue

                    href_path = href_parsed.path.lower()

                    if not self.is_likely_job_posting(href_path):
                        continue

                    for keyword in job_keywords:
                        if keyword in href_path:
                            if not self.keyword_found:
                                self.keyword_found = keyword

                            if href not in seen_urls:
                                seen_urls.add(href)

                                title = link.text.strip() or "Job Posting"

                                job_urls.append({
                                    'url': href,
                                    'title': title
                                })
                            break

                if job_urls:
                    print(f"    ✓ Found {len(job_urls)} job URLs with simpler keyword search")

            if not job_urls:
                print("    No jobs found with keyword search")
                print("    Trying XPath selectors as fallback...")

                xpath_selectors = [
                    '//*[@id="link_job_title_1_0_0"]',
                    '//*[contains(@id, "link_job_title")]',
                    '//*[contains(@class, "job-title")]//a',
                    '//*[contains(@class, "job-link")]',
                    '//*[contains(@class, "posting")]//a',
                    '//a[contains(@href, "/job")]',
                    '//a[contains(@href, "/position")]',
                ]

                for xpath in xpath_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, xpath)
                        if elements:
                            print(f"    Found {len(elements)} elements with XPath: {xpath}")

                            for element in elements:
                                try:
                                    href = element.get_attribute('href')
                                    if not href:
                                        continue

                                    href_parsed = urlparse(href)

                                    if href_parsed.netloc and href_parsed.netloc.lower() != base_domain:
                                        continue

                                    if href.rstrip('/').lower() == self.base_url.rstrip('/').lower():
                                        continue

                                    href_path = href_parsed.path.lower()
                                    if not self.is_likely_job_posting(href_path):
                                        continue

                                    if href not in seen_urls:
                                        seen_urls.add(href)

                                        title = element.text.strip() or "Job Posting"

                                        job_urls.append({
                                            'url': href,
                                            'title': title
                                        })
                                except:
                                    continue

                            if job_urls:
                                print(f"    ✓ Found {len(job_urls)} job URLs using XPath")
                                break
                    except:
                        continue

            print(f"    Found {len(job_urls)} job URLs")
            if self.keyword_found:
                print(f"    Using keyword: '{self.keyword_found}'")

            return job_urls

        except Exception as e:
            print(f"    Error extracting job URLs: {e}")
            return []

    def fetch_job_page(self, url):
        try:
            driver = webdriver.Chrome(options=self.options)
            driver.get(url)
            time.sleep(2)
            html_content = driver.page_source
            driver.quit()
            return html_content
        except Exception as e:
            print(f"    Error fetching {url}: {e}")
            return None

    def scrape(self):
        print(f"[1] Starting Selenium scraper for: {self.base_url}")

        driver = None
        try:
            driver = webdriver.Chrome(options=self.options)

            print(f"    Connecting to {self.base_url}...")
            driver.get(self.base_url)

            current_url = driver.current_url
            if current_url:
                print(f"    [OK] Connected successfully")
                print(f"    [OK] Page loaded: {current_url}")
            else:
                print(f"    [WARN] Connected but URL not available")

            time.sleep(3)

            self.dismiss_cookie_popup(driver)
            self.close_popups(driver)

            search_input = self.find_search_input(driver)

            if search_input:
                keyword_string = ', '.join(self.skills)
                keyword_string_encoded = quote(keyword_string)  # URL encode for direct URL manipulation
                print(f"[4] Entering keywords: {keyword_string}")
                if self.location:
                    print(f"    Location filter: {self.location}")

                search_submitted = False

                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_input)
                    time.sleep(0.3)
                    search_input.click()
                    time.sleep(0.2)
                    search_input.clear()
                    search_input.send_keys(keyword_string)
                    time.sleep(0.3)
                except Exception as e:
                    print(f"    Normal input failed: {e}, using JavaScript...")

                input_value = search_input.get_attribute('value')
                if not input_value or keyword_string not in input_value:
                    print(f"    Value not set properly (got: '{input_value}'), using JavaScript...")
                    driver.execute_script("arguments[0].value = arguments[1];", search_input, keyword_string)
                    driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", search_input)
                    time.sleep(0.3)

                location_input = None
                if self.location:
                    location_input = self.find_location_input(driver)
                    if location_input:
                        try:
                            print(f"[4b] Entering location: {self.location}")
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", location_input)
                            time.sleep(0.3)
                            location_input.click()
                            time.sleep(0.2)
                            location_input.clear()
                            location_input.send_keys(self.location)
                            time.sleep(0.3)
                        except Exception as e:
                            print(f"    Normal location input failed: {e}, using JavaScript...")

                        location_value = location_input.get_attribute('value')
                        if not location_value or self.location not in location_value:
                            print(f"    Location value not set properly, using JavaScript...")
                            driver.execute_script("arguments[0].value = arguments[1];", location_input, self.location)
                            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", location_input)
                            time.sleep(0.3)

                        print("    Location filter applied successfully")

                url_before = driver.current_url
                print(f"    [DEBUG] URL before submit: {url_before}")

                input_class = search_input.get_attribute('class')
                input_placeholder = search_input.get_attribute('placeholder')
                print(f"    [DEBUG] Using keyword input with class='{input_class}', placeholder='{input_placeholder}'")

                print("    Submitting search (pressing Enter twice)...")

                if location_input:
                    print("    Pressing Enter twice on location input...")
                    try:
                        location_input.send_keys(Keys.RETURN)
                        time.sleep(1)
                        location_input.send_keys(Keys.RETURN)
                        time.sleep(2)
                    except Exception as e:
                        print(f"    Could not press Enter on location input: {e}")
                else:
                    print("    Pressing Enter twice on keyword input...")
                    try:
                        search_input.send_keys(Keys.RETURN)
                        time.sleep(1)
                        search_input.send_keys(Keys.RETURN)
                        time.sleep(2)
                    except Exception as e:
                        print(f"    Could not press Enter on keyword input: {e}")

                time.sleep(1)

                url_after = driver.current_url
                print(f"    [DEBUG] URL after Enter: {url_after}")

                if url_before != url_after:
                    print("    Search submitted successfully via Enter key")
                    search_submitted = True
                else:
                    print("    Enter key didn't work, will look for submit button...")

                if not search_submitted:
                    current_url = driver.current_url
                    if 'search' in current_url.lower() or 'query' in current_url.lower() or 'keywords' in current_url.lower():
                        print("    Enter key didn't work, trying URL-based search...")
                        if 'base_query=' in current_url.lower():
                            if 'base_query=' in current_url:
                                search_url = current_url.split('base_query=')[0] + 'base_query=' + keyword_string_encoded
                            else:
                                search_url = current_url.split('base_query=')[0].replace('BASE_QUERY=', 'base_query=') + 'base_query=' + keyword_string_encoded

                            print(f"    Navigating to: {search_url}")
                            driver.get(search_url)
                            time.sleep(4)
                            search_submitted = True
                        elif 'query=' in current_url.lower():
                            if 'query=' in current_url:
                                search_url = current_url.split('query=')[0] + 'query=' + keyword_string_encoded
                            else:
                                search_url = current_url.split('query=')[0].replace('QUERY=', 'query=') + 'query=' + keyword_string_encoded

                            print(f"    Navigating to: {search_url}")
                            driver.get(search_url)
                            time.sleep(4)
                            search_submitted = True
                        elif 'search=' in current_url.lower():
                            if 'search=' in current_url:
                                search_url = current_url.split('search=')[0] + 'search=' + keyword_string_encoded
                            else:
                                search_url = current_url.split('search=')[0].replace('SEARCH=', 'search=') + 'search=' + keyword_string_encoded

                            print(f"    Navigating to: {search_url}")
                            driver.get(search_url)
                            time.sleep(4)
                            search_submitted = True
                        elif 'keywords=' in current_url.lower():
                            if 'keywords=' in current_url:
                                search_url = current_url.split('keywords=')[0] + 'keywords=' + keyword_string_encoded
                            else:
                                search_url = current_url.split('keywords=')[0].replace('KEYWORDS=', 'keywords=') + 'keywords=' + keyword_string_encoded

                            print(f"    Navigating to: {search_url}")
                            driver.get(search_url)
                            time.sleep(4)
                            search_submitted = True

                if not search_submitted:
                    self.dismiss_autocomplete_dropdown(driver)
                    print("    Looking for submit button...")

                    # try:
                    #     driver.save_screenshot("debug_before_button_search.png")
                    #     print("    [DEBUG] Screenshot saved: debug_before_button_search.png")
                    # except:
                    #     pass

                    submit_button = self.find_submit_button(driver)
                    if submit_button:
                        try:
                            btn_class = submit_button.get_attribute('class')
                            btn_type = submit_button.get_attribute('type')
                            btn_aria = submit_button.get_attribute('aria-label')
                            btn_text = submit_button.text
                            print(f"    [DEBUG] Button found - type='{btn_type}', class='{btn_class}', aria-label='{btn_aria}', text='{btn_text}'")
                        except:
                            pass

                        url_before_click = driver.current_url
                        print(f"    [DEBUG] URL before button click: {url_before_click}")

                        try:
                            print("    Clicking submit button...")
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
                            time.sleep(0.5)

                            # try:
                            #     driver.save_screenshot("debug_before_button_click.png")
                            #     print("    [DEBUG] Screenshot saved: debug_before_button_click.png")
                            # except:
                            #     pass

                            submit_button.click()
                            time.sleep(4)

                            url_after_click = driver.current_url
                            print(f"    [DEBUG] URL after button click: {url_after_click}")

                            try:
                                driver.save_screenshot("debug_after_button_click.png")
                                print("    [DEBUG] Screenshot saved: debug_after_button_click.png")
                            except:
                                pass

                            if url_before_click != url_after_click:
                                search_submitted = True
                                print(f"    Button click changed URL to: {url_after_click}")
                            else:
                                print("    Button clicked but URL didn't change")

                        except Exception as e:
                            print(f"    Regular click failed: {e}")
                            print("    Trying JavaScript click...")
                            try:
                                driver.execute_script("arguments[0].click();", submit_button)
                                time.sleep(4)

                                url_after_js_click = driver.current_url
                                print(f"    [DEBUG] URL after JS click: {url_after_js_click}")

                                if url_before_click != url_after_js_click:
                                    search_submitted = True
                                else:
                                    print("    JS click also didn't change URL")

                            except Exception as js_error:
                                print(f"    JavaScript click also failed: {js_error}")
                    else:
                        print("    No search submit button found, looking for nearest button...")
                        nearest_button = self.find_nearest_button(driver, search_input)
                        if nearest_button:
                            try:
                                print("    Clicking nearest button...")
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", nearest_button)
                                time.sleep(0.5)
                                nearest_button.click()
                                time.sleep(4)
                            except Exception as e:
                                print(f"    Regular click failed: {e}")
                                print("    Trying JavaScript click...")
                                try:
                                    driver.execute_script("arguments[0].click();", nearest_button)
                                    time.sleep(4)
                                except Exception as js_error:
                                    print(f"    JavaScript click also failed: {js_error}")
                        else:
                            print("    No nearby button found, continuing with current page...")

                final_url = driver.current_url
                keyword_in_url = False

                for skill in self.skills:
                    if skill.lower() in final_url.lower():
                        keyword_in_url = True
                        print(f"    ✓ Keyword '{skill}' found in URL")
                        break

                if not keyword_in_url:
                    print(f"    ⚠ Keywords not found in URL, trying direct URL manipulation...")

                    if 'base_query=' in final_url.lower():
                        print(f"    Found 'base_query=' parameter in URL")
                        if 'base_query=' in final_url:
                            base_part = final_url.split('base_query=')[0]
                            after_query = final_url.split('base_query=')[1]
                            if '&' in after_query:
                                rest_params = '&' + '&'.join(after_query.split('&')[1:])
                            elif '#' in after_query:
                                rest_params = '#' + '#'.join(after_query.split('#')[1:])
                            else:
                                rest_params = ''
                            search_url = base_part + 'base_query=' + keyword_string_encoded + rest_params
                        else:
                            base_part = final_url.lower().split('base_query=')[0]
                            search_url = base_part + 'base_query=' + keyword_string_encoded

                        print(f"    Navigating to: {search_url}")
                        driver.get(search_url)
                        time.sleep(4)
                        keyword_in_url = True

                    elif 'query=' in final_url.lower():
                        print(f"    Found 'query=' parameter in URL")
                        if 'query=' in final_url:
                            base_part = final_url.split('query=')[0]
                            after_query = final_url.split('query=')[1]
                            if '&' in after_query:
                                rest_params = '&' + '&'.join(after_query.split('&')[1:])
                            elif '#' in after_query:
                                rest_params = '#' + '#'.join(after_query.split('#')[1:])
                            else:
                                rest_params = ''
                            search_url = base_part + 'query=' + keyword_string_encoded + rest_params
                        else:
                            base_part = final_url.lower().split('query=')[0]
                            search_url = base_part + 'query=' + keyword_string_encoded

                        print(f"    Navigating to: {search_url}")
                        driver.get(search_url)
                        time.sleep(4)
                        keyword_in_url = True

                    elif 'search=' in final_url.lower():
                        print(f"    Found 'search=' parameter in URL")
                        if 'search=' in final_url:
                            base_part = final_url.split('search=')[0]
                            after_search = final_url.split('search=')[1]
                            if '&' in after_search:
                                rest_params = '&' + '&'.join(after_search.split('&')[1:])
                            elif '#' in after_search:
                                rest_params = '#' + '#'.join(after_search.split('#')[1:])
                            else:
                                rest_params = ''
                            search_url = base_part + 'search=' + keyword_string_encoded + rest_params
                        else:
                            base_part = final_url.lower().split('search=')[0]
                            search_url = base_part + 'search=' + keyword_string_encoded

                        print(f"    Navigating to: {search_url}")
                        driver.get(search_url)
                        time.sleep(4)
                        keyword_in_url = True

                    elif 'keywords=' in final_url.lower():
                        print(f"    Found 'keywords=' parameter in URL")
                        if 'keywords=' in final_url:
                            base_part = final_url.split('keywords=')[0]
                            after_keywords = final_url.split('keywords=')[1]
                            if '&' in after_keywords:
                                rest_params = '&' + '&'.join(after_keywords.split('&')[1:])
                            elif '#' in after_keywords:
                                rest_params = '#' + '#'.join(after_keywords.split('#')[1:])
                            else:
                                rest_params = ''
                            search_url = base_part + 'keywords=' + keyword_string_encoded + rest_params
                        else:
                            base_part = final_url.lower().split('keywords=')[0]
                            search_url = base_part + 'keywords=' + keyword_string_encoded

                        print(f"    Navigating to: {search_url}")
                        driver.get(search_url)
                        time.sleep(4)
                        keyword_in_url = True

                    else:
                        print(f"    No 'base_query=', 'query=', 'search=', or 'keywords=' parameter found in URL")
                        print(f"    Continuing with current page, results may not be filtered...")

                self.close_popups(driver)

                job_urls = self.extract_job_urls(driver)
            else:
                print("[4] No search input found, extracting jobs from main page...")

                self.close_popups(driver)

                job_urls = self.extract_job_urls(driver)

            all_job_urls = job_urls
            max_pages = 10  # Safety limit to prevent infinite loops
            current_page = 1

            while len(all_job_urls) < self.limit * 3 and current_page < max_pages:
                pagination_btn = self.find_pagination_button(driver)

                if not pagination_btn:
                    print(f"[Pagination] No more pages found (collected {len(all_job_urls)} jobs from {current_page} page(s))")
                    break

                try:
                    print(f"[Pagination] Navigating to page {current_page + 1}...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pagination_btn)
                    time.sleep(0.5)
                    pagination_btn.click()
                    time.sleep(3)  # Wait for page to load

                    self.close_popups(driver)

                    new_job_urls = self.extract_job_urls(driver)

                    if not new_job_urls or len(new_job_urls) == 0:
                        print("[Pagination] No jobs found on new page, stopping pagination")
                        break

                    new_unique_jobs = [job for job in new_job_urls if job['url'] not in [j['url'] for j in all_job_urls]]

                    if len(new_unique_jobs) == 0:
                        print("[Pagination] No new jobs found (duplicates), stopping pagination")
                        break

                    all_job_urls.extend(new_unique_jobs)
                    current_page += 1
                    print(f"[Pagination] Found {len(new_unique_jobs)} new jobs (total: {len(all_job_urls)})")

                except Exception as e:
                    print(f"[Pagination] Error clicking pagination button: {e}")
                    break

            jobs_to_scrape = all_job_urls[:self.limit * 3]  # Fetch 3x buffer for duplicates
            self.job_links = [job['url'] for job in jobs_to_scrape]

            print(f"[6] Fetching {len(jobs_to_scrape)} job pages from {current_page} page(s)...")

            for i, job in enumerate(jobs_to_scrape, 1):
                print(f"    [{i}/{len(jobs_to_scrape)}] {job['title']}")
                print(f"        Connecting to {job['url'][:60]}...")

                driver.get(job['url'])
                time.sleep(2)

                print(f"        [OK] Page loaded ({len(driver.page_source):,} bytes)")

                self.close_popups(driver)

                job_html = driver.page_source

                if job_html:
                    self.job_pages.append({
                        'url': job['url'],
                        'title': job['title'],
                        'html': job_html
                    })
                else:
                    print(f"        [FAIL] Failed to get page content")

            print(f"[7] Successfully scraped {len(self.job_pages)} job pages from {current_page} page(s)")

        except Exception as e:
            print(f"Error during Selenium scraping: {e}")

        finally:
            if driver:
                driver.quit()

        return self.job_pages
