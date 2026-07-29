Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepositoryRoot {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)]
    [string]$StartPath
  )

  $start = [System.IO.Path]::GetFullPath($StartPath)
  $rootOutput = @(& git -C $start rev-parse --show-toplevel 2>$null)
  if ($LASTEXITCODE -ne 0 -or $rootOutput.Count -eq 0) {
    throw "Unable to resolve a Git repository from: $start"
  }

  return [System.IO.Path]::GetFullPath([string]$rootOutput[0])
}

function Get-PathComparison {
  if ($IsWindows) {
    return [System.StringComparison]::OrdinalIgnoreCase
  }
  return [System.StringComparison]::Ordinal
}

function Assert-NoReparsePoint {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryRoot,

    [Parameter(Mandatory = $true)]
    [string]$Path
  )

  $root = [System.IO.Path]::GetFullPath($RepositoryRoot)
  $current = [System.IO.Path]::GetFullPath($Path)
  $comparison = Get-PathComparison

  while ($true) {
    if (Test-Path -LiteralPath $current) {
      $item = Get-Item -LiteralPath $current -Force
      if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Symbolic links and reparse points are not valid rewrite targets: $current"
      }
    }

    if ($current.Equals($root, $comparison)) {
      break
    }

    $parent = [System.IO.Directory]::GetParent($current)
    if ($null -eq $parent) {
      throw "Unable to prove repository containment for: $Path"
    }
    $current = $parent.FullName
  }
}

function Resolve-RepositoryPath {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryRoot,

    [Parameter(Mandatory = $true)]
    [string]$Path,

    [switch]$MustExist
  )

  $root = [System.IO.Path]::GetFullPath($RepositoryRoot).TrimEnd(
    [System.IO.Path]::DirectorySeparatorChar,
    [System.IO.Path]::AltDirectorySeparatorChar
  )
  if ([System.IO.Path]::IsPathRooted($Path)) {
    $candidate = [System.IO.Path]::GetFullPath($Path)
  } else {
    $candidate = [System.IO.Path]::GetFullPath(
      (Join-Path -Path $root -ChildPath $Path)
    )
  }

  $comparison = Get-PathComparison
  $rootPrefix = $root + [System.IO.Path]::DirectorySeparatorChar
  $inside = $candidate.Equals($root, $comparison) -or
    $candidate.StartsWith($rootPrefix, $comparison)
  if (-not $inside) {
    throw "Path escapes repository boundary: $Path"
  }

  $relative = [System.IO.Path]::GetRelativePath($root, $candidate).Replace("\", "/")
  if ($relative -eq ".git" -or $relative.StartsWith(".git/", $comparison)) {
    throw "Repository metadata is not a valid rewrite target: $Path"
  }

  if ($MustExist -and -not (Test-Path -LiteralPath $candidate)) {
    throw "Path not found inside repository: $relative"
  }
  Assert-NoReparsePoint -RepositoryRoot $root -Path $candidate

  return $candidate
}

function Get-RepositoryRelativePath {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryRoot,

    [Parameter(Mandatory = $true)]
    [string]$Path
  )

  $root = [System.IO.Path]::GetFullPath($RepositoryRoot)
  $safePath = Resolve-RepositoryPath `
    -RepositoryRoot $root `
    -Path $Path `
    -MustExist
  return [System.IO.Path]::GetRelativePath($root, $safePath).Replace("\", "/")
}

function Resolve-RepositoryBackupPath {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryRoot,

    [Parameter(Mandatory = $true)]
    [string]$SourcePath,

    [Parameter(Mandatory = $true)]
    [string]$BackupSuffix
  )

  if ([string]::IsNullOrWhiteSpace($BackupSuffix)) {
    throw "Backup suffix must be a non-empty filename suffix"
  }
  if ($BackupSuffix -match '[<>:"/\\|?*\x00-\x1F]') {
    throw "Backup suffix must not contain path separators or invalid filename characters"
  }

  $root = [System.IO.Path]::GetFullPath($RepositoryRoot)
  $safeSource = Resolve-RepositoryPath `
    -RepositoryRoot $root `
    -Path $SourcePath `
    -MustExist
  if (-not (Test-Path -LiteralPath $safeSource -PathType Leaf)) {
    throw "Backup source is not a file: $SourcePath"
  }

  $sourceParent = [System.IO.Path]::GetDirectoryName($safeSource)
  $candidate = [System.IO.Path]::GetFullPath($safeSource + $BackupSuffix)
  $candidateParent = [System.IO.Path]::GetDirectoryName($candidate)
  $comparison = Get-PathComparison
  if (-not $candidateParent.Equals($sourceParent, $comparison)) {
    throw "Backup destination must remain in the source file directory"
  }

  $safeBackup = Resolve-RepositoryPath `
    -RepositoryRoot $root `
    -Path $candidate
  if (Test-Path -LiteralPath $safeBackup) {
    throw "Backup destination already exists: $safeBackup"
  }

  return $safeBackup
}

function Get-TrackedRepositoryFiles {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryRoot,

    [Parameter(Mandatory = $true)]
    [string]$Path,

    [string[]]$Extensions = @()
  )

  $root = [System.IO.Path]::GetFullPath($RepositoryRoot)
  $safePath = Resolve-RepositoryPath `
    -RepositoryRoot $root `
    -Path $Path `
    -MustExist
  $pathSpec = [System.IO.Path]::GetRelativePath($root, $safePath).Replace("\", "/")
  $tracked = @(
    & git -C $root -c core.quotepath=false ls-files -- $pathSpec 2>$null
  )
  if ($LASTEXITCODE -ne 0) {
    throw "git ls-files failed for repository path: $pathSpec"
  }

  $normalizedExtensions = @(
    $Extensions | ForEach-Object { $_.ToLowerInvariant() }
  )
  foreach ($relative in $tracked) {
    if ([string]::IsNullOrWhiteSpace($relative)) {
      continue
    }
    $fullPath = Resolve-RepositoryPath `
      -RepositoryRoot $root `
      -Path ([string]$relative) `
      -MustExist
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
      continue
    }
    $extension = [System.IO.Path]::GetExtension($fullPath).ToLowerInvariant()
    if (
      $normalizedExtensions.Count -gt 0 -and
      $extension -notin $normalizedExtensions
    ) {
      continue
    }

    [PSCustomObject]@{
      FullPath = $fullPath
      RelativePath = ([string]$relative).Replace("\", "/")
    }
  }
}

Export-ModuleMember -Function @(
  "Get-RepositoryRoot",
  "Resolve-RepositoryPath",
  "Get-RepositoryRelativePath",
  "Resolve-RepositoryBackupPath",
  "Get-TrackedRepositoryFiles"
)
