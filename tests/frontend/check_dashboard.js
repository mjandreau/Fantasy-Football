/*
 * Executes the ACTUAL built dashboard/index.html in jsdom, clicks every tab,
 * and checks the Playoff Odds tab against the payload it was built from.
 *
 * Python tests cannot catch a dashboard that parses its data wrongly, renders
 * an empty panel, or throws on a tab nobody clicked -- this can, and it runs
 * the shipped bytes rather than a template.
 *
 *   npm install jsdom
 *   node tests/frontend/check_dashboard.js dashboard/index.html
 *
 * Exits non-zero on any console error, empty tab, or payload mismatch.
 */
const fs = require('fs');
const { JSDOM, VirtualConsole } = require('jsdom');

const file = process.argv[2] || 'dashboard/index.html';
const html = fs.readFileSync(file, 'utf8');
const errors = [];

const vc = new VirtualConsole();
vc.on('jsdomError', e => errors.push('jsdomError: ' + (e.stack || e.message)));
vc.on('error', (...a) => errors.push('console.error: ' + a.join(' ')));

const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  virtualConsole: vc,
  pretendToBeVisual: true,
  beforeParse(window) {
    // jsdom has no canvas. Stub Chart.js and record every chart config so we
    // can assert on the data the page asked to draw.
    window.__charts = [];
    function Chart(ctx, cfg) {
      window.__charts.push(cfg);
      this.destroy = () => {}; this.resize = () => {}; this.update = () => {};
    }
    Chart.getChart = () => null;
    Chart.register = () => {};
    Chart.defaults = { font: {}, plugins: { legend: { labels: {} } }, scale: { grid: {} } };
    window.Chart = Chart;
    window.HTMLCanvasElement.prototype.getContext = () => ({
      save() {}, restore() {}, clearRect() {}, fillRect() {},
      measureText: () => ({ width: 0 }),
    });
  },
});
const { window } = dom;
window.addEventListener('error', e => errors.push('window error: ' + (e.error?.stack || e.message)));

