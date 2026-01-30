# Multimodal RAG System - Quick Start Script
# This script will start the server with automatic port selection

Write-Host "="*60 -ForegroundColor Cyan
Write-Host "  Multimodal RAG System - Starting Server" -ForegroundColor Cyan  
Write-Host "="*60 -ForegroundColor Cyan
Write-Host ""

# Change to project directory
Set-Location $PSScriptRoot

# Try ports 8000-8010
$port = 8000
$started = $false

while (-not $started -and $port -lt 8010) {
    Write-Host "Trying port $port..." -ForegroundColor Yellow
    
    # Test if port is available
    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
        $listener.Start()
        $listener.Stop()
        
        # Port is available, start server
        Write-Host "`n✅ Port $port is available!" -ForegroundColor Green
        Write-Host "`n🚀 Starting server on http://localhost:$port" -ForegroundColor Cyan
        Write-Host ""
        
        python -m uvicorn backend.app:app --host 0.0.0.0 --port $port
        $started = $true
    }
    catch {
        Write-Host "  ✗ Port $port in use, trying next..." -ForegroundColor Red
        $port++
    }
    finally {
        if ($listener) {
            $listener.Stop()
        }
    }
}

if (-not $started) {
    Write-Host "`n❌ Could not find an available port. Please close other applications." -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
