import React, { useState } from 'react';
import {
  ShieldAlert,
  Lock,
  User,
  Eye,
  EyeOff,
  Loader2,
  AlertCircle,
  Radio,
  BadgeCheck,
  CheckCircle2,
  PhoneCall,
  Activity,
  ArrowRight,
} from 'lucide-react';
import './LoginView.css';

const API_BASE = 'http://127.0.0.1:8000';

export default function LoginView({ onLoginSuccess, backendStatus = 'connected' }) {
  const [username, setUsername] = useState('dispatcher_admin');
  const [password, setPassword] = useState('emergency2026!');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setErrorMessage(null);

    if (!username.trim() || !password.trim()) {
      setErrorMessage('Please enter both your Dispatcher ID and password.');
      return;
    }

    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username.trim(),
          password: password.trim(),
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Authentication failed. Please verify credentials.');
      }

      // Successful login
      if (onLoginSuccess) {
        onLoginSuccess(data.user, data.access_token);
      }
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setErrorMessage(
          'Cannot connect to FastAPI backend at port 8000. Please ensure `python run.py` is actively running.'
        );
      } else {
        setErrorMessage(err.message || 'An unexpected error occurred during login.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const fillCredentials = (user, pass) => {
    setUsername(user);
    setPassword(pass);
    setErrorMessage(null);
  };

  return (
    <div className="login-viewport">
      {/* Background Ambient Ambient Glows */}
      <div className="login-ambient-glow glow-top" />
      <div className="login-ambient-glow glow-bottom" />

      <div className="login-container">
        {/* Top Header Card */}
        <div className="login-card-shell">
          {/* Official Agency Banner */}
          <div className="login-card-header">
            <div className="agency-badge-pill">
              <span className="agency-pulsing-dot" />
              <Radio size={12} className="text-teal-400" />
              <span>MONTGOMERY COUNTY 911 CAD NETWORK</span>
            </div>

            <div className="login-brand-row">
              <div className="login-icon-box">
                <ShieldAlert size={28} className="text-teal-400" />
              </div>
              <div>
                <h1 className="login-main-title">Emergency Dispatch AI</h1>
                <p className="login-sub-title">Computer-Aided Dispatch & Demand Forecasting System</p>
              </div>
            </div>

            <div className="login-system-status">
              <span className={`status-indicator-dot ${backendStatus === 'connected' ? 'online' : 'offline'}`} />
              <span className="status-indicator-text">
                {backendStatus === 'connected' ? 'FastAPI Dispatch Service Online' : 'Service Offline (Port 8000)'}
              </span>
            </div>
          </div>

          {/* Form Area */}
          <div className="login-form-body">
            {errorMessage && (
              <div className="login-error-alert" role="alert">
                <AlertCircle size={18} className="error-icon" />
                <div className="error-text-content">
                  <strong>Access Denied:</strong> {errorMessage}
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="login-form">
              {/* Username Field */}
              <div className="form-group">
                <label htmlFor="username-input" className="form-label">
                  Dispatcher ID / Username
                </label>
                <div className="input-affix-wrapper">
                  <span className="input-icon-prefix">
                    <User size={16} />
                  </span>
                  <input
                    id="username-input"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. dispatcher_admin"
                    autoComplete="username"
                    disabled={isLoading}
                    className="login-input"
                    required
                  />
                </div>
              </div>

              {/* Password Field */}
              <div className="form-group">
                <div className="form-label-row">
                  <label htmlFor="password-input" className="form-label">
                    Security Password
                  </label>
                  <span className="label-caption">256-bit Encrypted</span>
                </div>
                <div className="input-affix-wrapper">
                  <span className="input-icon-prefix">
                    <Lock size={16} />
                  </span>
                  <input
                    id="password-input"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter security password"
                    autoComplete="current-password"
                    disabled={isLoading}
                    className="login-input with-suffix"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="input-icon-suffix-btn"
                    title={showPassword ? 'Hide password' : 'Show password'}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                className={`login-submit-btn ${isLoading ? 'loading' : ''}`}
              >
                {isLoading ? (
                  <>
                    <Loader2 size={18} className="spin-animation" />
                    <span>Authenticating CAD Session...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In to Dispatch Operations</span>
                    <ArrowRight size={18} className="btn-arrow-icon" />
                  </>
                )}
              </button>
            </form>

            {/* Quick Demo Credentials Box for Reviewers/Examiners */}
            <div className="demo-credentials-box">
              <div className="demo-credentials-title">
                <BadgeCheck size={14} className="text-teal-400" />
                <span>One-Click Demo Credentials (Evaluation Ready)</span>
              </div>
              <div className="demo-buttons-grid">
                <button
                  type="button"
                  onClick={() => fillCredentials('dispatcher_admin', 'emergency2026!')}
                  className={`demo-pill-btn ${username === 'dispatcher_admin' ? 'active-pill' : ''}`}
                >
                  <span className="pill-role">Supervisor Admin</span>
                  <span className="pill-creds">dispatcher_admin / emergency2026!</span>
                </button>

                <button
                  type="button"
                  onClick={() => fillCredentials('paramedic_user', 'medic123')}
                  className={`demo-pill-btn ${username === 'paramedic_user' ? 'active-pill' : ''}`}
                >
                  <span className="pill-role">Field Paramedic</span>
                  <span className="pill-creds">paramedic_user / medic123</span>
                </button>
              </div>
            </div>

            {/* Disclaimer Footer */}
            <div className="login-disclaimer-card">
              <p className="disclaimer-text">
                <strong>AUTHORIZED ACCESS ONLY:</strong> This system is reserved for official Montgomery County
                emergency medical operations and academic capstone demonstration. All dispatch transactions and triage
                evaluations are logged for audit compliance.
              </p>
            </div>
          </div>
        </div>

        {/* Outer Minimal Footer */}
        <div className="login-outer-footer">
          <span>Montgomery County Department of Public Safety &bull; CAD Emergency Intelligence</span>
        </div>
      </div>
    </div>
  );
}
