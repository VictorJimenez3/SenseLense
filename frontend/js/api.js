/**
 * api.js — Thin wrapper around the Flask backend.
 * All fetch calls go through here so changing the base URL is one-line.
 */

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

export const api = {
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

    // Events (pipeline ingestion point)
    ingestEvents: (sessionId, events) => request("POST", `/sessions/${sessionId}/events`, events),

    // Insights
    getInsights: (sessionId) => request("GET", `/sessions/${sessionId}/insights`),
};
