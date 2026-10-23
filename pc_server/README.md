# PC 서버 — 구글 클라우드 없이 PC 한 대로 돌리기

- **2단계(서버): `wj_server.py`** — 구글 Apps Script·시트(Code.gs)를 대신하는 자체 서버. 같은 요청·응답 형식이라 **앱·반영 프로그램은 `api_url.txt` 주소만 바꾸면 된다.** 저장소는 SQLite 파일 하나(`wj_data/wj.sqlite3`).
- 1단계(백업): `backup_journal.py` — 시트 → PC 날짜별 백업 (아래). 서버로 옮긴 뒤에는 `wj_admin.py backup` 이 대신한다.

## 처음 켜기 (윈도우, 파이썬만 있으면 됨 — 추가 설치 없음)

```
python pc_server\wj_admin.py init                              # 기본 계정 hk / tw / hq
python pc_server\wj_admin.py set-password tw                   # 계정마다 8자 이상 비밀번호 (hk, hq 도)
python pc_server\wj_admin.py add-user kim --label "김 부장" --ent TW --dept MD --role writer   # 필요하면 계정 추가
python pc_server\wj_admin.py push-key                          # ERP 숫자 반영 키 → apps_script\weekly_journal\push_key.txt 에 붙여넣기
python pc_server\wj_admin.py import-backup wj_backup           # (선택) 1단계 백업 폴더의 글·사진을 서버로 가져오기
python pc_server\wj_server.py                                  # 서버 켜기: http://127.0.0.1:8787/
```
- 같은 사무실의 다른 PC 에서도 쓰려면 `--host 0.0.0.0` 으로 켜고, 윈도우 방화벽에서 해당 포트(기본 8787)를 허용한다. **해외(홍콩·대만) 사용자는 인터넷에 직접 열지 말고 VPN 이나 보안 터널(예: Tailscale, Cloudflare Tunnel)로 연결**한다 — 이 서버는 HTTPS 를 직접 처리하지 않는다.
- 자동 시작·자동 백업: `powershell -ExecutionPolicy Bypass -File pc_server\register_server_task.ps1 [-BindHost 0.0.0.0]` (로그인 시 서버 시작, 매일 03:00 DB 백업 30일 보관)
- 앱 연결: `desktop_app` 의 `api_url.txt`(또는 `--api-url`)를 `http://<서버 PC 주소>:8787/api` 로 바꾼다. 앱 코드는 수정하지 않는다.

## 관리 도구 `wj_admin.py`
| 명령 | 하는 일 |
|---|---|
| `init` / `add-user` / `list-users` | 계정(명단) 관리. 역할 `writer`(작성자) · `hq`(본사) · `viewer`(조회), 법인 `HK`/`TW`/`ALL`, 부서 코드 |
| `set-password <id>` | 비밀번호 변경. 그 계정의 기존 로그인은 모두 끊긴다 |
| `push-key` | ERP 숫자 반영 키를 새로 만든다(이전 키 무효) |
| `import-backup <폴더>` | 1단계 백업(`YYYY-MM-DD/{HK\|TW}_{코드}.json.gz`)을 DB 로. 버전이 더 높은 쪽이 남고, 여러 번 해도 같은 결과 |
| `backup [--keep N]` | DB 를 `wj_data/backup/YYYY-MM-DD.sqlite3` 로 복사(서버가 켜져 있어도 안전). **복원 = 서버를 끄고 그 파일을 `wj.sqlite3` 로 덮어쓰기** |

## Code.gs 와 다른 점
- **자동 번역은 지금과 같은 구글 번역**을 쓴다. 구글 번역은 Apps Script 안에서만 부를 수 있어서, **번역만 하는 작은 Apps Script**(`translate_proxy.gs`)를 하나 두고 PC 서버가 글자만 보내 번역본을 받는다. 일지 데이터·시트는 구글에 저장되지 않는다. 구글 번역이 실패하면 Gemini 가 예비로 받고(키가 있을 때), 둘 다 실패해도 저장은 그대로 되며 이력(log)에만 남는다.
  - **설치(한 번, 5분)**: `translate_proxy.gs` 맨 위 주석의 1~4번을 따른다 — 새 Apps Script 프로젝트에 붙여넣기 → `setup` 실행해 열쇠 받기 → 웹 앱으로 배포(실행: 나 / 액세스: 모든 사용자) → `wj_data\translate_url.txt` 에 첫 줄 웹 앱 주소, 둘째 줄 열쇠.
  - **동작 확인**: `python pc_server\wj_admin.py translate-test "안녕하세요 <b>3분기</b> 매출" --to en` (사용 중인 엔진 순서도 표시)
  - 서버를 켜면 첫 줄에 `자동 번역: 켜짐 (구글 번역 → Gemini)` 처럼 보인다. 설정이 없으면 번역만 꺼진다.
  - 저장하면 나머지 두 언어 칸이 채워지고("Auto-translated" 표시), 사람이 직접 쓴 칸은 덮어쓰지 않는 규칙은 Code.gs 와 같다.
  - 구글 번역의 하루 사용량 한도는 지금 쓰시는 것과 같은 종류다(Apps Script 의 LanguageApp). Gemini 예비 키: 환경변수 `GEMINI_API_KEY` 또는 `wj_data\gemini_key.txt`.
