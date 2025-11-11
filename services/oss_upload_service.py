"""Service for uploading files to Alibaba Cloud OSS with public access."""
import os
import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class OSSUploadService:
    """Service for uploading files to Alibaba Cloud OSS."""
    
    def __init__(self, config=None):
        """
        Initialize OSS upload service.
        
        Args:
            config: Config object with OSS credentials. If None, will load from config.yaml
        """
        if config is None:
            from core.config import Config
            config = Config()
        
        self.config = config
        
        # Get OSS credentials - try from dedicated 'oss' section first, fallback to bilibili config
        self.access_key_id = (
            config.get('oss.access_key_id') or 
            config.get('scrapers.bilibili.oss_access_key_id')
        )
        self.access_key_secret = (
            config.get('oss.access_key_secret') or 
            config.get('scrapers.bilibili.oss_access_key_secret')
        )
        self.bucket_name = (
            config.get('oss.bucket') or 
            config.get('scrapers.bilibili.oss_bucket')
        )
        self.endpoint = (
            config.get('oss.endpoint') or 
            config.get('scrapers.bilibili.oss_endpoint', 'https://oss-cn-beijing.aliyuncs.com')
        )
        self.reports_prefix = config.get('oss.reports_prefix', 'research-reports')
        
        # Whether to set public-read ACL on individual files
        # If False, relies on bucket-level public read policy
        # Set to False if you get "Put public object acl is not allowed" error
        self.set_public_acl = config.get('oss.set_public_acl', False)
        
        # Validate credentials
        if not all([self.access_key_id, self.access_key_secret, self.bucket_name]):
            logger.warning(
                "[OSSUpload] Missing OSS credentials! Please configure in config.yaml:\n"
                "  oss:\n"
                "    access_key_id: 'YOUR_KEY_ID'\n"
                "    access_key_secret: 'YOUR_KEY_SECRET'\n"
                "    bucket: 'YOUR_BUCKET_NAME'\n"
                "    endpoint: 'https://oss-cn-beijing.aliyuncs.com'\n"
                "    reports_prefix: 'research-reports'  # Optional, defaults to 'research-reports'"
            )
            self._has_credentials = False
        else:
            self._has_credentials = True
            logger.info(f"[OSSUpload] Initialized with bucket: {self.bucket_name}")
    
    def upload_html_report(
        self, 
        html_file_path: str, 
        session_id: str = None,
        custom_object_key: str = None
    ) -> Optional[Dict[str, str]]:
        """
        Upload an HTML report to OSS with public-read access.
        
        Args:
            html_file_path: Path to the HTML file to upload
            session_id: Optional session ID for organizing files
            custom_object_key: Optional custom object key (overrides default naming)
        
        Returns:
            Dict with 'url' and 'object_key' if successful, None if failed
        """
        if not self._has_credentials:
            logger.error("[OSSUpload] Cannot upload: missing OSS credentials")
            return None
        
        try:
            import oss2
        except ImportError:
            logger.error("[OSSUpload] oss2 library not installed. Install with: pip install oss2")
            return None
        
        try:
            # Validate file exists
            file_path = Path(html_file_path)
            if not file_path.exists():
                logger.error(f"[OSSUpload] File not found: {html_file_path}")
                return None
            
            # Determine object key (path in OSS bucket)
            if custom_object_key:
                object_key = custom_object_key
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                if session_id:
                    filename = f"report_{session_id}.html"
                else:
                    filename = f"report_{timestamp}.html"
                object_key = f"{self.reports_prefix}/{filename}"
            
            # Create OSS auth
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            
            # Create bucket object
            bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            
            # Get file size for logging
            file_size = file_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            logger.info(f"[OSSUpload] Uploading {file_size_mb:.2f} MB to: {object_key}")
            
            # First, delete existing file if it exists (to clear any force-download metadata)
            try:
                bucket.delete_object(object_key)
                logger.info(f"[OSSUpload] Deleted existing file: {object_key}")
            except Exception:
                # File doesn't exist, that's fine
                pass
            
            # Prepare headers for upload
            # Critical: Set Content-Disposition as object metadata (x-oss-meta-*)
            # AND as standard header to prevent OSS force-download
            headers = {
                'Content-Type': 'text/html; charset=utf-8',
                'Content-Disposition': 'inline',  # Display in browser, not download
                'Cache-Control': 'public, max-age=31536000',  # Cache for 1 year
            }
            
            # Add public-read ACL if enabled and allowed by bucket policy
            if self.set_public_acl:
                headers['x-oss-object-acl'] = 'public-read'
            
            # Upload file with correct headers
            with open(file_path, 'rb') as f:
                bucket.put_object(object_key, f, headers=headers)
            
            # Generate permanent public URL
            # Extract region from endpoint for proper URL format
            endpoint_domain = self.endpoint.replace('https://', '').replace('http://', '')
            permanent_url = f"https://{self.bucket_name}.{endpoint_domain}/{object_key}"
            
            logger.info(f"[OSSUpload] ✅ Upload successful!")
            logger.info(f"[OSSUpload] 📎 Public URL: {permanent_url}")
            
            if self.set_public_acl:
                logger.info(f"[OSSUpload] 🔓 File ACL set to public-read")
            else:
                logger.info(f"[OSSUpload] ℹ️  Using bucket-level read policy (file ACL not set)")
                logger.warning(f"[OSSUpload] ⚠️  IMPORTANT: Ensure bucket '{self.bucket_name}' allows public read!")
                logger.warning(f"[OSSUpload] ⚠️  Run: python scripts/setup_oss_public_bucket.py")
                logger.warning(f"[OSSUpload] ⚠️  Or manually set bucket ACL to public-read in OSS console")
            
            logger.info(f"[OSSUpload] 🌐 File will be accessible once bucket is public")
            
            return {
                'url': permanent_url,
                'object_key': object_key,
                'bucket': self.bucket_name,
                'size_bytes': file_size
            }
            
        except Exception as e:
            logger.error(f"[OSSUpload] Upload failed: {e}")
            import traceback
            logger.error(f"[OSSUpload] Traceback:\n{traceback.format_exc()}")
            return None
    
    def upload_file(
        self,
        file_path: str,
        object_key: str = None,
        content_type: str = None,
        public: bool = True
    ) -> Optional[Dict[str, str]]:
        """
        Upload any file to OSS.
        
        Args:
            file_path: Path to the file to upload
            object_key: OSS object key (path in bucket). If None, uses filename
            content_type: MIME type. If None, auto-detects from extension
            public: If True, sets public-read ACL. If False, keeps private
        
        Returns:
            Dict with 'url' and 'object_key' if successful, None if failed
        """
        if not self._has_credentials:
            logger.error("[OSSUpload] Cannot upload: missing OSS credentials")
            return None
        
        try:
            import oss2
        except ImportError:
            logger.error("[OSSUpload] oss2 library not installed. Install with: pip install oss2")
            return None
        
        try:
            # Validate file exists
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.error(f"[OSSUpload] File not found: {file_path}")
                return None
            
            # Determine object key
            if object_key is None:
                object_key = f"uploads/{file_path_obj.name}"
            
            # Auto-detect content type if not provided
            if content_type is None:
                ext = file_path_obj.suffix.lower()
                content_type_map = {
                    '.html': 'text/html; charset=utf-8',
                    '.htm': 'text/html; charset=utf-8',
                    '.pdf': 'application/pdf',
                    '.json': 'application/json',
                    '.txt': 'text/plain; charset=utf-8',
                    '.md': 'text/markdown; charset=utf-8',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.mp4': 'video/mp4',
                    '.mp3': 'audio/mpeg',
                }
                content_type = content_type_map.get(ext, 'application/octet-stream')
            
            # Create OSS auth and bucket
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            
            # Get file size
            file_size = file_path_obj.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            logger.info(f"[OSSUpload] Uploading {file_size_mb:.2f} MB to: {object_key}")
            
            # Prepare headers
            headers = {'Content-Type': content_type}
            if public:
                # Only set ACL if configured to do so
                if self.set_public_acl:
                    headers['x-oss-object-acl'] = 'public-read'
                headers['Cache-Control'] = 'public, max-age=31536000'
            
            # Upload file
            with open(file_path, 'rb') as f:
                bucket.put_object(object_key, f, headers=headers)
            
            # Generate URL
            endpoint_domain = self.endpoint.replace('https://', '').replace('http://', '')
            url = f"https://{self.bucket_name}.{endpoint_domain}/{object_key}"
            
            access_status = "🔓 Public" if public else "🔒 Private"
            logger.info(f"[OSSUpload] ✅ Upload successful!")
            logger.info(f"[OSSUpload] 📎 URL: {url}")
            logger.info(f"[OSSUpload] {access_status}")
            
            return {
                'url': url,
                'object_key': object_key,
                'bucket': self.bucket_name,
                'size_bytes': file_size,
                'public': public
            }
            
        except Exception as e:
            logger.error(f"[OSSUpload] Upload failed: {e}")
            import traceback
            logger.error(f"[OSSUpload] Traceback:\n{traceback.format_exc()}")
            return None
    
    def delete_file(self, object_key: str) -> bool:
        """
        Delete a file from OSS.
        
        Args:
            object_key: OSS object key to delete
        
        Returns:
            True if successful, False otherwise
        """
        if not self._has_credentials:
            logger.error("[OSSUpload] Cannot delete: missing OSS credentials")
            return False
        
        try:
            import oss2
            
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            
            bucket.delete_object(object_key)
            logger.info(f"[OSSUpload] ✅ Deleted: {object_key}")
            return True
            
        except Exception as e:
            logger.error(f"[OSSUpload] Delete failed: {e}")
            return False
    
    def list_reports(self, prefix: str = None) -> list:
        """
        List uploaded reports.
        
        Args:
            prefix: Optional prefix to filter by. If None, uses reports_prefix
        
        Returns:
            List of object keys
        """
        if not self._has_credentials:
            logger.error("[OSSUpload] Cannot list: missing OSS credentials")
            return []
        
        try:
            import oss2
            
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            
            if prefix is None:
                prefix = self.reports_prefix
            
            objects = []
            for obj in oss2.ObjectIterator(bucket, prefix=prefix):
                objects.append(obj.key)
            
            logger.info(f"[OSSUpload] Found {len(objects)} objects with prefix: {prefix}")
            return objects
            
        except Exception as e:
            logger.error(f"[OSSUpload] List failed: {e}")
            return []


