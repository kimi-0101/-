# 영업일지 PC 서버를 PC 에 로그인할 때 자동으로 켜고, 매일 새벽 DB 백업을 하도록 작업 스케줄러에 등록한다.
# 실행:  powershell -ExecutionPolicy Bypass -File .\register_server_task.ps1                      (이 PC 안에서만 접속)
#        powershell -ExecutionPolicy Bypass -File .\register_server_task.ps1 -BindHost 0.0.0.0     (같은 네트워크의 다른 PC 도 접속)
param(
    [string]$BindHost = '127.0.0.1',
    [int]$Port = 8787,
    [string]$BackupTime = '03:00',
    [int]$Keep = 30
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $PSScriptRoot 'wj_server.py'))) { throw 'wj_server.py 를 찾지 못했습니다.' }
$py = (Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if (-not $py) { throw 'python.exe 를 찾지 못했습니다. 파이썬이 설치되어 있는지(PATH 포함) 확인해 주세요.' }
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 0) -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)

$cmd = '/c cd /d "' + $Root + '" && "' + $py + '" -X utf8 pc_server\wj_server.py --host ' + $BindHost + ' --port ' + $Port + ' >> wj_server_log.txt 2>&1'
Register-ScheduledTask -TaskName 'WJ_Server' -Action (New-ScheduledTaskAction -Execute 'cmd.exe' -Argument $cmd -WorkingDirectory $Root) `
    -Trigger (New-ScheduledTaskTrigger -AtLogOn) -Settings $settings -Description 'Weekly journal PC server' -Force | Out-Null

$bk = '/c cd /d "' + $Root + '" && "' + $py + '" -X utf8 pc_server\wj_admin.py backup --keep ' + $Keep + ' >> wj_server_log.txt 2>&1'
Register-ScheduledTask -TaskName 'WJ_ServerBackup' -Action (New-ScheduledTaskAction -Execute 'cmd.exe' -Argument $bk -WorkingDirectory $Root) `
    -Trigger (New-ScheduledTaskTrigger -Daily -At $BackupTime) -Settings $settings -Description 'Weekly journal DB backup' -Force | Out-Null

Write-Host "등록했습니다: 로그인 시 서버 시작(WJ_Server, ${BindHost}:${Port}), 매일 $BackupTime DB 백업(WJ_ServerBackup, ${Keep}일 보관)"
Write-Host "지금 켜 보기:  Start-ScheduledTask -TaskName WJ_Server   → 브라우저에서 http://localhost:${Port}/  (로그 $Root\wj_server_log.txt)"
Write-Host "해제:  Unregister-ScheduledTask -TaskName WJ_Server -Confirm:`$false; Unregister-ScheduledTask -TaskName WJ_ServerBackup -Confirm:`$false"
