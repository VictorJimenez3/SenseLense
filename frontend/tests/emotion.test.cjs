const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let result = {expressions:{happy:0.9,neutral:0.1}};
const samples = [], labels = [], timers = [], elements = new Map();
let resolveUpload;
const ctx = {
    URL, performance:{now:()=>10}, console,
    setTimeout(fn){timers.push(fn);return timers.length;}, clearTimeout(){},
    document:{currentScript:{src:'https://example.com/SenseLense/js/emotion.js'},
        getElementById(id){if(!elements.has(id)) elements.set(id,{style:{},textContent:'',innerHTML:''});return elements.get(id);}},
    window:{api:{ingestEvents(_, events){samples.push(...events);return new Promise(resolve=>{resolveUpload=resolve;});}}},
    faceapi:{nets:{tinyFaceDetector:{loadFromUri:async()=>{}},faceExpressionNet:{loadFromUri:async()=>{}}},
        TinyFaceDetectorOptions:class {},detectSingleFace(){return {withFaceExpressions:async()=>result};}},
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('frontend/js/emotion.js','utf8'),ctx);
(async()=>{
    await ctx.window.EmotionTracker.start({readyState:4},7,()=>1234, label=>labels.push(label));
    assert.equal(labels[0],'happy');
    assert.equal(elements.get('expression-status').textContent,'Tracking');
    result = undefined;
    await timers.shift()();
    assert.equal(labels.length,1,'no face does not invent a neutral reading');
    assert.equal(elements.get('expression-status').textContent,'No face detected');
    let stopped=false;
    const finish=ctx.window.EmotionTracker.stop().then(()=>{stopped=true;});
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(stopped,false,'stop drains the final sample upload');
    assert.equal(samples[0].source,'faceapi');
    assert.equal(samples[0].emotion,'happy');
    assert.equal(samples[0].timestamp_ms,1234);
    resolveUpload();await finish;
    assert.equal(stopped,true);
    assert.equal(ctx.window.EmotionTracker.avgValence100(),95);
    console.log('Live expression mapping, no-face handling and final upload passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
