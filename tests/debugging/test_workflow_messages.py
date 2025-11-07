"""
Test to verify what the backend actually sends in messages with real workflow.
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

from app.services.workflow_service import WorkflowService, calculate_total_scraping_processes
from app.websocket.manager import WebSocketManager
from collections import defaultdict

class MockWebSocketManager:
    """Mock WebSocket manager to capture messages."""
    def __init__(self):
        self.messages = defaultdict(list)
    
    async def broadcast(self, batch_id: str, message: dict):
        """Capture broadcast messages."""
        self.messages[batch_id].append(message)
        if message.get('type') in ['batch:initialized', 'scraping:status']:
            print(f"[BROADCAST] {message.get('type')}:")
            if message.get('type') == 'batch:initialized':
                print(f"  total_processes: {message.get('total_processes')}")
                print(f"  expected_total: {message.get('expected_total')}")
                print(f"  total_links: {message.get('total_links')}")
            elif message.get('type') == 'scraping:status':
                print(f"  total: {message.get('total')}")
                print(f"  expected_total: {message.get('expected_total')}")
                print(f"  completed: {message.get('completed')}")
                print(f"  completion_rate: {message.get('completion_rate')}")

async def test_workflow_messages():
    """Test what messages are sent during workflow initialization."""
    print("=" * 80)
    print("TEST: Workflow Message Verification")
    print("=" * 80)
    
    ws_manager = MockWebSocketManager()
    workflow_service = WorkflowService(ws_manager)
    batch_id = "test_real_links_001"
    
    # Links provided by user
    links = [
        "https://www.youtube.com/watch?v=am2Jl7o3roQ&pp=ygUGYWkgTlBD",
        "https://www.youtube.com/watch?v=1u6IfvGvx7Y&pp=ygUGYWkgTlBD",
        "https://www.red3d.com/cwr/steer/gdc99/#:~:text=Autonomous%20characters%20are%20a%20type,",
        "https://www.bilibili.com/video/BV1YhXjY3EFM/?spm_id_from=333.337.search-card.all.click",
        "https://www.bilibili.com/video/BV1SkeuzLE1a/?spm_id_from=333.337.search-card.all.click",
    ]
    
    print(f"\nLinks ({len(links)} total):")
    for i, link in enumerate(links, 1):
        print(f"  {i}. {link}")
    
    # Simulate _load_link_context (what happens when workflow starts)
    print(f"\nStep 1: Loading link context (simulating workflow start)...")
    
    # Create link context manually based on link detection
    context = {}
    
    # YouTube links (2)
    youtube_links = [
        link for link in links 
        if 'youtube.com' in link or 'youtu.be' in link
    ]
    if youtube_links:
        context['youtube'] = [
            {
                'link_id': f'yt_req{i}',
                'url': url,
                'scraper_type': 'youtube',
                'process_type': 'transcript'
            }
            for i, url in enumerate(youtube_links, 1)
        ]
    
    # Bilibili links (2)
    bilibili_links = [
        link for link in links 
        if 'bilibili.com' in link
    ]
    if bilibili_links:
        context['bilibili'] = [
            {
                'link_id': f'bili_req{i}',
                'url': url,
                'scraper_type': 'bilibili',
                'process_type': 'transcript'
            }
            for i, url in enumerate(bilibili_links, 1)
        ]
    
    # Article links (1 - red3d.com)
    article_links = [
        link for link in links 
        if 'red3d.com' in link
    ]
    if article_links:
        context['article'] = [
            {
                'link_id': f'art_req{i}',
                'url': url,
                'scraper_type': 'article',
                'process_type': 'article'
            }
            for i, url in enumerate(article_links, 1)
        ]
    
    print(f"\n  Link context:")
    for link_type, link_list in context.items():
        print(f"    {link_type}: {len(link_list)} links")
    
    # Calculate totals
    totals = calculate_total_scraping_processes(context)
    print(f"\n  Calculated totals:")
    print(f"    Total links: {totals['total_links']}")
    print(f"    Total processes: {totals['total_processes']}")
    print(f"    Breakdown: {totals['breakdown']}")
    
    # Build all expected processes
    all_expected_processes = []
    for link_type, links_list in context.items():
        for link in links_list:
            if link_type in ['youtube', 'bilibili']:
                # Transcript process
                all_expected_processes.append({
                    'link_id': link['link_id'],
                    'url': link['url'],
                    'scraper_type': link_type,
                    'process_type': 'transcript'
                })
                # Comments process
                all_expected_processes.append({
                    'link_id': f"{link['link_id']}_comments",
                    'url': link['url'],
                    'scraper_type': f"{link_type}comments",
                    'process_type': 'comments'
                })
            else:
                # Article/Reddit - single process
                all_expected_processes.append({
                    'link_id': link['link_id'],
                    'url': link['url'],
                    'scraper_type': link_type,
                    'process_type': 'article' if link_type == 'article' else 'reddit'
                })
    
    print(f"\n  Expected processes: {len(all_expected_processes)}")
    
    # Store in workflow service
    workflow_service.link_context[batch_id] = context
    workflow_service.batch_totals[batch_id] = {
        'total_processes': totals['total_processes'],
        'total_links': totals['total_links'],
        'breakdown': totals['breakdown'],
        'link_breakdown': totals['link_breakdown'],
    }
    
    # Pre-register expected links
    registered_count = workflow_service.progress_service.initialize_expected_links(
        batch_id, 
        all_expected_processes
    )
    print(f"  Pre-registered: {registered_count} processes")
    
    # Send batch:initialized message (what _load_link_context does)
    # Include both total_processes and expected_total for consistency
    print(f"\nStep 2: Sending batch:initialized message...")
    await ws_manager.broadcast(batch_id, {
        'type': 'batch:initialized',
        'batch_id': batch_id,
        'total_processes': totals['total_processes'],  # Keep for backward compatibility
        'expected_total': totals['total_processes'],  # Add for consistency with scraping:status
        'total_links': totals['total_links'],
        'breakdown': totals['breakdown'],
        'link_breakdown': totals['link_breakdown'],
        'timestamp': '2025-11-07T12:00:00.000000',
        'message': f'已初始化批次，共 {totals["total_processes"]} 个抓取任务'
    })
    
    # Send initial status update (what _update_batch_status does)
    print(f"\nStep 3: Sending initial scraping:status message...")
    await workflow_service.progress_service._update_batch_status(batch_id)
    
    # Check messages
    print(f"\nStep 4: Verifying messages...")
    
    batch_init_messages = [m for m in ws_manager.messages[batch_id] if m.get('type') == 'batch:initialized']
    status_messages = [m for m in ws_manager.messages[batch_id] if m.get('type') == 'scraping:status']
    
    errors = []
    
    # Check batch:initialized
    if not batch_init_messages:
        errors.append("No batch:initialized message found!")
    else:
        init_msg = batch_init_messages[-1]
        expected_total_in_init = init_msg.get('expected_total')
        total_processes_in_init = init_msg.get('total_processes')
        
        print(f"  batch:initialized message fields:")
        print(f"    total_processes: {total_processes_in_init}")
        print(f"    expected_total: {expected_total_in_init}")
        
        if total_processes_in_init != totals['total_processes']:
            errors.append(f"batch:initialized total_processes mismatch: expected {totals['total_processes']}, got {total_processes_in_init}")
        else:
            print(f"  [OK] batch:initialized has correct total_processes: {total_processes_in_init}")
        
        # Check that expected_total is also present and matches
        if expected_total_in_init is None:
            errors.append("batch:initialized missing expected_total field!")
        elif expected_total_in_init != totals['total_processes']:
            errors.append(f"batch:initialized expected_total mismatch: expected {totals['total_processes']}, got {expected_total_in_init}")
        else:
            print(f"  [OK] batch:initialized has correct expected_total: {expected_total_in_init}")
    
    # Check scraping:status
    if not status_messages:
        errors.append("No scraping:status message found!")
    else:
        status_msg = status_messages[-1]
        expected_total_in_status = status_msg.get('expected_total')
        total_in_status = status_msg.get('total')
        
        print(f"  Status message fields:")
        print(f"    total: {total_in_status}")
        print(f"    expected_total: {expected_total_in_status}")
        
        if expected_total_in_status != totals['total_processes']:
            errors.append(f"scraping:status expected_total mismatch: expected {totals['total_processes']}, got {expected_total_in_status}")
        else:
            print(f"  [OK] scraping:status has correct expected_total: {expected_total_in_status}")
        
        if expected_total_in_status == 0:
            errors.append("ERROR: expected_total is 0 in scraping:status message!")
    
    if errors:
        print(f"\n[FAIL] ERRORS FOUND:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print(f"\n[PASS] All messages have correct expected_total!")
        return True

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("WORKFLOW MESSAGE VERIFICATION TEST")
    print("=" * 80)
    
    passed = asyncio.run(test_workflow_messages())
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    if passed:
        print("[SUCCESS] Test PASSED!")
        sys.exit(0)
    else:
        print("[FAILURE] Test FAILED!")
        sys.exit(1)

