import React, { useState } from 'react';
import axios from 'axios';
import { 
  ShieldCheck, AlertTriangle, XCircle, CheckCircle, 
  MapPin, Phone, Calendar, Info, Edit3, Trash2
} from 'lucide-react';

const AHMEDABAD_WARDS = [
  "Navrangpura", "Vastrapur", "Satellite", "Naranpura", "Girdhar Nagar", 
  "Paldi", "Bodakdev", "Jodhpur", "Bopal", "Thaltej", "Ranip", 
  "Chandkheda", "Sabarmati", "Nikol", "Maninagar", "Kalupur", 
  "Jamalpur", "Shahpur", "Dariapur", "Astodia"
];

const COMPLAINT_CATEGORIES = [
  "Sewer & Drainage", "Garbage & Waste", "Streetlights", 
  "Roads & Potholes", "Water Supply", "Other"
];

export default function Review({ 
  quarantineRecords, 
  flaggedRecords, 
  fetchData 
}) {
  const [activeSubTab, setActiveSubTab] = useState('flagged'); // 'flagged' or 'quarantine'
  const [editingRecordId, setEditingRecordId] = useState(null);
  
  // Edited values state
  const [editWard, setEditWard] = useState('');
  const [editCategory, setEditCategory] = useState('');
  const [editSeverity, setEditSeverity] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [editPincode, setEditPincode] = useState('');

  // Active records listing based on sub-tab
  const records = activeSubTab === 'flagged' 
    ? flaggedRecords.filter(r => r.status === 'pending')
    : quarantineRecords.filter(r => r.status === 'pending');

  const startEditing = (rec) => {
    setEditingRecordId(rec.id);
    const clean = rec.partial_clean || {};
    setEditWard(clean.ward_name || '');
    setEditCategory(clean.complaint_category || 'Other');
    setEditSeverity(clean.severity || 'Medium');
    setEditDesc(clean.description || rec.raw_data?.["Complaint Details"] || '');
    setEditPhone(clean.phone || rec.raw_data?.["Reporter Phone"] || '');
    setEditPincode(clean.postal_code || rec.raw_data?.["Pincode"] || '');
  };

  const handleReviewAction = async (recordId, action) => {
    try {
      const payload = {
        record_id: recordId,
        source_table: activeSubTab === 'flagged' ? 'flagged_records' : 'quarantine_records',
        action: action,
        reviewer: 'Human Reviewer'
      };

      if (action === 'approve' && editingRecordId === recordId) {
        payload.edited_data = {
          ward_name: editWard || null,
          complaint_category: editCategory,
          severity: editSeverity,
          description: editDesc,
          phone: editPhone || null,
          postal_code: editPincode || null
        };
      }

      await axios.post('http://127.0.0.1:8000/review/submit', payload);
      setEditingRecordId(null);
      if (fetchData) fetchData();
    } catch (err) {
      alert("Error submitting review action: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <ShieldCheck className="text-blue-600" />
            Human Verification Center
          </h2>
          <p className="text-slate-500 text-sm">Review, correct, and promote records marked as suspicious or incomplete by the AI layer.</p>
        </div>

        {/* Sub-tabs toggler */}
        <div className="flex bg-white p-1 rounded-xl border border-slate-200 w-full md:w-auto shadow-sm">
          <button
            onClick={() => { setActiveSubTab('flagged'); setEditingRecordId(null); }}
            className={`flex-1 md:flex-initial px-4 py-1.5 rounded-lg text-xs font-bold tracking-wide transition-all ${
              activeSubTab === 'flagged'
                ? 'bg-amber-600 text-white shadow-md shadow-amber-100'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            Flagged Records ({flaggedRecords.filter(r => r.status === 'pending').length})
          </button>
          <button
            onClick={() => { setActiveSubTab('quarantine'); setEditingRecordId(null); }}
            className={`flex-1 md:flex-initial px-4 py-1.5 rounded-lg text-xs font-bold tracking-wide transition-all ${
              activeSubTab === 'quarantine'
                ? 'bg-rose-600 text-white shadow-md shadow-rose-100'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            Quarantine Pool ({quarantineRecords.filter(r => r.status === 'pending').length})
          </button>
        </div>
      </div>

      {/* Main Review queue listing */}
      <div className="space-y-4">
        {records.length > 0 ? (
          records.map((rec) => {
            const isEditing = editingRecordId === rec.id;
            const flags = rec.flags || (rec.partial_clean?.flags) || [];
            const confidence = rec.confidence_score || 0.0;
            const raw = rec.raw_data || {};

            return (
              <div 
                key={rec.id} 
                className={`glass-card p-6 rounded-2xl border transition-all duration-300 ${
                  isEditing ? 'border-blue-500 ring-4 ring-blue-50 shadow-lg' : 'hover:border-slate-300'
                }`}
              >
                {/* Header: Flags & Confidence */}
                <div className="flex flex-wrap justify-between items-center gap-3 border-b border-slate-100 pb-4 mb-4">
                  <div className="flex items-center gap-2">
                    <span className={`h-2.5 w-2.5 rounded-full ${activeSubTab === 'flagged' ? 'bg-amber-500 animate-pulse' : 'bg-rose-500 animate-pulse'}`}></span>
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Record ID: {rec.id.slice(0, 8)}</span>
                    {flags.map((flag, idx) => (
                      <span key={idx} className="bg-slate-50 text-slate-500 border border-slate-200 px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider">
                        {flag.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <span className="text-[10px] text-slate-400 uppercase tracking-wide block font-bold">AI Confidence</span>
                      <span className={`text-sm font-mono font-bold ${
                        confidence >= 0.70 ? 'text-amber-600' : 'text-rose-600'
                      }`}>{(confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>

                {/* Grid comparing original vs editable/clean */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Left Column: Original Unstructured CSV Raw Input */}
                  <div className="bg-slate-50/50 p-4 rounded-xl border border-slate-100">
                    <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-1.5">
                      <Info size={14} className="text-slate-300" />
                      Original Input (Raw Data)
                    </h4>
                    
                    <div className="space-y-3.5 text-xs">
                      <div>
                        <span className="text-slate-400 block font-bold uppercase text-[9px] tracking-tight">Ward/Area Specified</span>
                        <span className="text-slate-700 font-bold bg-white px-2.5 py-1.5 rounded-lg inline-block mt-1 border border-slate-100 shadow-sm min-w-[120px]">
                          {raw["Ward/Area"] || <em className="text-slate-300 font-normal">empty</em>}
                        </span>
                      </div>

                      <div>
                        <span className="text-slate-400 block font-bold uppercase text-[9px] tracking-tight">Complaint Details</span>
                        <span className="text-slate-700 block bg-white p-3 rounded-lg mt-1 leading-relaxed border border-slate-100 shadow-sm font-medium italic">
                          "{raw["Complaint Details"] || <em className="text-slate-300 font-normal">empty</em>}"
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="text-slate-400 block font-bold uppercase text-[9px] tracking-tight">Reporter Phone</span>
                          <span className="text-slate-600 font-mono bg-white px-2 py-1 rounded inline-block mt-1 border border-slate-100">
                            {raw["Reporter Phone"] || <em className="text-slate-300 font-normal">empty</em>}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block font-bold uppercase text-[9px] tracking-tight">Pincode</span>
                          <span className="text-slate-600 font-mono bg-white px-2 py-1 rounded inline-block mt-1 border border-slate-100">
                            {raw["Pincode"] || <em className="text-slate-300 font-normal">empty</em>}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Right Column: AI Proposed Cleaned Input (Editable) */}
                  <div className="bg-blue-50/20 p-4 rounded-xl border border-blue-100/50">
                    <div className="flex justify-between items-center mb-4">
                      <h4 className="text-[10px] font-bold text-blue-700 uppercase tracking-widest flex items-center gap-1.5">
                        <Edit3 size={14} />
                        AI Proposed Cleaned Format
                      </h4>
                      {!isEditing && (
                        <button
                          onClick={() => startEditing(rec)}
                          className="text-[10px] text-blue-600 hover:text-blue-700 flex items-center gap-1 font-bold uppercase tracking-wider transition bg-white px-2 py-1 rounded border border-blue-100 shadow-sm"
                        >
                          <Edit3 size={10} />
                          Unlock Fields
                        </button>
                      )}
                    </div>

                    {isEditing ? (
                      /* Editing Form Inputs */
                      <div className="space-y-4 text-xs">
                        <div>
                          <label className="text-slate-500 block font-bold uppercase text-[9px] mb-1">Standardized Ward</label>
                          <select
                            value={editWard}
                            onChange={(e) => setEditWard(e.target.value)}
                            className="w-full bg-white text-slate-900 rounded-lg border border-slate-200 px-3 py-2 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none font-bold"
                          >
                            <option value="">Select Ward...</option>
                            {AHMEDABAD_WARDS.map(w => (
                              <option key={w} value={w}>{w}</option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="text-slate-500 block font-bold uppercase text-[9px] mb-1">Description (Verified)</label>
                          <textarea
                            rows={3}
                            value={editDesc}
                            onChange={(e) => setEditDesc(e.target.value)}
                            className="w-full bg-white text-slate-900 rounded-lg border border-slate-200 px-3 py-2 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none resize-none leading-relaxed font-medium"
                          />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="text-slate-500 block font-bold uppercase text-[9px] mb-1">Category</label>
                            <select
                              value={editCategory}
                              onChange={(e) => setEditCategory(e.target.value)}
                              className="w-full bg-white text-slate-900 rounded-lg border border-slate-200 px-3 py-2 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none font-bold"
                            >
                              {COMPLAINT_CATEGORIES.map(c => (
                                <option key={c} value={c}>{c}</option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <label className="text-slate-500 block font-bold uppercase text-[9px] mb-1">Severity</label>
                            <select
                              value={editSeverity}
                              onChange={(e) => setEditSeverity(e.target.value)}
                              className="w-full bg-white text-slate-900 rounded-lg border border-slate-200 px-3 py-2 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none font-bold"
                            >
                              <option value="Low">Low</option>
                              <option value="Medium">Medium</option>
                              <option value="High">High</option>
                            </select>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="text-slate-500 block font-bold uppercase text-[9px] mb-1">Phone</label>
                            <input
                              type="text"
                              value={editPhone}
                              onChange={(e) => setEditPhone(e.target.value)}
                              placeholder="9876543210"
                              className="w-full bg-white text-slate-900 rounded-lg border border-slate-200 px-3 py-2 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none font-mono font-bold"
                            />
                          </div>
                          <div>
                            <label className="text-slate-500 block font-bold uppercase text-[9px] mb-1">Pincode</label>
                            <input
                              type="text"
                              value={editPincode}
                              onChange={(e) => setEditPincode(e.target.value)}
                              placeholder="380015"
                              className="w-full bg-white text-slate-900 rounded-lg border border-slate-200 px-3 py-2 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none font-mono font-bold"
                            />
                          </div>
                        </div>
                      </div>
                    ) : (
                      /* Standby Proposed values display */
                      <div className="space-y-4 text-xs leading-relaxed">
                        <div className="flex items-center gap-2">
                          <MapPin size={16} className="text-blue-600" />
                          <span className="text-slate-400 font-bold uppercase text-[9px] tracking-tight">Resolved Ward:</span>
                          <span className="font-bold text-blue-800 bg-blue-100 border border-blue-200 px-3 py-1 rounded-full">
                            {rec.partial_clean?.ward_name || "Unresolved"}
                          </span>
                        </div>

                        <div className="bg-white p-3 rounded-xl border border-blue-50 shadow-sm">
                          <span className="text-slate-400 block font-bold uppercase text-[9px] mb-1.5 tracking-tight">Standardized Text Proposal:</span>
                          <p className="text-slate-700 font-medium italic">"{rec.partial_clean?.description || "No proposal available"}"</p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div className="flex flex-col gap-1">
                            <span className="text-slate-400 font-bold uppercase text-[9px] tracking-tight">Classification:</span>
                            <span className="text-slate-900 font-bold">{rec.partial_clean?.complaint_category || 'Other'}</span>
                          </div>
                          <div className="flex flex-col gap-1">
                            <span className="text-slate-400 font-bold uppercase text-[9px] tracking-tight">Priority Assessment:</span>
                            <span className={`font-bold ${
                              rec.partial_clean?.severity === 'High' ? 'text-rose-600' :
                              rec.partial_clean?.severity === 'Medium' ? 'text-amber-600' : 'text-emerald-600'
                            }`}>{rec.partial_clean?.severity || 'Medium'}</span>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 font-mono">
                          <div className="flex items-center gap-2">
                            <Phone size={12} className="text-slate-400" />
                            <span className="text-slate-600 font-bold">{rec.partial_clean?.phone || 'N/A'}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-slate-400 font-bold uppercase text-[9px]">PIN:</span>
                            <span className="text-slate-600 font-bold">{rec.partial_clean?.postal_code || 'N/A'}</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Submitactions footer */}
                <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-slate-100">
                  <button
                    onClick={() => handleReviewAction(rec.id, 'reject')}
                    className="flex items-center gap-1.5 px-4 py-2 bg-slate-50 hover:bg-rose-50 text-slate-400 hover:text-rose-600 border border-slate-100 hover:border-rose-100 rounded-xl text-xs font-bold uppercase tracking-wider transition-all duration-300"
                  >
                    <Trash2 size={14} />
                    Discard
                  </button>

                  {isEditing ? (
                    <button
                      onClick={() => handleReviewAction(rec.id, 'approve')}
                      className="flex items-center gap-1.5 px-6 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold uppercase tracking-widest transition-all duration-300 shadow-md shadow-emerald-100"
                    >
                      <CheckCircle size={14} />
                      Verify & Commit
                    </button>
                  ) : (
                    <button
                      onClick={() => handleReviewAction(rec.id, 'approve')}
                      className="flex items-center gap-1.5 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold uppercase tracking-widest transition-all duration-300 shadow-md shadow-blue-100"
                    >
                      <ShieldCheck size={14} />
                      Approve AI Output
                    </button>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <div className="bg-white py-20 text-center rounded-2xl border border-slate-100 shadow-sm flex flex-col justify-center items-center space-y-4">
            <div className="bg-emerald-50 p-4 rounded-full">
              <CheckCircle size={48} className="text-emerald-500" />
            </div>
            <div>
              <h4 className="text-lg font-bold text-slate-900 tracking-tight">No Pending Verification Items</h4>
              <p className="text-sm text-slate-500 mt-1 max-w-xs mx-auto font-medium">
                The review pool for this category is currently empty. All records have been processed.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
