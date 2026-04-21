import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { AlertCircle, CheckCircle, AlertTriangle, Info, Upload, Loader, BarChart3, Shield, Code2, Zap, ArrowRight, Sparkles, Copy, Download, Search, History, Star, StarOff, Printer } from 'lucide-react';
import Joyride from 'react-joyride';
import { Tooltip } from 'react-tooltip';
import { apiClient } from './apiClient';

// ─── Module-level constants & utilities ─────────────────────────────────────

const getIcon = (severity) => {
  const icons = {
    CRITICAL: <AlertCircle className="w-6 h-6" />,
    HIGH:     <AlertTriangle className="w-6 h-6" />,
    MEDIUM:   <AlertTriangle className="w-6 h-6" />,
    LOW:      <Info className="w-6 h-6" />
  };
  return icons[severity] ?? null;
};

const colorMap = {
  CRITICAL: 'border-red-300 bg-red-50 hover:bg-red-100',
  HIGH:     'border-red-300 bg-red-50 hover:bg-red-100',
  MEDIUM:   'border-yellow-300 bg-yellow-50 hover:bg-yellow-100',
  LOW:      'border-green-300 bg-green-50 hover:bg-green-100'
};

const tourSteps = [
  { target: '.upload-area',     content: 'Upload your Solidity contract file here or drag and drop.' },
  { target: '.scan-button',     content: 'Click here to start the security scan.' },
  { target: '.findings-section', content: 'Your scan results and vulnerability findings appear here.' },
];

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const normalizeSeverity = (severity) => String(severity || 'LOW').toUpperCase();

const escapeHtml = (str) => {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
};

const safeLocalStorageSet = (key, value) => {
  try { localStorage.setItem(key, value); }
  catch (e) { console.error('localStorage write failed:', e); }
};

const safeLocalStorageGet = (key, fallback = null) => {
  try { return localStorage.getItem(key) ?? fallback; }
  catch (e) { console.error('localStorage read failed:', e); return fallback; }
};

const copyToClipboard = async (text) => {
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Fall through to the legacy clipboard fallback below.
    }
  }
  try {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0';
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(textarea);
    return ok;
  } catch {
    return false;
  }
};

// ─── SeverityBadge ───────────────────────────────────────────────────────────

const SeverityBadge = ({ severity }) => {
  const configs = {
    CRITICAL: { bg: 'from-red-500 to-red-600',       ring: 'ring-red-300',    glow: 'shadow-red-500/50' },
    HIGH:     { bg: 'from-orange-500 to-orange-600', ring: 'ring-orange-300', glow: 'shadow-orange-500/50' },
    MEDIUM:   { bg: 'from-yellow-500 to-yellow-600', ring: 'ring-yellow-300', glow: 'shadow-yellow-500/50' },
    LOW:      { bg: 'from-blue-500 to-blue-600',     ring: 'ring-blue-300',   glow: 'shadow-blue-500/50' },
  };
  const { bg, ring, glow } = configs[severity] || configs.LOW;
  return (
    <span className={`inline-block px-4 py-2 rounded-full text-sm font-bold text-white bg-gradient-to-r ${bg} ring-2 ${ring} shadow-lg ${glow} uppercase tracking-wider`}>
      {severity}
    </span>
  );
};

// ─── HelpModal ───────────────────────────────────────────────────────────────

const HelpModal = ({ isOpen, onClose }) => {
  const closeRef = useRef(null);

  // Close on Escape key + auto-focus close button for accessibility
  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKeyDown);
    const focusTimer = setTimeout(() => closeRef.current?.focus(), 0);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      clearTimeout(focusTimer);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;
  return (
    // Backdrop click closes modal
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* role="dialog" + aria-modal prevent screen readers from navigating behind it */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="help-modal-title"
        className="bg-white rounded-lg p-8 max-w-2xl w-full mx-4 max-h-96 overflow-y-auto"
      >
        <div className="flex justify-between items-center mb-4">
          <h2 id="help-modal-title" className="text-2xl font-bold">Help & Examples</h2>
          <button
            ref={closeRef}
            onClick={onClose}
            aria-label="Close help dialog"
            className="text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
          >&#x2715;</button>
        </div>
        <div className="space-y-4">
          <div>
            <h3 className="font-semibold">Common Vulnerabilities</h3>
            <ul className="list-disc list-inside text-sm">
              <li>Reentrancy: Functions that call external contracts before updating state.</li>
              <li>Integer Overflow: Arithmetic operations that exceed type limits.</li>
              <li>Access Control: Missing modifiers on sensitive functions.</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold">Example Contract</h3>
            <pre className="bg-gray-100 p-4 rounded text-xs font-mono">{`pragma solidity ^0.8.0;

contract SafeContract {
  mapping(address => uint) balances;

  function transfer(address to, uint amount) public {
    require(balances[msg.sender] >= amount);
    balances[msg.sender] -= amount;
    balances[to] += amount;
  }
}`}</pre>
          </div>
        </div>
      </div>
    </div>
  );
};

