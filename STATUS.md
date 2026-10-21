# STATUS — 지금 어디까지 했나 (빈 줄 제외 15줄, 항목당 한 줄. 배포 이력은 `docs/deploy-log.md`)

## 진행 중 (상태: 설계·구현·배포·확인대기 — 3줄이면 새 작업은 백로그 기록만)
- 전체 구조 `docs/work-plans/2026-10-22-전체구조.md` — 설계(Mac 몫 완료·푸시됨). 남은 것: Windows 에이전트가 W0 골격부터 착수, W0~W3 끝나면 구현 결과 적고 archive

## 막힌 것 / 사람 확인 필요
- Windows 첫 세션에 사람이 줄 것: 양도박사 EULA 자동화 조항 확인, 금지 메뉴 목록, 데이터 폴더 위치 (설계서 §5-5·6)

## 다음 할 일 (Windows 에이전트)
1. W0 저장소 골격 + W1 환경 점검(`tools/check_env.py`, 컨트롤 노출 확인) → `docs/env.md`
2. W1b 탐색(`tools/drive/explore.py`) → `docs/inventory/flow.md`·`screen_NN.md` 초안
3. W3 척추 케이스 C000 정의(`docs/reference/yangdose-testScenarios.js`에서 후보 선정) → W2·W2b·W4 1바퀴
