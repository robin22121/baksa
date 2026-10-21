/**
 * 양도소득세 테스트 시나리오 — 전체 케이스
 *
 * 넘버링 체계:
 *   1xx  1세대 1주택 (기본)
 *   2xx  일시적 2주택 특례
 *   3xx  상속으로 인한 2주택
 *   4xx  혼인·동거봉양 합가
 *   5xx  농어촌·고향주택 특례
 *   6xx  장기임대주택 거주주택 특례
 *   7xx  기타 특수 케이스
 *   8xx  공동명의·기타 구조
 */

// ═══════════════════════════════════════════════════════
//  카테고리 정의
// ═══════════════════════════════════════════════════════
export const CATEGORIES = [
  { code: '1xx', label: '1세대 1주택', color: '#3b82f6' },
  { code: '2xx', label: '일시적 2주택 특례', color: '#8b5cf6' },
  { code: '3xx', label: '상속 2주택', color: '#ec4899' },
  { code: '4xx', label: '혼인·동거봉양 합가', color: '#f59e0b' },
  { code: '5xx', label: '농어촌·고향주택', color: '#10b981' },
  { code: '6xx', label: '장기임대 거주주택', color: '#06b6d4' },
  { code: '7xx', label: '기타 특수', color: '#6366f1' },
  { code: '8xx', label: '공동명의·기타', color: '#78716c' },
];

export function getCategoryOf(id) {
  const prefix = Math.floor(id / 100);
  return CATEGORIES.find(c => parseInt(c.code) === prefix * 100) || CATEGORIES[0];
}

// ═══════════════════════════════════════════════════════
//  헬퍼
// ═══════════════════════════════════════════════════════
function s(name, ssn, share = 100) {
  return { name, ssn, phone: '010-0000-0000', share };
}
function b(name) {
  return { name, ssn: '000000-0000000', relation: '매수인' };
}

