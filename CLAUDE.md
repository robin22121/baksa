# baksa (양도박사 분석) — 작업 규칙 (프로젝트 값)

형식·절차는 `~/v/CLAUDE.md`(= `~/w/CLAUDE.md`) 공통 규칙에 있다. 이 파일에는 이 프로젝트에서만 다른 **값**을 쓴다. 빈칸은 사용자와 한 번에 하나씩 채우고, 못 채운 칸은 "초안 — 사용자 확인"으로 남긴다.

## 최우선 목표

**완벽한 세금 신고 사이트를 만든다** — 대상 세목은 양도박사가 다루는 **양도소득세·상속세·증여세·주식평가·종합부동산세 전부**(사용자 확정 2026-10-22). 양도박사는 올드 레거시이므로 거기서 제공하는 **모든 신고 기능을 습득**하되, ① UI is best 원칙 ② 세법 최신 반영 ③ 절세 포인트를 집어 주는 사이트가 목표다. (사용자 확정 2026-10-22)

- 1단계 범위(지금): 설치형 양도박사(데모버전)를 **분석 코드로 관찰**해 다섯 세목의 신고 기능 전부를 습득한다. 데이터 모델과 계산 검증 케이스를 확보한다. 출력 규격(전자신고·인쇄)은 데모버전 제약으로 보류한다(`docs/decisions.md` "라이선스·출력 분석"). 진행은 양도소득세 척추 케이스 C000 1바퀴(`docs/work-plans/2026-10-22-전체구조.md` §2.3) → 화면·케이스 확장 → 나머지 세목 순서다. 계산 기준은 양도박사가 아니라 세목별 법령(양도: 소득세법 §94~§118, 상속·증여: 상속세 및 증여세법, 종부세: 종합부동산세법, 주식평가: 상증법 §63)·시행령·국세청 명세이며, 양도박사 버전의 옛 세법과 현행법 차이는 케이스 `law_date`로 구분해 기록한다.
- 2단계 이후: 사이트 설계·구현. 저장소 분리 여부는 미정(`docs/decisions.md` ❓).
- 하지 않는 것: 디컴파일·실행파일 코드 추출(`docs/ANALYSIS_PLAN.md` §0), taxflow(원천세) 참조(사용자 지시 2026-10-22). 과거 양도세 계산기의 정의서·시나리오는 `docs/reference/` 사본으로만 참조하고 코드는 복사하지 않는다

## 시작할 때 읽을 문서

| 요청 키워드 | 문서 (읽을 절) |
|---|---|
| 현재 상태, 다음 할 일 | `STATUS.md` |
| 확정된 결정, 번복 이력, 알려진 결함, 목표 밖 재지시, 백로그 | `docs/decisions.md` |
| 진행 중인 작업 1건 | `docs/work-plans/날짜-이름.md` |
| 분석 단계, 금지 사항, 보고 주기, 우선 케이스 목록 | `docs/ANALYSIS_PLAN.md` §0·§2 |
| 폴더 규격, 케이스 yaml 형식, 사람/에이전트 분업, 1바퀴 판정 | `docs/work-plans/2026-10-22-전체구조.md` §2·§4 |
| 윈도우 환경, 양도박사 버전, ODBC 드라이버 | `docs/env.md`, `docs/windows-setup.md` |
| 화면 입력 항목, 화면 순서 | `docs/inventory/flow.md`, `docs/inventory/screen_NN.md` |
| DB 테이블, 화면↔컬럼 매핑 | `data/schema/tables.md`, `data/schema/mapping.csv` |
| 전자신고 파일 레이아웃 | `data/efile/layout/` |
| 케이스, 오라클 비교, 불일치 | `cases/index.csv`, `cases/<group>/C###.yaml` |
| 세법 해석(비과세·장특공제·세율·중과), 계산기 설계 입력, 케이스 씨앗 | `docs/reference/README.md` → `yangdose-ALG.md`(ALG-2~10), `yangdose-testScenarios.js` |
| 불편한 점, 업그레이드 후보 | `docs/reports/pain_points.md` |

## 역할과 모델 (모델명은 이 표에만)

