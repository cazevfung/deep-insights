"""
Integration test for scraping workflow with invalid tasks scenario.

This test simulates the real-world scenario where:
1. Tasks are created and added to the queue
2. Some tasks complete/fail during processing
3. Race conditions cause invalid tasks to remain in queue
4. Workers should continue processing valid tasks
5. System should complete successfully

This test uses the actual scraping control center and workflow code.
"""

import sys
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from queue import Queue

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.lib.scraping_control_center import (
    ScrapingControlCenter,
    ScrapingTask,
    TaskStatus,
    WorkerState
)
from loguru import logger

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)


class MockProgressCallback:
    """Mock progress callback to track messages."""
    
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.completed_tasks: List[str] = []
        self.failed_tasks: List[str] = []
        self.lock = threading.Lock()
    
    def __call__(self, message: dict):
        with self.lock:
            self.messages.append(message)
            msg_type = message.get('type', '')
            if msg_type == 'scraping:complete_link':
                status = message.get('status', '')
                link_id = message.get('link_id', '')
                if status == 'success':
                    self.completed_tasks.append(link_id)
                elif status == 'failed':
                    self.failed_tasks.append(link_id)
                logger.info(f"Task completed: {link_id} - {status}")
    
    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            return {
                'total_messages': len(self.messages),
                'completed': len(self.completed_tasks),
                'failed': len(self.failed_tasks),
                'completed_task_ids': self.completed_tasks.copy(),
                'failed_task_ids': self.failed_tasks.copy()
            }


def create_mock_scraper_result(should_succeed: bool, task: ScrapingTask) -> Dict[str, Any]:
    """Create a mock scraper result."""
    if should_succeed:
        return {
            'success': True,
            'url': task.url,
            'link_id': task.link_id,
            'batch_id': task.batch_id,
            'content': f'Mock content for {task.url}',
            'word_count': 100,
            'title': f'Title for {task.link_id}'
        }
    else:
        return {
            'success': False,
            'url': task.url,
            'link_id': task.link_id,
            'batch_id': task.batch_id,
            'error': 'Mock extraction error',
            'word_count': 0
        }


def test_scenario_1_all_tasks_valid():
    """Test scenario: All tasks are valid and should complete."""
    print("\n" + "="*80)
    print("SCENARIO 1: All tasks valid")
    print("="*80)
    
    batch_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    progress_callback = MockProgressCallback()
    
    # Create control center
    control_center = ScrapingControlCenter(
        worker_pool_size=2,
        progress_callback=progress_callback
    )
    
    # Create 5 valid tasks
    tasks = []
    for i in range(5):
        task = ScrapingTask(
            task_id=f"task_{i:03d}",
            link_id=f"link_{i}",
            url=f"https://example.com/valid_{i}",
            link_type='article',
            scraper_type='article',
            batch_id=batch_id,
            status=TaskStatus.PENDING
        )
        tasks.append(task)
    
    # Add tasks
    control_center.add_tasks(tasks)
    
    # Manually process tasks (simulate workers)
    # In real scenario, workers would do this automatically
    print(f"Added {len(tasks)} tasks to queue")
    
    # Check initial state
    queue_stats = control_center.task_queue.get_statistics()
    state_stats = control_center.state_tracker.get_statistics()
    print(f"Initial queue size: {queue_stats['queue_size']}")
    print(f"Initial pending tasks: {state_stats['pending']}")
    
    assert queue_stats['queue_size'] == 5, "All 5 tasks should be in queue"
    assert state_stats['pending'] == 5, "All 5 tasks should be pending"
    
    print("✓ Scenario 1 setup verified")


