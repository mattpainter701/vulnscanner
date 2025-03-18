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

# Remove existing OpenVAS container if it exists
Write-Host "Removing any existing OpenVAS container..."
docker rm -f openvas 2>$null

# Start the OpenVAS container
Write-Host "Starting OpenVAS container (immauss/openvas:latest)..."
docker run -d --name openvas `
    -p 443:443 -p 9392:9392 `
    -e PUBLIC_HOSTNAME="localhost" `
    -e ADMIN_PASSWORD="admin" `
    -v "${PWD}/reports:/reports" `
    immauss/openvas:latest

# Wait for OpenVAS to start
Write-Host "Waiting for OpenVAS to initialize..."
Write-Host "This will take some time on first run as it initializes the vulnerability database..."
Start-Sleep -Seconds 60  # Initial wait time

# Check if OpenVAS is running
Write-Host "Checking if OpenVAS is running..."
$openvasRunning = $false
$retry = 0
$maxRetries = 30  # 30 retries × 30 seconds = 15 minutes max wait time

while (-not $openvasRunning -and $retry -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "https://localhost:443" -SkipCertificateCheck -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            $openvasRunning = $true
            Write-Host "OpenVAS is running!"
        } else {
            Write-Host "OpenVAS not fully initialized yet. Waiting 30 more seconds (try $retry of $maxRetries)..."
            Start-Sleep -Seconds 30
            $retry++
        }
    } catch {
        Write-Host "OpenVAS not ready yet. Waiting 30 more seconds (try $retry of $maxRetries)..."
        Start-Sleep -Seconds 30
        $retry++
    }
}

if (-not $openvasRunning) {
    Write-Host "Failed to confirm OpenVAS is running. Checking container logs..."
    docker logs openvas
    Write-Host "Container status:"
    docker ps -a | findstr "openvas"
    Write-Host "You may need to wait longer for OpenVAS to initialize on first run, or there may be issues with the setup."
    
    # Ask user if they want to continue
    $continue = Read-Host "Do you want to continue with the scan attempt anyway? (y/n)"
    if ($continue -ne "y") {
        # Stop container if requested
        if (-not $keepContainerRunning) {
            Write-Host "Stopping container..."
            docker stop openvas
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

# Update the API configuration for the openvas_test.py script
Write-Host "Updating API configuration for scan script..."
$content = Get-Content container_documentation/openvas_test.py
$content = $content -replace "GVM_PORT = .+", "GVM_PORT = `"443`""
Set-Content container_documentation/openvas_test.py $content

# Run the scan
Write-Host "Starting vulnerability scan against $targetUrl..."
py container_documentation/openvas_test.py "$targetUrl"

# Output results location
Write-Host "`nScan completed! Check the generated reports."
Write-Host "Reports are saved in the 'reports' directory with names starting with 'openvas_report_'"

# Open browser to OpenVAS web interface
Write-Host "Opening OpenVAS web interface..."
Write-Host "Default credentials: admin / admin"
Start-Process "https://localhost:443"

# Stop the container by default unless -keepContainerRunning is specified
if (-not $keepContainerRunning) {
    Write-Host "Stopping OpenVAS container..."
    docker stop openvas
    Write-Host "OpenVAS container stopped."
} else {
    Write-Host "OpenVAS container is still running."
    Write-Host "Browse to https://localhost:443 to access the web interface."
    Write-Host "Stop it manually when done with: docker stop openvas"
} 