/* face-api.js 0.22.2: browser-only expression detection, no licensed service. */
(function () {
    const modelUrl = new URL('../assets/face-api/models/', document.currentScript.src).href;
    const expressions = ['neutral', 'happy', 'sad', 'angry', 'fearful', 'disgusted', 'surprised'];
    const labels = {neutral:'neutral', happy:'happy', sad:'negative', angry:'negative',
        fearful:'confused', disgusted:'negative', surprised:'engaged'};
    let models, active = false, generation = 0, timer, running;
    let sessionId, elapsed, updateEmotion, unavailable, video;
    let buffer = [], lastSnapshot = 0, valenceTotal = 0, valenceCount = 0;
    const uploads = new Set();
    const setText = (id, text) => {const el = document.getElementById(id); if (el) el.textContent = text;};

    function buildBars() {
        document.getElementById('expression-bars').innerHTML = expressions.map(name =>
            `<div class="mc-bar-item"><div class="mc-bar-row"><span>${name}</span><span id="expression-value-${name}">0%</span></div><div class="mc-bar-track"><div class="mc-bar-fill" id="expression-bar-${name}" style="background:var(--red)"></div></div></div>`
        ).join('');
    }

    function showScores(scores) {
        for (const name of expressions) {
            const value = scores?.[name] || 0;
            setText(`expression-value-${name}`, `${Math.round(value * 100)}%`);
            const bar = document.getElementById(`expression-bar-${name}`);
            if (bar) bar.style.width = `${value * 100}%`;
        }
    }

    function flushSnapshot() {
        if (!buffer.length) return;
        const scores = Object.fromEntries(expressions.map(name =>
            [name, buffer.reduce((sum, sample) => sum + sample.scores[name], 0) / buffer.length]));
        const dominant = expressions.reduce((best, name) => scores[name] > scores[best] ? name : best, 'neutral');
        const sample = {
            timestamp_ms: Math.round(buffer.reduce((sum, sample) => sum + sample.timestamp, 0) / buffer.length),
            source: 'faceapi', emotion: labels[dominant],
            valence: Number((buffer.reduce((sum, sample) => sum + sample.valence, 0) / buffer.length).toFixed(3)),
            text: JSON.stringify({expressions:scores, dominant_expression:dominant,
                note:'Valence is a heuristic derived from expression probabilities.'}),
        };
        buffer = [];
        lastSnapshot = elapsed();
        const upload = window.api.ingestEvents(sessionId, [sample]).catch(() => {
            window.utils?.toast('Could not save emotion sample; check the backend connection.', 'error');
        });
        uploads.add(upload);
        upload.finally(() => uploads.delete(upload));
    }

    async function detect(token) {
        if (!active || token !== generation) return;
        try {
            if (video.readyState >= 2) {
                const started = performance.now();
                const result = await faceapi.detectSingleFace(video,
                    new faceapi.TinyFaceDetectorOptions({inputSize:224, scoreThreshold:0.5})).withFaceExpressions();
                if (!active || token !== generation) return;
                setText('expression-latency', `${Math.round(performance.now() - started)} ms inference`);
                if (result) {
                    const scores = Object.fromEntries(expressions.map(name => [name, result.expressions[name] || 0]));
                    const dominant = expressions.reduce((best, name) => scores[name] > scores[best] ? name : best, 'neutral');
                    // Product heuristic, not a separate mood or attention model.
                    const valence = scores.happy - scores.sad - scores.angry - scores.fearful - scores.disgusted;
                    valenceTotal += valence; valenceCount++;
                    buffer.push({scores, valence, timestamp:elapsed()});
                    updateEmotion(labels[dominant]);
                    showScores(scores);
                    setText('expression-dominant', dominant);
                    setText('expression-status', 'Tracking');
                    if (elapsed() - lastSnapshot >= 2000) flushSnapshot();
                } else {
                    setText('expression-status', 'No face detected');
                    setText('expression-dominant', '—');
                    showScores(null);
                }
            }
        } catch (error) {
            if (!active || token !== generation) return;
            active = false;
            setText('expression-status', 'Expression analysis unavailable');
            unavailable();
            console.warn('[Expressions]', error);
            window.utils?.toast('Expression analysis failed; try restarting the session.', 'error');
        }
        if (active && token === generation) timer = setTimeout(() => {
            running = detect(token);
            return running;
        }, 100);
    }

    window.EmotionTracker = {
        async start(cameraVideo, id, readElapsed, onEmotion = () => {}, onUnavailable = () => {}) {
            const token = ++generation;
            active = true; video = cameraVideo; sessionId = id; elapsed = readElapsed;
            updateEmotion = onEmotion; unavailable = onUnavailable;
            buffer = []; lastSnapshot = 0; valenceTotal = 0; valenceCount = 0;
            document.getElementById('expression-panel').style.display = 'block';
            buildBars();
            setText('expression-status', 'Loading expression models…');
            try {
                if (typeof faceapi === 'undefined') throw new Error('face-api.js failed to load');
                models ||= Promise.all([
                    faceapi.nets.tinyFaceDetector.loadFromUri(modelUrl),
                    faceapi.nets.faceExpressionNet.loadFromUri(modelUrl),
                ]).catch(error => {models = null; throw error;});
                await models;
                if (!active || token !== generation) return;
                running = detect(token);
                await running;
            } catch (error) {
                if (!active || token !== generation) return;
                active = false;
                setText('expression-status', 'Model loading failed');
                unavailable();
                window.utils?.toast('Expression models could not load. Refresh and try again.', 'error');
                console.warn('[Expressions]', error);
            }
        },
        async stop() {
            active = false; generation++;
            clearTimeout(timer);
            await running;
            flushSnapshot();
            await Promise.allSettled([...uploads]);
            setText('expression-status', 'Stopped');
        },
        avgValence100() {return valenceCount ? (valenceTotal / valenceCount + 1) * 50 : null;},
    };
})();
