#!/usr/bin/env node
// sow: software-factories-masterclass-SOW-02
// Browser-level teaching/navigation contract for the staged c268 illustrations.
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
const args = process.argv.slice(2);
const option = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
const source = path.resolve(option('--deck', 'index.html'));
const output = path.resolve(option('--out', 'reveal-navigation-evidence'));
const require = createRequire(import.meta.url);
const { chromium } = require(option('--playwright', 'playwright-core'));
const browser = await chromium.launch({ headless: true });
const observations = [];
try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, reducedMotion: 'reduce' });
  await page.goto(pathToFileURL(source).href);
  await page.evaluate(async () => { await document.fonts.ready; });
  const observe = async (name, expectedSlide, required = [], absent = []) => {
    const actual = await page.evaluate(() => {
      const slides = [...document.querySelectorAll('.slide')];
      const slide = slides.find(s => getComputedStyle(s).display !== 'none');
      return { slide: slide?.id, count: slides.length, hash: location.hash,
        text: [...(slide?.querySelectorAll('svg text') || [])].filter(t => getComputedStyle(t).visibility !== 'hidden')
          .map(t => t.textContent.replace(/\s+/g, ' ').trim()) };
    });
    const passed = actual.count === 30 && actual.slide === `s${expectedSlide}` && actual.hash === `#${expectedSlide}`
      && required.every(label => actual.text.includes(label)) && absent.every(label => !actual.text.includes(label));
    observations.push({ name, passed, expectedSlide, required, absent, actual });
    if (!passed) throw Error(`Reveal/navigation contract failed: ${name}`);
  };
  const go = async number => {
    await page.evaluate(n => { location.hash = String(n); }, number);
    await page.waitForFunction(n => document.querySelector('.slide.on')?.id === `s${n}`, number);
  };
  await page.keyboard.press('Home');
  await observe('Home opens the complete cover', 1, ['Flight', 'Weather', 'Timing', 'Money']);
  await page.keyboard.press('ArrowRight');
  await observe('Sam precedes the four sources', 2, [], ['Flight', 'Weather', 'Timing', 'Money']);
  const sources = ['Flight', 'Weather', 'Timing', 'Money'];
  for (let i = 0; i < sources.length; i++) {
    await page.keyboard.press('ArrowRight');
    await observe(`Source ${i + 1} reveals without advancing slide`, 2, sources.slice(0, i + 1), sources.slice(i + 1));
  }
  await page.keyboard.press('ArrowRight');
  await observe('Only the press after the last reveal advances', 3, [], sources);
  await page.keyboard.press('ArrowLeft');
  await observe('Back from a new slide shows the prior completed diagram', 2, sources);
  await page.keyboard.press('ArrowLeft');
  await observe('Back reverses one reveal, retaining earlier sources', 2, sources.slice(0, 3), ['Money']);
  await go(15);
  await observe('Protected acceptance exists before the builder works', 15, ['Hidden tests'], ['Builder', 'Change', 'Decision']);
  await page.keyboard.press('ArrowRight');
  await observe('Builder arrives after protected tests', 15, ['Hidden tests', 'Builder'], ['Change', 'Decision']);
  await page.keyboard.press('ArrowRight');
  await observe('Change precedes its decision', 15, ['Hidden tests', 'Builder', 'Change'], ['Decision']);
  await page.keyboard.press('ArrowRight');
  await observe('Decision follows the completed change', 15, ['Hidden tests', 'Builder', 'Change', 'Decision']);
  await go(27);
  const chapters = ['Task', 'Tests', 'Builder', 'Checks', 'Integrate'];
  await observe('Factory begins with the task', 27, ['Task'], chapters.slice(1));
  for (let i = 1; i < chapters.length; i++) {
    await page.keyboard.press('ArrowRight');
    await observe(`Factory builds ${chapters[i]} in order`, 27, chapters.slice(0, i + 1), chapters.slice(i + 1));
  }
  await page.keyboard.press('ArrowRight');
  const good = '$ python run_a6.py tasks/a6-market-watchlist.json candidates/market-good';
  const bad = '$ python run_a6.py tasks/a6-market-watchlist.json candidates/market-shows-live';
  await observe('Terminal first shows the working directory', 28, ['$ cd workshops/software-factories-masterclass/factory/a6-market-watchlist'], [good, bad]);
  await page.keyboard.press('ArrowRight');
  await observe('Good command is revealed before the bad command', 28, [good], [bad]);
  await page.mouse.click(1800, 550);
  await observe('Right click reveals the bad command on the same slide', 28, [good, bad]);
  await page.mouse.click(250, 550);
  await observe('Left click reverses that reveal', 28, [good], [bad]);
  await page.keyboard.press('End');
  await observe('End opens the complete closing illustration', 30, sources);
  await page.keyboard.press('Home');
  await observe('Home returns to the cover after the whole journey', 1, sources);
} catch (error) {
  observations.push({ passed: false, error: String(error.stack || error) });
} finally {
  await browser.close();
  await fs.mkdir(output, { recursive: true });
  const passed = observations.length > 0 && observations.every(o => o.passed);
  await fs.writeFile(path.join(output, 'report.json'), JSON.stringify({ sow: 'software-factories-masterclass-SOW-02', source, passed, observations }, null, 2) + '\n');
  console.log(JSON.stringify({ passed, checks: observations.length, report: path.join(output, 'report.json') }));
  if (!passed) process.exitCode = 1;
}
