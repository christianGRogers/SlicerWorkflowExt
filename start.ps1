param(
    [switch]$RunSlicer,
    [switch]$RunInVesalius,
    [switch]$MonitorLocks = $true
)
$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Definition

$dctffrguiPath = Join-Path $scriptDirectory "DCTFFRGUI.exe"
$lockFile = Join-Path $scriptDirectory "dai_lock.txt"
$slicerLockFile = Join-Path $scriptDirectory "dai_slicer_lock.txt"
$invesaliusLockFile = Join-Path $scriptDirectory "dai_invesalius_lock.txt"

Write-Host "Cleaning up existing lock and trigger files..." -ForegroundColor Cyan
$filesToClean = @(
    $lockFile,
    $slicerLockFile,
    $invesaliusLockFile,
    (Join-Path $scriptDirectory "trigger_slicer.txt"),
    (Join-Path $scriptDirectory "trigger_invesalius.txt"),
    (Join-Path $scriptDirectory "trigger_external.txt"),
    (Join-Path $scriptDirectory "slicer_exit_lock.txt")
)

foreach ($file in $filesToClean) {
    if (Test-Path $file) {
        Remove-Item $file -Force -ErrorAction SilentlyContinue
        Write-Host "  Removed: $(Split-Path $file -Leaf)" -ForegroundColor Gray
    }
}
Write-Host "Cleanup completed." -ForegroundColor Green

