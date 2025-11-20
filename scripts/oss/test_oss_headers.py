import requests

# Test normal URL
url = "https://youliaodao-deep-research.oss-cn-beijing.aliyuncs.com/research-reports/report_20251110_192142.html"

print("Testing normal URL...")
response = requests.head(url)
print("Status Code:", response.status_code)
print("\nResponse Headers:")
for key, value in response.headers.items():
    print(f"  {key}: {value}")

print("\n" + "="*60)
print("Key Headers:")
print(f"  Content-Type: {response.headers.get('Content-Type', 'NOT SET')}")
print(f"  Content-Disposition: {response.headers.get('Content-Disposition', 'NOT SET')}")
print(f"  x-oss-force-download: {response.headers.get('x-oss-force-download', 'NOT SET')}")
