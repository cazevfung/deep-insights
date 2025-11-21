"""Quick test to check imports."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add backend directory to path
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

print("Step 1: Testing Config import...")
try:
    from core.config import Config
    print("  ✓ Config imported successfully")
except Exception as e:
    print(f"  ✗ Config import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 2: Testing Config initialization...")
try:
    config = Config()
    print("  ✓ Config initialized successfully")
except Exception as e:
    print(f"  ✗ Config initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 3: Testing ChannelScraperService import...")
try:
    from app.services.channel_scraper_service import ChannelScraperService
    print("  ✓ ChannelScraperService imported successfully")
except Exception as e:
    print(f"  ✗ ChannelScraperService import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 4: Testing NewsOutlineService import...")
try:
    from app.services.news_outline_service import NewsOutlineService
    print("  ✓ NewsOutlineService imported successfully")
except Exception as e:
    print(f"  ✗ NewsOutlineService import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 5: Testing NewsArticleService import...")
try:
    from app.services.news_article_service import NewsArticleService
    print("  ✓ NewsArticleService imported successfully")
except Exception as e:
    print(f"  ✗ NewsArticleService import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 6: Testing NewsSummaryWorkflowService import...")
try:
    from app.services.news_summary_workflow_service import NewsSummaryWorkflowService
    print("  ✓ NewsSummaryWorkflowService imported successfully")
except Exception as e:
    print(f"  ✗ NewsSummaryWorkflowService import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 7: Testing NewsSummaryWorkflowService initialization...")
try:
    service = NewsSummaryWorkflowService(config)
    print("  ✓ NewsSummaryWorkflowService initialized successfully")
except Exception as e:
    print(f"  ✗ NewsSummaryWorkflowService initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✓ All imports and initializations successful!")

