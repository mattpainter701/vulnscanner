import requests
import time
import os
import sys
from zapv2 import ZAPv2
from datetime import datetime

# ZAP API Configuration
API_KEY = "mysecretapikey"
ZAP_PROXY = "http://localhost:8080"
zap = ZAPv2(apikey=API_KEY, proxies={'http': ZAP_PROXY, 'https': ZAP_PROXY})

# Target to scan - MUST include http:// or https:// prefix
target = "https://usi-mail06-mtka.usinternet.com"

# Generate timestamp for report naming
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
report_filename = f"zap_report_{target.replace('http://', '').replace('https://', '').replace('/', '_')}_{timestamp}"

# Create reports directory if it doesn't exist
os.makedirs("reports", exist_ok=True)

# Generate full report paths
json_report_path = f"reports/{report_filename}.json"
xml_report_path = f"reports/{report_filename}.xml"
html_report_path = f"reports/{report_filename}.html"

# Function to generate reports even if scan fails
def generate_reports(note=""):
    try:
        # Get alerts for the target
        try:
            alerts = zap.core.alerts(baseurl=target)
            # Save alerts as JSON
            with open(json_report_path, "w") as f:
                f.write(str(alerts))
            print(f"Filtered JSON Report saved: {json_report_path}")
        except Exception as e:
            print(f"Could not generate JSON report: {str(e)}")
            # Create a minimal JSON report
            with open(json_report_path, "w") as f:
                f.write(f'{{"target": "{target}", "status": "scan_incomplete", "note": "{note}", "timestamp": "{timestamp}"}}')
            print(f"Minimal JSON Report saved: {json_report_path}")
            
        # Save XML report
        try:
            with open(xml_report_path, "w") as f:
                f.write(zap.core.xmlreport())
            print(f"XML Report saved: {xml_report_path}")
        except Exception as e:
            print(f"Could not generate XML report: {str(e)}")
            
        # Save HTML report
        try:
            with open(html_report_path, "w", encoding="utf-8") as f:
                f.write(zap.core.htmlreport())
            print(f"HTML Report saved: {html_report_path}")
        except Exception as e:
            print(f"Could not generate HTML report: {str(e)}")
            # Create a minimal HTML report
            with open(html_report_path, "w") as f:
                f.write(f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>ZAP Scan Report - {target}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        .error {{ color: red; }}
                    </style>
                </head>
                <body>
                    <h1>ZAP Scan Report</h1>
                    <p><strong>Target:</strong> {target}</p>
                    <p><strong>Timestamp:</strong> {timestamp}</p>
                    <p class="error"><strong>Status:</strong> Scan incomplete</p>
                    <p><strong>Note:</strong> {note}</p>
                </body>
                </html>
                """)
            print(f"Minimal HTML Report saved: {html_report_path}")
            
    except Exception as e:
        print(f"Failed to generate reports: {str(e)}")

### 🛠 FIX 1: Start a NEW ZAP SESSION (to prevent previous scan data from contaminating)
print("Starting a fresh ZAP session to clear old scan data...")
try:
    zap.core.new_session(name="NewSession", overwrite=True)
except Exception as e:
    print(f"Warning: Could not create new session: {str(e)}")

# Get all available site contexts
try:
    contexts = zap.context.context_list
    print(f"Available contexts: {str(contexts)}")
except Exception as e:
    print(f"Could not get context list: {str(e)}")

# Create a context for this scan
context_name = f"Context_{timestamp}"
try:
    zap.context.new_context(contextname=context_name)
    print(f"Created new context: {context_name}")
    
    # Include target in context
    zap.context.include_in_context(contextname=context_name, regex=f".*{target.replace('https://', '').replace('http://', '')}.*")
    print(f"Included target in context: {target}")
except Exception as e:
    print(f"Warning: Could not create context: {str(e)}")

print(f"Checking if target {target} is in the Sites tree...")

# Force ZAP to access the target URL directly
print(f"Directly accessing {target} to help with discovery...")
try:
    # Try using a regular GET request first
    print("Trying direct HTTP request first...")
    response = requests.get(target, verify=False, timeout=30)
    print(f"Direct HTTP request status: {response.status_code}")
    
    # Then have ZAP access it
    zap.core.access_url(url=target)
    print(f"Successfully accessed {target} via ZAP")
    time.sleep(5)  # Give ZAP time to process
except Exception as e:
    print(f"Warning: Error when trying to access {target}: {e}")
    print("Will continue with spider scan anyway...")

# Check if target is in sites
existing_sites = zap.core.sites
if existing_sites:
    print(f"Sites in ZAP: {existing_sites}")
else:
    print("No sites found in ZAP")

if not existing_sites or target not in existing_sites:
    print(f"Target {target} not found in Sites tree. Trying alternative approaches...")
    
    # Try with different URL formats
    alt_target = target
    if target.startswith("https://"):
        alt_target = target.replace("https://", "http://")
        print(f"Trying alternative protocol: {alt_target}")
    
    # Use Ajax Spider which is better for modern web applications
    print(f"Starting AJAX Spider on {target}...")
    try:
        ajax_scan_id = zap.ajaxSpider.scan(url=target, inscope=True)
        
        # Wait for Ajax Spider to complete or timeout after 2 minutes
        timeout = time.time() + 120  # 2 minute timeout
        while time.time() < timeout:
            status = zap.ajaxSpider.status
            if status == "stopped":
                break
            print(f"AJAX Spider status: {status}")
            time.sleep(5)
        
        print("AJAX Spider completed or timed out")
    except Exception as e:
        print(f"AJAX Spider error: {str(e)}")
    
    # Now try traditional spider
    print(f"Starting Spider scan on {target}...")
    try:
        spider_scan_id = zap.spider.scan(target)
        
        # Monitor Spider scan progress with a timeout
        timeout = time.time() + 120  # 2 minute timeout
        while time.time() < timeout:
            try:
                spider_status = zap.spider.status(spider_scan_id)
                if int(spider_status) >= 100:
                    break
                print(f"Spider progress: {spider_status}%")
                time.sleep(5)
            except:
                print("Error getting spider status")
                break
        
        print("Spider scan completed or timed out!")
    except Exception as e:
        print(f"Spider error: {str(e)}")

# Check for the target again
print("Rechecking for target in sites...")
existing_sites = zap.core.sites
site_found = False

# Check for exact match
if target in existing_sites:
    print(f"Target {target} found in Sites tree. Proceeding with active scan.")
    site_found = True
else:
    # Check for partial matches - domain only
    domain = target.split("//")[1].split("/")[0]
    print(f"Checking for domain: {domain}")
    
    for site in existing_sites:
        if domain in site:
            print(f"Found related site in tree: {site}")
            target = site  # Use this site instead
            site_found = True
            break

if not site_found:
    print(f"Warning: Target {target} still not found in Sites tree.")
    print("Will attempt to run an active scan anyway.")
    generate_reports("Target not found in Sites tree after spider scan.")

# Proceed with the Active Scan regardless
print(f"Starting Active Scan for {target}...")
try:
    scan_id = zap.ascan.scan(target)
    print(f"Active Scan started: {scan_id}")
    
    # Monitor Active Scan progress with a reasonable timeout
    timeout = time.time() + 300  # 5 minute timeout
    while time.time() < timeout:
        try:
            status = zap.ascan.status(scan_id)
            if int(status) >= 100:
                break
            print(f"Active Scan progress: {status}%")
            time.sleep(5)
        except:
            print("Error getting scan status")
            break
    
    print("Active Scan completed or timed out!")
except Exception as e:
    print(f"Active scan error: {str(e)}")
    generate_reports(f"Active scan error: {str(e)}")
    sys.exit(1)

# Generate reports regardless of how the scan went
generate_reports()
print("All reports generated and saved to the 'reports' directory.")


