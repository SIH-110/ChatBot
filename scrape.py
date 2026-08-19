import requests
from bs4 import BeautifulSoup
import json, os

HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_page(url, output_file):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        # Extract main content – adjust selector based on site
        content = soup.find("div", class_="main-content") or soup.find("main") or soup.body
        text = content.get_text(separator="\n", strip=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Saved {output_file}")
    except Exception as e:
        print(f"Error {url}: {e}")

if __name__ == "__main__":
    urls = [
        ("https://www.doj.gov.in/department", "data/about.txt"),
        ("https://www.doj.gov.in/department/our-division?page=1", "data/divisions.txt"),
        ("https://doj.gov.in/acts-rules/", "data/acts_rules.txt"),
        ("https://doj.gov.in/notifications/", "data/notifications.txt"),
        ("https://doj.gov.in/circulars/", "data/circulars.txt"),
        ("https://doj.gov.in/annual-reports/", "data/annual_reports.txt"),
        ("https://doj.gov.in/press-releases/", "data/press_releases.txt"),
        ("https://doj.gov.in/important-links/", "data/important_links.txt"),
        ("https://doj.gov.in/contact-us/", "data/contact_us.txt"),
        ("https://doj.gov.in/faq/", "data/faq.txt"),
        ("https://njdg.ecourts.gov.in/", "data/njdg.txt"),
        ("https://ecourts.gov.in/ecourts_home/", "data/court_orders.txt"),
        ("https://ecourts.gov.in/services/", "data/services.txt"),
        ("https://www.doj.gov.in/offerings/vacancies?page=1", "data/vacancies.txt"),
        ("https://echallan.parivahan.gov.in/ ", "data/echallan.txt"),
        (" https://www.sci.gov.in/live-streaming/", "data/live_streaming.txt"),
        ("https://dashboard.doj.gov.in/fast-track-court/ftc_functional", "data/fast_track_special_courts.txt"),
        ("https://ecourts.gov.in/ecourts2.0/", "data/ecourts2.txt")
    ]
    os.makedirs("data", exist_ok=True)
    for url, out in urls:
        scrape_page(url, out)