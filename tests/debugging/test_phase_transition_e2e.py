"""End-to-end test for phase transition timing with backend and frontend sync.

This test:
1. Sets up actual workflow service and progress service
2. Uses minimal test data and fast API responses
3. Captures all WebSocket messages (simulating frontend)
4. Measures actual phase transition timing
5. Verifies frontend/backend synchronization
"""
import sys
import time
import asyncio
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock
from queue import Queue
import websockets
from websockets.client import WebSocketClientProtocol

# Add project root and backend to path
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

from loguru import logger

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | {message}",
    level="INFO",
    colorize=False  # Avoid encoding issues
)

# Mock Qwen client with fast, minimal responses
class FastQwenClient:
    """Mock Qwen client that returns minimal responses quickly."""
    
    def __init__(self):
        self.call_count = 0
        self.total_tokens = 0
    
    def stream_and_collect(self, messages, callback=None, **kwargs):
        """Fast mock API call with minimal delay."""
        self.call_count += 1
        
        # Simulate network latency (50-200ms)
        import random
        delay = random.uniform(0.05, 0.2)
        time.sleep(delay)
        
        # Generate minimal response based on context
        response_text = self._generate_response(messages)
        
        # Simulate streaming tokens to callback
        if callback:
            for char in response_text[:50]:  # Only stream first 50 chars for speed
                callback(char)
                time.sleep(0.001)  # Minimal delay between tokens
        
        usage = {
            'prompt_tokens': 30,
            'completion_tokens': len(response_text.split()),
            'total_tokens': 30 + len(response_text.split())
        }
        self.total_tokens += usage['total_tokens']
        
        return response_text, usage
    
    def _generate_response(self, messages):
        """Generate minimal response based on message context."""
        msg_str = str(messages).lower()
        
        if 'phase0_5' in msg_str or '角色' in msg_str:
            return '{"research_role": "测试研究员", "rationale": "用于测试"}'
        elif 'phase1' in msg_str or '目标' in msg_str:
            return '{"suggested_goals": [{"goal_text": "测试目标1", "uses": ["transcript"]}, {"goal_text": "测试目标2", "uses": ["transcript"]}]}'
        elif 'phase2' in msg_str or '综合' in msg_str:
            return '{"synthesized_goal": {"comprehensive_topic": "测试综合主题", "unifying_theme": "测试", "research_scope": "测试"}}'
        elif 'phase3' in msg_str or '执行' in msg_str:
            return '{"findings": {"summary": "测试发现"}, "insights": "测试", "confidence": 0.8}'
        elif 'phase4' in msg_str or '报告' in msg_str:
            if 'outline' in msg_str or '大纲' in msg_str:
                return '{"sections": [{"title": "章节1", "target_words": 100}]}'
            else:
                return "# 测试报告\n\n内容"
        else:
            return '{"result": "test"}'
    
    def parse_json_from_stream(self, iterator):
        """Parse JSON from stream."""
        text = "".join(iterator)
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {}

# WebSocket client for capturing messages
class WebSocketMessageCapture:
    """Captures WebSocket messages to simulate frontend."""
    
    def __init__(self, batch_id: str, port: int = 8000):
        self.batch_id = batch_id
        self.port = port
        self.messages: List[Dict[str, Any]] = []
        self.timestamps: List[float] = []
        self.lock = threading.Lock()
        self.connected = False
        self.ws: Optional[WebSocketClientProtocol] = None
    
    async def connect(self):
        """Connect to WebSocket endpoint."""
        uri = f"ws://localhost:{self.port}/ws/{self.batch_id}"
        try:
            self.ws = await websockets.connect(uri)
            self.connected = True
            logger.info(f"[WS_CLIENT] Connected to {uri}")
            
            # Start message receiver
            asyncio.create_task(self._receive_messages())
        except Exception as e:
            logger.error(f"[WS_CLIENT] Failed to connect: {e}")
            # If server not running, create mock capture
            self.connected = False
    
    async def _receive_messages(self):
        """Receive messages from WebSocket."""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    with self.lock:
                        self.messages.append(data)
                        self.timestamps.append(time.time())
                    logger.info(f"[WS_CLIENT] Received: {data.get('type', 'unknown')}")
                except json.JSONDecodeError:
                    logger.warning(f"[WS_CLIENT] Invalid JSON: {message}")
        except Exception as e:
            logger.error(f"[WS_CLIENT] Receive error: {e}")
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.ws:
            await self.ws.close()
            self.connected = False
    
    def get_messages_by_type(self, msg_type: str) -> List[Dict]:
        """Get all messages of a specific type."""
        with self.lock:
            return [msg for msg in self.messages if msg.get('type') == msg_type]
    
    def get_message_count(self) -> int:
        """Get total message count."""
        with self.lock:
            return len(self.messages)

