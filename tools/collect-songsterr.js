// 收集 Songsterr 完整譜面。
// Songsterr 只渲染畫面附近的譜行，Ctrl+S 存不到整首。用法：
// 在譜頁按 F12 → Console，貼上整段後按 Enter；完成後會下載一個 .html，交給 songsterr2score 轉換即可。
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const SLOT = '[data-player-key="tab"][data-line-unit-index]';
  const LINE = 'svg[data-testid^="multitrack-line-group-"]';
  const total = document.querySelectorAll(SLOT).length;
  if (!total) return console.error('找不到譜面，請確認目前在 Songsterr 譜頁且譜面已載入');

  const got = new Map();
  const grab = () => document.querySelectorAll(LINE).forEach(s => {
    const i = +s.dataset.testid.split('-').pop();
    if (!got.has(i)) got.set(i, s.outerHTML);
  });

  for (let i = 0; i < total; i++) {
    if (got.has(i)) continue;
    document.querySelector(`${SLOT}[data-line-unit-index="${i}"]`)?.scrollIntoView({ block: 'center' });
    for (let t = 0; t < 50 && !document.querySelector(`svg[data-testid="multitrack-line-group-${i}"]`); t++) await sleep(100);
    grab();
    console.log(`收集中 ${got.size}/${total}`);
  }

  const missing = [...Array(total).keys()].filter(i => !got.has(i));
  if (missing.length) console.warn('以下譜行沒有收集到（行號從 0 起算）：', missing);

  const page = document.documentElement.cloneNode(true);
  page.querySelectorAll(LINE).forEach(s => s.remove());
  const box = document.createElement('div');
  box.id = 'songsterr2score-lines';
  box.innerHTML = [...got.keys()].sort((a, b) => a - b).map(i => got.get(i)).join('\n');
  page.querySelector('body').append(box);

  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob(['<!DOCTYPE html>\n' + page.outerHTML], { type: 'text/html' }));
  a.download = document.title.split('|')[0].trim().replace(/[\\/:*?"<>|]/g, '_') + '.html';
  a.click();
  console.log(`完成：${got.size}/${total} 行，已下載 ${a.download}`);
})();
