/**
 * api.js — Thin wrapper around the Flask backend.
 * Plain global script (no ES module exports) — works with <script src="..."> on all pages.
 */

(function () {
    const API_BASE = "http://localhost:5050/api";

    async function request(method, path, body = null) {
        const opts = {
            method,
            headers: { "Content-Type": "application/json" },
        };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(API_BASE + path, opts);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ error: res.statusText }));
            throw new Error(err.error || res.statusText);
        }
        return res.json();
    }

    window.api = {
        // Health
        health: () => request("GET", "/health"),

        // Clients
        getClients: () => request("GET", "/clients"),
        createClient: (data) => request("POST", "/clients", data),
        getClient: (id) => request("GET", `/clients/${id}`),

        // Sessions
        getSessions: () => request("GET", "/sessions"),
        createSession: (data) => request("POST", "/sessions", data),
        getSession: (id, events = false) => request("GET", `/sessions/${id}?events=${events}`),
        endSession: (id, data) => request("PATCH", `/sessions/${id}/end`, data),
        deleteSession: (id) => request("DELETE", `/sessions/${id}`),
        generateSummary: (id) => request("POST", `/sessions/${id}/summary/generate`),
        startRecording: (data) => request("POST", "/record", data),

        // Events (pipeline ingestion point)
        ingestEvents: (sessionId, events) => request("POST", `/sessions/${sessionId}/events`, events),

        // Recording pipeline — browser → Flask → ElevenLabs / DeepFace
        transcribeChunk: (sessionId, formData, offsetMs = 0) => {
            // formData is a FormData with an 'audio' file field
            const url = new URL(API_BASE + `/transcribe/${sessionId}`);
            url.searchParams.append("offset_ms", offsetMs);
            return fetch(url, {
                method: 'POST',
                body: formData,   // no Content-Type header — browser sets boundary automatically
            }).then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.error); }));
        },
        analyzeFrame: (sessionId, frameDataUrl, timestampMs) => request(
            "POST", `/analyze-frame/${sessionId}`,
            { frame: frameDataUrl, timestamp_ms: timestampMs }
        ),

        // Insights
        getInsights: (sessionId) => request("GET", `/sessions/${sessionId}/insights`),
    };
})();
