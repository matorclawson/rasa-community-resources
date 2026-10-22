#!/usr/bin/env node
// sow: software-factories-masterclass-SOW-02
// Export all 30 current illustrations as independent, staged 1000x400 SVGs.
// Rasa-ops retains the exact title/body/diagram labels and final publication.
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const option = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
const source = path.resolve(option('--deck', 'index.html'));
const output = path.resolve(option('--out', 'staged-pictures-review'));
const original = await fs.readFile(source);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
if (hash(original) !== '20eabce9d3c82617a9bfbb4f2b4c81f620a0a814af895c8df21a3a28489ffec5') throw Error('Different deck revision: rebind current content before exporting');
if (source === path.join(output, 'index.html')) throw Error('Output must be a separate review directory');
const controller = await fs.readFile(path.join(here, 'reveal-navigation.js'), 'utf8');
const css = await fs.readFile(path.join(here, 'style.css'), 'utf8');
const require = createRequire(import.meta.url);
const { chromium } = require(option('--playwright', 'playwright-core'));
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, reducedMotion: 'reduce' });
  await page.goto(pathToFileURL(source).href);
  await page.evaluate(async () => { await document.fonts.ready; });
  const exported = await page.evaluate(({ controller, css }) => {
    const ns = 'http://www.w3.org/2000/svg';
    const slides = [...document.querySelectorAll('.slide')];
    if (slides.length !== 30) throw Error('Expected 30 slides');
    const normalized = s => s.replace(/\s+/g, ' ').trim();
    const copy = () => slides.map(s => ({ title: normalized(s.querySelector('h1').textContent),
      body: normalized(s.querySelector('.words')?.textContent || ''), diagram: normalized(s.querySelector('svg.pic').textContent) }));
    const before = copy();
    const stageFor = (slide, el, index, x, y, r) => {
      // Structural panels stay visible while their contents build up.
      if (slide !== 9 && el.tagName === 'rect' && r.width >= 200 && r.height >= 100) return 0;
      if ([1, 4, 7, 26, 30].includes(slide)) return 0;
      if ([2, 3].includes(slide)) {
        if (Math.abs(x - 840) < 185 && Math.abs(y - 330) < 185 && !el.classList.contains('route')) return 0;
        if (el.classList.contains('route')) {
          const m = el.getAttribute('d')?.match(/^M([\d.]+)\s+([\d.]+)/);
          if (m) { x = Number(m[1]); y = Number(m[2]); }
        }
        return y < 330 ? (x < 840 ? 1 : 2) : (x < 840 ? 3 : 4);
      }
      if (slide === 5) return x > 700 ? 2 : y > 250 ? 1 : 0;
      if (slide === 6) return Math.min(3, Math.floor(x / 420));
      if (slide === 8) return y > 520 ? 3 : x < 400 ? 0 : x < 1000 ? 1 : 2;
      if (slide === 9) return el.tagName === 'text' ? 0 : Math.min(3, Math.floor((index - 1) / 3));
      if (slide === 10) return x < 600 ? 0 : x > 1100 ? 3 : y < 330 ? 1 : 2;
      if (slide === 11) return x < 550 ? 0 : x > 1350 ? 2 : 1;
      if ([12, 16, 23].includes(slide)) return x < 840 ? 0 : 1;
      if ([13, 22, 24].includes(slide)) {
        const column = Math.min(3, Math.max(0, Math.floor(x / 420)));
        return el.classList.contains('route') ? Math.min(3, column + 1) : column;
      }
      if ([14, 21].includes(slide)) return x < 560 ? 0 : x < 1120 ? 1 : 2;
      if (slide === 15) {
        if (x > 1400 || el.textContent.trim() === 'Decision') return 3;
        return x > 950 ? 0 : x < 430 ? 1 : 2;
      }
      if ([17, 25].includes(slide)) return Math.min(2, Math.max(0, Math.floor(x / 560)));
      if (slide === 18) return x < 400 ? 0 : x > 1050 ? 3 : y < 330 ? 1 : 2;
      if ([19, 20].includes(slide)) return x > 1050 ? 1 : 0;
      if (slide === 27) return Math.min(4, Math.max(0, Math.floor((x - 40) / 325)));
      if (slide === 28) return y < 180 ? 0 : y < 400 ? 1 : 2;
      if (slide === 29) return y < 200 ? 0 : y < 360 ? 1 : 2;
      return 0;
    };
    const properties = ['fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-opacity', 'stroke-linecap',
      'stroke-linejoin', 'stroke-dasharray', 'font-family', 'font-size', 'font-weight', 'font-style',
      'letter-spacing', 'text-anchor', 'dominant-baseline'];
    const result = [];
    for (const [index, slide] of slides.entries()) {
      // Temporarily expose the source so computed styles and screen transforms
      // are real for every slide. Do not run another writer's generator.
      slide.classList.add('on');
      const svg = slide.querySelector('svg.pic');
      const inverse = svg.getScreenCTM().inverse();
      const clone = svg.cloneNode(true);
      const originals = [svg, ...svg.querySelectorAll('*')];
      const clones = [clone, ...clone.querySelectorAll('*')];
      originals.forEach((el, i) => {
        if (el.tagName === 'defs' || el.tagName === 'title' || el.tagName === 'desc') return;
        const computed = getComputedStyle(el);
        for (const property of properties) {
          const value = computed.getPropertyValue(property);
          if (value) clones[i].style.setProperty(property, value);
        }
        if (el.tagName === 'text') clones[i].setAttribute('font-size', parseFloat(computed.fontSize));
        clones[i].removeAttribute('class');
      });
      clone.setAttribute('class', 'pic'); clone.setAttribute('viewBox', '0 0 1000 400');
      clone.setAttribute('preserveAspectRatio', 'xMidYMid meet');
      clone.removeAttribute('width'); clone.removeAttribute('height');
      const children = [...svg.children];
      const clonedChildren = [...clone.children];
      const wrapper = document.createElementNS(ns, 'g');
      wrapper.setAttribute('transform', 'translate(0 3.5714285714) scale(0.5952380952)');
      const steps = [];
      children.forEach((el, childIndex) => {
        const cloned = clonedChildren[childIndex];
        if (!(el instanceof SVGGraphicsElement) || ['defs', 'title', 'desc'].includes(el.tagName)) { wrapper.append(cloned); return; }
        const bounds = el.getBoundingClientRect();
        const point = new DOMPoint(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2).matrixTransform(inverse);
        const local = el.getBBox();
        let step = stageFor(index + 1, el, childIndex, point.x, point.y, local);
        if (childIndex === 0 && el.tagName === 'rect') step = 0;
        if (step > 0) {
          const group = document.createElementNS(ns, 'g');
          group.setAttribute('class', 'step'); group.setAttribute('data-s', String(step));
          group.append(cloned); wrapper.append(group); steps.push(step);
        } else wrapper.append(cloned);
      });
      clone.replaceChildren(wrapper);
      // CSS classes are now resolved into inline presentation styles. Host
      // fonts remain the exact deck's already embedded OFL fallback faces.
      const serialized = new XMLSerializer().serializeToString(clone);
      if (/(?:href|src)\s*=|url\s*\(/i.test(serialized)) throw Error(`External/reference dependency on slide ${index + 1}`);
      if (normalized(svg.textContent) !== normalized(clone.textContent)) throw Error(`Diagram wording changed on slide ${index + 1}`);
      svg.replaceWith(clone);
      // The detached source retains the captured numeric font-size attributes
      // only through its clone. Measure those explicit values after export.
      const exportedMinimum = Math.min(...[...clone.querySelectorAll('text')].map(t => Number(t.getAttribute('font-size')) * 0.5952380952));
      if (exportedMinimum < 17) throw Error(`Picture text under 17 normalized units on slide ${index + 1}`);
      result.push({ slide: index + 1, name: `${String(index + 1).padStart(2, '0')}.svg`, svg: serialized,
        maximumStep: Math.max(0, ...steps), minimumEffectiveFontUnits: exportedMinimum, diagramCopy: normalized(clone.textContent) });
      slide.classList.remove('on');
    }
    if (JSON.stringify(before) !== JSON.stringify(copy())) throw Error('Teaching copy changed');
    const totals = {}, seen = {};
    slides.forEach(slide => {
      const label = slide.querySelector('.crumb span'); const part = label.textContent.match(/^Part ([1-8]) of 8/)[1];
      totals[part] = (totals[part] || 0) + 1;
    });
    slides.forEach(slide => {
      const label = slide.querySelector('.crumb span'); const part = label.textContent.match(/^Part ([1-8]) of 8/)[1];
      const position = seen[part] = (seen[part] || 0) + 1;
      label.textContent += ` · Slide ${position} of ${totals[part]}`;
    });
    // Keep the licensed font faces embedded; bind the canonical LOOK file as
    // a local offline stylesheet. SVG artwork is inlined by the owner's
    // generator so reveal groups remain in the page DOM.
    const fontFaces = [...document.querySelectorAll('style')].flatMap(style =>
      [...style.textContent.matchAll(/@font-face\{[^}]+\}/g)].map(match => match[0])).join('\n');
    document.querySelectorAll('style').forEach(style => style.remove());
    const fonts = document.createElement('style'); fonts.textContent = fontFaces; document.head.append(fonts);
    const styleLink = document.createElement('link'); styleLink.rel = 'stylesheet'; styleLink.href = './style.css'; document.head.append(styleLink);
    document.querySelectorAll('script').forEach(script => script.remove());
    const script = document.createElement('script'); script.textContent = controller; document.body.append(script);
    // Do not execute the new controller inside the old document/listeners.
    // The gate loads this serialized candidate into a fresh browser context.
    slides[0].classList.add('on');
    return { pictures: result, copyPreserved: true, partPositions: true, html: '<!doctype html>\n' + document.documentElement.outerHTML };
  }, { controller, css });
  await fs.mkdir(path.join(output, 'art'), { recursive: true });
  for (const picture of exported.pictures) await fs.writeFile(path.join(output, 'art', picture.name), picture.svg + '\n');
  await fs.writeFile(path.join(output, 'index.html'), exported.html);
  await fs.writeFile(path.join(output, 'style.css'), css);
  await fs.copyFile(path.join(here, 'FONT-LICENSES.txt'), path.join(output, 'FONT-LICENSES.txt'));
  await fs.copyFile(path.join(here, 'reveal-navigation.js'), path.join(output, 'reveal-navigation.js'));
  await fs.writeFile(path.join(output, 'receipt.json'), JSON.stringify({ sow: 'software-factories-masterclass-SOW-02',
    parentHead: 'c268eccc202fa892ee222833f9fdb8add57d2c6f', parentHtmlSha256: hash(original), candidateHtmlSha256: hash(exported.html),
    copyPreserved: exported.copyPreserved, partPositions: exported.partPositions,
    pictures: exported.pictures.map(({ svg, ...picture }) => ({ ...picture, sha256: hash(svg + '\n'), bytes: Buffer.byteLength(svg + '\n') })),
    status: 'REVIEW_CANDIDATE_REQUIRES_CONTENT_OWNER_INTEGRATION_AND_EXACT_SUCCESSOR_GATE' }, null, 2) + '\n');
  console.log(`Exported ${exported.pictures.length} pictures into ${output}; teaching copy preserved.`);
} finally { await browser.close(); }
