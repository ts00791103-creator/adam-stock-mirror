/* Execute the actual generated chart scripts against a small chart/DOM adapter. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'mobile_chart.py'), 'utf8');
const template = source.match(/html = """([\s\S]*?)"""/)[1];
function render(width, empty = false) {
  const elements = new Map();
  const element = () => ({style:{},clientWidth:width,clientHeight:480,textContent:'',
    appendChild(){},replaceChildren(){},setAttribute(){},addEventListener(){},
    getBoundingClientRect(){return {left:0,top:0};}});
  const chartElement = element(); elements.set('chart', chartElement);
  const series = [];
  function add(type, options) {
    const item = {type,options:{...options},setData(){},
      applyOptions(value){Object.assign(this.options,value);},
      coordinateToPrice:y=>200-y,priceToCoordinate:p=>200-p};
    series.push(item); return item;
  }
  const time = {width:()=>chartElement.clientWidth-50,height:()=>30,
    timeToCoordinate:()=>100,subscribeVisibleLogicalRangeChange(){},setVisibleLogicalRange(){}};
  const chart = {addCandlestickSeries:o=>add('candle',o),addHistogramSeries:o=>add('volume',o),
    addLineSeries:o=>add('line',o),priceScale:()=>({applyOptions(){}}),timeScale:()=>time,
    subscribeCrosshairMove(){},applyOptions(){}};
  let resize;
  const context = {
    console,Number,Map,Math,Date,JSON,
    document:{getElementById(id){if(!elements.has(id))elements.set(id,element());return elements.get(id);},
      createElement:element,createElementNS:element},
    LightweightCharts:{createChart:()=>chart,CrosshairMode:{Normal:0},LineStyle:{Dashed:2,Dotted:1,Solid:0}},
    sessionStorage:{getItem:()=>null,setItem(){}},addEventListener(){},
    requestAnimationFrame:()=>1,setTimeout:()=>1,clearTimeout(){},
    ResizeObserver:class {constructor(callback){resize=callback;}observe(){}}
  };
  context.window = context;
  const data = {dark:true,title:'2330.TW',rendererVersion:'TEST',viewportKey:'test',count:60,
    bars:empty?[]:[{time:1791158400,open:99,high:102,low:98,close:100},
      {time:1791244800,open:101,high:112,low:100,close:110}],
    volumes:empty?[]:[{time:1791158400,value:500},{time:1791244800,value:600}],
    volumeMA5:[],volumeMA20:[],volumeUnit:'張',boxes:[],mirrorSummary:[],
    lines:[{name:'短波左右鏡像',color:'#00ff00',points:[{time:1791244800,value:110}]}]};
  const html = template.replace('PAN_SCRIPT',fs.readFileSync(path.join(root,'chart_price_pan.js'),'utf8'))
    .replace('PAYLOAD',JSON.stringify(data));
  vm.createContext(context);
  for(const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g))vm.runInContext(match[1],context);
  return {elements,series,resize:()=>resize(),chartElement};
}
const narrow = render(390);
const initial = narrow.elements.get('ohlc').textContent;
assert.ok(initial.includes('10.00%'), initial);
assert.ok(initial.includes('量 600 張'), initial);
const line = narrow.series.find(s=>s.type==='line');
assert.equal(line.options.title,'');
const provider = line.options.autoscaleInfoProvider;
narrow.chartElement.clientWidth=1000; narrow.resize();
assert.equal(line.options.title,'短波左右鏡像');
assert.equal(line.options.autoscaleInfoProvider,provider);
narrow.chartElement.clientWidth=390; narrow.resize();
assert.equal(line.options.title,'');
assert.equal(render(1000).series.find(s=>s.type==='line').options.title,'短波左右鏡像');
assert.doesNotThrow(()=>render(390,true));
console.log('Chart initial OHLC, responsive labels, and empty data checks passed');
module.exports = {passed:true};
