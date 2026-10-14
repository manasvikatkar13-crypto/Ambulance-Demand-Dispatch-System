import React from 'react';
import {
  LayoutDashboard,
  Sparkles,
  Flame,
  Truck,
  Compass,
  Layers,
  BarChart3,
  Info,
  ShieldAlert,
  RefreshCw,
  X,
  Activity,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';

/**
 * Sidebar Component
 * Fixed vertical left navigation with modern emergency response branding,
 * categorised navigation sections, animated active indicators, and system status card.
 */
export default function Sidebar({
  activeTab,
  setActiveTab,
  backendStatus,
  checkBackendHealth,
  isMobileOpen,
  setIsMobileOpen,
}) {
  const handleTabClick = (tabId) => {
    setActiveTab(tabId);
    if (setIsMobileOpen) {
      setIsMobileOpen(false);
    }
  };

  const navSections = [
    {
      group: 'INTELLIGENCE & DEMAND',
      items: [
        {
          id: 'dashboard',
          label: 'Overview',
          description: 'Historical call summary & peak trends',
          icon: LayoutDashboard,
          accent: 'teal',
        },
        {
          id: 'predict',
          label: 'Predict Emergency Calls',
          description: 'Random Forest surge likelihood',
          icon: Sparkles,
          accent: 'coral',
          alias: ['prediction'],
        },
        {
          id: 'hotspots',
          label: 'Past Call Hotspots',
          description: '1 km spatial call density map',
          icon: Flame,
          accent: 'amber',
        },
      ],
    },
    {
      group: 'DISPATCH & OPERATIONS',
      items: [
        {
          id: 'allocation',
          label: 'Ambulance Placement',
          description: 'Fleet placement advisory algorithm',
          icon: Truck,
          accent: 'teal',
        },
        {
          id: 'routing',
          label: 'Find a Route',
          description: 'A* shortest route finder',
          icon: Compass,
          accent: 'blue',
          alias: ['routes'],
        },
        {
          id: 'integrated',
          label: 'Response Planner',
          description: 'Full demand + fleet + route workflow',
          icon: Layers,
          accent: 'lavender',
          alias: ['dispatch'],
        },
      ],
    },
    {
      group: 'BENCHMARK & ABOUT',
      items: [
        {
          id: 'evaluation',
          label: 'Prediction Accuracy',
          description: '4-model benchmark & confusion matrix',
          icon: BarChart3,
          accent: 'teal',
          alias: ['models'],
        },
        {
          id: 'about',
          label: 'About This Project',
          description: 'Dataset info & human safety ethics',
          icon: Info,
          accent: 'slate',
        },
      ],
    },
  ];

  const isConnected = backendStatus === 'connected';
  const isChecking = backendStatus === 'checking';

  return (
    <aside className={`app-sidebar ${isMobileOpen ? 'mobile-open' : ''}`} aria-label="Main Navigation">
      {/* Sidebar Header / Branding */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-logo-bubble">
            <ShieldAlert size={22} className="sidebar-logo-icon" />
            <span className="sidebar-pulse-dot" />
          </div>
          <div className="sidebar-brand-text">
            <div className="sidebar-brand-name">
              Emergency Response AI
            </div>
            <div className="sidebar-brand-tagline">
              Ambulance Decision Support
            </div>
          </div>
        </div>

        {/* Mobile Close Button */}
        {isMobileOpen && (
          <button
            type="button"
            className="sidebar-mobile-close"
            onClick={() => setIsMobileOpen(false)}
            aria-label="Close navigation sidebar"
          >
            <X size={20} />
          </button>
        )}
      </div>

      {/* Montgomery County Badge Pill */}
      <div className="sidebar-location-pill">
        <span className="loc-dot"></span>
        <span className="loc-text">Montgomery County, PA</span>
        <span className="loc-badge">ML Demo</span>
      </div>

      {/* Vertical Navigation Links */}
      <nav className="sidebar-nav">
        {navSections.map((sec) => (
          <div key={sec.group} className="sidebar-nav-section">
            <div className="sidebar-section-label">{sec.group}</div>
            <ul className="sidebar-nav-list">
              {sec.items.map((item) => {
                const Icon = item.icon;
                const isActive =
                  activeTab === item.id ||
                  (item.alias && item.alias.includes(activeTab));

                return (
                  <li key={item.id} className="sidebar-nav-item">
                    <button
                      type="button"
                      className={`sidebar-nav-btn ${isActive ? 'active' : ''} accent-${item.accent}`}
                      onClick={() => handleTabClick(item.id)}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      {/* Active Indicator Bar on Left */}
                      <span className="sidebar-active-indicator" />

                      <div className={`nav-icon-box ${isActive ? 'active-icon' : ''}`}>
                        <Icon size={18} />
                      </div>

                      <div className="nav-label-box">
                        <span className="nav-item-title">{item.label}</span>
                        <span className="nav-item-desc">{item.description}</span>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Sidebar Footer: Real-Time System Status Card */}
      <div className="sidebar-footer">
        <div className={`sidebar-status-card ${isConnected ? 'online' : 'offline'}`}>
          <div className="status-card-header">
            <div className="status-left">
              <span className={`status-signal-dot ${isConnected ? 'online' : 'offline'}`} />
              <span className="status-state-text">
                {isChecking
                  ? 'Checking Server...'
                  : isConnected
                  ? 'Backend Online'
                  : 'Backend Offline'}
              </span>
            </div>
            <button
              type="button"
              className={`status-refresh-btn ${isChecking ? 'spinning' : ''}`}
              onClick={checkBackendHealth}
              title="Refresh connection status"
              aria-label="Refresh backend status"
            >
              <RefreshCw size={13} />
            </button>
          </div>

          <div className="status-card-details">
            <div className="status-meta-row">
              <span className="meta-label">Model Engine:</span>
              <span className="meta-val">Random Forest</span>
            </div>
            <div className="status-meta-row">
              <span className="meta-label">API Port:</span>
              <span className="meta-val">8000 (FastAPI)</span>
            </div>
          </div>
        </div>

        <div className="sidebar-academic-tag">
          Research Demonstration Only &bull; 911 Non-Dispatch
        </div>
      </div>
    </aside>
  );
}
