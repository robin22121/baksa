# 양도박사 DB 테이블 조사 (C단위, 정적 분석)

- 대상: `C:\Neoic\Tax2019\YDdoctor.exe` (SHA-256 a528bfb2…, MVID 52da1e5a…). 실행·DB 파일 열기 없음. 자격증명·연결 문자열 값은 생략(자격증명 생략). DB 파일은 상대 경로 `Data\neoTax.fdb`(Firebird) 하나로만 관찰됨.
- 방법: REA `inspect_managed_members`는 큰 폼(Cal100_*, JasanFOR, Jasan153 등)에서 "metadata exceeds 64MB budget"으로 실패했다. 그래서 (1) exe 바이트에서 `#US` 힙(ldstr 리터럴)을 읽기 전용으로 파싱해 SQL 문자열 전체를 모으고(스크립트, 실행 아님), (2) 클래스 귀속은 REA로 열린 클래스(DEList100, Men100, Jasan/JasanInfo/JasanConfirm, DM, ClientDataSet)의 user_strings 오프셋·call_edges로 확정했다. 그 밖의 클래스는 힙 위치 근접으로만 추정(표에 "추정" 표기).
- 접근 계층(확정): 폼은 SQL을 직접 쓰지 않고 `YDdoctor.ComData.ClientDataSet`(Delphi식 API: Open/Append/Edit/Post/Cancel/ApplyUpdates, 내부는 DataTable+FbDataAdapter)와 `YDdoctor.ComData.StringList`(SQL 묶음 Add/Execute)와 `YDdoctor.Common.DM`(데이터 모듈)을 호출한다. **Append/Edit/Post/Cancel은 메모리(DataTable)만 바꾸고, DB 쓰기는 `ApplyUpdates`·`StringList.Execute`·`ClientDataSet.Execute`에서만** 일어난다(ClientDataSet call_edges).

## 1. 세목 접두사

| 접두사 | 세목(추정 근거) | 테이블 |
|---|---|---|
| 100 | 양도소득세 (`JASAN100`, "양도인"=MEN100) | MEN100, JASAN100, JASAN100_ANBUN, JASAN100_PARTBUY, CINFO/CINFOSUB/PINFO/PINFOSUB(+_TEMP)100 |
| 200 | 상속세 (JASAN200에 EXPLIFE, 가업·영농 화면) | MEN200, JASAN200 |
| 300 | 증여세 ("수증자" 문구, MEN300.JNAME 등) | MEN300, JASAN300 |
| 400 | 주식평가 추정(확인 필요) — MEN300 복제 구조, JASAN400_SALERIGHTS | MEN400, JASAN400, JASAN400_SALERIGHTS |
| 500 | 종합부동산세 (MEN500.ONEHOUSE/AGE/PER, JASAN500.IMJU/EXJU/TOAREA) | MEN500, JASAN500 |

공통 규칙(확정): `MENxxx` = 납세자(신고 단위) 헤더, `JASANxxx` = 그 납세자의 자산 행. 연결은 100번대만 `JASAN100.MENID → MEN100.UID`, 200~500번대는 `JASANxxx.PID → MENxxx.UID`. 삭제 플래그 `MDEL`은 CHAR(1) 기본 '1'=정상, '0'=휴지통(DEList100: `WHERE MDEL='0'` 목록, 복원은 `SET MDEL='1'`, 완전삭제는 `DELETE ... WHERE MDEL='0'`로 자식 테이블까지 지움; 반대로 Men100 필터 조회는 `MDEL='1'`).

## 2. 양도(Tax100) 핵심 테이블

