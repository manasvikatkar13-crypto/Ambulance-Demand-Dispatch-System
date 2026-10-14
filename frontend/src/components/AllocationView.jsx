import React, { useState } from 'react';
import {
  Truck,
  Plus,
  Trash2,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Info,
  Sparkles,
  ShieldCheck,
} from 'lucide-react';

/**
 * Default sample areas representing high-volume Montgomery County townships
 * used for realistic decision-support scenario simulations.
 */
const DEFAULT_PRESET_AREAS = [
  { id: 'area-1', area_name: 'NORRISTOWN', predicted_demand: 3.5, current_ambulances: 1 },
  { id: 'area-2', area_name: 'LOWER PROVIDENCE', predicted_demand: 2.8, current_ambulances: 0 },
  { id: 'area-3', area_name: 'POTTSTOWN', predicted_demand: 2.2, current_ambulances: 2 },
  { id: 'area-4', area_name: 'CHELTENHAM', predicted_demand: 1.8, current_ambulances: 1 },
  { id: 'area-5', area_name: 'UPPER MERION', predicted_demand: 1.5, current_ambulances: 1 },
  { id: 'area-6', area_name: 'ABINGTON', predicted_demand: 1.2, current_ambulances: 1 },
];

export default function AllocationView() {
  const [totalFleet, setTotalFleet] = useState(5);
  const [areas, setAreas] = useState(DEFAULT_PRESET_AREAS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Area row change handlers
  const handleAreaChange = (id, field, value) => {
    setAreas((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item;
        let parsed = value;
        if (field === 'predicted_demand') {
          parsed = Math.max(0, parseFloat(value) || 0);
        } else if (field === 'current_ambulances') {
          parsed = Math.max(0, parseInt(value, 10) || 0);
        }
        return { ...item, [field]: parsed };
      })
    );
  };

  const handleAddArea = () => {
    const newId = `area-${Date.now()}`;
    setAreas((prev) => [
      ...prev,
      { id: newId, area_name: `SECTOR ${prev.length + 1}`, predicted_demand: 1.0, current_ambulances: 0 },
    ]);
  };

  const handleRemoveArea = (id) => {
    if (areas.length <= 1) {
      alert('At least one area is required for allocation simulation.');
      return;
    }
    setAreas((prev) => prev.filter((item) => item.id !== id));
  };

  const handleResetPresets = () => {
    setAreas(DEFAULT_PRESET_AREAS);
    setTotalFleet(5);
    setResult(null);
    setError(null);
  };

  const handleClearAll = () => {
    setAreas([
      { id: `area-${Date.now()}`, area_name: 'ZONE A', predicted_demand: 2.0, current_ambulances: 0 },
    ]);
    setResult(null);
    setError(null);
  };

  // Submit allocation simulation to FastAPI backend
  const handleGenerateRecommendations = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    // Client-side validation
    if (totalFleet < 0) {
      setError('Total available ambulance fleet cannot be negative.');
      setLoading(false);
      return;
    }

    if (areas.length === 0) {
      setError('Please provide at least one area to evaluate.');
      setLoading(false);
      return;
    }

    for (const a of areas) {
      if (!a.area_name.trim()) {
        setError('All area names must be non-empty.');
        setLoading(false);
        return;
      }
    }

    const payload = {
      total_fleet_available: parseInt(totalFleet, 10),
      areas: areas.map((a) => ({
        area_name: a.area_name.trim().toUpperCase(),
        predicted_demand: parseFloat(a.predicted_demand),
        current_ambulances: parseInt(a.current_ambulances, 10),
      })),
    };

    try {
      const response = await fetch('http://127.0.0.1:8000/allocation/recommendations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `Server responded with HTTP ${response.status}: ${response.statusText}`
        );
      }

      const json = await response.json();
      setResult(json);
    } catch (err) {
      setError(
        err.message || 'Failed to connect to FastAPI backend at http://127.0.0.1:8000. Please verify the API is running.'
      );
    } finally {
      setLoading(false);
    }
  };

  // Helper for status badge styling
  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'Deficit Covered':
        return 'badge-success';
      case 'Partial Deficit':
        return 'badge-warning';
      case 'Unmet Deficit':
        return 'badge-danger';
      case 'Surge Buffer':
        return 'badge-info';
      case 'Adequate Coverage':
      case 'Zero Demand':
      default:
        return 'badge-neutral';
    }
  };

  return (
    <div className="view-container allocation-view">
      {/* Header */}
      <header className="view-header">
        <span className="view-badge">Planning Tool</span>
        <h2 className="view-title">Ambulance Placement</h2>
        <p className="view-description">
          Suggestions are based on estimated demand and the ambulance numbers you enter.
          See where placing extra ambulances may help the most.
        </p>
      </header>

      {/* Academic Disclaimer Card */}
      <div className="dashboard-notice-card" role="region" aria-label="Research Disclaimer">
        <div className="dashboard-notice-icon">
          <Info size={20} />
        </div>
        <div>
          <div className="dashboard-notice-title">
            Planning Suggestion Only
          </div>
          <div className="dashboard-notice-text">
            Suggestions are based on estimated demand and the ambulance numbers you enter.
            This is an academic planning aid to explore hypothetical scenarios and <strong>does not connect to live 911 dispatch systems</strong>.
          </div>
        </div>
      </div>

      {/* Main Form & Scenario Setup */}
      <form onSubmit={handleGenerateRecommendations} className="allocation-form">
        {/* Top Controls: Fleet Size & Preset Actions */}
        <div className="allocation-fleet-card">
          <div className="fleet-input-group">
            <label htmlFor="total-fleet-input" className="fleet-label">
              <Truck size={18} style={{ color: 'var(--teal-primary)', verticalAlign: 'middle', marginRight: '0.4rem' }} />
              Extra Ambulances Available
              <span className="fleet-hint">(Total extra ambulances ready to be positioned)</span>
            </label>
            <div className="fleet-input-wrap">
              <input
                id="total-fleet-input"
                type="number"
                min="0"
                max="100"
                step="1"
                value={totalFleet}
                onChange={(e) => setTotalFleet(Math.max(0, parseInt(e.target.value, 10) || 0))}
                className="form-input fleet-input"
                required
              />
              <span className="fleet-unit">Extra Ambulances</span>
            </div>
          </div>

          <div className="preset-actions">
            <button
              type="button"
              onClick={handleResetPresets}
              className="btn-secondary btn-sm"
              title="Reset to sample scenario"
            >
              <RotateCcw size={14} style={{ marginRight: '0.3rem' }} />
              Load Sample Areas
            </button>
            <button
              type="button"
              onClick={handleClearAll}
              className="btn-secondary btn-sm"
              title="Clear list and start with a single area"
            >
              Clear List
            </button>
          </div>
        </div>

        {/* Sector Demand & Existing Coverage Table */}
        <div className="allocation-sectors-card">
          <div className="sectors-header">
            <div>
              <h3 className="card-heading">Areas & Current Ambulances</h3>
              <p className="card-subheading">
                Enter the expected demand and how many ambulances are already available in each area.
              </p>
            </div>
            <button
              type="button"
              onClick={handleAddArea}
              className="btn-secondary btn-sm"
            >
              <Plus size={14} style={{ marginRight: '0.25rem' }} />
              Add Area
            </button>
          </div>

          <div className="table-responsive">
            <table className="allocation-input-table">
              <thead>
                <tr>
                  <th style={{ width: '35%' }}>Area Name</th>
                  <th style={{ width: '25%' }}>Estimated Demand Level</th>
                  <th style={{ width: '25%' }}>Ambulances Already Available</th>
                  <th style={{ width: '15%', textAlign: 'center' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {areas.map((area, index) => {
                  const initialDeficit = Math.max(0, area.predicted_demand - area.current_ambulances);
                  return (
                    <tr key={area.id}>
                      <td>
                        <input
                          type="text"
                          value={area.area_name}
                          onChange={(e) => handleAreaChange(area.id, 'area_name', e.target.value)}
                          placeholder="e.g. NORRISTOWN"
                          className="form-input table-input"
                          required
                        />
                      </td>
                      <td>
                        <div className="input-with-sub">
                          <input
                            type="number"
                            min="0"
                            max="50"
                            step="0.1"
                            value={area.predicted_demand}
                            onChange={(e) => handleAreaChange(area.id, 'predicted_demand', e.target.value)}
                            className="form-input table-input"
                            required
                          />
                          <span className="deficit-preview">
                            {initialDeficit > 0 ? (
                              <span style={{ color: '#dc2626' }}>Need: {initialDeficit.toFixed(1)} more</span>
                            ) : (
                              <span style={{ color: '#16a34a' }}>Enough ambulances</span>
                            )}
                          </span>
                        </div>
                      </td>
                      <td>
                        <input
                          type="number"
                          min="0"
                          max="30"
                          step="1"
                          value={area.current_ambulances}
                          onChange={(e) => handleAreaChange(area.id, 'current_ambulances', e.target.value)}
                          className="form-input table-input"
                          required
                        />
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <button
                          type="button"
                          onClick={() => handleRemoveArea(area.id)}
                          className="btn-icon-danger"
                          title="Remove area"
                          disabled={areas.length <= 1}
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="sectors-footer">
            <div className="sectors-summary-text">
              Total Areas: <strong>{areas.length}</strong> &bull; Total Estimated Demand:{' '}
              <strong>{areas.reduce((acc, a) => acc + (parseFloat(a.predicted_demand) || 0), 0).toFixed(1)}</strong> &bull;{' '}
              Ambulances Already Available:{' '}
              <strong>{areas.reduce((acc, a) => acc + (parseInt(a.current_ambulances, 10) || 0), 0)}</strong>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary generate-btn"
            >
              <Sparkles size={16} style={{ marginRight: '0.4rem' }} />
              {loading ? 'Calculating Placement...' : 'Suggest Ambulance Placement'}
            </button>
          </div>
        </div>
      </form>

      {/* Error Banner */}
      {error && (
        <div className="error-banner" role="alert" style={{ marginTop: '1.5rem' }}>
          <div className="error-title">Could Not Calculate Placement</div>
          <div>{error}</div>
        </div>
      )}

      {/* Recommendation Results Section */}
      {result && !loading && (
        <div className="allocation-results-section" role="region" aria-label="Allocation Recommendations">
          {/* Summary Metric Cards */}
          <div className="allocation-summary-grid">
            <div className="metric-card">
              <span className="metric-label">Extra Ambulances Available</span>
              <span className="metric-value">{result.summary.total_fleet_available}</span>
              <span className="metric-sub">Ready to be assigned</span>
            </div>
            <div className="metric-card card-accent-teal">
              <span className="metric-label">Extra Ambulances Suggested</span>
              <span className="metric-value" style={{ color: 'var(--teal-primary)' }}>
                +{result.summary.total_allocated}
              </span>
              <span className="metric-sub">Assigned to areas</span>
            </div>
            <div className="metric-card card-accent-blue">
              <span className="metric-label">Ambulances Not Yet Assigned</span>
              <span className="metric-value" style={{ color: result.summary.unallocated_reserve > 0 ? 'var(--teal-primary)' : 'var(--text-muted)' }}>
                {result.summary.unallocated_reserve}
              </span>
              <span className="metric-sub">Kept in reserve</span>
            </div>
            <div className="metric-card card-accent-lavender">
              <span className="metric-label">Areas With Enough Coverage</span>
              <span className="metric-value">
                {result.summary.areas_fully_covered} / {result.summary.total_areas_evaluated}
              </span>
              <span className="metric-sub">Areas with demand met</span>
            </div>
          </div>

          {/* System Status Banner */}
          <div className="allocation-status-banner">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <ShieldCheck size={22} style={{ color: 'var(--teal-primary)' }} />
              <div>
                <div className="status-banner-title">
                  <strong>Overall Placement Status:</strong> {result.summary.overall_system_status}
                </div>
                <div className="status-banner-sub">
                  Estimated Coverage: <strong>{result.summary.system_coverage_rate}%</strong> across all evaluated areas.
                </div>
              </div>
            </div>
          </div>

          {/* Results Table */}
          <div className="results-table-card">
            <div className="card-header-row">
              <h3 className="card-heading">Suggested Ambulance Placement by Area</h3>
              <span className="tag-algorithm">Step-by-step priority method</span>
            </div>

            <div className="table-responsive">
              <table className="allocation-results-table">
                <thead>
                  <tr>
                    <th style={{ width: '6%', textAlign: 'center' }}>Priority</th>
                    <th style={{ width: '18%' }}>Area Name</th>
                    <th style={{ width: '12%', textAlign: 'right' }}>Estimated Demand</th>
                    <th style={{ width: '12%', textAlign: 'right' }}>Ambulances Already Available</th>
                    <th style={{ width: '14%', textAlign: 'center' }}>Extra Ambulances Suggested</th>
                    <th style={{ width: '12%', textAlign: 'right' }}>New Total</th>
                    <th style={{ width: '14%' }}>Coverage Status</th>
                    <th style={{ width: '24%' }}>Why This Was Suggested</th>
                  </tr>
                </thead>
                <tbody>
                  {result.recommendations.map((rec) => (
                    <tr key={rec.area_name}>
                      <td style={{ textAlign: 'center', fontWeight: 700, color: '#64748b' }}>
                        #{rec.priority_rank}
                      </td>
                      <td style={{ fontWeight: 700, color: 'var(--primary-navy)' }}>
                        {rec.area_name}
                      </td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                        {rec.predicted_demand.toFixed(1)}
                      </td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                        {rec.current_ambulances}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <span className={`add-pill ${rec.recommended_additional > 0 ? 'added' : 'zero'}`}>
                          {rec.recommended_additional > 0 ? `+${rec.recommended_additional}` : '0'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>
                        {rec.final_total_ambulances}
                      </td>
                      <td>
                        <span className={`status-pill ${getStatusBadgeClass(rec.coverage_status)}`}>
                          {rec.coverage_status}
                        </span>
                      </td>
                      <td className="reason-cell">
                        {rec.reason}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Visual Coverage Bar per Area */}
            <div className="visual-breakdown-section">
              <h4 className="breakdown-title">Visual Comparison: Current vs. Suggested Ambulances</h4>
              <div className="breakdown-list">
                {result.recommendations.map((rec) => {
                  const maxUnits = Math.max(5, ...result.recommendations.map((r) => r.final_total_ambulances));
                  const existingPct = (rec.current_ambulances / maxUnits) * 100;
                  const addedPct = (rec.recommended_additional / maxUnits) * 100;

                  return (
                    <div key={rec.area_name} className="breakdown-row">
                      <div className="breakdown-label">
                        <span className="b-area">{rec.area_name}</span>
                        <span className="b-demand">Demand: {rec.predicted_demand.toFixed(1)}</span>
                      </div>
                      <div className="breakdown-bar-track">
                        <div
                          className="bar-segment existing"
                          style={{ width: `${existingPct}%` }}
                          title={`Already Available: ${rec.current_ambulances}`}
                        >
                          {rec.current_ambulances > 0 && `${rec.current_ambulances}`}
                        </div>
                        <div
                          className="bar-segment recommended"
                          style={{ width: `${addedPct}%` }}
                          title={`Suggested Extra: +${rec.recommended_additional}`}
                        >
                          {rec.recommended_additional > 0 && `+${rec.recommended_additional}`}
                        </div>
                      </div>
                      <div className="breakdown-total">
                        <strong>{rec.final_total_ambulances}</strong> total
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="breakdown-legend">
                <span className="legend-item">
                  <span className="swatch existing"></span> Ambulances Already Available
                </span>
                <span className="legend-item">
                  <span className="swatch recommended"></span> Extra Ambulances Suggested
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
