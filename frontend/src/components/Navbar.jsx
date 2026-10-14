import React, { useState, useEffect } from 'react';
import {
  Activity,
  LayoutDashboard,
  MapPin,
  Truck,
  Navigation,
  Layers,
  BarChart3,
  Info,
  RefreshCw,
  Menu,
  X,
  ShieldAlert,
} from 'lucide-react';

/**
 * Navbar Component
 * Displays polished emergency management system branding, responsive navigation, and live backend health indicator.
 */
export default function Navbar({ activeTab, setActiveTab }) {
  const [healthStatus, setHealthStatus] = useState({
    checked: false,
    online: false,
    loading: false,
    details: null,
  });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Poll backend health at http://127.0.0.1:8000/health
  const checkBackendHealth = async () => {
    setHealthStatus((prev) => ({ ...prev, loading: true }));
    try {
      const response = await fetch('http://127.0.0.1:8000/health');
      if (response.ok) {
        const data = await response.json();
        setHealthStatus({
          checked: true,
          online: data.status === 'healthy' || data.status === 'ok' || data.model_loaded === true,
          loading: false,
          details: data,
        });
      } else {
        setHealthStatus({
          checked: true,
          online: false,
          loading: false,
          details: null,
        });
      }
    } catch {
      setHealthStatus({
        checked: true,
        online: false,
        loading: false,
        details: null,
      });
    }
  };

  useEffect(() => {
    checkBackendHealth();
  }, []);

  const handleSelectTab = (tabId) => {
    setActiveTab(tabId);
    setMobileMenuOpen(false);
  };

  const navItems = [
    { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
    { id: 'predict', label: 'Predict Emergency Calls', icon: Activity },
    { id: 'hotspots', label: 'Areas With More Past Emergency Calls', icon: MapPin },
    { id: 'allocation', label: 'Ambulance Placement', icon: Truck },
    { id: 'routing', label: 'Find a Route', icon: Navigation },
    { id: 'integrated', label: 'Emergency Response Planner', icon: Layers },
    { id: 'evaluation', label: 'Prediction Accuracy', icon: BarChart3 },
    { id: 'about', label: 'About This Project', icon: Info },
  ];

  return (
    <header className="navbar">
      <div className="navbar-container">
        {/* Brand Section */}
        <div className="brand-section">
          <div className="brand-icon-wrapper" aria-hidden="true">
            <ShieldAlert className="brand-svg" size={20} />
            <span className="brand-pulse"></span>
          </div>
          <div className="brand-titles">
            <div className="brand-name-row">
              <span className="brand-name">Ambulance Demand & Dispatch AI</span>
              <span className="brand-badge">Decision Support</span>
            </div>
            <p className="brand-subtitle">Montgomery County, PA &bull; Historical EMS Analytics</p>
          </div>
        </div>

        {/* Right side controls: Health pill + Mobile toggle */}
        <div className="navbar-actions">
          {/* Live Backend Health Status */}
          <div
            className={`health-badge-container ${healthStatus.online ? 'is-online' : 'is-offline'}`}
            title="Backend Health Status"
          >
            <span
              className={`status-dot ${healthStatus.online ? 'online' : 'offline'}`}
            ></span>
            <span className="status-text">
              {healthStatus.loading
                ? 'Checking...'
                : healthStatus.online
                ? 'System Online'
                : 'System Offline'}
            </span>
            <button
              onClick={checkBackendHealth}
              className={`health-refresh-btn ${healthStatus.loading ? 'spinning' : ''}`}
              title="Refresh connection status"
              aria-label="Refresh connection status"
            >
              <RefreshCw size={13} />
            </button>
          </div>

          {/* Mobile Menu Toggle Button */}
          <button
            className="mobile-menu-toggle"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            aria-label={mobileMenuOpen ? 'Close Navigation Menu' : 'Open Navigation Menu'}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Tab Navigation Menu (Desktop bar + Mobile dropdown) */}
      <nav className={`navbar-nav ${mobileMenuOpen ? 'mobile-open' : ''}`} aria-label="Main Navigation">
        <div className="nav-scroll-container">
          <ul className="nav-links">
            {navItems.map((item) => {
              const IconComponent = item.icon;
              const isActive =
                activeTab === item.id ||
                (item.id === 'predict' && activeTab === 'prediction') ||
                (item.id === 'routing' && activeTab === 'routes') ||
                (item.id === 'integrated' && activeTab === 'dispatch') ||
                (item.id === 'evaluation' && activeTab === 'models');

              return (
                <li key={item.id} className="nav-item">
                  <button
                    className={`nav-btn ${isActive ? 'active' : ''}`}
                    onClick={() => handleSelectTab(item.id)}
                  >
                    <IconComponent size={16} className="nav-btn-icon" />
                    <span>{item.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </nav>
    </header>
  );
}