| 테이블 | 컬럼(관찰) | 읽는/쓰는 클래스 | 비고 |
|---|---|---|---|
| MEN100 | UID(PK, GEN_MEN100_ID), CODE(표시용 순번, 없으면 UID로 채움), YDID(''=편집가능, '마감'=편집제한), REGDATE, YDDATE, JASANGU(자산구분 부동산/매매/파생·주식), YDYEAR(양도연도), NAME, JUMIN(Seed 암호화), JUSO, POST, TEL, HP, OUTJUSO, EMAIL, SEMUSEO/GUNAME/SEOCD/SEOONLINE(관할세무서), SINGOGU(예정/확정), SINDATE, NAPDATE, NAPGI1/2, BUNGU, OLDUID(수정신고 원본), MDEL, NOTSHARE/TID(클라우드 공유용, 로컬은 빈값), JUSOINFO, BIGO, IP, YANGSU, ETC, MEMO, X1~X4. 계산 결과 묶음 약 200컬럼: CC02_1x~4x, CC03_n/CC03Sn, CC04~CC15(및 _1.._7 세율구간별), CC08Nn, CCX1/CCX3/CCX4/CCX5(+_n), CCN3, CCG3(+_n), CC04X05_n, CC16~CC34, CC1H | 쓰기: ClientDataSet(ApplyUpdates의 UPDATE/INSERT MEN100, 컬럼 257/258개 전수 바인딩). 읽기: Men100, DEList100, Men100All, Men100Filter*, DM.GetMenRec, DM(`SELECT * FROM MEN100 M WHERE M.UID=`), Yangsu(백업 `.yb1`) | DB 업그레이드 루틴이 ALTER로 CCnn_5/6/7 구간 컬럼을 계속 추가(법 개정 때마다 구간 확장 — 데이터 모델 힌트). CC02~CC15 = 양도소득금액~세액 계산 줄 번호(신고서 항목 번호 추정) |
| JASAN100 | UID(PK; 채번은 `MAX(UID)`), PUID(부모 자산 UID, 분할 자산), MENID(→MEN100.UID), UID2(MENID 안 순번, `MAX(UID2) WHERE MENID`), REGDATE, YDID, JASAN(자산유형 코드 21~77 등), JASANNAME, CCGU, SEQ, CHK(목록 정렬 순서; `UPDATE SET CHK`), **CALC**('1'=계산 대상/완료, 조회는 거의 `CALC='1'`), INPUTDATA·SILINPUT·INPUTREC1~3(BLOB 텍스트: 화면 입력값 직렬화), CC01~CC24(+CC24_CODE/JISU/HANDO/NONG/JOHANG 감면), CC06(양도일), CC11(취득일), CC03(자산구분 한글 문자열), CC04(양도차익), CC17~CC23 및 `CC17_`~`CX23_`·`CC17ORG`·CK2018·CC00·CC1H·KD·YC1/YC2·Y0~Y4·C1~C4(계산 중간/결과값), X1~X4, X9~X11 | 쓰기: ClientDataSet.ApplyUpdates(INSERT/UPDATE 94~95컬럼), DM.DataPost/ADDDataProc, Jasan(`UPDATE ... SET CHK=`, `DELETE ... MENID=.. AND UID IN`), DEList100(MENID로 일괄삭제), DM(빈 INPUTDATA 정리 DELETE). 읽기: Cal100*/Cal100m* 계열(`WHERE MENID=? AND CALC='1' AND (JASAN IN ...)` 다수; 클래스 귀속은 추정), Jasan/JasanInfo, Men100 | `SELECT J.*, CAST(0 …) CX22 …` 처럼 계산용 가상 컬럼을 SELECT에서 붙임 |
| JASAN100_ANBUN | UID, TID, REGDATE, ADDR, SALEDATE, SALEAMOUNT, INPUTDATA, GUNDATA, TOJIDATA, CALLOG, GUNTOJIDATA, SUBLISTDATA | ClientDataSet.ApplyUpdates; 삭제: 클래스 `Jasan_Anbun`(추정, 힙 1222349~) | 겸용주택/건물·토지 안분 계산 데이터(건물·토지 분리 BLOB). 채번 `MAX(UID)` |
| JASAN100_PARTBUY | UID, SEQ, PID(→JASAN100.UID), JASAN, JASANNAME, ADDR, SALEDATE, SALEAMOUNT, INPUTDATA, SUBLISTDATA2, TBUYINFO, GBUYINFO, CINFO, CINFOSUB, PINFO, PINFOSUB, GOSIDATA, GOSI | Jasan(조회·삭제 확인), Jasan_PartBuy(추정) | "2회 이상 지분취득 자산분할" 입력. CINFO·PINFO 내용을 BLOB으로 중복 보관 |
| CINFO100 / CINFOSUB100 | CINFO: TID,UID,JASAN,SEQ,STYPE,STYPE2,S00,S11~S16,S1T,S21~S27,S2T,S31~S34,S3T,S4,ST,MENID. SUB: NUM,GU1,GU2,NAME,NO,GDATE,AMOUNT,CODE | ClientDataSet 경로의 INSERT…SELECT·DELETE(DM 근처 힙 1526897~1554175) | 취득가액·가산 비용 내역(추정: "취득실가 내역 및 비용 내역" 문구 인접). S1x/S2x/S3x 합계 컬럼 `…T` |
| PINFO100 / PINFOSUB100 | PINFO: S11~S17,S1T,S2,S21,S31~S35,S3T,S123T,S41,S42,S4T,S1234T,S51. SUB 동일 | 위와 동일 | 양도가액·양도비 내역(추정) |
| CINFO_TEMP100 / CINFOSUB_TEMP100 / PINFO_TEMP100 / PINFOSUB_TEMP100 | 위 본 테이블과 같은 컬럼 | 위와 동일 | **작업 사본**: 상세 입력 창을 열면 `INSERT INTO *_TEMP100 SELECT … FROM *100 WHERE UID/JASAN`로 복사, 확인 시 `INSERT INTO *100 SELECT … FROM *_TEMP100`(새 UID), 취소/완료 시 TEMP 삭제. TEMP는 UID 없이 JASAN+SEQ+STYPE로 키 |
| ENV | CUID(100번 마지막 선택 UID), CUID200/300/400/500, DBVER(0/1 스키마 갱신 플래그), ETC, JONG, UP, BACKGU, IDGU, PRINT, 암호·SMS 계열(생략) | DM.GetEnv, ClientDataSet(UPDATE ENV SET CUIDnnn=…) | 단일 행. 납세자를 고를 때마다 마지막 선택 UID를 저장 |
| SWS | FYEAR, MON1~MON12 | 업그레이드 루틴이 1965~2019 월별 값을 UPDATE로 시드(시드 SQL만 있고 2019까지, 5월 이후 0), 금액 환산 폼 읽기 | 연도×월 지수(생산자물가지수로 추정: "취득고시월 생산자물가지수" 문구, 골프회원권 기준시가 폼 인접). 법령 기준값 표 |
| SIGADATE | GU('HOUSE'/'APT'/'TOJI'), TERM('R' 등), GOSIDATE | 다수(주택·토지 고시일 목록) | 기준시가 고시일 목록. 양도일·취득일에 맞는 고시일 선택에 사용 |