| 역할 | 모델 | 하는 일 |
|---|---|---|
| 메인 | Opus | 설계·작업계획서, 결과 검토, 커밋, 문서·일회성 조회 스크립트. **메인이 직접 보는 판단**: 케이스 input·basis 조문 확정, 양도박사↔calc 불일치 원인 판정, 인벤토리 "근거 조문" 열 |
| `implementer` | Sonnet | `tools/` 스크립트·템플릿·골격 전부(한 줄 포함). `tools/calc/`(조문→코드)만 Opus |
| `Explore` · `general-purpose` | Sonnet | 캡처·DB 덤프·전자신고 파일 읽고 표 초안, 3파일 이상 조사 |
| `fable` | Fable, effort high | 전체 구조 설계(완료, 2026-10-22), 케이스 그룹별 작업계획서 검토(대안·빠진 위험·종료 조건), 막힌 버그 분석 |

## 확인받을 것 (이것만 묻는다. 그 외는 기본값으로 진행)

- 데이터: 가상 납세자가 아닌 **실제 자료**를 쓰게 되는 경우, `.gitignore` 제외 폴더를 커밋 대상으로 바꾸는 경우
- 돈·계정: 새 Python 패키지 설치(`tools/requirements.txt` 밖), 유료 도구
- 외부: `git push`, 클라우드형에서 **저장·제출·결제**가 일어나는 조작(읽기·덤프는 기본값으로 진행)
- 프로젝트 고유: `docs/ANALYSIS_PLAN.md` 본문 수정(사용자 문서), DB 분석 2시간 중단 기준을 넘겨 더 파는 것

## 검증 원칙 (이 프로젝트에서 "완료"의 뜻)

- 수치(양도차익·공제·과세표준·세액)는 양도박사 **실화면 캡처 또는 출력 파일**에서 메인이 직접 읽은 값과 대조한다. 스크립트 출력만으로 완료라 하지 않는다.
- 전자신고 레이아웃은 국세청 명세 **와** 양도박사가 만든 실제 파일 양쪽에 맞아야 한다. 파싱값 = 케이스 input.
- 케이스 정답(`expected_law`)은 조문 근거가 있어야 한다. 양도박사와 다르면 법령 기준으로 원인을 적는다(양도박사 오류 / 숨은 분기 / 내 해석 오류).
- 체크포인트 보고는 `docs/ANALYSIS_PLAN.md` §0 주기(화면 1개·신고서 1종·케이스 그룹 1개)를 지킨다.
- 결함 번호는 공통 규칙(A/Q/U/u/F)을 쓴다.

## 데이터·개인정보·외부 서비스

- 양도박사에 입력하는 납세자는 전부 가상(이름·주민번호·주소). 주민번호는 `tools/fake_rrn.py`로 만든다.
- `data/raw/`·`data/efile/spec,samples/`·`data/schema/dump/`·`docs/steps/`·`docs/screens/`는 커밋하지 않는다(`.gitignore`). 분석 산출물(표)만 커밋한다.
- 외부 서비스 없음. 국세청 명세는 공개 자료를 사람이 내려받아 `data/efile/spec/`에 둔다(출처 URL은 `docs/env.md`).
- 클라우드형은 본인 계정으로 사람이 로그인한 Chrome에 CDP로 붙어 덤프한다. HAR·덤프 HTML은 토큰·개인정보가 들어가므로 `data/raw/cloud/`(gitignore).

## 배포·실행

- git: 있음(원격 `https://github.com/robin22121/baksa`, `main`). Mac은 맨 처음 설계·문서화·기본 개발계획(`docs/work-plans/2026-10-22-전체구조.md`)까지만 했다. **W0부터 모든 작업은 Windows PC의 Claude Code가 한다**(구현·분석·후속 설계·보고). 예외: W0~W1b 뼈대는 Mac에서 먼저 썼다(`docs/decisions.md` "두 PC 역할", 2026-10-22) — Windows는 그 손질부터. 동기화는 `origin/main`만.
- 양도박사 조작: 설치형은 에이전트가 직접 자동 조작한다(탐색·캡처·케이스 입력, `tools/drive/`). 금지 메뉴는 `docs/env.md`. 클라우드형도 자동화 허용(`tools/cloud/dump-web.mjs` — 사람이 로그인한 Chrome에 CDP 연결, 화면별 HTML·필드 덤프; 2026-10-22 사용자 지시).
- 배포 대상: 없음. 종료 신호는 STATUS 갱신 + archive 이동 + 커밋.
- 로컬 실행(Windows): `python tools/check_env.py`, `python tools/compare.py cases/basic/C000.yaml`
