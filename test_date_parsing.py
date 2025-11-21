"""Test date parsing for both English and Chinese."""
from datetime import datetime
from scrapers.youtube_channel_scraper import YouTubeChannelScraper

scraper = YouTubeChannelScraper()

# Test cases
test_cases = [
    # English
    "2 days ago",
    "3 weeks ago",
    "5 minutes ago",
    "1 hour ago",
    "1 month ago",
    "1 year ago",
    # Chinese
    "2天前",
    "3周前",
    "5分钟前",
    "1小时前",
    "1个月前",
    "1年前",
    # Edge cases
    "2 days ago and some other text",
    "3周前 其他文字",
]

print("="*60)
print("Testing Date Parsing")
print("="*60)
print(f"Today: {datetime.now().date()}\n")

for text in test_cases:
    result = scraper._parse_relative_date(text)
    if result:
        print(f"✓ '{text}' -> {result.date()} ({result.strftime('%Y-%m-%d')})")
    else:
        print(f"✗ '{text}' -> None")

scraper.close()

