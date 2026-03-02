from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException
from urllib.parse import urlparse
import time


class SeleniumJobScraper:
    def __init__(self, base_url, limit=10, filters=None):
        self.base_url = base_url
        self.limit = limit
        self.filters = filters or {}
        self.skills = [s.strip() for s in self.filters.get('skills', [])]
        self.job_links = []
        self.job_pages = []
        self.keyword_found = None

        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
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
        exclude_keywords = ['scroll', 'pagination', 'results', 'page', 'filter']

        try:
            inputs = driver.find_elements(By.TAG_NAME, 'input')

            for input_elem in inputs:
                name = input_elem.get_attribute('name') or ''
                element_id = input_elem.get_attribute('id') or ''
                element_class = input_elem.get_attribute('class') or ''

                if any(exclude in name.lower() or exclude in element_id.lower() for exclude in exclude_keywords):
                    continue

                input_type = input_elem.get_attribute('type')
                if input_type and input_type.lower() == 'search':
                    print(f"    Found input with type='search' (id: '{element_id or name}')")
                    return input_elem

            for input_elem in inputs:
                name = input_elem.get_attribute('name') or ''
                element_id = input_elem.get_attribute('id') or ''

                if any(exclude in name.lower() or exclude in element_id.lower() for exclude in exclude_keywords):
                    continue

                element_class = input_elem.get_attribute('class') or ''
                if 'search' in element_class.lower() and ('keyword' in element_class.lower() or 'input' in element_class.lower() or 'field' in element_class.lower()):
                    print(f"    Found input with search class: '{element_class}'")
                    return input_elem

            for input_elem in inputs:
                name = input_elem.get_attribute('name') or ''
                element_id = input_elem.get_attribute('id') or ''

                if any(exclude in name.lower() or exclude in element_id.lower() for exclude in exclude_keywords):
                    continue

                placeholder = input_elem.get_attribute('placeholder')
                if placeholder:
                    placeholder_lower = placeholder.lower()
                    if any(keyword in placeholder_lower for keyword in search_keywords):
                        print(f"    Found input with placeholder: '{placeholder}'")
                        return input_elem

            for input_elem in inputs:
                name = input_elem.get_attribute('name') or ''
                element_id = input_elem.get_attribute('id') or ''

                if any(exclude in name.lower() or exclude in element_id.lower() for exclude in exclude_keywords):
                    continue

                aria_label = input_elem.get_attribute('aria-label')
                if aria_label:
                    aria_label_lower = aria_label.lower()
                    if any(keyword in aria_label_lower for keyword in search_keywords):
                        print(f"    Found input with aria-label: '{aria_label}'")
                        return input_elem

            for input_elem in inputs:
                name = input_elem.get_attribute('name') or ''
                element_id = input_elem.get_attribute('id') or ''

                if any(exclude in name.lower() or exclude in element_id.lower() for exclude in exclude_keywords):
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
                if text and (text == 'search' or text.startswith('search') or 'search jobs' in text):
                    print(f"    Found submit button with text: '{element.text}'")
                    return element

                value = element.get_attribute('value')
                if value and (value.lower() == 'search' or value.lower().startswith('search')):
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
            driver.get(self.base_url)

            time.sleep(3)

            self.dismiss_cookie_popup(driver)

            search_input = self.find_search_input(driver)

            if search_input:
                keyword_string = ', '.join(self.skills)
                print(f"[4] Entering keywords: {keyword_string}")

                search_submitted = False

                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_input)
                    time.sleep(0.5)

                    wait = WebDriverWait(driver, 10)
                    search_input = wait.until(EC.element_to_be_clickable(search_input))

                    search_input.click()
                    time.sleep(0.3)

                    search_input.clear()
                    search_input.send_keys(keyword_string)

                    time.sleep(0.3)
                    input_value = search_input.get_attribute('value')
                    if not input_value or keyword_string not in input_value:
                        print(f"    Value not set properly, trying JavaScript... (got: '{input_value}')")
                        driver.execute_script("arguments[0].value = arguments[1];", search_input, keyword_string)
                        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", search_input)
                        time.sleep(0.3)

                    url_before = driver.current_url

                    print("    Submitting search (pressing Enter)...")
                    search_input.send_keys(Keys.RETURN)

                    time.sleep(4)

                    url_after = driver.current_url
                    if url_before != url_after:
                        print("    Search submitted successfully (", url_after, ")")
                        search_submitted = True
                    else:
                        print("    URL didn't change, Enter may not have worked")

                except ElementNotInteractableException:
                    print("    Input not interactable, trying to press Enter via JavaScript...")
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_input)
                        time.sleep(0.5)

                        url_before = driver.current_url

                        driver.execute_script("arguments[0].value = arguments[1];", search_input, keyword_string)
                        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", search_input)
                        driver.execute_script("arguments[0].form.submit();", search_input)
                        time.sleep(4)

                        url_after = driver.current_url
                        if url_before != url_after:
                            print("    JavaScript submit successful (URL changed)")
                            search_submitted = True
                        else:
                            print("    JavaScript submit didn't change URL")
                    except Exception as e:
                        print(f"    JavaScript fallback failed: {e}")

                except TimeoutException:
                    print("    Search input timeout, trying with JavaScript...")
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_input)
                        time.sleep(0.5)

                        driver.execute_script("arguments[0].value = arguments[1];", search_input, keyword_string)
                        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", search_input)
                        time.sleep(0.5)
                    except:
                        pass

                if not search_submitted:
                    current_url = driver.current_url
                    if 'search' in current_url.lower() or 'query' in current_url.lower() or 'keywords' in current_url.lower():
                        print("    Enter key didn't work, trying URL-based search...")
                        if 'query=' in current_url.lower():
                            if 'query=' in current_url:
                                search_url = current_url.split('query=')[0] + 'query=' + keyword_string
                            else:
                                search_url = current_url.split('query=')[0].replace('QUERY=', 'query=') + 'query=' + keyword_string

                            print(f"    Navigating to: {search_url}")
                            driver.get(search_url)
                            time.sleep(4)
                            search_submitted = True
                        elif 'search=' in current_url.lower():
                            if 'search=' in current_url:
                                search_url = current_url.split('search=')[0] + 'search=' + keyword_string
                            else:
                                search_url = current_url.split('search=')[0].replace('SEARCH=', 'search=') + 'search=' + keyword_string

                            print(f"    Navigating to: {search_url}")
                            driver.get(search_url)
                            time.sleep(4)
                            search_submitted = True
                        elif 'keywords=' in current_url.lower():
                            if 'keywords=' in current_url:
                                search_url = current_url.split('keywords=')[0] + 'keywords=' + keyword_string
                            else:
                                search_url = current_url.split('keywords=')[0].replace('KEYWORDS=', 'keywords=') + 'keywords=' + keyword_string

                            print(f"    Navigating to: {search_url}")
                            driver.get(search_url)
                            time.sleep(4)
                            search_submitted = True

                if not search_submitted:
                    self.dismiss_autocomplete_dropdown(driver)
                    print("    Looking for submit button...")
                    submit_button = self.find_submit_button(driver)
                    if submit_button:
                        try:
                            print("    Clicking submit button...")
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
                            time.sleep(0.5)
                            submit_button.click()
                            time.sleep(4)
                            search_submitted = True
                        except Exception as e:
                            print(f"    Regular click failed: {e}")
                            print("    Trying JavaScript click...")
                            try:
                                driver.execute_script("arguments[0].click();", submit_button)
                                time.sleep(4)
                                search_submitted = True
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

                    if 'query=' in final_url.lower():
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
                            search_url = base_part + 'query=' + keyword_string + rest_params
                        else:
                            base_part = final_url.lower().split('query=')[0]
                            search_url = base_part + 'query=' + keyword_string

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
                            search_url = base_part + 'search=' + keyword_string + rest_params
                        else:
                            base_part = final_url.lower().split('search=')[0]
                            search_url = base_part + 'search=' + keyword_string

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
                            search_url = base_part + 'keywords=' + keyword_string + rest_params
                        else:
                            base_part = final_url.lower().split('keywords=')[0]
                            search_url = base_part + 'keywords=' + keyword_string

                        print(f"    Navigating to: {search_url}")
                        driver.get(search_url)
                        time.sleep(4)
                        keyword_in_url = True

                    else:
                        print(f"    No 'query=', 'search=', or 'keywords=' parameter found in URL")
                        print(f"    Continuing with current page, results may not be filtered...")

                job_urls = self.extract_job_urls(driver)
            else:
                print("[4] No search input found, extracting jobs from main page...")
                job_urls = self.extract_job_urls(driver)

            jobs_to_scrape = job_urls[:self.limit]
            self.job_links = [job['url'] for job in jobs_to_scrape]

            print(f"[6] Fetching {len(jobs_to_scrape)} job pages...")

            for i, job in enumerate(jobs_to_scrape, 1):
                print(f"    [{i}/{len(jobs_to_scrape)}] {job['title']}")

                driver.get(job['url'])
                time.sleep(2)
                job_html = driver.page_source

                if job_html:
                    self.job_pages.append({
                        'url': job['url'],
                        'title': job['title'],
                        'html': job_html
                    })

            print(f"[7] Successfully scraped {len(self.job_pages)} job pages")

        except Exception as e:
            print(f"Error during Selenium scraping: {e}")

        finally:
            if driver:
                driver.quit()

        return self.job_pages
