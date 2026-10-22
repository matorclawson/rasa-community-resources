#!/usr/bin/env node
// sow: software-factories-masterclass-SOW-02
// Browser-level teaching/navigation contract for the staged ce0b5d4 illustrations.
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
  await go(3);
  await observe('Sam precedes the four sources', 3, [], ['Flight', 'Weather', 'Timing', 'Money']);
  const sources = ['Flight', 'Weather', 'Timing', 'Money'];
  for (let i = 0; i < sources.length; i++) {
    await page.keyboard.press('ArrowRight');
    await observe(`Source ${i + 1} reveals without advancing slide`, 3, sources.slice(0, i + 1), sources.slice(i + 1));
  }
  await page.keyboard.press('ArrowRight');
  await observe('Only the press after the last reveal advances', 4, sources);
  await page.keyboard.press('ArrowLeft');
  await observe('Back from a new slide shows the prior completed diagram', 3, sources);
  await page.keyboard.press('ArrowLeft');
  await observe('Back reverses one reveal, retaining earlier sources', 3, sources.slice(0, 3), ['Money']);
  await go(14);
  await observe('Protected acceptance exists before the builder works', 14, ['Hidden tests'], ['Builder', 'Change', 'Decision']);
  await page.keyboard.press('ArrowRight');
  await observe('Builder arrives after protected tests', 14, ['Hidden tests', 'Builder'], ['Change', 'Decision']);
  await page.keyboard.press('ArrowRight');
  await observe('Change precedes its decision', 14, ['Hidden tests', 'Builder', 'Change'], ['Decision']);
  await page.keyboard.press('ArrowRight');
  await observe('Decision follows the completed change', 14, ['Hidden tests', 'Builder', 'Change', 'Decision']);
  await go(25);
  const chapters = ['Task', 'Tests', 'Builder', 'Checks', 'Integrate'];
  await observe('Factory begins with the task', 25, ['Task'], chapters.slice(1));
  for (let i = 1; i < chapters.length; i++) {
    await page.keyboard.press('ArrowRight');
    await observe(`Factory builds ${chapters[i]} in order`, 25, chapters.slice(0, i + 1), chapters.slice(i + 1));
  }
  await page.keyboard.press('ArrowRight');
  const good = '$ python run_a6.py tasks/a6-market-watchlist.json candidates/market-good';
  const bad = '$ python run_a6.py tasks/a6-market-watchlist.json candidates/market-shows-live';
  await observe('Terminal first shows the environment activation', 26, ['$ source .venv/bin/activate'], [good, bad]);
  await page.keyboard.press('ArrowRight');
  await observe('Good command is revealed before the bad command', 26, [good], [bad]);
  await page.mouse.click(1800, 550);
  await observe('Right click reveals the bad command on the same slide', 26, [good, bad]);
  await page.mouse.click(250, 550);
  await observe('Left click reverses that reveal', 26, [good], [bad]);
  await go(27);
  await observe('Integration begins with the request', 27, ['Request'], ['Gates', 'If accepted']);
  await page.keyboard.press('ArrowRight');
  await observe('Checks precede acceptance', 27, ['Request', 'Gates'], ['If accepted']);
  await page.keyboard.press('ArrowRight');
  await observe('Acceptance follows the gates', 27, ['Request', 'Gates', 'If accepted']);
  await go(28);
  const clone = '$ git clone https://github.com/RasaHQ/rasa-community-resources.git';
  const directory = '$ cd rasa-community-resources/workshops/software-factories-masterclass/book';
  const license = 'license: rasa.com/rasa-pro-developer-edition-license-key-request';
  await observe('Book setup starts with the clone', 28, [clone], [directory, license]);
  await page.keyboard.press('ArrowRight');
  await observe('Book directory follows the clone', 28, [clone, directory], [license]);
  await page.keyboard.press('ArrowRight');
  await observe('License direction completes setup', 28, [clone, directory, license]);
  await page.keyboard.press('End');
  await observe('End opens the current wordless closing illustration', 30);
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
