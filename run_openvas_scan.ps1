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
Write-Host "Removing any existing OpenVAS containers..."
docker rm -f openvas-scanner 2>$null

# Start OpenVAS container
Write-Host "Starting OpenVAS container..."
docker run -d --name openvas-scanner -p 9392:9392 `
    -v "${PWD}:/data" `
    greenbone/openvas-scanner

# Wait for OpenVAS to start
Write-Host "Waiting for OpenVAS to start..."
Write-Host "This may take several minutes on first run as it initializes the vulnerability database..."
Start-Sleep -Seconds 60  # Initial wait time

# Check if OpenVAS is running - attempt to connect to the web interface
Write-Host "Checking if OpenVAS is running..."
$openvasRunning = $false
$retry = 0
$maxRetries = 12  # 12 retries × 30 seconds = 6 minutes max wait time

while (-not $openvasRunning -and $retry -lt $maxRetries) {
    try {
        $response = docker logs openvas-scanner 2>&1
        if ($response -like "*Ready to serve client connections*") {
            $openvasRunning = $true
            Write-Host "OpenVAS is running!"
        } else {
            Write-Host "OpenVAS not ready yet. Waiting 30 more seconds (try $retry of $maxRetries)..."
            Start-Sleep -Seconds 30
            $retry++
        }
    } catch {
        Write-Host "Error checking OpenVAS status. Waiting 30 more seconds..."
        Start-Sleep -Seconds 30
        $retry++
    }
}

if (-not $openvasRunning) {
    Write-Host "Failed to start OpenVAS. Checking container logs..."
    docker logs openvas-scanner
    Write-Host "Container status:"
    docker ps -a | findstr openvas-scanner
    Write-Host "You may need to wait longer for OpenVAS to initialize on first run."
    exit 1
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

# Stop the container by default unless -keepContainerRunning is specified
if (-not $keepContainerRunning) {
    Write-Host "Stopping OpenVAS container..."
    docker stop openvas-scanner
    Write-Host "OpenVAS container stopped."
} else {
    Write-Host "OpenVAS container is still running. Stop it manually when done with 'docker stop openvas-scanner'"
} 