import argparse
import os
import sys
import json
import time
import xml.etree.ElementTree as ET
import requests
from datetime import datetime
import urllib3

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Parse command line arguments
parser = argparse.ArgumentParser(description='OpenVAS Vulnerability Scanner')
parser.add_argument('target', help='Target to scan (e.g., https://example.com or 192.168.1.1)')
args = parser.parse_args()

# OpenVAS API Configuration
OPENVAS_HOST = "localhost"
OPENVAS_PORT = "9392"
OPENVAS_USER = "admin"
OPENVAS_PASSWORD = "admin"
OPENVAS_URL = f"https://{OPENVAS_HOST}:{OPENVAS_PORT}"

# Target to scan - from command line argument
target = args.target

# Ensure target is properly formatted
if not target.startswith(('http://', 'https://')) and not all(c.isdigit() or c == '.' for c in target.split('.')):
    target = 'https://' + target
    print(f"No protocol specified, using HTTPS by default: {target}")

# Generate timestamp for report naming
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
sanitized_target = target.replace('http://', '').replace('https://', '').replace('/', '_').replace(':', '_')
report_filename = f"openvas_report_{sanitized_target}_{timestamp}"

# Create reports directory if it doesn't exist
os.makedirs("reports", exist_ok=True)

# Generate full report paths
json_report_path = f"reports/{report_filename}.json"
xml_report_path = f"reports/{report_filename}.xml"
html_report_path = f"reports/{report_filename}.html"
pdf_report_path = f"reports/{report_filename}.pdf"
log_file_path = f"reports/{report_filename}.log"