// ═══════════════════════════════════════════════════════
//  1xx — 1세대 1주택 (기본)
// ═══════════════════════════════════════════════════════
const CAT_1 = [
  {
    id: 101,
    title: '1주택 비과세 — 2년 보유+거주, 12억 이하',
    description: '가장 기본적인 비과세. 8억5천 매도, 보유 8년, 거주 5년',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '1세대 1주택 비과세' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '1세대 1주택자가 8년 보유, 5년 거주 후 8억5천에 매도. 양도가 12억 이하이므로 완전 비과세.',
      legalBasis: '소득세법 제89조 제1항 제3호, 시행령 제154조',
    },
    input: {
      houseType: 'A',
      personalInfo: { sellers: [s('홍길동', '800101-1234567')], buyer: b('김철수') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 5, holdingYears: 8 },
      extractedData: {
        saleDate: '2026-03-15', acquisitionDate: '2018-01-10',
        salePrice: 850_000_000, acquisitionPrice: 500_000_000,
        address: '서울시 강남구 역삼동 역삼아파트 101동 1001호',
        acquisitionTax: 5_500_000, brokerFee: 3_000_000,
      },
    },
  },
  {
    id: 102,
    title: '1주택 비과세 — 최소 요건 (보유 2년, 거주 2년)',
    description: '비과세 최소 요건 딱 충족, 10억 매도',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '1세대 1주택 비과세' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '1세대 1주택, 보유 2년·거주 2년 최소 요건 충족. 10억 매도, 12억 이하 완전 비과세.',
      legalBasis: '소득세법 제89조, 시행령 제154조 제1항',
    },
    input: {
      houseType: 'A',
      personalInfo: { sellers: [s('김민지', '850320-2345678')], buyer: b('이준호') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 2, holdingYears: 2 },
      extractedData: {
        saleDate: '2026-04-01', acquisitionDate: '2024-03-20',
        salePrice: 1_000_000_000, acquisitionPrice: 750_000_000,
        address: '서울시 송파구 잠실동 잠실엘스 201동 501호',
        acquisitionTax: 9_000_000, brokerFee: 4_000_000,
      },
    },
  },
  {
    id: 103,
    title: '1주택 과세 — 보유 2년 미만 (1년 6개월)',
    description: '1주택이지만 보유 2년 미만, 비과세 불가',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '보유기간 2년 미만' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '1세대 1주택이나 보유 1년 6개월로 2년 미충족. 비과세 불가, 일반세율 과세.',
      legalBasis: '소득세법 제89조 요건 미충족, 제104조 기본세율',
    },
    input: {
      houseType: 'A',
      personalInfo: { sellers: [s('박지현', '900505-2345678')], buyer: b('최우진') },
      taxExemption: { isExempt: false, isOneHouse: true, isResident: true, residenceYears: 1, holdingYears: 1 },
      extractedData: {
        saleDate: '2026-04-01', acquisitionDate: '2024-10-01',
        salePrice: 600_000_000, acquisitionPrice: 480_000_000,
        address: '경기도 수원시 영통구 매탄동 래미안 105동 301호',
        acquisitionTax: 5_760_000, brokerFee: 2_200_000,
      },
    },
  },
  {
    id: 104,
    title: '1주택 과세 — 보유 3년, 거주 0년 (비거주)',
    description: '보유 3년이나 거주 실적 없음 → 조정지역 거주 요건 미달',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '거주 2년 미만' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '1세대 1주택, 보유 3년이나 거주 0년. 조정대상지역 취득분은 2년 거주 필요. 비과세 불가.',
      legalBasis: '소득세법 시행령 제154조 제1항 (2년 거주 요건)',
    },
    input: {
      houseType: 'A',
      personalInfo: { sellers: [s('정하늘', '880101-1234567')], buyer: b('문서윤') },
      taxExemption: { isExempt: false, isOneHouse: true, isResident: false, residenceYears: 0, holdingYears: 3 },
      extractedData: {
        saleDate: '2026-03-01', acquisitionDate: '2023-03-01',
        salePrice: 900_000_000, acquisitionPrice: 650_000_000,
        address: '서울시 마포구 상암동 월드컵파크 102동 801호',
        acquisitionTax: 7_800_000, brokerFee: 3_500_000,
      },
    },
  },
  {
    id: 105,
    title: '1주택 고가주택 — 양도가 15억 (12억 초과)',
    description: '비과세 요건 충족이나 15억 매도, 12억 초과분 과세',
    expectedResult: '고가주택 일부 과세',
    expected: {
      exemption: { isExempt: true, reason: '1세대 1주택 비과세 (고가)' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: true,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '1세대 1주택 비과세 요건 충족. 양도가 15억으로 12억 초과 고가주택. 초과분 안분 과세.',
      legalBasis: '소득세법 제89조 제1항 제3호 단서, 시행령 제160조',
    },
    input: {
      houseType: 'A',
      personalInfo: { sellers: [s('이영희', '750515-2345678')], buyer: b('박민수') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 7, holdingYears: 10 },
      extractedData: {
        saleDate: '2026-02-20', acquisitionDate: '2016-02-20',
        salePrice: 1_500_000_000, acquisitionPrice: 800_000_000,
        address: '서울시 서초구 반포동 아크로리버파크 201동 3001호',
        acquisitionTax: 12_000_000, brokerFee: 5_000_000,
      },
    },
  },
  {
    id: 106,
    title: '1주택 고가주택 — 양도가 25억, 장특공제 최대 80%',
    description: '25억 매도, 보유 16년·거주 10년 → 장특공제 80%',
    expectedResult: '고가주택 일부 과세',
    expected: {
      exemption: { isExempt: true, reason: '1세대 1주택 비과세 (고가)' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: true,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '1세대 1주택, 25억 매도. 보유 16년·거주 10년으로 장특공제 최대 80%. 초과분 과세.',
      legalBasis: '소득세법 제89조 단서, 제95조의2 장기보유특별공제 80% 한도',
    },
    input: {
      houseType: 'A',
      personalInfo: { sellers: [s('오승환', '650101-1234567')], buyer: b('신혜진') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 10, holdingYears: 16 },
      extractedData: {
        saleDate: '2026-04-10', acquisitionDate: '2010-01-05',
        salePrice: 2_500_000_000, acquisitionPrice: 800_000_000,
        address: '서울시 강남구 대치동 은마아파트 7동 301호',
        acquisitionTax: 9_600_000, brokerFee: 8_000_000,
      },
    },
  },
  {
    id: 107,
    title: '1주택 고가주택 — 양도가 13억 (근소 초과)',
    description: '12억을 1억만 초과, 과세 안분 비율 약 7.7%',
    expectedResult: '고가주택 일부 과세',
    expected: {
      exemption: { isExempt: true, reason: '1세대 1주택 비과세 (고가)' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: true,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '양도가 13억으로 12억을 1억만 초과. 과세 안분 비율 약 7.7%로 세액 적음.',
      legalBasis: '소득세법 제89조 제1항 제3호 단서',
    },
    input: {
      houseType: 'A',
      personalInfo: { sellers: [s('한소희', '830710-2345678')], buyer: b('강동원') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 5, holdingYears: 7 },
      extractedData: {
        saleDate: '2026-03-10', acquisitionDate: '2019-03-10',
        salePrice: 1_300_000_000, acquisitionPrice: 800_000_000,
        address: '서울시 강동구 천호동 래미안강동팰리스 102동 1501호',
        acquisitionTax: 9_600_000, brokerFee: 4_200_000,
      },
    },
  },
  {
    id: 108,
    title: '1주택 양도차손 — 취득가보다 낮게 매도',
    description: '7.5억 취득 → 6억 매도, 양도차손으로 세금 0원',
    expectedResult: '양도차손',
    expected: {
      exemption: { isExempt: false, reason: '' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: true, highValue: false,
      filingGuide: { type: 'loss', hasDeadline: true },
    },
    meta: {
      situation: '부동산 하락으로 취득가보다 낮은 가격에 매도. 양도차손이므로 과세 대상 아님.',
      legalBasis: '소득세법 제95조 (양도차익 없음)',
    },
    input: {
      houseType: 'A',
      personalInfo: { sellers: [s('박수진', '790707-2345678')], buyer: b('한지훈') },
      taxExemption: { isExempt: false, isOneHouse: true, isResident: true, residenceYears: 3, holdingYears: 4 },
      extractedData: {
        saleDate: '2026-03-01', acquisitionDate: '2022-03-01',
        salePrice: 600_000_000, acquisitionPrice: 750_000_000,
        address: '인천시 연수구 송도동 더샵센트럴파크 501동 1201호',
        acquisitionTax: 9_000_000, brokerFee: 2_500_000,
      },
    },
  },
  {
    id: 109,
    title: '1주택 중간 공제 — 보유 5년·거주 3년, 14억 매도',
    description: '장특공제 보유20%+거주12%=32%, 고가주택 일부 과세',
    expectedResult: '고가주택 일부 과세',
    expected: {
      exemption: { isExempt: true, reason: '1세대 1주택 비과세 (고가)' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: true,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '14억 매도, 고가주택. 보유5년(20%)+거주3년(12%)=32% 장특공제 적용.',
      legalBasis: '소득세법 제95조의2 1세대1주택 보유+거주 이원화 공제',
    },
    input: {
      houseType: 'A',
      personalInfo: { sellers: [s('윤서준', '870315-1234567')], buyer: b('김나래') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 3, holdingYears: 5 },
      extractedData: {
        saleDate: '2026-04-01', acquisitionDate: '2021-03-01',
        salePrice: 1_400_000_000, acquisitionPrice: 900_000_000,
        address: '서울시 성동구 성수동 트리마제 101동 2001호',
        acquisitionTax: 10_800_000, brokerFee: 4_500_000,
      },
    },
  },
  {
    id: 110,
    title: '1주택 과세 — 보유 2년, 거주 1년 (거주 부족)',
    description: '보유 2년이나 거주 1년, 2년 거주 요건 미달',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '거주 2년 미만' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '1세대 1주택, 보유 2년이나 거주 1년. 2년 거주 요건 미충족. 과세.',
      legalBasis: '소득세법 시행령 제154조 제1항 (거주 2년 요건 미달)',
    },
    input: {
      houseType: 'A',
      personalInfo: { sellers: [s('조민아', '910820-2345678')], buyer: b('배성훈') },
      taxExemption: { isExempt: false, isOneHouse: true, isResident: false, residenceYears: 1, holdingYears: 2 },
      extractedData: {
        saleDate: '2026-02-15', acquisitionDate: '2024-02-01',
        salePrice: 700_000_000, acquisitionPrice: 550_000_000,
        address: '서울시 노원구 상계동 상계주공 103동 401호',
        acquisitionTax: 6_600_000, brokerFee: 2_800_000,
      },
    },
  },
];

// ═══════════════════════════════════════════════════════
//  2xx — 일시적 2주택 특례
// ═══════════════════════════════════════════════════════
const CAT_2 = [
  {
    id: 201,
    title: '일시적 2주택 비과세 — 3년 내 종전주택 매도',
    description: '종전주택 취득 후 1년 이상, 신규 취득 후 2년 만에 매도',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '일시적 2주택 특례' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '2020년 종전주택 취득, 2023년 신규주택 취득(1년 이상 갭). 2026년 종전주택 매도(3년 이내).',
      legalBasis: '소득세법 시행령 제155조 제1항 (일시적 2주택 비과세 특례)',
      newHouseAcquisitionDate: '2023-05-01',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: true, result: 'exempt' },
      personalInfo: { sellers: [s('최동욱', '780808-1234567')], buyer: b('정수민') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 4, holdingYears: 6 },
      extractedData: {
        saleDate: '2026-04-01', acquisitionDate: '2020-03-15',
        salePrice: 950_000_000, acquisitionPrice: 650_000_000,
        address: '경기도 성남시 분당구 정자동 두산위브 301동 501호',
        acquisitionTax: 7_800_000, brokerFee: 3_500_000,
      },
    },
  },
  {
    id: 202,
    title: '일시적 2주택 비과세 — 고가주택 (14억 매도)',
    description: '일시적 2주택 비과세이나 14억 고가주택 → 초과분 과세',
    expectedResult: '고가주택 일부 과세',
    expected: {
      exemption: { isExempt: true, reason: '일시적 2주택 특례 (고가)' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: true,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '일시적 2주택 비과세 요건 충족. 양도가 14억으로 12억 초과 고가주택. 초과분 과세.',
      legalBasis: '소득세법 시행령 제155조 + 제89조 단서 (고가주택)',
      newHouseAcquisitionDate: '2024-01-15',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: true, result: 'exempt' },
      personalInfo: { sellers: [s('송지은', '810320-2345678')], buyer: b('유재석') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 6, holdingYears: 8 },
      extractedData: {
        saleDate: '2026-03-20', acquisitionDate: '2018-04-01',
        salePrice: 1_400_000_000, acquisitionPrice: 750_000_000,
        address: '서울시 송파구 잠실동 리센츠 108동 2501호',
        acquisitionTax: 9_000_000, brokerFee: 5_500_000,
      },
    },
  },
  {
    id: 203,
    title: '일시적 2주택 과세 — 3년 초과 매도',
    description: '신규 취득 후 3년 10개월 경과, 처분기한 초과',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '처분기한 초과' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '신규주택 취득 2022-06-01, 종전주택 매도 2026-04-01. 3년 10개월 경과로 기한 초과.',
      legalBasis: '소득세법 시행령 제155조 제1항 처분기한(3년) 도과',
      newHouseAcquisitionDate: '2022-06-01',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: false, result: 'taxable' },
      personalInfo: { sellers: [s('김태형', '820202-1234567')], buyer: b('윤서아') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 7 },
      extractedData: {
        saleDate: '2026-04-01', acquisitionDate: '2019-01-20',
        salePrice: 700_000_000, acquisitionPrice: 450_000_000,
        address: '서울시 마포구 상암동 월드컵파크 102동 801호',
        acquisitionTax: 5_400_000, brokerFee: 2_800_000,
      },
    },
  },
  {
    id: 204,
    title: '일시적 2주택 과세 — 1년 갭 미충족 (8개월)',
    description: '종전-신규 취득 간격 8개월, 1년 갭 요건 미충족',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '1년 갭 미충족' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '종전주택 2022-08-01, 신규주택 2023-04-01 취득(8개월 갭). 1년 갭 요건 미충족.',
      legalBasis: '소득세법 시행령 제155조 제1항 (종전주택 취득 후 1년 이상 요건)',
      newHouseAcquisitionDate: '2023-04-01',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: false, withinThreeYears: true, result: 'taxable' },
      personalInfo: { sellers: [s('강민호', '850610-1234567')], buyer: b('서예진') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 3 },
      extractedData: {
        saleDate: '2026-02-01', acquisitionDate: '2022-08-01',
        salePrice: 550_000_000, acquisitionPrice: 400_000_000,
        address: '경기도 고양시 일산동구 백석동 일산자이 205동 903호',
        acquisitionTax: 4_800_000, brokerFee: 2_200_000,
      },
    },
  },
  {
    id: 205,
    title: '일시적 2주택 — 양도차손 발생',
    description: '비과세 요건 충족이나 취득가 대비 하락, 세금 없음',
    expectedResult: '양도차손',
    expected: {
      exemption: { isExempt: true, reason: '일시적 2주택 특례' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: true, highValue: false,
      filingGuide: { type: 'loss', hasDeadline: true },
    },
    meta: {
      situation: '일시적 2주택 비과세 요건 충족이나 양도차손 발생. 세금 없음.',
      legalBasis: '소득세법 제95조 (양도차익 없음)',
      newHouseAcquisitionDate: '2024-06-01',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: true, result: 'exempt' },
      personalInfo: { sellers: [s('이재은', '880215-2345678')], buyer: b('김현우') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 3, holdingYears: 5 },
      extractedData: {
        saleDate: '2026-03-15', acquisitionDate: '2021-03-01',
        salePrice: 450_000_000, acquisitionPrice: 520_000_000,
        address: '경기도 용인시 수지구 죽전동 대우푸르지오 301동 601호',
        acquisitionTax: 6_240_000, brokerFee: 1_800_000,
      },
    },
  },
  {
    id: 206,
    title: '일시적 2주택 과세 — 신규주택 먼저 매도 (순서 오류)',
    description: '종전이 아닌 신규주택을 먼저 매도 → 특례 불가',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '종전주택 미양도' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '종전주택 보유 상태에서 신규주택을 먼저 매도. 특례는 종전주택 양도 시만 적용.',
      legalBasis: '소득세법 시행령 제155조 (종전주택 양도 시에만 특례)',
      newHouseAcquisitionDate: '2023-01-01',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: false, oneYearGap: true, withinThreeYears: true, result: 'taxable' },
      personalInfo: { sellers: [s('황지수', '790925-2345678')], buyer: b('노진우') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 3 },
      extractedData: {
        saleDate: '2026-01-15', acquisitionDate: '2023-01-01',
        salePrice: 680_000_000, acquisitionPrice: 520_000_000,
        address: '경기도 하남시 미사동 미사강변도시 107동 1201호',
        acquisitionTax: 6_240_000, brokerFee: 2_700_000,
      },
    },
  },
];

