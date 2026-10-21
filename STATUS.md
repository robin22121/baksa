# STATUS — 지금 어디까지 했나 (빈 줄 제외 15줄, 항목당 한 줄. 배포 이력은 `docs/deploy-log.md`)

## 진행 중 (상태: 설계·구현·배포·확인대기 — 3줄이면 새 작업은 백로그 기록만)
- 전체 구조 `docs/work-plans/2026-10-22-전체구조.md` — 구현(W0~W1b 뼈대 Mac에서 작성·미검증, "구현 결과" 표). 남은 것: Windows에서 W1 실행 → 손질 지점 반영 → W1b 탐색 1회 → archive

## 막힌 것 / 사람 확인 필요
- Windows 첫 세션에 사람이 줄 것: 양도박사 EULA 자동화 조항 확인, 금지 메뉴 확정(`docs/env.md` 기본 8개), 데이터 폴더 위치 (설계서 §5-5·6)

## 다음 할 일 (Windows 에이전트)
1. `git pull` → `pip install -r tools/requirements.txt` → 양도박사 실행 후 `python tools/check_env.py` 출력을 `docs/env.md`에 붙이고 조작 방식(uia/win32/좌표+OCR) 결정
2. 설계서 "구현 결과 > 남은 것"의 손질 지점 반영 → `python tools/drive/explore.py --dry-run` → 실탐색 → `docs/inventory/flow.md`·`screen_NN.md` 초안
3. W3 척추 케이스 C000 정의(`docs/reference/yangdose-testScenarios.js`에서 후보 선정) → W2·W2b·W4 1바퀴
