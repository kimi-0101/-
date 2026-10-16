# 윈도우에서 설치 없이 실행되는 파일(WJApp.exe) 만들기
#   사용:  PowerShell 에서 이 폴더로 이동한 뒤  .\build_exe.ps1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt pyinstaller
# --windowed: 검은 콘솔창 없이 실행. 처음 시험할 때는 --windowed 를 빼고 만들면 오류 메시지가 보입니다.
pyinstaller --noconfirm --onefile --windowed --name WJApp wj_app.py
# 서버 주소 파일이 이 폴더에 있으면 앱 데이터 폴더로 복사 (exe 를 어디에 두든 찾도록)
$data = Join-Path $env:LOCALAPPDATA 'WJApp'
New-Item -ItemType Directory -Force -Path $data | Out-Null
if (Test-Path .\api_url.txt) { Copy-Item .\api_url.txt (Join-Path $data 'api_url.txt') -Force }
# exe 를 고정 위치로 복사하고 바탕화면 + 시작 메뉴에 아이콘(바로가기) 만들기
$exe = Join-Path $data 'WJApp.exe'
Copy-Item .\dist\WJApp.exe $exe -Force
$sh = New-Object -ComObject WScript.Shell
foreach ($dir in @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'))) {
  $lnk = $sh.CreateShortcut((Join-Path $dir '주간영업일지.lnk'))
  $lnk.TargetPath = $exe; $lnk.WorkingDirectory = $data; $lnk.IconLocation = "$exe,0"; $lnk.Save()
}
Write-Host "완료: 바탕화면과 시작 메뉴에 '주간영업일지' 아이콘이 생겼습니다. (실행 파일: $exe)"
if (-not (Test-Path (Join-Path $data 'api_url.txt'))) { Write-Host "서버 주소가 아직 없습니다: $data\api_url.txt 파일에 주소를 한 줄로 넣으세요." }
