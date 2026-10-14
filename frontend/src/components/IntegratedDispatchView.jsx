import React, { useState, useEffect } from 'react';
import {
  Layers,
  Sparkles,
  Calendar,
  Clock,
  CloudRain,
  Truck,
  Navigation,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Info,
  Plus,
  Trash2,
  ArrowRight,
} from 'lucide-react';

/**
 * Common Montgomery County townships
 */
const COMMON_TOWNSHIPS = [
  'NORRISTOWN',
  'LOWER PROVIDENCE',
  'POTTSTOWN',
  'CHELTENHAM',
  'UPPER MERION',
  'ABINGTON',
  'LOWER MERION',
  'LANSDALE',
  'HORSHAM',
  'UPPER MORELAND',
  'EAST NORRITON',
  'SPRINGFIELD',
  'PLYMOUTH',
];

/**
 * Realistic default scenario representing a winter evening rush hour with precipitation
 */
const DEFAULT_WEATHER_SCENARIO = {
  hour: 17,
  month: 12,
  day_of_week: 4, // Friday
  is_weekend: 0,
  temperature_2m: 1.5,
  relative_humidity_2m: 88.0,
  precipitation: 2.2,
  wind_speed_10m: 24.0,
  weather_code: 61, // Rain / sleet
};

const DEFAULT_SECTORS = [
  { id: 'sec-1', twp: 'NORRISTOWN', current_ambulances: 1, ...DEFAULT_WEATHER_SCENARIO },
  { id: 'sec-2', twp: 'LOWER PROVIDENCE', current_ambulances: 0, ...DEFAULT_WEATHER_SCENARIO },
  { id: 'sec-3', twp: 'POTTSTOWN', current_ambulances: 2, ...DEFAULT_WEATHER_SCENARIO },
  { id: 'sec-4', twp: 'CHELTENHAM', current_ambulances: 1, ...DEFAULT_WEATHER_SCENARIO },
  { id: 'sec-5', twp: 'UPPER MERION', current_ambulances: 1, ...DEFAULT_WEATHER_SCENARIO },
];

