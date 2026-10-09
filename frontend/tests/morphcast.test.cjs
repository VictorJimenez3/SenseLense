const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
let stopped = 0, events = 0;
const loader = {};
for (const method of ['licenseKey','maxInputFrameSize','powerSave','addModule']) loader[method] = () => loader;
loader.load = async () => ({start() {}, stop() { stopped++; }});
const moduleInfo = {name:'module', eventName:'event'};
const ctx = {
    CY: {loader: () => loader, modules: () => new Proxy({}, {get: () => moduleInfo})},
    window: {addEventListener() {}, api: {ingestEvents: () => {events++; return Promise.resolve();}}},
    document: {getElementById: () => ({style: {}, innerHTML:'', appendChild() {}}), createElement: () => ({})},
    setInterval: () => 1, clearInterval() {}, console,
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('frontend/js/morphcast.js','utf8'), ctx);
(async () => {
    ctx.window.MorphCast.start(1, () => 0);
    await new Promise(resolve => setImmediate(resolve));
    ctx.window.MorphCast.stop();
    assert.equal(stopped, 1, 'stop releases the SDK camera too');
    assert.equal(events, 0, 'no fabricated snapshot when no model data arrived');
    console.log('MorphCast shutdown and empty snapshot passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
