# PowerShell script to run OpenVAS scan
# Usage: .\run_openvas_scan.ps1 <target_url>
param(
    [Parameter(Mandatory=$true)]
    [string]$targetUrl,
    
    [Parameter(Mandatory=$false)]
    [switch]$keepContainerRunning = $false
)

# Check if URL has http/https prefix or is an IP address
if (-not ($targetUrl -match "^https?://") -and -not ($targetUrl -match "^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")) {
    Write-Host "Adding https:// prefix to URL..."
    $targetUrl = "https://$targetUrl"
}

# Create reports directory if it doesn't exist
if (-not (Test-Path -Path "reports")) {
    Write-Host "Creating reports directory..."
    New-Item -Path "reports" -ItemType Directory | Out-Null
}

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Error "Docker is not running. Please start Docker and try again."
    exit 1
}

# Create docker network if it doesn't exist
Write-Host "Setting up Docker network for OpenVAS..."
docker network create greenbone-network 2>$null

# Remove existing Greenbone containers if they exist
Write-Host "Removing any existing Greenbone containers..."
docker rm -f gvm-postgres gvm-redis greenbone-vulnerability-manager gvmd ospd-openvas notus-scanner 2>$null

# Set up PostgreSQL container for GVM
Write-Host "Setting up PostgreSQL container for GVM..."
docker run -d --name gvm-postgres `
    --network=greenbone-network `
    -e POSTGRES_PASSWORD=postgres `
    -v gvm-postgres-data:/var/lib/postgresql/data `
    -d postgres:15

# Set up Redis container for OSPD
Write-Host "Setting up Redis container for OSPD..."
docker run -d --name gvm-redis `
    --network=greenbone-network `
    -v gvm-redis-socket:/run/redis/ `
    -d redis:7

# Start main Greenbone Vulnerability Manager container
Write-Host "Starting Greenbone Vulnerability Manager..."
docker run -d --name greenbone-vulnerability-manager `
    --network=greenbone-network `
    -p 9392:9392 `
    -p 5432:5432 `
    -e GREENBONE_SECURITY_MANAGER_LOG_LEVEL=INFO `
    -v greenbone-community-data:/data `
    -v "${PWD}/reports:/reports" `
    --restart unless-stopped `
    greenbone/vulnerability-manager

# Wait for GVM to start
Write-Host "Waiting for Greenbone Vulnerability Manager to start..."
Write-Host "This will take some time on first run as it initializes the vulnerability database..."
Start-Sleep -Seconds 60  # Initial wait time

# Check if GVM is running
Write-Host "Checking if Greenbone Vulnerability Manager is running..."
$gvmRunning = $false
$retry = 0
$maxRetries = 30  # 30 retries × 30 seconds = 15 minutes max wait time

while (-not $gvmRunning -and $retry -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "https://localhost:9392" -SkipCertificateCheck -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            $gvmRunning = $true
            Write-Host "Greenbone Vulnerability Manager is running!"
        } else {
            Write-Host "GVM not fully initialized yet. Waiting 30 more seconds (try $retry of $maxRetries)..."
            Start-Sleep -Seconds 30
            $retry++
        }
    } catch {
        Write-Host "GVM not ready yet. Waiting 30 more seconds (try $retry of $maxRetries)..."
        Start-Sleep -Seconds 30
        $retry++
    }
}

if (-not $gvmRunning) {
    Write-Host "Failed to confirm GVM is running. Checking container logs..."
    docker logs greenbone-vulnerability-manager
    Write-Host "Container status:"
    docker ps -a | findstr "greenbone"
    Write-Host "You may need to wait longer for GVM to initialize on first run, or there may be issues with the setup."
    
    # Ask user if they want to continue
    $continue = Read-Host "Do you want to continue with the scan attempt anyway? (y/n)"
    if ($continue -ne "y") {
        # Stop containers if requested
        if (-not $keepContainerRunning) {
            Write-Host "Stopping containers..."
            docker stop greenbone-vulnerability-manager gvm-postgres gvm-redis
        }
        exit 1
    }
}

# Install required Python packages if not already installed
Write-Host "Checking Python dependencies..."
try {
    python -c "import xml.etree.ElementTree, requests" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installing Python dependencies..."
        py -m pip install requests urllib3
    }
} catch {
    Write-Host "Installing Python dependencies..."
    py -m pip install requests urllib3
}

# Run the scan
Write-Host "Starting vulnerability scan against $targetUrl..."
py container_documentation/openvas_test.py "$targetUrl"

# Output results location
Write-Host "`nScan completed! Check the generated reports."
Write-Host "Reports are saved in the 'reports' directory with names starting with 'openvas_report_'"

# Open browser to Greenbone Security Assistant web interface
Write-Host "Opening Greenbone Security Assistant web interface..."
Write-Host "Default credentials: admin / admin"
Start-Process "https://localhost:9392"

# Stop the containers by default unless -keepContainerRunning is specified
if (-not $keepContainerRunning) {
    Write-Host "Stopping Greenbone containers..."
    docker stop greenbone-vulnerability-manager gvm-postgres gvm-redis
    Write-Host "Greenbone containers stopped."
} else {
    Write-Host "Greenbone containers are still running."
    Write-Host "Browse to https://localhost:9392 to access the web interface."
    Write-Host "Stop them manually when done with: docker stop greenbone-vulnerability-manager gvm-postgres gvm-redis"
} 