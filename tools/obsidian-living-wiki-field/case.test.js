'use strict';
const test = require('node:test');
const assert = require('node:assert');
const Module = require('node:module');
const load = Module._load;
Module._load = (name, ...rest) => name === 'obsidian' ? {ItemView: class {}, TFile: class {}, parseYaml: () => ({})} : load(name, ...rest);
const {markGaps} = require('./case.js');
Module._load = load;

const fakeEl = () => ({marks: [], text: '', createEl(_t, o) { this.marks.push(o.text); return this; }, appendText(t) { this.text += t; }});

test('words absent from the source are marked, shared words are not', () => {
  const el = fakeEl();
  const gaps = markGaps(el, "After the director's note, the second scene was rewritten.", 'the second scene changed after a recorded discussion.');
  assert.deepStrictEqual(gaps, ["director's", 'note', 'rewritten']);
  assert.ok(el.text.includes('second'));
});

test('a claim fully covered by its source has no gaps', () => {
  assert.deepStrictEqual(markGaps(fakeEl(), 'The second scene changed.', 'the second scene changed after a recorded discussion'), []);
});
