"""Test script to verify phase transition and research phase timing improvements.

This test simulates the real workflow with minimal API calls to verify:
1. Phase transition timing (scraping → research)
2. Research phase internal delays and progress updates
3. Frontend/backend synchronization
4. Timing log output
"""
import sys
import time
import asyncio
import queue
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock, patch
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# Configure logging to see timing logs
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)

# Mock WebSocket manager for testing
class MockWebSocketManager:
    """Mock WebSocket manager that captures all messages."""
    
    def __init__(self):
        self.messages: list = []
        self.broadcast_lock = threading.Lock()
    
    async def broadcast(self, batch_id: str, message: Dict[str, Any]):
        """Capture broadcast messages."""
        with self.broadcast_lock:
            self.messages.append({
                'timestamp': time.time(),
                'batch_id': batch_id,
                'message': message
            })
            logger.info(f"[MOCK_WS] Broadcast: {message.get('type', 'unknown')} to batch {batch_id}")
    
    def get_messages_by_type(self, message_type: str) -> list:
        """Get all messages of a specific type."""
        return [msg for msg in self.messages if msg['message'].get('type') == message_type]
    
    def get_message_count(self) -> int:
        """Get total message count."""
        return len(self.messages)
    
    def clear_messages(self):
        """Clear all messages."""
        with self.broadcast_lock:
            self.messages.clear()

# Mock UI for testing
class MockWebSocketUI:
    """Mock WebSocket UI that captures all display calls."""
    
    def __init__(self, ws_manager, batch_id: str, main_loop=None):
        self.ws_manager = ws_manager
        self.batch_id = batch_id
        self.main_loop = main_loop
        self.messages: list = []
        self.phase_changes: list = []
        self.progress_updates: list = []
    
    def display_message(self, message: str, level: str = "info"):
        """Capture display message calls."""
        self.messages.append({
            'timestamp': time.time(),
            'message': message,
            'level': level
        })
        logger.info(f"[MOCK_UI] Display: [{level}] {message}")
    
    def display_header(self, title: str):
        """Capture header display."""
        self.display_message(f"\n{'=' * 60}\n  {title}\n{'=' * 60}\n", "info")
    
    def notify_phase_change(self, phase: str, phase_name: str = None):
        """Capture phase change notifications."""
        self.phase_changes.append({
            'timestamp': time.time(),
            'phase': phase,
            'phase_name': phase_name
        })
        logger.info(f"[MOCK_UI] Phase change: {phase} - {phase_name}")
    
    def display_progress(self, status: dict):
        """Capture progress updates."""
        self.progress_updates.append({
            'timestamp': time.time(),
            'status': status
        })
        logger.info(f"[MOCK_UI] Progress: {status.get('progress_percentage', 0):.1f}%")
    
    def display_stream(self, token: str, stream_id: str):
        """Capture stream tokens."""
        pass  # Don't log every token
    
    def clear_stream_buffer(self, stream_id: Optional[str] = None):
        """Clear stream buffer."""
        pass
    
    def prompt_user(self, prompt: str, choices: Optional[list] = None) -> str:
        """Mock user prompt - auto-confirm."""
        logger.info(f"[MOCK_UI] User prompt: {prompt}")
        if choices:
            return choices[0] if choices else ""
        return "y"  # Auto-confirm
    
    def display_goals(self, goals: list):
        """Display goals."""
        logger.info(f"[MOCK_UI] Display goals: {len(goals)} goals")
    
    def display_synthesized_goal(self, synthesized_goal: dict):
        """Display synthesized goal."""
        logger.info(f"[MOCK_UI] Display synthesized goal")
    
    def display_plan(self, plan: list):
        """Display plan."""
        logger.info(f"[MOCK_UI] Display plan: {len(plan)} steps")
    
    def display_report(self, report: str, save_path: Optional[str] = None):
        """Display report."""
        logger.info(f"[MOCK_UI] Display report: {len(report)} chars")

