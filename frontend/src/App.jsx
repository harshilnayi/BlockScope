import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, AlertTriangle, Info,InfoIcon, Upload, Loader, BarChart3, Shield, Code2, Zap, ArrowRight, Sparkles, Copy, Download, Search, History, Star, StarOff, Printer} from 'lucide-react';
import Joyride from 'react-joyride';
import { Tooltip } from 'react-tooltip';

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
  const [copySuccess, setCopySuccess] = useState(false);

return(
    // Modify the JSX for title and description
<h3
  className="text-lg font-bold text-gray-900 mb-2"
  data-tooltip-id="finding-tooltip"
  data-tooltip-content={finding.description}
>
  {finding.title}
</h3>
<p
  className="text-gray-700 mb-3 leading-relaxed"
  data-tooltip-id="finding-tooltip"
  data-tooltip-content="Click to expand for code details"
>
  {finding.description}
</p>

<Tooltip id="finding-tooltip" />
}

)

  // New component: HelpModal
  const HelpModal = ({ isOpen, onClose }) => {
        if (!isOpen) return null;

    return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-8 max-w-2xl w-full mx-4 max-h-96 overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">Help & Examples</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
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
            <pre className="bg-gray-100 p-4 rounded text-xs font-mono">
                    {`pragma solidity ^0.8.0;

                                contract SafeContract {
                                mapping(address => uint) balances;

                                function transfer(address to, uint amount) public {
                                require(balances[msg.sender] >= amount);
                                balances[msg.sender] -= amount;
                                balances[to] += amount;
                            }
                        }`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );

  const iconMap = {
    CRITICAL: <AlertCircle className="w-6 h-6" />,
    HIGH: <AlertTriangle className="w-6 h-6" />,
    MEDIUM: <AlertTriangle className="w-6 h-6" />,
    LOW: <Info className="w-6 h-6" />
  };

  const colorMap = {
    CRITICAL: 'border-red-300 bg-red-50 hover:bg-red-100',
    HIGH: 'border-red-300 bg-red-50 hover:bg-red-100',
    MEDIUM: 'border-yellow-300 bg-yellow-50 hover:bg-yellow-100',
    LOW: 'border-green-300 bg-green-50 hover:bg-green-100'
  };

  const handleCopyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(finding, null, 2));
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy: ', err);
    }
  };

  return (
   <div className="border-l-4 border-blue-500 rounded-lg p-6 bg-white shadow-sm hover:shadow-md transition-shadow">
    <div className="flex items-start justify-between gap-4">
      <div className="flex items-start gap-4 flex-1">
        {/* Icon / Leading Visual */}
        <div className="text-blue-500">
          <InfoIcon className="w-6 h-6" />
        </div>

        {/* Text Content */}
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 leading-none mb-1">
            {finding.title}
          </h3>
          <p className="text-sm text-gray-600 leading-relaxed">
            {finding.description}
          </p>
        </div>
      </div>

      {/* Action or Status Badge */}
      <span className="px-3 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
        {finding.status}
      </span>
    </div>
   </div>

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
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleCopyToClipboard();
            }}
            className="p-2 text-gray-500 hover:text-gray-700 transition-colors"
            title="Copy to clipboard"
          >
            {copySuccess ? <CheckCircle className="w-5 h-5 text-green-600" /> : <Copy className="w-5 h-5" />}
          </button>
        <SeverityBadge severity={finding.severity} />
      </div>
    </div>
  );

// Results List with premium styling
const ResultsList = ({ findings, fileName, loading, contractName }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('All');
  const [showSuccess, setShowSuccess] = useState(false);
  const [copyLinkSuccess, setCopyLinkSuccess] = useState(false);

  useEffect(() => {
    if (!loading && findings && findings.length === 0) {
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 3000);
    }
  }, [loading, findings]);

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