## 3. 참조(룩업) 테이블 — 읽기 전용으로 관찰됨

| 테이블 | 컬럼(관찰) | 용도 추정 |
|---|---|---|
| TAX_CODE | CD, NM, ONLINE | 세무서 코드·명·전자신고 계좌 |
| DONG | HNG, DONG, SI, GU, TAX(→TAX_CODE.CD) | 법정동→관할세무서 |
| POST / POST2 | "법정동코드","건물본번","건물부번","건물명","리","읍면동" … | 도로명주소 검색 |
| GAM | CD, NM, VYEAR | 감면 코드 목록 |
| GUJO, YONGDO, WICHI(ISANG,MIMAN,JISU,VYEAR), JOJUNG, JANGA, SANJUNG(MAKEYY), TOJI(GA,DNG), ROOF(vyear), SUBLIST(YYCD,AREA) | 건물 기준시가 산정 계수표(구조·용도·위치·조정·잔가·산정) | 건물 기준시가 계산 |
| EXPLIFE | YEARS, AGE, FEMALE, MALE | 기대여명표(상속) |
| GOLF | SYEAR, GOLFNAME, GOLFSPEC, ADDRESS | 골프회원권 기준시가 |
| BANK | NAME, CODE | 은행 목록 |
| BUYTYPE | UID … | 취득가액 유형 |
| VIRTUAL_CODE | CODE, NAME, SYMBOL | 가상자산 종류 |
| `nts{연도}`, `reb{연도}`, `molit{연도}` | NTS: ADDR, DOJU. REB: APT_CODE, DONG_NAME, HO_NAME, PRIV_AREA, PROVINCE_NAME… MOLIT: DANCODE, APTDONG, APTHO, MUN, APTDONGCODE, APTHOCODE | 연도별로 이름이 바뀌는 공시가격 테이블(국세청/부동산원/국토부 공동주택가격 추정). 이름은 문자열 조합이라 연도 목록은 미확인 |
| FILEMT | service | 파일·버전 메타(추정) |
| SHAREID, SHARE_JOIN, MEMBER | TID, SID, USERID, USERNAME | 클라우드 공유 계정(다중 사용자). 로컬 Firebird에서는 쓰이지 않는 것으로 보임 |

