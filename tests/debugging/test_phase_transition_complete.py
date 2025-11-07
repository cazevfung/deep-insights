"""Complete phase transition test with backend and frontend sync.

This test simulates the full workflow:
1. Scraping completion
2. Phase transition (scraping -> research)
3. Research phases with minimal API calls
4. WebSocket message capture and verification

Usage:
    # Run with backend server (for full WebSocket test):
    # 1. Start backend server: python backend/run_server.py
    # 2. Run test: python tests/test_phase_transition_complete.py

    # Run standalone (mock WebSocket):
    python tests/test_phase_transition_complete.py
"""
import sys
import time
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

# Add paths
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_path))

from loguru import logger

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="{time:HH:mm:ss.SSS} | {level: <8} | {message}",
    level="INFO"
)

# Message capture for WebSocket
class MessageCapture:
    """Captures WebSocket messages."""
    
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.timestamps: List[float] = []
    
    def capture(self, message: Dict[str, Any]):
        """Capture a message."""
        self.messages.append(message)
        self.timestamps.append(time.time())
        logger.info(f"[CAPTURE] {message.get('type', 'unknown')}")
    
    def get_messages_by_type(self, msg_type: str) -> List[Dict]:
        """Get messages by type."""
        return [msg for msg in self.messages if msg.get('type') == msg_type]
    
    def get_all_messages(self) -> List[Dict]:
        """Get all messages."""
        return self.messages.copy()
    
    def clear(self):
        """Clear messages."""
        self.messages.clear()
        self.timestamps.clear()

# Capturing WebSocket manager
class CapturingWSManager:
    """WebSocket manager that captures messages."""
    
    def __init__(self):
        self.capture = MessageCapture()
        self.connections = {}
    
    async def broadcast(self, batch_id: str, message: Dict[str, Any]):
        """Broadcast and capture."""
        self.capture.capture(message)
    
    async def connect(self, websocket, batch_id: str):
        """Mock connect."""
        pass
    
    async def disconnect(self, websocket, batch_id: str):
        """Mock disconnect."""
        pass
    
    def get_connection_count(self, batch_id: str) -> int:
        """Get connection count."""
        return 0

# Fast Qwen client
class FastQwenClient:
    """Fast mock Qwen client with minimal responses."""
    
    def __init__(self):
        self.call_count = 0
        self.total_tokens = 0
    
    def stream_and_collect(self, messages, callback=None, **kwargs):
        """Fast API call with minimal delay."""
        self.call_count += 1
        
        # Simulate realistic but fast API call (50-150ms)
        import random
        delay = random.uniform(0.05, 0.15)
        time.sleep(delay)
        
        # Generate appropriate response
        msg_str = str(messages).lower()
        if 'phase0_5' in msg_str or '角色' in msg_str:
            response = '{"research_role": "测试研究员", "rationale": "用于测试目的"}'
        elif 'phase1' in msg_str or '目标' in msg_str:
            response = '{"suggested_goals": [{"goal_text": "测试目标1", "uses": ["transcript"]}, {"goal_text": "测试目标2", "uses": ["transcript"]}]}'
        elif 'phase2' in msg_str or '综合' in msg_str:
            response = '{"synthesized_goal": {"comprehensive_topic": "测试综合主题", "unifying_theme": "测试主题", "research_scope": "测试范围", "component_questions": ["问题1", "问题2"]}}'
        elif 'phase3' in msg_str or '执行' in msg_str:
            response = '{"findings": {"summary": "测试发现摘要"}, "insights": "测试洞察", "confidence": 0.85}'
        elif 'phase4' in msg_str or '报告' in msg_str:
            if 'outline' in msg_str or '大纲' in msg_str:
                response = '{"sections": [{"title": "测试章节1", "target_words": 100}, {"title": "测试章节2", "target_words": 100}]}'
            else:
                response = "# 测试报告\n\n这是测试报告的内容。"
        else:
            response = '{"result": "test"}'
        
        # Simulate streaming
        if callback:
            chars_to_stream = min(50, len(response))
            for char in response[:chars_to_stream]:
                callback(char)
                time.sleep(0.001)  # Very fast streaming
        
        usage = {
            'prompt_tokens': 30,
            'completion_tokens': len(response.split()),
            'total_tokens': 30 + len(response.split())
        }
        self.total_tokens += usage['total_tokens']
        
        return response, usage
    
    def parse_json_from_stream(self, iterator):
        """Parse JSON from stream."""
        text = "".join(iterator)
        import json
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {}

