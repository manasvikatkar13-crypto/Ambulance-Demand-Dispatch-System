import React, { useState, useEffect, useRef, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  MapPin,
  Info,
  Flame,
  Layers,
  Compass,
  Filter,
  BarChart2,
  Calendar,
  Sparkles,
} from 'lucide-react';

/**
 * HotspotsView Component
 * Renders an interactive spatial map of historical EMS call concentrations across Montgomery County, PA.
 * Uses real latitude and longitude coordinates aggregated into 0.01-degree (~1 km) grid cells.
 */
export default function HotspotsView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedHotspot, setSelectedHotspot] = useState(null);
  const [displayLimit, setDisplayLimit] = useState(75);
  const [mapReady, setMapReady] = useState(false);

  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);

  // Fetch hotspot aggregation from FastAPI endpoint
  const fetchHotspots = useCallback(async () => {
    setLoading(true);
    setError(null);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    try {
      const response = await fetch(`http://127.0.0.1:8000/dashboard/hotspots?limit=150`, {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Failed to fetch hotspots from API (HTTP ${response.status}: ${response.statusText})`);
      }

      const json = await response.json();
      setData(json);
      if (json.hotspots && json.hotspots.length > 0) {
        setSelectedHotspot(json.hotspots[0]);
      }
    } catch (err) {
      setError(
        err.name === 'AbortError'
          ? 'Hotspots request timed out. Please verify that the FastAPI backend is running.'
          : err.message || 'Failed to connect to backend at http://127.0.0.1:8000.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHotspots();
  }, [fetchHotspots]);

  // Initialize Leaflet map once container is mounted into DOM
  useEffect(() => {
    // Cannot initialize if still loading or if container div is not yet mounted
    if (loading || error || !mapContainerRef.current) return;

    // Guard against duplicate initialization
    if (mapInstanceRef.current) return;

    // Safety cleanup for React 18 StrictMode mount/unmount cycle
    if (mapContainerRef.current._leaflet_id) {
      delete mapContainerRef.current._leaflet_id;
    }

    // Default center for Montgomery County, PA: [40.20, -75.35]
    const initialCenter = (data?.hotspots && data.hotspots.length > 0)
      ? [data.hotspots[0].lat, data.hotspots[0].lng]
      : [40.20, -75.35];

    const map = L.map(mapContainerRef.current, {
      center: initialCenter,
      zoom: 11,
      minZoom: 9,
      maxZoom: 16,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
      maxZoom: 18,
    }).addTo(map);

    const markersLayer = L.layerGroup().addTo(map);
    markersLayerRef.current = markersLayer;
    mapInstanceRef.current = map;
    setMapReady(true);

    // Invalidate size after layout settles to guarantee complete tile grid rendering
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 150);

    return () => {
      clearTimeout(timer);
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
      markersLayerRef.current = null;
      setMapReady(false);
    };
  }, [loading, error, data]);

  // Recalculate Leaflet map viewport dimensions on window resize
  useEffect(() => {
    const handleResize = () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.invalidateSize();
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Update map markers whenever map is ready, data updates, or displayLimit changes
  useEffect(() => {
    if (!mapReady || !mapInstanceRef.current || !markersLayerRef.current || !data?.hotspots) return;

    const layer = markersLayerRef.current;
    layer.clearLayers();

    const activeHotspots = data.hotspots.slice(0, displayLimit);

    activeHotspots.forEach((spot) => {
      // Perceptual circle radius scaled with square root of intensity
      // Min radius 7px, Max radius 28px
      const radius = 7 + Math.sqrt(spot.relative_intensity) * 21;

      // Color encoding based on call intensity
      let color = '#2563eb'; // blue for baseline/moderate
      let fillColor = '#3b82f6';
      if (spot.relative_intensity >= 0.6) {
        color = '#b91c1c'; // deep red for top surge tier
        fillColor = '#ef4444';
      } else if (spot.relative_intensity >= 0.3) {
        color = '#ea580c'; // orange for elevated surge tier
        fillColor = '#f97316';
      }

      const circle = L.circleMarker([spot.lat, spot.lng], {
        radius,
        color,
        fillColor,
        fillOpacity: 0.65,
        weight: 2,
      });

      const popupContent = `
        <div style="font-family: system-ui, sans-serif; font-size: 13px; line-height: 1.4; min-width: 190px;">
          <div style="font-size: 11px; font-weight: 800; color: #dc2626; text-transform: uppercase; margin-bottom: 2px;">
            #${spot.rank} High-Call Area
          </div>
          <div style="font-size: 15px; font-weight: 800; color: #0f172a; margin-bottom: 4px;">
            ${spot.primary_township}
          </div>
          <div style="color: #475569; font-size: 12px; margin-bottom: 6px;">
            <strong>Approximate Location:</strong> ${spot.lat.toFixed(2)}°N, ${Math.abs(spot.lng).toFixed(2)}°W
          </div>
          <div style="background-color: #f1f5f9; padding: 6px 8px; border-radius: 4px; margin-bottom: 6px;">
            <div style="font-weight: 700; color: #0f172a; font-size: 14px;">
              ${spot.call_count.toLocaleString()} Past Calls
            </div>
            <div style="font-size: 11px; color: #64748b;">
              ${spot.percentage_of_total}% of all county records
            </div>
          </div>
          <div style="font-size: 11px; color: #64748b;">
            <strong>Recorded Between:</strong> ${spot.start_date} and ${spot.end_date}
          </div>
        </div>
      `;

      circle.bindPopup(popupContent);

      circle.on('click', () => {
        setSelectedHotspot(spot);
      });

      layer.addLayer(circle);
    });
  }, [mapReady, data, displayLimit]);

  // Handler to pan and focus on a selected hotspot from sidebar list
  const handleSelectHotspot = (spot) => {
    setSelectedHotspot(spot);
    const map = mapInstanceRef.current;
    if (map) {
      map.flyTo([spot.lat, spot.lng], 13, { duration: 1.2 });
    }
  };

  return (
    <div className="view-container hotspots-view">
      <header className="view-header">
        <span className="view-badge">Historical Map</span>
        <h2 className="view-title">Areas With More Past Emergency Calls</h2>
        <p className="view-description">
          See which neighborhoods in Montgomery County, Pennsylvania had the most 911 emergency medical calls
          in our historical records (December 2015 to July 2020).
        </p>
      </header>

      {/* Mandatory Honest Context Notice */}
      <div className="dashboard-notice-card" role="region" aria-label="Dataset Authenticity Notice">
        <div className="dashboard-notice-icon">
          <Info size={20} />
        </div>
        <div>
          <div className="dashboard-notice-title">
            About This Map (Historical Records Only)
          </div>
          <div className="dashboard-notice-text">
            These colored circles show where <strong>past 911 calls were concentrated</strong> between December 2015
            and July 2020. <strong>These areas had more emergency calls in the historical dataset. They do not show live
            emergencies.</strong> Each circle marks the center of an approximate 1 km neighborhood area, not an ambulance
            station or exact incident address.
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="dashboard-loading-state">
          <div className="spinner"></div>
          <p style={{ fontWeight: 600, color: '#1e293b' }}>Loading map data...</p>
          <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.25rem' }}>
            Fetching call locations from the server
          </p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="dashboard-error-state">
          <div style={{ color: '#dc2626', fontWeight: 700, fontSize: '1rem', marginBottom: '0.5rem' }}>
            Map Information Currently Unavailable
          </div>
          <p style={{ fontSize: '0.875rem', color: '#475569', marginBottom: '1rem' }}>{error}</p>
          <p style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '1rem' }}>
            Please make sure the backend server is running and try again.
          </p>
          <button onClick={fetchHotspots} className="btn-primary" style={{ display: 'inline-flex', padding: '0.6rem 1.5rem' }}>
            Try Again
          </button>
        </div>
      )}

      {/* Main Content Area: Map and Hotspot Details */}
      {!loading && !error && data && (
        <div className="hotspots-layout">
          {/* Left Column: Interactive Map */}
          <div className="map-column">
            <div className="map-card">
              <div className="map-toolbar">
                <div className="map-legend-items">
                  <span className="legend-chip high">
                    <span className="dot high"></span> &ge; 4,000 calls (Busiest)
                  </span>
                  <span className="legend-chip med">
                    <span className="dot med"></span> 2,000–3,999 calls (Moderate)
                  </span>
                  <span className="legend-chip norm">
                    <span className="dot norm"></span> &lt; 2,000 calls (Baseline)
                  </span>
                </div>

                <div className="map-control-filter">
                  <Filter size={14} style={{ color: 'var(--teal-primary)' }} />
                  <label htmlFor="hotspot-limit" style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                    Show Top:
                  </label>
                  <select
                    id="hotspot-limit"
                    value={displayLimit}
                    onChange={(e) => setDisplayLimit(Number(e.target.value))}
                    className="form-select"
                    style={{ padding: '0.3rem 0.65rem', fontSize: '0.8rem', width: 'auto' }}
                  >
                    <option value={25}>Top 25 Areas</option>
                    <option value={50}>Top 50 Areas</option>
                    <option value={75}>Top 75 Areas</option>
                    <option value={100}>Top 100 Areas</option>
                    <option value={150}>Top 150 Areas</option>
                  </select>
                </div>
              </div>

              {/* Map Canvas */}
              <div
                ref={mapContainerRef}
                className="leaflet-map-canvas"
                style={{ height: '520px', minHeight: '450px', width: '100%', borderRadius: '0 0 10px 10px' }}
              ></div>

              <div className="map-footer-note">
                <Compass size={14} style={{ color: 'var(--teal-primary)', flexShrink: 0 }} />
                <span>Tip: Click any colored circle to view call details, or choose an area from the ranked list on the right.</span>
              </div>
            </div>
          </div>

          {/* Right Column: Hotspot Inspector & Ranked Table */}
          <div className="sidebar-column">
            {/* Selected Hotspot Detail Card */}
            {selectedHotspot && (
              <div className="inspector-card">
                <div className="inspector-header">
                  <span className="rank-pill">
                    <Flame size={13} style={{ marginRight: '0.25rem' }} />
                    Rank #{selectedHotspot.rank}
                  </span>
                  <span className="cell-id-badge">{selectedHotspot.cell_id}</span>
                </div>

                <h3 className="inspector-twp">
                  <MapPin size={18} style={{ color: 'var(--teal-primary)', verticalAlign: 'middle', marginRight: '0.35rem' }} />
                  {selectedHotspot.primary_township}
                </h3>
                <div className="inspector-coords">
                  Center: {selectedHotspot.lat.toFixed(2)}&deg; N, {Math.abs(selectedHotspot.lng).toFixed(2)}&deg; W
                </div>

                <div className="inspector-stat-grid">
                  <div className="stat-tile">
                    <div className="tile-label">Past Calls</div>
                    <div className="tile-value">{selectedHotspot.call_count.toLocaleString()}</div>
                    <div className="tile-sub">{selectedHotspot.percentage_of_total}% of all calls</div>
                  </div>
                  <div className="stat-tile">
                    <div className="tile-label">Relative Activity</div>
                    <div className="tile-value">{(selectedHotspot.relative_intensity * 100).toFixed(0)}%</div>
                    <div className="tile-sub">Compared to busiest area</div>
                  </div>
                </div>

                <div className="inspector-meta-row">
                  <span><strong>Years of Records:</strong> {selectedHotspot.start_date} to {selectedHotspot.end_date}</span>
                </div>
                <div className="inspector-meta-row">
                  <span><strong>Area Size:</strong> ~1 km &times; 1 km neighborhood box</span>
                </div>
              </div>
            )}

            {/* Ranked Hotspots List */}
            <div className="hotspot-list-card">
              <div className="hotspot-list-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <BarChart2 size={16} style={{ color: 'var(--teal-primary)' }} />
                  <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--primary-navy)' }}>
                    Areas Ranked by Past Calls
                  </h4>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Showing {data.hotspots.slice(0, displayLimit).length} of {data.summary.total_grid_cells_identified} areas
                </span>
              </div>

              <div className="hotspot-scroll-list">
                {data.hotspots.slice(0, displayLimit).map((spot) => {
                  const isSelected = selectedHotspot?.cell_id === spot.cell_id;
                  return (
                    <div
                      key={spot.cell_id}
                      className={`hotspot-list-item ${isSelected ? 'selected' : ''}`}
                      onClick={() => handleSelectHotspot(spot)}
                    >
                      <div className="spot-item-left">
                        <span className={`spot-rank ${spot.rank <= 5 ? 'top5' : ''}`}>
                          #{spot.rank}
                        </span>
                        <div>
                          <div className="spot-twp">{spot.primary_township}</div>
                          <div className="spot-coords">{spot.lat}&deg;N, {spot.lng}&deg;W</div>
                        </div>
                      </div>
                      <div className="spot-item-right">
                        <div className="spot-count">{spot.call_count.toLocaleString()}</div>
                        <div className="spot-percent">{spot.percentage_of_total}%</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Statistical Summary Box */}
      {data && (
        <div className="hotspot-stats-banner">
          <div className="banner-item">
            <span className="b-label">Total Past Calls Analyzed</span>
            <span className="b-val">{data.summary.total_calls_analyzed.toLocaleString()}</span>
          </div>
          <div className="banner-item">
            <span className="b-label">Records With Map Locations</span>
            <span className="b-val">{data.summary.valid_records_count.toLocaleString()}</span>
          </div>
          <div className="banner-item">
            <span className="b-label">Records Missing Coordinates</span>
            <span className="b-val">{data.summary.excluded_records_count}</span>
          </div>
          <div className="banner-item">
            <span className="b-label">Distinct Neighborhood Areas</span>
            <span className="b-val">{data.summary.total_grid_cells_identified.toLocaleString()}</span>
          </div>
          <div className="banner-item">
            <span className="b-label">Grid Neighborhood Size</span>
            <span className="b-val">~1 km across ({data.summary.approx_cell_dimensions})</span>
          </div>
        </div>
      )}
    </div>
  );
}
