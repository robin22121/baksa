# STATUS — 지금 어디까지 했나 (빈 줄 제외 15줄, 항목당 한 줄. 배포 이력은 `docs/deploy-log.md`)

## 진행 중 (상태: 설계·구현·배포·확인대기 — 3줄이면 새 작업은 백로그 기록만)
- 전체 구조 `docs/work-plans/2026-10-22-전체구조.md` — 구현. 남은 것: 아래 탐색기 작업이 끝나면 구현 결과 적고 archive
- 설치형 탐색기 `docs/work-plans/2026-10-22-설치형-탐색기.md` — 구현. 남은 것: W1·W1b 구현 → dry-run → 양도소득세 실탐색 → §4 판정

## 막힌 것 / 사람 확인 필요
- 데모버전이라 출력 분석(3단계·W2b) 보류. 정품으로 바꾸면 재개 (`docs/decisions.md` "라이선스·출력 분석")

## 다음 할 일 (Windows 에이전트)
1. `git pull` → `pip install -r tools/requirements.txt` → 양도박사 실행 후 `python tools/check_env.py` 출력을 `docs/env.md`에 붙이고 조작 방식(uia/win32/좌표+OCR) 결정
2. 설계서 "구현 결과 > 남은 것"의 손질 지점 반영 → `python tools/drive/explore.py --dry-run` → 실탐색 → `docs/inventory/flow.md`·`screen_NN.md` 초안
3. W3 척추 케이스 C000 정의(`docs/reference/yangdose-testScenarios.js`에서 후보 선정) → W2·W2b·W4 1바퀴
