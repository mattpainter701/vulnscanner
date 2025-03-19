# PowerShell script to run OpenVAS scan
# Usage: .\run_openvas_scan.ps1 <target_url>
param(
    [Parameter(Mandatory=$true)]
    [string]$targetUrl,
    
    [Parameter(Mandatory=$false)]
    [switch]$keepContainerRunning = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$useExistingContainer = $false,
    
    [Parameter(Mandatory=$false)]
    [int]$waitTimeMinutes = 15
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

# Container setup
$containerName = "openvas"
$containerExists = $false
$containerRunning = $false

# Check if OpenVAS container exists and is running
$containerStatus = docker ps -a --filter "name=$containerName" --format "{{.Status}}" 2>$null
if ($containerStatus) {
    $containerExists = $true
    if ($containerStatus -match "^Up") {
        $containerRunning = $true
        Write-Host "OpenVAS container is already running."
    } else {
        Write-Host "OpenVAS container exists but is not running."
    }
}

# Handle container setup based on parameters
if ($useExistingContainer) {
    if (-not $containerExists) {
        Write-Error "No existing OpenVAS container found. Please run without -useExistingContainer first."
        exit 1
    }
    
    if (-not $containerRunning) {
        Write-Host "Starting existing OpenVAS container..."
        docker start $containerName | Out-Null
    }
} else {
    # Remove existing container if it exists
    if ($containerExists) {
        Write-Host "Removing existing OpenVAS container..."
        docker rm -f $containerName | Out-Null
    }
    
    # Start a new OpenVAS container
    Write-Host "Starting new OpenVAS container (immauss/openvas:latest)..."
    docker run -d --name $containerName `
        -p 443:443 -p 9392:9392 `
        -e PUBLIC_HOSTNAME="localhost" `
        -e ADMIN_PASSWORD="admin" `
        -v "${PWD}/reports:/reports" `
        -v "openvas-data:/data" `
        immauss/openvas:latest
}

# Wait for OpenVAS to start
Write-Host "Waiting for OpenVAS to initialize..."
Write-Host "This may take up to $waitTimeMinutes minutes, especially on first run..."

$startTime = Get-Date
$maxWaitTime = (Get-Date).AddMinutes($waitTimeMinutes)
$openvasReady = $false

# First, wait for container to report as healthy
while (-not $openvasReady -and (Get-Date) -lt $maxWaitTime) {
    $containerHealth = docker inspect --format='{{.State.Health.Status}}' $containerName 2>$null
    
    if ($containerHealth -eq "healthy") {
        Write-Host "Container reports as healthy. Checking internal services..."
        
        # Check both main web interfaces (443 and 9392)
        $serviceReady = $false
        
        # Try port 443 first
        try {
            $response = Invoke-WebRequest -Uri "https://localhost:443" -SkipCertificateCheck -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Host "OpenVAS web interface is available on port 443!"
                $serviceReady = $true
                $openvasReady = $true
            }
        } catch {
            # Try port 9392 next
            try {
                $response = Invoke-WebRequest -Uri "https://localhost:9392" -SkipCertificateCheck -TimeoutSec 5 -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    Write-Host "OpenVAS web interface is available on port 9392!"
                    $serviceReady = $true
                    $openvasReady = $true
                    
                    # If we're successful with 9392, update the Python script to use this port
                    Write-Host "Updating API configuration for scan script to use port 9392..."
                    $content = Get-Content container_documentation/openvas_test.py
                    $content = $content -replace "OPENVAS_PORT = .+", "OPENVAS_PORT = `"9392`""
                    Set-Content container_documentation/openvas_test.py $content
                }
            } catch {
                # Neither port is responding yet
            }
        }
        
        if (-not $serviceReady) {
            # Check logs for specific messages that indicate readiness
            $logs = docker logs $containerName --tail 50 2>&1
            if ($logs -match "Your GVM/openvas/postgresql container is now ready to use!" -or
                $logs -match "Healthchecks completed with no issues") {
                Write-Host "OpenVAS service appears to be ready based on logs, but web interface is not responding yet."
                # Wait a bit longer for web interface to be available
                Start-Sleep -Seconds 30
            } else {
                Write-Host "Container is healthy but services still initializing. Waiting..."
                Start-Sleep -Seconds 30
            }
        }
    } else {
        $elapsedTime = (Get-Date) - $startTime
        $elapsedMinutes = [Math]::Floor($elapsedTime.TotalMinutes)
        $elapsedSeconds = $elapsedTime.Seconds
        
        Write-Host "OpenVAS initializing... (elapsed: $elapsedMinutes min $elapsedSeconds sec, container status: $containerHealth)"
        Start-Sleep -Seconds 30
    }
}

if (-not $openvasReady) {
    Write-Host "OpenVAS initialization timed out after $waitTimeMinutes minutes."
    Write-Host "Checking container logs for clues..."
    docker logs --tail 100 $containerName
    
    Write-Host "Container status:"
    docker ps -a | findstr "openvas"
    
    # Ask user if they want to continue
    $continue = Read-Host "Container may still be initializing. Do you want to continue with the scan attempt anyway? (y/n)"
    if ($continue -ne "y") {
        if (-not $keepContainerRunning) {
            Write-Host "Stopping container..."
            docker stop $containerName
        }
        exit 1
    }
}

# Check current port configuration in the Python script
$content = Get-Content container_documentation/openvas_test.py
if ($content -match "OPENVAS_PORT = `"(\d+)`"") {
    $currentPort = $matches[1]
    Write-Host "Current API port in Python script is: $currentPort"
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
Write-Host "Note: If this fails, try running the script with -waitTimeMinutes 25 for longer initialization time."
py container_documentation/openvas_test.py "$targetUrl"

# Check if reports were generated
$reportPattern = "reports/openvas_report_*$($sanitized_target)*"
$reportFiles = Get-ChildItem -Path $reportPattern -ErrorAction SilentlyContinue
if ($reportFiles.Count -eq 0) {
    Write-Host "`nWarning: No reports were generated. OpenVAS may still be initializing."
    Write-Host "Consider using the '-keepContainerRunning' option and try again in 5-10 minutes."
    Write-Host "Browse to https://localhost:$currentPort to check if the web interface is available yet."
} else {
    Write-Host "`nScan completed! Check the generated reports."
    Write-Host "Reports are saved in the 'reports' directory with names starting with 'openvas_report_'"
}

# Open browser to OpenVAS web interface
Write-Host "Opening OpenVAS web interface..."
Write-Host "Default credentials: admin / admin"
Start-Process "https://localhost:$currentPort"

# Container management
if (-not $keepContainerRunning) {
    Write-Host "Stopping OpenVAS container..."
    docker stop $containerName
    Write-Host "OpenVAS container stopped."
} else {
    Write-Host "OpenVAS container is still running."
    Write-Host "Browse to https://localhost:$currentPort to access the web interface."
    Write-Host "Run future scans with the '-useExistingContainer' flag to avoid initialization time."
    Write-Host "Stop it manually when done with: docker stop $containerName"
} 