def test_scenario_2_mixed_valid_invalid():
    """Test scenario: Mix of valid and invalid tasks."""
    print("\n" + "="*80)
    print("SCENARIO 2: Mixed valid and invalid tasks")
    print("="*80)
    
    batch_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    progress_callback = MockProgressCallback()
    
    # Create control center
    control_center = ScrapingControlCenter(
        worker_pool_size=2,
        progress_callback=progress_callback
    )
    
    # Create mix of tasks
    tasks = []
    
    # 3 valid tasks
    for i in range(3):
        task = ScrapingTask(
            task_id=f"valid_{i:03d}",
            link_id=f"link_valid_{i}",
            url=f"https://example.com/valid_{i}",
            link_type='article',
            scraper_type='article',
            batch_id=batch_id,
            status=TaskStatus.PENDING
        )
        tasks.append(task)
    
    # 2 invalid tasks (already completed)
    for i in range(3, 5):
        task = ScrapingTask(
            task_id=f"invalid_{i:03d}",
            link_id=f"link_invalid_{i}",
            url=f"https://example.com/invalid_{i}",
            link_type='article',
            scraper_type='article',
            batch_id=batch_id,
            status=TaskStatus.COMPLETED
        )
        tasks.append(task)
    
    # Add tasks
    control_center.add_tasks(tasks)
    
    # Check that only valid tasks are in queue
    queue_stats = control_center.task_queue.get_statistics()
    state_stats = control_center.state_tracker.get_statistics()
    
    print(f"Total tasks added: {len(tasks)}")
    print(f"Queue size: {queue_stats['queue_size']} (expected 3)")
    print(f"State tracker total: {state_stats['total']} (expected 5)")
    print(f"Pending in tracker: {state_stats['pending']} (expected 3)")
    print(f"Completed in tracker: {state_stats['completed']} (expected 2)")
    
    assert queue_stats['queue_size'] == 3, "Only 3 valid tasks should be in queue"
    assert state_stats['total'] == 5, "All 5 tasks should be in tracker"
    assert state_stats['pending'] == 3, "3 tasks should be pending"
    assert state_stats['completed'] == 2, "2 tasks should be completed"
    
    print("✓ Scenario 2 verified: Invalid tasks not added to queue")


def test_scenario_3_race_condition_simulation():
    """Test scenario: Simulate race condition where tasks become invalid after queuing."""
    print("\n" + "="*80)
    print("SCENARIO 3: Race condition simulation")
    print("="*80)
    
    batch_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    progress_callback = MockProgressCallback()
    
    # Create control center
    control_center = ScrapingControlCenter(
        worker_pool_size=2,
        progress_callback=progress_callback
    )
    
    # Create valid tasks
    tasks = []
    for i in range(4):
        task = ScrapingTask(
            task_id=f"task_{i:03d}",
            link_id=f"link_{i}",
            url=f"https://example.com/{i}",
            link_type='article',
            scraper_type='article',
            batch_id=batch_id,
            status=TaskStatus.PENDING
        )
        tasks.append(task)
    
    # Add tasks normally
    control_center.add_tasks(tasks)
    
    # Simulate race condition: mark some tasks as completed AFTER they're queued
    # This simulates the scenario where a task completes while still in queue
    for i, task in enumerate(tasks[:2]):  # Mark first 2 as completed
        control_center.state_tracker.update_task_state(
            task.task_id,
            TaskStatus.COMPLETED
        )
        logger.info(f"Simulated race: Task {task.task_id} marked as completed")
    
    # Manually add invalid tasks to queue (bypassing validation)
    # This simulates tasks that became invalid after being queued
    for i, task in enumerate(tasks[2:4]):  # Mark next 2 as failed
        control_center.state_tracker.update_task_state(
            task.task_id,
            TaskStatus.FAILED
        )
        # Manually add to queue to simulate the bug scenario
        control_center.task_queue.add_task(task)
        logger.info(f"Simulated race: Task {task.task_id} marked as failed and added to queue")
    
    print(f"\nInitial queue size: {control_center.task_queue.get_queue_size()}")
    
    # Start control center - workers should clean up invalid tasks
    control_center.start()
    
    # Wait for workers to process
    print("Waiting for workers to process tasks...")
    time.sleep(3)
    
    # Check queue - should be empty or only have valid tasks
    queue_stats = control_center.task_queue.get_statistics()
    state_stats = control_center.state_tracker.get_statistics()
    
    print(f"\nAfter processing:")
    print(f"Queue size: {queue_stats['queue_size']}")
    print(f"Pending: {state_stats['pending']}")
    print(f"Processing: {state_stats['processing']}")
    print(f"Completed: {state_stats['completed']}")
    print(f"Failed: {state_stats['failed']}")
    
    # Shutdown
    control_center.shutdown(wait=True, timeout=5.0)
    
    # Final check
    final_queue_stats = control_center.task_queue.get_statistics()
    final_state_stats = control_center.state_tracker.get_statistics()
    
    print(f"\nFinal state:")
    print(f"Queue size: {final_queue_stats['queue_size']} (should be 0)")
    print(f"Pending: {final_state_stats['pending']} (should be 0)")
    print(f"Processing: {final_state_stats['processing']} (should be 0)")
    
    # Queue should be empty after cleanup
    assert final_queue_stats['queue_size'] == 0, "Queue should be empty after cleanup"
    
    print("✓ Scenario 3 verified: Race condition handled correctly")