export default function IntegratedDispatchView() {
  const [totalFleet, setTotalFleet] = useState(5);
  const [sectors, setSectors] = useState(DEFAULT_SECTORS);
  const [sharedWeather, setSharedWeather] = useState(DEFAULT_WEATHER_SCENARIO);

  // Route Planning Option
  const [includeRoute, setIncludeRoute] = useState(true);
  const [nodes, setNodes] = useState([]);
  const [startNode, setStartNode] = useState('NORRISTOWN_EMS');
  const [destNode, setDestNode] = useState('POTTSTOWN_HOSPITAL');

  // Execution states
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [planResult, setPlanResult] = useState(null);

  // Fetch road network nodes for route planning selector
  useEffect(() => {
    const fetchNodes = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/routes/nodes');
        if (res.ok) {
          const data = await res.json();
          setNodes(data);
        }
      } catch {
        // Non-critical: route selector can use fallback IDs
      }
    };
    fetchNodes();
  }, []);

  // Update a sector's field
  const handleSectorChange = (id, field, value) => {
    setSectors((prev) =>
      prev.map((s) => {
        if (s.id !== id) return s;
        let parsed = value;
        if (field === 'current_ambulances' || field === 'hour' || field === 'month' || field === 'day_of_week' || field === 'is_weekend' || field === 'weather_code') {
          parsed = Math.max(0, parseInt(value, 10) || 0);
        } else if (['temperature_2m', 'relative_humidity_2m', 'precipitation', 'wind_speed_10m'].includes(field)) {
          parsed = parseFloat(value) || 0;
        }
        return { ...s, [field]: parsed };
      })
    );
  };

  // Apply shared weather/time to all sectors
  const applySharedConditionsToAll = (newConditions) => {
    setSharedWeather(newConditions);
    setSectors((prev) =>
      prev.map((s) => ({
        ...s,
        ...newConditions,
      }))
    );
  };

  // Quick weather presets
  const handleWeatherPreset = (type) => {
    let preset;
    if (type === 'rain_surge') {
      preset = {
        hour: 17,
        month: 12,
        day_of_week: 4,
        is_weekend: 0,
        temperature_2m: 2.0,
        relative_humidity_2m: 90.0,
        precipitation: 3.5,
        wind_speed_10m: 28.0,
        weather_code: 61,
      };
    } else if (type === 'snow_storm') {
      preset = {
        hour: 8,
        month: 1,
        day_of_week: 1,
        is_weekend: 0,
        temperature_2m: -4.0,
        relative_humidity_2m: 85.0,
        precipitation: 2.0,
        wind_speed_10m: 32.0,
        weather_code: 71,
      };
    } else if (type === 'clear_baseline') {
      preset = {
        hour: 10,
        month: 5,
        day_of_week: 2,
        is_weekend: 0,
        temperature_2m: 20.0,
        relative_humidity_2m: 55.0,
        precipitation: 0.0,
        wind_speed_10m: 10.0,
        weather_code: 1,
      };
    }
    if (preset) {
      applySharedConditionsToAll(preset);
    }
  };

  // Add / remove sector
  const handleAddSector = () => {
    const newId = `sec-${Date.now()}`;
    const nextTwp = COMMON_TOWNSHIPS[sectors.length % COMMON_TOWNSHIPS.length] || 'NORRISTOWN';
    setSectors((prev) => [
      ...prev,
      { id: newId, twp: nextTwp, current_ambulances: 1, ...sharedWeather },
    ]);
  };

  const handleRemoveSector = (id) => {
    if (sectors.length <= 1) {
      alert('At least one sector is required for dispatch planning.');
      return;
    }
    setSectors((prev) => prev.filter((s) => s.id !== id));
  };

  const handleResetPresets = () => {
    setSectors(DEFAULT_SECTORS);
    setTotalFleet(5);
    setSharedWeather(DEFAULT_WEATHER_SCENARIO);
    setPlanResult(null);
    setError(null);
  };

  // Submit integrated dispatch plan
  const handleGeneratePlan = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setPlanResult(null);

    // Validation
    if (totalFleet < 0) {
      setError('Available fleet cannot be negative.');
      setLoading(false);
      return;
    }
    if (sectors.length === 0) {
      setError('At least one candidate sector is required.');
      setLoading(false);
      return;
    }

    const payload = {
      total_fleet_available: parseInt(totalFleet, 10),
      sectors: sectors.map((s) => ({
        twp: String(s.twp).trim().toUpperCase(),
        hour: parseInt(s.hour, 10),
        month: parseInt(s.month, 10),
        day_of_week: parseInt(s.day_of_week, 10),
        is_weekend: parseInt(s.is_weekend, 10),
        temperature_2m: parseFloat(s.temperature_2m),
        relative_humidity_2m: parseFloat(s.relative_humidity_2m),
        precipitation: parseFloat(s.precipitation),
        wind_speed_10m: parseFloat(s.wind_speed_10m),
        weather_code: parseInt(s.weather_code, 10),
        current_ambulances: parseInt(s.current_ambulances, 10),
      })),
      route_request: includeRoute
        ? {
            start_node: startNode,
            destination_node: destNode,
          }
        : null,
    };

    try {
      const response = await fetch('http://127.0.0.1:8000/dispatch/integrated-plan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || `HTTP ${response.status}: Failed to generate dispatch plan.`);
      }

      setPlanResult(data);
    } catch (err) {
      setError(err.message || 'Failed to connect to backend at http://127.0.0.1:8000.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="view-container integrated-dispatch-view">
      {/* Header */}
      <header className="view-header">
        <span className="view-badge">Complete Planning Tool</span>
        <h2 className="view-title">Emergency Response Planner</h2>
        <p className="view-description">
          Combines demand prediction, ambulance placement, and route finding into one complete planning workflow.
        </p>
      </header>

      {/* Honest Academic Disclosure Notice */}
      <div className="dashboard-notice-card" role="region" aria-label="Authenticity Notice">
        <div className="dashboard-notice-icon">
          <Info size={20} />
        </div>
        <div>
          <div className="dashboard-notice-title">
            Planning Prototype (Not Live Dispatch)
          </div>
          <div className="dashboard-notice-text">
            This planning tool combines call predictions based on past Montgomery County data, ambulance placement suggestions,
            and sample route finding. It is an academic demonstration and <strong>does not connect to live 911 dispatch or GPS tracking</strong>.
          </div>
        </div>
      </div>

      {/* Main Integrated Configuration Form */}
      <form onSubmit={handleGeneratePlan} className="integrated-form">
        {/* Operational Shift & Weather Context Card */}
        <div className="dispatch-context-card">
          <div className="card-header-row">
            <div>
              <h3 className="card-heading">
                <Clock size={18} style={{ color: 'var(--teal-primary)', verticalAlign: 'middle', marginRight: '0.4rem' }} />
                1. Time and Weather Conditions
              </h3>
              <p className="card-subheading">
                Choose the time of day and weather to test how conditions affect expected demand.
              </p>
            </div>
            <div className="context-preset-pills">
              <span className="presets-label">Scenarios:</span>
              <button
                type="button"
                onClick={() => handleWeatherPreset('rain_surge')}
                className="btn-preset alert"
              >
                Rainy Weather
              </button>
              <button
                type="button"
                onClick={() => handleWeatherPreset('snow_storm')}
                className="btn-preset"
              >
                Winter Freeze
              </button>
              <button
                type="button"
                onClick={() => handleWeatherPreset('clear_baseline')}
                className="btn-preset"
              >
                Clear Day
              </button>
            </div>
          </div>

          <div className="context-inputs-grid">
            <div className="context-field">
              <label className="field-label">Time of Day (Hour 0-23)</label>
              <input
                type="number"
                min="0"
                max="23"
                value={sharedWeather.hour}
                onChange={(e) =>
                  applySharedConditionsToAll({ ...sharedWeather, hour: parseInt(e.target.value, 10) || 0 })
                }
                className="form-input"
              />
            </div>

            <div className="context-field">
              <label className="field-label">Month (1-12)</label>
              <input
                type="number"
                min="1"
                max="12"
                value={sharedWeather.month}
                onChange={(e) =>
                  applySharedConditionsToAll({ ...sharedWeather, month: parseInt(e.target.value, 10) || 1 })
                }
                className="form-input"
              />
            </div>

            <div className="context-field">
              <label className="field-label">Day of Week</label>
              <select
                value={sharedWeather.day_of_week}
                onChange={(e) => {
                  const dow = parseInt(e.target.value, 10);
                  applySharedConditionsToAll({
                    ...sharedWeather,
                    day_of_week: dow,
                    is_weekend: dow >= 5 ? 1 : 0,
                  });
                }}
                className="form-select"
              >
                <option value={0}>Monday (Weekday)</option>
                <option value={1}>Tuesday (Weekday)</option>
                <option value={2}>Wednesday (Weekday)</option>
                <option value={3}>Thursday (Weekday)</option>
                <option value={4}>Friday (Weekday)</option>
                <option value={5}>Saturday (Weekend)</option>
                <option value={6}>Sunday (Weekend)</option>
              </select>
            </div>

            <div className="context-field">
              <label className="field-label">Air Temperature (°C)</label>
              <input
                type="number"
                step="0.5"
                value={sharedWeather.temperature_2m}
                onChange={(e) =>
                  applySharedConditionsToAll({ ...sharedWeather, temperature_2m: parseFloat(e.target.value) || 0 })
                }
                className="form-input"
              />
            </div>

            <div className="context-field">
              <label className="field-label">Air Moisture (%)</label>
              <input
                type="number"
                min="0"
                max="100"
                value={sharedWeather.relative_humidity_2m}
                onChange={(e) =>
                  applySharedConditionsToAll({
                    ...sharedWeather,
                    relative_humidity_2m: parseFloat(e.target.value) || 0,
                  })
                }
                className="form-input"
              />
            </div>

            <div className="context-field">
              <label className="field-label">Rain / Snow (mm)</label>
              <input
                type="number"
                min="0"
                step="0.1"
                value={sharedWeather.precipitation}
                onChange={(e) =>
                  applySharedConditionsToAll({ ...sharedWeather, precipitation: parseFloat(e.target.value) || 0 })
                }
                className="form-input"
              />
            </div>

            <div className="context-field">
              <label className="field-label">Wind Speed (km/h)</label>
              <input
                type="number"
                min="0"
                value={sharedWeather.wind_speed_10m}
                onChange={(e) =>
                  applySharedConditionsToAll({ ...sharedWeather, wind_speed_10m: parseFloat(e.target.value) || 0 })
                }
                className="form-input"
              />
            </div>

            <div className="context-field">
              <label className="field-label">Sky Condition</label>
              <select
                value={sharedWeather.weather_code}
                onChange={(e) =>
                  applySharedConditionsToAll({ ...sharedWeather, weather_code: parseInt(e.target.value, 10) || 0 })
                }
                className="form-select"
              >
                <option value={0}>Clear Sky</option>
                <option value={1}>Mainly Clear</option>
                <option value={2}>Partly Cloudy</option>
                <option value={3}>Overcast</option>
                <option value={51}>Light Drizzle</option>
                <option value={61}>Moderate Rain</option>
                <option value={65}>Heavy Rain</option>
                <option value={71}>Moderate Snow</option>
              </select>
            </div>
          </div>
        </div>

        {/* Candidate Sectors & Current Fleet Card */}
        <div className="dispatch-sectors-card">
          <div className="card-header-row">
            <div>
              <h3 className="card-heading">
                <Truck size={18} style={{ color: 'var(--teal-primary)', verticalAlign: 'middle', marginRight: '0.4rem' }} />
                2. Selected Areas & Current Ambulances
              </h3>
              <p className="card-subheading">
                Choose areas and set how many ambulances are already available in each one.
              </p>
            </div>
            <div className="sector-actions">
              <button type="button" onClick={handleAddSector} className="btn-secondary btn-sm">
                <Plus size={14} style={{ marginRight: '0.25rem' }} />
                Add Area
              </button>
              <button type="button" onClick={handleResetPresets} className="btn-secondary btn-sm">
                Reset Sample Areas
              </button>
            </div>
          </div>

          {/* Fleet Input */}
          <div className="integrated-fleet-bar">
            <div className="fleet-bar-item">
              <label htmlFor="int-fleet-input" className="fleet-bar-label">
                Extra Ambulances Available:
              </label>
              <input
                id="int-fleet-input"
                type="number"
                min="0"
                max="50"
                value={totalFleet}
                onChange={(e) => setTotalFleet(Math.max(0, parseInt(e.target.value, 10) || 0))}
                className="form-input fleet-input"
              />
              <span className="fleet-unit">Extra Ambulances</span>
            </div>
            <div className="fleet-bar-sub">
              Areas: <strong>{sectors.length}</strong> &bull; Total Current Ambulances:{' '}
              <strong>{sectors.reduce((acc, s) => acc + (s.current_ambulances || 0), 0)}</strong>
            </div>
          </div>

          {/* Sectors Table */}
          <div className="table-responsive">
            <table className="dispatch-sectors-table">
              <thead>
                <tr>
                  <th style={{ width: '40%' }}>Area Name</th>
                  <th style={{ width: '25%' }}>Ambulances Already Available</th>
                  <th style={{ width: '25%' }}>Conditions Applied</th>
                  <th style={{ width: '10%', textAlign: 'center' }}>Remove</th>
                </tr>
              </thead>
              <tbody>
                {sectors.map((sec, idx) => (
                  <tr key={sec.id}>
                    <td>
                      <select
                        value={sec.twp}
                        onChange={(e) => handleSectorChange(sec.id, 'twp', e.target.value)}
                        className="form-select table-input"
                      >
                        {COMMON_TOWNSHIPS.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        type="number"
                        min="0"
                        max="20"
                        value={sec.current_ambulances}
                        onChange={(e) => handleSectorChange(sec.id, 'current_ambulances', e.target.value)}
                        className="form-input table-input"
                      />
                    </td>
                    <td>
                      <span className="condition-tag">
                        Hour {String(sec.hour).padStart(2, '0')}:00 &bull; {sec.temperature_2m}°C &bull;{' '}
                        {sec.precipitation > 0 ? `${sec.precipitation}mm rain` : 'Dry'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <button
                        type="button"
                        onClick={() => handleRemoveSector(sec.id)}
                        className="btn-icon-danger"
                        disabled={sectors.length <= 1}
                        title="Remove area"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Optional Route Planning Section */}
        <div className="dispatch-route-card">
          <div className="route-toggle-header">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={includeRoute}
                onChange={(e) => setIncludeRoute(e.target.checked)}
              />
              <span className="checkbox-title">
                <Navigation size={17} style={{ color: 'var(--teal-primary)', verticalAlign: 'middle', marginRight: '0.4rem' }} />
                3. Include Route Finding (Sample Road Network)
              </span>
            </label>
            <span className="route-demo-badge">Sample Network</span>
          </div>

          {includeRoute && (
            <div className="route-picker-grid">
              <div className="form-group">
                <label className="form-label">Starting Location:</label>
                <select
                  value={startNode}
                  onChange={(e) => setStartNode(e.target.value)}
                  className="form-select"
                >
                  {nodes.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Hospital Destination:</label>
                <select
                  value={destNode}
                  onChange={(e) => setDestNode(e.target.value)}
                  className="form-select"
                >
                  {nodes.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Submit Button */}
        <div className="dispatch-submit-row">
          <button type="submit" disabled={loading} className="btn-primary generate-plan-btn">
            <Sparkles size={16} style={{ marginRight: '0.4rem' }} />
            {loading ? 'Generating Plan...' : 'Generate Dispatch Plan'}
          </button>
        </div>
      </form>

      {/* Error Banner */}
      {error && (
        <div className="error-banner" role="alert" style={{ marginTop: '1.5rem' }}>
          <div className="error-title">Could Not Generate Plan</div>
          <div>{error}</div>
        </div>
      )}

      {/* Integrated Results Display */}
      {planResult && !loading && (
        <div className="integrated-results-section" role="region" aria-label="Integrated Plan Output">
          {/* Summary Metric Cards */}
          <div className="allocation-summary-grid">
            <div className="metric-card">
              <span className="metric-label">Extra Ambulances Available</span>
              <span className="metric-value">{planResult.summary.total_fleet_available}</span>
              <span className="metric-sub">Ready to be assigned</span>
            </div>
            <div className="metric-card card-accent-teal">
              <span className="metric-label">Extra Ambulances Suggested</span>
              <span className="metric-value" style={{ color: 'var(--teal-primary)' }}>
                +{planResult.summary.total_allocated}
              </span>
              <span className="metric-sub">Assigned to areas</span>
            </div>
            <div className="metric-card card-accent-blue">
              <span className="metric-label">Ambulances Not Yet Assigned</span>
              <span className="metric-value" style={{ color: planResult.summary.unallocated_reserve > 0 ? 'var(--teal-primary)' : 'var(--text-muted)' }}>
                {planResult.summary.unallocated_reserve}
              </span>
              <span className="metric-sub">Kept in reserve</span>
            </div>
            <div className="metric-card card-accent-coral">
              <span className="metric-label">Areas With High Demand Expected</span>
              <span className="metric-value" style={{ color: planResult.summary.high_demand_sectors_count > 0 ? 'var(--coral-primary)' : 'var(--primary-navy)' }}>
                {planResult.summary.high_demand_sectors_count} / {planResult.summary.total_sectors_evaluated}
              </span>
              <span className="metric-sub">2 or more calls expected</span>
            </div>
          </div>

          {/* Decision Rationale Explanation Banner */}
          <div className="route-explanation-card">
            <div className="explanation-header">
              <CheckCircle2 size={18} style={{ color: 'var(--teal-primary)', marginRight: '0.4rem' }} />
              <strong>Summary of Decisions</strong>
            </div>
            <p className="explanation-text">{planResult.decision_explanation}</p>
            <div className="explanation-meta">
              <span><strong>Overall Status:</strong> {planResult.summary.system_status}</span> &bull;{' '}
              <span><strong>Estimated Coverage:</strong> {planResult.summary.system_coverage_rate}%</span>
            </div>
          </div>

          {/* Unified Sectors Table: Predictions + Allocations */}
          <div className="results-table-card">
            <div className="card-header-row">
              <h3 className="card-heading">Area Predictions & Ambulance Placement</h3>
              <span className="tag-algorithm">Predictive Dispatch Plan</span>
            </div>

            <div className="table-responsive">
              <table className="allocation-results-table">
                <thead>
                  <tr>
                    <th style={{ width: '5%', textAlign: 'center' }}>Priority</th>
                    <th style={{ width: '16%' }}>Area Name</th>
                    <th style={{ width: '16%' }}>Estimated Demand</th>
                    <th style={{ width: '13%' }}>Chance of High Demand</th>
                    <th style={{ width: '10%', textAlign: 'right' }}>Demand Level</th>
                    <th style={{ width: '9%', textAlign: 'right' }}>Already Available</th>
                    <th style={{ width: '11%', textAlign: 'center' }}>Extra Suggested</th>
                    <th style={{ width: '9%', textAlign: 'right' }}>New Total</th>
                    <th style={{ width: '11%' }}>Coverage Status</th>
                  </tr>
                </thead>
                <tbody>
                  {planResult.sectors.map((sec) => (
                    <tr key={sec.area_name}>
                      <td style={{ textAlign: 'center', fontWeight: 700, color: '#64748b' }}>
                        #{sec.priority_rank}
                      </td>
                      <td style={{ fontWeight: 800, color: 'var(--primary-navy)' }}>
                        {sec.area_name}
                      </td>
                      <td>
                        <span className={`pred-pill ${sec.predicted_class === 'HIGH' ? 'high' : 'normal'}`}>
                          {sec.predicted_class === 'HIGH' ? 'More Emergency Calls Expected' : 'Usual Calls Expected'}
                        </span>
                      </td>
                      <td>
                        <div className="prob-mini-cell">
                          <span className="prob-pct">{(sec.high_probability * 100).toFixed(1)}%</span>
                          <div className="mini-bar-track">
                            <div
                              className={`mini-bar-fill ${sec.predicted_class === 'HIGH' ? 'high' : 'normal'}`}
                              style={{ width: `${sec.high_probability * 100}%` }}
                            ></div>
                          </div>
                        </div>
                      </td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                        {sec.expected_demand_score.toFixed(1)}
                      </td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                        {sec.current_ambulances}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <span className={`add-pill ${sec.recommended_additional > 0 ? 'added' : 'zero'}`}>
                          {sec.recommended_additional > 0 ? `+${sec.recommended_additional}` : '0'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>
                        {sec.final_total_ambulances}
                      </td>
                      <td>
                        <span className="status-pill badge-neutral">
                          {sec.coverage_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Detailed Justifications Accordion / List */}
            <div className="reasons-breakdown-list">
              <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--primary-navy)', marginTop: '1.25rem', marginBottom: '0.75rem' }}>
                Why Each Placement Was Suggested:
              </h4>
              {planResult.sectors.map((sec) => (
                <div key={sec.area_name} className="reason-item-row">
                  <span className="reason-area-badge">#{sec.priority_rank} {sec.area_name}</span>
                  <span className="reason-text">{sec.reason}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Route Planning Result Card (if included) */}
          {planResult.route_result && (
            <div className="route-stepper-card">
              <div className="card-header-row">
                <div>
                  <h3 className="card-heading">Sample Transit Route</h3>
                  <p className="card-subheading">
                    {planResult.route_result.start_name} &rarr; {planResult.route_result.destination_name}
                  </p>
                </div>
                <span className="tag-algorithm">
                  {planResult.route_result.total_cost_km} km &bull; {planResult.route_result.visited_count} points checked
                </span>
              </div>

              {planResult.route_result.found ? (
                <>
                  <div className="path-breadcrumbs-wrap">
                    {planResult.route_result.path.map((nodeId, idx) => (
                      <React.Fragment key={nodeId}>
                        <div className="breadcrumb-node">
                          <div className="node-step-num">{idx + 1}</div>
                          <span className="node-step-name">{nodeId}</span>
                        </div>
                        {idx < planResult.route_result.path.length - 1 && (
                          <div className="breadcrumb-arrow">&rarr;</div>
                        )}
                      </React.Fragment>
                    ))}
                  </div>

                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '1rem' }}>
                    {planResult.route_result.explanation}
                  </p>
                </>
              ) : (
                <div className="error-banner">
                  {planResult.route_result.explanation}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
