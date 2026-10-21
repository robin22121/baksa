// 클라우드형 화면 덤프 — 시스템 Chrome(CDP)에 붙어 화면별 page.html + fields.json + screenshot.png 저장
// 출력: data/raw/cloud/screens/NNN-<제목>/ (gitignore — HTML에 세션·개인정보가 섞일 수 있다)
//
// 사용법 (Chrome은 tools/cloud/start-chrome.sh 로 먼저 띄우고, 그 창에서 로그인까지 마친 뒤):
//   node tools/cloud/dump-web.mjs watch                       # 사람이 화면을 옮길 때마다 터미널에서 Enter → 현재 화면 덤프
//   node tools/cloud/dump-web.mjs crawl <시작URL> [범위prefix]  # 링크(a[href])를 BFS로 따라가며 자동 덤프
//
// 조건부 필드(특정 선택 시에만 나타나는 입력칸)는 crawl로 못 잡으므로 watch 모드에서 그 상태를 만든 뒤 Enter.
// 의존성: npm i playwright-core (브라우저는 내려받지 않고 시스템 Chrome에 CDP로 붙는다)

import { chromium } from 'playwright-core';
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';

const CDP = process.env.BROWSER_CDP_ENDPOINT || 'http://127.0.0.1:9222';
const OUT = path.resolve(import.meta.dirname, '..', '..', 'data', 'raw', 'cloud', 'screens');
const INDEX = path.join(OUT, 'index.jsonl');

// 브라우저 안에서 실행되는 필드 추출기 — 프레임마다 호출
const EXTRACT = () => {
  const text = (el) => (el?.innerText || el?.textContent || '').replace(/\s+/g, ' ').trim();
  const labelOf = (el) => {
    if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l) return text(l); }
    const wrap = el.closest('label'); if (wrap) return text(wrap);
    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
    if (el.getAttribute('aria-labelledby')) return text(document.getElementById(el.getAttribute('aria-labelledby')));
    // 국내 업무화면 관례: <th>라벨</th><td><input></td>
    const td = el.closest('td'); if (td) { const th = td.parentElement?.querySelector('th'); if (th) return text(th); }
    // 바로 앞 형제의 짧은 텍스트
    const prev = el.previousElementSibling; if (prev && text(prev).length < 40) return text(prev);
    return '';
  };
  const fields = [];
  for (const el of document.querySelectorAll('input, select, textarea, button, [role="button"], [contenteditable="true"]')) {
    const tag = el.tagName.toLowerCase();
    const type = tag === 'input' ? (el.type || 'text') : tag;
    if (type === 'hidden' && !el.name) continue;
    fields.push({
      tag, type,
      name: el.name || '', id: el.id || '',
      label: labelOf(el),
      placeholder: el.placeholder || '',
      value: type === 'password' ? '' : (el.value ?? '').toString().slice(0, 50),
      text: ['button', 'submit', 'reset'].includes(type) ? text(el).slice(0, 40) : '',
      required: !!el.required, disabled: !!el.disabled, readonly: !!el.readOnly,
      hidden: type === 'hidden' || el.offsetParent === null,
      maxlength: el.maxLength > 0 ? el.maxLength : undefined,
      options: tag === 'select' ? [...el.options].map(o => o.text.trim()).slice(0, 100) : undefined,
    });
  }
  const headings = [...document.querySelectorAll('h1,h2,h3,h4,legend,caption,.title,[class*="tit"]')].map(text).filter(Boolean).slice(0, 50);
  const tabs = [...document.querySelectorAll('[role="tab"], .tab li, .tabs li, ul[class*="tab"] li')].map(text).filter(Boolean).slice(0, 50);
  return { fields, headings, tabs, title: document.title, url: location.href };
};

const slug = (s) => s.replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '').slice(0, 60) || 'page';

async function dump(page, seq) {
  const frames = [];
  for (const fr of page.frames()) {
    try { frames.push({ frame: fr.url(), ...(await fr.evaluate(EXTRACT)) }); } catch { /* cross-origin 등 */ }
  }
  const main = frames[0] || { title: await page.title(), url: page.url() };
  const dir = path.join(OUT, `${String(seq).padStart(3, '0')}-${slug(main.title || new URL(page.url()).pathname)}`);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'page.html'), await page.content());
  fs.writeFileSync(path.join(dir, 'fields.json'), JSON.stringify({ source: 'web', url: page.url(), title: main.title, frames }, null, 2));
  await page.screenshot({ path: path.join(dir, 'screenshot.png'), fullPage: true }).catch(() => {});
  const nf = frames.reduce((n, f) => n + (f.fields?.length || 0), 0);
  fs.appendFileSync(INDEX, JSON.stringify({ seq, dir: path.basename(dir), url: page.url(), title: main.title, fields: nf }) + '\n');
  console.log(`[${seq}] ${main.title} — 필드 ${nf}개 → ${path.relative(process.cwd(), dir)}`);
}

function nextSeq() {
  if (!fs.existsSync(INDEX)) return 1;
  const lines = fs.readFileSync(INDEX, 'utf8').trim().split('\n').filter(Boolean);
  return lines.length ? JSON.parse(lines.at(-1)).seq + 1 : 1;
}

fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.connectOverCDP(CDP);
const ctx = browser.contexts()[0];
const [mode, startUrl, scope] = process.argv.slice(2);
let seq = nextSeq();

if (mode === 'watch') {
  console.log('Chrome에서 화면을 옮긴 뒤 Enter를 누르면 현재 화면을 덤프합니다. 종료: q + Enter');
  const rl = readline.createInterface({ input: process.stdin });
  for await (const line of rl) {
    if (line.trim() === 'q') break;
    await dump(ctx.pages().at(-1), seq++);
  }
} else if (mode === 'crawl' && startUrl) {
  const prefix = scope || new URL(startUrl).origin;
  const page = ctx.pages().at(-1) || await ctx.newPage();
  const seen = new Set(), queue = [startUrl];
  while (queue.length) {
    const url = queue.shift();
    const key = url.split('#')[0];
    if (seen.has(key)) continue;
    seen.add(key);
    try {
      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(800);
      await dump(page, seq++);
      const links = await page.evaluate(() => [...document.querySelectorAll('a[href]')].map(a => a.href));
      for (const l of links) if (l.startsWith(prefix) && !seen.has(l.split('#')[0]) && !/logout|signout|download/i.test(l)) queue.push(l);
    } catch (e) { console.warn(`skip ${url}: ${e.message}`); }
  }
} else {
  console.log('usage: node tools/cloud/dump-web.mjs watch | crawl <startURL> [scopePrefix]');
}
await browser.close();