## 4. 200~500번대 (요약)

| 테이블 | 컬럼(관찰) | 비고 |
|---|---|---|
| MEN200 | UID, CODE, NAME, JUMIN, ADDR, SDATE, SGU, TEL, SEOCODE, SEONAME, SEOBANKNO, EMAIL, SINYEAR, SINDATE, NAPDATE, REGDATE, MATE, JIBUN, INPUTDATA, GONGDATA, JANGDATA, CHEMUDATA, SDATA, BDATA, MEMO, JREG, ETC, YDID, MDEL, EJREPORT | 상속: 공제·장례·채무·재산 데이터를 BLOB(GONGDATA/JANGDATA/CHEMUDATA/SDATA/BDATA)로 보관 |
| JASAN200 | UID, PID, UID2, SEQ, JGU, JGUNAME, JCODE, JKIND, JBUN, SOJE, QTY, DANGA, AMOUNT, TAMOUNT, JIBUN, TJIBUN, GIJUN, BIGO, INPUTDATA, SUBDATA~SUBDATA4, JIBUNDATA, CALC | 상속재산 행 |
| MEN300 | UID, CODE, ADDR, SEOCODE/SEONAME/SEOBANKNO, JNAME, JJUMIN, JTEL, JHP, JADDR, JREL, JDATE, JGU, JREG, JSIN, SINYEAR, BIGO, JUSOINFO, YDID, MDEL … | 증여(수증자·증여자) |
| JASAN300 | UID, PID, UID2, JBUNAME, BASEDATE … (JASAN200 계열 컬럼) | 증여재산 |
| MEN400 / JASAN400 | MEN400=MEN300 구조(CREATE문 확인). JASAN400=JASAN200 구조 + JBUNAME, BASEDATE. MEN400·JASAN400은 `GEN_MENnnn_ID`/BEFORE INSERT 트리거로 UID 채번 | 세목 확인 필요 |
| JASAN400_SALERIGHTS | UID, TID, SEQ, S01~S21(S01_1~3, S18_1/2, S19_1, S20_HALF), S_CALC, S_GAM, INPUTDATA~INPUTDATA3, MEMO, SUBDATA1~4 | Tax400 `Jasan400_SaleRights` 화면 |
| MEN500 | UID, CODE, NAME, JUMIN, ADDR, TEL, HP, EMAIL, SINYEAR, REGDATE, INPUTDATA(2,3), MEMO, ETC, YDID, MDEL, ONEHOUSE, AGE, PER, COMPANYNO, CALMEMO1~4 | 종부세 납세자 |
| JASAN500 | PID, UID2, SEQ, JGU, SOJE, JA, AMT, AMT_P, AMT_N, JIBUN, TJIBUN, BIGO, IMJU, EXJU, TOAREA, GUAREA, JNAP, CCHK, CNAP, ACHK, ASIGA, ANAP, TOJIINFO, TOJICNT | 종부세 자산(주택/토지 구분 `TAX_CODE`·시가표준 조회 포함) |

