# restore_snapshot.ps1
# Usage: .\restore_snapshot.ps1

Write-Host "--- Starting Project Restoration ---" -ForegroundColor Cyan

$snapshotDir = "snapshots"

# 1. Restore MySQL
if (Test-Path "$snapshotDir/mysql_backup.sql") {
    Write-Host "Restoring MySQL..." -ForegroundColor Yellow
    mysql -u root < "$snapshotDir/mysql_backup.sql"
    Write-Host "✅ MySQL Restored successfully." -ForegroundColor Green
} else {
    Write-Host "⚠️ Warning: $snapshotDir/mysql_backup.sql not found." -ForegroundColor Red
}

# 2. Restore MongoDB
if (Test-Path "$snapshotDir/mongo_backup/") {
    Write-Host "Restoring MongoDB..." -ForegroundColor Yellow
    mongorestore --dir "$snapshotDir/mongo_backup/"
    Write-Host "✅ MongoDB Restored successfully." -ForegroundColor Green
} else {
    Write-Host "⚠️ Warning: $snapshotDir/mongo_backup/ not found." -ForegroundColor Red
}

Write-Host "--- Restoration Complete ---" -ForegroundColor Cyan