# Mock Qwen client that returns minimal responses quickly
class MockQwenClient:
    """Mock Qwen client with fast, minimal responses."""
    
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0
    
    def stream_and_collect(self, messages, callback=None, **kwargs):
        """Mock stream that simulates API call with minimal delay."""
        self.call_count += 1
        
        # Simulate API call delay (100-500ms to simulate network latency)
        import random
        delay = random.uniform(0.1, 0.5)
        time.sleep(delay)
        
        # Generate minimal response based on context
        response_text = ""
        if any("phase0_5" in str(m) or "角色" in str(m) for m in messages):
            response_text = '{"research_role": "测试研究员", "rationale": "用于测试"}'
        elif any("phase1" in str(m) or "目标" in str(m) for m in messages):
            response_text = '{"suggested_goals": [{"goal_text": "测试目标1", "uses": ["transcript"]}, {"goal_text": "测试目标2", "uses": ["transcript"]}]}'
        elif any("phase2" in str(m) or "综合" in str(m) for m in messages):
            response_text = '{"synthesized_goal": {"comprehensive_topic": "测试综合主题", "unifying_theme": "测试主题", "research_scope": "测试范围"}}'
        elif any("phase3" in str(m) or "执行" in str(m) for m in messages):
            response_text = '{"findings": {"summary": "测试发现"}, "insights": "测试洞察", "confidence": 0.8}'
        elif any("phase4" in str(m) or "报告" in str(m) for m in messages):
            if "outline" in str(m).lower() or "大纲" in str(m):
                response_text = '{"sections": [{"title": "章节1", "target_words": 100}, {"title": "章节2", "target_words": 100}]}'
            else:
                response_text = "# 测试报告\n\n这是测试报告内容。"
        else:
            response_text = '{"result": "测试结果"}'
        
        # Simulate streaming tokens to callback
        if callback:
            for char in response_text:
                callback(char)
                time.sleep(0.01)  # Small delay between tokens
        
        usage = {
            'prompt_tokens': 50,
            'completion_tokens': len(response_text.split()),
            'total_tokens': 50 + len(response_text.split())
        }
        
        self.total_input_tokens += usage['prompt_tokens']
        self.total_output_tokens += usage['completion_tokens']
        
        return response_text, usage
    
    def parse_json_from_stream(self, iterator):
        """Parse JSON from stream."""
        text = "".join(iterator)
        # Extract JSON from text
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {}
    
    def get_usage_info(self):
        """Get usage info."""
        return {
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens
        }

# Mock data loader
class MockDataLoader:
    """Mock data loader that returns minimal test data."""
    
    def __init__(self):
        self.results_base_path = Path(__file__).parent / "results"
    
    def load_batch(self, batch_id: str) -> Dict[str, Any]:
        """Load minimal test batch data."""
        return {
            'test_link_1': {
                'transcript': '这是测试转录内容。' * 10,  # Minimal content
                'comments': [],
                'metadata': {'word_count': 100},
                'source': 'youtube'
            },
            'test_link_2': {
                'transcript': '这是另一个测试转录内容。' * 10,
                'comments': [],
                'metadata': {'word_count': 100},
                'source': 'article'
            }
        }
    
    def create_abstract(self, data: Dict[str, Any], use_intelligent_sampling: bool = True) -> str:
        """Create minimal abstract."""
        return f"摘要: {data.get('transcript', '')[:100]}..."
    
    def assess_data_quality(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess data quality."""
        return {
            'quality_score': 0.9,
            'quality_flags': []
        }

# Mock summarizer
class MockContentSummarizer:
    """Mock content summarizer with fast responses."""
    
    def __init__(self, client, config):
        self.client = client
        self.config = config
    
    def summarize_content_item(self, link_id: str, transcript: str = None, comments: list = None, metadata: dict = None) -> Dict[str, Any]:
        """Create minimal summary quickly."""
        # Simulate small delay
        time.sleep(0.1)
        return {
            'transcript_summary': {
                'total_markers': 3,
                'markers': [
                    {'text': '标记1', 'position': 0},
                    {'text': '标记2', 'position': 50},
                    {'text': '标记3', 'position': 100}
                ]
            },
            'comments_summary': {
                'total_markers': 0,
                'markers': []
            },
            'created_at': datetime.now().isoformat(),
            'model_used': 'qwen-flash'
        }

async def test_workflow_service_transitions():
    """Test workflow service phase transitions."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: Workflow Service Phase Transitions")
    logger.info("=" * 80)
    
    from backend.app.services.workflow_service import WorkflowService
    from backend.app.services.progress_service import ProgressService
    
    # Create mock WebSocket manager
    ws_manager = MockWebSocketManager()
    progress_service = ProgressService(ws_manager)
    workflow_service = WorkflowService(ws_manager)
    
    # Mock batch ID
    batch_id = "test_batch_001"
    
    # Initialize progress service with expected links
    expected_processes = [
        {'link_id': 'link1', 'url': 'http://test1.com', 'scraper_type': 'youtube', 'process_type': 'transcript'},
        {'link_id': 'link1_comments', 'url': 'http://test1.com', 'scraper_type': 'youtubecomments', 'process_type': 'comments'},
    ]
    progress_service.initialize_expected_links(batch_id, expected_processes)
    
    # Simulate all links completing immediately
    for proc in expected_processes:
        await progress_service.update_link_status(
            batch_id=batch_id,
            link_id=proc['link_id'],
            url=proc['url'],
            status='completed'
        )
    
    # Test status updates wait
    logger.info("\n--- Testing _wait_for_status_updates ---")
    message_queue = queue.Queue()
    start_time = time.time()
    result = await workflow_service._wait_for_status_updates(
        message_queue,
        batch_id,
        max_wait_seconds=5.0
    )
    elapsed = time.time() - start_time
    logger.info(f"[TEST] Status updates wait: {result} in {elapsed:.3f}s")
    assert result, "Status updates should complete immediately"
    assert elapsed < 1.0, f"Should complete quickly, but took {elapsed:.3f}s"
    
    # Test confirmation wait
    logger.info("\n--- Testing wait_for_scraping_confirmation ---")
    start_time = time.time()
    confirmation = await workflow_service.wait_for_scraping_confirmation(
        message_queue,
        batch_id,
        max_wait_seconds=5.0
    )
    elapsed = time.time() - start_time
    logger.info(f"[TEST] Confirmation wait: {confirmation is not None} in {elapsed:.3f}s")
    assert confirmation is not None, "Confirmation should be received"
    assert confirmation.get('confirmed'), "Confirmation should be confirmed"
    assert elapsed < 1.0, f"Should complete quickly, but took {elapsed:.3f}s"
    
    logger.info("\n✓ TEST 1 PASSED: Phase transitions are fast\n")

