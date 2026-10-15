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
import LoginView from './components/LoginView';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [backendStatus, setBackendStatus] = useState('checking'); // 'checking' | 'connected' | 'disconnected'
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  // ---------------- Authentication State ---------------- //
  const [authToken, setAuthToken] = useState(() => {
    return localStorage.getItem('ems_auth_token') || null;
  });

  const [currentUser, setCurrentUser] = useState(() => {
    const saved = localStorage.getItem('ems_auth_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });

  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return Boolean(localStorage.getItem('ems_auth_token'));
  });

  // Verify stored session on initial mount
  useEffect(() => {
    const verifyStoredSession = async () => {
      const token = localStorage.getItem('ems_auth_token');
      if (!token) {
        setIsAuthenticated(false);
        setCurrentUser(null);
        return;
      }

      try {
        const res = await fetch('http://127.0.0.1:8000/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.ok) {
          const data = await res.json();
          if (data.valid && data.user) {
            setCurrentUser(data.user);
            setIsAuthenticated(true);
            return;
          }
        }

        // Token invalid or expired
        handleLogout();
      } catch {
        // If network error, retain local state so dispatcher isn't abruptly locked out during temporary offline
      }
    };

    verifyStoredSession();
  }, []);

  const handleLoginSuccess = (userData, token) => {
    localStorage.setItem('ems_auth_token', token);
    localStorage.setItem('ems_auth_user', JSON.stringify(userData));
    setAuthToken(token);
    setCurrentUser(userData);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('ems_auth_token');
    localStorage.removeItem('ems_auth_user');
    setAuthToken(null);
    setCurrentUser(null);
    setIsAuthenticated(false);
    setActiveTab('dashboard');
  };

  // ---------------- Backend Health Check ---------------- //
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

  // ---------------- Protected View Routing ---------------- //
  if (!isAuthenticated) {
    return (
      <LoginView
        onLoginSuccess={handleLoginSuccess}
        backendStatus={backendStatus}
      />
    );
  }

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
        currentUser={currentUser}
        onLogout={handleLogout}
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
          currentUser={currentUser}
          onLogout={handleLogout}
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
