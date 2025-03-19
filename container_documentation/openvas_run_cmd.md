# Running OpenVAS Vulnerability Scanner

This document explains how to run the OpenVAS vulnerability scanner using our script.

## Quick Method (Recommended)

Use our PowerShell script for a simple one-command scan:

```powershell
.\run_openvas_scan.ps1 https://example.com
```

### Additional Options

```powershell
# Keep the container running after scanning (for faster subsequent scans)
.\run_openvas_scan.ps1 https://example.com -keepContainerRunning

# Use an already running container (much faster for subsequent scans)
.\run_openvas_scan.ps1 https://example.com -useExistingContainer

# Increase wait time for initialization (for first-time runs)
.\run_openvas_scan.ps1 https://example.com -waitTimeMinutes 25
```

### What This Will Do

1. Set up the OpenVAS container (using immauss/openvas:latest which includes all components)
2. Wait for the OpenVAS services to fully initialize (may take 15-25 minutes on first run)
3. Run a complete scan against the target URL
4. Generate reports in the `reports` directory
5. Open the web interface for viewing detailed results
6. Either stop the container or keep it running based on your options

## Best Practices for Faster Scans

For the best experience with OpenVAS, we recommend:

1. **First-time setup**: Run with `-keepContainerRunning -waitTimeMinutes 25` to ensure full initialization
2. **Subsequent scans**: Run with `-useExistingContainer` to avoid the long initialization time
3. **When finished**: Stop the container manually with `docker stop openvas`

This approach provides the fastest scanning experience and avoids the long initialization period each time.

## Manual Method

If you prefer to run the steps manually, here are the commands:

### 1. Start and Keep the OpenVAS Container

```powershell
# Start the OpenVAS all-in-one container with persistent data
docker run -d --name openvas \
  -p 443:443 -p 9392:9392 \
  -e PUBLIC_HOSTNAME="localhost" \
  -e ADMIN_PASSWORD="admin" \
  -v ./reports:/reports \
  -v openvas-data:/data \
  immauss/openvas:latest
```

### 2. Wait for the System to Initialize

The OpenVAS system needs time to initialize, especially on first run:

```powershell
# First-time initialization may take 15-25 minutes
# You can check status with: docker logs -f openvas
```

### 3. Check Container Health

```powershell
# Check if container is healthy
docker inspect --format='{{.State.Health.Status}}' openvas

# View container logs
docker logs --tail 100 openvas
```

### 4. Access the Web Interface

Once initialized, you can access the web interface at either:

```
https://localhost:443  (primary port)
https://localhost:9392 (alternate port)
```

Default credentials:
- Username: `admin`
- Password: `admin`

### 5. Run the Python Scanner

```powershell
# Basic scan
python container_documentation/openvas_test.py https://example.com

# With additional retry options
python container_documentation/openvas_test.py https://example.com --retries 15 --retry-delay 20
```

### 6. For Future Scans

```powershell
# Start the existing container (after it's been stopped)
docker start openvas

# Stop the container when done
docker stop openvas
```

## Understanding the Reports

Reports are saved in the `reports` directory with names like:
- `openvas_report_example.com_2023-04-01_12-34-56.json` - JSON format for integration with other tools
- `openvas_report_example.com_2023-04-01_12-34-56.xml` - XML format containing all scan details
- `openvas_report_example.com_2023-04-01_12-34-56.html` - Human-readable HTML report
- `openvas_report_example.com_2023-04-01_12-34-56.pdf` - PDF report for documentation
- `openvas_report_example.com_2023-04-01_12-34-56.log` - Scan log with detailed scanner activity

You can also access more detailed reports through the web interface.

## About the immauss/openvas Container

The `immauss/openvas` container is an all-in-one solution that includes:

1. **Greenbone Vulnerability Manager (GVM)**: The core management service
2. **PostgreSQL**: Database for storing vulnerability data and scan results 
3. **OpenVAS Scanner**: The actual scanning engine
4. **Redis**: Used for caching and message passing between components
5. **Greenbone Security Assistant (GSA)**: Web interface for managing scans and viewing reports

All components are pre-configured and ready to use in a single container, which greatly simplifies the setup compared to using separate containers.

## Critical Troubleshooting Tips

### 1. Initialization Time is LONG

**The most common issue**: On first run, the system needs to download vulnerability definitions and initialize the database, which can take **15-25 minutes**. Be patient!

### 2. "Connection aborted" Errors

If you see "Connection aborted" errors:
- This usually means the services inside the container are still initializing
- Use `-waitTimeMinutes 25` to allow more initialization time
- Try both ports (443 and 9392) as sometimes one works before the other

### 3. Empty Reports

If you get empty reports:
- Container services may not be fully initialized yet
- Run with `-keepContainerRunning` and try the scan again after 5-10 minutes
- Check container health: `docker inspect --format='{{.State.Health.Status}}' openvas`

### 4. Web Interface Access

The container exposes two web interfaces:
```powershell
# Check which one works for you:
Invoke-WebRequest -Uri "https://localhost:443" -SkipCertificateCheck
Invoke-WebRequest -Uri "https://localhost:9392" -SkipCertificateCheck
```

### 5. Other Common Issues

- **Network Issues**: Make sure ports 443 and 9392 are not in use by other applications
- **Docker Resources**: Ensure Docker has at least 4GB of RAM allocated (Settings → Resources → Memory)
- **Persistent Data**: Always use the `-v openvas-data:/data` volume mount to preserve scan data
- **Reset Installation**: If you need to start fresh, remove the container and volumes:
  ```powershell
  docker rm -f openvas
  docker volume rm openvas-data
  ```

### 6. For Corporate Environments

If your organization uses proxies or firewalls:
- The connection could be blocked by security software
- Try adding `--network host` to the Docker run command
- You may need to configure proxy settings within the container
