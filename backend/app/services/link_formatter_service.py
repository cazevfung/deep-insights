"""
Link formatter service wrapper.
"""
from typing import List, Dict
from pathlib import Path
import json
import sys
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from utils.link_formatter import build_items, current_batch_id
except ImportError as e:
    logger.error(f"Failed to import from utils.link_formatter: {e}")
    raise

from datetime import datetime, timezone


def iso_timestamp() -> str:
    """Get ISO timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()


class LinkFormatterService:
    """Service for formatting links and creating batches."""
    
    def format_links(self, urls: List[str]) -> Dict:
        """
        Format URLs and create batch.
        
        Args:
            urls: List of URLs to format
            
        Returns:
            Dict with batch_id, items, and total count
        """
        try:
            logger.debug(f"format_links called with {len(urls) if urls else 0} URLs")
            
            # Validate input
            if not urls:
                raise ValueError("URLs list is empty")
            
            if not isinstance(urls, list):
                raise ValueError(f"URLs must be a list, got {type(urls)}")
            
            # Filter out empty URLs
            valid_urls = [url for url in urls if url and isinstance(url, str) and url.strip()]
            logger.debug(f"Filtered to {len(valid_urls)} valid URLs")
            
            if not valid_urls:
                raise ValueError("No valid URLs provided after filtering")
            
            # Build items using link_formatter logic
            logger.debug("Calling build_items...")
            items = build_items(valid_urls)
            logger.debug(f"Built {len(items)} items")
            
            logger.debug("Calling current_batch_id...")
            batch_id = current_batch_id()
            logger.debug(f"Got batch_id: {batch_id}")
            
            # Save to test_links.json
            target_file = project_root / "tests" / "data" / "test_links.json"
            logger.debug(f"Target file: {target_file}")
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            payload = {
                "batchId": batch_id,
                "createdAt": iso_timestamp(),
                "links": items,
            }
            
            # Write file with error handling
            logger.debug(f"Writing to {target_file}...")
            try:
                target_file.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                logger.debug("File written successfully")
            except IOError as e:
                logger.error(f"IOError writing file: {e}")
                raise IOError(f"Failed to write to {target_file}: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error writing file: {e}", exc_info=True)
                raise
            
            result = {
                "batch_id": batch_id,
                "items": items,
                "total": len(items),
            }
            logger.debug(f"Returning result with {result['total']} items")
            return result
            
        except Exception as e:
            logger.error(f"Exception in format_links: {e}", exc_info=True)
            import traceback
            error_msg = f"Failed to format links: {str(e)}\n{traceback.format_exc()}"
            raise Exception(error_msg)
