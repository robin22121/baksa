# YDdoctor 기능 지도 (REA 정적 분석 단위 A)

- 대상: `C:\Neoic\Tax2019\YDdoctor.exe` (.NET 4.6.1, SHA-256 a528bfb2…c6c9, MVID 52da1e5a-b892-417c-a02c-458e921388e9). 실행하지 않고 메타데이터·사용자 문자열(#US)만 읽었다.
- 목적: 기능·세액 계산 구조·신고 케이스 이해(복제 아님). 코드·CIL은 싣지 않는다.
- **근거 수준 표기**: `[문자열]` = 해당 클래스 묶음(분석 호출 1건)에서 읽은 문자열 근거. REA 문자열 표는 클래스별 귀속이 없어 **묶음 단위**로만 확인된다. `[이름]` = 클래스 이름(접미사·연도) 기반 추정이며 문자열로 확인하지 않았다. 따라서 폼 하나하나의 "화면 기능" 칸은 묶음 근거 + 이름 추정의 결합이다.

## 0. 모듈 ↔ 세목 매핑

| 모듈 | 세목 | 폼 수 | 메인/메뉴 클래스 | 근거 |
|---|---|---|---|---|
| Tax100 | 양도소득세 (+ 증권거래세 신고 포함) | 280 | `Tax100`, `Main`, `Men100`, `Men100All`, `MenView` | TaxLauncher 메뉴 문자열 "양도소득세", FAQ "양도소득세 FAQ", T100 묶음의 양도소득세 세율(소득세법 제104조)·양도차익·장기보유특별공제·비사업용토지 문자열 |
| Tax200 | 상속세 | 88 | `Tax200`, `Main200`, `Men200`, `Men200View` | "상속세 서식인쇄", 상속공제·가업상속공제·연부연납·물납·사전증여재산 문자열, 상속인 등록 |
| Tax300 | 증여세 | 88 | `Tax300`, `Main300`, `Men300`, `Men300View` | "증여세 서식인쇄", 수증자 등록, 혼인출산 공제, 가업승계 증여세 과세특례, 증여세 대납 계산 문자열 |
| Tax400 | 주식평가 | 15 | `Tax400`, `Tax400_New`, `Main400`, `Men400` | "비상장주식 평가"·"상장주식 평가"·평가그룹·영업권 평가 문자열 |
| Tax500 | 종합부동산세 | 25 | `Tax500`, `Main500`, `Men500`, `MenView500` | 종합부동산세법 조문(제8·9·10·14조), 주택분·종합합산·별도합산 토지, 세부담상한, 합산배제 임대주택 문자열 |
| Common | 공통(백업·인쇄·주소·은행·국가·자동백업) | 26 | `NEOIC_FORM`(폼 기반 클래스) | 클래스 이름 |
| ComData | 공통 메시지·진행·입력 상자 | 7 | `NeoMessageForm*`, `Progress`, `InputBox`, `UpdateMessage` | 클래스 이름 |
| (루트) | 런처 | `YDdoctor.TaxLauncher` 1 | `TaxLauncher` | 아래 §1 |

(리소스 목록 537행 = Tax100 + Tax200 + Tax300 + Tax400 + Tax500 + Common·ComData + TaxLauncher·Resources·컨트롤·라이선스 항목. 세목 폼 합계 496 + Common 26 + ComData 7 + 기타 8(TaxLauncher, Properties.Resources, 컨트롤 5, exe.licenses) = 537.)

핵심 관찰: 모듈 번호는 100=양도, 200=상속, 300=증여, 400=주식평가, 500=종부세로 모두 **클래스 이름(Main###·Men###·Tax###)과 문자열이 일치**한다. 각 세목은 같은 골격을 가진다. `Tax###`(세목 진입) → `Main###`(메인 화면, 3단계 흐름) → `Men###`(납세자 등록) → `Jasan###`(자산 등록) → `Cal###`(세액 계산) → `ECreate*`/`EReport*`(전자신고 파일 레코드·변환) → `rpt*`/`JPrint`(서식 인쇄). 상속·증여의 메인 화면은 "1. 납세자(수증자) 등록 / 2. 재산 등록 / 3. 세액 계산"의 3단계다 (Main200 "1. 납세자 등록·2. 재 산 등 록·3. 세 액 계 산", Tax300 묶음 "1. 수증자 등록").

## 1. 런처 (`YDdoctor.TaxLauncher`) 

| 항목 | 내용 | 근거 |
|---|---|---|
| 5개 세목 메뉴 | 양도소득세 / 상속세(버튼 "소득세"로 잘려 보임) / 증여세 / 주식평가 / 종합부동산 | [문자열] "양도소득세·소득세·증여세·주식평가·종합부동산", "종합부동산세 메뉴를 닫은 후 전체 백업ㆍ복원" |
| 다른 세목 실행 중 차단 | "다른(양도, 상속, 증여, 주식 등) 프로그램이 실행 중입니다" | [문자열] |
| 개정세법 보기 | 2020~2026 개정사항 PDF (`Form\20XX년개정사항.pdf`) | [문자열] |
| 데이터 관리 | 전체 백업·복원, 데이터 치료, 백업 중 메시지, 최초 실행 준비 | [문자열] "전체 백업·복원", "데 이 터 치 료" |
| 업데이트 | 수동 업데이트, 업데이트 확인, 세목 메뉴를 닫은 후 업데이트 안내 | [문자열] |
| 부가 | 기준시가 조회, 공서식 조회, 사용설명서, 원격지원, 고객센터, 공지사항, 회원정보 수정, 취득박사 요청, 부동산 감정가액 조회 | [문자열] |
| 공지 내용에서 읽히는 기능 연혁 | 주택분·토지분 종합부동산세 계산 메뉴·신고서식 추가, 상속세 전자신고, 증권거래세 전자신고, 신고파일 일괄 생성, 주식 양도 일괄 등록, 재개발·재건축 상가 추가, 개별주택가격·토지공시지가 자동 반영, 양도박사 클라우드 | [문자열] |
| 외부 연동 URL 키 | 홈택스·위택스·국세법령정보·공시가격(realtyprice)·KAB 기준시세 등 URL 설정 키 | [문자열] (URL 값은 기재하지 않음) |
| 로컬 DB | `Data\neoTax.fdb` (Firebird 계열 파일명), 환경 테이블 `ENV` 조회 | [문자열] |
| 분석 제외 | 사용기간·뷰어(보기)/데모 버전 판정 문자열은 라이선스 영역이라 분석하지 않음 | — |

## 2. 양도소득세 (Tax100, 280 클래스)

세목 구조: 양도인(납세자) 등록 → 자산 등록(주택·토지·건물·권리·주식·파생·국외자산 등) → 세액 계산(감면·중과·장기보유특별공제·세율) → 전자신고 파일 생성·서식 인쇄. 자산 등록 폼이 `Jasan###` 번호 체계로 자산유형별로 나뉜다.

[문자열] 근거 묶음 요약 (T100): 양도유형/취득유형, 주식종류코드(21~71: 중소기업 소액주주 10%, 중소기업외 20·25% 등), 국가 코드표(소재지국), ISIN, 양도가액·필요경비·양도차익·양도소득금액·감면소득금액, 환산취득가액, 취득실가를 모르는 경우, 장기보유특별공제(3년 10% ~ 15년 45%, 10년 50% 등), 비사업용토지, 1세대2·3주택, 고가주택, 미등기, 국외전출, 관리처분계획인가 전·후 및 청산금(재개발 입주권), 파생상품(콜·풋옵션, 차액결제, 워런트, 코스피), 양도자산별 세율(소득세법 제104조: 1년·2년 미만 보유, 조정대상지역 주택, 미등기, 비사업용 10% 가산, 파생상품, 국외자산, 대주주 주식), 미분양주택 과세특례(조특법 제98조), 신고서 Head 레코드(자료구분·서식코드·세목코드 등 1~17항목), 위임장/세무대리인, 증권거래세.

### 2.1 메뉴·진입·목록

| 폼 클래스 | 화면/기능 | 근거 |
|---|---|---|
| `Tax100`, `Main` | 양도소득세 진입 폼 / 메인 화면 | [이름] [문자열] 모듈 최상위 |
| `Men100`, `Men100All` | 양도인(납세자) 등록·목록 메인 | [이름] |
| `Men100Filter`, `Men100Filter_Gam`, `Men100Filter_Jasan`, `Men100Filter_TaxRate` | 목록 필터(감면 / 자산 / 세율 조건) | [이름] |
| `Men100_NapDate` | 납부기한(일자) 입력 | [이름] |
| `MenView`, `OldMenView`, `JasanView` | 납세자·자산 내용 미리보기(구버전 포함) | [이름] [문자열] "삭제한 납세자 정보 복원", Excel 서식 업로드/다운로드 |
| `DEList100` | 삭제·복원 목록(삭제 자료 목록) | [이름] 타 세목 `DEList###`의 "선택한 …정보 복원/완전 삭제" 패턴과 동일 |
| `Env` | 환경 설정(세무대리인 필수정보 등) | [이름] FAQ "환경 설정에서 세무대리인 필수정보 입력" |

### 2.2 양도인·관계인 정보

| 폼 클래스 | 화면/기능 | 근거 |
|---|---|---|
| `JInfo` | 양도인 정보 | [이름] |
| `PInfo`, `Pinfo2`, `Pinfo3`, `Pinfo4`, `Pinfo5`, `Pinfo6`, `PInfoSub`, `PInfoSub2` | 인적사항(양수인·관계인 등 하위 입력) | [이름] |
| `TInfo`, `TInfo2` | 양도(거래) 정보 | [이름] |
| `Yangsu` | 양수인 정보 | [이름] 양수자_성명·납세자번호 문자열 |
| `ChangeInfo`, `CInfo` | 정보 변경 / 공통 정보 | [이름] |
| `Attorney` | 대리인·위임장 | [문자열] 세무대리인·위임장·대리인 |
| `USInfo` | 미국 거주 등 국외 인적사항 | [이름] |
| `RelView`, `RelView2025` | 관계(친족) 확인 표(2025 개정판) | [이름] |
| `PostReg`, `PostReg_old`, `PostView`, `PostView2`, `PostView2_new`, `PostView2_old` | 우편번호·주소 등록/조회 | [이름] |
| `NapChange`, `NapChange_m` | 납부세액 변경(수정) | [이름] 타 세목 "납부세액 수정" |
| `NDateInfo`, `NDateInfo2`, `NDateInfo2_JasanFor` | 납기·신고 일자 정보(국외자산용 포함) | [이름] |
| `InputYear`, `InputSaleDate`, `InputGosiDate` | 연도 / 양도일 / 고시일 입력 | [이름] |

### 2.3 자산 등록 (`Jasan###`)

| 폼 클래스 | 화면/기능 | 근거 |
|---|---|---|
| `Jasan`, `JasanInfo`, `JasanConfirm`, `JasanGbase` | 자산 등록 기본·정보·확인·기준 | [이름] |
| `Jasan103`, `Jasan103_Sub`, `Jasan103_Sub2`, `Jasan104`, `Jasan104_Sub`, `Jasan104_Sub2`, `Jasan109`, `Jasan110`, `Jasan112` | 자산유형 103~112 입력(토지·건물류 추정) | [이름] 유형 미확정 |
| `Jasan121`, `Jasan121Ju`, `Jasan122`, `Jasan123`, `Jasan123Cal`, `Jasan123Cal_2020`, `Jasan123Jasan`, `Jasan123Ju` | 자산유형 121~123(주식 `Ju` 포함 추정), 양도가액·세액 계산 하위 폼 | [이름] 추정 |
| `Jasan153`, `Jasan153_`, `Jasan154`, `Jasan154_`, `Jasan155`, `Jasan155_`, `Jasan157`, `Jasan157_`, `Jasan159`, `Jasan159_`, `Jasan161`, `Jasan161_`, `Jasan162`, `Jasan162_`, `Jasan163`, `Jasan163_2`, `Jasan169`, `Jasan171`, `Jasan172`, `Jasan173`, `Jasan173_ChkInfo`, `Jasan174`, `Jasan174_`, `Jasan175`, `Jasan175_`, `Jasan181`, `Jasan191_`, `Jasan192_` | 자산유형 153~192 입력(부동산·권리·상가·재개발 입주권 등). `_` 접미사는 구/보조판 추정. 이 묶음 문자열: 취득 거래원인, 환산취득가액, 관리처분인가일 가액, 기존 토지·건물 필요경비, 청산금, 상가/주택 안분 | [문자열] (Jasan153·161·171·175·181 5종 묶음; 문자열은 묶음 단위) [이름] |
| `JasanFOR`, `JasanFOR2`, `JasanFOR_BuyType`, `JasanFOR_GOSI`, `JasanFOR_GOSI2`, `JasanFOR_GOSIDATE`, `JasanFOR_JUSE` | 국외자산(FOR) 등록: 취득유형, 고시일, 주식 | [이름] |
| `Jasan_Anbun`, `Anbun`, `Anbun_TInfo` | 토지·건물 안분(양도가액 안분) | [이름] [문자열] "양도가액 - 토지 양도가액" 계산식 |
| `Jasan_PartBuy`, `PartBuy`, `PartBuy_GBuyInfo`, `PartBuy_GBuyInfo_GInfo`, `PartBuy_GBuyInfo_TInfo`, `PartBuy_GInfo`, `PartBuy_Notice`, `PartBuy_TBuyInfo`, `PartBuy_TInfo` | 분할 취득(일부 취득) 입력 | [이름] |
| `Lot`, `Lot2`, `JusikAll`, `MessageJusik`, `MessageCategory` | 주식 로트(여러 건) 일괄 등록, 안내 메시지 | [이름] 공지 "주식 양도 일괄 등록 개선" |
| `JIBUNCheck` | 지번 확인 | [이름] |

### 2.4 세액 계산·감면·중과

| 폼 클래스 | 화면/기능 | 근거 |
|---|---|---|
| `Cal100`, `Cal100e`, `Cal100g`, `Cal100gr`, `Cal100m`, `Cal100me`, `Cal100_2020`, `Cal100m_2020`, `Cal100_JIe`, `Cal100m_e`, `Cal100m_JIe`, `Cal100g_JI`, `Cal100gr_e` | 세액 계산 화면(양도세 / 지방소득세 `JI`, `e`=전자신고 연계 추정, `m`=월(예정?) 추정) | [이름] 지방소득세 별도 신고 문구([문자열], 런처 FAQ) |
| `Cal100gr_2018`, `Cal100gr_2018_e`, `Cal100gr_2019`, `Cal100gr_2019_e`, `Cal100gr_2020`, `Cal100gr_2020_e`, `Cal100gr_2021`, `Cal100gr_2021_e`, `Cal100gr_2023`, `Cal100gr_2023_e`, `Cal100gr_2024`, `Cal100gr_2024_e`, `Cal100gr_2025`, `Cal100gr_2025_e`, `Cal100gr_2026`, `Cal100gr_2026_e` | 귀속연도별 세액계산 화면(2018~2026, 2022 없음) — 연도별 세법 분기 단서 | [이름] 개정 연도 단위 클래스 분리 |
| `Cal100_Hando`, `Cal100_Hando_2025` | 한도(감면 한도 등) 계산 | [이름] |
| `Cal100_Notice`, `Cal100_Notice2`, `Cal100_Notice2_2025` | 계산 중 안내 | [이름] |
| `CalPopup`, `CalPopup_JU`, `CalLog` | 계산 상세 팝업(주식), 계산 로그 | [이름] |
| `Gam102`, `GamView`, `GamAlert` | 감면 입력/조회/경고 | [이름] |
| `HighInfo`, `HighInfo_Check`, `HighInfo_Geju`, `HighInfo_Geju_Jae`, `HighInfo_Jae`, `HChkInfo`, `HChkInfo_New` | 고가주택·거주(Geju)·재건축(Jae) 판정 정보와 확인 | [이름] [문자열] "고가주택" |
| `ChkInfo`, `ChkInfo2`, `ChkInfo3`, `ChkInfo_2`, `ChkInfo2_2`, `ChkInfo_Ju` | 조건 확인(비과세·중과 판정 체크) | [이름] |
| `Jojung2001`, `Jojung2002`, `Jojung2003`, `Jojung2010`, `Jojung2015`, `Jojung2016`, `Jojung2023`, `Alert_Jojung` | 조정대상지역 조회·안내(연도별 지정 기준) | [이름] [문자열] "조정대상지역 조회(홈택스)" |
| `neoAddTax`, `neoAddTaxII`, `neoAddTax0701`, `neoAddTax200101` | 가산세 계산(적용 시점별) | [이름] |

### 2.5 조회 보조 화면

| 폼 클래스 | 화면/기능 | 근거 |
|---|---|---|
| `AptView`, `AptView2`, `AptView_New`, `AptView_Alert`, `NtsAPT` | 공동주택(아파트) 기준시가 조회 | [이름] [문자열] 아파트 기준시가 조회 |
| `NtsView_2`, `NtsView_4`, `NtsView_5`, `NtsView_6`, `NtsView_10` | 국세청 기준시가 조회(유형별) | [이름] |
| `CityInfo`, `CityInfo_JU`, `CityInfo_JU2022`, `SiGunView`, `DongView` | 시군구·동 선택, 지역 정보(주식 포함) | [이름] |
| `GolfView`, `GunView`, `RoofView`, `SwsView`, `YongdoView`, `GujoView` | 골프장·군 / 지붕 / 용도 / 구조 코드 조회 | [이름] 상속세 `ExpLifeView` 계열 코드 표 |
| `OutCountry`, `HelpCType`, `HelpDlg`, `OldBase` | 국가 선택 / 도움말(코드 유형) / 구 기준 | [이름] |

### 2.6 신고 파일·인쇄

| 폼 클래스 | 화면/기능 | 근거 |
|---|---|---|
| `ECreate201`~`ECreate230` (30개: 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230) | 양도소득세 전자신고 파일 서식별 레코드 생성 | [문자열] ECreate201 포함 묶음: "신고서 Head 레코드", "1.자료구분 2.서식코드 3.납세자ID 4.세목코드 5.신고구분코드 … 17.지급년월" |
| `ECreate201_ji`, `ECreate202_ji`, `ECreate203_ji`, `EReport2_ji` | 지방소득세 전자신고 레코드·변환 | [이름] |
| `EReport2` | 전자신고 파일 변환·오류 확인 | [이름] |
| `GRCreate101`, `GRCreate102`, `GRCreate103`, `GRCreate201`, `GRCreate202`, `GRReport` | 증권거래세 전자신고 레코드 및 변환 (양도자·양수자 납세자번호·주식수·양도가액·면제코드) | [문자열] GRCreate101·201·GRReport·Gam102 묶음 |
| `FormPrn`, `GrRpt1`, `GrRpt2`, `JuPrnEtc`, `JuPrnEtc_2020`, `rptDlgPDF` | 서식 인쇄·PDF 저장(주식 서식 포함) | [이름] |

### 2.6a 기타 (§2.1~2.6에 넣지 못한 폼)

| 폼 클래스 | 화면/기능 | 근거 |
|---|---|---|
| `BankCode` | 은행 코드 선택(환급·납부 계좌) | [이름] |
| `PyungInfo` | 평가(Pyung) 정보 입력 | [이름] |
| `SILGAInfo`, `SILGAInfo_New` | 실지거래가액(실가) 입력(신판 포함) | [이름] [문자열] 실지거래가액·취득실가 |

ECreate 전체 이름(전자신고 레코드 생성 폼, 위 §2.6 근거 동일): `ECreate201, ECreate202, ECreate203, ECreate204, ECreate205, ECreate206, ECreate207, ECreate208, ECreate209, ECreate210, ECreate211, ECreate212, ECreate213, ECreate214, ECreate215, ECreate216, ECreate217, ECreate218, ECreate219, ECreate220, ECreate221, ECreate222, ECreate223, ECreate224, ECreate225, ECreate226, ECreate227, ECreate228, ECreate229, ECreate230` — 문자열은 201 묶음만 읽었고 나머지는 번호 규칙(서식별 1개)에 따른 추정.

### 2.7 경고·안내 팝업

`Alert3`, `Alert4`, `Alert_BuyError`(분석 제외: 라이선스), `Alert_CDcloud`, `Alert_Jojung`(§2.4), `Alert_Notice`, `Alert_Notice2`, `Alert_Notice3`, `Alert_Notice4`, `Alert_Notice5`, `Alert_Notice5_1`, `Alert_Notice5_2`, `Alert_Notice5_2023`, `Alert_Notice5_3`, `Alert_Notice5_4`, `Notice`, `ggWarning`, `tgWarning`, `HapsanWarning`(합산 경고), `RestoreBeep`, `Alert_CDcloud`(클라우드 연동 안내), `Alert_Jojung`. 근거: [이름]. `Alert_Notice5*` 계열은 연도·개정별 공지 팝업으로 추정.

## 3. 상속세 (Tax200, 88 클래스)

[문자열] 근거 묶음 요약 (T200a~e): 재산 구분코드(상속재산·상속개시 전 처분재산·증여재산가산(상속인/상속인 외/창업자금/가업승계/거주자/비거주자)·비과세(금양임야·공공단체 유증)·과세가액불산입(장애인신탁·공익신탁·공익법인 출연)), 평가기준코드(기준시가 등·보충적 평가·저당권 등 평가특례·유사재산 매매사례가액·감정가액·수용보상가액·경매공매가액), 아파트·상가 기준시가, 서화·골동품 명세, 비상장·상장·협회등록 주식 평가, 국외자산, 채무 종류(금융·사업상·개인사채·저당권·기타), 상속공제 한도, 가업상속공제 신고서(최대 10개 가업, 가업영위기간, 중견기업 여부), 영업권, 단기재상속 세액공제, 증여세액 공제, 외국납부세액공제 신청서, 신고세액공제, 연부연납 허가신청서(일반·가업, 회차별 가산금), 물납(대상 재산 명세), 납세담보제공서, 상속인별 상속세 배분, 홈택스 전자신고 파일 변환(Head 레코드, 상속인/추정상속재산/소명 레코드).

| 폼 클래스 | 화면/기능 | 근거 |
|---|---|---|
| `Tax200`, `Main200` | 상속세 진입 / 메인(1 납세자 등록·2 재산 등록·3 세액 계산 + 자료 복원·백업·환경설정·공서식·도움말) | [문자열] |
| `Men200`, `Men200View`, `Men200Filter`, `Men200Filter_Jasan` | 납세자(상속인) 등록·목록·필터, 편집제한, 복사본 | [문자열] "납세자 등록", "「편집제한」" |
| `JInfo200` | 피상속인·상속인 정보 | [이름] |
| `HeirsChecklist`, `MemberCode` | 상속인 체크리스트 / 관계 코드 | [이름] |
| `Jasan200`, `Jasan200Div`, `Jasan201`, `Jasan203`, `Jasan204`, `Jasan206`, `JasanView200`, `SelectJasan200`, `LoadJasan200`, `JasanCode` | 재산 등록(유형 코드·분할·선택·불러오기·미리보기): 건물·토지·아파트·상장/비상장·국외·기타 | [문자열] |
| `Jang200`, `Jang200_2` | 채무·장례비 등 공제 입력 | [이름] [문자열] 채무종류 |
| `ArtList` | 서화·골동품 목록(작품코드·작가·제작년도) | [문자열] |
| `JibunInput`, `JibunEdit`, `JibunList`, `JibunAlert` | 상속재산별 지분율 입력·수정·목록·경고 (전체지분/상속지분) | [문자열] "전체지분이 입력되어 있지 않습니다", 상속재산별 지분율 입력(런처 FAQ) |
| `Gamjung`, `Gong200`, `ExpLifeView` | 감정가액 / 공제 / 기대여명 표(추정) | [이름] |
| `LandCode`, `SemokCode`, `SpecialCode`, `HelpCodeView` | 지목·세목·특례 코드표 및 도움말 | [문자열] 지목(잡종지·공장용지 등) |
| `GInfo` | 가업 정보 | [이름] 가업상속 문자열 |
| `Cal200`, `Cal200e` | 상속세 세액 계산 / 전자신고 연계 | [문자열] "상속세를 계산하고 있습니다" |
| `VicariousCalc` | 대납(대신 납부) 계산 | [이름] |
| `NapChange`, `NapEtc`, `InputSinDate`, `Alert_Singo`, `Alert_SangJung200` | 납부세액 변경 / 기타 납부 / 신고일 입력 / 신고·상정 경고 | [이름] |
| `Chemu200`, `rptFormB_Chemu` | 채무 서식(상속세 채무 명세서) | [이름] |
| `DEList200` | 삭제 자료 복원 목록 | [이름] |
| `EReport200` | 전자신고 파일 변환 | [이름] [문자열] "전자신고 파일변환 오류 확인" |
| `ECreate2_1_01`, `ECreate2_1_02`, `ECreate2_1_03` | 상속세 전자신고 레코드(그룹 1: 3종) | [문자열] ECreate2_1_01 |
| `ECreate2_2_01`, `ECreate2_2_02`, `ECreate2_2_03`, `ECreate2_2_04`, `ECreate2_2_05`, `ECreate2_2_06`, `ECreate2_2_07`, `ECreate2_2_08`, `ECreate2_2_09`, `ECreate2_2_10`, `ECreate2_2_11`, `ECreate2_2_12`, `ECreate2_2_13`, `ECreate2_2_14`, `ECreate2_2_15`, `ECreate2_2_16`, `ECreate2_2_17`, `ECreate2_2_18`, `ECreate2_2_19`, `ECreate2_2_20`, `ECreate2_2_21`, `ECreate2_2_22`, `ECreate2_2_23`, `ECreate2_2_24` (24종) | 상속세 전자신고 레코드(그룹 2: 상속인·추정상속재산·소명·서화골동품 명세 등) | [문자열] ECreate2_2_11·2_2_24 |
| `rptDlg` | 서식 인쇄 대화상자 | [문자열] "상속세 서식인쇄" |
| `rptFormA`, `rptFormA_20170207`, `rptFormA_20210511`, `rptFormB`, `rptFormC`, `rptFormD`, `rptFormE`, `rptFormF`, `rptFormG`, `rptFormH`, `rptFormI`, `rptFormJ`, `rptFormK`, `rptFormL` | 상속세 서식 A~L(기본 신고서, 채무, 가업상속공제신고서, 연부연납 허가신청서, 물납, 납세담보제공서, 외국납부세액공제신청서 등). 서식 A는 2017·2021 개정판 별도 | [문자열] 연부연납·물납·납세담보제공서·외국납부세액공제 서식 문자열(서식 알파벳별 매핑은 미확인) |

## 4. 증여세 (Tax300, 88 클래스)

[문자열] 근거 묶음 요약 (T300a~e): 수증자 등록, 증여자와의 관계(배우자·직계존속·기타친족), 증여재산 유형(상장·비상장 주식, 서화·골동품, 가상자산, 지상권·전세권·임차권, 대여금, 채무면제, 전환사채, 금전신탁, 건설기계, 미술품 등), 증여재산가산액·가산한 증여재산 산출세액, 기납부세액공제, 외국납부세액공제, 신고세액공제, 연부연납, 분납, 가업승계 증여세 과세특례(가업영위기간, 한도 50억/100억, 신규고용), 증여세 대납 계산(반복계산), 혼인·출산 증여재산공제, 특정법인 초과배당금액(소득세 상당액), 일감몰아주기(수혜법인), 부담부증여(기증여채무 가져오기), 비상장주식 평가서(순자산가액·순손익액·평가차액·영업권·자기주식), 수정신고서·경정청구서·납부서(QR코드), 홈택스 전자신고 레코드(서식 1~13).

| 폼 클래스 | 화면/기능 | 근거 |
|---|---|---|
| `Tax300`, `Main300` | 증여세 진입 / 메인(1 수증자 등록·2 재산 등록·3 세액 계산) | [문자열] |
| `Men300`, `Men300View`, `Men300Filter`, `Men300Filter_Jasan` | 수증자 등록·목록·필터, 공유목록 포함/제외, 편집제한 | [문자열] "수증자리스트", "공유포함/공유제외" |
| `GaInfo`, `GaInfo2`, `Gainfo2_2023`, `GaInfo_2023`, `GaInfo_Delay` | 증여자 정보(2023 개정판, 납부유예 포함) | [이름] [문자열] 증여자 가업영위기간 |
| `ChaInfo2` | 채무 정보(증여채무) | [이름] [문자열] 채무종류코드 01~09 |
| `StartupInfo`, `BusinessLeadDate`, `NewEmployee` | 창업자금 / 사업 개시일(가업영위기간) / 신규 고용 정보 | [이름] [문자열] 창업·가업승계 |
| `DeductionMarryOrChildbirth` | 혼인·출산 증여재산공제 | [문자열] "혼인출산 증여재산공제액 계산명세" |
| `ExcessHelp`, `TaxAnother` | 초과배당 안내 / 증여세 대납(타인 부담) | [문자열] 초과배당금액, 증여세 대납 계산 |
| `Jasan300`, `Jasan301`, `Jasan302`, `Jasan303`, `Jasan304`, `Jasan307`, `Jasan308`, `Jasan309`, `Jasan310`, `Jasan310_Help`, `JasanView300`, `LoadJasan` | 재산 등록(증여재산 유형별 입력·미리보기·불러오기) | [문자열] 재산 등록·재산유형·가상자산 등 |
| `Jasan305`, `Jasan305Jasan`, `Jasan305Jasan_MyStocks`, `Jasan305Sales`, `Jasan305Ju`, `Jasan305Ju_2017`, `Jasan305Pyung`, `Jasan305Pyung_2021`, `Jasan305Pyung_Gun`, `Jasan306`, `Jasan306Ju`, `Jasan306Ju2`, `Jasan306Ju_Info` | 비상장주식 평가 내장(재산 305/306): 순손익액·순자산가액·평가차액·자기주식·영업권, 건물 기준시가 계산 | [문자열] 묶음 T300c (비상장주식 평가조서, 순손익액계산서 등) |
| `Jasan305Cal`, `Jasan305Cal_2014`, `Jasan305Cal_2020`, `Jasan305Cal_2021`, `Jasan305Cal_20210315`, `Jasan305Cal_2024` | 주식평가 계산 폼의 시점별 판(2014/2020/2021/2024 세법 반영) | [이름] 연도별 분기 단서 |
| `JasanSejong`, `JasanSejongAPT` | 세종시 재산 / 세종시 아파트 평가 | [이름] |
| `JusikLot`, `StockList` | 주식 일괄 등록 / 종목 목록(시장구분·종목) | [문자열] "시장구분·종목리스트" |
| `Gam300`, `Cal300_OldGam` | 감정(평가) / 구 감정 계산 | [이름] |
| `Cal300`, `Cal300e1`, `Cal300e2` | 증여세 세액 계산 / 전자신고 연계 | [문자열] 세액계산>가산한증여재산산출세액 등 |
| `Alert_SangJung300`, `InputJDate` | 상정 경고 / 증여일 입력 | [이름] |
| `BankCode300`, `CountryCode` | 은행코드 / 국가코드 | [이름] [문자열] 은행명·은행코드 |
| `Chemu300`, `Chemu300_20190826`, `LoadChemu`, `LoadChemu_20190826` | 채무 입력·불러오기(2019.8.26 개정판 별도) | [이름] |
| `DEList300` | 삭제 자료 복원 목록 | [이름] |
| `EReport` | 전자신고 파일 변환·오류 확인 | [문자열] "국세청 홈택스 증여세 전자신고" |
| `ECreate101`, `ECreate102`, `ECreate103` | 전자신고 레코드 그룹 1(신고서 HEADER 등) | [문자열] ECreate101 |
| `ECreate201`, `ECreate202`, `ECreate203`, `ECreate204`, `ECreate205`, `ECreate206`, `ECreate207`, `ECreate208`, `ECreate209`, `ECreate210`, `ECreate211`, `ECreate212`, `ECreate213`, `ECreate214` (14종) | 전자신고 레코드 그룹 2(채무인수계약서, 서화·골동품, 증여계약서, 비상장 평가조서 등) | [문자열] ECreate206·214 |
| `JPrint`, `rptDlg300`, `rptDlgJu` | 서식 인쇄(증여세 신고서류 PDF, 주식평가 서류) | [문자열] "_증여세_신고서류.pdf", "_비상장주식_평가서류.pdf" |

## 5. 주식평가 (Tax400, 15 클래스)

상속·증여 재산에 들어갈 **주식 1주당 가액**을 상증법 보충적 평가방법으로 산출하고, 상속·증여 재산으로 복사하는 독립 모듈이다. 3단계 흐름: 평가그룹 등록 → 주식 등록 → (영업권) 평가.

[문자열] 근거 (T400/T400b): 비상장주식 평가·상장주식 평가·평가그룹 등록/복원/삭제/복사, 주식평가 데이터를 상속재산(본래·비과세·과세가액불산입)·증여재산에 복사, 일반과세·비과세·과세가액불산입 구분, 영업권(개인/법인; 순손익액 3·2·1년 가중평균; 상증법 시행령 제59조), 데이터 컨버트, 주식·영업권 선택 백업/복원, 뷰어 모드 복원 불가.

| 폼 클래스 | 화면/기능 | 근거 |
|---|---|---|
| `Tax400`, `Tax400_New`, `Main400` | 주식평가 진입 / 신 진입 폼 / 메인(1. 평가그룹 등록 · 2. 주식 등록) + 자료 백업/복원 | [문자열] |
| `Men400` | 평가그룹 등록·검색·고정·복사·삭제 | [문자열] "평가그룹등록/검색/삭제", 그룹번호 |
| `Jasan400`, `Jasan400_New` | 주식(자산) 등록 — 비상장/상장 | [문자열] 비상장주식 등록, 상장주식 등록, 주식순서 고정 |
| `Jasan400_SaleRights` | 영업권 평가(개인/법인) | [문자열] 영업권 평가액, 개인 영업권, 법인 영업권 |
| `Jasan401`, `Jasan402` | 주식 평가 내용(평가조서) / 보조 입력 | [이름] (번호 체계상 401·402는 평가 세부로 추정) |
| `Jasan400toData`, `Jasan400toData2`, `Jasan400toData2_List`, `Jasan400toData2_New` | 평가액을 상속·증여 재산으로 복사 (신고인/수증자 선택) | [문자열] "상속·증여재산에 복사", "신고인 조회" |
| `JasanView400` | 평가 결과 미리보기 | [이름] |
| `DEList400` | 삭제한 평가그룹 복원 목록 | [문자열] "삭제한 평가그룹 정보 복원" |

세 가지 평가 규칙 단서(문자열): 일반 법인 `Max{순손익가치×3 + 순자산가치×2}/5` 계열, 부동산·주식이 총 자산의 80% 이상인 법인, 잔여 존속기한 3년 이내 법인, 사업개시 전·후 3년 미만 법인은 순자산가치 평가(상증법 제54조제4항) — 정확한 식은 단위 B(계산 로직)에서 확인한다.

## 6. 종합부동산세 (Tax500, 25 클래스)

[문자열] 근거 (T500a/b): 주택분·토지분(종합합산·별도합산) 세율, 주택수별 세율(2주택 이하/3주택 등, 2020·2021 이후·2023 이후), 고령자·장기보유자·1세대1주택자 세액공제, 세부담상한비율(2020·2021·2022·2023 이후), 1세대 1주택 특례(혼인·동거봉양), 공동명의 1주택 지분, 합산배제 임대주택(종부세법 시행령 제3조 제1항 각호; 임대사업자 등록·매입임대·공공지원 등), 재산세 계산명세(과세표준·세율), 공제할 재산세액, 농어촌특별세, 수정신고·경정청구, 신고서 항목 1~25 (과세표준, 산출세액, 납부지연가산세, 납부유예, 분납).

| 폼 클래스 | 화면/기능 | 근거 |
|---|---|---|
| `Tax500`, `Main500` | 종합부동산세 진입 / 메인 | [이름] |
| `Men500`, `MenView500`, `Men500View` | 납세자 등록·목록·미리보기 | [문자열] "선택한 납세자 정보 완전 삭제/복원", 납세자 조회 |
| `Jasan500`, `Jasan501`, `Jasan502`, `JasanView500` | 과세물건 등록: 주택(500) / 토지(501 추정) / 합산배제(502 추정) | [문자열] 주택·토지 세부정보, 필지 삭제 |
| `LandCode` | 지목 코드표(운동장·체육용지 등) | [문자열] |
| `SigaView` | 공시지가·공시가격 조회(토지 공시지가 조회 자동 반영) | [문자열] "토지공시지가를 조회하여 자동으로 반영합니다" |
| `RentHouseOut` | 합산배제 임대주택 등록(임대사업자·등록일·임대개시일·유형코드) | [문자열] |
| `RateView500`, `RateView500_2023`, `RateView500_TOJI` | 주택분 세율표(2023 판) / 토지 세율표 | [문자열] "종합부동산세 주택분 세율", 토지분 세율 |
| `RateView501`, `RateView502`, `RateView502_2023`, `RateView503`, `RateView504` | 세액공제표(고령자·장기보유) / 세부담상한비율 / 1세대1주택자 설명 / 재산세 세율표 | [문자열] (표별 매핑은 이름 추정) |
| `Cal500`, `Cal500e`, `Cal500Compare` | 세액 계산 / 전자신고 연계 / 지분·2안 비교 계산 | [이름] [문자열] 세부담상한 초과세액 계산 |
| `rptDlg500` | 서식 인쇄(종합부동산세 신고서, 과세대상 물건명세서, 세부담 상한 초과세액 계산명세서, 재산세 계산명세서) | [문자열] T100c 묶음에도 같은 서식 제목 존재 |
| `DEList500` | 삭제 자료 복원 | [이름] |

참고: 종합부동산세 신고서·과세대상 물건명세서의 서식 제목 문자열이 Tax100 쪽 묶음(GRCreate/GRReport/Gam102 포함 묶음)에서도 검출됐다. 해당 문자열이 어느 클래스의 것인지는 REA 표로 귀속 불가 → 미확인.

## 7. 공통 (Common 26, ComData 7, 컨트롤)

| 클래스 | 기능 | 근거 |
|---|---|---|
| `Common.NEOIC_FORM` | 모든 폼의 기반 클래스(리사이즈 설정 등) | [이름] 런처 폼이 상속 |
| `Common.AddressEditor`, `Common.Bankno`, `Common.CountryList`, `Common.VirtualAssetsCode` | 주소 편집 / 은행번호 / 국가 목록 / 가상자산 코드 | [이름] |
| `Common.Alert_Alter`, `Common.Alert_EReportAndPDF`, `Common.EReport_Error` | 공통 경고, 전자신고·PDF 안내, 전자신고 오류 | [이름] |
| `Common.autoBackup`, `Common.BackupAndRestore` | 자동 백업 / 백업·복원 | [이름] [문자열] 백업 문구 |
| `Common.GJasanInput` | 공통 자산 입력 | [이름] |
| `Common.Intro`, `Common.StartProgress`, `Common.StartProgress2` | 인트로 / 시작 진행 | [이름] |
| `Common.PrintPreview` | 인쇄 미리보기 | [이름] |
| `ComData.InputBox`, `ComData.NeoMessageForm`, `ComData.NeoMessageFormMove`, `ComData.NeoMessageFormVertical`, `ComData.Progress`, `ComData.UpdateMessage` | 입력 상자 / 메시지 상자 3종 / 진행 / 업데이트 메시지 | [이름] |
| `UserControl.MultiEdit`, `UserControl.NeoGrid`, `UserControl.neoNavigator`, `NeoControl.NeoButton`, `NeoControl.NeoLabel` | 사용자 컨트롤(다중 입력, 그리드, 내비게이터, 버튼, 라벨) | [이름] |
| `YDdoctor.Properties.Resources`, `YDdoctor.exe.licenses` | 리소스 / 라이선스 컴포넌트 목록 | [이름] |

DevExpress UI 컴포넌트와 `ComData.ClientDataSet`/`StringList`(자체 데이터셋)를 사용한다(런처 call_edges에서 확인).

### 분석 제외(라이선스)

`Common.Reg`, `Common.Reg2`, `Common.TimeReg`, `Common.Demo`, `Common.BuyAlert`, `Common.BuyBankAlert`, `Common.BuyBankAlert2`, `Common.RegisterUser`, `Common.RegisterUser_CDcloud`, `Common.Login`, `Common.Alert_LeftDays`, `ComData.RegConfirmMessage`, `Tax100.Alert_BuyError`. 클래스 이름만 기록하고 내용은 읽지 않았다.

## 8. 클래스 인벤토리 점검

- Tax100 280 / Tax200 88 / Tax300 88 / Tax400 15 / Tax500 25 / Common 26 / ComData 7 / 기타 8 = 537. 라이선스 제외 13개(§7).
- 537개 클래스 이름 모두 본 문서에 등장함을 스크립트로 대조했다(누락 0).

## 9. 사용한 Evidence ID

런처·메인 클래스 묶음(TaxLauncher, Main 5종): ev_f9d9ce2c3f3d0d657a1e2060ab8283b673c4b6da1854c7728068b36e17cf5cc5(TaxLauncher), ev_88f8b842f2e0d26f91c5fa93ecd667df7780f6ac351f001f1d8df6c97d95f9c7(Main 5종+TaxLauncher). 모듈별 managed-members 묶음(parent ev):
- Tax400: ev_98460f6cff407417e4f2c1d4e58e098ed736f732c704785f93b03075ae1badf1, ev_f2b136a67b87debcdc48c78aabc07ae01f96e492339b2e641fab8887654280e9
- Tax500: ev_ff7944a1b53ecca2190b6b68498761d4ce6528896d05dd2828af3b5ba7d11737, ev_a4ff191dc1e0f5f840f8c0630478e210c57e6a2fb0f89d42fa9101e5a2283743
- Tax200: ev_6541f0476145f5b7936e4ea1fa024cee788a2d7d48c48661f38473b5c484ed23, ev_81db19010326ad7ff48db2085b882dd45d08e1d845ec5f77c9923b3d85b59bb2, ev_49f8e015d0727b79a00f37abcc50827b84c5699ec755b2fcd9ba3b725b4bd8c5, ev_568876553aebf3eeb3a59ad4f53c412553f8d9b585634a201df237a27609428d, ev_97eb2d1c6f09657f26d3969c14d9fd7d5da5390e149c80179b73d0021a7a2453
- Tax300: ev_5beb6b564126b791714306230fb5f3c93c5cf4f868fab37fa935be257b39170a, ev_6e2d39ef9810ef76147324d882f56b85366d47a217fd2e72cb3f156a7207c34d, ev_8bf86bd160fedb31031b27249b3ce1581069c21961b7238015236faf5d5d1470, ev_13fa1e5a8446104d7560a6897cd8633e4414f6319be9d6653285b2fb1c053733, ev_b688cb94c807eddb1a189b2d476bcb6511e215d7f21e90e724f74d83e3f9aa0a
- Tax100: ev_c1b04c1ab2ffec5357df0a0f7ddcc786c5f09735028fef2a009f8521dddb8345, ev_6b6f4c16777c8cc1f34b54be6fa8d562748ea3ea23e8ed00bdd89f3277951e12, ev_6c24810ca019b70d4660ad7d211beafc9db35b36395da28eede5751ae225adbd, ev_884bcd100ad54b9fac06aab73764a6aa75f42553f2a831464c69c580fb67ca06
- 보조(문자열 열람은 로컬 증거 번들 내보내기 파일에서 수행): ev_ccb741b1…(inspect_managed_artifact 요약).

## 10. 확인한 클래스 목록 (문자열을 읽은 클래스)

- 런처·메인: TaxLauncher, Tax100.Main, Tax200.Main200, Tax300.Main300, Tax400.Main400, Tax500.Main500
- Tax100(23): Men100, Tax100, Yangsu, JInfo, PInfo, TInfo, Env, DEList100, Men100All, MenView, JasanView, Gam102, GRCreate101, GRCreate201, GRReport, HighInfo, ChkInfo, NtsView_2, neoAddTax, Alert_Notice5_2023, Alert_Jojung, Attorney, Lot, FormPrn, EReport2, ECreate201, Jasan153, Jasan161, Jasan171, Jasan175, Jasan181
- Tax200: 전체 14+14+14+14 + (JInfo200, LandCode, Main200, Men200, Tax200, ECreate2_1_01, ECreate2_2_11, ECreate2_2_24) = 8개 묶음 포함 약 64개
- Tax300: 11+12+13(Jasan303~306 등) + 22(T300d) + 8(T300e) = 약 66개
- Tax400: 15개 전체
- Tax500: 25개 전체
- 정적 인벤토리(이름만): 위 외 모든 클래스.

## 11. 미확인 목록

1. **클래스별 문자열 귀속**: REA user_strings는 선언 클래스 없이 묶음 단위로 나온다. 개별 폼의 제목·버튼 문구는 `InitializeComponent` 단위 분석(단위 B/C)에서 확정해야 한다. 이 문서의 폼별 한 줄 설명 다수는 [이름] 추정이다.
2. **Tax100 미조사 묶음**: 다음 묶음은 메타데이터 크기 한도(64MB)로 거절됐고, 이름 추정으로만 분류함 — Cal100 계열 11종(Cal100, Cal100gr_2026, Cal100_Hando, Jojung2023, JusikAll, PartBuy, RelView2025, Jasan103, Jasan104, Cal100m, Cal100g), Jasan121/123/JasanFOR/JasanFOR_GOSI/Jasan_Anbun/OldBase/USInfo(일부 USInfo 포함), Alert_Notice*/Cal100gr_연도별/AptView/CityInfo/ECreate202~230 등 대다수 소형 폼.
3. **Tax300**: Cal300 등의 일부 대형 묶음은 22개 단위로 요청 시 거절되어 11~13개로 나눠 재조회함. Jasan305Cal_2014/2020/2021/20210315, Jasan305Pyung_2021, Jasan305Ju_2017, LoadChemu, Chemu300_20190826 등은 이름만 확인.
4. **번호 체계**: `Jasan1xx`(양도) 번호별 자산유형(예: 103·104·109·110·112=?)의 확정 매핑, `Jasan200~206`(상속), `Jasan300~310`(증여), `Jasan400~402`(주식)의 번호↔재산유형 대응.
5. **상속 서식 A~L**: 각 `rptForm*`가 어떤 법정 서식인지(알파벳별) 미확정. 연부연납 허가신청서·물납·납세담보제공서·외국납부세액공제신청서 등이 존재함만 확인.
6. **RateView501~504 / 502_2023**: 세액공제표·세부담상한·재산세 세율·1세대1주택자 설명 중 어느 표인지 개별 매핑 미확인.
7. **GR* 계열**: `GRCreate*`/`GRReport`가 증권거래세 신고로 보이나(양도자·양수자·주식수 문자열), 종합부동산세 신고서 서식 제목이 같은 묶음 주변에서 검출되어 일부 서식의 귀속은 불확실.
8. **Tax100의 `m`/`e`/`gr`/`g` 접미사 의미**(월/전자신고/…)는 추정.
9. **전자신고 레코드 레이아웃**(필드 길이·순서): 이 단계에서는 라벨만 확인함. 레이아웃은 별도 분석 단위 대상.
10. **세액 계산 로직 자체**(세율 표 적용, 공제 한도, 연도별 분기)는 단위 A 범위 밖. `Cal*` 클래스와 `_연도` 접미사 클래스 쌍이 세법 개정 연도별 분기점이라는 단서만 기록.
11. 런처에서 URL·키 문자열은 확인했으나 값은 문서화하지 않음.