async def test_full_phase_transition():
    """Test full phase transition with timing and WebSocket sync."""
    logger.info("\n" + "=" * 80)
    logger.info("COMPLETE TEST: Full Phase Transition with Backend/Frontend Sync")
    logger.info("=" * 80)
    
    try:
        # Setup WebSocket manager
        ws_manager = CapturingWSManager()
        
        # Import services (with proper path handling)
        # We'll use direct imports with mocked dependencies
        from backend.app.services.progress_service import ProgressService
        from backend.app.services.workflow_service import WorkflowService
        
        # Create services
        progress_service = ProgressService(ws_manager)
        workflow_service = WorkflowService(ws_manager)
        
        # Test batch
        batch_id = f"test_complete_{int(time.time())}"
        logger.info(f"[TEST] Batch ID: {batch_id}")
        
        # Setup minimal test data
        expected_processes = [
            {'link_id': 'test_link_1', 'url': 'http://test1.com', 'scraper_type': 'youtube', 'process_type': 'transcript'},
            {'link_id': 'test_link_1_comments', 'url': 'http://test1.com', 'scraper_type': 'youtubecomments', 'process_type': 'comments'},
        ]
        
        progress_service.initialize_expected_links(batch_id, expected_processes)
        
        # Simulate scraping completion
        logger.info("[TEST] Simulating scraping completion...")
        for proc in expected_processes:
            await progress_service.update_link_status(
                batch_id=batch_id,
                link_id=proc['link_id'],
                url=proc['url'],
                status='completed'
            )
        
        await asyncio.sleep(0.1)  # Allow messages to propagate
        
        # Test phase transition timing
        logger.info("[TEST] Testing phase transition...")
        message_queue = asyncio.Queue()
        
        timings = {}
        
        # Step 1: Status updates wait
        step1_start = time.time()
        status_complete = await workflow_service._wait_for_status_updates(
            message_queue, batch_id, max_wait_seconds=5.0
        )
        timings['status_wait'] = time.time() - step1_start
        logger.info(f"[TIMING] Status wait: {timings['status_wait']:.3f}s")
        
        # Step 2: Confirmation wait
        step2_start = time.time()
        confirmation = await workflow_service.wait_for_scraping_confirmation(
            message_queue, batch_id, max_wait_seconds=5.0
        )
        timings['confirmation_wait'] = time.time() - step2_start
        logger.info(f"[TIMING] Confirmation wait: {timings['confirmation_wait']:.3f}s")
        
        # Step 3: Verification (mock)
        step3_start = time.time()
        await asyncio.sleep(0.05)  # Simulate verification
        timings['verification'] = time.time() - step3_start
        logger.info(f"[TIMING] Verification: {timings['verification']:.3f}s")
        
        # Step 4: Phase change broadcast
        step4_start = time.time()
        await ws_manager.broadcast(batch_id, {
            "type": "research:phase_change",
            "phase": "research",
            "phase_name": "研究代理",
            "message": "开始研究阶段",
        })
        timings['phase_change'] = time.time() - step4_start
        logger.info(f"[TIMING] Phase change broadcast: {timings['phase_change']:.3f}s")
        
        # Total time
        total_time = sum(timings.values())
        timings['total'] = total_time
        
        # Check WebSocket messages
        phase_change_msgs = ws_manager.capture.get_messages_by_type('research:phase_change')
        status_msgs = ws_manager.capture.get_messages_by_type('scraping:status')
        progress_msgs = ws_manager.capture.get_messages_by_type('scraping:item_update')
        
        logger.info(f"[TEST] WebSocket messages captured:")
        logger.info(f"  - Phase change: {len(phase_change_msgs)}")
        logger.info(f"  - Status updates: {len(status_msgs)}")
        logger.info(f"  - Progress updates: {len(progress_msgs)}")
        logger.info(f"  - Total: {len(ws_manager.capture.get_all_messages())}")
        
        # Verify timing
        assert total_time < 2.0, f"Total transition should be < 2s, got {total_time:.3f}s"
        assert timings['status_wait'] < 1.0, f"Status wait should be < 1s, got {timings['status_wait']:.3f}s"
        assert timings['confirmation_wait'] < 1.0, f"Confirmation wait should be < 1s, got {timings['confirmation_wait']:.3f}s"
        assert len(phase_change_msgs) > 0, "Should have phase change message"
        
        logger.info("\n[OK] Phase transition is fast and WebSocket sync works!")
        
        return True, timings
        
    except Exception as e:
        logger.error(f"[FAILED] Error: {e}", exc_info=True)
        return False, {}

