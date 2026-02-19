import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, AlertTriangle, Info, Upload, Loader, BarChart3, Shield, Code2, Zap, ArrowRight, Sparkles } from 'lucide-react';

// API Service with error handling
const API_BASE_URL = 'http://localhost:5000/api/v1';

const apiClient = {
  scanContract: async (sourceCode, contractName) => {
    try {
      const response = await fetch(`${API_BASE_URL}/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          source_code: sourceCode, 
          contract_name: contractName || 'UnnamedContract',
          file_path: 'api_upload'
        })
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Scan API error:', error);
      throw new Error('Failed to scan contract: ' + error.message);
    }
  }
};

// Severity Badge with gradient
const SeverityBadge = ({ severity }) => {
  const severityConfig = {
    CRITICAL: { 
      bg: 'bg-gradient-to-r from-red-500 to-red-600', 
      text: 'text-white',
      ring: 'ring-2 ring-red-300',
      glow: 'shadow-lg shadow-red-500/50'
    },
    HIGH: { 
      bg: 'bg-gradient-to-r from-orange-500 to-orange-600', 
      text: 'text-white',
      ring: 'ring-2 ring-orange-300',
      glow: 'shadow-lg shadow-orange-500/50'
    },
    MEDIUM: { 
      bg: 'bg-gradient-to-r from-yellow-500 to-yellow-600', 
      text: 'text-white',
      ring: 'ring-2 ring-yellow-300',
      glow: 'shadow-lg shadow-yellow-500/50'
    },
    LOW: { 
      bg: 'bg-gradient-to-r from-blue-500 to-blue-600', 
      text: 'text-white',
      ring: 'ring-2 ring-blue-300',
      glow: 'shadow-lg shadow-blue-500/50'
    },
  };

  const config = severityConfig[severity] || severityConfig.LOW;

  return (
    <span className={`inline-block px-4 py-2 rounded-full text-sm font-bold ${config.bg} ${config.text} ${config.ring} ${config.glow} uppercase tracking-wider`}>
      {severity}
    </span>
  );
};

// Finding Card with animations
const FindingCard = ({ finding, index }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const iconMap = {
    CRITICAL: <AlertCircle className="w-6 h-6" />,
    HIGH: <AlertTriangle className="w-6 h-6" />,
    MEDIUM: <AlertTriangle className="w-6 h-6" />,
    LOW: <Info className="w-6 h-6" />
  };

  const colorMap = {
    CRITICAL: 'border-red-300 bg-red-50 hover:bg-red-100',
    HIGH: 'border-orange-300 bg-orange-50 hover:bg-orange-100',
    MEDIUM: 'border-yellow-300 bg-yellow-50 hover:bg-yellow-100',
    LOW: 'border-blue-300 bg-blue-50 hover:bg-blue-100'
  };

  return (
    <div 
      className={`border-l-4 rounded-lg p-6 transition-all duration-300 cursor-pointer transform hover:scale-102 ${colorMap[finding.severity]}`}
      onClick={() => setIsExpanded(!isExpanded)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4 flex-1">
          <div className={`mt-1 ${finding.severity === 'CRITICAL' ? 'text-red-600' : finding.severity === 'HIGH' ? 'text-orange-600' : finding.severity === 'MEDIUM' ? 'text-yellow-600' : 'text-blue-600'}`}>
            {iconMap[finding.severity]}
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-bold text-gray-900 mb-2">{finding.title}</h3>
            <p className="text-gray-700 mb-3 leading-relaxed">{finding.description}</p>
            
            {finding.line_number && (
              <div className="inline-block">
                <span className="inline-block bg-gray-200 px-3 py-1 rounded text-sm font-mono text-gray-800 mb-3">
                  Line {finding.line_number}
                </span>
              </div>
            )}
            
            {isExpanded && finding.code && (
              <div className="mt-4 bg-gray-900 p-4 rounded-lg overflow-x-auto">
                <pre className="text-xs text-green-400 font-mono">{finding.code}</pre>
              </div>
            )}
          </div>
        </div>
        <SeverityBadge severity={finding.severity} />
      </div>
    </div>
  );
};

// Results List with premium styling
const ResultsList = ({ findings, fileName, loading, contractName }) => {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="relative">
          <Loader className="w-16 h-16 text-blue-600 animate-spin" />
          <Zap className="w-8 h-8 text-yellow-500 absolute top-4 right-4 animate-pulse" />
        </div>
        <p className="text-gray-600 mt-6 text-lg font-semibold">Scanning with Semgrep...</p>
        <p className="text-gray-500 mt-2">Analyzing security vulnerabilities</p>
      </div>
    );
  }

  if (!findings || findings.length === 0) {
    return (
      <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-300 rounded-2xl p-10 text-center shadow-lg">
        <div className="flex justify-center mb-4">
          <CheckCircle className="w-16 h-16 text-green-600 animate-bounce" />
        </div>
        <p className="text-green-900 font-bold text-2xl">Perfect! No Vulnerabilities Found</p>
        <p className="text-green-700 text-lg mt-2">Your smart contract passed all security checks ✨</p>
      </div>
    );
  }

  const critical = findings.filter(f => f.severity === 'CRITICAL').length;
  const high = findings.filter(f => f.severity === 'HIGH').length;
  const medium = findings.filter(f => f.severity === 'MEDIUM').length;
  const low = findings.filter(f => f.severity === 'LOW').length;

  return (
    <div className="space-y-8">
      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-xl p-6 text-white shadow-xl hover:shadow-2xl transition-shadow">
          <p className="text-red-100 text-sm font-semibold mb-2">CRITICAL</p>
          <p className="text-4xl font-bold">{critical}</p>
        </div>
        <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl p-6 text-white shadow-xl hover:shadow-2xl transition-shadow">
          <p className="text-orange-100 text-sm font-semibold mb-2">HIGH</p>
          <p className="text-4xl font-bold">{high}</p>
        </div>
        <div className="bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-xl p-6 text-white shadow-xl hover:shadow-2xl transition-shadow">
          <p className="text-yellow-100 text-sm font-semibold mb-2">MEDIUM</p>
          <p className="text-4xl font-bold">{medium}</p>
        </div>
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white shadow-xl hover:shadow-2xl transition-shadow">
          <p className="text-blue-100 text-sm font-semibold mb-2">LOW</p>
          <p className="text-4xl font-bold">{low}</p>
        </div>
      </div>

      {/* Contract Info */}
      <div className="bg-white border-2 border-gray-200 rounded-xl p-6 shadow-md">
        <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Code2 className="w-5 h-5" />
          Scan Summary
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
          Security Findings ({findings.length})
        </h3>
        <div className="space-y-4">
          {findings.map((finding, idx) => (
            <FindingCard key={idx} finding={finding} index={idx} />
          ))}
        </div>
      </div>
    </div>
  );
};

// Scan Form with premium design
const ScanForm = ({ onSubmit, loading }) => {
  const [contractCode, setContractCode] = useState('');
  const [contractName, setContractName] = useState('');
  const [fileName, setFileName] = useState('');
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);

  const handleFileUpload = (e) => {
    try {
      const file = e.target.files?.[0];
      if (!file) return;

      if (!file.name.endsWith('.sol')) {
        setError('❌ Please upload a .sol file');
        return;
      }

      setError('');
      setFileName(file.name);
      
      // Extract contract name from filename
      const nameWithoutExt = file.name.replace('.sol', '');
      setContractName(nameWithoutExt);

      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const content = event.target?.result;
          if (typeof content === 'string') {
            setContractCode(content);
          }
        } catch (err) {
          setError('❌ Error reading file: ' + err.message);
        }
      };
      reader.onerror = () => {
        setError('❌ Failed to read file');
      };
      reader.readAsText(file);
    } catch (err) {
      setError('❌ Error handling file upload: ' + err.message);
    }
  };

  const handleDrag = (e) => {
    try {
      e.preventDefault();
      e.stopPropagation();
      if (e.type === "dragenter" || e.type === "dragover") {
        setDragActive(true);
      } else if (e.type === "dragleave") {
        setDragActive(false);
      }
    } catch (err) {
      console.error('Drag error:', err);
    }
  };

  const handleDrop = (e) => {
    try {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      const file = e.dataTransfer.files?.[0];
      if (file) {
        const fileInput = document.getElementById('fileInput');
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;
        handleFileUpload({ target: fileInput });
      }
    } catch (err) {
      console.error('Drop error:', err);
      setError('❌ Error processing dropped file');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (!contractCode.trim()) {
        setError('❌ Please provide contract code');
        return;
      }
      setError('');
      await onSubmit(contractCode, contractName || fileName || 'contract.sol');
    } catch (err) {
      setError('❌ Error submitting scan: ' + err.message);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 text-red-800 px-6 py-4 rounded-lg shadow-md animate-pulse">
          <p className="font-semibold text-lg">{error}</p>
        </div>
      )}

      <div 
        className={`relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 ${
          dragActive 
            ? 'border-blue-500 bg-blue-50 shadow-xl scale-102' 
            : 'border-blue-300 bg-gradient-to-br from-blue-50 to-indigo-50 hover:shadow-lg'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <div onClick={() => document.getElementById('fileInput').click()} className="cursor-pointer">
          <Upload className="w-16 h-16 text-blue-600 mx-auto mb-4" />
          <p className="text-gray-900 font-bold text-xl mb-2">📁 Upload Your Solidity Contract</p>
          <p className="text-gray-600 mb-2">or drag and drop</p>
          <p className="text-gray-500 text-sm">.sol files only</p>
        </div>
        <input
          id="fileInput"
          type="file"
          accept=".sol"
          onChange={handleFileUpload}
          className="hidden"
        />
      </div>

      {fileName && (
        <p className="text-sm text-green-700 bg-green-50 px-6 py-4 rounded-lg font-semibold border-l-4 border-green-500">
          ✅ File selected: {fileName}
        </p>
      )}

      <div className="grid grid-cols-1 gap-6">
        <div>
          <label className="block text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-600" />
            Contract Name (Optional)
          </label>
          <input
            type="text"
            value={contractName}
            onChange={(e) => setContractName(e.target.value)}
            placeholder="e.g., MyToken, DeFiProtocol"
            className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>

        <div>
          <label className="block text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
            <Code2 className="w-4 h-4 text-blue-600" />
            Or paste contract code
          </label>
          <textarea
            value={contractCode}
            onChange={(e) => setContractCode(e.target.value)}
            placeholder="pragma solidity ^0.8.0;

contract MyContract {
  // Your contract code here
  function transfer(address to, uint256 amount) public {
    // Implementation
  }
}"
            className="w-full h-80 p-4 border-2 border-gray-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={loading || !contractCode.trim()}
        className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-400 text-white font-bold py-4 px-6 rounded-xl transition-all duration-300 flex items-center justify-center gap-3 text-lg shadow-xl hover:shadow-2xl disabled:shadow-none"
      >
        {loading ? (
          <>
            <Loader className="w-6 h-6 animate-spin" />
            Scanning... Please wait
          </>
        ) : (
          <>
            <Shield className="w-6 h-6" />
            Start Security Scan
            <ArrowRight className="w-6 h-6" />
          </>
        )}
      </button>
    </form>
  );
};

// Main App Component
export default function App() {
  const [currentPage, setCurrentPage] = useState('scan');
  const [findings, setFindings] = useState([]);
  const [contractName, setContractName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleScan = async (contractCode, uploadedContractName) => {
    try {
      setLoading(true);
      setError('');
      setContractName(uploadedContractName);

      const response = await apiClient.scanContract(contractCode, uploadedContractName);
      
      try {
        const scanFindings = response.findings || [];
        setFindings(Array.isArray(scanFindings) ? scanFindings : []);
      } catch (parseErr) {
        setError('Error parsing results: ' + parseErr.message);
        setFindings([]);
      }

      setCurrentPage('results');
    } catch (err) {
      setError('Scan failed: ' + err.message);
      console.error('Scan error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleNewScan = () => {
    try {
      setCurrentPage('scan');
      setFindings([]);
      setContractName('');
      setError('');
    } catch (err) {
      console.error('Error resetting form:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* Animated background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute bottom-0 left-1/2 w-96 h-96 bg-pink-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      {/* Navbar */}
      <nav className="relative bg-white/10 backdrop-blur-md border-b border-white/20 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-400" />
            <h1 className="text-3xl font-black text-white">BlockScope</h1>
          </div>
          <p className="text-blue-300 font-semibold">Powered by Semgrep</p>
        </div>
      </nav>

      {/* Main Content */}
      <main className="relative max-w-6xl mx-auto px-6 py-12">
        {currentPage === 'scan' ? (
          <div>
            <div className="bg-white/95 backdrop-blur rounded-3xl shadow-2xl p-12 mb-8">
              <div className="flex items-center gap-3 mb-8">
                <Zap className="w-8 h-8 text-blue-600" />
                <h2 className="text-4xl font-black text-gray-900">Smart Contract Security Scanner</h2>
              </div>
              <p className="text-gray-600 text-lg mb-8">Upload your Solidity contracts for instant vulnerability detection powered by Semgrep</p>
              <ScanForm onSubmit={handleScan} loading={loading} />
            </div>

            {/* Features */}
            <div className="grid grid-cols-3 gap-6 mt-12">
              <div className="bg-white/10 backdrop-blur border border-white/20 rounded-2xl p-6 text-white">
                <AlertCircle className="w-8 h-8 text-red-400 mb-4" />
                <h3 className="font-bold text-lg mb-2">Real-time Analysis</h3>
                <p className="text-white/70">Instant vulnerability detection using advanced Semgrep rules</p>
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
                  <Upload className="w-5 h-5" />
                  New Scan
                </button>
              </div>

              {error && (
                <div className="bg-red-50 border-l-4 border-red-500 text-red-800 px-6 py-4 rounded-lg mb-8 shadow-md">
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
          <p>🔒 BlockScope Security Scanner | Powered by Semgrep | Always conduct thorough audits before deployment</p>
        </div>
      </footer>

      <style jsx>{`
        @keyframes blob {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(30px, -50px) scale(1.1); }
          66% { transform: translate(-20px, 20px) scale(0.9); }
        }
        .animate-blob {
          animation: blob 7s infinite;
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        .animation-delay-4000 {
          animation-delay: 4s;
        }
        .scale-102 {
          transform: scale(1.02);
        }
      `}</style>
    </div>
  );
}