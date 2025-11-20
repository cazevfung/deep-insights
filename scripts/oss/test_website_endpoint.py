import requests

# Website endpoint (should allow inline viewing)
website_url = "http://youliaodao-deep-research.oss-website-cn-beijing.aliyuncs.com/research-reports/report_20251110_192142.html"

print("Testing Website Endpoint URL...")
print(f"URL: {website_url}")
print("="*60)

try:
    response = requests.head(website_url, allow_redirects=True, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"\nAll Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    
    print(f"\n" + "="*60)
    print(f"Key Headers:")
    print(f"  Content-Type: {response.headers.get('Content-Type', 'NOT SET')}")
    print(f"  Content-Disposition: {response.headers.get('Content-Disposition', 'NOT SET')}")
    print(f"  x-oss-force-download: {response.headers.get('x-oss-force-download', 'NOT SET')}")
    
    if 'Content-Disposition' not in response.headers or response.headers.get('Content-Disposition') == 'inline':
        print("\n✅ SUCCESS! HTML should display in browser!")
        print(f"\nUse this URL: {website_url}")
    else:
        print("\n❌ Still forcing download")
        
except Exception as e:
    print(f"❌ Error: {e}")