async def test_research_phase_api_calls():
    """Test research phase API calls with progress updates."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Research Phase API Calls with Progress Updates")
    logger.info("=" * 80)
    
    try:
        # Mock imports
        with patch('research.phases.phase0_prepare.ContentSummarizer', MockContentSummarizer):
            with patch('research.phases.phase0_prepare.ResearchDataLoader', MockDataLoader):
                from research.session import ResearchSession
                
                # Create mock client
                mock_client = MockQwenClient()
                
                # Create mock UI
                ws_manager = MockWebSocketManager()
                batch_id = "test_batch_002"
                mock_ui = MockWebSocketUI(ws_manager, batch_id)
                
                # Mock session
                session = ResearchSession()
                
                # Test Phase 0.5
                logger.info("\n--- Testing Phase 0.5: Role Generation ---")
                from research.phases.phase0_5_role_generation import Phase0_5RoleGeneration
                
                phase0_5 = Phase0_5RoleGeneration(mock_client, session, ui=mock_ui)
                start_time = time.time()
                
                result = phase0_5.execute("测试数据摘要", "测试主题")
                
                elapsed = time.time() - start_time
                logger.info(f"[TEST] Phase 0.5 completed in {elapsed:.3f}s")
                
                # Check progress updates
                progress_messages = [m for m in mock_ui.messages if "正在" in m['message'] or "完成" in m['message']]
                logger.info(f"[TEST] Progress messages sent: {len(progress_messages)}")
                for msg in progress_messages:
                    logger.info(f"  - {msg['message'][:60]}...")
                
                assert len(progress_messages) > 0, "Should have progress messages"
                assert elapsed < 2.0, f"Should complete quickly, but took {elapsed:.3f}s"
                
                # Test Phase 1
                logger.info("\n--- Testing Phase 1: Discover ---")
                from research.phases.phase1_discover import Phase1Discover
                
                mock_ui.messages.clear()
                phase1 = Phase1Discover(mock_client, session, ui=mock_ui)
                start_time = time.time()
                
                result = phase1.execute(
                    "测试数据摘要",
                    "测试主题",
                    research_role={"role": "测试研究员"},
                    amendment_feedback=None,
                    batch_data={}
                )
                
                elapsed = time.time() - start_time
                logger.info(f"[TEST] Phase 1 completed in {elapsed:.3f}s")
                
                progress_messages = [m for m in mock_ui.messages if "正在" in m['message'] or "完成" in m['message']]
                logger.info(f"[TEST] Progress messages sent: {len(progress_messages)}")
                assert len(progress_messages) > 0, "Should have progress messages"
                
                logger.info("\n✓ TEST 2 PASSED: Research phases send progress updates\n")
    except ImportError as e:
        logger.warning(f"Could not import research modules: {e}")
        logger.info("Skipping TEST 2 (requires research modules)")
        raise

async def test_progress_update_synchronization():
    """Test that progress updates are synchronized between frontend and backend."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Progress Update Synchronization")
    logger.info("=" * 80)
    
    from backend.app.services.workflow_service import WorkflowService
    from backend.app.services.progress_service import ProgressService
    
    ws_manager = MockWebSocketManager()
    progress_service = ProgressService(ws_manager)
    workflow_service = WorkflowService(ws_manager)
    
    batch_id = "test_batch_003"
    
    # Initialize with expected links
    expected_processes = [
        {'link_id': 'link1', 'url': 'http://test1.com', 'scraper_type': 'youtube', 'process_type': 'transcript'},
    ]
    progress_service.initialize_expected_links(batch_id, expected_processes)
    
    # Simulate progress updates
    logger.info("\n--- Testing progress update broadcasting ---")
    await progress_service.update_link_progress(
        batch_id=batch_id,
        link_id='link1',
        url='http://test1.com',
        stage='downloading',
        stage_progress=50.0,
        overall_progress=25.0,
        message='下载中...'
    )
    
    # Check WebSocket messages
    messages = ws_manager.get_messages_by_type('scraping:item_progress')
    logger.info(f"[TEST] Progress messages broadcast: {len(messages)}")
    assert len(messages) > 0, "Should broadcast progress messages"
    
    # Simulate completion
    await progress_service.update_link_status(
        batch_id=batch_id,
        link_id='link1',
        url='http://test1.com',
        status='completed'
    )
    
    # Check completion message
    status_messages = ws_manager.get_messages_by_type('scraping:item_update')
    logger.info(f"[TEST] Status messages broadcast: {len(status_messages)}")
    assert len(status_messages) > 0, "Should broadcast status messages"
    
    # Check batch status update
    batch_status = ws_manager.get_messages_by_type('scraping:status')
    logger.info(f"[TEST] Batch status messages broadcast: {len(batch_status)}")
    assert len(batch_status) > 0, "Should broadcast batch status"
    
    logger.info("\n✓ TEST 3 PASSED: Progress updates are synchronized\n")

