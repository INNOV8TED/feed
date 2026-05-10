# setup_heartbeat.ps1
# IMPORTANT: YOU MUST RUN THIS AS ADMINISTRATOR
$VbsPath = "C:\Users\Stephen Portman\Desktop\ACTIVE_WORK\activity_feed\silent_heartbeat.vbs"

if (-not (Test-Path $VbsPath)) {
    Write-Host "ERROR: Could not find $VbsPath" -ForegroundColor Red
    exit
}

$TaskName = "StudioHeartbeatPersistence"

# Action: Run the silent VBS launcher
$Action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$VbsPath`""

# Trigger: Start when any user logs on
$Trigger = New-ScheduledTaskTrigger -AtLogOn

    # Robust Settings: Unlimited execution time, auto-restart on failure
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    
    # Register the task with highest privileges and custom settings
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -RunLevel Highest -Force
    Write-Host "SUCCESS! Heartbeat will now start automatically whenever you log in." -ForegroundColor Green
    Write-Host "Persistence Hardened: The task will now restart automatically if it fails." -ForegroundColor Cyan
} catch {
    if ($_.Exception.Message -match "Access is denied") {
        Write-Host "FAILED: Access Denied. Please right-click PowerShell and 'Run as Administrator'." -ForegroundColor Red
    } else {
        Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }
}
