import requests
import time
import os
from zapv2 import ZAPv2
from datetime import datetime

# ZAP API Configuration
API_KEY = "mysecretapikey"
ZAP_PROXY = "http://localhost:8080"
zap = ZAPv2(apikey=API_KEY, proxies={'http': ZAP_PROXY, 'https': ZAP_PROXY})

# Target to scan - add http:// prefix as it's required for proper scanning
target = "https://usi-mail06-mtka.usinternet.com"

# Generate timestamp for report naming
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
report_filename = f"zap_report_{target.replace('http://', '').replace('/', '_')}_{timestamp}"

# Start a NEW ZAP SESSION
print("Starting a fresh ZAP session to clear old scan data...")
zap.core.new_session(name="NewSession", overwrite=True)

print(f"Checking if target {target} is in the Sites tree...")

# Fetch existing sites from ZAP
existing_sites = zap.core.sites

if not existing_sites or target not in existing_sites:
    print(f"Target {target} not found in Sites tree. Initiating Spider scan first...")

    # Start the Spider scan
    print(f"Starting spider scan on {target}")
    spider_scan_id = zap.spider.scan(target)
    
    # Check if the scan started successfully
    if isinstance(spider_scan_id, str) and spider_scan_id in ['illegal_parameter', 'url_not_found']:
        print(f"Error: {spider_scan_id}. Check if the target is valid and accessible.")
        exit(1)

    # Monitor Spider scan progress
    while True:
        spider_status = zap.spider.status(spider_scan_id)
        if int(spider_status) >= 100:
            break
        print(f"Spider progress: {spider_status}%")
        time.sleep(5)

    print("Spider scan completed!")

    # Wait until the target appears in the Sites tree
    print(f"Waiting for ZAP to register {target} in the Sites tree...")
    for i in range(10):  # Wait up to 10 retries
        existing_sites = zap.core.sites
        if target in existing_sites:
            print(f"Target {target} successfully added to the Sites tree.")
            break
        time.sleep(3)
    else:
        print(f"Error: Target {target} did not appear in the Sites tree. Active scan will not start.")
        exit(1)

# Now, proceed with the Active Scan
print(f"Starting Active Scan for {target}...")

scan_id = zap.ascan.scan(target)
if isinstance(scan_id, str) and scan_id in ['illegal_parameter', 'url_not_found']:
    print(f"Error: {scan_id}. Check if the target is valid and accessible.")
    exit(1)

print(f"Active Scan started: {scan_id}")

# Monitor Active Scan progress
while True:
    status = zap.ascan.status(scan_id)
    if status == 'does_not_exist':
        print("Error: Scan ID does not exist. The scan might not have started correctly.")
        exit(1)
    elif int(status) >= 100:
        break
    print(f"Active Scan progress: {status}%")
    time.sleep(5)

print("Active Scan completed!")

# Generate reports for the current scan target only
alerts = zap.core.alerts(baseurl=target)

# Save alerts as JSON
json_report_path = f"{report_filename}.json"
with open(json_report_path, "w") as f:
    f.write(str(alerts))
print(f"Filtered JSON Report saved: {json_report_path}")

# Save XML report
xml_report_path = f"{report_filename}.xml"
with open(xml_report_path, "w") as f:
    f.write(zap.core.xmlreport())
print(f"XML Report saved: {xml_report_path}")

# Save HTML report
html_report_path = f"{report_filename}.html"
with open(html_report_path, "w", encoding="utf-8") as f:
    f.write(zap.core.htmlreport())
print(f"HTML Report saved: {html_report_path}")

print("All reports generated successfully!") 