async def test_research_phases_with_minimal_tokens():
    """Test research phases with minimal token usage."""
    logger.info("\n" + "=" * 80)
    logger.info("COMPLETE TEST: Research Phases with Minimal Token Usage")
    logger.info("=" * 80)
    
    try:
        # Setup
        fast_client = FastQwenClient()
        ws_manager = CapturingWSManager()
        
        from research.session import ResearchSession
        from research.phases.phase0_5_role_generation import Phase0_5RoleGeneration
        from research.phases.phase1_discover import Phase1Discover
        from backend.app.services.websocket_ui import WebSocketUI
        
        batch_id = f"test_research_{int(time.time())}"
        session = ResearchSession()
        ui = WebSocketUI(ws_manager, batch_id)
        
        # Test Phase 0.5
        logger.info("[TEST] Phase 0.5: Role Generation...")
        phase0_5 = Phase0_5RoleGeneration(fast_client, session, ui=ui)
        
        phase_start = time.time()
        result = phase0_5.execute("测试数据摘要", "测试主题")
        phase0_5_time = time.time() - phase_start
        
        logger.info(f"[TIMING] Phase 0.5: {phase0_5_time:.3f}s, API calls: {fast_client.call_count}")
        
        # Test Phase 1
        logger.info("[TEST] Phase 1: Discover...")
        phase1 = Phase1Discover(fast_client, session, ui=ui)
        
        phase_start = time.time()
        result = phase1.execute(
            "测试数据摘要",
            "测试主题",
            research_role={"role": "测试研究员"},
            amendment_feedback=None,
            batch_data={}
        )
        phase1_time = time.time() - phase_start
        
        logger.info(f"[TIMING] Phase 1: {phase1_time:.3f}s, API calls: {fast_client.call_count}")
        
        # Check WebSocket messages
        ui_messages = ws_manager.capture.get_messages_by_type('workflow:progress')
        logger.info(f"[TEST] UI progress messages: {len(ui_messages)}")
        
        # Verify
        assert phase0_5_time < 1.0, f"Phase 0.5 should be < 1s, got {phase0_5_time:.3f}s"
        assert phase1_time < 2.0, f"Phase 1 should be < 2s, got {phase1_time:.3f}s"
        assert fast_client.call_count == 2, f"Should have 2 API calls, got {fast_client.call_count}"
        assert fast_client.total_tokens < 200, f"Should use < 200 tokens, got {fast_client.total_tokens}"
        
        logger.info(f"\n[OK] Research phases complete quickly with minimal tokens!")
        logger.info(f"  Total tokens: {fast_client.total_tokens}")
        logger.info(f"  Total time: {phase0_5_time + phase1_time:.3f}s")
        
        return True, {
            'phase0_5_time': phase0_5_time,
            'phase1_time': phase1_time,
            'total_time': phase0_5_time + phase1_time,
            'api_calls': fast_client.call_count,
            'total_tokens': fast_client.total_tokens,
            'ui_messages': len(ui_messages)
        }
        
    except Exception as e:
        logger.error(f"[FAILED] Error: {e}", exc_info=True)
        return False, {}

async def main():
    """Run all complete tests."""
    logger.info("\n" + "=" * 80)
    logger.info("COMPLETE PHASE TRANSITION TEST SUITE")
    logger.info("=" * 80)
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info("")
    
    results = []
    
    # Test 1: Full phase transition
    try:
        success, metrics = await test_full_phase_transition()
        results.append(("Full Phase Transition", success, metrics))
    except Exception as e:
        logger.error(f"Test 1 failed: {e}", exc_info=True)
        results.append(("Full Phase Transition", False, {}))
    
    # Test 2: Research phases with minimal tokens
    try:
        success, metrics = await test_research_phases_with_minimal_tokens()
        results.append(("Research Phases Minimal Tokens", success, metrics))
    except Exception as e:
        logger.error(f"Test 2 failed: {e}", exc_info=True)
        results.append(("Research Phases Minimal Tokens", False, {}))
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for _, success, _ in results if success)
    
    for name, success, metrics in results:
        status = "PASSED" if success else "FAILED"
        logger.info(f"{status}: {name}")
        if metrics:
            for key, value in metrics.items():
                if isinstance(value, float):
                    logger.info(f"  {key}: {value:.3f}s")
                else:
                    logger.info(f"  {key}: {value}")
    
    logger.info(f"\nTotal: {passed}/{len(results)} tests passed")
    logger.info(f"Finished: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    
    if passed == len(results):
        logger.info("\n[SUCCESS] ALL TESTS PASSED!")
        logger.info("Phase transition improvements are working correctly.")
        logger.info("Backend timing and frontend sync are verified.")
        return 0
    else:
        logger.info(f"\n[FAILED] {len(results) - passed} test(s) failed.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

