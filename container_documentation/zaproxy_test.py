import requests
import time
import os
import sys
import json
import argparse
from zapv2 import ZAPv2
from datetime import datetime

# Parse command line arguments
parser = argparse.ArgumentParser(description='ZAP Vulnerability Scanner')
parser.add_argument('target', help='Target URL to scan (e.g., https://example.com)')
args = parser.parse_args()

# ZAP API Configuration
API_KEY = "mysecretapikey"
ZAP_PROXY = "http://localhost:8080"
zap = ZAPv2(apikey=API_KEY, proxies={'http': ZAP_PROXY, 'https': ZAP_PROXY})

# Target to scan - from command line argument
target = args.target

# Ensure target has protocol prefix
if not target.startswith(('http://', 'https://')):
    target = 'https://' + target
    print(f"No protocol specified, using HTTPS by default: {target}")

# Generate timestamp for report naming
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
report_filename = f"zap_report_{target.replace('http://', '').replace('https://', '').replace('/', '_')}_{timestamp}"

# Create reports directory if it doesn't exist
os.makedirs("reports", exist_ok=True)

# Generate full report paths
json_report_path = f"reports/{report_filename}.json"
xml_report_path = f"reports/{report_filename}.xml"
html_report_path = f"reports/{report_filename}.html"

# Log file to capture scan information
log_file_path = f"reports/{report_filename}.log"

