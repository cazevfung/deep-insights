"""
Test to verify expected total calculation with real links.
"""
import asyncio
import sys
import os
import io
from pathlib import Path

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(backend_path / 'app'))

from app.services.workflow_service import calculate_total_scraping_processes

def test_total_calculation():
    """Test total calculation with the provided links."""
    print("=" * 80)
    print("TEST: Expected Total Calculation with Real Links")
    print("=" * 80)
    
    # Links provided by user
    links = [
        "https://www.youtube.com/watch?v=am2Jl7o3roQ&pp=ygUGYWkgTlBD",
        "https://www.youtube.com/watch?v=1u6IfvGvx7Y&pp=ygUGYWkgTlBD",
        "https://www.red3d.com/cwr/steer/gdc99/#:~:text=Autonomous%20characters%20are%20a%20type,",
        "https://www.bilibili.com/video/BV1YhXjY3EFM/?spm_id_from=333.337.search-card.all.click",
        "https://www.bilibili.com/video/BV1SkeuzLE1a/?spm_id_from=333.337.search-card.all.click",
    ]
    
    print(f"\nLinks provided ({len(links)} total):")
    for i, link in enumerate(links, 1):
        print(f"  {i}. {link}")
    
    # Simulate link context (what workflow_service would create)
    # Based on link detection logic
    context = {}
    
    # YouTube links (2)
    youtube_links = [
        link for link in links 
        if 'youtube.com' in link or 'youtu.be' in link
    ]
    if youtube_links:
        context['youtube'] = [
            {'link_id': f'yt_req{i}', 'url': url}
            for i, url in enumerate(youtube_links, 1)
        ]
    
    # Bilibili links (2)
    bilibili_links = [
        link for link in links 
        if 'bilibili.com' in link
    ]
    if bilibili_links:
        context['bilibili'] = [
            {'link_id': f'bili_req{i}', 'url': url}
            for i, url in enumerate(bilibili_links, 1)
        ]
    
    # Article links (1 - red3d.com)
    article_links = [
        link for link in links 
        if 'red3d.com' in link or ('http' in link and 'youtube.com' not in link and 'bilibili.com' not in link and 'reddit.com' not in link)
    ]
    if article_links:
        context['article'] = [
            {'link_id': f'art_req{i}', 'url': url}
            for i, url in enumerate(article_links, 1)
        ]
    
    print(f"\nDetected link types:")
    for link_type, link_list in context.items():
        print(f"  {link_type}: {len(link_list)} links")
        for link in link_list:
            print(f"    - {link['link_id']}: {link['url'][:60]}...")
    
    # Calculate expected total
    totals = calculate_total_scraping_processes(context)
    
    print(f"\nCalculation Results:")
    print(f"  Total links: {totals['total_links']}")
    print(f"  Total processes: {totals['total_processes']}")
    print(f"  Breakdown: {totals['breakdown']}")
    
    # Expected calculation:
    # YouTube: 2 links × 2 processes = 4
    # Bilibili: 2 links × 2 processes = 4
    # Article: 1 link × 1 process = 1
    # Total = 4 + 4 + 1 = 9
    
    expected_total = 9
    actual_total = totals['total_processes']
    
    print(f"\nVerification:")
    print(f"  Expected total: {expected_total}")
    print(f"  Calculated total: {actual_total}")
    
    if actual_total == expected_total:
        print(f"  [OK] Total calculation is CORRECT!")
    else:
        print(f"  [ERROR] Total calculation is WRONG!")
        print(f"    Expected {expected_total}, got {actual_total}")
        print(f"    Difference: {actual_total - expected_total}")
    
    # Check breakdown
    print(f"\nBreakdown verification:")
    expected_breakdown = {
        'youtube': 4,  # 2 links × 2 processes
        'bilibili': 4,  # 2 links × 2 processes
        'article': 1,  # 1 link × 1 process
    }
    
    for link_type, expected_count in expected_breakdown.items():
        actual_count = totals['breakdown'].get(link_type, 0)
        if actual_count == expected_count:
            print(f"  [OK] {link_type}: {actual_count} processes")
        else:
            print(f"  [ERROR] {link_type}: expected {expected_count}, got {actual_count}")
    
    return actual_total == expected_total

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("EXPECTED TOTAL CALCULATION TEST")
    print("=" * 80)
    
    passed = test_total_calculation()
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    if passed:
        print("[SUCCESS] Test PASSED!")
        sys.exit(0)
    else:
        print("[FAILURE] Test FAILED!")
        sys.exit(1)

