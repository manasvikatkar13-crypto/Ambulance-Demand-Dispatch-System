import React from 'react';
import {
  Menu,
  Activity,
  LayoutDashboard,
  Sparkles,
  Flame,
  Truck,
  Compass,
  Layers,
  BarChart3,
  Info,
  Clock,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';

/**
 * TopHeader Component
 * Modern header bar above the main content area, displaying current section,
 * system status pill, quick context, and mobile menu toggle.
 */
export default function TopHeader({
  activeTab,
  backendStatus,
  checkBackendHealth,
  onToggleSidebar,
}) {
  const getTabInfo = (tab) => {
    switch (tab) {
      case 'dashboard':
        return {
          title: 'System Overview & Historical Trends',
          badge: 'Historical Analytics',
          icon: LayoutDashboard,
        };
      case 'predict':
      case 'prediction':
        return {
          title: 'Predict Emergency Calls (Surge Likelihood)',
          badge: 'Machine Learning Model',
          icon: Sparkles,
        };
      case 'hotspots':
        return {
          title: 'Areas With More Past Emergency Calls (Hotspot Map)',
          badge: 'Spatial Intelligence',
          icon: Flame,
        };
      case 'allocation':
        return {
          title: 'Ambulance Placement Recommendations',
          badge: 'Fleet Advisory',
          icon: Truck,
        };
      case 'routing':
      case 'routes':
        return {
          title: 'Find a Route (A* Pathfinding)',
          badge: 'Road Network',
          icon: Compass,
        };
      case 'integrated':
      case 'dispatch':
        return {
          title: 'Emergency Response Planner (Integrated Workflow)',
          badge: 'End-to-End Planning',
          icon: Layers,
        };
      case 'evaluation':
      case 'models':
        return {
          title: 'Prediction Accuracy (Model Evaluation)',
          badge: 'Retrospective Benchmark',
          icon: BarChart3,
        };
      case 'about':
        return {
          title: 'About This Project & Ethics',
          badge: 'Documentation',
          icon: Info,
        };
      default:
        return {
          title: 'Emergency Response AI',
          badge: 'Decision Support',
          icon: Activity,
        };
    }
  };

  const info = getTabInfo(activeTab);
  const Icon = info.icon;
  const isOnline = backendStatus === 'connected';

  return (
    <header className="top-header">
      <div className="top-header-left">
        {/* Mobile Sidebar Hamburger Toggle */}
        <button
          type="button"
          className="top-header-menu-btn"
          onClick={onToggleSidebar}
          aria-label="Toggle navigation menu"
        >
          <Menu size={20} />
        </button>

        {/* Current View Breadcrumb / Title */}
        <div className="top-header-title-box">
          <div className="top-header-badge">
            <Icon size={13} style={{ marginRight: '0.35rem' }} />
            <span>{info.badge}</span>
          </div>
          <h1 className="top-header-title">{info.title}</h1>
        </div>
      </div>

      <div className="top-header-right">
        {/* Montgomery County Scope Tag */}
        <div className="top-header-chip county-chip">
          <span className="chip-dot"></span>
          <span>Montgomery County, PA</span>
        </div>

        {/* Live System Health Pill */}
        <div
          className={`top-header-health-pill ${isOnline ? 'online' : 'offline'}`}
          title={isOnline ? 'FastAPI & Random Forest Loaded' : 'Backend Disconnected'}
        >
          <span className={`health-pulse-dot ${isOnline ? 'online' : 'offline'}`}></span>
          <span className="health-label">
            {backendStatus === 'checking'
              ? 'Checking...'
              : isOnline
              ? 'ML Engine Online'
              : 'Backend Offline'}
          </span>
          <button
            type="button"
            className="top-health-refresh"
            onClick={checkBackendHealth}
            title="Refresh connection"
            aria-label="Refresh connection"
          >
            <RefreshCw size={12} />
          </button>
        </div>
      </div>
    </header>
  );
}
