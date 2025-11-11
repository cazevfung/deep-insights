"""
Helper script to configure OSS bucket for public read access.

This script helps you set up your Alibaba Cloud OSS bucket to allow
public access to uploaded HTML reports.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Config
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def setup_bucket_public_read():
    """Set bucket to allow public read access."""
    try:
        import oss2
    except ImportError:
        logger.error("❌ oss2 library not installed. Install with: pip install oss2")
        return False
    
    # Load config
    config = Config()
    access_key_id = config.get('scrapers.bilibili.oss_access_key_id')
    access_key_secret = config.get('scrapers.bilibili.oss_access_key_secret')
    bucket_name = config.get('scrapers.bilibili.oss_bucket')
    endpoint = config.get('scrapers.bilibili.oss_endpoint', 'https://oss-cn-beijing.aliyuncs.com')
    
    if not all([access_key_id, access_key_secret, bucket_name]):
        logger.error("❌ Missing OSS credentials in config.yaml")
        return False
    
    try:
        # Create OSS client
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        
        print("\n" + "="*60)
        print("🔧 OSS Bucket Configuration Helper")
        print("="*60)
        print(f"📦 Bucket: {bucket_name}")
        print(f"🌐 Endpoint: {endpoint}")
        
        # Get current ACL
        try:
            current_acl = bucket.get_bucket_acl().acl
            print(f"📋 Current Bucket ACL: {current_acl}")
        except Exception as e:
            logger.warning(f"⚠️  Could not read current ACL: {e}")
            current_acl = "unknown"
        
        print("\n" + "-"*60)
        print("Choose an option to enable public access:")
        print("-"*60)
        print("1. Set entire bucket to PUBLIC READ (recommended)")
        print("   - Anyone can read all files in the bucket")
        print("   - Simplest option")
        print()
        print("2. Set bucket policy for research-reports folder only")
        print("   - Only files in research-reports/ are public")
        print("   - More secure (other folders remain private)")
        print()
        print("3. Show current bucket policy")
        print()
        print("4. Exit without changes")
        print("-"*60)
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            # Set bucket ACL to public-read
            print("\n🔄 Setting bucket ACL to public-read...")
            bucket.put_bucket_acl(oss2.BUCKET_ACL_PUBLIC_READ)
            print("✅ Bucket ACL updated to public-read!")
            print("🌐 All files in this bucket are now publicly readable")
            print(f"🔗 Test URL: https://{bucket_name}.{endpoint.replace('https://', '')}/research-reports/")
            return True
            
        elif choice == "2":
            # Set bucket policy for specific folder
            policy_text = f'''{{
  "Version": "1",
  "Statement": [
    {{
      "Effect": "Allow",
      "Principal": ["*"],
      "Action": ["oss:GetObject"],
      "Resource": ["acs:oss:*:*:{bucket_name}/research-reports/*"]
    }}
  ]
}}'''
            
            print("\n🔄 Setting bucket policy for research-reports folder...")
            print("\nPolicy to be applied:")
            print(policy_text)
            
            confirm = input("\nApply this policy? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                bucket.put_bucket_policy(policy_text)
                print("✅ Bucket policy updated!")
                print("🌐 Files in research-reports/ folder are now publicly readable")
                print(f"🔗 Test URL: https://{bucket_name}.{endpoint.replace('https://', '')}/research-reports/")
                return True
            else:
                print("❌ Cancelled.")
                return False
                
        elif choice == "3":
            # Show current policy
            print("\n📋 Current Bucket Policy:")
            try:
                policy = bucket.get_bucket_policy()
                print(policy.read().decode('utf-8'))
            except oss2.exceptions.NoSuchBucketPolicy:
                print("(No bucket policy set)")
            except Exception as e:
                print(f"Error reading policy: {e}")
            return False
            
        else:
            print("❌ No changes made.")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def setup_bucket_public_read_auto(policy_type='folder'):
    """
    Automatically set bucket to public read without prompts.
    
    Args:
        policy_type: 'bucket' for whole bucket, 'folder' for research-reports only
    """
    try:
        import oss2
    except ImportError:
        logger.error("❌ oss2 library not installed. Install with: pip install oss2")
        return False
    
    # Load config
    config = Config()
    access_key_id = config.get('scrapers.bilibili.oss_access_key_id')
    access_key_secret = config.get('scrapers.bilibili.oss_access_key_secret')
    bucket_name = config.get('scrapers.bilibili.oss_bucket')
    endpoint = config.get('scrapers.bilibili.oss_endpoint', 'https://oss-cn-beijing.aliyuncs.com')
    
    if not all([access_key_id, access_key_secret, bucket_name]):
        logger.error("❌ Missing OSS credentials in config.yaml")
        return False
    
    try:
        # Create OSS client
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        
        print("\n" + "="*60)
        print("🔧 Configuring OSS Bucket for Public Access")
        print("="*60)
        print(f"📦 Bucket: {bucket_name}")
        print(f"🌐 Endpoint: {endpoint}")
        
        if policy_type == 'bucket':
            # Set entire bucket to public-read
            print("\n🔄 Setting entire bucket to public-read...")
            bucket.put_bucket_acl(oss2.BUCKET_ACL_PUBLIC_READ)
            print("✅ Bucket ACL updated to public-read!")
            print("🌐 All files in this bucket are now publicly readable")
            
        else:  # folder
            # Set policy for research-reports folder only
            policy_text = f'''{{
  "Version": "1",
  "Statement": [
    {{
      "Effect": "Allow",
      "Principal": ["*"],
      "Action": ["oss:GetObject"],
      "Resource": ["acs:oss:*:*:{bucket_name}/research-reports/*"]
    }}
  ]
}}'''
            
            print("\n🔄 Setting bucket policy for research-reports folder...")
            bucket.put_bucket_policy(policy_text)
            print("✅ Bucket policy updated!")
            print("🌐 Files in research-reports/ are now publicly readable")
        
        print(f"🔗 Test URL: https://{bucket_name}.{endpoint.replace('https://', '')}/research-reports/")
        print("="*60)
        return True
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Configure OSS bucket for public HTML report access'
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompts (use folder policy)'
    )
    parser.add_argument(
        '--type',
        choices=['bucket', 'folder'],
        default='folder',
        help='Policy type: "bucket" for entire bucket, "folder" for research-reports only (default: folder)'
    )
    
    args = parser.parse_args()
    
    print("""
╔════════════════════════════════════════════════════════════╗
║  OSS Public Bucket Setup Helper                           ║
║  Configure your OSS bucket for public HTML report access  ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    if args.yes:
        # Non-interactive mode
        print(f"⚡ Auto-mode: Applying {args.type} policy...")
        success = setup_bucket_public_read_auto(args.type)
    else:
        # Interactive mode
        print("⚠️  WARNING: This will make files in your bucket publicly accessible!")
        print("   Only proceed if you understand the security implications.")
        print()
        
        proceed = input("Continue? (yes/no): ").strip().lower()
        if proceed not in ['yes', 'y']:
            print("❌ Cancelled.")
            return 1
        
        success = setup_bucket_public_read()
    
    if success:
        print("\n" + "="*60)
        print("✅ Setup Complete!")
        print("="*60)
        print("\n📝 Next steps:")
        print("1. Upload an HTML report:")
        print("   python scripts/generate_export_html.py <session_id> --upload")
        print()
        print("2. Test the public URL in an incognito window")
        print()
        print("3. Share the URL with others!")
        print("="*60)
        return 0
    else:
        print("\n❌ Setup failed or cancelled.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

