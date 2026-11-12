"""Shared visual theme, header and PWA head tags."""

from __future__ import annotations

from nicegui import ui

from .session import current_role

PWA_HEAD = """
<link rel="manifest" href="/static/manifest.webmanifest">
<meta name="theme-color" content="#0f766e">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="MediQueue">
<link rel="apple-touch-icon" href="/static/icons/icon-192.png">
<script>
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
    });
  }
</script>
"""

CSS = """
:root {
  --mq-primary: #0f766e;
  --mq-primary-dark: #115e59;
  --mq-bg: #f1f5f9;
  --mq-text: #0f172a;
  --mq-muted: #64748b;
  --mq-border: #e2e8f0;
}
body { background: var(--mq-bg); color: var(--mq-text); }
.mq-header {
  background: #ffffff !important;
  color: var(--mq-text) !important;
  border-bottom: 1px solid var(--mq-border);
  box-shadow: none !important;
}
.mq-header-inner {
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 12px;
  height: 60px;
  align-items: center;
  flex-wrap: nowrap;
  gap: 2px;
}
.mq-brand { font-weight: 800; font-size: 1.1rem; letter-spacing: -0.02em; color: var(--mq-primary) !important; }
.mq-nav { color: var(--mq-muted) !important; font-weight: 600; }
.mq-nav-active { color: var(--mq-primary) !important; background: #ccfbf1 !important; }
.mq-shell {
  width: 100%;
  max-width: 540px;
  margin: 0 auto;
  padding: 80px 16px 40px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.mq-shell-wide { max-width: 1080px; }
.mq-card {
  background: #ffffff;
  border: 1px solid var(--mq-border);
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
  width: 100%;
}
.mq-title { font-size: 1.35rem; font-weight: 800; letter-spacing: -0.02em; }
.mq-section-title { font-weight: 700; font-size: 0.95rem; }
.mq-subtitle { color: var(--mq-muted); font-size: 0.9rem; }
.mq-muted { color: var(--mq-muted); font-size: 0.85rem; }
.mq-error { color: #dc2626; font-size: 0.85rem; min-height: 1.1rem; }
.mq-hero {
  border-radius: 24px;
  padding: 22px;
  color: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-shadow: 0 14px 32px rgba(15, 118, 110, 0.28);
}
.mq-hero-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.mq-hero-caption { font-size: 0.7rem; letter-spacing: 0.18em; text-transform: uppercase; opacity: 0.85; font-weight: 700; }
.mq-hero-label { font-weight: 700; font-size: 1rem; }
.mq-number {
  font-size: clamp(4.5rem, 26vw, 8rem);
  font-weight: 800;
  line-height: 0.95;
  letter-spacing: -0.05em;
  font-variant-numeric: tabular-nums;
}
.mq-pill {
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 0.78rem;
  font-weight: 700;
  white-space: nowrap;
}
.mq-hero-stats { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
.mq-hero-stat { background: rgba(255, 255, 255, 0.12); border-radius: 12px; padding: 8px 12px; min-width: 86px; }
.mq-hero-stat b { display: block; font-size: 1.15rem; font-variant-numeric: tabular-nums; }
.mq-hero-stat span { font-size: 0.66rem; opacity: 0.82; text-transform: uppercase; letter-spacing: 0.08em; }
.mq-message {
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  color: #115e59;
  border-radius: 14px;
  padding: 12px 16px;
  font-size: 0.9rem;
}
.mq-chips { display: flex; gap: 8px; flex-wrap: wrap; }
.mq-chip {
  background: #f1f5f9;
  border: 1px solid var(--mq-border);
  border-radius: 10px;
  padding: 6px 12px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.mq-chip-next { background: #ccfbf1; border-color: #99f6e4; color: #115e59; }
.mq-queue-row { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px dashed var(--mq-border); }
.mq-queue-row:last-child { border-bottom: none; }
.mq-pos { width: 26px; text-align: center; color: var(--mq-muted); font-size: 0.8rem; font-weight: 700; }
.mq-ticket { font-weight: 800; font-size: 1.1rem; font-variant-numeric: tabular-nums; }
.mq-serving-number { font-size: 3rem; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; color: var(--mq-primary); }
.mq-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.mq-grid-2 { display: grid; grid-template-columns: 1fr; gap: 16px; }
@media (min-width: 860px) { .mq-grid-2 { grid-template-columns: 1fr 1fr; } }
.mq-dialog { width: min(460px, 92vw); }
.mq-stat-row { display: flex; gap: 10px; flex-wrap: wrap; }
.mq-mini-stat {
  flex: 1 1 120px;
  background: #ffffff;
  border: 1px solid var(--mq-border);
  border-radius: 14px;
  padding: 12px 14px;
}
.mq-mini-stat b { display: block; font-size: 1.4rem; font-variant-numeric: tabular-nums; }
.mq-mini-stat span { color: var(--mq-muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; }
.mq-display-body { background: #0b1220 !important; }
.mq-display {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 18px;
  color: #ffffff;
  padding: 32px;
  text-align: center;
}
.mq-display .mq-number { font-size: clamp(6rem, 32vw, 18rem); }
.mq-display-caption { letter-spacing: 0.3em; text-transform: uppercase; font-weight: 700; opacity: 0.72; font-size: 0.85rem; }
.mq-display-next { background: rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 10px 18px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; justify-content: center; }
.mq-display-next .mq-chip { background: rgba(255, 255, 255, 0.14); border-color: rgba(255, 255, 255, 0.2); color: #ffffff; }
"""


def install_head() -> None:
    """Install PWA metadata and the stylesheet once for every page."""
    ui.add_head_html(PWA_HEAD + "<style>" + CSS + "</style>", shared=True)


def page_frame(*, active: str = "") -> None:
    """Render the shared top navigation bar."""
    with ui.header().classes("mq-header"):
        with ui.row().classes("mq-header-inner"):
            ui.button(
                "MediQueue",
                icon="confirmation_number",
                on_click=lambda: ui.navigate.to("/"),
            ).props("flat no-caps").classes("mq-brand")
            ui.space()
            for label, path, key in (
                ("Live queue", "/", "patient"),
                ("Staff", "/staff", "staff"),
                ("Admin", "/admin", "admin"),
            ):
                classes = "mq-nav" + (" mq-nav-active" if key == active else "")
                ui.button(
                    label,
                    on_click=lambda _=None, target=path: ui.navigate.to(target),
                ).props("flat dense no-caps").classes(classes)
            role = current_role()
            if role:
                ui.badge(role.title()).props("color=teal")
                ui.button(
                    icon="logout",
                    on_click=lambda: ui.navigate.to("/logout"),
                ).props("flat round dense").tooltip("Sign out")
