# Windows 준비 체크리스트 (사람이 하는 설치)

- [ ] Python 3.12 설치 (64비트 / 32비트 중 Access ODBC 드라이버 비트와 일치시킴 — 불일치가 가장 흔한 막힘)
- [ ] Microsoft Access ODBC 드라이버 설치 (Access Database Engine), `python tools/check_env.py`로 목록 확인
- [ ] Sysinternals Process Monitor(ProcMon) 설치
- [ ] HxD 설치
- [ ] psr.exe(문제 단계 레코더) 실행 가능 확인
- [ ] `pip install -r tools/requirements.txt`
- [ ] 양도박사 EULA에 자동 조작/자동화 금지 조항이 있는지 확인 (있으면 결정 번복, 전체구조 §5-5)
- [ ] 양도박사 데이터 폴더 백업 (`docs/env.md`에 위치 기록)
- [ ] 양도박사 실행·로그인 후 `python tools/check_env.py` 출력을 `docs/env.md`에 붙이기