async def test_phase_transition_timing():
    """Test timing of phase transitions end-to-end."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: End-to-End Phase Transition Timing")
    logger.info("=" * 80)
    
    # This test simulates the full transition from scraping to research
    from backend.app.services.workflow_service import WorkflowService
    from backend.app.services.progress_service import ProgressService
    
    ws_manager = MockWebSocketManager()
    progress_service = ProgressService(ws_manager)
    workflow_service = WorkflowService(ws_manager)
    
    batch_id = "test_batch_004"
    
    # Initialize with expected links
    expected_processes = [
        {'link_id': 'link1', 'url': 'http://test1.com', 'scraper_type': 'youtube', 'process_type': 'transcript'},
        {'link_id': 'link2', 'url': 'http://test2.com', 'scraper_type': 'article', 'process_type': 'transcript'},
    ]
    progress_service.initialize_expected_links(batch_id, expected_processes)
    
    # Simulate all links completing
    for proc in expected_processes:
        await progress_service.update_link_status(
            batch_id=batch_id,
            link_id=proc['link_id'],
            url=proc['url'],
            status='completed'
        )
    
    # Test the full transition sequence
    message_queue = queue.Queue()
    
    logger.info("\n--- Simulating full transition sequence ---")
    overall_start = time.time()
    
    # Step 1: Wait for status updates
    step1_start = time.time()
    status_complete = await workflow_service._wait_for_status_updates(
        message_queue, batch_id, max_wait_seconds=5.0
    )
    step1_elapsed = time.time() - step1_start
    logger.info(f"[TIMING] Step 1 (Status updates): {step1_elapsed:.3f}s")
    
    # Step 2: Wait for confirmation
    step2_start = time.time()
    confirmation = await workflow_service.wait_for_scraping_confirmation(
        message_queue, batch_id, max_wait_seconds=5.0
    )
    step2_elapsed = time.time() - step2_start
    logger.info(f"[TIMING] Step 2 (Confirmation): {step2_elapsed:.3f}s")
    
    # Step 3: Verify results (mock - should be fast)
    step3_start = time.time()
    await asyncio.sleep(0.1)  # Simulate verification
    step3_elapsed = time.time() - step3_start
    logger.info(f"[TIMING] Step 3 (Verification): {step3_elapsed:.3f}s")
    
    # Step 4: Phase change notification
    step4_start = time.time()
    await ws_manager.broadcast(batch_id, {
        "type": "research:phase_change",
        "phase": "research",
        "phase_name": "研究代理",
        "message": "开始研究阶段",
    })
    step4_elapsed = time.time() - step4_start
    logger.info(f"[TIMING] Step 4 (Phase change): {step4_elapsed:.3f}s")
    
    overall_elapsed = time.time() - overall_start
    logger.info(f"[TIMING] Total transition time: {overall_elapsed:.3f}s")
    
    # Verify timing is acceptable
    assert overall_elapsed < 2.0, f"Transition should be fast (<2s), but took {overall_elapsed:.3f}s"
    assert step1_elapsed < 1.0, f"Status updates should be fast (<1s), but took {step1_elapsed:.3f}s"
    assert step2_elapsed < 1.0, f"Confirmation should be fast (<1s), but took {step2_elapsed:.3f}s"
    
    logger.info("\n✓ TEST 4 PASSED: Phase transitions are fast\n")

async def test_research_phase_with_minimal_api():
    """Test research phases with minimal API calls to verify progress updates."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Research Phases with Minimal API Calls")
    logger.info("=" * 80)
    
    # Mock client with fast responses
    mock_client = MockQwenClient()
    
    # Create mock UI
    ws_manager = MockWebSocketManager()
    batch_id = "test_batch_005"
    mock_ui = MockWebSocketUI(ws_manager, batch_id)
    
    # Mock session
    from research.session import ResearchSession
    session = ResearchSession()
    
    # Test Phase 0 (with mocked summarizer)
    logger.info("\n--- Testing Phase 0: Prepare with Summarization ---")
    try:
        with patch('research.phases.phase0_prepare.ContentSummarizer', MockContentSummarizer):
            with patch('research.phases.phase0_prepare.ResearchDataLoader', MockDataLoader):
                from research.phases.phase0_prepare import Phase0Prepare
                
                mock_data_loader = MockDataLoader()
                phase0 = Phase0Prepare(mock_client, session)
                phase0.data_loader = mock_data_loader
                phase0.ui = mock_ui
                
                start_time = time.time()
                result = phase0.execute(batch_id)
                elapsed = time.time() - start_time
                
                logger.info(f"[TEST] Phase 0 completed in {elapsed:.3f}s")
                logger.info(f"[TEST] Progress messages: {len(mock_ui.messages)}")
                
                # Check for summarization progress messages
                summary_messages = [m for m in mock_ui.messages if "摘要" in m['message']]
                logger.info(f"[TEST] Summarization progress messages: {len(summary_messages)}")
                for msg in summary_messages[:5]:  # Show first 5
                    logger.info(f"  - {msg['message'][:70]}...")
                
                assert len(summary_messages) > 0, "Should have summarization progress messages"
                assert elapsed < 5.0, f"Should complete quickly, but took {elapsed:.3f}s"
    except ImportError as e:
        logger.warning(f"Could not import Phase0Prepare: {e}")
        raise
    
    # Test Phase 3 step execution
    logger.info("\n--- Testing Phase 3: Step Execution ---")
    from research.phases.phase3_execute import Phase3Execute
    from research.progress_tracker import ProgressTracker
    
    progress_tracker = ProgressTracker(total_steps=2)
    progress_tracker.add_callback(mock_ui.display_progress)
    
    phase3 = Phase3Execute(mock_client, session, progress_tracker)
    phase3.ui = mock_ui
    
    # Create minimal research plan
    research_plan = [
        {
            'step_id': 1,
            'goal': '测试目标1',
            'required_data': 'transcript',
            'chunk_strategy': 'all'
        },
        {
            'step_id': 2,
            'goal': '测试目标2',
            'required_data': 'transcript',
            'chunk_strategy': 'all'
        }
    ]
    
    mock_batch_data = MockDataLoader().load_batch(batch_id)
    
    mock_ui.messages.clear()
    mock_ui.progress_updates.clear()
    
    start_time = time.time()
    result = phase3.execute(research_plan, mock_batch_data)
    elapsed = time.time() - start_time
    
    logger.info(f"[TEST] Phase 3 completed in {elapsed:.3f}s")
    logger.info(f"[TEST] Progress messages: {len(mock_ui.messages)}")
    logger.info(f"[TEST] Progress updates: {len(mock_ui.progress_updates)}")
    
    # Check for step progress messages
    step_messages = [m for m in mock_ui.messages if "步骤" in m['message'] or "执行" in m['message']]
    logger.info(f"[TEST] Step progress messages: {len(step_messages)}")
    for msg in step_messages[:5]:  # Show first 5
        logger.info(f"  - {msg['message'][:70]}...")
    
    assert len(step_messages) > 0, "Should have step progress messages"
    assert result['completed_steps'] == 2, "Should complete all steps"
    
    logger.info("\n✓ TEST 5 PASSED: Research phases send progress updates\n")