def main():
    """CLI interface for uploading files."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload files to Alibaba Cloud OSS')
    parser.add_argument('file', help='File to upload')
    parser.add_argument('--session-id', help='Session ID for organizing reports')
    parser.add_argument('--object-key', help='Custom object key (overrides default)')
    parser.add_argument('--private', action='store_true', help='Upload as private (default: public)')
    parser.add_argument('--content-type', help='MIME content type')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    # Create service
    service = OSSUploadService()
    
    # Upload file
    if args.file.lower().endswith('.html'):
        result = service.upload_html_report(
            args.file,
            session_id=args.session_id,
            custom_object_key=args.object_key
        )
    else:
        result = service.upload_file(
            args.file,
            object_key=args.object_key,
            content_type=args.content_type,
            public=not args.private
        )
    
    if result:
        print("\n" + "="*60)
        print("✅ Upload Successful!")
        print("="*60)
        print(f"📎 Public URL: {result['url']}")
        print(f"📁 Object Key: {result['object_key']}")
        print(f"📦 Bucket: {result['bucket']}")
        print(f"💾 Size: {result['size_bytes']:,} bytes ({result['size_bytes']/(1024*1024):.2f} MB)")
        if result.get('public', True):
            print("🔓 Access: Public (anyone with link can access)")
        else:
            print("🔒 Access: Private (requires authentication)")
        print("="*60)
        return 0
    else:
        print("\n❌ Upload failed. Check logs above for details.")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())

