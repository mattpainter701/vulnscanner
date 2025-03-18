# Vulnerability Scanner

A simple web vulnerability scanner using OWASP ZAP in Docker.

## Requirements

- Docker
- Python 3.x
- PowerShell

## Quick Start

1. Clone the repository
2. Run the scanner with a target URL:

```powershell
.\run_zap_scan.ps1 example.com
```

This will:
- Start a ZAP container
- Run a vulnerability scan against the target
- Generate reports in JSON, XML, and HTML formats

## Reports

Reports are saved in the project root with names starting with `zap_report_` and include:
- A JSON report (for programmatic analysis)
- An XML report (for integration with other tools)
- An HTML report (for human-readable results)

## Manual Execution

If you prefer to run the steps manually:

1. Start the ZAP container:
```powershell
docker run -d --name zap -p 8080:8080 -v "${PWD}:/home/zap/wrk" zaproxy/zap-weekly zap.sh -daemon -host 0.0.0.0 -config api.key=mysecretapikey -config api.addrs.addr.name=.* -config api.addrs.addr.regex=true
```

2. Edit the target in `container_documentation/zaproxy_test.py`

3. Install dependencies:
```powershell
py -m pip install python-owasp-zap-v2.4 requests
```

4. Run the scan:
```powershell
py container_documentation/zaproxy_test.py
```

## Troubleshooting

If you encounter issues:

1. Make sure Docker is running
2. Check container logs: `docker logs zap`
3. Ensure the URL has the correct format (http:// or https://)
4. Check container status: `docker ps -a | findstr zap`
5. The correct mount path for zaproxy/zap-weekly is `/home/zap/wrk` (not `/zap/wrk`)

## For AWS Fargate Deployment

This scanner can be deployed to AWS Fargate with minimal modifications:
- Package the Docker image with the script
- Set environment variables for the target
- Mount an S3 bucket for reports

## Security Considerations

Always ensure you have permission to scan the target system. Unauthorized scanning may be illegal in many jurisdictions. 