// ═══════════════════════════════════════════════════════
//  3xx — 상속으로 인한 2주택
// ═══════════════════════════════════════════════════════
const CAT_3 = [
  {
    id: 301,
    title: '상속 2주택 비과세 — 일반주택 양도',
    description: '상속주택 보유 중 기존 일반주택 매도 → 비과세',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '상속 2주택 특례' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '2020년 부친 사망으로 주택 상속. 기존 일반주택(보유 10년·거주 5년) 9억에 매도.',
      legalBasis: '소득세법 시행령 제155조 제2항 (상속주택 특례)',
      inheritanceDate: '2020-05-15',
      sellingWhichHouse: '일반주택',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: true, result: 'exempt' },
      personalInfo: { sellers: [s('김상우', '750101-1234567')], buyer: b('이현정') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 5, holdingYears: 10 },
      extractedData: {
        saleDate: '2026-03-01', acquisitionDate: '2016-01-10',
        salePrice: 900_000_000, acquisitionPrice: 450_000_000,
        address: '서울시 동대문구 이문동 래미안 102동 701호',
        acquisitionTax: 5_400_000, brokerFee: 3_600_000,
      },
    },
  },
  {
    id: 302,
    title: '상속 2주택 과세 — 상속주택을 먼저 매도',
    description: '일반주택 보유 중 상속주택 매도 → 특례 불가, 과세',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '상속주택 먼저 양도' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '상속주택을 먼저 매도. 상속 특례는 일반주택 양도 시에만 적용.',
      legalBasis: '소득세법 시행령 제155조 제2항 (일반주택 먼저 양도 시에만)',
      inheritanceDate: '2021-03-20',
      sellingWhichHouse: '상속주택',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: false, oneYearGap: true, withinThreeYears: true, result: 'taxable' },
      personalInfo: { sellers: [s('김상우', '750101-1234567')], buyer: b('박영미') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 5 },
      extractedData: {
        saleDate: '2026-04-01', acquisitionDate: '2021-03-20',
        salePrice: 550_000_000, acquisitionPrice: 350_000_000,
        address: '경기도 안산시 단원구 고잔동 고잔주공 205동 301호',
        acquisitionTax: 4_200_000, brokerFee: 2_200_000,
      },
    },
  },
  {
    id: 303,
    title: '상속 2주택 비과세 — 고가 일반주택 (15억)',
    description: '상속 특례 비과세이나 일반주택 15억 고가 → 초과분 과세',
    expectedResult: '고가주택 일부 과세',
    expected: {
      exemption: { isExempt: true, reason: '상속 2주택 특례 (고가)' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: true,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '상속 2주택 특례로 비과세 대상이나 양도가 15억 고가주택. 12억 초과분 과세.',
      legalBasis: '소득세법 시행령 제155조 제2항 + 제89조 단서',
      inheritanceDate: '2019-11-01',
      sellingWhichHouse: '일반주택',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: true, result: 'exempt' },
      personalInfo: { sellers: [s('이태호', '700808-1234567')], buyer: b('장미란') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 8, holdingYears: 12 },
      extractedData: {
        saleDate: '2026-02-15', acquisitionDate: '2014-02-01',
        salePrice: 1_500_000_000, acquisitionPrice: 600_000_000,
        address: '서울시 강남구 압구정동 현대아파트 71동 1501호',
        acquisitionTax: 7_200_000, brokerFee: 6_000_000,
      },
    },
  },
  {
    id: 304,
    title: '상속 2주택 과세 — 상속 후 취득한 주택 매도',
    description: '상속 개시 당시 보유 주택이 아닌 새 취득 주택 매도',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '상속 특례 미해당' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '상속 후 새로 취득한 주택 양도. 상속 특례는 상속 개시 당시 보유 주택에만 적용.',
      legalBasis: '소득세법 시행령 제155조 제2항 (상속 개시 당시 보유 주택 한정)',
      inheritanceDate: '2020-01-15',
      sellingWhichHouse: '상속 후 신규 취득 주택',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: false, oneYearGap: true, withinThreeYears: false, result: 'taxable' },
      personalInfo: { sellers: [s('윤미래', '800303-2345678')], buyer: b('정우성') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 4 },
      extractedData: {
        saleDate: '2026-03-01', acquisitionDate: '2022-05-01',
        salePrice: 620_000_000, acquisitionPrice: 480_000_000,
        address: '경기도 의정부시 금오동 센트럴자이 102동 501호',
        acquisitionTax: 5_760_000, brokerFee: 2_500_000,
      },
    },
  },
];

