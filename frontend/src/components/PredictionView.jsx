import React, { useState } from 'react';
import {
  MapPin,
  Clock,
  Calendar,
  CalendarDays,
  Thermometer,
  Droplets,
  CloudRain,
  Wind,
  SunMedium,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  RotateCcw,
  Info,
  ShieldCheck,
} from 'lucide-react';

/**
 * PredictionView Component
 * Form interface for submitting zone and weather parameters to POST /predict.
 * Displays live model inference, class probabilities, and calibration caveats.
 */
export default function PredictionView() {
  // Pre-filled with valid sample example (Norristown weekday morning)
  const defaultFormData = {
    twp: 'NORRISTOWN',
    hour: 10,
    month: 5,
    day_of_week: 2,
    is_weekend: 0,
    temperature_2m: 18.5,
    relative_humidity_2m: 65,
    precipitation: 0,
    wind_speed_10m: 12,
    weather_code: 1,
  };

  const [formData, setFormData] = useState(defaultFormData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Top Montgomery County townships for convenient selection
  const commonTownships = [
    'NORRISTOWN',
    'LOWER MERION',
    'ABINGTON',
    'POTTSTOWN',
    'LOWER PROVIDENCE',
    'UPPER MERION',
    'CHELTENHAM',
    'UPPER MORELAND',
    'HORSHAM',
    'EAST NORRITON',
    'SPRINGFIELD',
    'PLYMOUTH',
    'UPPER DUBLIN',
    'MONTGOMERY',
    'WHITEMARSH',
    'LANSDALE',
    'UPPER PROVIDENCE',
    'WHITPAIN',
    'WEST NORRITON',
    'LIMERICK',
    'TOWAMENCIN',
    'AMBLER',
    'CONSHOHOCKEN',
  ];

  // Handle form input changes with type parsing
  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name === 'twp') {
      setFormData((prev) => ({ ...prev, twp: value }));
    } else if (['hour', 'month', 'day_of_week', 'is_weekend', 'weather_code'].includes(name)) {
      setFormData((prev) => ({
        ...prev,
        [name]: value === '' ? '' : parseInt(value, 10),
      }));
    } else {
      setFormData((prev) => ({
        ...prev,
        [name]: value === '' ? '' : parseFloat(value),
      }));
    }
  };

  // Reset form back to sample values
  const handleReset = () => {
    setFormData(defaultFormData);
    setError(null);
    setResult(null);
  };

  // Submit form payload to FastAPI backend
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    // Format payload with exact expected types for FastAPI Pydantic schema
    const payload = {
      twp: String(formData.twp).trim().toUpperCase(),
      hour: parseInt(formData.hour, 10),
      month: parseInt(formData.month, 10),
      day_of_week: parseInt(formData.day_of_week, 10),
      is_weekend: parseInt(formData.is_weekend, 10),
      temperature_2m: parseFloat(formData.temperature_2m),
      relative_humidity_2m: parseFloat(formData.relative_humidity_2m),
      precipitation: parseFloat(formData.precipitation),
      wind_speed_10m: parseFloat(formData.wind_speed_10m),
      weather_code: parseInt(formData.weather_code, 10),
    };

    try {
      // POST request to the local FastAPI backend service
      const response = await fetch('http://127.0.0.1:8000/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(
          errData?.detail || `API request failed with HTTP ${response.status} (${response.statusText})`
        );
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(
        'The prediction service is unavailable. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="prediction-view">
      <header className="view-header">
        <span className="view-badge">Call Demand Estimation</span>
        <h2 className="view-title">Predict Emergency Calls</h2>
        <p className="view-description">
          Estimate which areas may receive more emergency calls based on past records and the selected conditions.
        </p>
      </header>

      {/* Dataset & Location Notice */}
      <div className="dashboard-notice-card" role="region" aria-label="Prediction Scope Notice">
        <div className="dashboard-notice-icon">
          <ShieldCheck size={20} />
        </div>
        <div>
          <div className="dashboard-notice-title">Based on Historical Records from Montgomery County, PA, USA</div>
          <div className="dashboard-notice-text">
            Predictions are calculated using a machine learning model trained on past 911 calls and historical weather
            from Montgomery County, Pennsylvania, USA. This is an academic planning demonstration, not a live emergency system.
          </div>
        </div>
      </div>

      <div className="prediction-container">
        {/* Form Column */}
        <section className="form-card" aria-label="Prediction Form">
          <div className="form-card-header">
            <div>
              <h3 className="section-title">Select Area & Weather Conditions</h3>
              <p className="section-desc">
                Choose a township, time, and weather conditions to see expected emergency call demand.
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit} noValidate>
            {/* Card 1: Location & Township */}
            <div className="form-subcard">
              <div className="subcard-header">
                <MapPin size={17} className="subcard-icon teal" />
                <h4 className="subcard-title">1. Location & Area</h4>
              </div>
              <div className="form-group full-width">
                <label className="form-label" htmlFor="twp">
                  <span>Township / Area Name</span>
                  <span className="form-hint">Montgomery County, PA municipality</span>
                </label>
                <div className="input-with-icon">
                  <MapPin size={15} className="input-icon" />
                  <input
                    id="twp"
                    name="twp"
                    type="text"
                    list="township-list"
                    className="form-input with-left-icon"
                    value={formData.twp}
                    onChange={handleChange}
                    required
                    placeholder="e.g. NORRISTOWN"
                  />
                </div>
                <datalist id="township-list">
                  {commonTownships.map((t) => (
                    <option key={t} value={t} />
                  ))}
                </datalist>
              </div>
            </div>

            {/* Card 2: Date & Time Factors */}
            <div className="form-subcard">
              <div className="subcard-header">
                <Clock size={17} className="subcard-icon blue" />
                <h4 className="subcard-title">2. Time of Day & Calendar</h4>
              </div>
              <div className="form-grid">
                {/* Hour (0-23) */}
                <div className="form-group">
                  <label className="form-label" htmlFor="hour">
                    <span>Time of Day (Hour)</span>
                    <span className="form-hint">0 (midnight) to 23 (11 PM)</span>
                  </label>
                  <input
                    id="hour"
                    name="hour"
                    type="number"
                    min="0"
                    max="23"
                    className="form-input"
                    value={formData.hour}
                    onChange={handleChange}
                    required
                  />
                </div>

                {/* Month (1-12) */}
                <div className="form-group">
                  <label className="form-label" htmlFor="month">
                    <span>Month of Year</span>
                    <span className="form-hint">1 (Jan) to 12 (Dec)</span>
                  </label>
                  <input
                    id="month"
                    name="month"
                    type="number"
                    min="1"
                    max="12"
                    className="form-input"
                    value={formData.month}
                    onChange={handleChange}
                    required
                  />
                </div>

                {/* Day of Week (0-6) */}
                <div className="form-group">
                  <label className="form-label" htmlFor="day_of_week">
                    <span>Day of the Week</span>
                    <span className="form-hint">Monday to Sunday</span>
                  </label>
                  <select
                    id="day_of_week"
                    name="day_of_week"
                    className="form-select"
                    value={formData.day_of_week}
                    onChange={(e) => {
                      const dow = parseInt(e.target.value, 10);
                      setFormData((prev) => ({
                        ...prev,
                        day_of_week: dow,
                        is_weekend: dow === 5 || dow === 6 ? 1 : 0,
                      }));
                    }}
                    required
                  >
                    <option value={0}>Monday</option>
                    <option value={1}>Tuesday</option>
                    <option value={2}>Wednesday</option>
                    <option value={3}>Thursday</option>
                    <option value={4}>Friday</option>
                    <option value={5}>Saturday (Weekend)</option>
                    <option value={6}>Sunday (Weekend)</option>
                  </select>
                </div>

                {/* Is Weekend (0 or 1) */}
                <div className="form-group">
                  <label className="form-label" htmlFor="is_weekend">
                    <span>Day Type</span>
                    <span className="form-hint">Weekday or Weekend</span>
                  </label>
                  <select
                    id="is_weekend"
                    name="is_weekend"
                    className="form-select"
                    value={formData.is_weekend}
                    onChange={handleChange}
                    required
                  >
                    <option value={0}>Weekday (Monday – Friday)</option>
                    <option value={1}>Weekend (Saturday – Sunday)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Card 3: Meteorological & Weather Context */}
            <div className="form-subcard">
              <div className="subcard-header">
                <CloudRain size={17} className="subcard-icon lavender" />
                <h4 className="subcard-title">3. Weather Conditions</h4>
              </div>
              <div className="form-grid">
                {/* Temperature 2m (°C) */}
                <div className="form-group">
                  <label className="form-label" htmlFor="temperature_2m">
                    <span>Air Temperature</span>
                    <span className="form-hint">°C (e.g. 18.5°C)</span>
                  </label>
                  <input
                    id="temperature_2m"
                    name="temperature_2m"
                    type="number"
                    step="0.1"
                    className="form-input"
                    value={formData.temperature_2m}
                    onChange={handleChange}
                    required
                  />
                </div>

                {/* Relative Humidity 2m (%) */}
                <div className="form-group">
                  <label className="form-label" htmlFor="relative_humidity_2m">
                    <span>Air Moisture (Humidity)</span>
                    <span className="form-hint">% (0% to 100%)</span>
                  </label>
                  <input
                    id="relative_humidity_2m"
                    name="relative_humidity_2m"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    className="form-input"
                    value={formData.relative_humidity_2m}
                    onChange={handleChange}
                    required
                  />
                </div>

                {/* Precipitation (mm) */}
                <div className="form-group">
                  <label className="form-label" htmlFor="precipitation">
                    <span>Rain or Snow Amount</span>
                    <span className="form-hint">mm (0 for dry weather)</span>
                  </label>
                  <input
                    id="precipitation"
                    name="precipitation"
                    type="number"
                    step="0.1"
                    min="0"
                    className="form-input"
                    value={formData.precipitation}
                    onChange={handleChange}
                    required
                  />
                </div>

                {/* Wind Speed 10m (km/h) */}
                <div className="form-group">
                  <label className="form-label" htmlFor="wind_speed_10m">
                    <span>Wind Speed</span>
                    <span className="form-hint">km/h</span>
                  </label>
                  <input
                    id="wind_speed_10m"
                    name="wind_speed_10m"
                    type="number"
                    step="0.1"
                    min="0"
                    className="form-input"
                    value={formData.wind_speed_10m}
                    onChange={handleChange}
                    required
                  />
                </div>

                {/* Weather Code (WMO) */}
                <div className="form-group full-width">
                  <label className="form-label" htmlFor="weather_code">
                    <span>Sky & Weather Conditions</span>
                    <span className="form-hint">General weather outside</span>
                  </label>
                  <select
                    id="weather_code"
                    name="weather_code"
                    className="form-select"
                    value={formData.weather_code}
                    onChange={handleChange}
                    required
                  >
                    <option value={0}>Clear Sky (0)</option>
                    <option value={1}>Mainly Clear (1)</option>
                    <option value={2}>Partly Cloudy (2)</option>
                    <option value={3}>Overcast (3)</option>
                    <option value={45}>Fog (45)</option>
                    <option value={51}>Light Drizzle (51)</option>
                    <option value={61}>Light Rain (61)</option>
                    <option value={63}>Moderate Rain (63)</option>
                    <option value={65}>Heavy Rain (65)</option>
                    <option value={71}>Light Snow (71)</option>
                    <option value={75}>Heavy Snow (75)</option>
                    <option value={95}>Thunderstorm (95)</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="form-actions">
              <button type="submit" className="btn-primary btn-prominent" disabled={loading}>
                <Sparkles size={17} />
                <span>{loading ? 'Estimating Calls...' : 'Estimate Emergency Calls'}</span>
              </button>
              <button type="button" onClick={handleReset} className="btn-secondary" disabled={loading}>
                <RotateCcw size={15} />
                <span>Reset to Sample</span>
              </button>
            </div>
          </form>
        </section>

        {/* Results Column */}
        <section className="results-card" aria-label="Prediction Results">
          <div className="results-card-header">
            <h3 className="section-title">Estimated Demand</h3>
            {result && (
              <span className={`result-status-pill ${result.predicted_class === 'HIGH' ? 'surge' : 'normal'}`}>
                {result.predicted_class === 'HIGH' ? 'Elevated Call Alert' : 'Standard Baseline'}
              </span>
            )}
          </div>

          {error && (
            <div className="error-banner" role="alert">
              <div className="error-banner-header">
                <AlertTriangle size={18} className="error-icon" />
                <div className="error-title">Could Not Complete Estimation</div>
              </div>
              <p>{error}</p>
              <p style={{ marginTop: '0.4rem', fontSize: '0.75rem', color: '#64748b' }}>
                Please make sure the backend server is running and try again.
              </p>
            </div>
          )}

          {!result && !error && !loading && (
            <div className="empty-state">
              <div className="empty-icon-circle">
                <Sparkles size={28} />
              </div>
              <h4 className="empty-title">Ready to Estimate</h4>
              <p className="empty-desc">
                Select your scenario inputs on the left and click <strong>"Estimate Emergency Calls"</strong> to evaluate expected demand.
              </p>
            </div>
          )}

          {loading && (
            <div className="empty-state">
              <div className="spinner"></div>
              <h4 className="empty-title" style={{ marginTop: '1rem' }}>Calculating Estimated Demand...</h4>
              <p className="empty-desc">Analyzing historical patterns for this area and time</p>
            </div>
          )}

          {result && (
            <div className="result-content">
              {/* Surge Classification Banner */}
              <div className={`result-banner ${result.predicted_class}`}>
                <div className="result-banner-top">
                  <div className={`banner-icon-bubble ${result.predicted_class}`}>
                    {result.predicted_class === 'HIGH' ? (
                      <AlertTriangle size={20} />
                    ) : (
                      <CheckCircle2 size={20} />
                    )}
                  </div>
                  <div>
                    <span className="result-tag">Estimated Call Demand</span>
                    <div className="result-class-title">
                      {result.predicted_class === 'HIGH'
                        ? 'More Emergency Calls Expected'
                        : 'Usual Number of Emergency Calls Expected'}
                    </div>
                  </div>
                </div>
                <p className="result-subtitle">
                  {result.predicted_class === 'HIGH'
                    ? 'Higher number of emergency calls expected (2 or more calls during this hour).'
                    : 'Normal call volume expected (fewer than 2 calls during this hour).'}
                </p>
              </div>

              {/* Class Probability Distribution */}
              {result.probabilities && (
                <div className="prob-section">
                  <div className="prob-section-header">
                    <h4 className="prob-heading">Demand Likelihood</h4>
                    <span className="prob-sub-badge">Model Output</span>
                  </div>

                  {/* HIGH Probability */}
                  <div className="prob-row">
                    <div className="prob-header">
                      <span className="prob-label high">Chance of High Demand</span>
                      <span className="prob-percent high">{(result.probabilities.HIGH * 100).toFixed(1)}%</span>
                    </div>
                    <div className="prob-bar-bg">
                      <div
                        className="prob-bar-fill high"
                        style={{ width: `${result.probabilities.HIGH * 100}%` }}
                      ></div>
                    </div>
                  </div>

                  {/* NORMAL Probability */}
                  <div className="prob-row">
                    <div className="prob-header">
                      <span className="prob-label normal">Chance of Usual Demand</span>
                      <span className="prob-percent normal">{(result.probabilities.NORMAL * 100).toFixed(1)}%</span>
                    </div>
                    <div className="prob-bar-bg">
                      <div
                        className="prob-bar-fill normal"
                        style={{ width: `${result.probabilities.NORMAL * 100}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              )}

              {/* Echoed Input Context Chips */}
              <div className="situation-card">
                <span className="situation-title">Selected Situation:</span>
                <div className="situation-chips">
                  <span className="situation-chip">{result.input_features?.twp}</span>
                  <span className="situation-chip">{result.input_features?.hour}:00</span>
                  <span className="situation-chip">Month {result.input_features?.month}</span>
                  <span className="situation-chip">{result.input_features?.temperature_2m}&deg;C</span>
                </div>
              </div>

              {/* Probability Caveat Box (Mandatory Machine Learning Note) */}
              <div className="caveat-box">
                <Info size={16} className="caveat-icon" />
                <div>
                  <strong>How to use this information:</strong>{' '}
                  {result.probability_note ||
                    'These probabilities reflect patterns from past records. Use this as a helpful guide to prepare ambulance coverage, not as a replacement for live dispatch judgment.'}
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
