$sessionsDir = "data\research\sessions"
$reportsDir = "data\research\reports"

# Get all session files
$sessions = Get-ChildItem -Path $sessionsDir -Filter "session_*.json"

# Build set of used report filenames
$usedReports = @()

foreach ($session in $sessions) {
    $content = Get-Content $session.FullName -Raw | ConvertFrom-Json
    $batchId = $content.metadata.batch_id
    $sessionId = $content.metadata.session_id
    
    if ($batchId -and $sessionId) {
        $reportName = "report_${batchId}_${sessionId}.md"
        $usedReports += $reportName
        Write-Host "Session $($session.Name) -> $reportName"
    }
}

# Get all report files
$allReports = Get-ChildItem -Path $reportsDir -Filter "report_*.md" | Select-Object -ExpandProperty Name

# Find unused reports
$unusedReports = $allReports | Where-Object { $usedReports -notcontains $_ }

Write-Host "`n=== USED REPORTS ($($usedReports.Count)) ==="
$usedReports | Sort-Object | ForEach-Object { Write-Host $_ }

Write-Host "`n=== UNUSED REPORTS ($($unusedReports.Count)) ==="
$unusedReports | Sort-Object | ForEach-Object { Write-Host $_ }

# Return unused reports for deletion
return $unusedReports

