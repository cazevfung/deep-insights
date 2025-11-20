[CmdletBinding()]
param(
    [string]$Repo = "cazevfung/deep-research-tool",
    [string]$Branch = "main",
    [switch]$DryRun,
    [switch]$SkipPush,
    [switch]$SkipRelease,
    [string]$ReleaseNotesDir = "release-notes"
)

$ErrorActionPreference = "Stop"

function Invoke-CommandChecked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$Description = ""
    )

    $commandText = "$FilePath $($Arguments -join ' ')".Trim()
    if ($PSBoundParameters.ContainsKey("Description") -and $Description) {
        Write-Host ("`n==== {0} ====" -f $Description)
    }

    if ($DryRun) {
        Write-Host "[dry-run] $commandText"
        return
    }

    Write-Host "→ $commandText"
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed (exit code $LASTEXITCODE): $commandText"
    }
}

Push-Location -Path $PSScriptRoot
try {
    if (-not (Test-Path -Path $ReleaseNotesDir -PathType Container)) {
        throw "Release notes directory '$ReleaseNotesDir' not found."
    }

    $latestNote = Get-ChildItem -Path $ReleaseNotesDir -Filter "v*.md" -File |
        Sort-Object { [version]($_.BaseName.TrimStart('v')) } -Descending |
        Select-Object -First 1

    if (-not $latestNote) {
        throw "No release notes found matching pattern 'v*.md' in '$ReleaseNotesDir'."
    }

    $noteBody = Get-Content -Path $latestNote.FullName -Raw
    $versionMatch = [regex]::Match($noteBody, '##\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)')
    if (-not $versionMatch.Success) {
        throw "Release note '$($latestNote.Name)' does not contain a version heading (## x.y or ## x.y.z)."
    }

    $version = $versionMatch.Groups[1].Value
    $tagName = "v$version"

    Write-Host ("Preparing publish pipeline for {0} using {1}" -f $tagName, $latestNote.Name)

    if (-not $DryRun) {
        & git rev-parse --verify HEAD > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            & git reset --quiet HEAD > $null 2>&1
        } else {
            Write-Host "No commits yet; skipping git reset."
        }
    }

    Invoke-CommandChecked -FilePath "git" -Arguments @("add", $ReleaseNotesDir) -Description "Stage release notes"

    $hasStagedChanges = $true
    if (-not $DryRun) {
        & git diff --cached --quiet
        $hasStagedChanges = ($LASTEXITCODE -ne 0)
    }

    if ($hasStagedChanges) {
        Invoke-CommandChecked -FilePath "git" -Arguments @("commit", "-m", "chore: release $tagName") -Description "Commit release notes"
    } else {
        Write-Host "No staged release note changes to commit; skipping commit step."
    }

    if (-not $DryRun) {
        $existingTag = (& git tag -l $tagName)
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to query existing tags."
        }

        if ($existingTag) {
            throw "Tag '$tagName' already exists. Delete or bump the version before rerunning."
        }
    }

    Invoke-CommandChecked -FilePath "git" -Arguments @("tag", "-a", $tagName, "-m", "Release $version") -Description "Create annotated tag"

    if (-not $SkipPush) {
        Invoke-CommandChecked -FilePath "git" -Arguments @("push", "origin", $Branch) -Description "Push branch '$Branch'"
        Invoke-CommandChecked -FilePath "git" -Arguments @("push", "origin", $tagName) -Description "Push tag '$tagName'"
    } else {
        Write-Host "Skipping git push steps because -SkipPush was supplied."
    }

    if (-not $SkipRelease) {
        $tempNotes = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "release-notes-$tagName-$([guid]::NewGuid()).md")
        try {
            if (-not $DryRun) {
                Set-Content -Path $tempNotes -Value $noteBody -Encoding UTF8
            }

            Invoke-CommandChecked `
                -FilePath "gh" `
                -Arguments @(
                    "release", "create", $tagName,
                    "--repo", $Repo,
                    "--title", $tagName,
                    "--notes-file", $tempNotes
                ) `
                -Description "Create GitHub release for $tagName"
        }
        finally {
            if (-not $DryRun -and (Test-Path $tempNotes)) {
                Remove-Item -Path $tempNotes -Force
            }
        }
    } else {
        Write-Host "Skipping GitHub release creation because -SkipRelease was supplied."
    }

    Write-Host "`nRelease workflow complete for $tagName."
}
finally {
    Pop-Location
}