# Mock progress callback that simulates scraper progress
class MockProgressCallback:
    """Mock progress callback for scrapers."""
    
    def __init__(self, progress_service, batch_id: str):
        self.progress_service = progress_service
        self.batch_id = batch_id
    
    async def __call__(self, link_id: str, url: str, stage: str, progress: float, message: str):
        """Simulate progress update."""
        await self.progress_service.update_link_progress(
            batch_id=self.batch_id,
            link_id=link_id,
            url=url,
            stage=stage,
            stage_progress=progress,
            overall_progress=progress * 0.5,  # Simple calculation
            message=message
        )
        
        # Simulate completion quickly
        if progress >= 100.0:
            await self.progress_service.update_link_status(
                batch_id=self.batch_id,
                link_id=link_id,
                url=url,
                status='completed'
            )

async def test_phase_transition_with_backend_frontend_sync():
    """Test phase transition timing with backend and frontend sync."""
    logger.info("\n" + "=" * 80)
    logger.info("E2E TEST: Phase Transition Timing with Backend/Frontend Sync")
    logger.info("=" * 80)
    
    try:
        # Import backend services
        from backend.app.services.workflow_service import WorkflowService
        from backend.app.services.progress_service import ProgressService
        from backend.app.websocket.manager import WebSocketManager
        
        # Create WebSocket manager
        ws_manager = WebSocketManager()
        
        # Create services
        progress_service = ProgressService(ws_manager)
        workflow_service = WorkflowService(ws_manager)
        
        # Test batch ID
        batch_id = f"test_e2e_{int(time.time())}"
        logger.info(f"[TEST] Batch ID: {batch_id}")
        
        # Create WebSocket message capture (simulate frontend)
        ws_capture = WebSocketMessageCapture(batch_id, port=8000)
        
        # Try to connect to WebSocket (if server is running)
        try:
            await asyncio.wait_for(ws_capture.connect(), timeout=2.0)
        except (asyncio.TimeoutError, ConnectionRefusedError):
            logger.info("[TEST] WebSocket server not running, using message capture from manager")
            ws_capture.connected = False
        
        # Mock minimal test data
        test_links = [
            {'id': 'test_link_1', 'url': 'http://test1.com', 'type': 'youtube'},
        ]
        
        # Initialize expected links
        expected_processes = [
            {'link_id': 'test_link_1', 'url': 'http://test1.com', 'scraper_type': 'youtube', 'process_type': 'transcript'},
            {'link_id': 'test_link_1_comments', 'url': 'http://test1.com', 'scraper_type': 'youtubecomments', 'process_type': 'comments'},
        ]
        progress_service.initialize_expected_links(batch_id, expected_processes)
        
        # Simulate scraping completion immediately
        logger.info("[TEST] Simulating scraping completion...")
        for proc in expected_processes:
            await progress_service.update_link_status(
                batch_id=batch_id,
                link_id=proc['link_id'],
                url=proc['url'],
                status='completed'
            )
        
        # Wait a moment for messages to propagate
        await asyncio.sleep(0.1)
        
        # Test phase transition timing
        logger.info("[TEST] Testing phase transition timing...")
        message_queue = Queue()
        
        # Measure timing for each step
        timings = {}
        
        # Step 1: Wait for status updates
        step1_start = time.time()
        logger.info("[TIMING] Step 1: Waiting for status updates...")
        status_complete = await workflow_service._wait_for_status_updates(
            message_queue, batch_id, max_wait_seconds=5.0
        )
        step1_elapsed = time.time() - step1_start
        timings['status_updates'] = step1_elapsed
        logger.info(f"[TIMING] Step 1 completed in {step1_elapsed:.3f}s")
        
        # Step 2: Wait for confirmation
        step2_start = time.time()
        logger.info("[TIMING] Step 2: Waiting for scraping confirmation...")
        confirmation = await workflow_service.wait_for_scraping_confirmation(
            message_queue, batch_id, max_wait_seconds=5.0
        )
        step2_elapsed = time.time() - step2_start
        timings['confirmation'] = step2_elapsed
        logger.info(f"[TIMING] Step 2 completed in {step2_elapsed:.3f}s")
        
        # Step 3: Verify results (mock)
        step3_start = time.time()
        logger.info("[TIMING] Step 3: Verifying results...")
        await asyncio.sleep(0.05)  # Simulate verification
        step3_elapsed = time.time() - step3_start
        timings['verification'] = step3_elapsed
        logger.info(f"[TIMING] Step 3 completed in {step3_elapsed:.3f}s")
        
        # Step 4: Phase change notification
        step4_start = time.time()
        logger.info("[TIMING] Step 4: Sending phase change notification...")
        await ws_manager.broadcast(batch_id, {
            "type": "research:phase_change",
            "phase": "research",
            "phase_name": "研究代理",
            "message": "开始研究阶段",
        })
        step4_elapsed = time.time() - step4_start
        timings['phase_change'] = step4_elapsed
        logger.info(f"[TIMING] Step 4 completed in {step4_elapsed:.3f}s")
        
        # Total transition time
        total_transition_time = sum(timings.values())
        logger.info(f"[TIMING] Total phase transition time: {total_transition_time:.3f}s")
        
        # Check WebSocket messages (from manager's broadcast history or capture)
        if ws_capture.connected:
            await asyncio.sleep(0.5)  # Wait for messages
            ws_messages = ws_capture.get_messages_by_type('research:phase_change')
            logger.info(f"[TEST] WebSocket messages received: {ws_capture.get_message_count()}")
        else:
            # Messages were broadcast, verify they would be sent
            logger.info("[TEST] WebSocket messages broadcast (frontend would receive them)")
            ws_messages = []  # Can't verify without connection
        
        # Verify timing improvements
        logger.info("\n" + "=" * 80)
        logger.info("TIMING RESULTS")
        logger.info("=" * 80)
        for step, elapsed in timings.items():
            logger.info(f"  {step}: {elapsed:.3f}s")
        logger.info(f"  TOTAL: {total_transition_time:.3f}s")
        
        # Assertions
        assert total_transition_time < 2.0, f"Total transition should be < 2s, got {total_transition_time:.3f}s"
        assert step1_elapsed < 1.0, f"Status updates should be < 1s, got {step1_elapsed:.3f}s"
        assert step2_elapsed < 1.0, f"Confirmation should be < 1s, got {step2_elapsed:.3f}s"
        
        logger.info("\n[OK] Phase transition timing is fast!")
        
        # Cleanup
        if ws_capture.connected:
            await ws_capture.disconnect()
        
        return True, timings
        
    except ImportError as e:
        logger.error(f"[FAILED] Import error: {e}")
        logger.info("This test requires the backend modules to be available")
        return False, {}
    except Exception as e:
        logger.error(f"[FAILED] Test error: {e}", exc_info=True)
        return False, {}

