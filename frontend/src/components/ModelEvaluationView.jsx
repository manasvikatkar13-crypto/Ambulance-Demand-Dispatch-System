import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  Award,
  TrendingUp,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Info,
  Scale,
  Target,
  Sparkles,
} from 'lucide-react';

/**
 * Model Evaluation View (Step 17)
 * Displays retrospective empirical evaluation metrics, multi-model comparison,
 * interactive confusion matrices, precision-recall trade-offs, and educational context.
 */
export default function ModelEvaluationView() {
  const [evaluationData, setEvaluationData] = useState(null);
  const [selectedModelId, setSelectedModelId] = useState('random_forest');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [chartMetric, setChartMetric] = useState('f1_score'); // 'f1_score' | 'recall' | 'precision' | 'balanced_acc' | 'all'

  // Fetch evaluation data from backend
  useEffect(() => {
    const fetchEvaluation = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch('http://127.0.0.1:8000/evaluation/models');
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: Failed to load model evaluation data.`);
        }
        const data = await res.json();
        setEvaluationData(data);
        if (data.selected_model_id) {
          setSelectedModelId(data.selected_model_id);
        }
      } catch (err) {
        setError(err.message || 'Could not connect to backend evaluation service.');
      } finally {
        setLoading(false);
      }
    };
    fetchEvaluation();
  }, []);

  if (loading) {
    return (
      <div className="view-container">
        <div className="loading-state" style={{ padding: '3rem 0', textAlign: 'center' }}>
          <div className="loading-spinner"></div>
          <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>
            Loading empirical model evaluation benchmark...
          </p>
        </div>
      </div>
    );
  }

  if (error || !evaluationData) {
    return (
      <div className="view-container">
        <div className="error-banner" role="alert" style={{ marginTop: '2rem' }}>
          <div className="error-title">Evaluation Data Unavailable</div>
          <div>{error || 'Unable to load evaluation benchmark.'}</div>
          <button
            onClick={() => window.location.reload()}
            className="btn-secondary btn-sm"
            style={{ marginTop: '1rem' }}
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  const { models, metadata, guidance } = evaluationData;
  const activeModel = models.find((m) => m.model_id === selectedModelId) || models[0];

  return (
    <div className="view-container model-evaluation-view">
      {/* Header */}
      <header className="view-header">
        <span className="view-badge">Model Testing</span>
        <h2 className="view-title">Prediction Accuracy</h2>
        <p className="view-description">
          Comparing 4 computer models on past Montgomery County test records to see how accurately they spot high emergency demand.
        </p>
      </header>

      {/* Experimental Protocol & Dataset Split Notice */}
      <div className="dashboard-notice-card" role="region" aria-label="Experimental Protocol">
        <div className="dashboard-notice-icon">
          <Info size={20} />
        </div>
        <div>
          <div className="dashboard-notice-title">
            How the Models Were Tested
          </div>
          <div className="dashboard-notice-text">
            All 4 models were tested on the <strong>exact same test dataset</strong>{' '}
            (<strong>{metadata.test_sample_size.toLocaleString()} past hours</strong> from{' '}
            <strong>{metadata.test_start_date}</strong> onward, containing{' '}
            <strong>{metadata.test_high_count} actual high-demand periods ({metadata.test_high_prevalence_pct}%)</strong>).
            Each model was trained only on earlier records ({metadata.train_cutoff_date}) to test real-world prediction accuracy.
          </div>
        </div>
      </div>

      {/* Selected Candidate Spotlight Card */}
      <div className="candidate-spotlight-card">
        <div className="spotlight-header">
          <div>
            <span className="candidate-tag">
              <Award size={14} style={{ marginRight: '0.3rem' }} />
              Best Overall Model
            </span>
            <h3 className="spotlight-title">Random Forest</h3>
            <p className="spotlight-sub">
              Chosen because it caught most busy periods while keeping false alarms much lower than other models.
            </p>
          </div>
          <div className="spotlight-badge-f1">
            <span className="f1-label">Overall Balance Score</span>
            <span className="f1-val">16.01%</span>
            <span className="f1-sub">Highest among all 4 models</span>
          </div>
        </div>

        <div className="spotlight-metrics-grid">
          <div className="spotlight-metric">
            <span className="s-label">Overall Accuracy</span>
            <span className="s-val">90.14%</span>
            <span className="s-sub">4,507 of 5,000 correct</span>
          </div>
          <div className="spotlight-metric">
            <span className="s-label">Balanced Score</span>
            <span className="s-val">77.45%</span>
            <span className="s-sub">Fair across quiet & busy hours</span>
          </div>
          <div className="spotlight-metric">
            <span className="s-label">Busy Hours Caught</span>
            <span className="s-val" style={{ color: '#16a34a' }}>64.38%</span>
            <span className="s-sub">47 of 73 busy periods caught</span>
          </div>
          <div className="spotlight-metric">
            <span className="s-label">Precision on Busy Hours</span>
            <span className="s-val" style={{ color: 'var(--accent-blue)' }}>9.14%</span>
            <span className="s-sub">47 correct out of 514 alerts</span>
          </div>
          <div className="spotlight-metric">
            <span className="s-label">Fewer False Alarms</span>
            <span className="s-val" style={{ color: '#15803d' }}>-77.9%</span>
            <span className="s-sub">467 false alarms vs 2,119 in KNN</span>
          </div>
        </div>
      </div>

      {/* Architecture Comparison Table */}
      <div className="results-table-card" style={{ marginTop: '1.75rem' }}>
        <div className="card-header-row">
          <div>
            <h3 className="card-heading">1. Comparing the 4 Models</h3>
            <p className="card-subheading">
              Click any model row to see its detailed results and error breakdown below.
            </p>
          </div>
          <span className="tag-algorithm">Tested on 5,000 past hours</span>
        </div>

        <div className="table-responsive">
          <table className="allocation-results-table eval-table">
            <thead>
              <tr>
                <th style={{ width: '24%' }}>Model Name</th>
                <th style={{ width: '10%', textAlign: 'right' }}>Overall Accuracy</th>
                <th style={{ width: '10%', textAlign: 'right' }}>Balanced Score</th>
                <th style={{ width: '10%', textAlign: 'right' }}>Busy Hours Caught</th>
                <th style={{ width: '10%', textAlign: 'right' }}>Precision</th>
                <th style={{ width: '10%', textAlign: 'right' }}>Balance Score</th>
                <th style={{ width: '9%', textAlign: 'center' }}>Caught</th>
                <th style={{ width: '9%', textAlign: 'center' }}>False Alarms</th>
                <th style={{ width: '8%', textAlign: 'center' }}>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => {
                const isSelected = m.model_id === selectedModelId;
                return (
                  <tr
                    key={m.model_id}
                    className={`eval-row ${isSelected ? 'row-selected' : ''}`}
                    onClick={() => setSelectedModelId(m.model_id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <div className="eval-model-cell">
                        <span className="model-name-text">{m.model_name}</span>
                        <div className="model-sub-wrap">
                          <span className="model-type-tag">{m.architecture_type}</span>
                          {m.is_selected_candidate && (
                            <span className="candidate-mini-pill">SELECTED MODEL</span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                      {(m.overall_accuracy * 100).toFixed(2)}%
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                      {(m.balanced_accuracy * 100).toFixed(2)}%
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', color: m.high_recall > 0.6 ? '#16a34a' : '#dc2626', fontWeight: 700 }}>
                      {(m.high_recall * 100).toFixed(2)}%
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                      {(m.high_precision * 100).toFixed(2)}%
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 800, color: m.is_selected_candidate ? 'var(--accent-blue)' : 'inherit' }}>
                      {(m.high_f1_score * 100).toFixed(2)}%
                    </td>
                    <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                      <span className="tp-count-pill">{m.confusion_matrix.tp} / 73</span>
                    </td>
                    <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
                      <span className={`fp-count-pill ${m.confusion_matrix.fp > 1000 ? 'high-alarm' : ''}`}>
                        {m.confusion_matrix.fp.toLocaleString()}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <button
                        type="button"
                        className={`btn-inspect ${isSelected ? 'active' : ''}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedModelId(m.model_id);
                        }}
                      >
                        {isSelected ? 'Viewing' : 'Inspect'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confusion Matrix Section */}
      <div className="confusion-matrix-section" style={{ marginTop: '2rem' }}>
        <div className="card-header-row">
          <div>
            <h3 className="card-heading">2. Detailed Results for Selected Model</h3>
            <p className="card-subheading">
              Inspecting model: <strong>{activeModel.model_name}</strong> ({activeModel.architecture_type})
            </p>
          </div>
          <div className="model-switcher-pills">
            {models.map((m) => (
              <button
                key={m.model_id}
                type="button"
                className={`btn-model-tab ${m.model_id === selectedModelId ? 'active' : ''}`}
                onClick={() => setSelectedModelId(m.model_id)}
              >
                {m.model_name.split(' ')[0]}
              </button>
            ))}
          </div>
        </div>

        {/* 2x2 Confusion Matrix Grid with Labeled Axes */}
        <div className="cm-layout-container">
          <div className="cm-wrapper">
            {/* Top Axis Label: Predicted Class */}
            <div className="cm-top-axis">
              <span className="axis-title">WHAT THE MODEL PREDICTED</span>
              <div className="axis-col-headers">
                <div className="axis-col-header">
                  <strong>Predicted High Demand</strong>
                  <span className="axis-sub">Expected 2+ calls</span>
                </div>
                <div className="axis-col-header">
                  <strong>Predicted Normal Demand</strong>
                  <span className="axis-sub">Expected under 2 calls</span>
                </div>
              </div>
            </div>

            {/* Matrix Body with Left Axis Label */}
            <div className="cm-body-row">
              {/* Left Axis Label: Actual Class */}
              <div className="cm-left-axis">
                <span className="axis-title-vertical">WHAT ACTUALLY HAPPENED</span>
                <div className="axis-row-headers">
                  <div className="axis-row-header">
                    <strong>Actually High Demand</strong>
                    <span className="axis-sub">Total: {activeModel.confusion_matrix.actual_high}</span>
                  </div>
                  <div className="axis-row-header">
                    <strong>Actually Normal Demand</strong>
                    <span className="axis-sub">Total: {activeModel.confusion_matrix.actual_normal.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              {/* 2x2 Grid of Cells */}
              <div className="cm-grid">
                {/* Cell 1: True Positive (TP) */}
                <div className="cm-cell cm-tp">
                  <div className="cell-tag">Correctly Caught (True Positive)</div>
                  <div className="cell-number">{activeModel.confusion_matrix.tp}</div>
                  <div className="cell-pct">
                    {activeModel.confusion_matrix.actual_high > 0
                      ? `${((activeModel.confusion_matrix.tp / activeModel.confusion_matrix.actual_high) * 100).toFixed(1)}% of busy hours`
                      : '0%'}
                  </div>
                  <div className="cell-status-label">Busy Hours Caught</div>
                </div>

                {/* Cell 2: False Negative (FN) */}
                <div className="cm-cell cm-fn">
                  <div className="cell-tag">Missed (False Negative)</div>
                  <div className="cell-number">{activeModel.confusion_matrix.fn}</div>
                  <div className="cell-pct">
                    {activeModel.confusion_matrix.actual_high > 0
                      ? `${((activeModel.confusion_matrix.fn / activeModel.confusion_matrix.actual_high) * 100).toFixed(1)}% missed`
                      : '0%'}
                  </div>
                  <div className="cell-status-label">Missed Busy Hours</div>
                </div>

                {/* Cell 3: False Positive (FP) */}
                <div className="cm-cell cm-fp">
                  <div className="cell-tag">False Alarm (False Positive)</div>
                  <div className="cell-number">{activeModel.confusion_matrix.fp.toLocaleString()}</div>
                  <div className="cell-pct">
                    {`${((activeModel.confusion_matrix.fp / activeModel.confusion_matrix.actual_normal) * 100).toFixed(1)}% of normal`}
                  </div>
                  <div className="cell-status-label">False Alarms Sounded</div>
                </div>

                {/* Cell 4: True Negative (TN) */}
                <div className="cm-cell cm-tn">
                  <div className="cell-tag">Correct Normal (True Negative)</div>
                  <div className="cell-number">{activeModel.confusion_matrix.tn.toLocaleString()}</div>
                  <div className="cell-pct">
                    {`${((activeModel.confusion_matrix.tn / activeModel.confusion_matrix.actual_normal) * 100).toFixed(1)}% normal`}
                  </div>
                  <div className="cell-status-label">Correct Routine Hours</div>
                </div>
              </div>
            </div>
          </div>

          {/* Operational Meaning of Cells */}
          <div className="cm-explanations-card">
            <h4 className="card-subheading" style={{ marginBottom: '0.85rem' }}>
              What This Means in Practice:
            </h4>
            <div className="cm-expl-list">
              <div className="cm-expl-item tp">
                <strong>Correctly Caught ({activeModel.confusion_matrix.tp} hours):</strong>{' '}
                {activeModel.confusion_matrix.cell_explanations.tp}
              </div>
              <div className="cm-expl-item fn">
                <strong>Missed ({activeModel.confusion_matrix.fn} hours):</strong>{' '}
                {activeModel.confusion_matrix.cell_explanations.fn}
              </div>
              <div className="cm-expl-item fp">
                <strong>False Alarms ({activeModel.confusion_matrix.fp.toLocaleString()} hours):</strong>{' '}
                {activeModel.confusion_matrix.cell_explanations.fp}
              </div>
              <div className="cm-expl-item tn">
                <strong>Routine Hours ({activeModel.confusion_matrix.tn.toLocaleString()} hours):</strong>{' '}
                {activeModel.confusion_matrix.cell_explanations.tn}
              </div>
            </div>

            {/* Model Assessment Note */}
            <div className="model-assessment-box">
              <strong>Summary:</strong> {activeModel.operational_assessment}
            </div>
          </div>
        </div>
      </div>

      {/* Visual Metric Comparison Bars */}
      <div className="results-table-card" style={{ marginTop: '2rem' }}>
        <div className="card-header-row">
          <div>
            <h3 className="card-heading">3. Visual Comparison Across Models</h3>
            <p className="card-subheading">
              Comparing accuracy metrics on the same 5,000 test hours.
            </p>
          </div>
          <div className="metric-toggle-group">
            <button
              type="button"
              className={`btn-metric-toggle ${chartMetric === 'f1_score' ? 'active' : ''}`}
              onClick={() => setChartMetric('f1_score')}
            >
              Balance Score
            </button>
            <button
              type="button"
              className={`btn-metric-toggle ${chartMetric === 'recall' ? 'active' : ''}`}
              onClick={() => setChartMetric('recall')}
            >
              Busy Hours Caught
            </button>
            <button
              type="button"
              className={`btn-metric-toggle ${chartMetric === 'precision' ? 'active' : ''}`}
              onClick={() => setChartMetric('precision')}
            >
              Precision
            </button>
            <button
              type="button"
              className={`btn-metric-toggle ${chartMetric === 'balanced_acc' ? 'active' : ''}`}
              onClick={() => setChartMetric('balanced_acc')}
            >
              Balanced Score
            </button>
            <button
              type="button"
              className={`btn-metric-toggle ${chartMetric === 'all' ? 'active' : ''}`}
              onClick={() => setChartMetric('all')}
            >
              All Metrics
            </button>
          </div>
        </div>

        {/* Bar Chart Container */}
        <div className="eval-chart-container">
          {chartMetric === 'all' ? (
            <div className="multi-metric-grid">
              {models.map((m) => (
                <div key={m.model_id} className={`multi-metric-card ${m.is_selected_candidate ? 'candidate-border' : ''}`}>
                  <div className="m-card-header">
                    <strong>{m.model_name}</strong>
                    {m.is_selected_candidate && <span className="candidate-badge-sm">Selected</span>}
                  </div>
                  <div className="m-bars-stack">
                    <div className="m-bar-row">
                      <span className="m-bar-lbl">Caught:</span>
                      <div className="m-bar-track">
                        <div className="m-bar-fill recall" style={{ width: `${m.high_recall * 100}%` }}></div>
                      </div>
                      <span className="m-bar-val">{(m.high_recall * 100).toFixed(1)}%</span>
                    </div>
                    <div className="m-bar-row">
                      <span className="m-bar-lbl">Precision:</span>
                      <div className="m-bar-track">
                        <div className="m-bar-fill precision" style={{ width: `${Math.min(100, m.high_precision * 100 * 5)}%` }}></div>
                      </div>
                      <span className="m-bar-val">{(m.high_precision * 100).toFixed(1)}%</span>
                    </div>
                    <div className="m-bar-row">
                      <span className="m-bar-lbl">Balance:</span>
                      <div className="m-bar-track">
                        <div className="m-bar-fill f1" style={{ width: `${Math.min(100, m.high_f1_score * 100 * 3)}%` }}></div>
                      </div>
                      <span className="m-bar-val">{(m.high_f1_score * 100).toFixed(1)}%</span>
                    </div>
                    <div className="m-bar-row">
                      <span className="m-bar-lbl">Balanced:</span>
                      <div className="m-bar-track">
                        <div className="m-bar-fill balacc" style={{ width: `${m.balanced_accuracy * 100}%` }}></div>
                      </div>
                      <span className="m-bar-val">{(m.balanced_accuracy * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="single-metric-bars">
              {models.map((m) => {
                let val = 0;
                let maxVal = 1.0;
                let label = '';
                if (chartMetric === 'f1_score') {
                  val = m.high_f1_score;
                  label = `${(val * 100).toFixed(2)}%`;
                } else if (chartMetric === 'recall') {
                  val = m.high_recall;
                  label = `${(val * 100).toFixed(2)}% (${m.confusion_matrix.tp}/73 caught)`;
                } else if (chartMetric === 'precision') {
                  val = m.high_precision;
                  label = `${(val * 100).toFixed(2)}% (${m.confusion_matrix.tp}/${m.predicted_high_count})`;
                } else if (chartMetric === 'balanced_acc') {
                  val = m.balanced_accuracy;
                  label = `${(val * 100).toFixed(2)}%`;
                }

                const pctWidth = Math.max(3, (val / maxVal) * 100);

                return (
                  <div key={m.model_id} className="single-bar-row">
                    <div className="single-bar-model-info">
                      <span className="bar-model-name">{m.model_name}</span>
                      {m.is_selected_candidate && <span className="candidate-badge-sm">Selected</span>}
                    </div>
                    <div className="single-bar-track">
                      <div
                        className={`single-bar-fill ${chartMetric} ${m.is_selected_candidate ? 'highlight' : ''}`}
                        style={{ width: `${pctWidth}%` }}
                      ></div>
                    </div>
                    <span className="single-bar-value-text">{label}</span>
                  </div>
                );
              })}
            </div>
          )}

          <div className="chart-legend-row">
            <span className="legend-note">
              &#9733; <strong>Key Takeaway:</strong> Random Forest achieved the best overall balance (16.01%) by cutting false alarms down to 467 (compared to 2,119 in KNN) while still catching 64.38% of busy periods.
            </span>
          </div>
        </div>
      </div>

      {/* Educational & Decision-Support Insights Section */}
      <div className="educational-guidance-grid" style={{ marginTop: '2rem' }}>
        {/* Card 1: Accuracy Paradox */}
        <div className="guidance-card">
          <div className="guidance-card-header">
            <div className="guidance-icon warning">&#9888;</div>
            <h4 className="guidance-title">1. Why High Overall Accuracy Can Be Misleading</h4>
          </div>
          <p className="guidance-text">
            {guidance.why_accuracy_is_misleading}
          </p>
          <div className="guidance-highlight">
            <strong>Key Lesson:</strong> Over 98% of hours have normal demand. A simple model that always guesses "normal" scores 98.5% accuracy, but it would miss 100% of busy periods. That is why we check how many busy hours were actually caught.
          </div>
        </div>

        {/* Card 2: Operational Error Trade-offs */}
        <div className="guidance-card">
          <div className="guidance-card-header">
            <div className="guidance-icon balance">&#9878;</div>
            <h4 className="guidance-title">2. Balancing Missed Surges vs. False Alarms</h4>
          </div>
          <p className="guidance-text">
            {guidance.operational_tradeoffs}
          </p>
          <div className="guidance-highlight">
            <strong>Practical Balance:</strong> While KNN catches 58 surges, it sounds 2,119 false alarms (alerting in 43.5% of all hours). Random Forest cuts false alarms by nearly 78%, making suggestions useful in real life.
          </div>
        </div>

        {/* Card 3: Academic Baseline Scope */}
        <div className="guidance-card">
          <div className="guidance-card-header">
            <div className="guidance-icon notice">&#9432;</div>
            <h4 className="guidance-title">3. Designed to Assist, Not Replace Humans</h4>
          </div>
          <p className="guidance-text">
            {guidance.academic_prototype_disclaimer}
          </p>
          <div className="guidance-highlight">
            <strong>Decision Support Only:</strong> This tool helps dispatch supervisors anticipate busier hours when planning extra coverage. It is an academic decision aid, not an autonomous 911 dispatch system.
          </div>
        </div>
      </div>

      {/* Final Academic Disclaimer Footer Notice */}
      <div className="eval-disclaimer-card" style={{ marginTop: '2rem' }}>
        <p className="eval-disclaimer-text">
          {evaluationData.disclaimer}
        </p>
      </div>
    </div>
  );
}
