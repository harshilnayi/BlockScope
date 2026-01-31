import React, { useState } from 'react';
import {
  AlertCircle,
  CheckCircle,
  AlertTriangle,
  Info,
  Upload,
  Loader,
  BarChart3,
  Shield,
  Code2,
  Zap,
  ArrowRight,
  Sparkles,
} from 'lucide-react';

import { apiClient } from './apiClient';

/* =========================
   Severity Badge
   ========================= */
const SeverityBadge = ({ severity }) => {
  const severityConfig = {
    CRITICAL: 'bg-red-600',
    HIGH: 'bg-orange-600',
    MEDIUM: 'bg-yellow-600',
    LOW: 'bg-blue-600',
  };

  return (
    <span
      className={`px-4 py-2 rounded-full text-white text-sm font-bold uppercase ${severityConfig[severity]}`}
    >
      {severity}
    </span>
  );
};

/* =========================
   Finding Card
   ========================= */
const FindingCard = ({ finding }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="border-l-4 border-blue-500 bg-blue-50 rounded-lg p-6 cursor-pointer transition hover:shadow-lg"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex justify-between gap-4">
        <div>
          <SeverityBadge severity={finding.severity} />
          <h3 className="text-lg font-bold mt-3">{finding.title}</h3>
          <p className="text-gray-700">{finding.description}</p>

          {finding.line_number && (
            <p className="mt-2 text-sm font-mono text-gray-600">
              Line {finding.line_number}
            </p>
          )}

          {expanded && finding.code && (
            <pre className="mt-4 bg-gray-900 text-green-400 p-4 rounded text-xs overflow-x-auto">
              {finding.code}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};

/* =========================
   Results List
   ========================= */
const ResultsList = ({ findings, loading, contractName }) => {
  if (loading) {
    return (
      <div className="flex flex-col items-center py-20">
        <Loader className="w-14 h-14 animate-spin text-blue-600" />
        <p className="mt-4 text-gray-600 font-semibold">
          Scanning with Semgrep…
        </p>
      </div>
    );
  }

  if (!findings.length) {
    return (
      <div className="bg-green-50 border-2 border-green-300 rounded-2xl p-10 text-center">
        <CheckCircle className="w-16 h-16 text-green-600 mx-auto mb-4" />
        <p className="text-2xl font-bold text-green-800">
          No Vulnerabilities Found 🎉
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-black">
        Security Findings – {contractName}
      </h2>

      {findings.map((f, i) => (
        <FindingCard key={i} finding={f} />
      ))}
    </div>
  );
};

/* =========================
   Scan Form
   ========================= */
const ScanForm = ({ onSubmit, loading }) => {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    if (!code.trim()) {
      setError('❌ Please provide contract code');
      return;
    }
    setError('');
    onSubmit(code, 'UploadedContract.sol');
  };

  return (
    <form onSubmit={submit} className="space-y-6">
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 text-red-800">
          {error}
        </div>
      )}

      <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        className="w-full h-80 p-4 border-2 rounded font-mono"
        placeholder="Paste Solidity contract here…"
      />

      <button
        disabled={loading}
        className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold py-4 rounded-xl flex justify-center items-center gap-2"
      >
        {loading ? (
          <>
            <Loader className="w-5 h-5 animate-spin" />
            Scanning…
          </>
        ) : (
          <>
            <Shield className="w-5 h-5" />
            Start Security Scan
            <ArrowRight className="w-5 h-5" />
          </>
        )}
      </button>
    </form>
  );
};

/* =========================
   MAIN APP
   ========================= */
export default function App() {
  const [page, setPage] = useState('scan');
  const [findings, setFindings] = useState([]);
  const [contractName, setContractName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleScan = async (code, name) => {
    try {
      setLoading(true);
      setError('');
      setContractName(name);

      const res = await apiClient.scanContract(code, name);
      setFindings(res.findings || []);
      setPage('results');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* Navbar */}
      <nav className="bg-white/10 backdrop-blur border-b border-white/20 px-8 py-6">
        <div className="flex items-center gap-3 text-white">
          <Shield className="w-8 h-8 text-blue-400" />
          <h1 className="text-3xl font-black">BlockScope</h1>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto p-8">
        {page === 'scan' ? (
          <div className="bg-white rounded-3xl p-10 shadow-2xl">
            <h2 className="text-4xl font-black mb-6">
              Smart Contract Security Scanner
            </h2>
            <ScanForm onSubmit={handleScan} loading={loading} />
          </div>
        ) : (
          <div className="bg-white rounded-3xl p-10 shadow-2xl space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-3xl font-black">Scan Results</h2>
              <button
                onClick={() => setPage('scan')}
                className="bg-blue-600 text-white px-6 py-3 rounded-xl font-bold"
              >
                New Scan
              </button>
            </div>

            {error && (
              <div className="bg-red-50 border-l-4 border-red-500 p-4 text-red-800">
                {error}
              </div>
            )}

            <ResultsList
              findings={findings}
              contractName={contractName}
              loading={loading}
            />
          </div>
        )}
      </main>

      <footer className="text-center text-white/70 py-6">
        🔒 BlockScope | Powered by Semgrep
      </footer>
    </div>
  );
}
