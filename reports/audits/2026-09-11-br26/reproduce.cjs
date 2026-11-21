// Run: node reproduce.cjs /path/to/business-rules-validator.js
// Executes the actual sibling rule methods with synthetic, root-resolved ordinals.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const sandbox = { module: { exports: {} }, require: () => class {} };
vm.runInNewContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox);
const Validator = sandbox.module.exports;
const cases = [
  { name: 'BR26 implicit-only equal ordinals', rule: 'BR26', values: [[1, true], [1, true]], efsa: false, sibling: true },
  { name: 'BR26 implicit plus explicit equal ordinals', rule: 'BR26', values: [[1, true], [1, false]], efsa: true, sibling: true },
  { name: 'BR26 zero ordinals', rule: 'BR26', values: [[0, false], [0, false]], efsa: false, sibling: false },
  { name: 'BR27 equal decimal ordinals', rule: 'BR27', values: [[1.1, true], [1.1, false]], efsa: false, sibling: true },
  { name: 'BR27 distinct decimal ordinals', rule: 'BR27', values: [[1.1, true], [1.2, false]], efsa: true, sibling: true },
  { name: 'BR27 implicit-only distinct decimals', rule: 'BR27', values: [[1.1, true], [1.2, true]], efsa: false, sibling: false },
];
(async () => {
  for (const c of cases) {
    const v = Object.create(Validator.prototype);
    v.hierarchyHelper = { isDerivative: () => true };
    v.getProcessesWithOrdinalCodes = async () => c.values.map(([ordinalCode, isImplicit], i) => ({ code: `synthetic-${i}`, ordinalCode, isImplicit }));
    v.createWarning = rule => ({ rule });
    const warnings = [];
    await v[`check${c.rule}`]({ code: 'synthetic-derivative' }, c.values.filter(v => !v[1]).map((_, i) => `F28.synthetic-${i}`), warnings);
    const observed = warnings.some(w => w.rule === c.rule);
    assert.equal(observed, c.sibling, c.name);
    console.log(JSON.stringify({ case: c.name, efsaMethodExpected: c.efsa, siblingObserved: observed }));
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
