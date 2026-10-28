# 환경 고정 (빈칸 양식)

## 양도박사
- 버전:
- 빌드:
- 세법 기준일(도움말 > 정보):
- 설치 경로: `C:\Neoic\Tax2019\YDdoctor.exe` (창 제목 "양도박사2026", 창 클래스 `WindowsForms10.Window.8.app.0.2dac507_r7_ad1` → WinForms, uia 우선)
- 버전 표시: ~~v.20261021.001 (첫 화면, 2026-10-22)~~ → ~~v.20261023.002 (2026-10-24 자동 업데이트, U6)~~ → **v.20261028.002** (2026-10-28 23:14 자동 업데이트, U6 재발, `FileUpdate.ini` Rev 3752, `YDdoctor.exe` 38,362,032 B). C000은 옛 버전, C001 자산 입력·계산은 20261023.002, C001 양수인·세액부터 20261028.002
- 라이선스: **데모버전 — 인쇄·전자신고 미지원** (첫 화면 문구). 데모로 진행하고 출력 분석은 보류 (`docs/decisions.md` "라이선스·출력 분석")
- EULA 자동화 조항: 없음 (사용자 확인 2026-10-22)
- 첫 화면 세목 버튼: 양도소득세 · 상속세 · 증여세 · 주식평가 · 종합부동산세 (모두 분석 대상)
- 실행 권한: 기본 실행은 **관리자 권한** → 일반 권한 분석 코드에서 컨트롤 읽기 접근 거부, `PrintWindow` 실패(UIPI). **`__COMPAT_LAYER=RunAsInvoker`로 일반 권한 실행**하면 정상 동작하고 로그인도 됨(2026-10-22 확인). 설치 폴더는 일반 권한으로 쓰기 가능
- 조작 방식: pywinauto **uia** (메인 화면 Button 26개 이름·좌표 노출. 메뉴바 없음, 버튼으로 화면 이동). 하위 화면은 DevExpress WinForms
- 화면 캡처: 창을 맨 앞으로 가져온 뒤 DPI 인식을 켠 화면 복사(`ImageGrab`/`CopyFromScreen`). 가려진 창은 위에 있는 창이 찍힘. 배율 약 175%. 디스플레이 보호(affinity) 0

## Windows / Python
- Windows 버전:
- Python 버전:
- Python 비트(32/64):
- ODBC 드라이버 목록:

## 데이터 폴더 위치
- 후보: `C:\Neoic\Tax2019\Data` (설치 폴더 하위: BACKUP, Base, Data, form, ko, pdf, Rep, Rep200, Rep300, Rep500, SKIN). W4 ProcMon으로 확정 전까지 탐색 전후 해시 비교 대상으로만 쓴다

## 금지 메뉴
<!-- 불릿 한 줄 = 메뉴 텍스트 하나 (부분일치로 차단). 기본값은 전체구조 §5-6, 사람이 확정 -->
- 전송
- 제출
- 삭제
- 업데이트
- 결제
- 라이선스
- 복원
- 초기화
- 양도박사 등록
- 원격지원
<!-- 양도박사 등록·원격지원: 사용자 지정 2026-10-22. "등록"만 단독으로 넣지 않는다(납세자·물건 등록 같은 입력 메뉴까지 막힘) -->

## 국세청 명세 출처 URL
-

## 환경 점검 출력
<!-- python tools/check_env.py 출력을 아래에 붙인다 -->

