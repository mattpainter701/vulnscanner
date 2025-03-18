# Running OpenVAS Vulnerability Scanner

This document explains how to run the OpenVAS vulnerability scanner using our script.

## Quick Method (Recommended)

Use our PowerShell script for a simple one-command scan:

```powershell
.\run_openvas_scan.ps1 https://example.com
```

This will:
1. Set up the OpenVAS container (using immauss/openvas:latest which includes all components)
2. Run a complete scan against the target URL
3. Generate reports in the `reports` directory
4. Open the web interface for viewing detailed results
5. Stop the container when finished (unless you specify `-keepContainerRunning`)

## Manual Method

If you prefer to run the steps manually, here are the commands:

### 1. Start the OpenVAS Container

```powershell
# Start the OpenVAS all-in-one container
docker run -d --name openvas \
  -p 443:443 \
  -e PUBLIC_HOSTNAME="localhost" \
  -e ADMIN_PASSWORD="admin" \
  -v ./reports:/reports \
  immauss/openvas:latest
```

### 2. Wait for the System to Initialize

The OpenVAS system needs time to initialize, especially on first run:

```powershell
# Wait at least 5-10 minutes for first-time initialization
```

### 3. Access the Web Interface

Once initialized, you can access the web interface at:

```
https://localhost:443
```

Default credentials:
- Username: `admin`
- Password: `admin`

### 4. Run the Python Scanner

```powershell
python container_documentation/openvas_test.py https://example.com
```

### 5. Stop the Container When Done

```powershell
docker stop openvas
```

## Understanding the Reports

Reports are saved in the `reports` directory with names like:
- `openvas_report_example.com_2023-04-01_12-34-56.json` - JSON format for integration with other tools
- `openvas_report_example.com_2023-04-01_12-34-56.xml` - XML format containing all scan details
- `openvas_report_example.com_2023-04-01_12-34-56.html` - Human-readable HTML report
- `openvas_report_example.com_2023-04-01_12-34-56.pdf` - PDF report for documentation
- `openvas_report_example.com_2023-04-01_12-34-56.log` - Scan log with detailed scanner activity

You can also access more detailed reports through the web interface at https://localhost:443.

## About the immauss/openvas Container

The `immauss/openvas` container is an all-in-one solution that includes:

1. **Greenbone Vulnerability Manager (GVM)**: The core management service
2. **PostgreSQL**: Database for storing vulnerability data and scan results 
3. **OpenVAS Scanner**: The actual scanning engine
4. **Redis**: Used for caching and message passing between components
5. **Greenbone Security Assistant (GSA)**: Web interface for managing scans and viewing reports

All components are pre-configured and ready to use in a single container, which greatly simplifies the setup compared to using separate containers.

## Troubleshooting

If you encounter issues:

1. **Initialization Time**: On first run, the system needs to download vulnerability definitions and initialize the database, which can take **15-20 minutes**. Be patient!

2. **Web Interface Not Available**: Check container status:
   ```powershell
   docker ps -a | findstr openvas
   ```

3. **View Container Logs**:
   ```powershell
   docker logs openvas
   ```

4. **Network Issues**: Make sure port 443 is not in use by other applications.

5. **Container Storage**: If you need to preserve scan data between container restarts, mount a persistent volume:
   ```powershell
   docker run -d --name openvas -p 443:443 -v openvas-data:/data -v ./reports:/reports immauss/openvas:latest
   ```

6. **Reset Installation**: If you need to start fresh, remove the container and volumes:
   ```powershell
   docker rm -f openvas
   docker volume rm openvas-data
   ```

7. **"Could not connect to server" Error**: This is normal during initialization. Wait for the database and services to fully start.

8. **Limited Resources**: The container requires significant resources. Ensure Docker has at least 4GB of memory allocated:
   - Windows/Mac: Docker Desktop Settings → Resources → Memory
