import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import TopHeader from './components/TopHeader';
import DashboardView from './components/DashboardView';
import PredictionView from './components/PredictionView';
import HotspotsView from './components/HotspotsView';
import AllocationView from './components/AllocationView';
import RoutePlanningView from './components/RoutePlanningView';
import IntegratedDispatchView from './components/IntegratedDispatchView';
import ModelEvaluationView from './components/ModelEvaluationView';
import AboutView from './components/AboutView';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [backendStatus, setBackendStatus] = useState('checking'); // 'checking' | 'connected' | 'disconnected'
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const checkBackendHealth = useCallback(async () => {
    setBackendStatus('checking');
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);

      const res = await fetch('http://127.0.0.1:8000/health', {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        if (data.status === 'healthy' || data.status === 'ok' || data.model_loaded === true) {
          setBackendStatus('connected');
          return;
        }
      }
      setBackendStatus('disconnected');
    } catch {
      setBackendStatus('disconnected');
    }
  }, []);

  useEffect(() => {
    checkBackendHealth();
  }, [checkBackendHealth]);

  // Scroll to top of main content whenever tab changes
  useEffect(() => {
    const mainEl = document.querySelector('.main-content-scroll');
    if (mainEl) {
      mainEl.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [activeTab]);

  return (
    <div className="app-shell">
      {/* Left Fixed Vertical Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        backendStatus={backendStatus}
        checkBackendHealth={checkBackendHealth}
        isMobileOpen={isMobileOpen}
        setIsMobileOpen={setIsMobileOpen}
      />

      {/* Backdrop for mobile drawer */}
      {isMobileOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setIsMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Right Content Workspace */}
      <div className="main-wrapper">
        <TopHeader
          activeTab={activeTab}
          backendStatus={backendStatus}
          checkBackendHealth={checkBackendHealth}
          onToggleSidebar={() => setIsMobileOpen((prev) => !prev)}
        />

        <div className="main-content-scroll">
          <main className="main-content" key={activeTab}>
            <div className="page-enter-animation">
              {activeTab === 'dashboard' && (
                <DashboardView
                  onNavigateToPredict={() => setActiveTab('predict')}
                  onNavigatePredict={() => setActiveTab('predict')}
                  onNavigateToHotspots={() => setActiveTab('hotspots')}
                />
              )}
              {(activeTab === 'predict' || activeTab === 'prediction') && <PredictionView />}
              {activeTab === 'hotspots' && <HotspotsView />}
              {activeTab === 'allocation' && <AllocationView />}
              {(activeTab === 'routing' || activeTab === 'routes') && <RoutePlanningView />}
              {(activeTab === 'integrated' || activeTab === 'dispatch') && <IntegratedDispatchView />}
              {(activeTab === 'evaluation' || activeTab === 'models') && <ModelEvaluationView />}
              {activeTab === 'about' && <AboutView />}
            </div>
          </main>

          <footer className="app-footer">
            <div className="footer-content">
              <div className="footer-left">
                <span className="footer-badge">Academic ML Capstone</span>
                <p className="footer-text">
                  <strong>Emergency Response AI &bull; Ambulance Demand & Dispatch Decision Support</strong>
                </p>
                <p className="footer-sub">
                  Built on 332,436 historical 911 calls across Montgomery County, PA (December 2015 – July 2020).
                </p>
              </div>
              <div className="footer-right">
                <p className="footer-disclaimer">
                  Decision-support research demonstration only. Not a substitute for human 911 dispatch telecommunicators.
                </p>
              </div>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
