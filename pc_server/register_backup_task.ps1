# 영업일지 백업을 매주 화요일 오전에 자동 실행하도록 작업 스케줄러에 등록한다.
# 실행:  powershell -ExecutionPolicy Bypass -File .\register_backup_task.ps1            (기본: 화요일 09:00)
#        powershell -ExecutionPolicy Bypass -File .\register_backup_task.ps1 -Time 10:30 -Day Tuesday
#        powershell -ExecutionPolicy Bypass -File .\register_backup_task.ps1 -Daily -Time 02:00 -Keep 60      (매일, 60일 보관)
# 그 시각에 PC 가 꺼져 있었으면 켜진 뒤 바로 따라잡아 실행한다(StartWhenAvailable). 로그인된 상태에서 돈다.
param(
    [string]$Time = '09:00',
    [string]$Day = 'Tuesday',
    [int]$Keep = 90,
    [string]$Name = 'WJ_Backup',
    [switch]$Daily                      # 매일 실행 (기본은 매주 -Day)
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$Script = Join-Path $PSScriptRoot 'backup_journal.py'
if (-not (Test-Path $Script)) { throw "backup_journal.py 를 찾지 못했습니다: $Script" }
$py = (Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if (-not $py) { throw 'python.exe 를 찾지 못했습니다. 파이썬이 설치되어 있는지(PATH 포함) 확인해 주세요.' }

$cmd = '/c cd /d "' + $Root + '" && "' + $py + '" pc_server\backup_journal.py --keep ' + $Keep + ' >> wj_backup_log.txt 2>&1'
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument $cmd -WorkingDirectory $Root
if ($Daily) { $trigger = New-ScheduledTaskTrigger -Daily -At $Time } else { $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Day -At $Time }
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Description 'Weekly journal backup (sheet to PC)' -Force | Out-Null
if ($Daily) { $when = "매일 $Time" } else { $when = "매주 $Day $Time" }
Write-Host "등록했습니다: $when (작업 이름 $Name, 보관 ${Keep}일)"
Write-Host "지금 한 번 돌려 보기:  Start-ScheduledTask -TaskName $Name   → 잠시 뒤 $Root\wj_backup_log.txt 마지막 줄 확인"
Write-Host "해제:  Unregister-ScheduledTask -TaskName $Name -Confirm:`$false"
