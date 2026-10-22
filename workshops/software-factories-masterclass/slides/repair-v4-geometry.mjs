#!/usr/bin/env node
// sow: software-factories-masterclass-SOW-02
// Exact-source visual repair for rasa-ops' first 30-slide v4 preview.
// Refuse another revision; never overwrite the content owner's deck.
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
const args = process.argv.slice(2);
const option = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
const source = path.resolve(option('--deck', 'index.html'));
const output = path.resolve(option('--out', 'geometry-repair'));
if (source === path.join(output, 'index.html')) throw Error('Output must be separate from the input deck');
const bytes = await fs.readFile(source);
const sourceSha256 = createHash('sha256').update(bytes).digest('hex');
if (sourceSha256 !== '658b68a130a06b5ad46c3d0eb596ff82dc72206ad04d3e3117dc5b978c3e5b52') throw Error('Different deck revision: inspect/rebind the geometry repair before applying');
const require = createRequire(import.meta.url);
const { chromium } = require(option('--playwright', 'playwright-core'));
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, reducedMotion: 'reduce' });
  await page.goto(pathToFileURL(source).href);
  const receipt = await page.evaluate(() => {
    const normalize = text => text.replace(/\s+/g, ' ').trim();
    const content = () => [...document.querySelectorAll('.slide')].map(s => ({ id: s.id,
      title: normalize(s.querySelector('h1').textContent), body: normalize(s.querySelector('.words').textContent),
      diagram: normalize(s.querySelector('svg.pic').textContent) }));
    const before = content();
    const style = document.createElement('style');
    style.textContent = '.slide{padding:6.5vh 6.25vw}';
    document.head.append(style);
    const patches = {
      10: { titles: ['4', '5'], subs: ['pass', 'fail'] },
      12: { titles: ['Claim', 'Proof'], subs: ['“it worked”', 'a test passed'] },
      15: { titles: ['Agent', 'Tests'], subs: ['works here', 'sealed, written first'] },
      16: { titles: ['tests.py'], subs: ['fingerprint ab12', 'fingerprint 9f3c'] },
      19: { titles: ['Tests'], subs: ['the only lit window'] },
      21: { titles: ['Agent'], subs: ['Sam talks to'] },
      25: { titles: ['Time', 'Tool calls'], subs: ['limit'] },
      26: { titles: ['Mantle', 'Agents API'], subs: ['where the agent lives', 'the builder'] },
    };
    for (const [number, patch] of Object.entries(patches)) for (const t of document.querySelectorAll(`#s${number} svg text`)) {
      if (patch.titles.includes(t.textContent)) t.setAttribute('y', Number(t.getAttribute('y')) - 6);
      if (patch.subs.includes(t.textContent)) t.setAttribute('y', Number(t.getAttribute('y')) + 14);
    }
    const subtitle = [...document.querySelectorAll('#s7 svg text')].find(t => t.textContent === 'how do we build agents we can trust?');
    const title = [...document.querySelectorAll('#s7 svg text')].find(t => t.textContent === 'Next');
    if (!subtitle || !title) throw Error('Expected slide 7 preimage missing');
    title.setAttribute('y', '176'); subtitle.textContent = '';
    ['how do we build agents ', 'we can trust?'].forEach((value, index) => {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'tspan');
      line.setAttribute('x', subtitle.getAttribute('x')); line.setAttribute('y', String(220 + index * 29));
      line.textContent = value; subtitle.append(line);
    });
    if (JSON.stringify(before) !== JSON.stringify(content())) throw Error('Instructional wording changed');
    const svg = {};
    for (const number of [7, 10, 12, 15, 16, 19, 21, 25, 26]) {
      const el = document.querySelector(`#s${number} svg.pic`);
      el.removeAttribute('aria-hidden'); el.setAttribute('aria-label', document.querySelector(`#s${number} h1`).textContent);
      svg[number] = el.outerHTML;
    }
    return { copyPreserved: true, slides: before, svg };
  });
  await fs.mkdir(path.join(output, 'pics'), { recursive: true });
  for (const [number, svg] of Object.entries(receipt.svg)) await fs.writeFile(path.join(output, 'pics', `${String(number).padStart(2, '0')}.svg`), svg + '\n');
  await fs.writeFile(path.join(output, 'index.html'), await page.content());
  await fs.writeFile(path.join(output, 'margin-override.css'), '.slide{padding:6.5vh 6.25vw}\n');
  await fs.copyFile(path.join(path.dirname(fileURLToPath(import.meta.url)), 'FONT-LICENSES.txt'), path.join(output, 'FONT-LICENSES.txt'));
  await fs.writeFile(path.join(output, 'receipt.json'), JSON.stringify({ sow: 'software-factories-masterclass-SOW-02', sourceSha256, ...receipt,
    limits: 'Geometry repair only. Body/diagram words unchanged; excess-word failures remain for the content owner. Gate the regenerated deck before preview update.' }, null, 2) + '\n');
  console.log(`Prepared nine SVG drop-ins and margin override in ${output}; all 30 title/body/diagram texts unchanged.`);
} finally { await browser.close(); }
