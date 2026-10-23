# 윈도우에서 설치 없이 실행되는 파일(WJApp.exe) 만들기
#   사용:  PowerShell 에서 이 폴더로 이동한 뒤  .\build_exe.ps1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt pyinstaller
# --windowed: 검은 콘솔창 없이 실행. 처음 시험할 때는 --windowed 를 빼고 만들면 오류 메시지가 보입니다.
pyinstaller --noconfirm --onefile --windowed --name WJApp wj_app.py
Write-Host "완료: dist\WJApp.exe  (같은 폴더에 api_url.txt 를 두거나 %LOCALAPPDATA%\WJApp\api_url.txt 에 서버 주소를 넣으세요)"
