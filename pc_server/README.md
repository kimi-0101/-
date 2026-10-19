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

## 매일 새벽 자동 실행 (윈도우 작업 스케줄러)

```
schtasks /Create /TN "WJ_Backup" /SC DAILY /ST 05:00 /TR "cmd /c cd /d C:\Users\더네이쳐홀딩스\Desktop\중국판매데이터RAW && python pc_server\backup_journal.py >> wj_backup_log.txt 2>&1"
```

## 시험

```
python -I pc_server\tests\test_backup.py
```
