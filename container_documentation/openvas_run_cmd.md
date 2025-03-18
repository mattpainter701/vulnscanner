# Running OpenVAS Vulnerability Scanner

This document explains how to run the OpenVAS vulnerability scanner using our script.

## Quick Method (Recommended)

Use our PowerShell script for a simple one-command scan:

```powershell
.\run_openvas_scan.ps1 https://example.com
```

This will:
1. Start the OpenVAS container
2. Run a complete scan against the target URL
3. Generate reports in the `reports` directory
4. Stop the container when finished

## Manual Method

If you prefer to run the steps manually, here are the commands:

### 1. Start the OpenVAS Container

```powershell
docker run -d --name openvas-scanner -p 9392:9392 -v "${PWD}:/data" greenbone/openvas-scanner
```

🔹 Breakdown of Each Flag:
- `-d` → Runs the container in detached mode (background).
- `--name openvas-scanner` → Names the container for easy reference.
- `-p 9392:9392` → Exposes port 9392 for GSA (Greenbone Security Assistant) web interface.
- `-v "${PWD}:/data"` → Mounts the current directory into the container to persist reports.
- `greenbone/openvas-scanner` → Uses the official OpenVAS scanner image.

### 2. Wait for OpenVAS to Start

OpenVAS can take several minutes to initialize on first run:

```powershell
docker logs -f openvas-scanner
```

Wait until you see "Ready to serve client connections" in the logs.

### 3. Run the Python Scanner

```powershell
python container_documentation/openvas_test.py https://example.com
```

### 4. Stop the Container When Done

```powershell
docker stop openvas-scanner
```

## Understanding the Reports

Reports are saved in the `reports` directory with names like:
- `openvas_report_example.com_2023-04-01_12-34-56.json` - JSON format for integration with other tools
- `openvas_report_example.com_2023-04-01_12-34-56.xml` - XML format containing all scan details
- `openvas_report_example.com_2023-04-01_12-34-56.html` - Human-readable HTML report
- `openvas_report_example.com_2023-04-01_12-34-56.pdf` - PDF report for documentation
- `openvas_report_example.com_2023-04-01_12-34-56.log` - Scan log with detailed scanner activity

## OpenVAS vs. ZAP

OpenVAS and ZAP have different strengths:

- **OpenVAS**: Powerful for network-level vulnerability scanning, supports wider range of vulnerability checks, including system-level vulnerabilities. Better for comprehensive security audits.

- **ZAP**: Focused on web application security testing, OWASP Top 10 vulnerabilities, more suited for web developers and application security testing.

Consider using both scanners for maximum coverage.

## Troubleshooting

If you encounter issues:

1. **Initialization Time**: On first run, OpenVAS needs to download vulnerability definitions, which can take 5-10 minutes.

2. **Connection Issues**: Check container logs:
   ```powershell
   docker logs openvas-scanner
   ```

3. **Container Status**:
   ```powershell
   docker ps -a | findstr openvas-scanner
   ```

4. **Authentication Problems**: Default credentials are admin/admin, verify they are set correctly in the script.

5. **Network Access**: Ensure the target is accessible from your machine:
   ```powershell
   curl -k https://example.com
   ```
