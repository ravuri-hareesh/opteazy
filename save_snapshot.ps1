# save_snapshot.ps1
# Usage: .\save_snapshot.ps1 "Optional commit message"

param (
    [string]$CommitMessage = "Project Snapshot: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
)

Write-Host "--- Starting Project Snapshot ---" -ForegroundColor Cyan

# 1. Ensure snapshots directory exists
$snapshotDir = "snapshots"
if (!(Test-Path $snapshotDir)) { 
    Write-Host "Creating snapshots directory..." -ForegroundColor Gray
    New-Item -ItemType Directory -Path $snapshotDir 
}

# 2. Dump MySQL (All Databases)
Write-Host "Dumping MySQL databases..." -ForegroundColor Yellow
try {
    # We use -u root and assume no password (Scoop default)
    mysqldump -u root --all-databases --result-file="$snapshotDir/mysql_backup.sql"
    Write-Host "✅ MySQL Exported to $snapshotDir/mysql_backup.sql" -ForegroundColor Green
} catch {
    Write-Host "❌ MySQL Dump Failed. Ensure MySQL is running." -ForegroundColor Red
}

# 3. Dump MongoDB (All Databases)
Write-Host "Dumping MongoDB databases..." -ForegroundColor Yellow
try {
    # Dumps to a folder structure
    mongodump --out "$snapshotDir/mongo_backup/"
    Write-Host "✅ MongoDB Exported to $snapshotDir/mongo_backup/" -ForegroundColor Green
} catch {
    Write-Host "❌ MongoDB Dump Failed. Ensure MongoDB is running." -ForegroundColor Red
}

# 4. Git Synchronization
Write-Host "Syncing with Git repository..." -ForegroundColor Cyan
git add .
git commit -m "$CommitMessage"

Write-Host "Pushing to remote..." -ForegroundColor Yellow
git push

Write-Host "--- Snapshot Complete and Pushed ---" -ForegroundColor Cyan