function payload() {
  const m = html.match(/\/\*DATA_START\*\/([\s\S]*?)\/\*DATA_END\*\//);
  if (!m) throw new Error('data markers not found');
  // The injector escapes "</" as "<\/" so a team name cannot close the script
  // tag; JSON.parse accepts both, but undo it here to mirror the page exactly.
  return JSON.parse(m[1].replace(/<\\\//g, '</'));
}

function checkTabs(doc) {
  const buttons = [...doc.querySelectorAll('.nav-btn[data-tab]')];
  if (!buttons.length) { errors.push('no tab buttons found'); return; }
  console.log(`tabs: ${buttons.length}`);
  for (const b of buttons) {
    const before = errors.length;
    try { b.click(); } catch (err) { errors.push(`click "${b.dataset.tab}" threw: ${err.stack}`); }
    const panel = doc.getElementById('tab-' + b.dataset.tab);
    const filled = panel ? panel.textContent.trim().length : 0;
    if (filled < 40) errors.push(`tab "${b.dataset.tab}" rendered ${filled} chars — looks empty`);
    console.log(`  ${b.dataset.tab.padEnd(12)} ${String(filled).padStart(7)} chars  ` +
                `${errors.length > before ? 'ERROR' : 'ok'}`);
  }
}

function checkOdds(doc, ODDS) {
  if (!ODDS || !ODDS.seasons?.length) { console.log('odds: no payload, skipping'); return; }
  doc.querySelector('.nav-btn[data-tab="odds"]').click();
  const panel = doc.getElementById('tab-odds');
  const years = [...panel.querySelectorAll('.subnav-btn')].map(b => b.dataset.id);
  if (years.length !== ODDS.seasons.length)
    errors.push(`odds: ${years.length} season pills for ${ODDS.seasons.length} seasons`);

  for (const y of years) {
    window.__charts.length = 0;
    panel.querySelector(`.subnav-btn[data-id="${y}"]`).click();
    const S = ODDS.by_season[y];
    const curve = window.__charts.find(c => c.type === 'line');
    if (!curve) { errors.push(`${y}: no odds curve drawn`); continue; }

    if (curve.data.labels.length !== S.reg_weeks + 1)
      errors.push(`${y}: ${curve.data.labels.length} curve points, expected ${S.reg_weeks + 1}`);
    if (curve.data.datasets.length !== S.owners.length * 2)
      errors.push(`${y}: ${curve.data.datasets.length} datasets, expected ${S.owners.length * 2} (live + hindsight)`);

    if (!S.in_progress) {
      const finals = curve.data.datasets.filter(d => !d._hindsight).map(d => d.data.at(-1));
      const undecided = finals.filter(v => v !== 0 && v !== 100);
      if (undecided.length) errors.push(`${y}: final-week odds not settled: ${undecided}`);
      const made = finals.filter(v => v === 100).length;
      if (made !== S.playoff_spots) errors.push(`${y}: ${made} teams at 100%, expected ${S.playoff_spots}`);
    }

    const luck = [...panel.querySelectorAll('table.data-table')]
      .find(t => [...t.querySelectorAll('th')].some(th => th.textContent.includes('Luck')));
    if (!luck) { errors.push(`${y}: no schedule-luck table`); continue; }
    const col = [...luck.querySelectorAll('th')].findIndex(th => th.textContent.includes('Luck'));
    const sum = [...luck.querySelectorAll('tbody tr')]
      .reduce((a, tr) => a + parseFloat(tr.children[col].textContent), 0);
    // Schedule luck is zero-sum: one owner's fortune is another's robbery.
    if (Math.abs(sum) > 0.05) errors.push(`${y}: luck sums to ${sum.toFixed(3)}, expected ~0`);
  }
  console.log(`odds: ${years.length} seasons checked`);
}

function checkDrafts(doc, D) {
  if (!D || !D.years) { console.log('drafts: no payload, skipping'); return; }
  doc.querySelector('.nav-btn[data-tab="drafts"]').click();
  const panel = doc.getElementById('tab-drafts');
  const years = Object.keys(D.years).sort();

  const options = [...panel.querySelectorAll('option')].map(o => o.value).sort();
  if (options.join(',') !== years.join(','))
    errors.push(`drafts: year picker [${options}] does not match payload [${years}]`);

  // The newest draft is the one people open the tab to see.
  const newest = years[years.length - 1];
  const sel = panel.querySelector('select');
  if (sel && sel.value !== newest)
    errors.push(`drafts: board opened on ${sel.value}, expected ${newest}`);
  if (!panel.textContent.includes(D.years[newest].picks[0].player))
    errors.push(`drafts: ${newest} board does not show its first pick`);

  console.log(`drafts: ${years.length} boards (${years[0]}-${newest}), ` +
              `${newest} opens on ${D.years[newest].picks[0].player}`);
}

setTimeout(() => {
  const doc = window.document;
  const css = html.match(/<style>([\s\S]*?)<\/style>/)?.[1] || '';
  if (/max-width:\s*var\(--maxw\)/.test(css)) errors.push('layout: the --maxw width cap is back');
  if (!/--gutter/.test(css)) errors.push('layout: --gutter is not defined');

  checkTabs(doc);
  try { checkDrafts(doc, payload().drafts); }
  catch (err) { errors.push('drafts check threw: ' + err.stack); }
  try { checkOdds(doc, payload().odds); }
  catch (err) { errors.push('odds check threw: ' + err.stack); }

  if (errors.length) {
    console.log(`\nFAIL — ${errors.length} error(s):`);
    errors.slice(0, 20).forEach(e => console.log('  - ' + e.slice(0, 400)));
    process.exit(1);
  }
  console.log('\nPASS — every tab rendered, 0 console errors, odds consistent with payload');
  process.exit(0);
}, 2000);
