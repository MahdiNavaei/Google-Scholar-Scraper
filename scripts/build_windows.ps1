param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Version = "2.0.0"
$AppDirName = "Google-Scholar-Scraper-v$Version"
$PortableName = "Google-Scholar-Scraper-v$Version-Portable-Windows-x64.zip"
$InstallerName = "Google-Scholar-Scraper-v$Version-Setup-Windows-x64.exe"
$BuildDir = Join-Path $ProjectRoot "build"
$DistDir = Join-Path $ProjectRoot "dist"
$ReleaseDir = Join-Path $DistDir "release"
$PortablePath = Join-Path $ReleaseDir $PortableName
$ChecksumPath = Join-Path $ReleaseDir "SHA256SUMS.txt"
$SpecPath = Join-Path $ProjectRoot "packaging\pyinstaller\GoogleScholarScraper.spec"
$InstallerScript = Join-Path $ProjectRoot "installer\GoogleScholarScraper.iss"

function Remove-GeneratedPath {
    param([Parameter(Mandatory=$true)][string]$Path)
    $root = [System.IO.Path]::GetFullPath($ProjectRoot)
    $target = [System.IO.Path]::GetFullPath($Path)
    if (-not $target.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove path outside repository: $target"
    }
    if ((Split-Path -Leaf $target) -notin @("build", "dist")) {
        throw "Refusing to remove unexpected generated path: $target"
    }
    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}

function Get-InnoCompiler {
    $fromPath = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($fromPath) {
        return $fromPath.Source
    }

    $candidates = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return $null
}

function Get-Sha256 {
    param([Parameter(Mandatory=$true)][string]$Path)
    $stream = [System.IO.File]::OpenRead($Path)
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            $hash = $sha.ComputeHash($stream)
            return -join ($hash | ForEach-Object { $_.ToString("x2") })
        } finally {
            $sha.Dispose()
        }
    } finally {
        $stream.Dispose()
    }
}

Set-Location $ProjectRoot
Remove-GeneratedPath $BuildDir
Remove-GeneratedPath $DistDir
New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null

python -m PyInstaller $SpecPath --noconfirm --clean

$ExePath = Join-Path $DistDir "$AppDirName\GoogleScholarScraper.exe"
if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Expected executable was not created: $ExePath"
}

Compress-Archive -Path (Join-Path $DistDir $AppDirName) -DestinationPath $PortablePath -Force
if (-not (Test-Path -LiteralPath $PortablePath)) {
    throw "Expected portable archive was not created: $PortablePath"
}

$checksums = @()
$portableHash = Get-Sha256 $PortablePath
$checksums += "$portableHash  $PortableName"

$InnoCompiler = Get-InnoCompiler
if ($InnoCompiler -and -not $SkipInstaller) {
    & $InnoCompiler $InstallerScript
    $InstallerPath = Join-Path $DistDir "installer\$InstallerName"
    if (-not (Test-Path -LiteralPath $InstallerPath)) {
        throw "Expected installer was not created: $InstallerPath"
    }
    $installerHash = Get-Sha256 $InstallerPath
    $checksums += "$installerHash  installer/$InstallerName"
} else {
    Write-Host "Inno Setup compiler not found or installer build skipped; installer definition was not compiled."
}

$checksums | Set-Content -LiteralPath $ChecksumPath -Encoding ASCII
Write-Host "Portable archive: $PortablePath"
Write-Host "Checksums: $ChecksumPath"
