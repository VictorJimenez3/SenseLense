(function () {
    const MC_LICENSE = "sk514a0ced0dca050a7951d6591224c8cc7a7fec72762f";
    const MC_SNAPSHOT_MS = 20000;
    const MC_DISPLAY_EMOS = ["Happy", "Surprise", "Sad", "Negative", "Neutral"];
    const MC_RAW_EMOS = ["Happy", "Surprise", "Sad", "Angry", "Disgust", "Fear", "Neutral"];
    const MC_EMO_COLORS = {
        Happy: "var(--positive)",
        Surprise: "#60A5FA",
        Sad: "#818CF8",
        Negative: "var(--negative)",
        Neutral: "var(--text-muted)",
    };

    let activeSessionId = null;
    let readElapsedMs = () => 0;
    let mcAttSmoothed = 100;
    const MC_ATT_RISE = 0.25;
    const MC_ATT_FALL = 0.04;
    const mcBuf = { emotions: {}, attention: [], valence: [], positivity: [] };
    MC_RAW_EMOS.forEach((emotion) => {
        mcBuf.emotions[emotion] = [];
    });
    let mcSnapshotHandle = null;
    let mcSdkStarted = false;
    let stopSdk = null;
    let onEmotion = () => {};
    let onUnavailable = () => {};
    let listenersInstalled = false;
    let valenceTotal = 0, valenceCount = 0;
    const pendingSnapshots = new Set();

    function buildMcBars() {
        const container = document.getElementById("mc-emotion-bars");
        container.innerHTML = "";
        MC_DISPLAY_EMOS.forEach((name) => {
            const item = document.createElement("div");
            item.className = "mc-bar-item";
            item.innerHTML = `<div class="mc-bar-row"><span>${name}</span><span id="mc-ev-${name}">0%</span></div>
                <div class="mc-bar-track"><div class="mc-bar-fill" id="mc-eb-${name}" style="background:${MC_EMO_COLORS[name]}"></div></div>`;
            container.appendChild(item);
        });
    }

    function setMcBar(name, value) {
        const bar = document.getElementById(`mc-eb-${name}`);
        const text = document.getElementById(`mc-ev-${name}`);
        if (bar) bar.style.width = `${(value * 100).toFixed(1)}%`;
        if (text) text.textContent = `${(value * 100).toFixed(0)}%`;
    }

    function average(values) {
        return values.length
            ? values.reduce((total, value) => total + value, 0) / values.length
            : 0;
    }

    function flushSnapshot() {
        if (!activeSessionId || !mcBuf.valence.length) return;

        const emotionAverages = {};
        MC_RAW_EMOS.forEach((emotion) => {
            emotionAverages[emotion] = average(mcBuf.emotions[emotion]);
        });
        const negative = Math.min(
            1,
            (emotionAverages.Angry || 0) +
                (emotionAverages.Disgust || 0) +
                (emotionAverages.Fear || 0),
        );
        emotionAverages.Negative = negative;

        let dominant = "Neutral";
        let maxValue = 0;
        MC_DISPLAY_EMOS.forEach((emotion) => {
            const value = emotionAverages[emotion] || 0;
            if (value > maxValue) {
                maxValue = value;
                dominant = emotion;
            }
        });

        const valenceNorm = (average(mcBuf.valence) - 50) / 50;
        const upload = window.api.ingestEvents(activeSessionId, [{
            timestamp_ms: readElapsedMs(),
            source: "morphcast",
            emotion: dominant.toLowerCase(),
            valence: Number(valenceNorm.toFixed(3)),
            text: JSON.stringify({
                attention: Math.round(average(mcBuf.attention)),
                valence100: Math.round(average(mcBuf.valence)),
                positivity: Math.round(average(mcBuf.positivity)),
                emotions: Object.fromEntries(
                    MC_DISPLAY_EMOS.map((emotion) => [
                        emotion.toLowerCase(),
                        Number((emotionAverages[emotion] || 0).toFixed(3)),
                    ]),
                ),
            }),
        }]).catch(() => {
            window.utils?.toast("Could not save MorphCast sample; check the backend connection.", "error");
        });
        pendingSnapshots.add(upload);
        upload.finally(() => pendingSnapshots.delete(upload));

        MC_RAW_EMOS.forEach((emotion) => {
            mcBuf.emotions[emotion] = [];
        });
        mcBuf.attention = [];
        mcBuf.valence = [];
        mcBuf.positivity = [];
    }

    function setupListeners() {
        if (listenersInstalled) return;
        listenersInstalled = true;
        window.addEventListener(CY.modules().FACE_EMOTION.eventName, (event) => {
            if (!activeSessionId) return;
            const output = event.detail.output;
            if (!output) return;
            const raw = output.emotion || {};
            MC_RAW_EMOS.forEach((emotion) => {
                mcBuf.emotions[emotion].push(raw[emotion] || 0);
            });
            const negative = Math.min(
                1,
                (raw.Angry || 0) + (raw.Disgust || 0) + (raw.Fear || 0),
            );
            setMcBar("Happy", raw.Happy || 0);
            setMcBar("Surprise", raw.Surprise || 0);
            setMcBar("Sad", raw.Sad || 0);
            setMcBar("Negative", negative);
            setMcBar("Neutral", raw.Neutral || 0);

            const trackerLabel = {Happy: "happy", Surprise: "engaged", Sad: "negative",
                Angry: "negative", Disgust: "negative", Fear: "confused", Neutral: "neutral"};
            onEmotion(trackerLabel[output.dominantEmotion] || "neutral");
            let label = output.dominantEmotion || "Neutral";
            if (["Angry", "Disgust", "Fear"].includes(label)) label = "Negative";
            const dominantEmotion = document.getElementById("mc-dom-emo");
            if (dominantEmotion) {
                dominantEmotion.textContent = label;
                dominantEmotion.style.color = MC_EMO_COLORS[label] || "var(--text-primary)";
            }
        });

        window.addEventListener(CY.modules().FACE_ATTENTION.eventName, (event) => {
            if (!activeSessionId) return;
            const raw = event.detail.output.attention;
            if (raw === undefined) return;
            const rawPercent = raw * 100;
            const difference = rawPercent - mcAttSmoothed;
            mcAttSmoothed = Math.max(
                0,
                Math.min(
                    100,
                    mcAttSmoothed + (difference > 0 ? MC_ATT_RISE : MC_ATT_FALL) * difference,
                ),
            );
            const display = Math.round(mcAttSmoothed);
            mcBuf.attention.push(display);

            const attentionValue = document.getElementById("mc-att-val");
            const ring = document.getElementById("mc-ring-circle");
            const rawValue = document.getElementById("mc-att-raw");
            if (attentionValue) attentionValue.textContent = display;
            if (ring) {
                ring.setAttribute("stroke-dashoffset", 163.4 - (163.4 * mcAttSmoothed / 100));
            }
            if (rawValue) rawValue.textContent = `raw: ${Math.round(rawPercent)}%`;
        });

        window.addEventListener(CY.modules().FACE_AROUSAL_VALENCE.eventName, (event) => {
            if (!activeSessionId) return;
            const output = event.detail.output;
            if (output.valence === undefined) return;
            const value = Math.round((output.valence + 1) / 2 * 100);
            mcBuf.valence.push(value);
            valenceTotal += value;
            valenceCount++;

            const valenceValue = document.getElementById("mc-valence-val");
            const bar = document.getElementById("mc-val-bar");
            const description = document.getElementById("mc-val-desc");
            const color = value > 60
                ? "var(--positive)"
                : value < 40 ? "var(--negative)" : "var(--neutral)";
            const label = value > 70
                ? "Positive"
                : value > 55 ? "Mildly +" : value < 30 ? "Negative" : value < 45 ? "Mildly −" : "Neutral";
            if (valenceValue) {
                valenceValue.textContent = value;
                valenceValue.style.color = color;
            }
            if (bar) {
                bar.style.width = `${value}%`;
                bar.style.background = color;
            }
            if (description) description.textContent = label;
        });

        window.addEventListener(CY.modules().FACE_POSITIVITY.eventName, (event) => {
            if (!activeSessionId) return;
            const positivity = event.detail.output.positivity;
            if (positivity === undefined) return;
            mcBuf.positivity.push(Math.round(positivity * 100));
            const positivityValue = document.getElementById("mc-positivity");
            if (positivityValue) {
                positivityValue.textContent = `Pos: ${Math.round(positivity * 100)}%`;
            }
        });

        window.addEventListener(CY.modules().ALARM_LOW_ATTENTION.eventName, (event) => {
            if (!activeSessionId) return;
            const alarm = document.getElementById("mc-alarm");
            if (!alarm) return;
            if (event.detail.output.isLowAttention) alarm.classList.add("show");
            else alarm.classList.remove("show");
        });
    }

    function startSdk() {
        if (typeof CY === "undefined") {
            onUnavailable();
            window.utils?.toast("MorphCast SDK did not load; emotion tracking unavailable.", "error");
            return;
        }
        if (mcSdkStarted) return;
        mcSdkStarted = true;

        CY.loader()
            .licenseKey(MC_LICENSE)
            .maxInputFrameSize(480)
            .powerSave(0)
            .addModule(CY.modules().FACE_EMOTION.name)
            .addModule(CY.modules().FACE_ATTENTION.name)
            .addModule(CY.modules().FACE_AROUSAL_VALENCE.name)
            .addModule(CY.modules().FACE_POSITIVITY.name)
            .addModule(CY.modules().ALARM_LOW_ATTENTION.name, { threshold: 0.3 })
            .load()
            .then(({ start, stop }) => {
                if (!activeSessionId) { stop(); return; }
                stopSdk = stop;
                setupListeners();
                start();
                document.getElementById("morphcast-panel").style.display = "block";
                buildMcBars();
                mcSnapshotHandle = setInterval(flushSnapshot, MC_SNAPSHOT_MS);
            })
            .catch((error) => {
                mcSdkStarted = false;
                console.error("[MorphCast] SDK error:", error);
                onUnavailable();
                window.utils?.toast("MorphCast unavailable: check the AI SDK license. Emotion tracking has not switched providers.", "error");
            });
    }

    window.MorphCast = {
        start(sessionId, getElapsedMs, updateEmotion = () => {}, unavailable = () => {}) {
            activeSessionId = sessionId;
            readElapsedMs = getElapsedMs;
            onEmotion = updateEmotion;
            onUnavailable = unavailable;
            valenceTotal = 0;
            valenceCount = 0;
            mcAttSmoothed = 100;
            startSdk();
        },
        stop() {
            clearInterval(mcSnapshotHandle);
            flushSnapshot();
            stopSdk?.();
            stopSdk = null;
            activeSessionId = null;
            mcSdkStarted = false;
            document.getElementById("morphcast-panel").style.display = "none";
            return Promise.allSettled([...pendingSnapshots]);
        },
        avgValence100() {
            return valenceCount ? valenceTotal / valenceCount : null;
        },
    };
})();
