import React, { useState } from 'react';
import axios from 'axios';
import {
  UploadCloud, Play, Loader, ShieldAlert,
  ArrowRight, FileSpreadsheet, RefreshCcw,
  MapPin, CheckCircle, RefreshCw, AlertTriangle, X, Download
} from 'lucide-react';

export default function Upload({ onUploadSuccess }) {
  const [files, setFiles] = useState([]);
  const [numRows, setNumRows] = useState(50);
  const [isProcessing, setIsProcessing] = useState(false);
  const [pipelineStep, setPipelineStep] = useState(0);
  const [batchResult, setBatchResult] = useState(null);
  const [mergeOption, setMergeOption] = useState('both');
  const [uploadMode, setUploadMode] = useState('single'); // 'single' or 'multi'

  const pipelineSteps = [
    { label: "Parsing CSV & Ingesting Raw Data", desc: "Verifying formatting of input dataset" },
    { label: "Resolving Ward Names", desc: "Matching and correcting ward misspellings & ambiguous locations" },
    { label: "Classifying Complaint Categories", desc: "Analyzing semantic context & severity mapping" },
    { label: "Detecting & Deduplicating Records", desc: "Matching identical descriptions, phone, and time-windows" },
    { label: "Geocoding Coordinates", desc: "Assigning precise latitude and longitude based on resolved geography" },
    { label: "Normalizing Contact Formats", desc: "Standardizing dates, pincodes, and phone formats" },
    { label: "Computing Confidence Index", desc: "Determining routing to structured/flagged/quarantine database tables" }
  ];

  // Simulates progress steps of the pipeline for UX wow factor
  const runProgressSimulation = (callback) => {
    setIsProcessing(true);
    setPipelineStep(0);
    setBatchResult(null);

    let currentStep = 0;
    const interval = setInterval(() => {
      currentStep++;
      if (currentStep < pipelineSteps.length) {
        setPipelineStep(currentStep);
      } else {
        clearInterval(interval);
        callback();
      }
    }, 1200);
  };

  const handleFileChange = (e) => {
    if (e.target.files) {
      if (uploadMode === 'single') {
        setFiles([e.target.files[0]]);
      } else {
        setFiles(Array.from(e.target.files));
      }
    }
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (files.length === 0) return;

    runProgressSimulation(async () => {
      try {
        if (uploadMode === 'single') {
          // Single file upload
          const formData = new FormData();
          formData.append('file', files[0]);

          const response = await axios.post('http://127.0.0.1:8000/upload/csv', formData, {
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          });
          setBatchResult(response.data);
        } else {
          // Multiple file merge
          const formData = new FormData();
          files.forEach((file) => {
            formData.append('files', file);
          });

          const response = await axios.post(
            `http://127.0.0.1:8000/upload/csv/merge?merge_option=${mergeOption}`,
            formData,
            {
              headers: {
                'Content-Type': 'multipart/form-data'
              }
            }
          );
          setBatchResult(response.data);
        }
        setIsProcessing(false);
        if (onUploadSuccess) onUploadSuccess();
      } catch (err) {
        alert(err.response?.data?.detail || "Upload failed");
        setIsProcessing(false);
      }
    });
  };

  const handleGenerateMock = async () => {
    runProgressSimulation(async () => {
      try {
        const response = await axios.post(`http://127.0.0.1:8000/upload/generate-mock?num_rows=${numRows}`);
        setBatchResult(response.data);
        setIsProcessing(false);
        if (onUploadSuccess) onUploadSuccess();
      } catch (err) {
        alert("Failed to generate mock data");
        setIsProcessing(false);
      }
    });
  };

  const downloadBatchCSV = () => {
    if (!batchResult || !batchResult.structured || batchResult.structured.length === 0) {
      alert("No structured records available in this batch to download.");
      return;
    }

    const dataToExport = batchResult.structured.map(r => ({
      "Complaint ID": r.complaint_id,
      "Ward": r.ward_name || "N/A",
      "Category": r.complaint_category,
      "Description": r.description,
      "Latitude": r.lat || "",
      "Longitude": r.lng || "",
      "Severity": r.severity || "Low",
      "Confidence Score": `${((r.confidence_score || 1.0) * 100).toFixed(0)}%`
    }));

    const filename = `urbanfix_cleaned_batch_${batchResult.batch_id.slice(0, 8)}.csv`;

    const headers = Object.keys(dataToExport[0]);
    const csvRows = [
      headers.join(','),
      ...dataToExport.map(row => 
        headers.map(fieldName => {
          const value = row[fieldName] !== undefined && row[fieldName] !== null ? row[fieldName] : "";
          const escaped = ('' + value).replace(/"/g, '""');
          return `"${escaped}"`;
        }).join(',')
      )
    ];

    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
          <UploadCloud className="text-blue-600" />
          Ingest & Process Data
        </h2>
        <p className="text-slate-500 text-sm">Upload unstructured CSV files or generate mock city datasets to clean.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ingestion Panel */}
        <div className="space-y-6">
          {/* Upload Mode Selector */}
          <div className="glass-card p-6 rounded-2xl">
            <h3 className="text-lg font-bold text-slate-900 mb-4">Upload Mode</h3>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="single"
                  checked={uploadMode === 'single'}
                  onChange={(e) => {
                    setUploadMode(e.target.value);
                    setFiles([]);
                  }}
                  disabled={isProcessing}
                  className="w-4 h-4"
                />
                <span className="text-sm font-medium text-slate-700">Single File</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="multi"
                  checked={uploadMode === 'multi'}
                  onChange={(e) => {
                    setUploadMode(e.target.value);
                    setFiles([]);
                  }}
                  disabled={isProcessing}
                  className="w-4 h-4"
                />
                <span className="text-sm font-medium text-slate-700">Multiple Files (Merge)</span>
              </label>
            </div>
          </div>

          {/* File Upload card */}
          <div className="glass-card p-6 rounded-2xl">
            <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
              <FileSpreadsheet className="text-blue-600" size={20} />
              Unstructured CSV Ingest
            </h3>

            <form onSubmit={handleUpload} className="space-y-4">
              <div className="border-2 border-dashed border-slate-200 hover:border-blue-500/50 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-all duration-300 bg-slate-50 hover:bg-blue-50/30">
                <input
                  type="file"
                  id="csv-file"
                  accept=".csv"
                  onChange={handleFileChange}
                  className="hidden"
                  disabled={isProcessing}
                  multiple={uploadMode === 'multi'}
                />
                <label htmlFor="csv-file" className="flex flex-col items-center cursor-pointer text-center w-full">
                  <UploadCloud size={44} className="text-slate-400 mb-3" />
                  <span className="text-sm font-bold text-slate-700">
                    {files.length > 0
                      ? `${files.length} file${files.length !== 1 ? 's' : ''} selected`
                      : uploadMode === 'multi'
                        ? "Choose multiple CSV files or drag here"
                        : "Choose CSV file or drag here"
                    }
                  </span>
                  <span className="text-xs text-slate-500 mt-1 font-medium">Accepts raw 311 files up to 20MB</span>
                </label>
              </div>

              {/* File list */}
              {files.length > 0 && (
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 space-y-2">
                  {files.map((file, idx) => (
                    <div key={idx} className="flex items-center justify-between bg-white p-2.5 rounded-lg border border-slate-100">
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <FileSpreadsheet size={16} className="text-blue-600 flex-shrink-0" />
                        <span className="text-sm font-medium text-slate-700 truncate">{file.name}</span>
                        <span className="text-xs text-slate-500 flex-shrink-0">({(file.size / 1024).toFixed(2)} KB)</span>
                      </div>
                      {uploadMode === 'multi' && (
                        <button
                          type="button"
                          onClick={() => removeFile(idx)}
                          disabled={isProcessing}
                          className="ml-2 text-slate-400 hover:text-rose-600 transition-colors flex-shrink-0"
                        >
                          <X size={16} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Merge option selector for multiple files */}
              {uploadMode === 'multi' && files.length > 1 && (
                <div className="bg-blue-50 rounded-xl p-4 border border-blue-100 space-y-3">
                  <span className="text-xs font-bold text-blue-700 uppercase tracking-wide block">Merge Strategy</span>
                  <div className="space-y-2">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="radio"
                        value="latest"
                        checked={mergeOption === 'latest'}
                        onChange={(e) => setMergeOption(e.target.value)}
                        disabled={isProcessing}
                        className="w-4 h-4"
                      />
                      <span className="text-sm font-medium text-blue-900">
                        Latest Only
                        <span className="block text-xs text-blue-700 font-normal">Use only the most recent file</span>
                      </span>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="radio"
                        value="previous"
                        checked={mergeOption === 'previous'}
                        onChange={(e) => setMergeOption(e.target.value)}
                        disabled={isProcessing}
                        className="w-4 h-4"
                      />
                      <span className="text-sm font-medium text-blue-900">
                        Previous Only
                        <span className="block text-xs text-blue-700 font-normal">Use only the first file</span>
                      </span>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="radio"
                        value="both"
                        checked={mergeOption === 'both'}
                        onChange={(e) => setMergeOption(e.target.value)}
                        disabled={isProcessing}
                        className="w-4 h-4"
                      />
                      <span className="text-sm font-medium text-blue-900">
                        Combine All
                        <span className="block text-xs text-blue-700 font-normal">Merge all selected files together</span>
                      </span>
                    </label>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={files.length === 0 || isProcessing}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-blue-100"
              >
                {isProcessing ? (
                  <>
                    <Loader className="animate-spin" size={18} />
                    <span>Processing Pipeline...</span>
                  </>
                ) : (
                  <>
                    <Play size={18} />
                    <span>Run AI Cleaning Layer</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Generator card */}
          <div className="glass-card p-6 rounded-2xl">
            <h3 className="text-lg font-bold text-slate-900 mb-2 flex items-center gap-2">
              <RefreshCcw className="text-emerald-600" size={20} />
              Faker Mock Generator
            </h3>
            <p className="text-xs text-slate-500 mb-4 font-medium leading-relaxed">
              Simulate messy, unstructured real-world city complaints (Gujarati translations, invalid numbers, duplicate entries).
            </p>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-slate-500 font-bold block mb-2 uppercase tracking-wide">Number of complaints</label>
                <input
                  type="range"
                  min="10"
                  max="150"
                  step="10"
                  value={numRows}
                  onChange={(e) => setNumRows(parseInt(e.target.value))}
                  disabled={isProcessing}
                  className="w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-emerald-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400 font-bold mt-1">
                  <span>10 records</span>
                  <span className="text-emerald-700 font-bold text-sm bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded">{numRows} records</span>
                  <span>150 records</span>
                </div>
              </div>

              <button
                type="button"
                onClick={handleGenerateMock}
                disabled={isProcessing}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-50 shadow-md shadow-emerald-100"
              >
                {isProcessing ? (
                  <>
                    <Loader className="animate-spin" size={18} />
                    <span>Processing Pipeline...</span>
                  </>
                ) : (
                  <>
                    <RefreshCw size={18} />
                    <span>Generate & Process Dirty Data</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Status / Output Panel */}
        <div className="glass-card p-6 rounded-2xl flex flex-col justify-between min-h-[400px]">
          {isProcessing ? (
            /* Pipeline steps visualization */
            <div className="space-y-6 my-auto">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="h-10 w-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  <div className="absolute inset-0 flex items-center justify-center text-xs font-bold text-blue-600">AI</div>
                </div>
                <div>
                  <h4 className="text-md font-bold text-slate-900">AI Cleaning Pipeline Running</h4>
                  <p className="text-xs text-slate-500 font-medium">Processing live LLM calls & normalization heuristics</p>
                </div>
              </div>

              <div className="space-y-3.5 relative pl-4 border-l border-slate-100">
                {pipelineSteps.map((step, idx) => {
                  const isCurrent = idx === pipelineStep;
                  const isDone = idx < pipelineStep;
                  return (
                    <div
                      key={idx}
                      className={`relative flex items-start gap-3 transition-opacity duration-300 ${
                        isCurrent ? 'opacity-100 scale-100' : isDone ? 'opacity-60' : 'opacity-30'
                      }`}
                    >
                      {/* Status indicatordot */}
                      <span className={`absolute -left-[21px] flex h-2.5 w-2.5 rounded-full ${
                        isCurrent ? 'bg-blue-600 ring-4 ring-blue-100 animate-pulse' :
                        isDone ? 'bg-emerald-500' : 'bg-slate-200'
                      }`}></span>
                      <div>
                        <h5 className={`text-xs font-bold ${isCurrent ? 'text-blue-700' : 'text-slate-700'}`}>
                          {step.label}
                        </h5>
                        <p className="text-[10px] text-slate-400 font-medium mt-0.5">{step.desc}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : batchResult ? (
            /* Execution Result Card */
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-50 text-emerald-600 rounded-xl border border-emerald-100 shadow-sm">
                  <CheckCircle size={24} />
                </div>
                <div>
                  <h4 className="text-md font-bold text-slate-900">Batch Cleaning Successful</h4>
                  <p className="text-xs text-slate-500 font-bold">Batch ID: {batchResult.batch_id.slice(0, 8)}...</p>
                  {batchResult.merge_info && (
                    <p className="text-xs text-slate-400 font-medium mt-1">
                      {batchResult.merge_info.merge_option === 'both'
                        ? `Merged ${batchResult.merge_info.total_files} files`
                        : `Used ${batchResult.merge_info.merge_option} file`
                      } ({batchResult.merge_info.total_records_merged} records)
                    </p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Structured Records</span>
                  <p className="text-xl font-bold text-emerald-600 mt-1">{batchResult.structured.length}</p>
                  <span className="text-[10px] text-slate-500 font-medium italic">Routed to master table</span>
                </div>

                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Flagged Reviews</span>
                  <p className="text-xl font-bold text-amber-600 mt-1">{batchResult.flagged.length}</p>
                  <span className="text-[10px] text-slate-500 font-medium italic">Confidence: 50% - 84%</span>
                </div>

                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Quarantined Records</span>
                  <p className="text-xl font-bold text-rose-600 mt-1">{batchResult.quarantine.length}</p>
                  <span className="text-[10px] text-slate-500 font-medium italic">Confidence &lt; 50%</span>
                </div>

                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Accuracy Score</span>
                  <p className="text-xl font-bold text-blue-600 mt-1">
                    {((batchResult.report?.avg_confidence || 0) * 100).toFixed(0)}%
                  </p>
                  <span className="text-[10px] text-slate-500 font-medium italic">Batch average confidence</span>
                </div>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-100 shadow-sm text-xs text-slate-600 space-y-2 font-medium">
                <div className="flex justify-between border-b border-slate-50 pb-2">
                  <span className="text-slate-400 font-bold uppercase tracking-wider text-[9px]">Duplicates Found:</span>
                  <span className="font-mono text-slate-900 font-bold">{batchResult.report?.duplicate_count || 0}</span>
                </div>
                <div className="flex justify-between pt-1">
                  <span className="text-slate-400 font-bold uppercase tracking-wider text-[9px]">Execution Time:</span>
                  <span className="font-mono text-slate-900 font-bold">{batchResult.report?.processing_time_ms || 0} ms</span>
                </div>
              </div>

              {batchResult.structured && batchResult.structured.length > 0 && (
                <button
                  type="button"
                  onClick={downloadBatchCSV}
                  className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-100 transition-all duration-300"
                >
                  <Download size={14} />
                  Download Cleaned Batch CSV ({batchResult.structured.length} Records)
                </button>
              )}
            </div>
          ) : (
            /* Standby Card */
            <div className="my-auto text-center space-y-4 py-8">
              <div className="inline-flex p-4 bg-slate-50 text-slate-300 rounded-full border border-slate-100">
                <ShieldAlert size={40} />
              </div>
              <div>
                <h4 className="text-md font-bold text-slate-800">Awaiting Ingestion Stream</h4>
                <p className="text-xs text-slate-500 max-w-xs mx-auto mt-1 font-medium leading-relaxed">
                  Upload a dataset or trigger our mock pipeline generator to watch AI data sorting in action.
                </p>
              </div>
            </div>
          )}

          {batchResult && !isProcessing && (
            <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider text-center border-t border-slate-50 pt-4 mt-6">
              Navigate to the <strong className="text-blue-600">Dashboard</strong> or <strong className="text-blue-600">Review Center</strong> to handle flagged items.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
