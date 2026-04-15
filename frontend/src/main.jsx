/**
 * BlockScope - Entry point with performance optimizations.
 *
 * Enhancements:
 *  - React.lazy + Suspense for the main App component (code splitting)
 *  - Service Worker registration for offline shell + asset caching
 *  - Web Vitals measurement (CLS, FID, FCP, LCP, TTFB)
 *  - reportWebVitals fed into console in dev, analytics endpoint in prod
 */

import React, { lazy, Suspense } from 'react';
import ReactDOM from 'react-dom/client';
import ErrorBoundary from './ErrorBoundary';
import './index.css';

// ── Lazy-load the App to enable code-splitting ───────────────────────────────
// The App chunk is only fetched when the browser is ready to render.
const App = lazy(() => import('./App'));

// ── Loading skeleton shown while the App chunk is fetched ────────────────────
// Defined as a module-level const (not exported) before createRoot so it is
// only evaluated once and satisfies react-refresh component rules.
const AppFallback = () => (
  <div
    role="status"
    aria-label="Loading BlockScope…"
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%)',
      color: '#93c5fd',
      fontFamily: 'system-ui, sans-serif',
    }}
  >
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="64"
      height="64"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ animation: 'blockscope-spin 1s linear infinite', color: '#3b82f6' }}
      aria-hidden="true"
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
    <p style={{ marginTop: '1rem', fontSize: '1.1rem', fontWeight: 600 }}>
      Loading BlockScope…
    </p>
  </div>
);

// ── Mount the React tree ─────────────────────────────────────────────────────
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <Suspense fallback={<AppFallback />}>
        <App />
      </Suspense>
    </ErrorBoundary>
  </React.StrictMode>
);

// ── Service Worker registration (production only) ────────────────────────────
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js', { scope: '/' })
      .then((registration) => {
        console.info('[SW] Registered:', registration.scope);

        // Check for updates every hour
        setInterval(() => registration.update(), 60 * 60 * 1000);
      })
      .catch((err) => {
        console.warn('[SW] Registration failed:', err);
      });
  });
}

// ── Web Vitals ───────────────────────────────────────────────────────────────
// Only import in production to keep dev bundle small.
// web-vitals is optional — the app works perfectly without it.
if (import.meta.env.PROD) {
  import('web-vitals').then(({ onCLS, onFID, onFCP, onLCP, onTTFB }) => {
    const send = (metric) => {
      if (import.meta.env.VITE_ANALYTICS_URL) {
        fetch(import.meta.env.VITE_ANALYTICS_URL, {
          method: 'POST',
          body: JSON.stringify(metric),
          headers: { 'Content-Type': 'application/json' },
          keepalive: true,
        }).catch(() => {/* silently ignore analytics failures */});
      } else {
        // Log to console in production preview for debugging
        console.table({ metric: metric.name, value: metric.value.toFixed(2) });
      }
    };
    onCLS(send);
    onFID(send);
    onFCP(send);
    onLCP(send);
    onTTFB(send);
  }).catch(() => {
    // web-vitals not installed — metrics silently disabled
  });
}
