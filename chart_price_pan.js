/* Price-range panning shared by mouse and one-finger input. No quote mutation. */
(function (root, factory) {
  const createPricePan = factory();
  if (typeof module === 'object' && module.exports) module.exports = createPricePan;
  else root.createAdamPricePan = createPricePan;
})(typeof window === 'object' ? window : globalThis, function () {
  'use strict';
  return function createPricePan({readPricePerPixel, onChange, initialOffset = 0}) {
    let offset = Number.isFinite(initialOffset) ? initialOffset : 0;
    let drag = null;
    const setOffset = value => {
      if (!Number.isFinite(value) || value === offset) return false;
      offset = value;
      onChange(offset);
      return true;
    };
    return {
      get offset() { return offset; },
      begin(x, y) {
        drag = null;
        const step = readPricePerPixel();
        if (![x, y, step].every(Number.isFinite) || step <= 0) return false;
        // Capture the starting scale: recalculating it on every move causes drift.
        drag = {y, offset, step};
        return true;
      },
      move(x, y) {
        if (!drag || ![x, y].every(Number.isFinite)) return false;
        const dy = y - drag.y;
        if (Math.abs(dy) < 4) return false;
        return setOffset(drag.offset + dy * drag.step);
      },
      end() { drag = null; },
      reset() { drag = null; return setOffset(0); },
      autoscaleInfo(baseImplementation) {
        const info = baseImplementation();
        if (!info || !info.priceRange) return info;
        const {minValue, maxValue} = info.priceRange;
        if (![minValue, maxValue].every(Number.isFinite)) return info;
        // Shift the coordinate range, never the series data or the canvas itself.
        return {...info, priceRange: {...info.priceRange,
          minValue: minValue + offset, maxValue: maxValue + offset}};
      }
    };
  };
});