# Record scan events for reporting
scan_log = []
def log_event(message):
    print(message)
    scan_log.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
    with open(log_file_path, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

# Function to generate reports even if scan fails
def generate_reports(note=""):
    try:
        # Get alerts for the target
        try:
            alerts = zap.core.alerts(baseurl=target)
            # Save alerts as JSON
            with open(json_report_path, "w") as f:
                if alerts and len(alerts) > 0:
                    f.write(str(alerts))
                    log_event(f"Found {len(alerts)} alerts for {target}")
                else:
                    # Create a more informative report when no alerts are found
                    report_data = {
                        "target": target,
                        "timestamp": timestamp,
                        "note": note if note else "No vulnerabilities were detected",
                        "scan_log": scan_log,
                        "status": "completed" if not note else "incomplete"
                    }
                    f.write(json.dumps(report_data, indent=2))
                    log_event("No vulnerabilities found - created detailed report")
            print(f"JSON Report saved: {json_report_path}")
        except Exception as e:
            print(f"Could not generate JSON report: {str(e)}")
            # Create a minimal JSON report
            report_data = {
                "target": target,
                "timestamp": timestamp,
                "note": note if note else f"Error generating report: {str(e)}",
                "scan_log": scan_log,
                "status": "error",
                "error": str(e)
            }
            with open(json_report_path, "w") as f:
                f.write(json.dumps(report_data, indent=2))
            log_event(f"Generated error JSON report: {str(e)}")
            
        # Save XML report
        try:
            xml_content = zap.core.xmlreport()
            if xml_content and len(xml_content) > 100:  # Check if it has meaningful content
                with open(xml_report_path, "w") as f:
                    f.write(xml_content)
                log_event("Generated XML report with scan data")
            else:
                # Create a more informative XML report
                xml_template = f"""<?xml version="1.0"?>
<OWASPZAPReport version="2.11.1" generated="{datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}">
  <site name="{target}">
    <alerts/>
    <scanInfo>
      <scanStatus>completed</scanStatus>
      <scanDateTime>{datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}</scanDateTime>
      <scanVersion>2.11.1</scanVersion>
      <scanTarget>{target}</scanTarget>
      <scanNotes>{note if note else "No vulnerabilities were detected"}</scanNotes>
    </scanInfo>
  </site>
</OWASPZAPReport>"""
                with open(xml_report_path, "w") as f:
                    f.write(xml_template)
                log_event("Generated custom XML report template")
            print(f"XML Report saved: {xml_report_path}")
        except Exception as e:
            print(f"Could not generate XML report: {str(e)}")
            # Create a minimal XML report
            xml_template = f"""<?xml version="1.0"?>
<OWASPZAPReport version="2.11.1" generated="{datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}">
  <site name="{target}">
    <alerts/>
    <scanInfo>
      <error>{str(e)}</error>
      <scanStatus>error</scanStatus>
      <scanDateTime>{datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')}</scanDateTime>
      <scanTarget>{target}</scanTarget>
      <scanNotes>{note if note else f"Error generating report: {str(e)}"}</scanNotes>
    </scanInfo>
  </site>
</OWASPZAPReport>"""
            with open(xml_report_path, "w") as f:
                f.write(xml_template)
            log_event(f"Generated error XML report: {str(e)}")
            
        # Save HTML report
        try:
            html_content = zap.core.htmlreport()
            if html_content and len(html_content) > 500:  # Check if it has meaningful content
                with open(html_report_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                log_event("Generated HTML report with scan data")
            else:
                # Create a more informative HTML report
                with open(html_report_path, "w") as f:
                    f.write(f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>ZAP Scan Report - {target}</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                            .container {{ max-width: 1000px; margin: 0 auto; }}
                            .header {{ background-color: #205081; color: white; padding: 20px; margin-bottom: 20px; }}
                            .content {{ padding: 20px; background-color: #f9f9f9; border-radius: 5px; }}
                            .info {{ color: #31708f; background-color: #d9edf7; border: 1px solid #bce8f1; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
                            .warning {{ color: #8a6d3b; background-color: #fcf8e3; border: 1px solid #faebcc; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
                            .error {{ color: #a94442; background-color: #f2dede; border: 1px solid #ebccd1; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
                            .success {{ color: #3c763d; background-color: #dff0d8; border: 1px solid #d6e9c6; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
                            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                            th, td {{ padding: 10px; text-align: left; border: 1px solid #ddd; }}
                            th {{ background-color: #f2f2f2; }}
                            .log {{ max-height: 400px; overflow-y: auto; background-color: #f5f5f5; padding: 10px; font-family: monospace; border: 1px solid #ddd; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>ZAP Vulnerability Scan Report</h1>
                                <h2>{target}</h2>
                                <p>Scan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                            </div>
                            <div class="content">
                                <div class="{"info" if not note else "warning"}">
                                    <h3>Scan Summary</h3>
                                    <p><strong>Status:</strong> {"Completed - No Vulnerabilities Detected" if not note else "Scan Issues Encountered"}</p>
                                    <p><strong>Target:</strong> {target}</p>
                                    <p><strong>Note:</strong> {note if note else "No vulnerabilities were detected in this scan. This could mean the target is secure, or that the scanner was unable to properly assess the target."}</p>
                                </div>
                                
                                <h3>Scan Information</h3>
                                <table>
                                    <tr>
                                        <th>Item</th>
                                        <th>Details</th>
                                    </tr>
                                    <tr>
                                        <td>Target URL</td>
                                        <td>{target}</td>
                                    </tr>
                                    <tr>
                                        <td>Scan Date</td>
                                        <td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                                    </tr>
                                    <tr>
                                        <td>Scanner</td>
                                        <td>OWASP ZAP (Zed Attack Proxy)</td>
                                    </tr>
                                    <tr>
                                        <td>Total Alerts</td>
                                        <td>0</td>
                                    </tr>
                                    <tr>
                                        <td>Risk Level</td>
                                        <td>{"Inconclusive (could not properly scan target)" if note else "Low (no vulnerabilities found)"}</td>
                                    </tr>
                                </table>
                                
                                <h3>Scan Log</h3>
                                <div class="log">
                                    {"<br>".join(scan_log)}
                                </div>
                                
                                <h3>Recommendations</h3>
                                <ul>
                                    <li>{"If this is a mail server, consider using specialized mail server security scanning tools instead of web vulnerability scanners." if "mail" in target.lower() else "Consider additional security testing methods to verify these results."}</li>
                                    <li>{"Ensure proper SSL/TLS configuration on all public-facing services." if "SSL" in str(scan_log) else "Continue regular security scans to maintain vigilance."}</li>
                                    <li>Follow security best practices for your environment.</li>
                                </ul>
                            </div>
                        </div>
                    </body>
                    </html>
                    """)
                log_event("Generated enhanced HTML report template")
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
                    <h1>ZAP Scan Report - Error</h1>
                    <p><strong>Target:</strong> {target}</p>
                    <p><strong>Timestamp:</strong> {timestamp}</p>
                    <p class="error"><strong>Status:</strong> Scan error</p>
                    <p><strong>Error:</strong> {str(e)}</p>
                    <p><strong>Note:</strong> {note}</p>
                    <h3>Scan Log</h3>
                    <pre>{os.linesep.join(scan_log)}</pre>
                </body>
                </html>
                """)
            log_event(f"Generated error HTML report: {str(e)}")
            
    except Exception as e:
        log_event(f"Failed to generate reports: {str(e)}")

# Create empty log file
with open(log_file_path, "w") as f:
    f.write(f"Scan started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} for target: {target}\n")

### 🛠 FIX 1: Start a NEW ZAP SESSION (to prevent previous scan data from contaminating)
log_event("Starting a fresh ZAP session to clear old scan data...")
try:
    zap.core.new_session(name="NewSession", overwrite=True)
except Exception as e:
    log_event(f"Warning: Could not create new session: {str(e)}")

# Get all available site contexts
try:
    contexts = zap.context.context_list
    log_event(f"Available contexts: {str(contexts)}")
except Exception as e:
    log_event(f"Could not get context list: {str(e)}")

# Create a context for this scan
context_name = f"Context_{timestamp}"
try:
    zap.context.new_context(contextname=context_name)
    log_event(f"Created new context: {context_name}")
    
    # Include target in context
    zap.context.include_in_context(contextname=context_name, regex=f".*{target.replace('https://', '').replace('http://', '')}.*")
    log_event(f"Included target in context: {target}")
except Exception as e:
    log_event(f"Warning: Could not create context: {str(e)}")

log_event(f"Checking if target {target} is in the Sites tree...")

# Force ZAP to access the target URL directly
log_event(f"Directly accessing {target} to help with discovery...")
try:
    # Try using a regular GET request first
    log_event("Trying direct HTTP request first...")
    response = requests.get(target, verify=False, timeout=30)
    log_event(f"Direct HTTP request status: {response.status_code}")
    
    # Then have ZAP access it
    zap.core.access_url(url=target)
    log_event(f"Successfully accessed {target} via ZAP")
    time.sleep(5)  # Give ZAP time to process
except Exception as e:
    log_event(f"Warning: Error when trying to access {target}: {e}")
    log_event("Will continue with spider scan anyway...")

# Check if target is in sites
existing_sites = zap.core.sites
if existing_sites:
    log_event(f"Sites in ZAP: {existing_sites}")
else:
    log_event("No sites found in ZAP")

if not existing_sites or target not in existing_sites:
    log_event(f"Target {target} not found in Sites tree. Trying alternative approaches...")
    
    # Try with different URL formats
    alt_target = target
    if target.startswith("https://"):
        alt_target = target.replace("https://", "http://")
        log_event(f"Trying alternative protocol: {alt_target}")
    
    # Use Ajax Spider which is better for modern web applications
    log_event(f"Starting AJAX Spider on {target}...")
    try:
        ajax_scan_id = zap.ajaxSpider.scan(url=target, inscope=True)
        
        # Wait for Ajax Spider to complete or timeout after 2 minutes
        timeout = time.time() + 120  # 2 minute timeout
        while time.time() < timeout:
            status = zap.ajaxSpider.status
            if status == "stopped":
                break
            log_event(f"AJAX Spider status: {status}")
            time.sleep(5)
        
        log_event("AJAX Spider completed or timed out")
    except Exception as e:
        log_event(f"AJAX Spider error: {str(e)}")
    
    # Now try traditional spider
    log_event(f"Starting Spider scan on {target}...")
    try:
        spider_scan_id = zap.spider.scan(target)
        
        # Monitor Spider scan progress with a timeout
        timeout = time.time() + 120  # 2 minute timeout
        while time.time() < timeout:
            try:
                spider_status = zap.spider.status(spider_scan_id)
                if int(spider_status) >= 100:
                    break
                log_event(f"Spider progress: {spider_status}%")
                time.sleep(5)
            except:
                log_event("Error getting spider status")
                break
        
        log_event("Spider scan completed or timed out!")
    except Exception as e:
        log_event(f"Spider error: {str(e)}")

# Check for the target again
log_event("Rechecking for target in sites...")
existing_sites = zap.core.sites
site_found = False

# Check for exact match
if target in existing_sites:
    log_event(f"Target {target} found in Sites tree. Proceeding with active scan.")
    site_found = True
else:
    # Check for partial matches - domain only
    domain = target.split("//")[1].split("/")[0]
    log_event(f"Checking for domain: {domain}")
    
    for site in existing_sites:
        if domain in site:
            log_event(f"Found related site in tree: {site}")
            target = site  # Use this site instead
            site_found = True
            break

if not site_found:
    log_event(f"Warning: Target {target} still not found in Sites tree.")
    log_event("Will attempt to run an active scan anyway.")
    generate_reports("Target not found in Sites tree after spider scan. The target may not be accessible or may not respond to HTTP requests.")

# Proceed with the Active Scan regardless
log_event(f"Starting Active Scan for {target}...")
try:
    scan_id = zap.ascan.scan(target)
    log_event(f"Active Scan started: {scan_id}")
    
    # Check if scan started successfully
    if scan_id == "url_not_found":
        log_event("Error: URL not found. Cannot perform active scan.")
        generate_reports("URL not found. Cannot perform active scan. The target may not be accessible via HTTP/HTTPS.")
        sys.exit(0)
    
    # Monitor Active Scan progress with a reasonable timeout
    timeout = time.time() + 300  # 5 minute timeout
    while time.time() < timeout:
        try:
            status = zap.ascan.status(scan_id)
            if int(status) >= 100:
                break
            log_event(f"Active Scan progress: {status}%")
            time.sleep(5)
        except:
            log_event("Error getting scan status")
            break
    
    log_event("Active Scan completed or timed out!")
except Exception as e:
    log_event(f"Active scan error: {str(e)}")
    generate_reports(f"Active scan error: {str(e)}")
    sys.exit(0)

# Generate reports regardless of how the scan went
scan_msg = ""
if target.lower().find("mail") >= 0:
    scan_msg = "Note: This appears to be a mail server which typically doesn't expose web services on standard HTTP/HTTPS ports. Consider using specialized mail security scanning tools for a more accurate assessment."

generate_reports(scan_msg)
log_event("All reports generated and saved to the 'reports' directory.")