// ═══════════════════════════════════════════════════════
//  4xx — 혼인·동거봉양 합가
// ═══════════════════════════════════════════════════════
const CAT_4 = [
  {
    id: 401,
    title: '혼인 합가 비과세 — 혼인 후 3년 내 매도',
    description: '각 1주택 남녀 혼인, 3년 내 한 채 매도 → 비과세',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '혼인 합가 특례' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '2024-01-20 혼인신고. 각자 1주택. 혼인 후 2년 만에 한 채 매도. 10년 이내 비과세.',
      legalBasis: '소득세법 시행령 제155조 제5항 (혼인 합가 특례, 2024년 개정 10년)',
      marriageDate: '2024-01-20',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: true, result: 'exempt' },
      personalInfo: { sellers: [s('이준서', '880505-1234567')], buyer: b('김도현') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 4, holdingYears: 6 },
      extractedData: {
        saleDate: '2026-02-01', acquisitionDate: '2020-01-15',
        salePrice: 800_000_000, acquisitionPrice: 500_000_000,
        address: '서울시 관악구 봉천동 관악산휴먼시아 103동 901호',
        acquisitionTax: 6_000_000, brokerFee: 3_200_000,
      },
    },
  },
  {
    id: 402,
    title: '혼인 합가 비과세 — 혼인 후 8년 (개정 10년 적용)',
    description: '2024년 개정으로 5년→10년 연장, 8년 경과 비과세',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '혼인 합가 특례' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '2018-03-15 혼인. 8년 경과. 구법 5년이었으나 2024년 말 개정 10년 이내. 비과세.',
      legalBasis: '소득세법 시행령 제155조 제5항 (2024년 개정, 5년→10년 연장)',
      marriageDate: '2018-03-15',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: true, result: 'exempt' },
      personalInfo: { sellers: [s('조은지', '850220-2345678')], buyer: b('노재원') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 5, holdingYears: 10 },
      extractedData: {
        saleDate: '2026-04-01', acquisitionDate: '2016-04-01',
        salePrice: 1_100_000_000, acquisitionPrice: 600_000_000,
        address: '서울시 강서구 화곡동 우장산힐스테이트 201동 1101호',
        acquisitionTax: 7_200_000, brokerFee: 4_400_000,
      },
    },
  },
  {
    id: 403,
    title: '혼인 합가 과세 — 혼인 후 10년 초과',
    description: '혼인 후 11년 경과, 10년 처분기한 초과 → 과세',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '처분기한 초과' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '2015-02-01 혼인. 11년 이상 경과로 10년 처분기한 초과. 2주택 과세.',
      legalBasis: '소득세법 시행령 제155조 제5항 처분기한(10년) 도과',
      marriageDate: '2015-02-01',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: false, result: 'taxable' },
      personalInfo: { sellers: [s('황태영', '780101-1234567')], buyer: b('임수진') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 12 },
      extractedData: {
        saleDate: '2026-03-01', acquisitionDate: '2014-01-15',
        salePrice: 750_000_000, acquisitionPrice: 400_000_000,
        address: '경기도 부천시 중동 롯데캐슬 105동 801호',
        acquisitionTax: 4_800_000, brokerFee: 3_000_000,
      },
    },
  },
  {
    id: 404,
    title: '동거봉양 합가 비과세 — 60세 이상 부모, 7년 내',
    description: '부모 동거봉양 합가 후 6년 경과 매도 → 비과세',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '동거봉양 합가 특례' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '2020-06-01 60세 이상 부모 합가. 6년 경과 후 매도. 10년 이내 비과세.',
      legalBasis: '소득세법 시행령 제155조 제6항 (동거봉양 합가 특례)',
      mergeDate: '2020-06-01',
      parentAge: 65,
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: true, result: 'exempt' },
      personalInfo: { sellers: [s('유진혁', '820901-1234567')], buyer: b('나승우') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 6, holdingYears: 8 },
      extractedData: {
        saleDate: '2026-04-01', acquisitionDate: '2018-04-01',
        salePrice: 850_000_000, acquisitionPrice: 500_000_000,
        address: '경기도 안양시 동안구 평촌동 래미안 103동 501호',
        acquisitionTax: 6_000_000, brokerFee: 3_400_000,
      },
    },
  },
  {
    id: 405,
    title: '동거봉양 합가 과세 — 10년 초과',
    description: '동거봉양 합가 후 11년 경과, 처분기한 초과',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '처분기한 초과' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '2015-01-01 합가. 11년 이상 경과로 10년 처분기한 초과. 2주택 과세.',
      legalBasis: '소득세법 시행령 제155조 제6항 처분기한(10년) 도과',
      mergeDate: '2015-01-01',
      parentAge: 70,
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: false, result: 'taxable' },
      personalInfo: { sellers: [s('서동민', '770515-1234567')], buyer: b('한지영') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 15 },
      extractedData: {
        saleDate: '2026-02-01', acquisitionDate: '2011-01-01',
        salePrice: 620_000_000, acquisitionPrice: 350_000_000,
        address: '경기도 광명시 하안동 광명아파트 102동 301호',
        acquisitionTax: 4_200_000, brokerFee: 2_500_000,
      },
    },
  },
  {
    id: 406,
    title: '동거봉양 합가 과세 — 부모 60세 미만 (58세)',
    description: '부모 58세로 60세 요건 미충족 → 일반 2주택 과세',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '60세 미만' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '부모 58세. 동거봉양 합가 요건(직계존속 60세 이상) 미충족. 일반 2주택 과세.',
      legalBasis: '소득세법 시행령 제155조 제6항 (60세 이상 요건 미달)',
      mergeDate: '2023-06-01',
      parentAge: 58,
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: false, result: 'taxable' },
      personalInfo: { sellers: [s('장세영', '850820-1234567')], buyer: b('민경훈') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 5 },
      extractedData: {
        saleDate: '2026-03-15', acquisitionDate: '2021-03-01',
        salePrice: 580_000_000, acquisitionPrice: 420_000_000,
        address: '경기도 김포시 장기동 한강메트로자이 201동 701호',
        acquisitionTax: 5_040_000, brokerFee: 2_300_000,
      },
    },
  },
];

