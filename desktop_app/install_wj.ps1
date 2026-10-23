# 영업일지 앱을 이 PC에 한 번에 설치한다 (파이썬 확인 → 앱 복사 → 전용 환경 만들기 → 서버 주소 저장 → 바탕화면 아이콘).
# 실행:  powershell -ExecutionPolicy Bypass -File .\install_wj.ps1
#        powershell -ExecutionPolicy Bypass -File .\install_wj.ps1 -ApiUrl "https://.../exec" -Startup
#   -ApiUrl  서버 주소 (없으면 api_url.txt 를 이 폴더에서 찾고, 그것도 없으면 물어봄)
#   -Startup 윈도우에 로그인하면 앱이 자동으로 켜지게 한다 (매일 쓰는 담당자용, 화면이 미리 받아져서 더 빠르게 열림)
#   -Uninstall 바탕화면·시작 프로그램 아이콘을 지운다 (저장본·로그인 정보는 %LOCALAPPDATA%\WJApp 에 남김. --reset 으로 지움)
# 설치 위치: %LOCALAPPDATA%\WJApp  (관리자 권한 필요 없음). 다시 실행하면 앱만 새 버전으로 바뀌고 서버 주소·저장본은 그대로.
param(
    [string]$ApiUrl = '',
    [switch]$Startup,
    [switch]$Uninstall
)
$ErrorActionPreference = 'Stop'
$Src = $PSScriptRoot
$App = Join-Path $env:LOCALAPPDATA 'WJApp'
$Dir = Join-Path $App 'app'
$Venv = Join-Path $App 'venv'
$Name = [string]::Concat([char]0xC601, [char]0xC5C5, [char]0xC77C, [char]0xC9C0, '.lnk')   # 영업일지.lnk
$DeskLnk = Join-Path ([Environment]::GetFolderPath('Desktop')) $Name
$StartLnk = Join-Path ([Environment]::GetFolderPath('Startup')) $Name

if ($Uninstall) {
    foreach ($p in @($DeskLnk, $StartLnk)) { if (Test-Path $p) { Remove-Item $p -Force; Write-Host "지움: $p" } }
    Write-Host "완료. 앱 파일과 저장본은 $App 에 남겨 두었습니다. 완전히 지우려면 그 폴더를 삭제하세요."
    return
}

# 1) 파이썬 3 찾기 (윈도우 스토어 안내용 가짜 python.exe 는 걸러냄)
function Test-Py($exe, $extra) {
    try { $v = & $exe @extra -c "import sys;print(sys.version_info[0])" 2>$null; return ("$v".Trim() -eq '3') } catch { return $false }
}
$py = $null; $pyArgs = @()
$cmd = Get-Command py.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if ($cmd -and (Test-Py $cmd.Source @('-3'))) { $py = $cmd.Source; $pyArgs = @('-3') }
if (-not $py) {
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd -and (Test-Py $cmd.Source @())) { $py = $cmd.Source }
}
if (-not $py) { throw '파이썬 3 을 찾지 못했습니다. https://www.python.org/downloads/ 에서 설치하면서 "Add python.exe to PATH" 를 체크한 뒤 다시 실행하세요. (파이썬 없이 쓰려면 관리자에게 WJApp.exe 를 받으세요)' }
Write-Host "파이썬: $py"

# 2) 앱 파일 복사
New-Item -ItemType Directory -Force -Path $Dir | Out-Null
foreach ($f in @('wj_app.py', 'wj_app.ico', 'requirements.txt')) {
    $from = Join-Path $Src $f
    if (Test-Path $from) { Copy-Item $from (Join-Path $Dir $f) -Force } elseif ($f -eq 'wj_app.py') { throw "wj_app.py 를 찾지 못했습니다: $from" }
}

# 3) 이 앱 전용 파이썬 환경 (다른 프로그램과 섞이지 않음) + 필요한 부품 설치
$venvPy = Join-Path $Venv 'Scripts\python.exe'
if (-not (Test-Path $venvPy)) { & $py @pyArgs -m venv $Venv; if ($LASTEXITCODE -ne 0) { throw '전용 환경을 만들지 못했습니다.' } }
& $venvPy -m pip install --disable-pip-version-check -q -r (Join-Path $Dir 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw '부품(pywebview) 설치에 실패했습니다. 인터넷 연결을 확인하세요.' }

# 4) 서버 주소 저장 (BOM 없는 UTF-8 — 앱이 이 파일을 그대로 읽는다)
$urlFile = Join-Path $App 'api_url.txt'
$srcUrl = Join-Path $Src 'api_url.txt'
if ($ApiUrl) { $url = $ApiUrl.Trim() }
elseif (Test-Path $urlFile) { $url = $null }
elseif (Test-Path $srcUrl) { $url = (Get-Content $srcUrl -Raw).Trim() }
else { $url = (Read-Host '서버 주소를 붙여 넣으세요 (관리자에게 받은 주소)').Trim() }
if ($url) { [System.IO.File]::WriteAllText($urlFile, $url, (New-Object System.Text.UTF8Encoding($false))) }
if (-not (Test-Path $urlFile)) { throw '서버 주소가 없습니다. -ApiUrl 로 주소를 주세요.' }

# 5) 바탕화면(과 선택 시 시작 프로그램) 아이콘
function New-WJLink($path) {
    # 바로가기 파일명이 한글이면 WScript.Shell 의 Save() 가 로케일에 따라 실패한다(영어 윈도우 등: FileNotFoundException).
    # 그래서 ASCII 임시 이름으로 저장한 뒤 .NET(Move-Item)으로 한글 이름으로 바꾼다. 바꾸지 못하면 임시(영어) 이름을 그대로 쓴다.
    $parent = Split-Path $path -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }   # 바탕화면/시작 프로그램 폴더가 없는 PC 에서도 되도록
    $target = Join-Path $Venv 'Scripts\pythonw.exe'
    if (-not (Test-Path $target)) { throw "venv 의 pythonw.exe 가 없습니다: $target" }
    $tmp = Join-Path $parent 'Weekly Journal.lnk'
    $sh = New-Object -ComObject WScript.Shell
    $s = $sh.CreateShortcut($tmp)
    $s.TargetPath = $target
    $s.Arguments = '"' + (Join-Path $Dir 'wj_app.py') + '"'
    $s.WorkingDirectory = $Dir
    $s.Description = 'Weekly Journal App'
    $ico = Join-Path $Dir 'wj_app.ico'
    if (Test-Path $ico) { $s.IconLocation = $ico + ',0' }
    $s.Save()
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
    try { Move-Item -LiteralPath $tmp -Destination $path -Force; return $path }
    catch { Write-Host "[알림] 한글 이름으로 바꾸지 못해 영어 이름으로 둡니다: $tmp"; return $tmp }
}
$made = New-WJLink $DeskLnk
Write-Host "바탕화면 아이콘: $made"
if ($Startup) { $made2 = New-WJLink $StartLnk; Write-Host "로그인 시 자동 실행: $made2" }
Write-Host ''
Write-Host '설치 완료. 바탕화면의 아이콘을 더블클릭하세요. (처음 한 번은 로그인이 필요하고, 로그인 화면의 "이 PC 에서 자동 로그인"을 켜면 다음부터 입력 없이 열립니다)'
