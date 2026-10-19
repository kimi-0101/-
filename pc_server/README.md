# PC 서버 1단계 — 일일 백업

시트(JOURNAL)에만 있는 부서 글·사진을 PC 에 날짜별로 저장합니다. **시트에는 아무것도 쓰지 않습니다(읽기 전용).**

```
python pc_server\backup_journal.py            # 기본: <프로젝트>\wj_backup\YYYY-MM-DD\{HK|TW}_{W41|M09}.json.gz, 30일 보관
python pc_server\backup_journal.py --no-photos   # 사진 제외(빠르게 시험할 때)
python pc_server\backup_journal.py --out D:\wj_backup --keep 60
```

- 글이 있는 코드(W1~W53, M01~M12)만 저장합니다. 같은 날 다시 실행하면 이미 받은 파일은 건너뛰고 이어서 받습니다.
- 로그인은 요약 반영과 같은 계정(`apps_script\weekly_journal\summarizer_login.txt`, `api_url.txt`)을 씁니다.
- 종료코드 0 성공 / 1 일부 실패 / 2 로그인·설정 오류.
- **복원 도구는 아직 없습니다.** 저장 형식은 시트의 칸 ID·html·version·작성자·시각 그대로라서 다음 단계에서 복원 스크립트를 만듭니다.

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