// ═══════════════════════════════════════════════════════
//  5xx — 농어촌·고향주택 특례
// ═══════════════════════════════════════════════════════
const CAT_5 = [
  {
    id: 501,
    title: '농어촌주택 비과세 — 3년 보유 후 일반주택 매도',
    description: '읍면 농어촌주택 3년+ 보유, 일반주택 매도 → 비과세',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '농어촌주택 특례' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '2021년 강원도 읍면 농어촌주택 취득(기준시가 2억). 3년+ 보유 후 서울 일반주택 매도.',
      legalBasis: '소득세법 시행령 제155조 제7항 (농어촌주택 특례)',
      ruralHouseLocation: '강원도 횡성군 횡성읍',
      ruralHouseAcquisitionDate: '2021-06-01',
      ruralHousePrice: '2억',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: true, result: 'exempt' },
      personalInfo: { sellers: [s('박노준', '770320-1234567')], buyer: b('임수빈') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 6, holdingYears: 10 },
      extractedData: {
        saleDate: '2026-03-01', acquisitionDate: '2016-03-01',
        salePrice: 880_000_000, acquisitionPrice: 500_000_000,
        address: '서울시 광진구 구의동 아차산래미안 101동 1201호',
        acquisitionTax: 6_000_000, brokerFee: 3_500_000,
      },
    },
  },
  {
    id: 502,
    title: '농어촌주택 과세 — 3년 미보유',
    description: '농어촌주택 2년만에 일반주택 매도 → 3년 보유 미충족',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '농어촌주택 3년 미보유' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '농어촌주택 2024-06-01 취득. 2년 미만에 일반주택 매도. 3년 보유 요건 미충족.',
      legalBasis: '소득세법 시행령 제155조 제7항 (농어촌주택 3년 보유 요건 미달)',
      ruralHouseLocation: '전남 담양군 담양읍',
      ruralHouseAcquisitionDate: '2024-06-01',
      ruralHousePrice: '1억5천',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: false, result: 'taxable' },
      personalInfo: { sellers: [s('고재현', '830115-1234567')], buyer: b('송유진') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 8 },
      extractedData: {
        saleDate: '2026-02-01', acquisitionDate: '2018-02-01',
        salePrice: 650_000_000, acquisitionPrice: 400_000_000,
        address: '대전시 유성구 봉명동 유성래미안 102동 801호',
        acquisitionTax: 4_800_000, brokerFee: 2_600_000,
      },
    },
  },
  {
    id: 503,
    title: '농어촌주택 과세 — 수도권 소재 (대상 아님)',
    description: '수도권 읍면 → 농어촌주택 특례 대상 아님',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '수도권 소재' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '경기도 여주시 가남읍(수도권). 농어촌주택 특례는 수도권 밖만 가능.',
      legalBasis: '소득세법 시행령 제155조 제7항 (수도권 밖 요건 미달)',
      ruralHouseLocation: '경기도 여주시 가남읍 (수도권)',
      ruralHouseAcquisitionDate: '2022-01-01',
      ruralHousePrice: '1억8천',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: false, result: 'taxable' },
      personalInfo: { sellers: [s('나경태', '790620-1234567')], buyer: b('오수현') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 6 },
      extractedData: {
        saleDate: '2026-01-15', acquisitionDate: '2020-01-01',
        salePrice: 720_000_000, acquisitionPrice: 480_000_000,
        address: '서울시 중랑구 면목동 면목래미안 101동 601호',
        acquisitionTax: 5_760_000, brokerFee: 2_900_000,
      },
    },
  },
];

