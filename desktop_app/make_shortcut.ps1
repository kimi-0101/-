# 영업일지 앱 바로가기를 바탕화면에 만든다. 실행:  powershell -ExecutionPolicy Bypass -File .\make_shortcut.ps1
# 더블클릭하면 검은 창 없이 앱 창이 바로 열린다 (pythonw 로 실행). 아이콘은 같은 폴더의 wj_app.ico.
$ErrorActionPreference = 'Stop'
$Here = $PSScriptRoot
$Script = Join-Path $Here 'wj_app.py'
$Icon = Join-Path $Here 'wj_app.ico'
if (-not (Test-Path $Script)) { throw "wj_app.py 를 찾지 못했습니다: $Script" }

# 검은 창이 없는 파이썬(pythonw.exe) 위치 찾기
$pyw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if (-not $pyw) {
    $py = (Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    if ($py) { $cand = Join-Path (Split-Path $py) 'pythonw.exe'; if (Test-Path $cand) { $pyw = $cand } }
}
if (-not $pyw) { throw 'pythonw.exe 를 찾지 못했습니다. 파이썬이 설치되어 있는지(PATH 포함) 확인해 주세요.' }

# 아이콘이 없으면 만들어 본다 (Pillow 필요). 실패해도 바로가기는 만든다.
if (-not (Test-Path $Icon)) {
    try { & python (Join-Path $Here 'make_icon.py') | Out-Null } catch { Write-Host '[알림] 아이콘 만들기 실패 - 기본 아이콘으로 만듭니다.' }
}

$Desktop = [Environment]::GetFolderPath('Desktop')
$Lnk = Join-Path $Desktop ([string]::Concat([char]0xC601, [char]0xC5C5, [char]0xC77C, [char]0xC9C0, '.lnk'))   # 영업일지.lnk
$sh = New-Object -ComObject WScript.Shell
$s = $sh.CreateShortcut($Lnk)
$s.TargetPath = $pyw
$s.Arguments = '"' + $Script + '"'
$s.WorkingDirectory = $Here
$s.Description = 'Weekly Journal App'
if (Test-Path $Icon) { $s.IconLocation = $Icon + ',0' }
$s.Save()
Write-Host "바탕화면에 바로가기를 만들었습니다: $Lnk"
