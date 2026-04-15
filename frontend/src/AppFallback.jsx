/**
 * AppFallback - Loading skeleton shown while the App chunk is fetched.
 * Extracted to its own file so main.jsx has no component definitions,
 * satisfying the react-refresh/only-export-components lint rule.
 */

import React from 'react';

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

export default AppFallback;