// ═══════════════════════════════════════════════════════
//  6xx — 장기임대주택 거주주택 특례
// ═══════════════════════════════════════════════════════
const CAT_6 = [
  {
    id: 601,
    title: '장기임대+거주주택 비과세 — 2년 거주, 의무 준수',
    description: '임대등록 주택 외 거주주택 2년+ 거주 후 매도 → 비과세',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '장기임대 거주주택 특례' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '임대사업자 등록 1채 + 거주주택 1채. 거주주택 2년+ 거주, 임대 의무 준수(5% 증액 제한).',
      legalBasis: '소득세법 시행령 제155조 제20항 (장기임대 거주주택 특례)',
      rentalRegistrationDate: '2019-03-01',
      rentalProperty: '서울시 성북구 장위동 장위자이 (임대등록)',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: true, result: 'exempt' },
      personalInfo: { sellers: [s('정일우', '780815-1234567')], buyer: b('강서연') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 4, holdingYears: 7 },
      extractedData: {
        saleDate: '2026-03-20', acquisitionDate: '2019-04-01',
        salePrice: 950_000_000, acquisitionPrice: 600_000_000,
        address: '서울시 노원구 공릉동 태릉해링턴플레이스 102동 1801호',
        acquisitionTax: 7_200_000, brokerFee: 3_800_000,
      },
    },
  },
  {
    id: 602,
    title: '장기임대+거주주택 과세 — 거주 2년 미만 (1년)',
    description: '거주주택에서 1년만 거주 → 2년 요건 미충족',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '거주 2년 미만' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '거주주택에서 1년만 거주. 거주 2년 요건 미충족. 거주주택 특례 불가.',
      legalBasis: '소득세법 시행령 제155조 제20항 (2년 거주 요건 미달)',
      rentalRegistrationDate: '2020-01-01',
      rentalProperty: '경기도 파주시 운정 (임대등록)',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: false, result: 'taxable' },
      personalInfo: { sellers: [s('백진호', '850420-1234567')], buyer: b('차수빈') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 1, holdingYears: 4 },
      extractedData: {
        saleDate: '2026-02-15', acquisitionDate: '2022-01-01',
        salePrice: 680_000_000, acquisitionPrice: 500_000_000,
        address: '경기도 파주시 교하동 운정신도시 자이 301동 1501호',
        acquisitionTax: 6_000_000, brokerFee: 2_700_000,
      },
    },
  },
  {
    id: 603,
    title: '장기임대+거주주택 과세 — 임대 의무 위반 (5% 초과)',
    description: '임대료 8% 인상, 의무 위반 → 특례 박탈',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '임대 의무 위반' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '임대료 8% 인상으로 5% 증액 제한 의무 위반. 거주주택 특례 박탈, 2주택 과세.',
      legalBasis: '소득세법 시행령 제155조 제20항 (임대 의무 위반 시 특례 배제)',
      rentalRegistrationDate: '2018-06-01',
      rentalProperty: '서울시 금천구 독산동 (임대등록, 의무 위반)',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: false, result: 'taxable' },
      personalInfo: { sellers: [s('오태석', '790305-1234567')], buyer: b('김예은') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 3, holdingYears: 6 },
      extractedData: {
        saleDate: '2026-04-01', acquisitionDate: '2020-04-01',
        salePrice: 780_000_000, acquisitionPrice: 550_000_000,
        address: '서울시 구로구 구로동 구로파크밸리 102동 901호',
        acquisitionTax: 6_600_000, brokerFee: 3_100_000,
      },
    },
  },
];

