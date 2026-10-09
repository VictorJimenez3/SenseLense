// Exercise actual recorder logic without accessing a camera or external services.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('frontend/record.html', 'utf8');
const start = html.indexOf('function startMicRecording(');
const end = html.indexOf('// ── Transcript poll', start);
let recorder;
let receivedOffset;
const context = {
    recording: true, sessionId: 5, timerSecs: 0, pendingTranscriptions: new Set(),
    setInterval: () => 1, clearInterval: () => {},
    MediaStream: class {}, FormData: class { append() {} },
    MediaRecorder: class {
        static isTypeSupported() { return true; }
        constructor() { recorder = this; }
        start() { this.state = 'recording'; }
        stop() { this.state = 'inactive'; this.ondataavailable({data: {size: 5000}}); this.onstop?.(); }
    },
    window: {api: {transcribeChunk: async (_, __, offset) => {
        receivedOffset = offset; return {segments: []};
    }}},
    document: {getElementById: () => ({textContent: ''})},
    toast: () => {}, pollTranscript: () => {}, console,
};
vm.createContext(context);
vm.runInContext(html.slice(start, end), context);
context.startMicRecording({getAudioTracks: () => []});
context.timerSecs = 10;
recorder.stop();
assert.equal(receivedOffset, 0, 'chunk timestamps start where recording began, not where it ended');
console.log('Recording chunk offset passed');

(async () => {
    let finishUpload;
    context.window.api.transcribeChunk = () => new Promise(resolve => { finishUpload = resolve; });
    context.MorphCast = {stop() {}};
    context.videoStream = {getTracks: () => [{stop() {}}]};
    context.document = {getElementById: () => ({style: {}})};
    vm.runInContext(html.slice(html.indexOf('async function stopCamera('), html.indexOf('// MorphCast feeds')), context);
    context.startMicRecording({getAudioTracks: () => []});
    let finished = false;
    const stop = context.stopCamera().then(() => { finished = true; });
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(finished, false, 'ending waits for final transcription');
    finishUpload({segments: []});
    await stop;
    assert.equal(finished, true);
    console.log('Final transcription drain passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