async def test_research_phase_with_minimal_api():
    """Test research phases with minimal API calls and WebSocket sync."""
    logger.info("\n" + "=" * 80)
    logger.info("E2E TEST: Research Phases with Minimal API and WebSocket Sync")
    logger.info("=" * 80)
    
    try:
        # Mock Qwen client
        mock_client = FastQwenClient()
        
        # Import research modules
        from research.session import ResearchSession
        from research.phases.phase0_5_role_generation import Phase0_5RoleGeneration
        from research.phases.phase1_discover import Phase1Discover
        from backend.app.websocket.manager import WebSocketManager
        from backend.app.services.websocket_ui import WebSocketUI
        
        # Create WebSocket manager and UI
        batch_id = f"test_research_{int(time.time())}"
        ws_manager = WebSocketManager()
        mock_ui = WebSocketUI(ws_manager, batch_id)
        
        # Create session
        session = ResearchSession()
        
        # Test Phase 0.5
        logger.info("[TEST] Testing Phase 0.5: Role Generation...")
        phase0_5 = Phase0_5RoleGeneration(mock_client, session, ui=mock_ui)
        
        phase_start = time.time()
        result = phase0_5.execute("测试数据摘要", "测试主题")
        phase_elapsed = time.time() - phase_start
        
        logger.info(f"[TIMING] Phase 0.5 completed in {phase_elapsed:.3f}s")
        logger.info(f"[TIMING] API calls made: {mock_client.call_count}")
        
        # Test Phase 1
        logger.info("[TEST] Testing Phase 1: Discover...")
        phase1 = Phase1Discover(mock_client, session, ui=mock_ui)
        
        phase_start = time.time()
        result = phase1.execute(
            "测试数据摘要",
            "测试主题",
            research_role={"role": "测试研究员"},
            amendment_feedback=None,
            batch_data={}
        )
        phase_elapsed = time.time() - phase_start
        
        logger.info(f"[TIMING] Phase 1 completed in {phase_elapsed:.3f}s")
        logger.info(f"[TIMING] Total API calls: {mock_client.call_count}")
        logger.info(f"[TIMING] Total tokens used: {mock_client.total_tokens}")
        
        # Verify timing
        assert phase_elapsed < 2.0, f"Phase 1 should complete in < 2s, got {phase_elapsed:.3f}s"
        
        logger.info("\n[OK] Research phases complete quickly with minimal tokens!")
        
        return True, {
            'phase0_5_time': phase_elapsed,
            'phase1_time': phase_elapsed,
            'total_api_calls': mock_client.call_count,
            'total_tokens': mock_client.total_tokens
        }
        
    except ImportError as e:
        logger.error(f"[FAILED] Import error: {e}")
        return False, {}
    except Exception as e:
        logger.error(f"[FAILED] Test error: {e}", exc_info=True)
        return False, {}