def test_scenario_4_worker_retry_exhaustion():
    """Test scenario: Workers exhaust retries and cleanup invalid tasks."""
    print("\n" + "="*80)
    print("SCENARIO 4: Worker retry exhaustion and cleanup")
    print("="*80)
    
    batch_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    progress_callback = MockProgressCallback()
    
    # Create control center
    control_center = ScrapingControlCenter(
        worker_pool_size=2,
        progress_callback=progress_callback
    )
    
    # Create many invalid tasks (all completed)
    invalid_tasks = []
    for i in range(10):
        task = ScrapingTask(
            task_id=f"invalid_{i:03d}",
            link_id=f"link_invalid_{i}",
            url=f"https://example.com/invalid_{i}",
            link_type='article',
            scraper_type='article',
            batch_id=batch_id,
            status=TaskStatus.PENDING
        )
        invalid_tasks.append(task)
        # Add to tracker and mark as completed
        control_center.state_tracker.add_task(task)
        control_center.state_tracker.update_task_state(
            task.task_id,
            TaskStatus.COMPLETED
        )
        # Manually add to queue (bypassing validation)
        control_center.task_queue.add_task(task)
    
    print(f"Added {len(invalid_tasks)} invalid tasks to queue")
    print(f"Initial queue size: {control_center.task_queue.get_queue_size()}")
    
    # Start control center
    control_center.start()
    
    # Wait for workers to exhaust retries and cleanup
    print("Waiting for workers to exhaust retries and cleanup...")
    time.sleep(5)
    
    # Check queue - should be empty after cleanup
    queue_stats = control_center.task_queue.get_statistics()
    state_stats = control_center.state_tracker.get_statistics()
    
    print(f"\nAfter cleanup:")
    print(f"Queue size: {queue_stats['queue_size']} (should be 0)")
    print(f"Completed in tracker: {state_stats['completed']} (should be 10)")
    
    # Shutdown
    control_center.shutdown(wait=True, timeout=5.0)
    
    # Final check
    final_queue_stats = control_center.task_queue.get_statistics()
    print(f"\nFinal queue size: {final_queue_stats['queue_size']} (should be 0)")
    
    assert final_queue_stats['queue_size'] == 0, "Queue should be empty after cleanup"
    
    print("✓ Scenario 4 verified: Worker retry exhaustion triggers cleanup")


def run_all_scenarios():
    """Run all test scenarios."""
    print("\n" + "="*80)
    print("SCRAPING WORKFLOW INVALID TASKS INTEGRATION TEST")
    print("="*80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    try:
        test_scenario_1_all_tasks_valid()
        results.append(("Scenario 1", True))
    except Exception as e:
        print(f"❌ Scenario 1 FAILED: {e}")
        results.append(("Scenario 1", False))
        import traceback
        traceback.print_exc()
    
    try:
        test_scenario_2_mixed_valid_invalid()
        results.append(("Scenario 2", True))
    except Exception as e:
        print(f"❌ Scenario 2 FAILED: {e}")
        results.append(("Scenario 2", False))
        import traceback
        traceback.print_exc()
    
    try:
        test_scenario_3_race_condition_simulation()
        results.append(("Scenario 3", True))
    except Exception as e:
        print(f"❌ Scenario 3 FAILED: {e}")
        results.append(("Scenario 3", False))
        import traceback
        traceback.print_exc()
    
    try:
        test_scenario_4_worker_retry_exhaustion()
        results.append(("Scenario 4", True))
    except Exception as e:
        print(f"❌ Scenario 4 FAILED: {e}")
        results.append(("Scenario 4", False))
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for scenario_name, passed in results:
        status = "✓ PASSED" if passed else "❌ FAILED"
        print(f"{scenario_name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("\n" + "="*80)
        print("ALL SCENARIOS PASSED ✓")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("SOME SCENARIOS FAILED ❌")
        print("="*80)
    
    return all_passed


if __name__ == "__main__":
    success = run_all_scenarios()
    sys.exit(0 if success else 1)


