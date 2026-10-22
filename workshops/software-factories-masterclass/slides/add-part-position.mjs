#!/usr/bin/env node
// sow: software-factories-masterclass-SOW-02
// Restore the operator's within-part breadcrumb without changing teaching copy.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
const args = process.argv.slice(2);
const option = (name, fallback) => args.includes(name) ? args[args.indexOf(name) + 1] : fallback;
const source = path.resolve(option('--deck', 'index.html'));
const output = path.resolve(option('--out', 'part-position-review'));
if (source === path.join(output, 'index.html')) throw Error('Write to a separate review directory');
const original = await fs.readFile(source, 'utf8');
const hash = value => createHash('sha256').update(value).digest('hex');
const expected = '20eabce9d3c82617a9bfbb4f2b4c81f620a0a814af895c8df21a3a28489ffec5';
if (hash(original) !== expected) throw Error('Different deck revision; inspect and rebind before changing navigation');
const pattern = /(<nav class="crumb" aria-label="Where you are"><span>)(Part ([1-8]) of 8 · [^<]+)(<\/span>)/g;
const matches = [...original.matchAll(pattern)];
if (matches.length !== 30) throw Error('Expected all 30 breadcrumb preimages');
const totals = {}, seen = {}, positions = [];
for (const match of matches) totals[match[3]] = (totals[match[3]] || 0) + 1;
const html = original.replace(pattern, (_, before, label, part, after) => {
  const position = seen[part] = (seen[part] || 0) + 1;
  positions.push({ slide: positions.length + 1, part: Number(part), position, total: totals[part] });
  return `${before}${label} · Slide ${position} of ${totals[part]}${after}`;
});
const withoutNav = value => value.replace(/<nav\b[\s\S]*?<\/nav>/g, '');
if (withoutNav(original) !== withoutNav(html)) throw Error('Non-navigation bytes changed');
await fs.mkdir(output, { recursive: true });
await fs.writeFile(path.join(output, 'index.html'), html);
await fs.copyFile(path.join(path.dirname(fileURLToPath(import.meta.url)), 'FONT-LICENSES.txt'), path.join(output, 'FONT-LICENSES.txt'));
await fs.writeFile(path.join(output, 'receipt.json'), JSON.stringify({ sow: 'software-factories-masterclass-SOW-02',
  parentHead: 'c268eccc202fa892ee222833f9fdb8add57d2c6f', parentHtmlSha256: expected,
  candidateHtmlSha256: hash(html), scope: 'Within-part breadcrumb only; all non-navigation bytes identical',
  positions, status: 'REVIEW_CANDIDATE_NOT_PUBLISHED_OR_ACCEPTED' }, null, 2) + '\n');
console.log(`Prepared all 30 within-part counters in ${output}`);