// ═══════════════════════════════════════════════════════
//  7xx — 기타 특수 케이스
// ═══════════════════════════════════════════════════════
const CAT_7 = [
  {
    id: 701,
    title: '취학·근무 비과세 — 사유 해소 후 3년 내 매도',
    description: '자녀 취학 목적 지방 주택 취득, 졸업 후 2년 내 일반주택 매도',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '취학·근무 특례' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '취학 목적 대전 주택 취득(수도권 밖). 졸업(사유 해소) 후 2년 내 서울 일반주택 매도.',
      legalBasis: '소득세법 시행령 제155조 제4항 (취학·근무 등 부득이한 사유)',
      reasonType: '취학',
      reasonResolvedDate: '2024-02-28',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: true, result: 'exempt' },
      personalInfo: { sellers: [s('장동현', '750620-1234567')], buyer: b('이소영') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 5, holdingYears: 8 },
      extractedData: {
        saleDate: '2026-01-15', acquisitionDate: '2018-01-15',
        salePrice: 920_000_000, acquisitionPrice: 550_000_000,
        address: '서울시 서대문구 연희동 연희파크푸르지오 101동 801호',
        acquisitionTax: 6_600_000, brokerFee: 3_700_000,
      },
    },
  },
  {
    id: 702,
    title: '취학·근무 과세 — 사유 해소 후 3년 초과',
    description: '졸업 후 4년 경과, 3년 처분기한 초과 → 과세',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '사유 해소 후 3년 초과' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '취학 사유 해소(졸업) 2022-02-28. 2026-04-01 매도로 4년 경과. 3년 기한 초과.',
      legalBasis: '소득세법 시행령 제155조 제4항 (사유 해소 후 3년 기한 초과)',
      reasonType: '취학',
      reasonResolvedDate: '2022-02-28',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: false, result: 'taxable' },
      personalInfo: { sellers: [s('임창균', '800101-1234567')], buyer: b('구하라') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 10 },
      extractedData: {
        saleDate: '2026-04-01', acquisitionDate: '2016-03-01',
        salePrice: 700_000_000, acquisitionPrice: 450_000_000,
        address: '서울시 종로구 평창동 평창동주택 101호',
        acquisitionTax: 5_400_000, brokerFee: 2_800_000,
      },
    },
  },
  {
    id: 703,
    title: '문화재주택 비과세 — 문화재 외 일반주택 매도',
    description: '국가등록문화재 주택 보유 → 주택 수 제외, 일반주택 비과세',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '문화재주택 특례' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '국가등록문화재 주택 보유. 일반주택(보유 8년·거주 4년) 매도. 문화재주택 주택 수 제외.',
      legalBasis: '소득세법 시행령 제155조 제9항 (문화재 주택 특례)',
      culturalPropertyDesignation: '2015-09-01',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: true, result: 'exempt' },
      personalInfo: { sellers: [s('배성재', '720405-1234567')], buyer: b('김태리') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 4, holdingYears: 8 },
      extractedData: {
        saleDate: '2026-02-01', acquisitionDate: '2018-02-01',
        salePrice: 780_000_000, acquisitionPrice: 450_000_000,
        address: '서울시 종로구 계동 현대아파트 101동 501호',
        acquisitionTax: 5_400_000, brokerFee: 3_100_000,
      },
    },
  },
  {
    id: 704,
    title: '소수지분 상속 — 주택 수 제외, 1주택 비과세',
    description: '공동상속 소수지분(20%) → 주택 수 제외, 기존 1주택 비과세',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '소수지분 제외, 1주택 비과세' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '형제 3명 상속, 본인 지분 20%(소수). 소수지분 주택 수 제외. 기존 1주택 비과세.',
      legalBasis: '소득세법 시행령 제155조 제3항 (공동상속주택 소수지분 주택 수 제외)',
      inheritedShare: '20%',
      totalHeirs: 3,
    },
    input: {
      houseType: 'A',
      personalInfo: { sellers: [s('한승우', '810910-1234567')], buyer: b('유지원') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 5, holdingYears: 7 },
      extractedData: {
        saleDate: '2026-03-15', acquisitionDate: '2019-03-01',
        salePrice: 850_000_000, acquisitionPrice: 500_000_000,
        address: '서울시 양천구 목동 목동신시가지 7단지 704동 301호',
        acquisitionTax: 6_000_000, brokerFee: 3_400_000,
      },
    },
  },
  {
    id: 705,
    title: '지방 저가주택 — 주택 수 제외, 1주택 비과세',
    description: '인구감소지역 공시가 1.5억 → 주택 수 제외',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '저가주택 제외, 1주택 비과세' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '인구감소지역(경북 영주시) 공시가 1억5천 주택 보유. 저가주택 주택 수 제외. 1주택 비과세.',
      legalBasis: '조세특례제한법 제99조의4 (인구감소지역 저가주택 주택 수 제외)',
      lowValueHouseLocation: '경북 영주시',
      officialPrice: '1억5천',
    },
    input: {
      houseType: 'A',
      personalInfo: { sellers: [s('권태준', '830227-1234567')], buyer: b('신은정') },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 4, holdingYears: 6 },
      extractedData: {
        saleDate: '2026-04-01', acquisitionDate: '2020-04-01',
        salePrice: 770_000_000, acquisitionPrice: 480_000_000,
        address: '서울시 동작구 사당동 사당래미안 101동 1001호',
        acquisitionTax: 5_760_000, brokerFee: 3_100_000,
      },
    },
  },
  {
    id: 706,
    title: '지방 저가주택 과세 — 공시가 4억 (3억 초과)',
    description: '인구감소지역이나 공시가 4억으로 저가주택 미충족',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '저가주택 미충족' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '인구감소지역이나 공시가 4억으로 3억 기준 초과. 저가주택 특례 불가. 2주택 과세.',
      legalBasis: '조세특례제한법 제99조의4 (공시가격 3억 이하 요건 미달)',
      lowValueHouseLocation: '강원도 원주시',
      officialPrice: '4억',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: false, result: 'taxable' },
      personalInfo: { sellers: [s('문성호', '790110-1234567')], buyer: b('정하영') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 7 },
      extractedData: {
        saleDate: '2026-03-01', acquisitionDate: '2019-02-01',
        salePrice: 680_000_000, acquisitionPrice: 430_000_000,
        address: '서울시 은평구 응암동 응암동래미안 103동 601호',
        acquisitionTax: 5_160_000, brokerFee: 2_700_000,
      },
    },
  },
];

