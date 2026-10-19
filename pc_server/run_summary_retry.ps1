# SUMMARY 요약·번역을 한도가 풀린 뒤 자동으로 돌리고, 끝나면 결과를 점검한다. 실패하면(한도 등) 기다렸다가 이어서 다시 한다.
# 사용(직접 실행):  powershell -ExecutionPolicy Bypass -File pc_server\run_summary_retry.ps1 -Week 41 -Codes M09 -Fresh
#   -Fresh        지정한 코드의 기존 정리본을 *.before_rerun.json 으로 백업하고 처음부터 새로 만든다(끝내 실패하면 백업을 되돌린다)
#   -Codes        M09 처럼 하나, 또는 M09,W41 처럼 여러 개
#   -MaxAttempts  최대 시도 횟수(기본 5),  -WaitMinutes  한도 오류 뒤 기다리는 분(기본 30)
# 기록: 프로젝트 폴더의 wj_summary_run_log.txt (UTF-8)
param(
    [int]$Week = 41,
    [string]$Codes = 'M09',
    [switch]$Fresh,
    [int]$MaxAttempts = 5,
    [int]$WaitMinutes = 30,
    [string]$Status = 'final'
)
$ErrorActionPreference = 'Continue'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$log = Join-Path $Root 'wj_summary_run_log.txt'
function Log([string]$m) { Add-Content -Path $log -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ' + $m) -Encoding UTF8 }
$py = (Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if (-not $py) { Log 'ERROR python.exe not found'; exit 2 }
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$codeList = @($Codes -split '[, ]+' | Where-Object { $_ })
$ents = @('HK', 'TW')
$draftDir = Join-Path $Root 'weekly_journal\summary_draft'
Log ('BEGIN week=' + $Week + ' codes=' + ($codeList -join ',') + ' fresh=' + $Fresh.IsPresent)

if ($Fresh) {
    foreach ($e in $ents) {
        foreach ($c in $codeList) {
            $f = Join-Path $draftDir ($e + '_' + $c + '.json')
            $bak = Join-Path $draftDir ($e + '_' + $c + '.before_rerun.json')
            if (Test-Path $f) {
                if (-not (Test-Path $bak)) { Copy-Item $f $bak }
                Remove-Item $f -Force
                Log ('BACKUP ' + $f + ' -> ' + $bak)
            }
        }
    }
}

$ok = $false
for ($i = 1; $i -le $MaxAttempts; $i++) {
    Log ('START attempt ' + $i + ' of ' + $MaxAttempts)
    $a1 = @('weekly_journal\pipeline.py', '--week', $Week, '--status', $Status, '--summary-only', '--summary-codes') + $codeList
    & $py @a1 2>&1 | Out-File -FilePath $log -Append -Encoding UTF8
    $rc = $LASTEXITCODE
    $crc = 0
    foreach ($c in $codeList) {
        & $py 'weekly_journal\check_summary.py' '--code' $c 2>&1 | Out-File -FilePath $log -Append -Encoding UTF8
        if ($LASTEXITCODE -ne 0) { $crc = 1 }
    }
    Log ('RESULT attempt ' + $i + ' pipeline=' + $rc + ' check=' + $crc)
    if (($rc -eq 0) -and ($crc -eq 0)) { $ok = $true; break }
    if ($i -lt $MaxAttempts) {
        $w = 3
        if ($rc -ne 0) { $w = $WaitMinutes }
        Log ('WAIT ' + $w + ' minutes then retry')
        Start-Sleep -Seconds ($w * 60)
    }
}

foreach ($e in $ents) {
    foreach ($c in $codeList) {
        $f = Join-Path $draftDir ($e + '_' + $c + '.json')
        $bak = Join-Path $draftDir ($e + '_' + $c + '.before_rerun.json')
        if ((-not (Test-Path $f)) -and (Test-Path $bak)) {
            Copy-Item $bak $f
            Log ('RESTORED old draft ' + $f)
        }
    }
}
if ($ok) { Log 'DONE all checks passed' } else { Log 'FINISHED with problems - read the log above' }
