# Stop OptEazy Databases (MySQL and MongoDB) - Graceful Termination

Write-Host "Gracefully stopping databases..." -ForegroundColor Cyan

# --- 1. MySQL ---
$mysqlProc = Get-Process -Name "mysqld" -ErrorAction SilentlyContinue
if ($mysqlProc) {
    Write-Host "[STOP] Stopping MySQL (PID: $($mysqlProc.Id))..." -ForegroundColor Yellow
    # Using mysqladmin for a clean shutdown
    mysqladmin -u root shutdown 2>$null
    Start-Sleep -Seconds 2
    # Verify
    if (Get-Process -Name "mysqld" -ErrorAction SilentlyContinue) {
        Write-Host "MySQL still running. Using fallback force shutdown..." -ForegroundColor Gray
        Stop-Process -Name "mysqld" -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "[CHECK] MySQL is not running." -ForegroundColor Green
}

# --- 2. MongoDB ---
$mongoProc = Get-Process -Name "mongod" -ErrorAction SilentlyContinue
if ($mongoProc) {
    Write-Host "[STOP] Stopping MongoDB (PID: $($mongoProc.Id))..." -ForegroundColor Yellow
    # Attempt a standard Stop-Process (sends a termination signal)
    # Note: On Windows, without mongosh/mongo shell, this is the most common way.
    Stop-Process -Name "mongod" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    # Verify
    if (Get-Process -Name "mongod" -ErrorAction SilentlyContinue) {
        Write-Host "MongoDB still running. Using fallback force shutdown..." -ForegroundColor Gray
        Stop-Process -Name "mongod" -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "[CHECK] MongoDB is not running." -ForegroundColor Green
}

Write-Host "`nOptEazy Database Services: STOPPED" -ForegroundColor Green
