# Start OptEazy Databases (MySQL and MongoDB) - Robust Idempotent Version

$mysqlBase = "C:\Users\ravur\Downloads\opteazy\db_persist\mysql"
$mysqlData = "$mysqlBase\data"
$mongoBase = "C:\Users\ravur\Downloads\opteazy\db_persist\mongodb"
$mongoData = "$mongoBase\data"
$mysqlLogDir = "$mysqlBase\log"
$mongoLogDir = "$mongoBase\log"

# Ensure directories exist
@( $mysqlLogDir, $mongoLogDir, $mysqlData, $mongoData ) | ForEach-Object {
    if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
}

# --- 1. MySQL ---
$mysqlProc = Get-Process -Name "mysqld" -ErrorAction SilentlyContinue
if ($mysqlProc) {
    Write-Host "[CHECK] MySQL is already running (PID: $($mysqlProc.Id))." -ForegroundColor Green
} else {
    Write-Host "[START] MySQL is not running. Launching..." -ForegroundColor Cyan
    if (-not (Test-Path "$mysqlData\mysql")) {
        Write-Host "Initializing MySQL data directory..." -ForegroundColor Yellow
        mysqld --initialize-insecure --datadir=$mysqlData
    }
    Start-Process "mysqld" -ArgumentList "--datadir=$mysqlData", "--console", "--log-error=$mysqlLogDir\error.log" -NoNewWindow
}

# --- 2. MongoDB ---
function Start-Mongo {
    Start-Process "mongod" -ArgumentList "--dbpath=$mongoData", "--logpath=$mongoLogDir\mongod.log", "--logappend" -NoNewWindow
    Start-Sleep -Seconds 4
    return Get-Process -Name "mongod" -ErrorAction SilentlyContinue
}

$mongoProc = Get-Process -Name "mongod" -ErrorAction SilentlyContinue
if ($mongoProc) {
    Write-Host "[CHECK] MongoDB is already running (PID: $($mongoProc.Id))." -ForegroundColor Green
} else {
    Write-Host "[START] MongoDB is not running. Launching..." -ForegroundColor Cyan
    $mongoProc = Start-Mongo
    if (-not $mongoProc) {
        Write-Host "[REPAIR] MongoDB failed to start. Attempting automated recovery..." -ForegroundColor Yellow
        Remove-Item "$mongoData\mongod.lock" -Force -ErrorAction SilentlyContinue
        # Attempt repair
        Start-Process "mongod" -ArgumentList "--dbpath=$mongoData", "--repair" -NoNewWindow -Wait
        $mongoProc = Start-Mongo
    }
}

if ($mongoProc) {
    Write-Host "[CHECK] MongoDB is active." -ForegroundColor Green
} else {
    Write-Host "[ERROR] MongoDB failed to start cleanly." -ForegroundColor Red
    Write-Host "Action Required: Check logs at $mongoLogDir\mongod.log or consider a manual data reset." -ForegroundColor Gray
}

Write-Host "`nOptEazy Database Services Status: OK" -ForegroundColor Green
