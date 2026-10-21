# 참조 자료 (사본, 수정하지 않는다)

| 파일 | 출처 | 용도 |
|---|---|---|
| `yangdose-ALG.md` | `~/v/yangdose-selfreport-app-sell/research.md` "세무 알고리즘 정의서" 절(ALG-1~12), 커밋 `7e1f96f`(2026-05-07) | `tools/calc/` 조문 모듈 설계 입력. 사용자가 직접 쓴 세법 해석. 범위는 아파트 1주택 중심이라 분양권·상속증여 취득가액·환산취득가액·이월과세·감면·예정확정 합산은 없다 |
| `yangdose-testScenarios.js` | 같은 저장소 `src/test/testScenarios.js`(39개 시나리오, `input.extractedData` + `expectedResult`) | `cases/` 초기 케이스 후보. **기대값은 코드 출력일 수 있어 정답이 아니다.** 양도박사 오라클과 법령으로 재검증한 뒤에만 `cases/`로 옮긴다 |

- 결정: `docs/decisions.md` "외부 코드 참조" 행. 코드는 복사하지 않고 Python으로 조문 단위 재작성한다.
- 날짜 의존 주의: 중과 유예 2026-05-09 만료, 조정대상지역 DB 2026-02-12 기준, 세율 2025~2026년. 케이스 `law_date`로 구분한다.
- Windows PC에는 원본 저장소가 없으므로 이 사본이 유일한 참조다.
