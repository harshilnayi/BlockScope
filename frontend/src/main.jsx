/**
 * BlockScope - Entry point with performance optimizations.
 *
 * Enhancements:
 *  - React.lazy + Suspense for the main App component (code splitting)
 *  - Service Worker registration for offline shell + asset caching
 *  - Web Vitals measurement (CLS, FID, FCP, LCP, TTFB)
 *  - reportWebVitals fed into console in dev, analytics endpoint in prod
 *
 * Note: No React component definitions live in this file.
 * AppFallback is imported from ./AppFallback so that react-refresh
 * fast-reload works correctly (only-export-components rule).
 */

import React, { lazy, Suspense } from 'react';
import ReactDOM from 'react-dom/client';
import ErrorBoundary from './ErrorBoundary';
import AppFallback from './AppFallback';
import './index.css';

// ── Lazy-load the App to enable code-splitting ───────────────────────────────
// The App chunk is only fetched when the browser is ready to render.
const App = lazy(() => import('./App'));

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