- **비밀번호는 새로 정한다**: 시트의 해시는 옮길 수 없다. 대신 PBKDF2(사용자별 소금)로 저장한다.
- 화면(HTML)은 시트·드라이브 대신 DB 에 한 줄로 저장한다(조각 나누기 불필요).
- 로그인 5회 실패 시 15분 잠금, 로그인 유지 1일, 칸 버전 충돌 검사, 마감, "편집 중" 표시, 입구(site)별 계정 제한은 Code.gs 와 같다.

## 백업 복원·검증 `restore_journal.py` (구글 서버·PC 서버 모두)

```
python pc_server\restore_journal.py --api-url <서버 주소> --id hq --verify      # 백업과 서버를 대조만 한다 (아무것도 바꾸지 않음)
python pc_server\restore_journal.py --api-url <서버 주소> --id hq --dry-run     # 무엇을 되돌릴지 보기만
python pc_server\restore_journal.py --api-url <서버 주소> --id hq               # 서버에 없거나 비어 있는 칸만 채움 (안전, 기본)
python pc_server\restore_journal.py --api-url <서버 주소> --id hq --mode overwrite   # 내용이 다른 칸도 백업 내용으로 (새 버전으로 기록되어 이력이 남음)
```
- 옵션: `--day 2026-10-21`(기본 가장 최근 백업) `--ent TW` `--codes W41 M09` `--include-auto`(자동번역 칸도).
- **본사(hq) 계정**으로 실행해야 모든 칸·마감된 주도 되돌릴 수 있다. 자동번역 칸은 사람이 쓴 것으로 바뀌지 않게 기본으로 건너뛴다. 그 사이 서버에서 바뀐 칸은 덮어쓰지 않고 '충돌'로 센다. 같은 명령을 다시 실행해도 결과가 같다.
- 정기 백업을 **매일**로 바꾸려면: `powershell -ExecutionPolicy Bypass -File pc_server\register_backup_task.ps1 -Daily -Time 02:00 -Keep 60`
- 권장 점검: 한 주에 한 번 `--verify` 로 최근 백업이 서버와 일치하는지 확인(차이가 나오면 종료코드 1).

## 시험
```
python -I pc_server\tests\test_server.py      # 서버·번역·관리 도구 36개 항목 (실제 HTTP, 번역은 가짜 엔진)
python -I pc_server\tests\test_restore.py     # 복원·검증 10개 항목 (실제 HTTP)
python -I pc_server\tests\test_backup.py
```

---

## 1단계 — 일일 백업 (시트 → PC)

시트(JOURNAL)에만 있는 부서 글·사진을 PC 에 날짜별로 저장합니다. **시트에는 아무것도 쓰지 않습니다(읽기 전용).**

```
python pc_server\backup_journal.py            # 기본: <프로젝트>\wj_backup\YYYY-MM-DD\{HK|TW}_{W41|M09}.json.gz, 30일 보관
python pc_server\backup_journal.py --no-photos   # 사진 제외(빠르게 시험할 때)
python pc_server\backup_journal.py --out D:\wj_backup --keep 60
```

- 글이 있는 코드(W1~W53, M01~M12)만 저장합니다. 같은 날 다시 실행하면 이미 받은 파일은 건너뛰고 이어서 받습니다.
- 로그인은 요약 반영과 같은 계정(`apps_script\weekly_journal\summarizer_login.txt`, `api_url.txt`)을 씁니다.
- 종료코드 0 성공 / 1 일부 실패 / 2 로그인·설정 오류.
- 복원·검증은 아래 `restore_journal.py` 를 쓴다. 저장 형식은 시트의 칸 ID·html·version·작성자·시각 그대로다.

## 매주 화요일 자동 실행 (윈도우 작업 스케줄러)

월요일에 부서 기입이 끝나면 화요일 오전에 한 주 분량을 백업합니다.

```
powershell -ExecutionPolicy Bypass -File pc_server\register_backup_task.ps1                  # 기본: 화요일 09:00, 90일 보관
powershell -ExecutionPolicy Bypass -File pc_server\register_backup_task.ps1 -Time 10:30
Start-ScheduledTask -TaskName WJ_Backup                                                      # 지금 한 번 돌려 보기
Unregister-ScheduledTask -TaskName WJ_Backup -Confirm:$false                                  # 해제
```
- 그 시각에 PC 가 꺼져 있었으면 켜진 뒤 바로 따라잡아 실행합니다. 로그인된 상태에서 돌고, 결과는 프로젝트 폴더의 `wj_backup_log.txt` 에 쌓입니다.
- 매주 받으므로 보관은 90일(약 13번)입니다. 날짜 폴더가 곧 그날의 전체 사본입니다.

## 시험

```
python -I pc_server\tests\test_backup.py
```

## SUMMARY 요약·번역 예약 실행 (한도가 풀린 뒤 한 번, 실패하면 이어서 재시도)

```powershell
$root = 'C:\Users\더네이쳐홀딩스\Desktop\중국판매데이터RAW'
$a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $root + '\pc_server\run_summary_retry.ps1" -Week 41 -Codes M09 -Fresh') -WorkingDirectory $root
$t = New-ScheduledTaskTrigger -Once -At '22:35'
$s = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Hours 5)
Register-ScheduledTask -TaskName WJ_Summary_M09 -Action $a -Trigger $t -Settings $s -Force
```
결과는 `wj_summary_run_log.txt` 에 쌓입니다. 끝나면 `Unregister-ScheduledTask -TaskName WJ_Summary_M09 -Confirm:$false`.
점검만 따로: `python weekly_journal\check_summary.py --code M09`
