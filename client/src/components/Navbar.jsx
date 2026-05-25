import React from 'react';
import { Shield, LayoutDashboard, UploadCloud, EyeOff } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'upload', label: 'Data Ingestion', icon: UploadCloud },
    { id: 'review', label: 'Review Center', icon: Shield },
  ];

  return (
    <nav className="bg-white sticky top-0 z-50 px-6 py-4 flex items-center justify-between border-b border-slate-200 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="bg-blue-600 text-white p-2 rounded-xl border border-blue-500 shadow-sm">
          <Shield size={24} />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            UrbanFix <span className="text-blue-600">311</span>
          </h1>
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Phase 1: Sorting & Organization</p>
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-sm transition-all duration-300 ${
                isActive
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-200 border border-blue-600'
                  : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100 border border-transparent'
              }`}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
