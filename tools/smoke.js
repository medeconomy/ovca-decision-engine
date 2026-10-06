#!/usr/bin/env node
/* Headless smoke test for index.html.
   Usage:  python3 -m http.server 8765 &   (from the repo root)
           npm install                      (once; installs playwright)
           npx playwright install chromium  (once, if no browser is installed)
           node tools/smoke.js [base-url]   (default http://localhost:8765/)
   Prints each scenario's tiers, cards and flags so a change in ranking is visible in the diff,
   checks the evidence-browser tabs and trial links for every histology, checks phone width,
   and exits 1 on any page error or console error. */
const { chromium } = require('playwright');
const BASE = process.argv[2] || 'http://localhost:8765/';

const CASES = [
  // epithelial
  {n:"HGSC 1L maint BRCAm R0 CR", p:{setting:"first_line_maintenance",stage:"III",surg:"primary",resid:"R0",img:"none",ca:"normal",brca:"germline_path",hrd:"positive",lines:1,ledger:[["platinum","progressed_after"],["taxane","progressed_after"]]}},
  {n:"HGSC 1L maint HRp IDS PR CA fell90", p:{setting:"first_line_maintenance",stage:"III",surg:"interval",resid:"R1",img:"shrink",ca:"fell90",brca:"wild_type",hrd:"negative",lines:1}},
  {n:"HGSC PROC FRa-high prior bev", p:{setting:"platinum_resistant_recurrence",stage:"IV",pfi:4,fra:"high",brca:"wild_type",cps:5,lines:2,ledger:[["platinum","progressed_after"],["anti_vegf","progressed_after"]]}},
  {n:"OCCC PROC", p:{hist:"OCCC",setting:"platinum_resistant_recurrence",stage:"III",pfi:4,brca:"wild_type",mmr:"pMMR",lines:1,ledger:[["platinum","progressed_after"]]}},
  {n:"OEC adjuvant p53abn WT1+", p:{hist:"endometrioid",setting:"adjuvant",stage:"I",grade:"3",mol:"p53abn",wt1:"positive"}},
  {n:"MOC 1L HER2 3+", p:{hist:"mucinous",setting:"first_line_chemo",stage:"III",resid:"R1",inv:"infiltrative",prim:"true",her2:"3+"}},
  // germ cell
  {n:"GCT adj IA YST child AFP", p:{hist:"GCT",setting:"adjuvant",stage:"I",gct_sub:"YST",age:"child",staging:"complete",markers:"afp"}},
  {n:"GCT adj dysgerminoma incomplete >=40", p:{hist:"GCT",setting:"adjuvant",stage:"I",gct_sub:"dysgerminoma",age:"adult40",staging:"incomplete"}},
  {n:"GCT 1L dysgerminoma III R0", p:{hist:"GCT",setting:"first_line_chemo",stage:"III",resid:"R0",gct_sub:"dysgerminoma",age:"adult",markers:"none"}},
  {n:"GCT 1L YST IV R2 child ILD", p:{hist:"GCT",setting:"first_line_chemo",stage:"IV",resid:"R2",gct_sub:"YST",age:"child",markers:"afp",flags:["ild_or_pneumonitis"]}},
  {n:"GCT refractory CrCl 45", p:{hist:"GCT",setting:"platinum_resistant_recurrence",gct_sub:"YST",age:"adult",lines:2,crcl:45,ledger:[["platinum","progressed_on"]]}},
  // sex cord-stromal
  {n:"SCST adj I SLCT heterologous", p:{hist:"SCST",setting:"adjuvant",stage:"I",scst_sub:"SLCT_heterologous",age:"adult",staging:"complete"}},
  {n:"SCST 1L III AGCT", p:{hist:"SCST",setting:"first_line_chemo",stage:"III",scst_sub:"AGCT",age:"adult40"}},
  {n:"SCST recurrence AGCT ER+ unresectable", p:{hist:"SCST",setting:"recurrence",scst_sub:"AGCT",age:"adult40",erpr:"positive",resect:"no",lines:1,ledger:[["platinum","progressed_after"],["taxane","progressed_after"]]}},
];

