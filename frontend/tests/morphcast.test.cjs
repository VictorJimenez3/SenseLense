const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
let stopped = 0, events = 0;
const listeners = {};
let observedEmotion;
const loader = {};
for (const method of ['licenseKey','maxInputFrameSize','powerSave','addModule']) loader[method] = () => loader;
loader.load = async () => ({start() {}, stop() { stopped++; }});
const moduleInfo = name => ({name, eventName:name});
const ctx = {
    CY: {loader: () => loader, modules: () => new Proxy({}, {get: (_, name) => moduleInfo(name)})},
    window: {addEventListener(name, handler) {listeners[name] = handler;}, api: {ingestEvents: () => {events++; return Promise.resolve();}}},
    document: {getElementById: () => ({style: {}, innerHTML:'', appendChild() {}}), createElement: () => ({})},
    setInterval: () => 1, clearInterval() {}, console,
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('frontend/js/morphcast.js','utf8'), ctx);
(async () => {
    ctx.window.MorphCast.start(1, () => 0, emotion => {observedEmotion = emotion;});
    await new Promise(resolve => setImmediate(resolve));
    listeners.FACE_EMOTION({detail:{output:{dominantEmotion:"Happy", emotion:{Happy:0.9}}}});
    assert.equal(observedEmotion, "happy", "MorphCast supplies the primary tracker");
    ctx.window.MorphCast.stop();
    assert.equal(stopped, 1, 'stop releases the SDK camera too');
    assert.equal(events, 0, 'no fabricated snapshot when no model data arrived');
    console.log('MorphCast shutdown and empty snapshot passed');
    let completeUpload;
    ctx.window.api.ingestEvents = (_, samples) => {
        assert.equal(samples[0].source, 'morphcast');
        assert.equal(samples[0].emotion, 'happy');
        assert.equal(samples[0].valence, 0.4);
        return new Promise(resolve => {completeUpload = resolve;});
    };
    ctx.window.MorphCast.start(2, () => 1000);
    await new Promise(resolve => setImmediate(resolve));
    listeners.FACE_EMOTION({detail:{output:{dominantEmotion:'Happy',emotion:{Happy:0.9}}}});
    listeners.FACE_AROUSAL_VALENCE({detail:{output:{valence:0.4}}});
    assert.equal(ctx.window.MorphCast.avgValence100(), 70);
    let drained = false;
    const finish = ctx.window.MorphCast.stop().then(() => {drained = true;});
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(drained, false, 'ending waits for the final MorphCast snapshot');
    completeUpload();
    await finish;
    assert.equal(drained, true);
    console.log('MorphCast final snapshot persisted before ending');
})().catch(error => { console.error(error); process.exitCode = 1; });