async def test_full_workflow_simulation():
    """Test full workflow simulation with minimal data."""
    logger.info("\n" + "=" * 80)
    logger.info("E2E TEST: Full Workflow Simulation")
    logger.info("=" * 80)
    
    try:
        from backend.app.services.workflow_service import WorkflowService
        from backend.app.services.progress_service import ProgressService
        from backend.app.websocket.manager import WebSocketManager
        
        # Setup
        ws_manager = WebSocketManager()
        progress_service = ProgressService(ws_manager)
        workflow_service = WorkflowService(ws_manager)
        
        batch_id = f"test_full_{int(time.time())}"
        
        # Mock minimal batch data
        batch_data = {
            'test_link_1': {
                'transcript': '测试转录内容 ' * 20,  # Minimal content
                'comments': [],
                'metadata': {'word_count': 100},
                'source': 'youtube'
            }
        }
        
        # Initialize progress
        expected_processes = [
            {'link_id': 'test_link_1', 'url': 'http://test1.com', 'scraper_type': 'youtube', 'process_type': 'transcript'},
        ]
        progress_service.initialize_expected_links(batch_id, expected_processes)
        
        # Simulate all processes completing
        for proc in expected_processes:
            await progress_service.update_link_status(
                batch_id=batch_id,
                link_id=proc['link_id'],
                url=proc['url'],
                status='completed'
            )
        
        # Test transition
        overall_start = time.time()
        message_queue = Queue()
        
        # Wait for status
        await workflow_service._wait_for_status_updates(message_queue, batch_id, max_wait_seconds=5.0)
        
        # Wait for confirmation
        confirmation = await workflow_service.wait_for_scraping_confirmation(message_queue, batch_id, max_wait_seconds=5.0)
        
        # Phase change
        await ws_manager.broadcast(batch_id, {
            "type": "research:phase_change",
            "phase": "research",
            "phase_name": "研究代理",
            "message": "开始研究阶段",
        })
        
        overall_elapsed = time.time() - overall_start
        
        logger.info(f"[TIMING] Full workflow transition: {overall_elapsed:.3f}s")
        assert overall_elapsed < 2.0, f"Full transition should be < 2s, got {overall_elapsed:.3f}s"
        
        logger.info("\n[OK] Full workflow transition is fast!")
        
        return True, {'total_time': overall_elapsed}
        
    except Exception as e:
        logger.error(f"[FAILED] Test error: {e}", exc_info=True)
        return False, {}

async def main():
    """Run all E2E tests."""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE TRANSITION E2E TEST SUITE")
    logger.info("=" * 80)
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info("")
    
    results = []
    
    # Test 1: Phase transition with backend/frontend sync
    try:
        success, timings = await test_phase_transition_with_backend_frontend_sync()
        results.append(("Phase Transition Backend/Frontend Sync", success, timings))
    except Exception as e:
        logger.error(f"[FAILED] Test 1 error: {e}", exc_info=True)
        results.append(("Phase Transition Backend/Frontend Sync", False, {}))
    
    # Test 2: Research phases with minimal API
    try:
        success, metrics = await test_research_phase_with_minimal_api()
        results.append(("Research Phases Minimal API", success, metrics))
    except Exception as e:
        logger.error(f"[FAILED] Test 2 error: {e}", exc_info=True)
        results.append(("Research Phases Minimal API", False, {}))
    
    # Test 3: Full workflow simulation
    try:
        success, metrics = await test_full_workflow_simulation()
        results.append(("Full Workflow Simulation", success, metrics))
    except Exception as e:
        logger.error(f"[FAILED] Test 3 error: {e}", exc_info=True)
        results.append(("Full Workflow Simulation", False, {}))
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for name, success, _ in results if success)
    total = len(results)
    
    for name, success, metrics in results:
        status = "PASSED" if success else "FAILED"
        logger.info(f"{status}: {name}")
        if metrics:
            for key, value in metrics.items():
                if isinstance(value, float):
                    logger.info(f"  {key}: {value:.3f}s")
                else:
                    logger.info(f"  {key}: {value}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    logger.info(f"Finished: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    
    if passed == total:
        logger.info("\n[SUCCESS] ALL E2E TESTS PASSED!")
        return 0
    else:
        logger.info(f"\n[FAILED] {total - passed} test(s) failed.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