// ═══════════════════════════════════════════════════════
//  8xx — 공동명의·기타 구조
// ═══════════════════════════════════════════════════════
const CAT_8 = [
  {
    id: 801,
    title: '공동명의 50:50 — 고가주택, 지분별 과세',
    description: '부부 공동명의, 14억 매도. 각 지분별 기본공제 별도 적용',
    expectedResult: '고가주택 일부 과세',
    expected: {
      exemption: { isExempt: true, reason: '1세대 1주택 비과세 (고가)' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: true,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '부부 공동명의(50:50) 1주택. 14억 고가주택. 각 지분별 기본공제 250만원 별도.',
      legalBasis: '소득세법 제89조, 공동소유 지분별 과세 원칙',
    },
    input: {
      houseType: 'A',
      personalInfo: {
        sellers: [s('장민호', '800303-1234567', 50), s('장서연', '820505-2345678', 50)],
        buyer: b('이준혁'),
      },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 6, holdingYears: 8 },
      extractedData: {
        saleDate: '2026-03-20', acquisitionDate: '2018-03-20',
        salePrice: 1_400_000_000, acquisitionPrice: 700_000_000,
        address: '서울시 용산구 한남동 한남더힐 202동 1501호',
        acquisitionTax: 10_500_000, brokerFee: 5_000_000,
      },
    },
  },
  {
    id: 802,
    title: '공동명의 70:30 — 비과세 (12억 이하)',
    description: '부부 70:30, 11억 매도 → 두 사람 모두 완전 비과세',
    expectedResult: '비과세',
    expected: {
      exemption: { isExempt: true, reason: '1세대 1주택 비과세' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: 0, isLoss: false, highValue: false,
      filingGuide: { type: 'exempt', hasDeadline: true },
    },
    meta: {
      situation: '부부 공동명의(70:30). 양도가 11억, 12억 이하이므로 두 사람 모두 완전 비과세.',
      legalBasis: '소득세법 제89조 (12억 이하 비과세)',
    },
    input: {
      houseType: 'A',
      personalInfo: {
        sellers: [s('이동건', '780815-1234567', 70), s('이수진', '810220-2345678', 30)],
        buyer: b('홍길순'),
      },
      taxExemption: { isExempt: true, isOneHouse: true, isResident: true, residenceYears: 5, holdingYears: 10 },
      extractedData: {
        saleDate: '2026-02-01', acquisitionDate: '2016-01-15',
        salePrice: 1_100_000_000, acquisitionPrice: 550_000_000,
        address: '서울시 강남구 개포동 개포주공 5단지 508동 1201호',
        acquisitionTax: 6_600_000, brokerFee: 4_400_000,
      },
    },
  },
  {
    id: 803,
    title: '공동명의 50:50 — 2주택 과세',
    description: '부부 공동명의 2주택, 비과세 불가 → 지분별 과세',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '2주택 과세' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '부부 공동명의(50:50) 2주택. 비과세 미충족. 지분별 양도차익 산정 후 각각 과세.',
      legalBasis: '소득세법 제104조 기본세율, 공동소유 지분별 과세',
    },
    input: {
      houseType: 'B',
      tempTwoHouse: { sellingFirst: true, oneYearGap: true, withinThreeYears: false, result: 'taxable' },
      personalInfo: {
        sellers: [s('한정우', '810505-1234567', 50), s('한미영', '830710-2345678', 50)],
        buyer: b('이철수'),
      },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 5 },
      extractedData: {
        saleDate: '2026-04-01', acquisitionDate: '2021-04-01',
        salePrice: 800_000_000, acquisitionPrice: 550_000_000,
        address: '경기도 성남시 중원구 성남동 산성역자이 102동 1001호',
        acquisitionTax: 6_600_000, brokerFee: 3_200_000,
      },
    },
  },
  {
    id: 804,
    title: '단기보유 과세 — 1년 미만 (8개월)',
    description: '보유 8개월, 장기보유공제 없음, 기본세율 과세',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '보유기간 2년 미만' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '1주택이나 보유 8개월. 비과세 미달. 1년 미만 장특공제 없음.',
      legalBasis: '소득세법 제104조 (1년 미만 보유)',
    },
    input: {
      houseType: 'A',
      personalInfo: { sellers: [s('윤대한', '880101-1234567')], buyer: b('고은별') },
      taxExemption: { isExempt: false, isOneHouse: true, isResident: false, residenceYears: 0, holdingYears: 0 },
      extractedData: {
        saleDate: '2026-04-05', acquisitionDate: '2025-08-10',
        salePrice: 550_000_000, acquisitionPrice: 480_000_000,
        address: '경기도 수원시 영통구 매탄동 래미안 105동 301호',
        acquisitionTax: 5_760_000, brokerFee: 2_200_000,
      },
    },
  },
  {
    id: 805,
    title: '3주택 이상 과세 — 다주택자',
    description: '3주택 보유, 비과세 불가, 일반세율 과세',
    expectedResult: '과세',
    expected: {
      exemption: { isExempt: false, reason: '3주택 이상' },
      surtax: { isSurtax: false, reason: '' },
      totalTax: null, isLoss: false, highValue: false,
      filingGuide: { type: 'taxable', hasDeadline: true },
    },
    meta: {
      situation: '3주택 이상 다주택자. 중과세 한시 유예 중이나 비과세는 불가. 일반세율 과세.',
      legalBasis: '소득세법 제104조, 다주택 중과 한시 유예 (2026년 현재)',
    },
    input: {
      houseType: 'C',
      personalInfo: { sellers: [s('최부자', '700101-1234567')], buyer: b('서민석') },
      taxExemption: { isExempt: false, isOneHouse: false, isResident: false, residenceYears: 0, holdingYears: 8 },
      extractedData: {
        saleDate: '2026-03-01', acquisitionDate: '2018-03-01',
        salePrice: 1_200_000_000, acquisitionPrice: 700_000_000,
        address: '서울시 강남구 삼성동 아이파크 201동 2501호',
        acquisitionTax: 8_400_000, brokerFee: 4_800_000,
      },
    },
  },
];

// ═══════════════════════════════════════════════════════
//  전체 합치기
// ═══════════════════════════════════════════════════════
const TEST_SCENARIOS = [
  ...CAT_1, ...CAT_2, ...CAT_3, ...CAT_4,
  ...CAT_5, ...CAT_6, ...CAT_7, ...CAT_8,
];

export default TEST_SCENARIOS;
