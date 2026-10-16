# -*- coding: utf-8 -*-
"""앱 파일 4개를 한 개의 설치 스크립트(install_desktop_app.ps1)로 묶는다.  앱을 고칠 때마다 다시 실행:  python make_installer.py"""
import base64, os
HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ['wj_app.py', 'README.md', 'requirements.txt', 'build_exe.ps1']
BOM = b'\xef\xbb\xbf'

def payload(name):
    b = open(os.path.join(HERE, name), 'rb').read()
    if name.endswith('.ps1') and not b.startswith(BOM):
        b = BOM + b                      # 윈도우 PowerShell 5 가 한글을 깨지 않게 BOM 을 붙인다
    return base64.b64encode(b).decode('ascii')

lines = ["$ErrorActionPreference = 'Stop'", "$Target = Join-Path $env:USERPROFILE 'Desktop\\중국판매데이터RAW\\desktop_app'",
         "if ($args.Count -gt 0) { $Target = $args[0] }", "$files = @{"]
lines += [f"  '{n}' = '{payload(n)}'" for n in FILES]
lines += ["}",
          "New-Item -ItemType Directory -Force -Path $Target | Out-Null",
          "foreach ($name in $files.Keys) {",
          "  $path = Join-Path $Target $name",
          "  if (Test-Path $path) { Copy-Item $path ($path + '.bak') -Force }",
          "  [System.IO.File]::WriteAllBytes($path, [Convert]::FromBase64String($files[$name]))",
          "  Write-Host ('저장: ' + $path)",
          "}",
          "Write-Host ''",
          "Write-Host '완료. 다음 순서로 실행하세요:'",
          "Write-Host ('  cd \"' + $Target + '\"')",
          "Write-Host '  pip install -r requirements.txt'",
          "Write-Host '  python wj_app.py --browser'"]
out = os.path.join(HERE, 'install_desktop_app.ps1')
open(out, 'wb').write(BOM + ('\r\n'.join(lines) + '\r\n').encode('utf-8'))
print('만듦:', out)