200~500은 수량이 적어 폼별 귀속은 힙 위치 군집으로만 추정했다(§6).

## 5. U2 / U4 관련 SQL·구조 (정적 근거, 동작 확인은 아님)

### 5.1 U2 (화면만 열어도 레코드가 생김)
1. **쓰기 경로가 한 곳뿐**: 레코드는 `ClientDataSet.ApplyUpdates`(INSERT/UPDATE 전 컬럼 일괄)·`DM.DataPost`/`ADDDataProc`에서만 생긴다. 이 구조에서는 "열기만 해도 행이 생긴다"면 열기 경로가 이들을 호출한다는 뜻이다.
2. **양도인 화면(Men100)은 열기만으로는 INSERT 호출이 없다** — `Men100_Shown`(fn_FMCreate, rb1_Click, FilterInputCheck), `fn_Env`, `DataNew`의 call_edges에 Append/Post/ApplyUpdates가 없다. 쓰기는 `acRegExecute`(등록)에서만(Append→Post→ApplyUpdates), `FormClose`는 편집 상태이면 확인창(show_yesno) 후 acRegExecute를 부른다. 즉 U2의 원인은 양도인 화면이 아닐 가능성이 높다.
3. **자산 목록(Jasan)이 유력**: `btnG1`~`btnG65`(기준시가 > 토지/건물/아파트…), `btnS52`~`btnS69`(실지거래 > …) 등 자산유형 버튼 클릭 핸들러(`btnG1Click`, `btnEdit_Click`)가 `DM.DataPost`를 40회 안팎 호출(Append→SetString/SetNum→Post→ApplyUpdates→ADDDataProc)하고 `DM.SaveCalLog`를 부른다 → 상세 입력 전에 JASAN100 행이 먼저 만들어진다고 읽힌다(상세 화면 호출 전 선삽입 방식 — 추정).
4. **빈 레코드 정리 SQL이 따로 존재**: DM 문자열에 `DELETE FROM JASAN100 WHERE PUID=… AND (INPUTDATA IS NULL OR INPUTDATA='')`, `SELECT * FROM JASAN100 WHERE PUID=… AND (INPUTDATA IS NULL OR INPUTDATA='')`, 계산 조회 쪽에 `(INPUTDATA IS NULL OR DATALENGTH(INPUTDATA) < 3)`. `Jasan.JasanCancel`·`btnDel_Click`·`btnReSeq_Click`는 `GetJasanUIDGroup` + `StringList.Execute`(삭제/재정렬 SQL)를 실행한다. 입력이 빈 선삽입 행을 사후에 지우는 설계로 보이며, 정리를 놓치면 유령 행이 남는다.
5. **UID 채번**: JASAN100·_ANBUN·_PARTBUY·JASAN400_SALERIGHTS는 `SELECT MAX(UID)`(+UID2는 `MAX(UID2) WHERE MENID/PID`), MEN100~MEN400은 Firebird 제너레이터(`GEN_ID(GEN_MENnnn_ID,0)` 조회, MEN400·JASAN400은 BEFORE INSERT 트리거 존재). MAX+1 방식이면 행이 먼저 생겨도 UID가 즉시 소비됨.
6. 확인 못 한 것: 실제 입력 폼(Jasan153/JasanFOR 등)과 Cal100*의 열기 핸들러(REA 메타데이터 한도 초과). 따라서 "자산 입력 폼을 열 때 선삽입하는가"는 미확인.

