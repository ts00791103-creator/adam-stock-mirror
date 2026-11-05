const assert = require('node:assert/strict');
const createPricePan = require('../chart_price_pan.js');
let passed = 0;
function test(name, run) { run(); passed++; }
function controller(step = 2, initialOffset = 0) {
  const changes = [];
  const pan = createPricePan({readPricePerPixel: () => step,
    onChange: value => changes.push(value), initialOffset});
  return {pan, changes};
}
test('down/up drag shifts the range in price units', () => {
  const {pan} = controller();
  pan.begin(100, 100); pan.move(100, 120);
  assert.equal(pan.offset, 40);
  pan.move(100, 80); assert.equal(pan.offset, -40);
});
test('mouse move events do not accumulate scale drift', () => {
  const {pan} = controller();
  pan.begin(100, 100); pan.move(120, 120); pan.move(140, 130);
  assert.equal(pan.offset, 60);
  pan.end(); pan.begin(140, 130); pan.move(150, 140);
  assert.equal(pan.offset, 80);
});
test('horizontal motion and small jitter leave price scale unchanged', () => {
  const {pan, changes} = controller();
  pan.begin(100, 100); pan.move(300, 100); pan.move(400, 103);
  assert.equal(pan.offset, 0); assert.deepEqual(changes, []);
});
test('returning to the drag origin restores the starting range', () => {
  const {pan} = controller(2, 30);
  pan.begin(100, 100); pan.move(100, 150); pan.move(100, 101); pan.move(100, 100);
  assert.equal(pan.offset, 30);
});
test('cancel before multitouch prevents stale one-finger panning', () => {
  const {pan} = controller();
  pan.begin(0, 0); pan.move(0, 20); pan.end(); pan.move(0, 100);
  assert.equal(pan.offset, 40);
});
test('autoscale provider preserves base data and margins', () => {
  const {pan} = controller(2, 40);
  const base = {priceRange: {minValue: -20, maxValue: 100}, margins: {above: 10, below: 20}};
  const copy = JSON.stringify(base);
  const result = pan.autoscaleInfo(() => base);
  assert.deepEqual(result.priceRange, {minValue: 20, maxValue: 140});
  assert.deepEqual(result.margins, base.margins);
  assert.equal(JSON.stringify(base), copy);
  assert.equal(result.priceRange.maxValue - result.priceRange.minValue, 120);
});
test('all price series receive the same offset', () => {
  const {pan} = controller(1, -50);
  assert.deepEqual(pan.autoscaleInfo(() => ({priceRange:{minValue:100,maxValue:200}})).priceRange,
    {minValue:50,maxValue:150});
  assert.deepEqual(pan.autoscaleInfo(() => ({priceRange:{minValue:300,maxValue:400}})).priceRange,
    {minValue:250,maxValue:350});
});
test('empty ranges and invalid input are safe', () => {
  const {pan} = controller(null, NaN);
  assert.equal(pan.begin(0, 0), false); assert.equal(pan.offset, 0);
  assert.equal(pan.move(0, 100), false);
  assert.equal(pan.autoscaleInfo(() => null), null);
  assert.deepEqual(pan.autoscaleInfo(() => ({margins: {above:0}})), {margins:{above:0}});
});
test('reset clears offset and active drag', () => {
  const {pan, changes} = controller();
  pan.begin(0, 0); pan.move(0, 10); pan.reset(); pan.move(0, 30);
  assert.equal(pan.offset, 0); assert.deepEqual(changes, [20, 0]);
});
console.log(`${passed} price pan behavior tests passed`);
module.exports = {passed};
