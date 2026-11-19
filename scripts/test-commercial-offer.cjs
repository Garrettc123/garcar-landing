'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const checkout = fs.readFileSync(path.join(root, 'checkout.html'), 'utf8');
const readme = fs.readFileSync(path.join(root, 'README.md'), 'utf8');

const reviewLink = 'https://buy.stripe.com/8x2eVddjf0hQ86Tf0f43S2h';
const installLink = 'https://buy.stripe.com/14AdR95QN3u2af14lB43S2j';
const alternativeInstallLink = 'https://buy.stripe.com/6oUaEX4MJ0hQevhf0f43S2i';

assert.match(index, /Lead Follow-Up Review/);
assert.match(index, /\$497/);
assert.match(index, /\$2,500/);
assert.doesNotMatch(index, /\$299|ten-day turnaround/i,
  'The canonical home page must not advertise the deprecated $299 audit');
assert.ok(index.includes(reviewLink), 'The $497 review checkout must be linked');
assert.ok(index.includes(installLink), 'The $2,500 installation checkout must be linked');

assert.match(checkout, /Lead Follow-Up Review/);
assert.match(checkout, /Start the \$497 review/);
assert.ok(checkout.includes(reviewLink), 'Checkout review link changed');
assert.ok(checkout.includes(alternativeInstallLink), 'Checkout installation link changed');

for (const [fileName, html] of [['index.html', index], ['checkout.html', checkout]]) {
  assert.match(html, /\$497 credit/i, fileName + ': credit terms missing');
  assert.match(html, /invoice/i, fileName + ': invoice requirement missing');
  assert.match(html, /full-price/i, fileName + ': double-payment warning missing');
}
assert.ok(readme.includes('does not currently call'), 'Document the static checkout behavior');
console.log('Commercial offer regression checks passed (static source only).');