```
[OS/Python]
  OS: Windows 11 10.0.26200
  Python: 3.14.7 (64비트)
[ODBC 드라이버]
  - SQL Server
  - Microsoft Access Driver (*.mdb, *.accdb)
  - Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)
  - Microsoft Access Text Driver (*.txt, *.csv)
  - Microsoft Access dBASE Driver (*.dbf, *.ndx, *.mdx)
[도구 존재 여부]
  psr.exe: C:\WINDOWS\system32\psr.exe
  procmon.exe: 없음
  HxD.exe: 없음
[양도박사 창 컨트롤 노출]
  [uia] 창: '양도박사2026' (hwnd=460136)
  [uia] 컨트롤 요약: {'Button': 26, 'Text': 19, 'Pane': 11, 'ScrollBar': 1, 'TitleBar': 1, 'MenuBar': 1, 'MenuItem': 1}
Control Identifiers:

Dialog - '양도박사2026'    (L91, T91, R1839, B1237)
['Dialog', '양도박사2026', '양도박사2026Dialog']
child_window(title="양도박사2026", auto_id="TaxLauncher", control_type="Window")
   | 
   | Pane - ''    (L84, T84, R1846, B1244)
   | ['Pane', '        현재 프로그램은 『데모버전』이며, 인쇄·전자신고가 지원되지 않습니다.Pane', 'Pane0', 'Pane1']
   | 
   | Pane - 'System.Drawing.Bitmap'    (L126, T336, R1444, B901)
   | ['System.Drawing.Bitmap', 'Pane2', 'System.Drawing.BitmapPane']
   | child_window(title="System.Drawing.Bitmap", auto_id="pictureEdit4", control_type="Pane")
   | 
   | Static - '최신 버전입니다. (v.20261021.001)'    (L368, T285, R734, B320)
   | ['Static', '최신 버전입니다. (v.20261021.001)', '최신 버전입니다. (v.20261021.001)Static', 'Static0', 'Static1']
   | child_window(title="최신 버전입니다. (v.20261021.001)", auto_id="lbNewVersion", control_type="Text")
   | 
   | Button - '업데이트 확인'    (L760, T284, R902, B319)
   | ['업데이트 확인', '업데이트 확인Button', 'Button', 'Button0', 'Button1']
   | child_window(title="업데이트 확인", auto_id="btn_update_check", control_type="Button")
   | 
   | Button - '종합부동산세'    (L1190, T931, R1444, B1071)
   | ['종합부동산세', '종합부동산세Button', 'Button2']
   | child_window(title="종합부동산세", auto_id="bTax500", control_type="Button")
   | 
   | Button - '원격지원'    (L121, T259, R354, B320)
   | ['원격지원Button', '원격지원', 'Button3']
   | child_window(title="원격지원", auto_id="btnRemote", control_type="Button")
   | 
   | Button - '주식평가'    (L924, T931, R1178, B1071)
   | ['주식평가', '주식평가Button', 'Button4']
   | child_window(title="주식평가", auto_id="bTax301", control_type="Button")
   | 
   | Button - '증 여 세'    (L658, T931, R912, B1071)
   | ['Button5', '증 여 세', '증 여 세Button']
   | child_window(title="증 여 세", auto_id="bTax300", control_type="Button")
   | 
   | Button - '상 속 세'    (L392, T931, R646, B1071)
   | ['상 속 세', '상 속 세Button', 'Button6']
   | child_window(title="상 속 세", auto_id="bTax200", control_type="Button")
   | 
   | Button - '양도소득세'    (L126, T931, R380, B1071)
   | ['양도소득세Button', 'Button7', '양도소득세']
   | child_window(title="양도소득세", auto_id="bTax100", control_type="Button")
   | 
   | Pane - 'panelControl4'    (L1465, T250, R1826, B1104)
   | ['panelControl4Pane', 'Pane3', 'panelControl4']
   | child_window(title="panelControl4", auto_id="panelControl4", control_type="Pane")
   |    | 
   |    | Pane - 'imageSlider1'    (L1470, T947, R1811, B1061)
   |    | ['imageSlider1', 'imageSlider1Pane', 'Pane4']
   |    | child_window(title="imageSlider1", auto_id="isBanner", control_type="Pane")
   |    | 
   |    | Pane - 'panelControl11'    (L1794, T697, R1812, B758)
   |    | ['panelControl11', 'Pane5', 'panelControl11Pane']
   |    | child_window(title="panelControl11", auto_id="panelControl11", control_type="Pane")
   |    | 
   |    | Button - '회원정보 수정'    (L1470, T625, R1811, B686)
   |    | ['Button8', '회원정보 수정Button', '회원정보 수정']
   |    | child_window(title="회원정보 수정", auto_id="bUserModify", control_type="Button")
   |    | 
   |    | Pane - 'panelControl10'    (L1794, T768, R1812, B829)
   |    | ['Pane6', 'panelControl10', 'panelControl10Pane']
   |    | child_window(title="panelControl10", auto_id="panelControl10", control_type="Pane")
   |    | 
   |    | Pane - 'panelControl9'    (L1794, T840, R1812, B901)
   |    | ['Pane7', 'panelControl9', 'panelControl9Pane']
   |    | child_window(title="panelControl9", auto_id="panelControl9", control_type="Pane")
   |    | 
   |    | Button - '주요 업데이트 내역'    (L1470, T410, R1811, B471)
   |    | ['Button9', '주요 업데이트 내역Button', '주요 업데이트 내역']
   |    | child_window(title="주요 업데이트 내역", auto_id="update", control_type="Button")
   |    | 
   |    | Button - '입금 계좌번호'    (L1470, T840, R1811, B901)
   |    | ['입금 계좌번호', '입금 계좌번호Button', 'Button10']
   |    | child_window(title="입금 계좌번호", auto_id="btnBankNo", control_type="Button")
   |    | 
   |    | Button - '전체 백업·복원'    (L1470, T697, R1811, B758)
   |    | ['전체 백업·복원', '전체 백업·복원Button', 'Button11']
   |    | child_window(title="전체 백업·복원", auto_id="bBackup", control_type="Button")
   |    | 
   |    | Button - '기준시가 조회'    (L1470, T481, R1811, B542)
   |    | ['기준시가 조회Button', '기준시가 조회', 'Button12']
   |    | child_window(title="기준시가 조회", auto_id="bNtsView", control_type="Button")
   |    | 
   |    | Button - '양도박사 등록'    (L1470, T768, R1811, B829)
   |    | ['양도박사 등록', 'Button13', '양도박사 등록Button']
   |    | child_window(title="양도박사 등록", auto_id="bReg", control_type="Button")
   |    | 
   |    | Button - '공서식 조회'    (L1470, T553, R1811, B614)
   |    | ['공서식 조회', '공서식 조회Button', 'Button14']
   |    | child_window(title="공서식 조회", auto_id="bForm", control_type="Button")
   |    | 
   |    | Button - '개정세법'    (L1470, T338, R1811, B399)
   |    | ['개정세법', '개정세법Button', 'Button15']
   |    | child_window(title="개정세법", auto_id="bTaxView", control_type="Button")
   | 
   | Pane - 'panelControl2'    (L105, T1104, R1825, B1223)
   | ['Pane8', 'panelControl2', 'panelControl2Pane']
   | child_window(title="panelControl2", auto_id="panelControl2", control_type="Pane")
   |    | 
   |    | Pane - 'xtraScrollableControl1'    (L315, T1103, R1087, B1222)
   |    | ['xtraScrollableControl1Pane', 'Pane9', 'xtraScrollableControl1']
   |    | child_window(title="xtraScrollableControl1", auto_id="xtraScrollableControl1", control_type="Pane")
   |    | 
   |    | Button - ' 고객센터'    (L1085, T1104, R1295, B1223)
   |    | [' 고객센터', ' 고객센터Button', 'Button21']
   |    | child_window(title=" 고객센터", auto_id="simpleButton2", control_type="Button")
   |    | 
   |    | Static - '        neoic@neoic.com'    (L1558, T1166, R1808, B1199)
   |    | ['        neoic@neoic.com', '        neoic@neoic.comStatic', 'Static15']
   |    | child_window(title="        neoic@neoic.com", auto_id="labelControl7", control_type="Text")
   |    | 
   |    | Static - '        neoic.com'    (L1558, T1132, R1787, B1165)
   |    | ['        neoic.com', 'Static16', '        neoic.comStatic']
   |    | child_window(title="        neoic.com", auto_id="homepage", control_type="Text")
   |    | 
   |    | Static - '(평일 오전9시~오후6시)'    (L1330, T1166, R1547, B1199)
   |    | ['Static17', '(평일 오전9시~오후6시)', '(평일 오전9시~오후6시)Static']
   |    | child_window(title="(평일 오전9시~오후6시)", auto_id="labelControl3", control_type="Text")
   |    | 
   |    | Static - '02-472-4710'    (L1330, T1132, R1547, B1165)
   |    | ['02-472-4710', 'Static18', '02-472-4710Static']
   |    | child_window(title="02-472-4710", auto_id="labelControl2", control_type="Text")
   |    | 
   |    | Button - '고객센터'    (L1288, T1104, R1825, B1223)
   |    | ['고객센터', '고객센터Button', 'Button22']
   |    | child_window(title="고객센터", auto_id="simpleButton3", control_type="Button")
   |    | 
   |    | Button - '공지사항'    (L105, T1104, R315, B1223)
   |    | ['공지사항', '공지사항Button', 'Button23']
   |    | child_window(title="공지사항", auto_id="simpleButton1", control_type="Button")
   | 
   | Pane - 'panelControl1'    (L105, T152, R1825, B250)
   | ['panelControl1', 'panelControl1Pane', 'Pane11']
   | child_window(title="panelControl1", auto_id="panelControl1", control_type="Pane")
   |    | 
   |    | Static - '        현재 프로그램은 『데모버전』이며, 인쇄·전자신고가 지원되지 않습니다.'    (L123, T168, R825, B196)
   |    | ['Static19', '        현재 프로그램은 『데모버전』이며, 인쇄·전자신고가 지원되지 않습니다.', '        현재 프로그램은 『데모버전』이며, 인쇄·전자신고가 지원되지 않습니다.Static']
   |    | child_window(title="        현재 프로그램은 『데모버전』이며, 인쇄·전자신고가 지원되지 않습니다.", auto_id="lbMsg", control_type="Text")
   | 
   | TitleBar - ''    (L144, T105, R1826, B145)
   | ['TitleBar']
   |    | 
   |    | Menu - '시스템'    (L60, T60, R82, B82)
   |    | ['시스템Menu', 'Menu', '시스템', '시스템0', '시스템1']
   |    | child_window(title="시스템", auto_id="MenuBar", control_type="MenuBar")
   |    | 
   |    | Button - '최소화'    (L1708, T103, R1750, B145)
   |    | ['최소화Button', '최소화', 'Button24']
   |    | child_window(title="최소화", control_type="Button")
   |    | 
   |    | Button - '최대화'    (L1747, T103, R1789, B145)
   |    | ['Button25', '최대화Button', '최대화']
   |    | child_window(title="최대화", control_type="Button")
   |    | 
   |    | Button - '닫기'    (L1785, T103, R1827, B145)
   |    | ['닫기Button', '닫기', 'Button26']
   |    | child_window(title="닫기", control_type="Button")


이 출력을 docs/env.md의 '환경 점검 출력' 절에 붙이세요.
```
