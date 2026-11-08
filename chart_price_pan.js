/* Price-range panning shared by mouse and one-finger input. No quote mutation. */
(function (root, factory) {
  const createPricePan = factory();
  if (typeof module === 'object' && module.exports) module.exports = createPricePan;
  else root.createAdamPricePan = createPricePan;
})(typeof window === 'object' ? window : globalThis, function () {
  'use strict';
  function createPricePan({readPricePerPixel, onChange, initialOffset = 0, readAdditionalRange = () => null}) {
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
        drag = {y, offset, step, active: false};
        return true;
      },
      move(x, y) {
        if (!drag || ![x, y].every(Number.isFinite)) return false;
        const dy = y - drag.y;
        if (!drag.active && Math.abs(dy) < 4) return false;
        drag.active = true;
        return setOffset(drag.offset + dy * drag.step);
      },
      end() { drag = null; },
      reset() { drag = null; return setOffset(0); },
      autoscaleInfo(baseImplementation) {
        const info = baseImplementation();
        if (!info || !info.priceRange) return info;
        const {minValue, maxValue} = info.priceRange;
        if (![minValue, maxValue].every(Number.isFinite)) return info;
        // Include visible active overlays before applying the user's vertical offset.
        const extra = readAdditionalRange();
        const valid = extra && Number.isFinite(extra.minValue) && Number.isFinite(extra.maxValue)
          && extra.maxValue >= extra.minValue;
        const low = valid ? Math.min(minValue, extra.minValue) : minValue;
        const high = valid ? Math.max(maxValue, extra.maxValue) : maxValue;
        // Shift the coordinate range, never the series data or the canvas itself.
        return {...info, priceRange: {...info.priceRange,
          minValue: low + offset, maxValue: high + offset}};
      }
    };
  }
  createPricePan.activeBoxRange = (boxes, visible) => {
    if (!visible || !Number.isFinite(visible.from) || !Number.isFinite(visible.to)) return null;
    const relevant = (boxes || []).filter(b => (b.active === true || (b.active === undefined && b.status === '整理中'))
      && [b.start,b.end,b.bottom,b.top].every(Number.isFinite)
      && b.top >= b.bottom && b.start <= visible.to && b.end >= visible.from);
    if (!relevant.length) return null;
    return {minValue: Math.min(...relevant.map(b => b.bottom)),
      maxValue: Math.max(...relevant.map(b => b.top))};
  };
  return createPricePan;
});
