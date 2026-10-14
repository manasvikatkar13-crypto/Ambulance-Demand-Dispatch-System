import React, { useState, useEffect, useCallback } from 'react';
import {
  PhoneCall,
  MapPin,
  Calendar,
  Clock,
  Flame,
  ShieldCheck,
  ArrowRight,
  Filter,
  Layers,
  Sparkles,
  TrendingUp,
} from 'lucide-react';

/**
 * DashboardView Component
 * Renders executive analytics using real historical EMS data fetched from FastAPI:
 * - GET /dashboard/summary
 * - GET /dashboard/hourly-pattern
 * - GET /dashboard/top-zones
 */
export default function DashboardView({ onNavigateToPredict, onNavigatePredict, onNavigateToHotspots }) {
  const handleNavigate = onNavigateToPredict || onNavigatePredict;

  const [summary, setSummary] = useState(null);
  const [hourlyPattern, setHourlyPattern] = useState(null);
  const [topZones, setTopZones] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch all dashboard datasets concurrently from FastAPI backend
  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);

    try {
      const [sumRes, hourRes, topRes] = await Promise.all([
        fetch('http://127.0.0.1:8000/dashboard/summary', { signal: controller.signal }),
        fetch('http://127.0.0.1:8000/dashboard/hourly-pattern', { signal: controller.signal }),
        fetch('http://127.0.0.1:8000/dashboard/top-zones', { signal: controller.signal }),
      ]);

      clearTimeout(timeoutId);

      if (!sumRes.ok || !hourRes.ok || !topRes.ok) {
        throw new Error(
          `Failed to retrieve analytics from API (HTTP ${sumRes.status}/${hourRes.status}/${topRes.status}).`
        );
      }

      const [sumData, hourData, topData] = await Promise.all([
        sumRes.json(),
        hourRes.json(),
        topRes.json(),
      ]);

      setSummary(sumData);
      setHourlyPattern(hourData);
      setTopZones(topData);
    } catch (err) {
      setError(
        err.name === 'AbortError'
          ? 'Dashboard request timed out. Please verify that the FastAPI backend is running.'
          : err.message || 'Failed to connect to http://127.0.0.1:8000.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  // Calculate maximum hourly demand to scale bar heights
  const maxHourlyDemand = hourlyPattern?.hourly_pattern?.length
    ? Math.max(...hourlyPattern.hourly_pattern.map((p) => p.demand))
    : 1;

  // Calculate maximum township calls to scale zone progress bars
  const maxZoneCalls = topZones?.top_zones?.length
    ? Math.max(...topZones.top_zones.map((z) => z.call_count))
    : 1;

  return (
    <div className="dashboard-view">
      <header className="view-header">
        <span className="view-badge">System Overview</span>
        <h2 className="view-title">Overview: Past Emergency Call Patterns</h2>
        <p className="view-description">
          Review historical patterns of 911 emergency medical calls across Montgomery County, Pennsylvania, USA.
          These past records help emergency planning teams understand when and where calls have been most frequent.
        </p>
      </header>

      {/* Historical Dataset Notice */}
      <div className="dashboard-notice-card" role="region" aria-label="Dataset Scope Notice">
        <div className="dashboard-notice-icon">
          <ShieldCheck size={20} />
        </div>
        <div>
          <div className="dashboard-notice-title">Historical Records from Montgomery County, Pennsylvania, USA (2015–2020)</div>
          <div className="dashboard-notice-text">
            All statistics, busy hours, and area rankings below are based on past 911 emergency medical calls recorded
            between <strong>December 10, 2015 and July 29, 2020</strong> in Montgomery County, Pennsylvania, USA.
            This is historical research data to help study demand patterns, not live emergency dispatches.
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="dashboard-loading-state">
          <div className="spinner"></div>
          <p style={{ fontWeight: 600, color: '#1e293b' }}>Loading past records from the system...</p>
          <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.25rem' }}>
            Fetching call summary, hourly distribution, and top areas...
          </p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="dashboard-error-state">
          <div style={{ color: '#dc2626', fontWeight: 700, fontSize: '1rem', marginBottom: '0.5rem' }}>
            Information Currently Unavailable
          </div>
          <p style={{ fontSize: '0.875rem', color: '#475569', marginBottom: '1rem' }}>
            We could not load the overview data right now. Please check that the backend service is running and try again.
          </p>
          <button onClick={fetchDashboardData} className="btn-primary" style={{ display: 'inline-flex', padding: '0.6rem 1.5rem' }}>
            Try Again
          </button>
        </div>
      )}

      {/* Four Summary Cards Powered by Real Backend Analytics */}
      {!loading && !error && summary && (
        <section className="cards-grid" aria-label="Dataset Summary Metrics">
          {/* Card 1: Total Calls */}
          <div className="summary-card card-accent-teal">
            <div className="summary-card-top">
              <span className="card-label">Total Past Emergency Calls</span>
              <div className="card-icon-bubble teal">
                <PhoneCall size={18} />
              </div>
            </div>
            <div className="card-value">{summary.total_calls.toLocaleString()}</div>
            <p className="card-subtext">Total medical calls in dataset</p>
            <span className="card-badge-static teal">Verified 911 Records</span>
          </div>

          {/* Card 2: Monitored Townships */}
          <div className="summary-card card-accent-blue">
            <div className="summary-card-top">
              <span className="card-label">Townships & Areas Covered</span>
              <div className="card-icon-bubble blue">
                <MapPin size={18} />
              </div>
            </div>
            <div className="card-value">{summary.total_townships}</div>
            <p className="card-subtext">Municipalities across county</p>
            <span className="card-badge-static blue">Montgomery County, PA</span>
          </div>

          {/* Card 3: Date Coverage Range */}
          <div className="summary-card card-accent-lavender">
            <div className="summary-card-top">
              <span className="card-label">Years of Past Records</span>
              <div className="card-icon-bubble lavender">
                <Calendar size={18} />
              </div>
            </div>
            <div className="card-value date-range-val">
              Dec 2015 – Jul 2020
            </div>
            <p className="card-subtext">{summary.start_date} to {summary.end_date}</p>
            <span className="card-badge-static lavender">4.5 Years of Records</span>
          </div>

          {/* Card 4: Peak Demand Hour */}
          <div className="summary-card card-accent-coral">
            <div className="summary-card-top">
              <span className="card-label">Busiest Time of Day</span>
              <div className="card-icon-bubble coral">
                <Clock size={18} />
              </div>
            </div>
            <div className="card-value coral-val">{summary.busiest_hour_label || `${summary.busiest_hour}:00`}</div>
            <p className="card-subtext">
              {summary.busiest_hour_calls.toLocaleString()} calls during this peak hour
            </p>
            <span className="card-badge-static coral">
              Highest Call Volume
            </span>
          </div>
        </section>
      )}

      {/* Visual Analytics Grid: 24-Hour Distribution & Top 5 Townships */}
      {!loading && !error && hourlyPattern && topZones && (
        <section className="dashboard-charts-grid" aria-label="Visual Analytics">
          {/* Chart 1: 24-Hour Cumulative Demand Distribution */}
          <div className="analytics-card">
            <div className="analytics-card-header">
              <div>
                <h3 className="analytics-card-title">24-Hour Past Emergency Call Pattern</h3>
                <p className="analytics-card-subtitle">
                  Total calls during each hour of the day (from midnight 00:00 through 11:00 PM 23:00)
                </p>
              </div>
              <span className="chart-badge highlight">
                Busiest Hour: {summary?.busiest_hour_label} ({summary?.busiest_hour_calls.toLocaleString()} calls)
              </span>
            </div>

            <div className="hourly-chart-container">
              <div className="bars-viewport" role="img" aria-label="Hourly Demand Bar Chart">
                {hourlyPattern.hourly_pattern.map((point) => {
                  const heightPercent = maxHourlyDemand > 0 ? (point.demand / maxHourlyDemand) * 100 : 0;
                  const isPeak = summary ? point.hour === summary.busiest_hour : false;

                  return (
                    <div
                      key={point.hour}
                      className={`bar-column ${isPeak ? 'is-peak' : ''}`}
                      title={`${point.label}: ${point.demand.toLocaleString()} calls`}
                    >
                      <div
                        className="bar-rect"
                        style={{ height: `${Math.max(heightPercent, 4)}%` }}
                      ></div>
                      <div className="bar-tooltip">
                        <strong>{point.label}</strong>: {point.demand.toLocaleString()} calls
                        {isPeak && ' (Busiest Hour)'}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* X-Axis Hour Labels */}
              <div className="hours-axis">
                <span>00:00 (Midnight)</span>
                <span>04:00</span>
                <span>08:00</span>
                <span>12:00 (Noon)</span>
                <span>16:00</span>
                <span>20:00</span>
                <span>23:00</span>
              </div>

              {/* Chart Legend */}
              <div className="chart-legend">
                <div className="legend-item">
                  <span className="legend-dot normal"></span>
                  <span>Hourly Call Volume</span>
                </div>
                <div className="legend-item">
                  <span className="legend-dot peak"></span>
                  <span>Busiest Hour (10:00 AM)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Chart 2: Top 5 Busiest Townships Ranked */}
          <div className="analytics-card">
            <div className="analytics-card-header">
              <div>
                <h3 className="analytics-card-title">Top 5 Areas With the Most Past Calls</h3>
                <p className="analytics-card-subtitle">
                  Townships that had the highest number of emergency medical calls in past records
                </p>
              </div>
              <span className="chart-badge">Busiest Areas</span>
            </div>

            <div className="top-zones-list">
              {topZones.top_zones.map((zone, idx) => {
                const fillWidth = maxZoneCalls > 0 ? (zone.call_count / maxZoneCalls) * 100 : 0;
                const totalCountyCalls = summary?.total_calls || 332436;
                const percentageOfTotal = ((zone.call_count / totalCountyCalls) * 100).toFixed(1);

                return (
                  <div key={zone.twp} className="zone-rank-item">
                    <div className="zone-rank-header">
                      <div className="zone-title-group">
                        <span className={`rank-badge ${idx === 0 ? 'rank-1' : idx === 1 ? 'rank-2' : ''}`}>
                          #{zone.rank}
                        </span>
                        <span className="zone-name">{zone.twp}</span>
                      </div>
                      <div className="zone-metrics">
                        <span className="zone-call-count">{zone.call_count.toLocaleString()} calls</span>
                        <span className="zone-percentage">({percentageOfTotal}%)</span>
                      </div>
                    </div>

                    <div className="zone-progress-bg">
                      <div
                        className={`zone-progress-fill ${idx === 0 ? 'top-rank' : ''}`}
                        style={{ width: `${fillWidth}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div style={{ marginTop: '1.25rem', fontSize: '0.75rem', color: '#64748b' }}>
              These top 5 areas accounted for more than 29% of all past emergency medical calls in Montgomery County.
            </div>
          </div>
        </section>
      )}

      {/* Decision-Support Workflow */}
      <section className="workflow-section">
        <h3 className="section-title">How the System Works</h3>
        <p className="section-desc">
          How past records turn into helpful planning suggestions for emergency dispatch teams:
        </p>

        <div className="workflow-steps">
          <div className="workflow-step">
            <div className="workflow-step-header">
              <span className="step-num">Step 1</span>
              <div className="workflow-step-icon teal">
                <Filter size={15} />
              </div>
            </div>
            <h4 className="step-title">Cleaning Past Records</h4>
            <p className="step-text">
              Filtered raw 911 calls strictly to emergency medical incidents, removing incomplete or erroneous entries.
            </p>
          </div>

          <div className="workflow-step">
            <div className="workflow-step-header">
              <span className="step-num">Step 2</span>
              <div className="workflow-step-icon blue">
                <Layers size={15} />
              </div>
            </div>
            <h4 className="step-title">Organizing by Area and Time</h4>
            <p className="step-text">
              Grouped calls by township and hour to see call volume across different times of day and days of the week.
            </p>
          </div>

          <div className="workflow-step">
            <div className="workflow-step-header">
              <span className="step-num">Step 3</span>
              <div className="workflow-step-icon lavender">
                <Calendar size={15} />
              </div>
            </div>
            <h4 className="step-title">Connecting Weather Data</h4>
            <p className="step-text">
              Added historical temperature, humidity, rain, snow, and wind data to study how weather impacts calls.
            </p>
          </div>

          <div className="workflow-step">
            <div className="workflow-step-header">
              <span className="step-num">Step 4</span>
              <div className="workflow-step-icon coral">
                <Sparkles size={15} />
              </div>
            </div>
            <h4 className="step-title">Estimating High-Demand Hours</h4>
            <p className="step-text">
              Trains a model to learn when an area is likely to have 2 or more calls in an hour, suggesting extra ambulance placement.
            </p>
          </div>
        </div>

        <div className="notice-box">
          <div className="notice-box-header">
            <ShieldCheck size={18} className="notice-box-icon" />
            <h4 className="notice-title">Important Note on Safety</h4>
          </div>
          <p className="notice-desc">
            This dashboard provides research-based planning suggestions based on past records. It is a decision-support
            prototype, not a replacement for professional 911 dispatch telecommunicators.
          </p>
        </div>
      </section>

      {/* Quick Calls to Action */}
      <div className="dashboard-cta-row">
        <button
          onClick={handleNavigate}
          className="btn-primary btn-cta"
        >
          <span>Predict Emergency Calls</span>
          <ArrowRight size={16} />
        </button>
        {onNavigateToHotspots && (
          <button
            onClick={onNavigateToHotspots}
            className="btn-secondary btn-cta"
          >
            <span>See Areas With More Past Calls</span>
            <MapPin size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