# Record scan events for reporting
scan_log = []
def log_event(message):
    print(message)
    scan_log.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
    with open(log_file_path, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

# Create empty log file
with open(log_file_path, "w") as f:
    f.write(f"Scan started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} for target: {target}\n")

# Function to make API requests to GSA (Greenbone Security Assistant)
def gvm_request(endpoint, method="GET", data=None, params=None):
    url = f"{OPENVAS_URL}/gmp{endpoint}"
    headers = {"Content-Type": "application/xml"}
    try:
        if method == "GET":
            response = requests.get(url, auth=(OPENVAS_USER, OPENVAS_PASSWORD), params=params, 
                                    headers=headers, verify=False, timeout=30)
        else:
            response = requests.post(url, auth=(OPENVAS_USER, OPENVAS_PASSWORD), data=data, 
                                     headers=headers, verify=False, timeout=30)
        
        if response.status_code >= 400:
            log_event(f"API Error: {response.status_code} - {response.text}")
            return None
        
        return response.text
    except Exception as e:
        log_event(f"Error making API request to {endpoint}: {str(e)}")
        return None

# Generate reports based on the scan results
def generate_reports(scan_id=None, report_id=None, note=""):
    try:
        if not scan_id and not report_id:
            log_event("No scan or report ID provided, generating empty reports")
            # Create a minimal JSON report
            report_data = {
                "target": target,
                "timestamp": timestamp,
                "note": note if note else "No scan was performed",
                "scan_log": scan_log,
                "status": "error",
                "vulnerabilities": []
            }
            with open(json_report_path, "w") as f:
                f.write(json.dumps(report_data, indent=2))
            log_event("Generated empty JSON report")
            
            # Create a minimal XML report
            with open(xml_report_path, "w") as f:
                f.write(f"""<?xml version="1.0"?>
<report>
  <target>{target}</target>
  <timestamp>{timestamp}</timestamp>
  <status>error</status>
  <note>{note if note else "No scan was performed"}</note>
</report>""")
            log_event("Generated empty XML report")
            
            # Create a minimal HTML report
            with open(html_report_path, "w") as f:
                f.write(f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>OpenVAS Scan Report - {target}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                        .container {{ max-width: 1000px; margin: 0 auto; }}
                        .header {{ background-color: #4CAF50; color: white; padding: 20px; margin-bottom: 20px; }}
                        .content {{ padding: 20px; background-color: #f9f9f9; border-radius: 5px; }}
                        .warning {{ color: #8a6d3b; background-color: #fcf8e3; border: 1px solid #faebcc; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
                        .log {{ max-height: 400px; overflow-y: auto; background-color: #f5f5f5; padding: 10px; font-family: monospace; border: 1px solid #ddd; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>OpenVAS Vulnerability Scan Report</h1>
                            <h2>{target}</h2>
                            <p>Scan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        </div>
                        <div class="content">
                            <div class="warning">
                                <h3>Scan Error</h3>
                                <p><strong>Status:</strong> Failed to perform scan</p>
                                <p><strong>Target:</strong> {target}</p>
                                <p><strong>Note:</strong> {note if note else "No scan was performed. There may be an issue with the OpenVAS server or connection."}</p>
                            </div>
                            
                            <h3>Scan Log</h3>
                            <div class="log">
                                {"<br>".join(scan_log)}
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """)
            log_event("Generated HTML error report")
            return
        
        log_event(f"Generating reports for scan ID: {scan_id}, report ID: {report_id}")
        
        # Get report formats
        formats_xml = gvm_request("/get_report_formats")
        if formats_xml:
            formats_root = ET.fromstring(formats_xml)
            
            # Find format IDs
            format_ids = {
                "XML": None,
                "HTML": None,
                "PDF": None
            }
            
            for report_format in formats_root.findall(".//report_format"):
                name = report_format.find("name").text
                format_id = report_format.get("id")
                
                if "XML" in name:
                    format_ids["XML"] = format_id
                elif "HTML" in name:
                    format_ids["HTML"] = format_id
                elif "PDF" in name:
                    format_ids["PDF"] = format_id
            
            log_event(f"Found report format IDs: {format_ids}")
            
            # Download reports in different formats
            if report_id:
                # Get XML report
                if format_ids["XML"]:
                    xml_data = f'<get_reports report_id="{report_id}" format_id="{format_ids["XML"]}"/>'
                    xml_report = gvm_request("", method="POST", data=xml_data)
                    if xml_report:
                        with open(xml_report_path, "w") as f:
                            f.write(xml_report)
                        log_event(f"Saved XML report to {xml_report_path}")
                        
                        # Also create JSON from XML
                        try:
                            report_root = ET.fromstring(xml_report)
                            report_data = {
                                "target": target,
                                "timestamp": timestamp,
                                "scan_id": scan_id,
                                "report_id": report_id,
                                "vulnerabilities": []
                            }
                            
                            # Extract vulnerabilities from XML
                            results = report_root.findall(".//result")
                            for result in results:
                                severity = result.find("severity").text
                                name = result.find("name").text if result.find("name") is not None else "Unknown"
                                description = result.find("description").text if result.find("description") is not None else ""
                                
                                vuln = {
                                    "name": name,
                                    "severity": severity,
                                    "description": description
                                }
                                report_data["vulnerabilities"].append(vuln)
                            
                            # Save as JSON
                            with open(json_report_path, "w") as f:
                                f.write(json.dumps(report_data, indent=2))
                            log_event(f"Saved JSON report to {json_report_path}")
                        except Exception as e:
                            log_event(f"Error creating JSON report: {str(e)}")
                
                # Get HTML report
                if format_ids["HTML"]:
                    html_data = f'<get_reports report_id="{report_id}" format_id="{format_ids["HTML"]}"/>'
                    html_report = gvm_request("", method="POST", data=html_data)
                    if html_report:
                        with open(html_report_path, "w") as f:
                            f.write(html_report)
                        log_event(f"Saved HTML report to {html_report_path}")
                
                # Get PDF report
                if format_ids["PDF"]:
                    pdf_data = f'<get_reports report_id="{report_id}" format_id="{format_ids["PDF"]}"/>'
                    pdf_report = gvm_request("", method="POST", data=pdf_data)
                    if pdf_report:
                        with open(pdf_report_path, "wb") as f:
                            f.write(pdf_report.encode('latin1'))
                        log_event(f"Saved PDF report to {pdf_report_path}")
            else:
                log_event("No report ID available, cannot generate detailed reports")
        else:
            log_event("Could not retrieve report formats")
    
    except Exception as e:
        log_event(f"Error generating reports: {str(e)}")
        # Create a minimal error report
        with open(html_report_path, "w") as f:
            f.write(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>OpenVAS Scan Report - {target}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .error {{ color: red; }}
                </style>
            </head>
            <body>
                <h1>OpenVAS Scan Report - Error</h1>
                <p><strong>Target:</strong> {target}</p>
                <p><strong>Timestamp:</strong> {timestamp}</p>
                <p class="error"><strong>Status:</strong> Report generation error</p>
                <p><strong>Error:</strong> {str(e)}</p>
                <h3>Scan Log</h3>
                <pre>{os.linesep.join(scan_log)}</pre>
            </body>
            </html>
            """)
        log_event(f"Generated minimal HTML error report due to exception: {e}")

# Main scanning function
def run_openvas_scan():
    # Test connection to OpenVAS
    log_event("Testing connection to OpenVAS...")
    version_response = gvm_request("/get_version")
    if not version_response:
        log_event("Failed to connect to OpenVAS. Please check that the server is running and credentials are correct.")
        generate_reports(note="Failed to connect to OpenVAS server")
        return
    
    try:
        version_root = ET.fromstring(version_response)
        version = version_root.find("version").text
        log_event(f"Connected to OpenVAS (version {version})")
    except Exception as e:
        log_event(f"Error parsing version response: {str(e)}")
        log_event("Connected to OpenVAS but couldn't determine version")
    
    # Create a target for scanning
    log_event(f"Creating OpenVAS target for {target}")
    target_name = f"Python_Scan_{timestamp}"
    
    # Extract hostname/IP for target creation
    hostname = target.replace('http://', '').replace('https://', '').split('/')[0]
    target_data = f'<create_target><name>{target_name}</name><hosts>{hostname}</hosts></create_target>'
    
    target_response = gvm_request("", method="POST", data=target_data)
    if not target_response:
        log_event("Failed to create target in OpenVAS")
        generate_reports(note="Failed to create target in OpenVAS")
        return
    
    try:
        target_root = ET.fromstring(target_response)
        target_id = target_root.find("create_target_response").get("id")
        log_event(f"Target created with ID: {target_id}")
    except Exception as e:
        log_event(f"Error parsing target creation response: {str(e)}")
        generate_reports(note="Failed to parse target creation response")
        return
    
    # Get available scan configs
    log_event("Getting available scan configurations...")
    config_response = gvm_request("/get_configs")
    if not config_response:
        log_event("Failed to get scan configurations")
        generate_reports(note="Failed to get scan configurations")
        return
    
    try:
        config_root = ET.fromstring(config_response)
        # Try to find Full and Fast scan config
        config_id = None
        for config in config_root.findall(".//config"):
            name = config.find("name").text
            if "Full and fast" in name:
                config_id = config.get("id")
                log_event(f"Using '{name}' scan configuration")
                break
        
        if not config_id:
            # If Full and Fast not found, use the first available config
            config_id = config_root.find(".//config").get("id")
            config_name = config_root.find(".//config/name").text
            log_event(f"Full and fast scan config not found, using '{config_name}' as fallback")
    except Exception as e:
        log_event(f"Error finding scan configuration: {str(e)}")
        generate_reports(note="Failed to find scan configuration")
        return
    
    # Create a task for scanning
    log_event("Creating scan task...")
    task_name = f"Scan_{target_name}_{timestamp}"
    task_data = f'<create_task><name>{task_name}</name><target id="{target_id}"/><config id="{config_id}"/></create_task>'
    
    task_response = gvm_request("", method="POST", data=task_data)
    if not task_response:
        log_event("Failed to create scan task")
        generate_reports(note="Failed to create scan task")
        return
    
    try:
        task_root = ET.fromstring(task_response)
        task_id = task_root.find("create_task_response").get("id")
        log_event(f"Scan task created with ID: {task_id}")
    except Exception as e:
        log_event(f"Error parsing task creation response: {str(e)}")
        generate_reports(note="Failed to parse task creation response")
        return
    
    # Start the scan
    log_event(f"Starting scan of {target}...")
    start_data = f'<start_task task_id="{task_id}"/>'
    
    start_response = gvm_request("", method="POST", data=start_data)
    if not start_response:
        log_event("Failed to start scan")
        generate_reports(note="Failed to start scan")
        return
    
    try:
        start_root = ET.fromstring(start_response)
        report_id = start_root.find("start_task_response").get("report_id")
        log_event(f"Scan started, report ID: {report_id}")
    except Exception as e:
        log_event(f"Error parsing scan start response: {str(e)}")
        generate_reports(note="Failed to parse scan start response")
        return
    
    # Monitor scan progress
    log_event("Monitoring scan progress...")
    scan_complete = False
    timeout = time.time() + 3600  # 1 hour timeout
    
    while not scan_complete and time.time() < timeout:
        try:
            task_status_data = f'<get_tasks task_id="{task_id}" details="1"/>'
            status_response = gvm_request("", method="POST", data=task_status_data)
            
            if not status_response:
                log_event("Failed to get task status, will retry...")
                time.sleep(30)
                continue
            
            status_root = ET.fromstring(status_response)
            status = status_root.find(".//status").text
            progress = status_root.find(".//progress").text
            
            log_event(f"Scan status: {status}, progress: {progress}%")
            
            if status == "Done":
                scan_complete = True
                log_event("Scan completed successfully!")
                break
            
            # Wait before checking again
            time.sleep(30)
        except Exception as e:
            log_event(f"Error checking scan status: {str(e)}")
            time.sleep(30)
    
    if not scan_complete:
        log_event("Scan timed out or failed to complete")
        
    # Generate reports
    log_event("Generating reports...")
    generate_reports(scan_id=task_id, report_id=report_id)
    
    log_event("All tasks completed!")

# Run the scan
if __name__ == "__main__":
    try:
        run_openvas_scan()
    except KeyboardInterrupt:
        log_event("Scan interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_event(f"Unhandled exception: {str(e)}")
        generate_reports(note=f"Scan failed with error: {str(e)}")
        sys.exit(1)
