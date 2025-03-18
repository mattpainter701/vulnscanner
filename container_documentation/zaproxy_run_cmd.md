# Running ZAProxy Vulnerability Scanner

This document explains how to run the OWASP ZAP vulnerability scanner using our script.

## Quick Method (Recommended)

Use our PowerShell script for a simple one-command scan:

```powershell
.\run_zap_scan.ps1 https://example.com
```

This will:
1. Start the ZAP container
2. Run a complete scan against the target URL
3. Generate reports in the `reports` directory
4. Stop the container when finished

## Manual Method

If you prefer to run the steps manually, here are the commands:

### 1. Start the ZAP Container

```powershell
docker run -d --name zap -p 8080:8080 -v "${PWD}:/home/zap/wrk" zaproxy/zap-weekly zap.sh -daemon -host 0.0.0.0 -config api.key=mysecretapikey -config api.addrs.addr.name=.* -config api.addrs.addr.regex=true
```

🔹 Breakdown of Each Flag:
- `-d` → Runs the container in detached mode (background).
- `--name zap` → Names the container zap for easy reference.
- `-p 8080:8080` → Exposes port 8080 for API/Web UI access.
- `-v "${PWD}:/home/zap/wrk"` → Mounts the current directory into the container to persist reports.
- `zaproxy/zap-weekly` → Uses the weekly ZAP container image.
- `zap.sh -daemon -host 0.0.0.0` → Runs ZAP in daemon mode so it accepts API requests.
- `-config api.key=mysecretapikey` → Sets the API key for secure API access.
- `-config api.addrs.addr.name=.*` → Allows API requests from all addresses.
- `-config api.addrs.addr.regex=true` → Interprets the addr.name as a regex.

### 2. Run the Python Scanner

```powershell
python container_documentation/zaproxy_test.py https://example.com
```

### 3. Stop the Container When Done

```powershell
docker stop zap
```

## Understanding the Reports

Reports are saved in the `reports` directory with names like:
- `zap_report_example.com_2023-04-01_12-34-56.json`
- `zap_report_example.com_2023-04-01_12-34-56.xml`
- `zap_report_example.com_2023-04-01_12-34-56.html`
- `zap_report_example.com_2023-04-01_12-34-56.log`

The HTML report is the most user-friendly and provides a complete overview of the scan results.

## Troubleshooting

If you encounter issues:

1. Check the Docker container status:
   ```powershell
   docker ps -a | findstr zap
   ```

2. View container logs:
   ```powershell
   docker logs zap
   ```

3. Verify the target is accessible from your machine:
   ```powershell
   curl -k https://example.com
   ```

4. Ensure the correct path is mounted:
   ```powershell
   docker exec zap ls -la /home/zap/wrk
   ```
