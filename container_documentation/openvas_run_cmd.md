# Running OpenVAS Vulnerability Scanner

This document explains how to run the OpenVAS vulnerability scanner using our script.

## Quick Method (Recommended)

Use our PowerShell script for a simple one-command scan:

```powershell
.\run_openvas_scan.ps1 https://example.com
```

This will:
1. Set up the complete Greenbone Vulnerability Management stack (with PostgreSQL and Redis)
2. Run a complete scan against the target URL
3. Generate reports in the `reports` directory
4. Open the web interface for viewing detailed results
5. Stop the containers when finished (unless you specify `-keepContainerRunning`)

## Manual Method

If you prefer to run the steps manually, here are the commands:

### 1. Create a Network for the Containers

```powershell
docker network create greenbone-network
```

### 2. Start the Required Containers

```powershell
# PostgreSQL database
docker run -d --name gvm-postgres --network=greenbone-network -e POSTGRES_PASSWORD=postgres -v gvm-postgres-data:/var/lib/postgresql/data postgres:15

# Redis for scan engine
docker run -d --name gvm-redis --network=greenbone-network -v gvm-redis-socket:/run/redis/ redis:7

# Main Greenbone Vulnerability Manager
docker run -d --name greenbone-vulnerability-manager --network=greenbone-network -p 9392:9392 -p 5432:5432 -v greenbone-community-data:/data -v ./reports:/reports greenbone/vulnerability-manager
```

### 3. Wait for the System to Initialize

The Greenbone system needs time to initialize, especially on first run:

```powershell
# Wait at least 5-10 minutes for first-time initialization
```

### 4. Access the Web Interface

Once initialized, you can access the web interface at:

```
https://localhost:9392
```

Default credentials:
- Username: `admin`
- Password: `admin`

### 5. Run the Python Scanner

```powershell
python container_documentation/openvas_test.py https://example.com
```

### 6. Stop the Containers When Done

```powershell
docker stop greenbone-vulnerability-manager gvm-postgres gvm-redis
```

## Understanding the Reports

Reports are saved in the `reports` directory with names like:
- `openvas_report_example.com_2023-04-01_12-34-56.json` - JSON format for integration with other tools
- `openvas_report_example.com_2023-04-01_12-34-56.xml` - XML format containing all scan details
- `openvas_report_example.com_2023-04-01_12-34-56.html` - Human-readable HTML report
- `openvas_report_example.com_2023-04-01_12-34-56.pdf` - PDF report for documentation
- `openvas_report_example.com_2023-04-01_12-34-56.log` - Scan log with detailed scanner activity

You can also access more detailed reports through the web interface at https://localhost:9392.

## System Architecture

The Greenbone Vulnerability Management system consists of several components:

1. **Greenbone Vulnerability Manager (GVM)**: The core management service
2. **PostgreSQL**: Database for storing vulnerability data and scan results
3. **OpenVAS Scanner**: The actual scanning engine
4. **Redis**: Used for caching and message passing between components
5. **Greenbone Security Assistant (GSA)**: Web interface for managing scans and viewing reports

## Troubleshooting

If you encounter issues:

1. **Initialization Time**: On first run, the system needs to download vulnerability definitions and initialize the database, which can take **15-20 minutes**. Be patient!

2. **Web Interface Not Available**: Check container status:
   ```powershell
   docker ps -a | findstr greenbone
   ```

3. **View Container Logs**:
   ```powershell
   docker logs greenbone-vulnerability-manager
   ```

4. **Network Issues**: Make sure ports 9392 and 5432 are not in use by other applications.

5. **Container Volumes**: If data seems to be missing after restarts, check your Docker volumes:
   ```powershell
   docker volume ls | findstr greenbone
   ```

6. **Reset Installation**: If you need to start fresh, remove the containers and volumes:
   ```powershell
   docker rm -f gvm-postgres gvm-redis greenbone-vulnerability-manager
   docker volume rm gvm-postgres-data gvm-redis-socket greenbone-community-data
   ```