const handleCopyShareableLink = async () => {
  const reportData = {
    contractName,
    findings,
    summary: { critical, high, medium, low, total: findings.length },
    date: new Date().toISOString()
  };
  const encodedData = btoa(JSON.stringify(reportData));
  const shareableLink = `${window.location.origin}/share?data=${encodedData}`;

  try {
    await navigator.clipboard.writeText(shareableLink);
    setCopyLinkSuccess(true);
    setTimeout(() => setCopyLinkSuccess(false), 2000);
  } catch (err) {
    console.error('Failed to copy link: ', err);
  }
};

  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    const printContent = `
        <html>
        <head>
            <title>Security Scan Report - ${contractName}</title>
            <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            .summary { background: #f0f0f0; padding: 10px; margin-bottom: 20px; }
            .finding { border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; }
            .severity { font-weight: bold; }
            pre { background: #f9f9f9; padding: 10px; overflow-x: auto; }
            </style>
        </head>
        <body>
            <h1>Security Scan Report for ${contractName}</h1>
            <div class="summary">
            <p><strong>Total Findings:</strong> ${findings.length}</p>
            <p><strong>Critical:</strong> ${critical}</p>
            <p><strong>High:</strong> ${high}</p>
            <p><strong>Medium:</strong> ${medium}</p>
            <p><strong>Low:</strong> ${low}</p>
            </div>
            <h2>Findings</h2>
            ${findings.map((finding, idx) => `
            <div class="finding">
                <h3>${idx + 1}. ${finding.title}</h3>
                <p class="severity">Severity: ${finding.severity}</p>
                <p>${finding.description}</p>
                ${finding.line_number ? `<p>Line Number: ${finding.line_number}</p>` : ''}
                ${finding.code ? `<pre>${finding.code}</pre>` : ''}
            </div>
            `).join('')}
            <p><em>Generated by BlockScope Security Scanner on ${new Date().toLocaleString()}</em></p>
        </body>
        </html>
    `;
  printWindow.document.write(printContent);
  printWindow.document.close();
  printWindow.print();
};

  const filteredFindings = findings.filter(finding => {
    const matchesSearch = finding.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         finding.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterSeverity === 'All' || finding.severity === filterSeverity;
    return matchesSearch && matchesFilter;
  });

  const critical = findings.filter(f => f.severity === 'CRITICAL').length;
  const high = findings.filter(f => f.severity === 'HIGH').length;
  const medium = findings.filter(f => f.severity === 'MEDIUM').length;
  const low = findings.filter(f => f.severity === 'LOW').length;

