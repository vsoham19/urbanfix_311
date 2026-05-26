import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import Upload from './components/Upload';
import Review from './components/Review';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://urbanfix-311.onrender.com';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [structuredRecords, setStructuredRecords] = useState([]);
  const [quarantineRecords, setQuarantineRecords] = useState([]);
  const [flaggedRecords, setFlaggedRecords] = useState([]);
  const [reports, setReports] = useState([]);
  const [iotSewerReadings, setIotSewerReadings] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = async (showLoader = true) => {
    try {
      if (showLoader) setIsLoading(true);
      
      const [structuredRes, quarantineRes, flaggedRes, reportsRes, iotSewerRes] = await Promise.all([
            axios.get(`${API_BASE_URL}/records/structured`),
            axios.get(`${API_BASE_URL}/records/quarantine`),
            axios.get(`${API_BASE_URL}/records/flagged`),
            axios.get(`${API_BASE_URL}/records/reports`),
            axios.get(`${API_BASE_URL}/iot/sewer-readings`)
            ]);

      setStructuredRecords(structuredRes.data);
      setQuarantineRecords(quarantineRes.data);
      setFlaggedRecords(flaggedRes.data);
      setReports(reportsRes.data);
      setIotSewerReadings(iotSewerRes.data.readings || []);
      
    } catch (err) {
      console.error("Error loading data from API backend:", err);
    } finally {
      if (showLoader) setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(false), 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Top Navigation */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8 md:px-6">
        {isLoading && reports.length === 0 && iotSewerReadings.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[50vh] space-y-4">
            <div className="h-10 w-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-sm text-slate-500 font-medium">Initializing connection to UrbanFix 311 Core...</p>
          </div>
        ) : (
          <>
            {activeTab === 'dashboard' && (
              <Dashboard 
                structuredRecords={structuredRecords}
                quarantineRecords={quarantineRecords}
                flaggedRecords={flaggedRecords}
                reports={reports}
                iotSewerReadings={iotSewerReadings}
                fetchData={fetchData}
              />
            )}

            {activeTab === 'upload' && (
              <Upload onUploadSuccess={fetchData} />
            )}

            {activeTab === 'review' && (
              <Review 
                quarantineRecords={quarantineRecords}
                flaggedRecords={flaggedRecords}
                fetchData={fetchData}
              />
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500 font-semibold">
        &copy; {new Date().getFullYear()} Urbanfix IT Services LLP. All rights reserved.
      </footer>
    </div>
  );
}