(async () => {
  const b = await chromium.launch({ args: ['--no-sandbox'] });
  const errs = [];
  const page = async (w, h) => {
    const p = await b.newPage({ viewport: { width: w, height: h } });
    p.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
    p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    await p.goto(BASE + 'index.html', { waitUntil: 'networkidle' });
    await p.evaluate(() => { try { localStorage.clear() } catch (e) {} });
    await p.reload({ waitUntil: 'networkidle' });
    return p;
  };

  const p = await page(1280, 1000);
  for (const c of CASES) {
    await p.evaluate(x => applyPreset(x), c.p);
    await p.waitForTimeout(80);
    const fields = await p.$$eval('#pf .fld', fs => fs.filter(f => f.offsetParent !== null).map(f => f.querySelector('select,input').id.replace('f_', '')).join(','));
    const notices = await p.$$eval('#results .notice', n => n.map(x => x.textContent.slice(0, 90)));
    const tiers = await p.$$eval('#results > details', ds => ds.map(d => {
      const h = d.querySelector('summary h3').textContent;
      const items = [...d.querySelectorAll('.rcard')].map(c => {
        const t = c.querySelector('.tierbadge').textContent, nm = c.querySelector('.name').textContent;
        const fl = [...c.querySelectorAll('.flag')].map(f => f.querySelector('b').textContent + ': ' + f.querySelector('span').textContent.slice(0, 60));
        return `   [${t}] ${nm.slice(0, 72)}` + (fl.length ? '\n      ' + fl.join('\n      ') : '');
      });
      return (d.open ? '▼ ' : '▶ ') + h + '\n' + items.join('\n');
    }));
    console.log(`=== ${c.n}\n  fields: ${fields}` + (notices.length ? '\n  NOTICE: ' + notices.join('\n  NOTICE: ') : '') + '\n' + tiers.join('\n'));
  }

  // evidence browser: every histology renders tabs; a trial link from the ranker opens the right page
  await p.evaluate(() => switchView('browser'));
  for (const h of await p.$$eval('#hswitch button', bs => bs.map(x => x.dataset.hist))) {
    await p.click(`#hswitch button[data-hist="${h}"]`); await p.waitForTimeout(120);
    const tabs = await p.$$eval('#tabs [role=tab]', t => t.length);
    const cards = await p.$$eval('#panels .card', c => c.length);
    console.log(`browser ${h}: ${tabs} tabs, ${cards} cards`);
    if (!tabs) errs.push(`browser ${h}: no tabs`);
  }
  await p.evaluate(() => switchView('ranker'));
  await p.evaluate(x => applyPreset(x), CASES.find(c => c.n.startsWith('GCT 1L dysger')).p);
  const tl = await p.$('#results .tlink');
  if (tl) {
    await tl.click(); await p.waitForTimeout(250);
    const s = await p.evaluate(() => ({ browser: document.querySelector('#viewBrowser').classList.contains('on'), hist: browserHist, tab: state.tab }));
    console.log('trial link →', JSON.stringify(s));
    if (!s.browser || s.hist !== 'GCT') errs.push('trial link did not open the GCT evidence page');
  }
  await p.close();

  // phone width: no horizontal page scroll
  const ph = await page(390, 844);
  for (const c of [CASES[0], CASES[CASES.length - 1]]) {
    await ph.evaluate(x => applyPreset(x), c.p); await ph.waitForTimeout(80);
    const sw = await ph.evaluate(() => document.documentElement.scrollWidth);
    console.log(`phone ${c.n}: scrollWidth ${sw}`);
    if (sw > 390) errs.push(`phone overflow ${sw}px on ${c.n}`);
  }
  await b.close();
  console.log(errs.length ? 'FAIL\n' + errs.join('\n') : 'OK — no page or console errors');
  process.exit(errs.length ? 1 : 0);
})();