// ─── FindingCard ─────────────────────────────────────────────────────────────

const FindingCard = ({ finding }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copyState, setCopyState] = useState('idle');
  const copyTimerRef = useRef(null);
  useEffect(() => () => clearTimeout(copyTimerRef.current), []);
  const severity = normalizeSeverity(finding.severity);
  const codeSnippet = finding.code ?? finding.code_snippet;

  const handleCopyToClipboard = async (e) => {
    e.stopPropagation();
    const ok = await copyToClipboard(JSON.stringify(finding, null, 2));
    setCopyState(ok ? 'success' : 'error');
    copyTimerRef.current = setTimeout(() => setCopyState('idle'), 2000);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-expanded={isExpanded}
      aria-label={`${severity} finding: ${finding.title}. Click to ${isExpanded ? 'collapse' : 'expand'}.`}
      className={`border-l-4 rounded-lg p-6 transition-all duration-300 cursor-pointer hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${colorMap[severity] ?? 'border-gray-300 bg-gray-50 hover:bg-gray-100'}`}
      onClick={() => setIsExpanded(!isExpanded)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setIsExpanded(!isExpanded); } }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4 flex-1">
          <div className={`mt-1 ${
            severity === 'CRITICAL' ? 'text-red-600'
            : severity === 'HIGH'   ? 'text-orange-600'
            : severity === 'MEDIUM' ? 'text-yellow-600'
            : 'text-blue-600'
          }`}>
            {getIcon(severity)}
          </div>
          <div className="flex-1">
            <h3
              className="text-lg font-bold text-gray-900 mb-2"
              data-tooltip-id="finding-tooltip"
              data-tooltip-content={finding.description}
            >
              {finding.title}
            </h3>
            <p className="text-gray-700 mb-3 leading-relaxed">{finding.description}</p>
            {finding.line_number && (
              <span className="inline-block bg-gray-200 px-3 py-1 rounded text-sm font-mono text-gray-800 mb-3">
                Line {finding.line_number}
              </span>
            )}
            {isExpanded && codeSnippet && (
              <div className="mt-4 bg-gray-900 p-4 rounded-lg overflow-x-auto">
                <pre className="text-xs text-green-400 font-mono">{codeSnippet}</pre>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <SeverityBadge severity={severity} />
          <button
            onClick={handleCopyToClipboard}
            className="p-2 text-gray-500 hover:text-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
            title="Copy finding to clipboard"
            aria-label={copyState === 'success' ? 'Copied!' : copyState === 'error' ? 'Copy failed' : 'Copy finding to clipboard'}
            aria-live="polite"
          >
            {copyState === 'success' && <CheckCircle className="w-5 h-5 text-green-600" />}
            {copyState === 'error'   && <AlertCircle className="w-5 h-5 text-red-500" />}
            {copyState === 'idle'    && <Copy className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </div>
  );
};

// ─── ResultsList ─────────────────────────────────────────────────────────────

const ResultsList = ({ findings, loading, contractName }) => {
  const [searchTerm,      setSearchTerm]      = useState('');
  const [filterSeverity,  setFilterSeverity]  = useState('All');
  const [copyLinkState,   setCopyLinkState]   = useState('idle');
  const [printError,      setPrintError]      = useState('');

  const copyLinkTimerRef = useRef(null);
  useEffect(() => () => clearTimeout(copyLinkTimerRef.current), []);

  const critical = useMemo(() => findings.filter(f => normalizeSeverity(f.severity) === 'CRITICAL').length, [findings]);
  const high     = useMemo(() => findings.filter(f => normalizeSeverity(f.severity) === 'HIGH').length,     [findings]);
  const medium   = useMemo(() => findings.filter(f => normalizeSeverity(f.severity) === 'MEDIUM').length,   [findings]);
  const low      = useMemo(() => findings.filter(f => normalizeSeverity(f.severity) === 'LOW').length,      [findings]);

  const filteredFindings = useMemo(() => findings.filter(f => {
    const matchesSearch =
      (f.title ?? '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (f.description ?? '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterSeverity === 'All' || normalizeSeverity(f.severity) === filterSeverity;
    return matchesSearch && matchesFilter;
  }), [findings, searchTerm, filterSeverity]);

  const handleCopyShareableLink = async () => {
    const reportData = {
      contractName, findings,
      summary: { critical, high, medium, low, total: findings.length },
      date: new Date().toISOString()
    };
    // Use TextEncoder + Uint8Array → btoa for full Unicode safety
    const json    = JSON.stringify(reportData);
    const bytes   = new TextEncoder().encode(json);
    const binStr  = Array.from(bytes, (b) => String.fromCodePoint(b)).join('');
    const encoded = btoa(binStr);
    const shareableLink = `${window.location.origin}/share?data=${encodeURIComponent(encoded)}`;
    const ok = await copyToClipboard(shareableLink);
    setCopyLinkState(ok ? 'success' : 'error');
    copyLinkTimerRef.current = setTimeout(() => setCopyLinkState('idle'), 2000);
  };

  const handlePrint = () => {
    setPrintError('');
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      setPrintError('Printing failed: popups are blocked. Please allow popups for this site and try again.');
      return;
    }
    const content = `<html><head><title>Security Scan Report - ${escapeHtml(contractName)}</title>
      <style>body{font-family:Arial,sans-serif;margin:20px}h1{color:#333}.summary{background:#f0f0f0;padding:10px;margin-bottom:20px}.finding{border:1px solid #ccc;padding:10px;margin-bottom:10px}.severity{font-weight:bold}pre{background:#f9f9f9;padding:10px;overflow-x:auto}</style>
      </head><body>
      <h1>Security Scan Report for ${escapeHtml(contractName)}</h1>
      <div class="summary"><p><strong>Total:</strong> ${findings.length}</p><p><strong>Critical:</strong> ${critical}</p><p><strong>High:</strong> ${high}</p><p><strong>Medium:</strong> ${medium}</p><p><strong>Low:</strong> ${low}</p></div>
      <h2>Findings</h2>
      ${findings.map((f, i) => `<div class="finding"><h3>${i + 1}. ${escapeHtml(f.title)}</h3><p class="severity">Severity: ${escapeHtml(normalizeSeverity(f.severity))}</p><p>${escapeHtml(f.description)}</p>${f.line_number ? `<p>Line: ${escapeHtml(String(f.line_number))}</p>` : ''}${(f.code ?? f.code_snippet) ? `<pre>${escapeHtml(f.code ?? f.code_snippet)}</pre>` : ''}</div>`).join('')}
      <p><em>Generated by BlockScope on ${new Date().toLocaleString()}</em></p>
      </body></html>`;
    printWindow.document.write(content);
    printWindow.document.close();
    printWindow.print();
  };

  const handleDownloadMarkdown = () => {
    const md = `# Security Scan Report for ${contractName}\n\n## Summary\n- **Total**: ${findings.length}\n- **Critical**: ${critical}\n- **High**: ${high}\n- **Medium**: ${medium}\n- **Low**: ${low}\n\n## Findings\n\n${findings.map((f, i) => `### ${i + 1}. ${f.title}\n- **Severity**: ${normalizeSeverity(f.severity)}\n- **Description**: ${f.description}\n${f.line_number ? `- **Line**: ${f.line_number}\n` : ''}${(f.code ?? f.code_snippet) ? `\`\`\`solidity\n${f.code ?? f.code_snippet}\n\`\`\`\n` : ''}`).join('\n')}\n\n---\n*Generated on ${new Date().toLocaleString()}*\n`;
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `${contractName}_security_report.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleDownloadJSON = () => {
    const blob = new Blob(
      [JSON.stringify({ contractName, findings, summary: { critical, high, medium, low, total: findings.length } }, null, 2)],
      { type: 'application/json;charset=utf-8' }
    );
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `${contractName}_security_report.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div role="status" aria-live="polite" className="flex flex-col items-center justify-center py-20">
        <div className="relative">
          <Loader className="w-16 h-16 text-blue-600 animate-spin" aria-hidden="true" />
          <Zap className="w-8 h-8 text-yellow-500 absolute top-4 right-4 animate-pulse" aria-hidden="true" />
        </div>
        <p className="text-gray-600 mt-6 text-lg font-semibold">Scanning with BlockScope...</p>
        <p className="text-gray-500 mt-2">Analyzing security vulnerabilities</p>
      </div>
    );
  }

  if (!findings || findings.length === 0) {
    return (
      <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-300 rounded-2xl p-10 text-center shadow-lg">
        <div className="flex justify-center mb-4">
          <CheckCircle className="w-16 h-16 text-green-600 animate-bounce" aria-hidden="true" />
        </div>
        <p className="text-green-900 font-bold text-2xl">Perfect! No Vulnerabilities Found</p>
        <p className="text-green-700 text-lg mt-2">Your smart contract passed all security checks</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 findings-section">
      <Tooltip id="finding-tooltip" />

      {printError && (
        <div role="alert" className="bg-red-50 border-l-4 border-red-500 text-red-800 px-4 py-3 rounded-lg text-sm">
          {printError}
        </div>
      )}

      {/* Search and Filter */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search vulnerabilities..."
            aria-label="Search vulnerabilities by title or description"
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="flex gap-2 w-full md:w-auto flex-wrap items-center">
          <button
            onClick={handleCopyShareableLink}
            className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
            title="Copy Shareable Link"
            aria-label={copyLinkState === 'success' ? 'Link copied!' : copyLinkState === 'error' ? 'Copy failed' : 'Copy shareable link'}
          >
            {copyLinkState === 'success' && <CheckCircle className="w-5 h-5 text-green-600" />}
            {copyLinkState === 'error'   && <AlertCircle className="w-5 h-5 text-red-500" />}
            {copyLinkState === 'idle'    && <Copy className="w-5 h-5 text-gray-600" />}
          </button>

          <button onClick={handleDownloadMarkdown} className="flex items-center gap-1 px-3 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-sm text-gray-600" title="Download Markdown Report">
            <Download className="w-4 h-4" /> MD
          </button>
          <button onClick={handleDownloadJSON} className="flex items-center gap-1 px-3 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-sm text-gray-600" title="Download JSON Report">
            <Download className="w-4 h-4" /> JSON
          </button>

          <button onClick={handlePrint} className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50" title="Print Report">
            <Printer className="w-5 h-5 text-gray-600" />
          </button>

          {["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((level) => (
            <button
              key={level}
              onClick={() => setFilterSeverity(level)}
              aria-pressed={filterSeverity === level}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                filterSeverity === level ? 'bg-gray-800 text-white shadow-md' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'CRITICAL', count: critical, from: 'from-red-500',    to: 'to-red-600',    muted: 'text-red-100' },
          { label: 'HIGH',     count: high,     from: 'from-orange-500', to: 'to-orange-600', muted: 'text-orange-100' },
          { label: 'MEDIUM',   count: medium,   from: 'from-yellow-500', to: 'to-yellow-600', muted: 'text-yellow-100' },
          { label: 'LOW',      count: low,      from: 'from-blue-500',   to: 'to-blue-600',   muted: 'text-blue-100' },
        ].map(({ label, count, from, to, muted }) => (
          <div key={label} className={`bg-gradient-to-br ${from} ${to} rounded-xl p-6 text-white shadow-xl hover:shadow-2xl transition-shadow`}>
            <p className={`${muted} text-sm font-semibold mb-2`}>{label}</p>
            <p className="text-4xl font-bold">{count}</p>
          </div>
        ))}
      </div>

      {/* Contract Info */}
      <div className="bg-white border-2 border-gray-200 rounded-xl p-6 shadow-md">
        <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Code2 className="w-5 h-5" /> Scan Summary
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-gray-600 text-sm">Contract Name</p>
            <p className="font-semibold text-gray-900">{contractName}</p>
          </div>
          <div>
            <p className="text-gray-600 text-sm">Total Findings</p>
            <p className="font-semibold text-gray-900">{findings.length}</p>
          </div>
        </div>
      </div>

      {/* Findings */}
      <div>
        <h3 className="font-bold text-2xl text-gray-900 mb-6 flex items-center gap-2">
          <AlertCircle className="w-6 h-6 text-red-600" />
          Security Findings ({filteredFindings.length} of {findings.length})
        </h3>
        <div className="space-y-4">
          {filteredFindings.map((finding, idx) => (
            <FindingCard
              key={`${finding.severity}-${finding.title}-${finding.line_number ?? idx}`}
              finding={finding}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

// ─── ScanHistory ─────────────────────────────────────────────────────────────

const ScanHistory = ({ scanHistory, onRescan, onToggleFavorite, onLoadFromHistory }) => {
  const [showDropdown, setShowDropdown] = useState(false);

  const dropdownRef = useRef(null);
  useEffect(() => {
    if (!showDropdown) return;
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showDropdown]);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setShowDropdown(prev => !prev)}
        aria-haspopup="true"
        aria-expanded={showDropdown}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-all focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <History className="w-4 h-4" />
        Scan History
      </button>
      {showDropdown && (
        <div className="absolute top-full mt-2 right-0 w-96 bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-h-64 overflow-y-auto">
          {scanHistory.length === 0 ? (
            <p className="p-4 text-gray-500">No scan history yet.</p>
          ) : (
            scanHistory.map((scan, idx) => (
              <div key={`${scan.contractName}-${scan.date}`} className="p-4 border-b border-gray-100 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0 mr-2">
                    <p className="font-semibold text-gray-900 truncate">{scan.contractName}</p>
                    <p className="text-sm text-gray-600">{scan.date}</p>
                    <p className="text-xs text-gray-500">Findings: {scan.findingsSummary?.total ?? 'N/A'}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => onToggleFavorite(idx)}
                      className="p-1 text-gray-500 hover:text-yellow-500"
                      title={scan.favorite ? 'Remove from favorites' : 'Add to favorites'}
                    >
                      {scan.favorite ? <Star className="w-4 h-4 text-yellow-500" /> : <StarOff className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => { onLoadFromHistory(scan); setShowDropdown(false); }}
                      className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                      aria-label={`Load ${scan.contractName}`}
                    >
                      Load
                    </button>
                    <button
                      onClick={() => { onRescan(scan); setShowDropdown(false); }}
                      className="px-3 py-1 bg-green-500 text-white rounded text-sm hover:bg-green-600"
                      aria-label={`Re-scan ${scan.contractName}`}
                    >
                      Re-scan
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

// ─── ScanForm ────────────────────────────────────────────────────────────────

const ScanForm = ({
  onSubmit, loading,
  scanHistory, onRescan, onToggleFavorite, onLoadFromHistory,
  onCodeChange, onNameChange,
  initialCode, initialName
}) => {
  const [contractCode,   setContractCode]   = useState(initialCode || '');
  const [contractName,   setContractName]   = useState(initialName || '');
  const [fileName,       setFileName]       = useState('');
  const [fileSize,       setFileSize]       = useState(0);
  const [filePreview,    setFilePreview]    = useState('');
  const [error,          setError]          = useState('');
  const [dragActive,     setDragActive]     = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef(null);
  const [uploadHistory,  setUploadHistory]  = useState([]);

  useEffect(() => {
    if (initialCode !== undefined) {
      setContractCode(initialCode);
    }
  }, [initialCode]);

  useEffect(() => {
    if (initialName !== undefined) setContractName(initialName);
  }, [initialName]);

  useEffect(() => {
    let history = [];
    try { history = JSON.parse(safeLocalStorageGet('upload_history', '[]')); } catch { history = []; }
    setUploadHistory(history);
  }, []);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const processFile = useCallback((file) => {
    if (!file.name.endsWith('.sol')) {
      setError('Invalid file type. Please upload a .sol file.');
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setError('File size exceeds 50MB limit.');
      return;
    }
    setError('');
    setFileName(file.name);
    setFileSize(file.size);
    const nameWithoutExt = file.name.replace(/\.sol$/i, '');
    setContractName(nameWithoutExt);
    onNameChange?.(nameWithoutExt);

    const reader = new FileReader();
    reader.onloadstart = () => setUploadProgress(0);
    reader.onprogress  = (e) => {
      if (e.lengthComputable) setUploadProgress((e.loaded / e.total) * 100);
    };
    reader.onload = (event) => {
      try {
        const content = event.target?.result;
        if (typeof content === 'string') {
          setContractCode(content);
          onCodeChange?.(content);
          setFilePreview(content.substring(0, 500) + (content.length > 500 ? '...' : ''));
          setUploadProgress(100);
          setTimeout(() => setUploadProgress(0), 800);
          const newHistory = [
            { name: file.name, size: file.size, date: new Date().toLocaleString() },
            ...uploadHistory
          ].slice(0, 10);
          setUploadHistory(newHistory);
          safeLocalStorageSet('upload_history', JSON.stringify(newHistory));
        }
      } catch (err) {
        setError('Error reading file: ' + err.message);
      }
    };
    reader.onerror = () => setError('Failed to read file. Please try again.');
    reader.readAsText(file);
  }, [uploadHistory, onCodeChange, onNameChange]);

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!contractCode.trim()) {
      setError('Please provide contract code');
      return;
    }
    setError('');
    try {
      await onSubmit(contractCode, contractName || fileName || 'contract.sol');
    } catch (err) {
      setError('Error submitting scan: ' + err.message);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      <div className="flex justify-between items-center mb-6">
        <div />
        <ScanHistory
          scanHistory={scanHistory}
          onRescan={onRescan}
          onToggleFavorite={onToggleFavorite}
          onLoadFromHistory={onLoadFromHistory}
        />
      </div>

      {error && (
        <div role="alert" className="bg-red-50 border-l-4 border-red-500 text-red-800 px-6 py-4 rounded-lg shadow-md">
          <p className="font-semibold text-lg">{error}</p>
        </div>
      )}

      <div
        className={`upload-area relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 ${
          dragActive
            ? 'border-blue-500 bg-blue-50 shadow-xl scale-105 ring-4 ring-blue-200'
            : 'border-blue-300 bg-gradient-to-br from-blue-50 to-indigo-50 hover:shadow-lg hover:border-blue-400'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <div
          role="button"
          tabIndex={0}
          aria-label="Upload Solidity contract file"
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInputRef.current?.click(); } }}
          className="cursor-pointer"
        >
          <Upload className={`w-16 h-16 mx-auto mb-4 transition-transform ${dragActive ? 'scale-110 text-blue-700' : 'text-blue-600'}`} />
          <p className="text-gray-900 font-bold text-xl mb-2">Upload Your Solidity Contract</p>
          <p className="text-gray-600 mb-2">or drag and drop</p>
          <p className="text-gray-500 text-sm">.sol files only, max 50MB</p>
        </div>
        <input ref={fileInputRef} type="file" accept=".sol" onChange={handleFileUpload} className="hidden" aria-hidden="true" />
        {uploadProgress > 0 && uploadProgress < 100 && (
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
            </div>
            <p className="text-sm text-gray-600 mt-2">Uploading... {Math.round(uploadProgress)}%</p>
          </div>
        )}
      </div>

      {fileName && (
        <div className="bg-green-50 border-l-4 border-green-500 px-6 py-4 rounded-lg shadow-md">
          <p className="text-green-800 font-semibold">File selected: {fileName}</p>
          <p className="text-green-700 text-sm">Size: {formatFileSize(fileSize)}</p>
          {filePreview && (
            <div className="mt-3">
              <p className="text-green-800 font-medium text-sm mb-2">Preview:</p>
              <pre className="bg-white p-3 rounded text-xs text-gray-800 font-mono overflow-x-auto max-h-32">{filePreview}</pre>
            </div>
          )}
        </div>
      )}

      {uploadHistory.length > 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-3">Recent Uploads</h4>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {uploadHistory.map((item, idx) => (
              <div key={idx} className="flex justify-between text-sm text-gray-600">
                <span>{item.name}</span>
                <span>{formatFileSize(item.size)} — {item.date}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6">
        <div>
          <label htmlFor="contractNameInput" className="flex text-sm font-bold text-gray-900 mb-3 items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-600" />
            Contract Name (Optional)
          </label>
          <input
            id="contractNameInput"
            type="text"
            value={contractName}
            onChange={(e) => {
              setContractName(e.target.value);
              // FIX C: Mirror name up to App so Ctrl+S uses the current value
              onNameChange?.(e.target.value);
            }}
            placeholder="e.g., MyToken, DeFiProtocol"
            className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>

        <div>
          <label htmlFor="contractCodeTextarea" className="flex text-sm font-bold text-gray-900 mb-3 items-center gap-2">
            <Code2 className="w-4 h-4 text-blue-600" />
            Or paste contract code
          </label>
          <textarea
            id="contractCodeTextarea"
            value={contractCode}
            onChange={(e) => {
              setContractCode(e.target.value);
              onCodeChange?.(e.target.value);
            }}
            placeholder={`pragma solidity ^0.8.0;\n\ncontract MyContract {\n  function transfer(address to, uint256 amount) public {\n    // Implementation\n  }\n}`}
            className="w-full h-80 p-4 border-2 border-gray-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={loading || !contractCode.trim()}
        className="scan-button w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-400 text-white font-bold py-4 px-6 rounded-xl transition-all duration-300 flex items-center justify-center gap-3 text-lg shadow-xl hover:shadow-2xl disabled:shadow-none"
      >
        {loading ? (
          <><Loader className="w-6 h-6 animate-spin" /> Scanning... Please wait</>
        ) : (
          <><Shield className="w-6 h-6" /> Start Security Scan <ArrowRight className="w-6 h-6" /></>
        )}
      </button>
    </form>
  );
};

// ─── App ─────────────────────────────────────────────────────────────────────

export default function App() {
  const [currentPage,   setCurrentPage]   = useState('scan');
  const [findings,      setFindings]      = useState([]);
  const [contractName,  setContractName]  = useState('');
  const [contractCode,  setContractCode]  = useState('');
  const [loading,       setLoading]       = useState(false);
  const [error,         setError]         = useState('');
  const [scanHistory,   setScanHistory]   = useState([]);
  const [runTour,       setRunTour]       = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);

  useEffect(() => {
    const hasSeenTour = safeLocalStorageGet('hasSeenTour');
    if (!hasSeenTour) {
      setRunTour(true);
      safeLocalStorageSet('hasSeenTour', 'true');
    }
  }, []);

  useEffect(() => {
    let history = [];
    try { history = JSON.parse(safeLocalStorageGet('scan_history', '[]')); } catch { history = []; }
    setScanHistory(history);
  }, []);

  const handleNewScan = useCallback(() => {
    setCurrentPage('scan');
    setFindings([]);
    setContractName('');
    setContractCode('');
    setError('');
  }, []);

  const handleScan = useCallback(async (code, uploadedContractName) => {
    try {
      setLoading(true);
      setError('');
      setContractName(uploadedContractName);

      const response    = await apiClient.scanContract(code, uploadedContractName);
      const scanFindings = Array.isArray(response.findings)
        ? response.findings.map((finding) => ({
            ...finding,
            severity: normalizeSeverity(finding.severity),
          }))
        : [];
      setFindings(scanFindings);

      const newScan = {
        contractName: uploadedContractName,
        contractCode: code,
        findings:     scanFindings,
        findingsSummary: {
          critical: scanFindings.filter(f => normalizeSeverity(f.severity) === 'CRITICAL').length,
          high:     scanFindings.filter(f => normalizeSeverity(f.severity) === 'HIGH').length,
          medium:   scanFindings.filter(f => normalizeSeverity(f.severity) === 'MEDIUM').length,
          low:      scanFindings.filter(f => normalizeSeverity(f.severity) === 'LOW').length,
          total:    scanFindings.length
        },
        date:     new Date().toLocaleString(),
        favorite: false
      };
      setScanHistory(prev => {
        const updated = [newScan, ...prev].slice(0, 10);
        safeLocalStorageSet('scan_history', JSON.stringify(updated));
        return updated;
      });
      setCurrentPage('results');
    } catch (err) {
      setError('Scan failed: ' + err.message);
      console.error('Scan error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRescan = useCallback(async (scan) => {
    if (!scan.contractCode) {
      setError('No contract code is stored for this history entry — cannot re-scan.');
      return;
    }
    await handleScan(scan.contractCode, scan.contractName);
  }, [handleScan]);

  const handleToggleFavorite = useCallback((index) => {
    const updatedHistory = [...scanHistory];
    updatedHistory[index].favorite = !updatedHistory[index].favorite;
    setScanHistory(updatedHistory);
    safeLocalStorageSet('scan_history', JSON.stringify(updatedHistory));
  }, [scanHistory]);

  const handleLoadFromHistory = useCallback((scan) => {
    setContractCode(scan.contractCode || '');
    setContractName(scan.contractName || '');
    setCurrentPage('scan');
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      switch (e.key) {
        case 's':
          e.preventDefault();
          if (currentPage === 'scan' && contractCode.trim()) {
            handleScan(contractCode, contractName || 'contract.sol');
          }
          break;
        case 'h':
          e.preventDefault();
          setShowHelpModal(true);
          break;
        case 'n':
          e.preventDefault();
          handleNewScan();
          break;
        default:
          break;
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [currentPage, contractCode, contractName, handleScan, handleNewScan]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* Animated background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none" style={{ isolation: 'isolate' }}>
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob" style={{ willChange: 'transform' }} />
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000" style={{ willChange: 'transform' }} />
        <div className="absolute bottom-0 left-1/2 w-96 h-96 bg-pink-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-4000" style={{ willChange: 'transform' }} />
      </div>

      {/* Skip-to-content — keyboard accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 bg-white text-blue-700 font-bold px-4 py-2 rounded z-[100]"
      >
        Skip to main content
      </a>

      {/* Navbar */}
      <nav aria-label="Main navigation" className="relative bg-white/10 backdrop-blur-md border-b border-white/20 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-400" />
            <h1 className="text-3xl font-black text-white">BlockScope</h1>
            <button
              onClick={() => setShowHelpModal(true)}
              aria-label="Open help and examples"
              className="text-blue-300 hover:text-white ml-2 focus:outline-none focus:ring-2 focus:ring-blue-400 rounded px-2 py-1"
            >
              Help
            </button>
          </div>
          <p className="text-blue-300 font-semibold">Powered by Slither + custom rules</p>
        </div>
      </nav>

      {/* Main Content */}
      <main id="main-content" className="relative max-w-6xl mx-auto px-6 py-12">
        {currentPage === 'scan' ? (
          <div>
            <div className="bg-white/95 backdrop-blur rounded-3xl shadow-2xl p-12 mb-8">
              <div className="flex items-center gap-3 mb-8">
                <Zap className="w-8 h-8 text-blue-600" />
                <h2 className="text-4xl font-black text-gray-900">Smart Contract Security Scanner</h2>
              </div>
              <p className="text-gray-600 text-lg mb-8">
                Upload your Solidity contracts for instant vulnerability detection powered by Slither and custom rules
              </p>
              <ScanForm
                onSubmit={handleScan}
                scanHistory={scanHistory}
                loading={loading}
                onRescan={handleRescan}
                onToggleFavorite={handleToggleFavorite}
                onLoadFromHistory={handleLoadFromHistory}
                onCodeChange={setContractCode}
                onNameChange={setContractName}
                initialCode={contractCode}
                initialName={contractName}
              />
            </div>

            {/* Feature highlights */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
              <div className="bg-white/10 backdrop-blur border border-white/20 rounded-2xl p-6 text-white">
                <AlertCircle className="w-8 h-8 text-red-400 mb-4" />
                <h3 className="font-bold text-lg mb-2">Real-time Analysis</h3>
                <p className="text-white/70">Instant vulnerability detection using Slither and custom security rules</p>
              </div>
              <div className="bg-white/10 backdrop-blur border border-white/20 rounded-2xl p-6 text-white">
                <BarChart3 className="w-8 h-8 text-blue-400 mb-4" />
                <h3 className="font-bold text-lg mb-2">Detailed Reports</h3>
                <p className="text-white/70">Comprehensive findings with severity levels and remediation</p>
              </div>
              <div className="bg-white/10 backdrop-blur border border-white/20 rounded-2xl p-6 text-white">
                <Shield className="w-8 h-8 text-green-400 mb-4" />
                <h3 className="font-bold text-lg mb-2">Security Score</h3>
                <p className="text-white/70">Get an overall security rating for your smart contract</p>
              </div>
            </div>
          </div>
        ) : (
          <div>
            <div className="bg-white/95 backdrop-blur rounded-3xl shadow-2xl p-12">
              <div className="flex items-center justify-between mb-10">
                <div>
                  <h2 className="text-4xl font-black text-gray-900 flex items-center gap-3">
                    <BarChart3 className="w-8 h-8 text-blue-600" />
                    Scan Results
                  </h2>
                  <p className="text-gray-600 mt-2">{contractName}</p>
                </div>
                <button
                  onClick={handleNewScan}
                  className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold py-3 px-8 rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl flex items-center gap-2"
                >
                  <Upload className="w-5 h-5" /> New Scan
                </button>
              </div>
              {error && (
                <div role="alert" className="bg-red-50 border-l-4 border-red-500 text-red-800 px-6 py-4 rounded-lg mb-8 shadow-md">
                  {error}
                </div>
              )}
              <ResultsList findings={findings} contractName={contractName} loading={loading} />
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="relative border-t border-white/20 mt-20 py-8 bg-white/5 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 text-center text-white/70 text-sm">
          <p>BlockScope Security Scanner | Powered by Slither + custom rules | Always conduct thorough audits before deployment</p>
        </div>
      </footer>

      <Joyride
        steps={tourSteps}
        run={runTour}
        continuous
        showSkipButton
        showProgress
        callback={(data) => {
          if (data.status === 'finished' || data.status === 'skipped') setRunTour(false);
        }}
      />

      <HelpModal isOpen={showHelpModal} onClose={() => setShowHelpModal(false)} />

      <style>{`
        @keyframes blob {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33%       { transform: translate(30px, -50px) scale(1.1); }
          66%       { transform: translate(-20px, 20px) scale(0.9); }
        }
        .animate-blob         { animation: blob 7s infinite; }
        .animation-delay-2000 { animation-delay: 2s; }
        .animation-delay-4000 { animation-delay: 4s; }

        /* Respect user's reduced-motion preference */
        @media (prefers-reduced-motion: reduce) {
          .animate-blob,
          .animate-spin,
          .animate-pulse,
          .animate-bounce {
            animation: none !important;
          }
          .transition-all,
          .transition-shadow,
          .transition-colors {
            transition: none !important;
          }
        }
      `}</style>
    </div>
  );
}
