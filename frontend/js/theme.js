// js/theme.js — Light/dark mode manager. Imported by every page.

const STORAGE_KEY = "sl-theme";

export function applyTheme() {
    const saved = localStorage.getItem(STORAGE_KEY) || "dark";
    document.documentElement.setAttribute("data-theme", saved === "light" ? "light" : "");
}

export function toggleTheme() {
    const current = localStorage.getItem(STORAGE_KEY) || "dark";
    const next = current === "dark" ? "light" : "dark";
    localStorage.setItem(STORAGE_KEY, next);
    document.documentElement.setAttribute("data-theme", next === "light" ? "light" : "");
    return next;
}

export function currentTheme() {
    return localStorage.getItem(STORAGE_KEY) || "dark";
}
