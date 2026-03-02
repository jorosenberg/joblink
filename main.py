from scraper import JobScraper

def main():
    print("=== JobLink Extraction Framework ===")
    target_url = input("Enter the target job board URL: ").strip()
    limit = int(input("Enter the maximum number of jobs to add: ").strip())

    filters = {
        "skills": input("Enter required skills (comma-separated): ").split(','),
    }

    print("\n[1] Initiating scraping...")

    scraper = JobScraper(base_url=target_url, limit=limit, filters=filters)
    job_pages = scraper.scrape()

    print(f"\n=== Scraping Complete ===")
    print(f"Total jobs scraped: {len(job_pages)}")

    for i, job in enumerate(job_pages, 1):
        print(f"{i}. {job['title']}")
        print(f"   URL: {job['url']}")
        print(f"   HTML Length: {len(job['html'])} characters")

if __name__ == "__main__":
    main()
