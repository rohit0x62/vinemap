# Vinemap one-line installer for Windows.
#   irm https://<your-domain>/install.ps1 | iex
$ErrorActionPreference = "Stop"

function Find-Python {
    foreach ($cmd in @("py -3", "python3", "python")) {
        try {
            $ver = Invoke-Expression "$cmd -c `"import sys; print(sys.version_info >= (3, 9))`"" 2>$null
            if ($ver -eq "True") { return $cmd }
        } catch {}
    }
    return $null
}

$py = Find-Python
if (-not $py) {
    Write-Error "Python 3.9+ not found. Install from https://python.org (check 'Add to PATH') and re-run."
}

$home_dir = if ($env:VINEMAP_HOME) { $env:VINEMAP_HOME } else { "$env:USERPROFILE\.vinemap-cli" }
Write-Host "[vinemap] installing into $home_dir"

Invoke-Expression "$py -m venv `"$home_dir\venv`""
& "$home_dir\venv\Scripts\pip.exe" install --quiet --upgrade pip
& "$home_dir\venv\Scripts\pip.exe" install --quiet vinemap

$binDir = "$env:USERPROFILE\.local\bin"
New-Item -ItemType Directory -Force -Path $binDir | Out-Null
Copy-Item "$home_dir\venv\Scripts\vinemap.exe" "$binDir\vinemap.exe" -Force

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$binDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$binDir", "User")
    Write-Host "[vinemap] added $binDir to your PATH — restart your terminal"
}

Write-Host "[vinemap] installed. Get started:"
Write-Host "    cd your-project"
Write-Host "    vinemap index .      # build the code graph"
Write-Host "    vinemap mcp .        # start the MCP server for your agent"
