/**
 * utils.js — Shared utility functions used across all pages.
 * Plain global script — exposes window.utils so all pages can use it via <script src="...">.
 */
(function () {

    /** Show a toast notification */
    function toast(msg, type = "info") {
        const container = document.getElementById("toast-container");
        if (!container) return;
        const el = document.createElement("div");
        el.className = `toast ${type}`;
        const icons = { success: "✓", error: "✕", info: "ℹ" };
        el.innerHTML = `<span>${icons[type] || "ℹ"}</span> ${msg}`;
        container.appendChild(el);
        setTimeout(() => el.remove(), 3500);
    }

    /** Format ms duration → "1m 24s" */
    function fmtDuration(ms) {
        if (!ms) return "—";
        const s = Math.floor(ms / 1000);
        const m = Math.floor(s / 60);
        const rs = s % 60;
        if (m > 0) return `${m}m ${rs}s`;
        return `${s}s`;
    }

    /** Format ISO date → "Feb 21, 2026 · 3:45 PM" */
    function fmtDate(iso) {
        if (!iso) return "—";
        return new Date(iso).toLocaleString("en-US", {
            month: "short", day: "numeric", year: "numeric",
            hour: "numeric", minute: "2-digit",
        });
    }

    /** Format ISO date → short "Feb 21" */
    function fmtDateShort(iso) {
        if (!iso) return "—";
        return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
    }

    /** Map valence float (-1→1) to a label + CSS class */
    function sentimentLabel(val) {
        if (val == null) return { label: "Unknown", cls: "neutral" };
        if (val >= 0.2) return { label: "Positive", cls: "positive" };
        if (val <= -0.2) return { label: "Negative", cls: "negative" };
        return { label: "Neutral", cls: "neutral" };
    }

    /** Get initials from full name */
    function initials(name = "") {
        return name.split(" ").slice(0, 2).map(w => w[0]).join("").toUpperCase();
    }

    /** Format mm:ss timer from seconds */
    function fmtTimer(secs) {
        const m = String(Math.floor(secs / 60)).padStart(2, "0");
        const s = String(secs % 60).padStart(2, "0");
        return `${m}:${s}`;
    }

    /** Open / close a modal by id */
    function openModal(id) {
        document.getElementById(id)?.classList.add("open");
    }

    function closeModal(id) {
        document.getElementById(id)?.classList.remove("open");
    }

    /** Mark active sidebar nav link based on current page filename */
    function setActiveNav() {
        const page = location.pathname.split("/").pop().replace(".html", "") || "index";
        document.querySelectorAll(".nav-item").forEach(el => {
            const href = el.getAttribute("href")?.replace(".html", "") || "";
            if (href.endsWith(page)) el.classList.add("active");
        });
    }

    window.utils = { toast, fmtDuration, fmtDate, fmtDateShort, sentimentLabel, initials, fmtTimer, openModal, closeModal, setActiveNav };

    // Also expose each function at global scope for convenience in inline scripts
    window.toast = toast;
    window.fmtDuration = fmtDuration;
    window.fmtDate = fmtDate;
    window.fmtDateShort = fmtDateShort;
    window.sentimentLabel = sentimentLabel;
    window.initials = initials;
    window.fmtTimer = fmtTimer;
    window.openModal = openModal;
    window.closeModal = closeModal;
})();