function Monitor-LockFiles {
    param(
        [string]$LockFilePath,
        [string]$SlicerLockFilePath,
        [string]$InVesaliusLockFilePath
    )
    
    Write-Host "Monitoring lock files:" -ForegroundColor Cyan
    Write-Host "  Main lock: $LockFilePath" -ForegroundColor Gray
    Write-Host "  Slicer lock: $SlicerLockFilePath" -ForegroundColor Gray
    Write-Host "  InVesalius lock: $InVesaliusLockFilePath" -ForegroundColor Gray
    
    while ($true) {
        if (Test-Path $SlicerLockFilePath) {
            Write-Host "Slicer execution requested..." -ForegroundColor Yellow
            Execute-Slicer
            Remove-Item $SlicerLockFilePath -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path $InVesaliusLockFilePath) {
            Write-Host "InVesalius execution requested..." -ForegroundColor Yellow
            $lockContent = Get-Content $InVesaliusLockFilePath -ErrorAction SilentlyContinue
            if ($lockContent -and $lockContent.Count -ge 5) {
                $pre = $lockContent[0]
                $post = $lockContent[1]
                $top = $lockContent[2]
                $bottom = $lockContent[3]
                $folderPath = $lockContent[4]
                
                Write-Host "InVesalius Arguments received:" -ForegroundColor Green
                Write-Host "Pre: $pre" -ForegroundColor Gray
                Write-Host "Post: $post" -ForegroundColor Gray
                Write-Host "Top: $top" -ForegroundColor Gray
                Write-Host "Bottom: $bottom" -ForegroundColor Gray
                Write-Host "Folder: $folderPath" -ForegroundColor Gray
                
                Execute-InVesalius -Pre $pre -Post $post -Top $top -Bottom $bottom -FolderPath $folderPath
            }
            Remove-Item $InVesaliusLockFilePath -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path $LockFilePath) {
            $lockContent = Get-Content $LockFilePath -ErrorAction SilentlyContinue
            if ($lockContent -and $lockContent.Count -gt 0) {
                Write-Host "Legacy lock released - processing external program triggers..." -ForegroundColor Yellow
                $args = $lockContent
                if ($args.Count -ge 5) {
                    $pre = $args[0]
                    $post = $args[1]
                    $top = $args[2]
                    $bottom = $args[3]
                    $folderPath = $args[4]
                    
                    Write-Host "Legacy Arguments received:" -ForegroundColor Green
                    Write-Host "Pre: $pre" -ForegroundColor Gray
                    Write-Host "Post: $post" -ForegroundColor Gray
                    Write-Host "Top: $top" -ForegroundColor Gray
                    Write-Host "Bottom: $bottom" -ForegroundColor Gray
                    Write-Host "Folder: $folderPath" -ForegroundColor Gray
                    Execute-InVesalius -Pre $pre -Post $post -Top $top -Bottom $bottom -FolderPath $folderPath
                }
                Remove-Item $LockFilePath -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Milliseconds 500
    }
}
# Commented out original Execute-Slicer function
<#
function Execute-Slicer {
    try {
        Write-Host "Launching Slicer..." -ForegroundColor Green

        $userHome = $env:USERPROFILE
        $slicerShortcut = Join-Path $userHome "AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Slicer 5.8.1\Slicer 5.8.1.lnk"
        
        if (Test-Path $slicerShortcut) {
            Write-Host "Starting Slicer from shortcut: $slicerShortcut" -ForegroundColor Green
            Start-Process -FilePath $slicerShortcut -Wait
            Write-Host "Slicer execution completed." -ForegroundColor Green
        } else {
            $slicerPath = "C:\Program Files\Slicer 5.8.1\Slicer.exe"
            if (Test-Path $slicerPath) {
                Write-Host "Starting Slicer from executable: $slicerPath" -ForegroundColor Green
                Start-Process -FilePath $slicerPath -Wait
                Write-Host "Slicer execution completed." -ForegroundColor Green
            } else {
                Write-Host "Slicer not found at expected locations" -ForegroundColor Red
                Write-Host "Shortcut checked: $slicerShortcut" -ForegroundColor Red
                Write-Host "Executable checked: $slicerPath" -ForegroundColor Red
            }
        }
    }
    catch {
        Write-Host "Error executing Slicer: $($_.Exception.Message)" -ForegroundColor Red
    }
}
#>

# New Execute-Slicer function using specified location
function Execute-Slicer {
    try {
        Write-Host "Launching Slicer..." -ForegroundColor Green

        $slicerPath = "D:\slicer.org\Slicer 5.8.1\Slicer.exe"
        $slicerExitLockFile = Join-Path $scriptDirectory "slicer_exit_lock.txt"
        
        if (Test-Path $slicerPath) {
            Write-Host "Starting Slicer from executable: $slicerPath --no-splash" -ForegroundColor Green
            
            # Start Slicer and wait for it to complete
            $slicerProcess = Start-Process -FilePath $slicerPath -ArgumentList "--no-splash" -PassThru
            $slicerProcess.WaitForExit()
            
            # Get exit information
            $exitCode = $slicerProcess.ExitCode
            $exitTime = Get-Date
            
            Write-Host "Slicer execution completed." -ForegroundColor Green
            Write-Host "  Exit Code: $exitCode" -ForegroundColor Gray
            Write-Host "  Exit Time: $($exitTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Gray
            
            # Create lock file to notify listeners that Slicer has exited
            $lockContent = @(
                "SLICER_EXITED",
                $exitCode,
                $exitTime.ToString('yyyy-MM-dd HH:mm:ss'),
                $slicerProcess.Id
            )
            $lockContent | Out-File -FilePath $slicerExitLockFile -Encoding UTF8
            Write-Host "Created exit notification lock file: $slicerExitLockFile" -ForegroundColor Cyan
            
        } else {
            Write-Host "Slicer not found at: $slicerPath" -ForegroundColor Red
            Write-Host "Please verify that Slicer is installed at the specified location." -ForegroundColor Yellow
            
            # Create lock file indicating Slicer was not found
            $lockContent = @(
                "SLICER_NOT_FOUND",
                -1,
                (Get-Date).ToString('yyyy-MM-dd HH:mm:ss'),
                0
            )
            $lockContent | Out-File -FilePath $slicerExitLockFile -Encoding UTF8
        }
    }
    catch {
        Write-Host "Error executing Slicer: $($_.Exception.Message)" -ForegroundColor Red
        
        # Create lock file indicating an error occurred
        $lockContent = @(
            "SLICER_ERROR",
            -1,
            (Get-Date).ToString('yyyy-MM-dd HH:mm:ss'),
            0,
            $_.Exception.Message
        )
        $lockContent | Out-File -FilePath $slicerExitLockFile -Encoding UTF8
    }
}

function Execute-InVesalius {
    param(
        [string]$Pre,
        [string]$Post,
        [string]$Top,
        [string]$Bottom,
        [string]$FolderPath
    )
    
    try {
        Write-Host "Launching InVesalius..." -ForegroundColor Green
        $invesaliusPath = "C:\Program Files (x86)\InVesalius 3.1\dist\InVesalius 3.1.exe"
        
        if (Test-Path $invesaliusPath) {
            $invesaliusArgs = @(
                '--raycast-mode', '"Mid contrast"',
                '--pre', $Pre,
                '--post', $Post,
                '--top', $Top,
                '--bottom', $Bottom,
                '-i', "`"$FolderPath`""
            )
            
            Write-Host "Starting InVesalius with arguments:" -ForegroundColor Green
            Write-Host "  Path: $invesaliusPath" -ForegroundColor Gray
            Write-Host "  Args: $($invesaliusArgs -join ' ')" -ForegroundColor Gray
            
            Start-Process -FilePath $invesaliusPath -ArgumentList $invesaliusArgs -Wait
            Write-Host "InVesalius execution completed." -ForegroundColor Green
        } else {
            Write-Host "InVesalius not found at: $invesaliusPath" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "Error executing InVesalius: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Write-ArgsToLockFile {
    param(
        [string]$LockFilePath,
        [string]$Pre,
        [string]$Post,
        [string]$Top,
        [string]$Bottom,
        [string]$FolderPath
    )
    
    $args = @($Pre, $Post, $Top, $Bottom, $FolderPath)
    $args | Out-File -FilePath $LockFilePath -Encoding UTF8
}

function Request-SlicerExecution {
    param(
        [string]$SlicerLockFilePath
    )

    "" | Out-File -FilePath $SlicerLockFilePath -Encoding UTF8
    Write-Host "Slicer execution requested via lock file: $SlicerLockFilePath" -ForegroundColor Yellow
}

function Request-InVesaliusExecution {
    param(
        [string]$InVesaliusLockFilePath,
        [string]$Pre,
        [string]$Post,
        [string]$Top,
        [string]$Bottom,
        [string]$FolderPath
    )
    
    $args = @($Pre, $Post, $Top, $Bottom, $FolderPath)
    $args | Out-File -FilePath $InVesaliusLockFilePath -Encoding UTF8
    Write-Host "InVesalius execution requested via lock file: $InVesaliusLockFilePath" -ForegroundColor Yellow
}

if ($RunSlicer -or $RunInVesalius) {
    Write-Host "Running in direct execution mode..." -ForegroundColor Cyan
    if ($RunSlicer) {
        Execute-Slicer
    }
    if ($RunInVesalius) {
        Execute-InVesalius -Pre "" -Post "" -Top "" -Bottom "" -FolderPath ""
    }
    exit 0
}
if (Test-Path $dctffrguiPath) {
    Write-Host "Starting DCTFFRGUI.exe..." -ForegroundColor Green

    $dctProcess = Start-Process -FilePath $dctffrguiPath -PassThru
    
    if ($MonitorLocks) {
        $lockMonitorJob = Start-Job -ScriptBlock {
            param($LockFilePath, $SlicerLockFilePath, $InVesaliusLockFilePath, $ScriptPath)
            
            function Monitor-LockFiles {
                param(
                    [string]$LockFilePath,
                    [string]$SlicerLockFilePath,
                    [string]$InVesaliusLockFilePath
                )
                
                while ($true) {
                    if (Test-Path $SlicerLockFilePath) {
                        Write-Host "Slicer execution requested..." -ForegroundColor Yellow
                        $triggerFile = Join-Path (Split-Path $LockFilePath) "trigger_slicer.txt"
                        "" | Out-File -FilePath $triggerFile -Encoding UTF8
                        Remove-Item $SlicerLockFilePath -Force -ErrorAction SilentlyContinue
                    }
                    
                    if (Test-Path $InVesaliusLockFilePath) {
                        Write-Host "InVesalius execution requested..." -ForegroundColor Yellow
                        $lockContent = Get-Content $InVesaliusLockFilePath -ErrorAction SilentlyContinue
                        if ($lockContent -and $lockContent.Count -ge 5) {
                            $triggerFile = Join-Path (Split-Path $LockFilePath) "trigger_invesalius.txt"
                            $lockContent | Out-File -FilePath $triggerFile -Encoding UTF8
                        }
                        Remove-Item $InVesaliusLockFilePath -Force -ErrorAction SilentlyContinue
                    }
                    
                    if (Test-Path $LockFilePath) {
                        $lockContent = Get-Content $LockFilePath -ErrorAction SilentlyContinue
                        if ($lockContent -and $lockContent.Count -gt 0) {
                            Write-Host "Legacy lock released - triggering external programs..." -ForegroundColor Yellow
                            $triggerFile = Join-Path (Split-Path $LockFilePath) "trigger_external.txt"
                            $lockContent | Out-File -FilePath $triggerFile -Encoding UTF8
                            Remove-Item $LockFilePath -Force -ErrorAction SilentlyContinue
                        }
                    }
                    
                    Start-Sleep -Milliseconds 500
                }
            }
            
            Monitor-LockFiles -LockFilePath $LockFilePath -SlicerLockFilePath $SlicerLockFilePath -InVesaliusLockFilePath $InVesaliusLockFilePath
        } -ArgumentList $lockFile, $slicerLockFile, $invesaliusLockFile, $PSCommandPath
        
        Write-Host "Lock monitoring started in background..." -ForegroundColor Cyan
        
        $triggerSlicerFile = Join-Path $scriptDirectory "trigger_slicer.txt"
        $triggerInVesaliusFile = Join-Path $scriptDirectory "trigger_invesalius.txt"
        $triggerExternalFile = Join-Path $scriptDirectory "trigger_external.txt"
        
        while (-not $dctProcess.HasExited) {
            if (Test-Path $triggerSlicerFile) {
                Write-Host "Slicer trigger detected!" -ForegroundColor Yellow
                Execute-Slicer
                Remove-Item $triggerSlicerFile -Force -ErrorAction SilentlyContinue
            }
            
            if (Test-Path $triggerInVesaliusFile) {
                Write-Host "InVesalius trigger detected!" -ForegroundColor Yellow
                $triggerContent = Get-Content $triggerInVesaliusFile -ErrorAction SilentlyContinue
                if ($triggerContent -and $triggerContent.Count -ge 5) {
                    Execute-InVesalius -Pre $triggerContent[0] -Post $triggerContent[1] -Top $triggerContent[2] -Bottom $triggerContent[3] -FolderPath $triggerContent[4]
                }
                Remove-Item $triggerInVesaliusFile -Force -ErrorAction SilentlyContinue
            }
            
            if (Test-Path $triggerExternalFile) {
                Write-Host "Legacy external program trigger detected!" -ForegroundColor Yellow
                $triggerContent = Get-Content $triggerExternalFile -ErrorAction SilentlyContinue
                if ($triggerContent -and $triggerContent.Count -ge 5) {
                    Execute-InVesalius -Pre $triggerContent[0] -Post $triggerContent[1] -Top $triggerContent[2] -Bottom $triggerContent[3] -FolderPath $triggerContent[4]
                }
                Remove-Item $triggerExternalFile -Force -ErrorAction SilentlyContinue
            }
            
            Start-Sleep -Milliseconds 1000
        }
        
        Stop-Job $lockMonitorJob -ErrorAction SilentlyContinue
        Remove-Job $lockMonitorJob -ErrorAction SilentlyContinue
    } else {
        $dctProcess.WaitForExit()
    }
    
    Write-Host "DCTFFRGUI.exe has finished execution." -ForegroundColor Green
} else {
    Write-Host "DCTFFRGUI.exe not found in the script directory: $scriptDirectory" -ForegroundColor Red
    Write-Host "Please ensure DCTFFRGUI.exe is in the same directory as this script." -ForegroundColor Yellow
    exit 1
}