async def test_websocket_message_delivery():
    """Test that WebSocket messages are delivered in correct order."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 6: WebSocket Message Delivery Order")
    logger.info("=" * 80)
    
    ws_manager = MockWebSocketManager()
    batch_id = "test_batch_006"
    
    # Simulate message sequence
    messages_to_send = [
        {'type': 'scraping:status', 'message': 'Status update 1'},
        {'type': 'research:phase_change', 'phase': 'phase0', 'message': 'Phase 0 started'},
        {'type': 'workflow:progress', 'message': 'Processing...'},
        {'type': 'research:phase_change', 'phase': 'phase1', 'message': 'Phase 1 started'},
        {'type': 'workflow:progress', 'message': 'API call started'},
        {'type': 'workflow:progress', 'message': 'API call completed'},
    ]
    
    async def send_messages():
        for msg in messages_to_send:
            await ws_manager.broadcast(batch_id, msg)
            await asyncio.sleep(0.05)  # Small delay between messages
    
    start_time = time.time()
    await send_messages()
    elapsed = time.time() - start_time
    
    logger.info(f"[TEST] Messages sent in {elapsed:.3f}s")
    logger.info(f"[TEST] Total messages received: {ws_manager.get_message_count()}")
    
    # Verify message order
    received_messages = ws_manager.messages
    assert len(received_messages) == len(messages_to_send), "Should receive all messages"
    
    for i, (sent, received) in enumerate(zip(messages_to_send, received_messages)):
        assert received['message']['type'] == sent['type'], f"Message {i} type mismatch"
        logger.info(f"  Message {i}: {sent['type']} at {received['timestamp']:.3f}")
    
    # Verify timestamps are in order
    timestamps = [msg['timestamp'] for msg in received_messages]
    assert timestamps == sorted(timestamps), "Messages should be in chronological order"
    
    logger.info("\n✓ TEST 6 PASSED: WebSocket messages delivered in order\n")

async def main():
    """Run all tests."""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE TRANSITION TIMING TEST SUITE")
    logger.info("=" * 80)
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info("")
    
    test_results = []
    
    try:
        # Test 1: Workflow service transitions
        await test_workflow_service_transitions()
        test_results.append(("Workflow Service Transitions", True))
    except Exception as e:
        logger.error(f"TEST 1 FAILED: {e}", exc_info=True)
        test_results.append(("Workflow Service Transitions", False))
    
    try:
        # Test 2: Research phase API calls
        await test_research_phase_api_calls()
        test_results.append(("Research Phase API Calls", True))
    except Exception as e:
        logger.error(f"TEST 2 FAILED: {e}", exc_info=True)
        test_results.append(("Research Phase API Calls", False))
    
    try:
        # Test 3: Progress update synchronization
        await test_progress_update_synchronization()
        test_results.append(("Progress Update Synchronization", True))
    except Exception as e:
        logger.error(f"TEST 3 FAILED: {e}", exc_info=True)
        test_results.append(("Progress Update Synchronization", False))
    
    try:
        # Test 4: Phase transition timing
        await test_phase_transition_timing()
        test_results.append(("Phase Transition Timing", True))
    except Exception as e:
        logger.error(f"TEST 4 FAILED: {e}", exc_info=True)
        test_results.append(("Phase Transition Timing", False))
    
    try:
        # Test 5: Research phases with minimal API
        await test_research_phase_with_minimal_api()
        test_results.append(("Research Phases with Minimal API", True))
    except Exception as e:
        logger.error(f"TEST 5 FAILED: {e}", exc_info=True)
        test_results.append(("Research Phases with Minimal API", False))
    
    try:
        # Test 6: WebSocket message delivery
        await test_websocket_message_delivery()
        test_results.append(("WebSocket Message Delivery", True))
    except Exception as e:
        logger.error(f"TEST 6 FAILED: {e}", exc_info=True)
        test_results.append(("WebSocket Message Delivery", False))
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    logger.info(f"Finished: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    
    if passed == total:
        logger.success("\n🎉 ALL TESTS PASSED! Timing improvements are working correctly.")
        return 0
    else:
        logger.error(f"\n❌ {total - passed} test(s) failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