const handleDownloadMarkdown = () => {
  const markdown = `# Security Scan Report for ${contractName}

## Summary
- **Total Findings**: ${findings.length}
- **Critical**: ${critical}
- **High**: ${high}
- **Medium**: ${medium}
- **Low**: ${low}

## Findings

${findings.map((finding, idx) => `
### ${idx + 1}. ${finding.title}
- **Severity**: ${finding.severity}
- **Description**: ${finding.description}
${finding.line_number ? `- **Line Number**: ${finding.line_number}` : ''}
${finding.code ? `\`\`\`solidity\n${finding.code}\n\`\`\`` : ''}
`).join('\n')}

---
*Generated by BlockScope Security Scanner on ${new Date().toLocaleString()}*
`;

  const dataUri = 'data:text/markdown;charset=utf-8,' + encodeURIComponent(markdown);
  const exportFileDefaultName = `${contractName}_security_report.md`;
  const linkElement = document.createElement('a');
  linkElement.setAttribute('href', dataUri);
  linkElement.setAttribute('download', exportFileDefaultName);
  linkElement.click();
};

  const handleDownloadJSON = () => {
    const dataStr = JSON.stringify({ contractName, findings, summary: { critical, high, medium, low, total: findings.length } }, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    const exportFileDefaultName = `${contractName}_security_report.json`;
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  return (
    <div className="space-y-8">
      {/* Search and Filter */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search vulnerabilities..."
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          {["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((level) => (
              <button
                onClick={handleCopyShareableLink}
                className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
                title="Copy Shareable Link"
              >
                {copyLinkSuccess ? <CheckCircle className="w-5 h-5 text-green-600" /> : <Copy className="w-5 h-5 text-gray-600" />}
              </button>

              <button
                onClick={handleDownloadMarkdown}
                className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
                title="Download Markdown Report"
                >
                <Download className="w-5 h-5 text-gray-600" />
              </button>

              <button
                onClick={handlePrint}
                className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
                title="Print Report"
                >
                <Printer className="w-5 h-5 text-gray-600" />
              </button>

            <button
              key={level}
              onClick={() => setFilterSeverity(level)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                filterSeverity === level
                  ? 'bg-gray-800 text-white shadow-md'
                  : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {level}
            </button>
          ))}
          <button
            onClick={handleDownloadJSON}
            className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
            title="Download JSON Report"
          >
            <Download className="w-5 h-5 text-gray-600" />
          </button>
        </div>
      </div>

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
           Security Findings ({filteredFindings.length} of {findings.length})
        </h3>
        <div className="space-y-4">
          {filteredFindings.map((finding, idx) => (
            <FindingCard key={idx} finding={finding} index={idx} />
          ))}
        </div>
      </div>
    </div>
  );
};

const ScanHistory = ({ scanHistory, onRescan, onToggleFavorite, onLoadFromHistory }) => {
 const [showDropdown, setShowDropdown] = useState(false);

 return (
   <div className="relative">
     <button
       onClick={() => setShowDropdown(!showDropdown)}
       className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-all"
     >
       <History className="w-4 h-4" />
       Scan History
     </button>
     {showDropdown && (
       <div className="absolute top-full mt-2 w-96 bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-h-64 overflow-y-auto">
         {scanHistory.length === 0 ? (
           <p className="p-4 text-gray-500">No scan history yet.</p>
         ) : (
           scanHistory.map((scan, idx) => (
             <div key={idx} className="p-4 border-b border-gray-100 hover:bg-gray-50">
               <div className="flex items-center justify-between">
                 <div className="flex-1">
                   <p className="font-semibold text-gray-900">{scan.contractName}</p>
                   <p className="text-sm text-gray-600">{scan.date}</p>
                   <p className="text-xs text-gray-500">Findings: {scan.findingsSummary.total}</p>
                 </div>
                 <div className="flex items-center gap-2">
                   <button
                     onClick={() => onToggleFavorite(idx)}
                     className="p-1 text-gray-500 hover:text-yellow-500"
                     title={scan.favorite ? "Remove from favorites" : "Add to favorites"}
                   >
                     {scan.favorite ? <Star className="w-4 h-4 text-yellow-500" /> : <StarOff className="w-4 h-4" />}
                   </button>
                   <button
                     onClick={() => onLoadFromHistory(scan)}
                     className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                   >
                     Load
                   </button>
                   <button
                     onClick={() => onRescan(scan)}
                     className="px-3 py-1 bg-green-500 text-white rounded text-sm hover:bg-green-600"                   >
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

// Scan Form with premium design
const ScanForm = ({ onSubmit, loading, scanHistory, onRescan, onToggleFavorite, onLoadFromHistory }) => {
  const [contractCode, setContractCode] = useState('');
  const [contractName, setContractName] = useState('');
  const [fileName, setFileName] = useState('');
  const [fileSize, setFileSize] = useState(0);
  const [filePreview, setFilePreview] = useState('');
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadHistory, setUploadHistory] = useState([]);
  const [showError, setShowError] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);

  // Load history from local storage on mount
  useEffect(() => {
    const history = JSON.parse(localStorage.getItem('upload_history') || '[]');
    setUploadHistory(history);
  }, []);

  useEffect(() => {
    if (error) {
      setShowError(true);
      setTimeout(() => setShowError(false), 5000);
    }
  }, [error]);

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
   )

  const handleFileUpload = (e) => {
    try {
      const file = e.target.files?.[0];
      if (!file) return;

      if (!file.name.endsWith('.sol')) {
        setError('❌ Invalid file type. Please upload a .sol file.');
        return;
      }

      if (file.size > 50 * 1024 * 1024) { // 50MB limit
        setError('❌ File size exceeds 50MB limit.');
        return;
      }

      setError('');
      setFileName(file.name);
      setFileSize(file.size);

      // Extract contract name from filename
      const nameWithoutExt = file.name.replace('.sol', '');
      setContractName(nameWithoutExt);

      const reader = new FileReader();
      reader.onloadstart = () => setUploadProgress(0);
      reader.onprogress = (e) => {
        if (e.lengthComputable) {
          setUploadProgress((e.loaded / e.total) * 100);
        }
      };
      reader.onload = (event) => {
        try {
          const content = event.target?.result;
          if (typeof content === 'string') {
            setContractCode(content);
            setFilePreview(content.substring(0, 500) + (content.length > 500 ? '...' : '')); // Preview first 500 chars
            setUploadProgress(100);

            // Add to history
            const newHistory = [{ name: file.name, size: file.size, date: new Date().toLocaleString() }, ...uploadHistory].slice(0, 10);
            setUploadHistory(newHistory);
            localStorage.setItem('upload_history', JSON.stringify(newHistory));
          }
        } catch (err) {
          setError('❌ Error reading file: ' + err.message);
        }
      };
      reader.onerror = () => {
        setError('❌ Failed to read file. Please try again.');
      };
      reader.readAsText(file);
    } catch (err) {
      setError('❌ Error handling file upload: ' + err.message);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
          <div className="flex justify-between items-center mb-6">
          <div>
           {/* Existing header content can stay or be adjusted */}
          </div>
          <ScanHistory
           scanHistory={scanHistory}
           onRescan={onRescan}
           onToggleFavorite={onToggleFavorite}
           onLoadFromHistory={onLoadFromHistory}
        />
    </div>

      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 text-red-800 px-6 py-4 rounded-lg shadow-md animate-pulse">
          <p className="font-semibold text-lg">{error}</p>
        </div>
      )}

      <div
        className={`relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 ${
          dragActive
            ? 'border-blue-500 bg-blue-50 shadow-xl scale-102 ring-4 ring-blue-200'
            : 'border-blue-300 bg-gradient-to-br from-blue-50 to-indigo-50 hover:shadow-lg hover:border-blue-400'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <div onClick={() => document.getElementById('fileInput').click()} className="cursor-pointer">
          <Upload className={`w-16 h-16 mx-auto mb-4 transition-transform ${dragActive ? 'scale-110 text-blue-700' : 'text-blue-600'}`} />
          <p className="text-gray-900 font-bold text-xl mb-2">📁 Upload Your Solidity Contract</p>
          <p className="text-gray-600 mb-2">or drag and drop</p>
          <p className="text-gray-500 text-sm">.sol files only, max 50MB</p>
        </div>
        <input
          id="fileInput"
          type="file"
          accept=".sol"
          onChange={handleFileUpload}
          className="hidden"
        />
        {uploadProgress > 0 && uploadProgress < 100 && (
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full transition-all duration-300" style={{ width: `${uploadProgress}%` }}></div>
            </div>
            <p className="text-sm text-gray-600 mt-2">Uploading... {Math.round(uploadProgress)}%</p>
          </div>
        )}
      </div>

      {fileName && (
        <div className="bg-green-50 border-l-4 border-green-500 px-6 py-4 rounded-lg shadow-md">
          <p className="text-green-800 font-semibold">✅ File selected: {fileName}</p>
          <p className="text-green-700 text-sm">Size: {formatFileSize(fileSize)}</p>
          {filePreview && (
            <div className="mt-3">
              <p className="text-green-800 font-medium text-sm mb-2">Preview:</p>
              <pre className="bg-white p-3 rounded text-xs text-gray-800 font-mono overflow-x-auto max-h-32">{filePreview}</pre>
            </div>
          )}
        </div>
      )}

      {/* Upload History */}
      {uploadHistory.length > 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h4 className="font-semibold text-gray-900 mb-3">Recent Uploads</h4>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {uploadHistory.map((item, idx) => (
              <div key={idx} className="flex justify-between text-sm text-gray-600">
                <span>{item.name}</span>
                <span>{formatFileSize(item.size)} - {item.date}</span>
              </div>
            ))}
          </div>
        </div>
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
  const [scanHistory, setScanHistory] = useState([]);
  const [runTour, setRunTour] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [contractCode, setContractCode] = useState('');

  const tourSteps = [
  {
    target: '.upload-area',
    content: 'Upload your Solidity contract file here or paste the code below.',
  },
  {
    target: '.scan-button',
    content: 'Click this button to start the security scan.',
  },
  {
    target: '.results-section',
    content: 'View your scan results and findings here.',
  },
];

// Trigger tour on first visit (check localStorage)
useEffect(() => {
  const hasSeenTour = localStorage.getItem('hasSeenTour');
  if (!hasSeenTour) {
    setRunTour(true);
    localStorage.setItem('hasSeenTour', 'true');
  }
}, []);

// In App component, add useEffect for shortcuts
useEffect(() => {
  const handleKeyDown = (e) => {
    if (e.ctrlKey || e.metaKey) {
      switch (e.key) {
        case 's':
          e.preventDefault();
          // Trigger scan if on scan page
          if (currentPage === 'scan') {
            // Call handleScan with current code
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
    }
  };

  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}, [currentPage]);


  useEffect(() => {
 const history = JSON.parse(localStorage.getItem('scan_history') || '[]');
 setScanHistory(history);
}, []);

const handleScan = async (contractCode, uploadedContractName) => {
 try {
   setLoading(true);
   setError('');
   setContractName(uploadedContractName);

   const response = await apiClient.scanContract(contractCode, uploadedContractName);

   try {
     const scanFindings = response.findings || [];
     setFindings(Array.isArray(scanFindings) ? scanFindings : []);

     // Save to scan history
     const newScan = {
       contractName: uploadedContractName,
       contractCode,
       findings: scanFindings,
       findingsSummary: {
         critical: scanFindings.filter(f => f.severity === 'CRITICAL').length,
         high: scanFindings.filter(f => f.severity === 'HIGH').length,
         medium: scanFindings.filter(f => f.severity === 'MEDIUM').length,
         low: scanFindings.filter(f => f.severity === 'LOW').length,
         total: scanFindings.length
       },
       date: new Date().toLocaleString(),
       favorite: false
     };
     const updatedHistory = [newScan, ...scanHistory].slice(0, 10);
     setScanHistory(updatedHistory);
     localStorage.setItem('scan_history', JSON.stringify(updatedHistory));

     setCurrentPage('results');
   } catch (parseErr) {
     setError('Error parsing results: ' + parseErr.message);
     setFindings([]);
   }
 } catch (err) {
   setError('Scan failed: ' + err.message);
   console.error('Scan error:', err);
 } finally {
   setLoading(false);
 }
};

const handleRescan = async (scan) => {
 await handleScan(scan.contractCode, scan.contractName);
};

const handleToggleFavorite = (index) => {
 const updatedHistory = [...scanHistory];
 updatedHistory[index].favorite = !updatedHistory[index].favorite;
 setScanHistory(updatedHistory);
 localStorage.setItem('scan_history', JSON.stringify(updatedHistory));
};

const handleLoadFromHistory = (scan) => {
 setContractCode(scan.contractCode);
 setContractName(scan.contractName);
 setCurrentPage('scan');
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
            <button
                onClick={() => setShowHelpModal(true)}
                className="text-blue-300 hover:text-white"
            >
            Help
            </button>
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

      <Joyride
        steps={tourSteps}
        run={runTour}
        continuous
        showSkipButton
        showProgress
        callback={(data) => {
            if (data.status === 'finished' || data.status === 'skipped') {
            setRunTour(false);
         }
     }}
/>

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