import React from 'react';
import { Target, Database, BarChart3, ShieldCheck, CheckCircle2 } from 'lucide-react';

export default function AboutView() {
  return (
    <div className="view-container">
      <div className="view-header">
        <span className="view-badge">Project Background</span>
        <h2 className="view-title">About This Project</h2>
        <p className="view-subtitle">
          An academic machine learning project demonstrating decision support for emergency ambulance planning.
        </p>
      </div>

      <div className="about-grid">
        <div className="card about-card card-accent-teal">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Target size={18} style={{ color: 'var(--teal-primary)' }} />
              <span className="card-title">What This Project Does</span>
            </div>
            <span className="badge badge-normal">Goal</span>
          </div>
          <p className="about-p">
            Emergency medical service calls rise and fall throughout the day and week, influenced by time, season, and weather. In suburban areas, ambulances are often moved only after calls start piling up.
          </p>
          <p className="about-p">
            This project explores whether computer models trained on past data can help predict unusually busy hours (defined as <strong>2 or more emergency calls in an area during a single hour</strong>). This can help ambulance planners position extra ambulances ahead of time.
          </p>
        </div>

        <div className="card about-card card-accent-blue">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Database size={18} style={{ color: 'var(--soft-blue-text)' }} />
              <span className="card-title">The Dataset</span>
            </div>
            <span className="badge badge-normal">Past Records</span>
          </div>
          <ul className="about-list">
            <li>
              <strong>Real Historical Records:</strong> 332,436 emergency 911 calls from Montgomery County, Pennsylvania, USA between December 2015 and July 2020.
            </li>
            <li>
              <strong>Hourly Analysis:</strong> Call records organized by hour across 69 townships and boroughs, including quiet hours with zero calls.
            </li>
            <li>
              <strong>Weather Records:</strong> Historical weather data for the county (temperature, air moisture, rain/snow, wind speed, and conditions).
            </li>
            <li>
              <strong>Most Hours Are Quiet:</strong> Normal hours (fewer than 2 calls) make up 98.5% of all recorded hours, while busy surge hours make up only 1.5%.
            </li>
          </ul>
        </div>

        <div className="card about-card card-accent-lavender">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <BarChart3 size={18} style={{ color: 'var(--light-lavender-text)' }} />
              <span className="card-title">Comparing Models</span>
            </div>
            <span className="badge badge-normal">Testing</span>
          </div>
          <div className="table-container">
            <table className="eval-table">
              <thead>
                <tr>
                  <th>Model Type</th>
                  <th>How It Works</th>
                  <th>Key Finding</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Simple Baseline</strong></td>
                  <td>Predicts normal call numbers every hour</td>
                  <td>Scores high overall accuracy because most hours are quiet, but misses 100% of busy emergency surges.</td>
                </tr>
                <tr>
                  <td><strong>KNN Model</strong></td>
                  <td>Finds similar past hours</td>
                  <td>Catches many busy hours, but sounds too many false alarms (over 2,000 false alarms on 5,000 test hours).</td>
                </tr>
                <tr>
                  <td><strong>Random Forest Model</strong> (Selected)</td>
                  <td>Combines multiple decision trees</td>
                  <td>Provides the best real-world balance: catches 64% of busy hours while cutting false alarms by nearly 78%.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className="card about-card card-accent-coral">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldCheck size={18} style={{ color: 'var(--coral-primary)' }} />
              <span className="card-title">Human-First Design</span>
            </div>
            <span className="badge badge-surge">Safety</span>
          </div>
          <p className="about-p">
            This system is strictly an <strong>advisory decision aid</strong>, not an automated 911 dispatcher. Computer models estimate chances of busy demand, but trained human dispatchers and supervisors always make the final decisions.
          </p>
          <div className="philosophy-box">
            <div className="philosophy-item">
              <span className="phi-title">1. Clear Likelihood</span>
              <p>Users receive straightforward percentages rather than confusing technical jargon.</p>
            </div>
            <div className="philosophy-item">
              <span className="phi-title">2. Human Judgment First</span>
              <p>Real-world knowledge (like road closures, storms, or local events) always takes precedence over computer estimates.</p>
            </div>
            <div className="philosophy-item">
              <span className="phi-title">3. Safe Operation</span>
              <p>Emergency dispatching operates safely regardless of whether the software is active.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