### 5.2 U4 (계산 버튼이 저장함)
1. 계산 결과는 별도 테이블이 아니라 **MEN100·JASAN100의 CC* 컬럼에 같이 저장**된다(MEN100 약 200개 결과 컬럼, JASAN100 CC17~CC23·`_` 변형). 계산 로직이 값을 컬럼에 채우면 그대로 `ApplyUpdates`(UPDATE MEN100 257컬럼 전수, UPDATE JASAN100 95컬럼 전수)로 나간다 → "계산 = 저장"이 구조적으로 합쳐져 있다.
2. 계산 로그는 DB가 아닌 **파일**: `DM.SaveCalLog` → `StringList.SaveToFile`, `TCalLog.SaveFile`(문자열 `Log\`, `.Log`, `.HLog`, `Rep\CalLog.frx`). `DM.reSetCalLog`도 있음.
3. **편집제한/허용 플래그**: `UPDATE MEN100 SET YDID='마감'`(편집제한), `SET YDID=''`(허용). 문구: "「편집허용」가 되면 「세액재계산」이 자동실행되며, 수기로 입력한 항목의 값은 소멸될 수 있습니다." → 허용 시 재계산이 자동으로 돌아 값을 덮어쓴다. `UPDATE JASAN100 SET CC10=…`, `SET X9=…`, `SET CHK=…` 등 부분 UPDATE도 계산 폼 근처에 있음.
4. `JASAN100.CALC`: 계산 조회가 `CALC='1'`만 읽으므로 자산 행에는 "계산 포함 여부" 상태가 있다. 계산 버튼이 이 플래그를 바꾸는지는 미확인.
5. 확인 못 한 것: `Cal100_*`, `Cal100m_*`, `Jasan123Cal` 등 계산 폼 본체(메타데이터 한도 초과)에서 어떤 버튼이 어떤 ApplyUpdates를 부르는지.

## 6. 폼·클래스별 SQL 사용 (확정=REA 오프셋 일치, 추정=힙 근접)

| 클래스 | 상태 | 읽기/쓰기 요약 |
|---|---|---|
| ComData.ClientDataSet | 확정 | 모든 테이블 일반 읽기(`Open`=FbDataAdapter.Fill)·쓰기. ApplyUpdates: UPDATE/INSERT(MEN100·JASAN100·_ANBUN·_PARTBUY·MEN/JASAN200~500·SALERIGHTS), `MAX(UID)`/`MAX(UID2)` 채번, `GEN_ID`, 100번대 `*_TEMP100`↔본 테이블 INSERT…SELECT·DELETE 일체 |
| Common.DM | 확정 | `GetEnv`(SELECT * FROM ENV), `GetMenRec`, `DataPost`, `ADDDataProc`, `GetJasanUIDGroup`, `GetParentUID`, `SaveCalLog`, `NextConsole`; SQL: `SELECT UID,PUID FROM JASAN100 WHERE MENID=`, `DELETE FROM JASAN100 WHERE PUID=`/`UID IN`, `UPDATE MEN100 SET YDYEAR=`, `SELECT INPUTDATA FROM JASAN100 WHERE UID=`, SIGADATE(HOUSE) 조회 |
| Tax100.Men100 | 확정 | MEN100 CODE 보정 UPDATE, 연도 목록(`SUBSTRING(YDYEAR …)`), 중복 납세자 검사 SELECT(MDEL='1', JASANGU·YDYEAR·JUMIN 조건 36문), `UPDATE MEN100 SET MDEL='0'`(삭제=휴지통), `SET YDID='마감'/''`, `SET NOTSHARE`, JASAN100을 CC06/CC11 기간·MENID로 조회, JASAN100_PARTBUY MAX(UID,SEQ) |
| Tax100.DEList100 | 확정 | MDEL='0' 목록, 복원 `SET MDEL='1'`, 완전삭제 시 MEN100+JASAN100+CINFO/CINFOSUB/PINFO/PINFOSUB(+_TEMP) 연쇄 DELETE |
| Tax100.Jasan / JasanInfo / JasanConfirm | 확정 | JASAN100 MENID 조회, `SET CHK=`(순서 고정), `DELETE … MENID AND UID IN`, JASAN100_PARTBUY 조회·삭제, MEN100 UID 조회. ApplyUpdates는 `JasanUpdate`에서만 |
| Tax100.Yangsu | 확정(문자열 일부) | 데이터 파일 `.yb1` 백업·복원: MEN100/JASAN100/CINFO*/PINFO*/JASAN100_PARTBUY/_ANBUN 전체 SELECT·`DELETE FROM … ;`(전체 비우기), `UPDATE ENV SET CUID=`, `SELECT * FROM JASAN100 ROWS 1`(스키마용 빈 조회) |
| Tax100 Cal100*/Cal100m*/Cal100g* 계열 | 추정(열기 실패) | `SELECT J.* … FROM JASAN100 WHERE MENID=? AND CALC='1' AND JASAN IN/NOT IN (21,22,23,71~77 …)` 다수(힙 652849~663032, 674995~682311, 780185~792866), `UPDATE JASAN100 SET X9=/CC10=` |
| Tax100.Jasan_Anbun / Jasan_PartBuy | 추정 | JASAN100_ANBUN·PARTBUY SELECT/DELETE (힙 1222349~1224588, 1313428~1330819) |
| Tax100 주소·공시가 폼(SiGunView, CityInfo, SigaView 등) | 추정 | DONG/TAX_CODE/POST/POST2, nts·reb·molit{연도}, SIGADATE |
| Tax200 | 추정 | MEN200/JASAN200/EXPLIFE (힙 381723~482853, 560725~567596) |
| Tax300 | 추정 | MEN300/JASAN300 (힙 241397~278759, 349750~375489) |
| Tax400 | 추정 | MEN400/JASAN400/SALERIGHTS/BANK (힙 173258~210090) |
| Tax500 | 추정 | MEN500/JASAN500/TAX_CODE, 공유 계정 SELECT(SHAREID·SHARE_JOIN·MEMBER) (힙 99349~169364) |
| DB 업그레이드 루틴(클래스 미확인) | 추정 | 시작 시 `rdb$relation_fields`/`rdb$relations`로 컬럼·테이블 존재 확인 후 `ALTER TABLE … ADD`/`CREATE TABLE`(MEN400, JASAN400, MEN500, JASAN500, 트리거·제너레이터), `CHARACTER SET NONE` 변환, SWS 시드, MEN100.MEMO 재생성. `ENV.DBVER` 0/1 갱신 (힙 38395~110000) |
| Common.VirtualAssetsCode | 추정 | VIRTUAL_CODE SELECT |
| Common.BackupAndRestore | 추정 | MEMBER_YD(기본형·클라우드 구분) 조회·갱신 — 라이선스성 가능, 상세 생략 |

제외(규칙상 분석 안 함): Reg*/RegisterUser*/Login/Demo/TimeReg 등의 `member*`·`NEOKEY`·`connect_log`·`sp_GetYdId` 호출, 연결 문자열·계정 값.

## 7. 특이점 (설계 관찰)

- 이중 SQL: 같은 쿼리가 `TID` 조건 유무, `Top 1`(SQL Server)/`ROWS 1`(Firebird), `SUBSTRING(x ,1 ,4)`/`SUBSTRING(x FROM 1 FOR 4)`로 쌍으로 존재 → 로컬(Firebird)+클라우드(SQL Server, 사용자별 TID) 겸용 코드. 로컬 분석 시 TID 없는 쪽만 보면 된다.
- 한 납세자 레코드에 입력 원본(INPUTDATA BLOB 텍스트)과 계산 결과 컬럼이 같이 있다. 재현 시 INPUTDATA의 직렬화 규격을 따로 확보해야 한다(이 단계에서는 미조사).
- 주민번호는 `Seed_Encrypt`로 암호화되어 MEN100.JUMIN에 저장되는 것으로 보임(Men100 edges: `Seed_Encrypt::Encrypt/Decrypt`).

## 부록 A. Evidence IDs

| 대상 | 요약 Evidence | 부모(페이징용) |
|---|---|---|
| Common.Bankno | ev_52d3490a159943e4ce80676f70b6bbd552a15d5db474f99318367cd718dad80b | ev_690cb244ade58f9c50822b962607cbdc7691054a257d5892c9ad1d0a54f10b1f |
| Tax100.Men100 | ev_b0c465d206013746dbe99fb2be72595bced8d76027c70075004b2e894a30a199 | ev_bd7557cb6b8a03e5d51b86ac5c5f30b2b3d549590ef86830e4ef5c46171d55ec |
| Tax100.DEList100 | ev_03fdbf0eeb6e9b0df13f049a4bd9a696e247848a208e2a6e3582104aea00f0ad | ev_7a4eda1f1b9c0c2b09a6d5afca5e37b87577c7cd4ecf861c23a58041039e3dda |
| Tax100.Yangsu | ev_62cb68d264c4953d6b0ced058b7599cb42c21b0c7a19cf46c3624fb80e1c422c | ev_99de39c28498787189435adddec324612b951158baeea013c5a3749a7363d73f |
| Common.DM | ev_d37374f8c6d51350847329afb067985b18e477f26caebfdacba49b3f2f7979d5 | ev_96f840d81b0e9d0655614fa9ae19dcc324c286a651df7b33ed8fb5a3198e7f17 |
| ComData.ClientDataSet | ev_750f429524da6a799f75ec4798dd4d9d7be66f396efdeac094312446a1a7c179 | ev_69ade3787cb34deab41f06079a1f871d2a6a0c406af3babef5e6a9af5b575f38 |
| Tax100.Jasan+JasanInfo+JasanConfirm | ev_b61559b8222f36501d85944093128355167053b6ee189bf0ab7e0ffd18941ade | ev_adc8de199a8500e7b08dcf7f6ccec64148c8019349c98500d6babddb1d61b5b1 |
| Common.StartProgress, Common.DB, Program (DB 아님/소규모) | ev_a1b2a72c245e716fa106cf3c9a9d2d517eaa72edc5d789b8c8829e7a80df78fb, ev_f4214ae089e031d3b0fc70a03cf443ad372c879d800e7ba2727a309247bdc0b0 | ev_82d663b7…, ev_e2f64040… |
| 실패(메타데이터 한도 초과) | Cal100_2020 ev_5543f7f9e540aa62bd2d92cf9b38b24097ed5369985913fe05194083d258a7d4, 10개 폼 묶음 ev_7716c95137c311257df4336c9df4230ad153bc28d60cb043c5c53a502ecc758a, JasanFOR+Jasan153 ev_947b4efc0c82b0a2b023071758dda33d4b2f98b2cf40d09da2ee850deb9e2bc0, JasanFOR ev_644541daa27f869b42cb1037f133ba47971482c1a4c2a3f44f340967346881cc | – |

## 부록 B. 검토한 클래스

Tax100.Men100, DEList100, Yangsu, Jasan, JasanInfo, JasanConfirm; Common.DM, Bankno, StartProgress, DB; ComData.ClientDataSet(+StringList·Util 호출 관계). 문자열 힙 전체(약 4.3만 리터럴 중 SQL 898개)는 클래스 귀속 없이 위치 군집(104개)으로 분류.

## 부록 C. 미확인

- 큰 폼의 열기·버튼 핸들러: Cal100_*/Cal100m_*/Cal100gr_*, JasanFOR, Jasan1xx(153~181), Tax100.Tax100·Main, Tax200/300/400/500 폼 본체 (REA 메타데이터 64MB 한도). U2/U4 확정에는 이 폼들의 call_edges가 필요 → 분할 도구(IL 추출 도구 등) 또는 런타임 관찰로 보완.
- DB 업그레이드 루틴과 `Common.Util`/`CommonVar` 소속 SQL의 클래스명.
- 테이블 전체 목록·타입·인덱스(스키마 직접 조회는 금지 범위; `data/schema` 덤프와 대조 필요). 본 문서의 컬럼은 SQL에 등장한 것만이며 DB 실제 컬럼과 다를 수 있음.
- 400번대 세목 확정, CINFO/PINFO의 정확한 의미, `nts/reb/molit{연도}`의 연도 목록, JASAN100.CALC·CHK·KD·CK2018 값의 의미, INPUTDATA 직렬화 형식.
- 영문/한글 구분이 필요한 SQL 중 일부(자산구분 한글 조건 `JASANGU='부동산'` 등)는 값 해석을 코드 페이지 문제로 일부 확인하지 못함.
