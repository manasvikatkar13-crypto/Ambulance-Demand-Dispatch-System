import React, { useState, useEffect, useRef, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Navigation,
  ArrowLeftRight,
  MapPin,
  Hospital,
  Sparkles,
  Clock,
  Compass,
  Route,
  Info,
  CheckCircle2,
  ChevronRight,
  RotateCcw,
  Maximize2,
  AlertCircle,
  Trash2,
  Layers,
  ShieldCheck,
  Activity,
  GitBranch,
} from 'lucide-react';

/**
 * 12 Verified Geographic Presets Across Montgomery County, Pennsylvania
 * All latitude and longitude coordinates correspond to real hospitals, EMS stations,
 * and key arterial highway junctions in Montgomery County, PA.
 */
export const MONTGOMERY_COUNTY_PRESETS = [
  {
    id: 'NORRISTOWN_EMS',
    name: 'Norristown Central EMS Station',
    category: 'EMS Station',
    address: 'East Main St, Norristown, PA',
    lat: 40.1215,
    lng: -75.3400,
    description: 'Central municipal emergency response depot for Norristown',
    graphNodeId: 'NORRISTOWN_EMS',
  },
  {
    id: 'SUBURBAN_HOSPITAL',
    name: 'Suburban Community Hospital',
    category: 'Hospital',
    address: '2701 DeKalb Pike, East Norriton, PA',
    lat: 40.1340,
    lng: -75.3340,
    description: 'Acute emergency care facility in East Norriton',
    graphNodeId: 'SUBURBAN_HOSPITAL',
  },
  {
    id: 'ABINGTON_HOSPITAL',
    name: 'Jefferson Abington Hospital Trauma Center',
    category: 'Hospital',
    address: '1200 Old York Rd, Abington, PA',
    lat: 40.1200,
    lng: -75.1180,
    description: 'Regional Level II trauma and tertiary emergency referral center',
    graphNodeId: 'ABINGTON_HOSPITAL',
  },
  {
    id: 'POTTSTOWN_HOSPITAL',
    name: 'Pottstown Hospital Emergency Dept',
    category: 'Hospital',
    address: '1600 E High St, Pottstown, PA',
    lat: 40.2520,
    lng: -75.6420,
    description: 'Tower Health acute emergency care center in Pottstown',
    graphNodeId: 'POTTSTOWN_HOSPITAL',
  },
  {
    id: 'MAIN_LINE_HOSPITAL',
    name: 'Bryn Mawr Hospital (Main Line Health)',
    category: 'Hospital',
    address: '130 S Bryn Mawr Ave, Bryn Mawr, PA',
    lat: 40.0210,
    lng: -75.3160,
    description: 'Emergency department serving southern Montgomery County',
    graphNodeId: 'MAIN_LINE_HOSPITAL',
  },
  {
    id: 'LANKENAU_HOSPITAL',
    name: 'Lankenau Medical Center',
    category: 'Hospital',
    address: '100 E Lancaster Ave, Wynnewood, PA',
    lat: 39.9880,
    lng: -75.2630,
    description: 'Level II trauma center serving Lower Merion township',
    graphNodeId: null,
  },
  {
    id: 'HOLY_REDEEMER_HOSPITAL',
    name: 'Holy Redeemer Hospital Emergency Room',
    category: 'Hospital',
    address: '1648 Huntingdon Pike, Meadowbrook, PA',
    lat: 40.1190,
    lng: -75.0740,
    description: 'Community emergency facility in eastern Montgomery County',
    graphNodeId: null,
  },
  {
    id: 'KOP_INTERCHANGE',
    name: 'King of Prussia Mall & US-202 / I-76 Hub',
    category: 'Hub',
    address: 'US-202 & Goddard Blvd, King of Prussia, PA',
    lat: 40.0880,
    lng: -75.3960,
    description: 'High-volume commercial corridor and highway interchange',
    graphNodeId: 'ZONE_KING_OF_PRUSSIA',
  },
  {
    id: 'LANSDALE_EMS',
    name: 'Lansdale VMSC Station',
    category: 'EMS Station',
    address: '175 Medical Campus Dr, Lansdale, PA',
    lat: 40.2415,
    lng: -75.2838,
    description: 'Volunteer Medical Service Corps serving North Penn region',
    graphNodeId: 'LANSDALE_EMS',
  },
  {
    id: 'LOWER_PROVIDENCE_EMS',
    name: 'Lower Providence EMS Station',
    category: 'EMS Station',
    address: 'Ridge Pike & Trooper Rd, Eagleville, PA',
    lat: 40.1580,
    lng: -75.4050,
    description: 'EMS depot serving Lower Providence, Audubon, and Eagleville',
    graphNodeId: 'LOWER_PROVIDENCE_EMS',
  },
  {
    id: 'CHELTENHAM_EMS',
    name: 'Cheltenham Township EMS Station',
    category: 'EMS Station',
    address: 'Cheltenham Ave, Cheltenham, PA',
    lat: 40.0600,
    lng: -75.1100,
    description: 'Depot serving eastern township border and Route 611 corridor',
    graphNodeId: 'CHELTENHAM_EMS',
  },
  {
    id: 'VALLEY_FORGE_PARK',
    name: 'Valley Forge Sector',
    category: 'Landmark',
    address: 'Route 23, Valley Forge, PA',
    lat: 40.1010,
    lng: -75.4480,
    description: 'National Historical Park and Schuylkill River corridor',
    graphNodeId: 'ZONE_VALLEY_FORGE',
  },
];

const INITIAL_MAP_CENTER = [40.18, -75.33]; // Montgomery County, PA geographic center
const INITIAL_MAP_ZOOM = 11;

/**
 * RoutePlanningView Component
 * Features:
 * 1. Real Road Route on Interactive Leaflet Map using OpenStreetMap data and OSRM engine.
 * 2. Complete route geometry highlighted in bright electric cyan with a thick dark navy outline.
 * 3. Animated progressive drawing along actual road curves from Marker A (green) to Marker B (red).
 * 4. Automatic zoom and fitBounds so both markers and the complete route are visible.
 * 5. Swap Locations recalculates and redraws the reversed route.
 * 6. Clear Route removes the polyline and resets view.
 * 7. Race condition protection prevents older API responses from overwriting newer requests.
 * 8. Preserves the A* Algorithm Demonstration as a separate academic graph solver.
 */
export default function RoutePlanningView() {
  // Mode toggle: 'road' (Real Road Route on Map) vs 'astar' (A* Algorithm Demonstration)
  const [activeMode, setActiveMode] = useState('road');

  // Road Routing State
  const [startPoint, setStartPoint] = useState(MONTGOMERY_COUNTY_PRESETS[0]);
  const [destPoint, setDestPoint] = useState(MONTGOMERY_COUNTY_PRESETS[1]);
  const [roadRoute, setRoadRoute] = useState(null);
  const [loadingRoad, setLoadingRoad] = useState(false);
  const [roadError, setRoadError] = useState(null);

  // A* Graph Search State (Preserved from Step 15)
  const [nodes, setNodes] = useState([]);
  const [startNode, setStartNode] = useState('NORRISTOWN_EMS');
  const [destinationNode, setDestinationNode] = useState('POTTSTOWN_HOSPITAL');
  const [loadingAstar, setLoadingAstar] = useState(false);
  const [loadingNodes, setLoadingNodes] = useState(true);
  const [astarError, setAstarError] = useState(null);
  const [astarResult, setAstarResult] = useState(null);

  // Cross-comparison state: when road route endpoints match known A* graph nodes
  const [comparedAstar, setComparedAstar] = useState(null);

  // Request race-condition counter
  const requestIdRef = useRef(0);

  // Leaflet map references
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);
  const routeLayerRef = useRef(null);
  const animFrameRef = useRef(null);

  // Load backend A* graph nodes on mount
  useEffect(() => {
    const fetchNodes = async () => {
      setLoadingNodes(true);
      try {
        const response = await fetch('http://127.0.0.1:8000/routes/nodes');
        if (response.ok) {
          const data = await response.json();
          setNodes(data);
        }
      } catch (err) {
        console.warn('Backend graph nodes unavailable; using offline defaults:', err);
      } finally {
        setLoadingNodes(false);
      }
    };
    fetchNodes();
  }, []);

  // ---------------------------------------------------------------------------
  // Leaflet Map Initialization
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (activeMode !== 'road') return;
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    // React 18 StrictMode cleanup guard
    if (mapContainerRef.current._leaflet_id) {
      delete mapContainerRef.current._leaflet_id;
    }

    const map = L.map(mapContainerRef.current, {
      center: INITIAL_MAP_CENTER,
      zoom: INITIAL_MAP_ZOOM,
      minZoom: 9,
      maxZoom: 18,
      zoomControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors | OSRM Driving Engine',
      maxZoom: 18,
    }).addTo(map);

    // Create dedicated panes for the route outline and electric cyan line
    // to guarantee they render above base map tiles/polygons and beneath markers
    const outlinePane = map.createPane('routeOutlinePane');
    outlinePane.style.zIndex = '450';
    outlinePane.style.pointerEvents = 'none';

    const linePane = map.createPane('routeLinePane');
    linePane.style.zIndex = '460';
    linePane.style.pointerEvents = 'none';

    const markersLayer = L.layerGroup().addTo(map);
    const routeLayer = L.layerGroup().addTo(map);

    markersLayerRef.current = markersLayer;
    routeLayerRef.current = routeLayer;
    mapInstanceRef.current = map;

    // Map click handler: allows user to click any point to set Start or Destination
    map.on('click', (e) => {
      const { lat, lng } = e.latlng;
      const popupContent = document.createElement('div');
      popupContent.className = 'map-picker-popup';
      popupContent.innerHTML = `
        <div class="popup-title"><strong>Selected Location</strong></div>
        <div class="popup-coord">${lat.toFixed(5)}, ${lng.toFixed(5)}</div>
        <div class="popup-hint">Montgomery County Area</div>
        <div class="popup-buttons">
          <button type="button" class="popup-set-btn set-start">Set as Start (A)</button>
          <button type="button" class="popup-set-btn set-dest">Set as Destination (B)</button>
        </div>
      `;

      const startBtn = popupContent.querySelector('.set-start');
      const destBtn = popupContent.querySelector('.set-dest');

      startBtn.addEventListener('click', () => {
        handleStartChange({
          id: `CUSTOM_${Date.now()}`,
          name: `Custom Point (${lat.toFixed(4)}, ${lng.toFixed(4)})`,
          category: 'Selected Location',
          address: 'User-selected point on map',
          lat,
          lng,
          isCustom: true,
          graphNodeId: null,
        });
        map.closePopup();
      });

      destBtn.addEventListener('click', () => {
        handleDestinationChange({
          id: `CUSTOM_${Date.now()}`,
          name: `Custom Point (${lat.toFixed(4)}, ${lng.toFixed(4)})`,
          category: 'Selected Location',
          address: 'User-selected point on map',
          lat,
          lng,
          isCustom: true,
          graphNodeId: null,
        });
        map.closePopup();
      });

      L.popup({ offset: [0, -10] })
        .setLatLng(e.latlng)
        .setContent(popupContent)
        .openOn(map);
    });

    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 150);

    return () => {
      clearTimeout(timer);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
      markersLayerRef.current = null;
      routeLayerRef.current = null;
    };
  }, [activeMode]);

  // Window resize & layout settlement listener to keep map correctly sized
  useEffect(() => {
    if (activeMode !== 'road' || !mapInstanceRef.current) return;
    const map = mapInstanceRef.current;
    const t1 = setTimeout(() => map.invalidateSize(), 100);
    const t2 = setTimeout(() => map.invalidateSize(), 350);

    const onResize = () => {
      map.invalidateSize();
    };
    window.addEventListener('resize', onResize);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      window.removeEventListener('resize', onResize);
    };
  }, [activeMode]);

  // ---------------------------------------------------------------------------
  // Synchronize Markers on the Map
  // ---------------------------------------------------------------------------
  const updateMapMarkers = useCallback(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;
    const layer = markersLayerRef.current;
    layer.clearLayers();

    // 1. Render subtle preset icons across Montgomery County
    MONTGOMERY_COUNTY_PRESETS.forEach((preset) => {
      const isStart = startPoint && startPoint.id === preset.id;
      const isDest = destPoint && destPoint.id === preset.id;
      if (isStart || isDest) return; // Dedicated highlight markers handled below

      const isHospital = preset.category === 'Hospital';
      const iconHtml = `
        <div class="preset-map-pin ${isHospital ? 'hospital-pin' : 'station-pin'}" title="${preset.name}">
          <span>${isHospital ? '&#10010;' : '&#9679;'}</span>
        </div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'preset-marker-div',
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });

      const marker = L.marker([preset.lat, preset.lng], { icon: customIcon });

      const popupEl = document.createElement('div');
      popupEl.className = 'preset-popup-box';
      popupEl.innerHTML = `
        <div class="preset-popup-title">${preset.name}</div>
        <div class="preset-popup-category">${preset.category} &bull; ${preset.address}</div>
        <div class="preset-popup-actions">
          <button type="button" class="preset-pop-btn pick-start">Set as Start (A)</button>
          <button type="button" class="preset-pop-btn pick-dest">Set as Destination (B)</button>
        </div>
      `;

      popupEl.querySelector('.pick-start').addEventListener('click', () => {
        handleStartChange(preset);
        mapInstanceRef.current.closePopup();
      });

      popupEl.querySelector('.pick-dest').addEventListener('click', () => {
        handleDestinationChange(preset);
        mapInstanceRef.current.closePopup();
      });

      marker.bindPopup(popupEl, { offset: [0, -8] });
      layer.addLayer(marker);
    });

    // 2. Render prominent START marker (Green with pulse ring, letter A)
    if (startPoint && startPoint.lat && startPoint.lng) {
      const startHtml = `
        <div class="route-endpoint-pin start-pin">
          <div class="pin-badge">A</div>
          <div class="pin-ring"></div>
        </div>
      `;
      const startIcon = L.divIcon({
        html: startHtml,
        className: 'start-marker-container',
        iconSize: [36, 36],
        iconAnchor: [18, 18],
      });
      const startMarker = L.marker([startPoint.lat, startPoint.lng], {
        icon: startIcon,
        zIndexOffset: 1000,
      }).bindTooltip(`<strong>START (A):</strong> ${startPoint.name}`, {
        direction: 'top',
        offset: [0, -18],
        permanent: false,
      });
      layer.addLayer(startMarker);
    }

    // 3. Render prominent DESTINATION marker (Red with pulse ring, letter B)
    if (destPoint && destPoint.lat && destPoint.lng) {
      const destHtml = `
        <div class="route-endpoint-pin dest-pin">
          <div class="pin-badge">B</div>
          <div class="pin-ring"></div>
        </div>
      `;
      const destIcon = L.divIcon({
        html: destHtml,
        className: 'dest-marker-container',
        iconSize: [36, 36],
        iconAnchor: [18, 18],
      });
      const destMarker = L.marker([destPoint.lat, destPoint.lng], {
        icon: destIcon,
        zIndexOffset: 1000,
      }).bindTooltip(`<strong>DESTINATION (B):</strong> ${destPoint.name}`, {
        direction: 'top',
        offset: [0, -18],
        permanent: false,
      });
      layer.addLayer(destMarker);
    }
  }, [startPoint, destPoint]);

  useEffect(() => {
    if (activeMode === 'road') {
      updateMapMarkers();
    }
  }, [activeMode, updateMapMarkers]);

  // ---------------------------------------------------------------------------
  // Route Line Drawing & Smooth Animation
  // ---------------------------------------------------------------------------
  const renderRoadPolyline = useCallback(
    (geometryCoords) => {
      if (!mapInstanceRef.current || !routeLayerRef.current) return;
      const map = mapInstanceRef.current;
      const layer = routeLayerRef.current;

      layer.clearLayers();
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);

      if (!geometryCoords || geometryCoords.length < 2) {
        if (geometryCoords && geometryCoords.length === 1) {
          const dot = L.circleMarker(geometryCoords[0], {
            radius: 8,
            color: '#070e1b',
            weight: 3,
            fillColor: '#00f0ff',
            fillOpacity: 1,
            pane: 'routeLinePane',
          });
          layer.addLayer(dot);
        }
        return;
      }

      const totalPts = geometryCoords.length;

      // 1. Thick dark navy casing underneath (weight 10, opacity 0.95)
      // Guarantees high-contrast visibility over city streets, buildings, and terrain
      const casingPolyline = L.polyline(geometryCoords.slice(0, 2), {
        color: '#070e1b',
        weight: 10,
        opacity: 0.95,
        lineCap: 'round',
        lineJoin: 'round',
        pane: 'routeOutlinePane',
      });

      // 2. Bright electric cyan / bright blue line on top (weight 5, opacity 1.0)
      const activePolyline = L.polyline(geometryCoords.slice(0, 2), {
        color: '#00f0ff',
        weight: 5,
        opacity: 1.0,
        lineCap: 'round',
        lineJoin: 'round',
        pane: 'routeLinePane',
      });

      layer.addLayer(casingPolyline);
      layer.addLayer(activePolyline);

      // Auto zoom & pan so that the entire highlighted route and both markers are visible
      const fullBounds = L.latLngBounds(geometryCoords);
      if (startPoint?.lat && startPoint?.lng) fullBounds.extend([startPoint.lat, startPoint.lng]);
      if (destPoint?.lat && destPoint?.lng) fullBounds.extend([destPoint.lat, destPoint.lng]);

      map.fitBounds(fullBounds, {
        padding: [60, 60],
        maxZoom: 15,
        animate: true,
      });

      // Smooth route-drawing animation from A to B
      const startTime = performance.now();
      const animDuration = Math.min(800, Math.max(350, totalPts * 1.5));

      const animateStep = (now) => {
        const elapsed = now - startTime;
        const progress = Math.min(1, elapsed / animDuration);
        // Cubic ease-out curve
        const eased = 1 - Math.pow(1 - progress, 3);
        const count = Math.max(2, Math.floor(eased * totalPts));

        const sliceCoords = geometryCoords.slice(0, count);
        casingPolyline.setLatLngs(sliceCoords);
        activePolyline.setLatLngs(sliceCoords);

        if (progress < 1) {
          animFrameRef.current = requestAnimationFrame(animateStep);
        } else {
          casingPolyline.setLatLngs(geometryCoords);
          activePolyline.setLatLngs(geometryCoords);
        }
      };

      animFrameRef.current = requestAnimationFrame(animateStep);
    },
    [startPoint, destPoint]
  );

  // Re-draw route if activeMode is switched back to 'road' with existing roadRoute
  useEffect(() => {
    if (activeMode === 'road' && mapInstanceRef.current && roadRoute?.geometry) {
      renderRoadPolyline(roadRoute.geometry);
    }
  }, [activeMode, roadRoute, renderRoadPolyline]);

  // ---------------------------------------------------------------------------
  // Core Route Fetching & Calculation Function
  // ---------------------------------------------------------------------------
  const calculateRoadRoute = useCallback(
    async (origin, destination) => {
      if (!origin || !destination) {
        setRoadError('Please select both a starting location and destination.');
        return;
      }

      const currentReqId = ++requestIdRef.current;

      // Cancel running animations and clear existing route visualization
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (routeLayerRef.current) routeLayerRef.current.clearLayers();

      setLoadingRoad(true);
      setRoadError(null);
      setRoadRoute(null);
      setComparedAstar(null);

      try {
        let routeData = null;

        // 1. Try FastAPI backend route endpoint first
        try {
          const response = await fetch('http://127.0.0.1:8000/routes/road', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              start_lat: origin.lat,
              start_lng: origin.lng,
              dest_lat: destination.lat,
              dest_lng: destination.lng,
              start_name: origin.name,
              dest_name: destination.name,
            }),
          });

          if (response.ok) {
            routeData = await response.json();
          }
        } catch (backendErr) {
          console.warn('Backend /routes/road failed, falling back to direct OSRM:', backendErr);
        }

        // Prevent older request from overwriting a newer route request
        if (currentReqId !== requestIdRef.current) return;

        // 2. Direct browser fallback to public OSRM driving API if backend was unreachable
        if (!routeData || !routeData.found) {
          const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${origin.lng},${origin.lat};${destination.lng},${destination.lat}?overview=full&geometries=geojson`;
          const res = await fetch(osrmUrl);
          if (!res.ok) {
            throw new Error(`OSRM service returned HTTP status ${res.status}`);
          }

          const osrmJson = await res.json();
          if (osrmJson.code !== 'Ok' || !osrmJson.routes || osrmJson.routes.length === 0) {
            throw new Error('No drivable road route found between these locations.');
          }

          const rawRoute = osrmJson.routes[0];
          const distKm = parseFloat((rawRoute.distance / 1000).toFixed(2));
          const distMi = parseFloat((distKm * 0.621371).toFixed(2));
          const durMin = parseFloat((rawRoute.duration / 60).toFixed(1));
          const coords = rawRoute.geometry.coordinates.map((pt) => [pt[1], pt[0]]);

          routeData = {
            found: true,
            source: 'OpenStreetMap / OSRM (Direct Public Client)',
            start_name: origin.name,
            dest_name: destination.name,
            start_lat: origin.lat,
            start_lng: origin.lng,
            dest_lat: destination.lat,
            dest_lng: destination.lng,
            distance_km: distKm,
            distance_miles: distMi,
            duration_minutes: durMin,
            geometry: coords,
            coordinate_count: coords.length,
            disclaimer:
              'Road route calculated along OpenStreetMap road centerlines via OSRM. Standard speed limit estimate without live traffic delays.',
          };
        }

        // Prevent older response from overwriting newer request
        if (currentReqId !== requestIdRef.current) return;

        if (!routeData.geometry || routeData.geometry.length === 0) {
          throw new Error('No route geometry returned by routing service.');
        }

        setRoadRoute(routeData);
        renderRoadPolyline(routeData.geometry);
        checkAstarComparison(origin, destination);
      } catch (err) {
        if (currentReqId === requestIdRef.current) {
          setRoadError(
            `Unable to retrieve road route (${err.message || 'Network error'}). Please verify your internet connection or try another pair of locations.`
          );
        }
      } finally {
        if (currentReqId === requestIdRef.current) {
          setLoadingRoad(false);
        }
      }
    },
    [renderRoadPolyline]
  );

  // Submit button handler
  const handleFindRoadRoute = (e) => {
    if (e) e.preventDefault();
    calculateRoadRoute(startPoint, destPoint);
  };

  // Cross-compare with A* graph if both locations correspond to known graph nodes
  const checkAstarComparison = async (startP, destP) => {
    if (startP.graphNodeId && destP.graphNodeId && startP.graphNodeId !== destP.graphNodeId) {
      try {
        const res = await fetch('http://127.0.0.1:8000/routes/astar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            start_node: startP.graphNodeId,
            destination_node: destP.graphNodeId,
          }),
        });
        if (res.ok) {
          const astarData = await res.json();
          setComparedAstar(astarData);
        }
      } catch {
        // Silently omit comparison if backend A* is unreachable
      }
    } else {
      setComparedAstar(null);
    }
  };

  // ---------------------------------------------------------------------------
  // Location Change, Swap, and Clear Actions
  // ---------------------------------------------------------------------------
  const handleStartChange = (newStart) => {
    requestIdRef.current += 1;
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (routeLayerRef.current) routeLayerRef.current.clearLayers();
    setStartPoint(newStart);
    setRoadRoute(null);
    setRoadError(null);
    setComparedAstar(null);
  };

  const handleDestinationChange = (newDest) => {
    requestIdRef.current += 1;
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (routeLayerRef.current) routeLayerRef.current.clearLayers();
    setDestPoint(newDest);
    setRoadRoute(null);
    setRoadError(null);
    setComparedAstar(null);
  };

  const handleSwapLocations = () => {
    const prevStart = startPoint;
    const prevDest = destPoint;
    setStartPoint(prevDest);
    setDestPoint(prevStart);
    setRoadRoute(null);
    setComparedAstar(null);
    if (routeLayerRef.current) routeLayerRef.current.clearLayers();
    // Requirement 8: Recalculate and redraw route for the reversed direction!
    calculateRoadRoute(prevDest, prevStart);
  };

  const handleClearRoute = () => {
    requestIdRef.current += 1;
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (routeLayerRef.current) routeLayerRef.current.clearLayers();
    setRoadRoute(null);
    setRoadError(null);
    setComparedAstar(null);
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView(INITIAL_MAP_CENTER, INITIAL_MAP_ZOOM, { animate: true });
    }
  };

  const handleFitToRoute = () => {
    if (!mapInstanceRef.current) return;
    if (roadRoute && roadRoute.geometry && roadRoute.geometry.length > 0) {
      const bounds = L.latLngBounds(roadRoute.geometry);
      if (startPoint?.lat && startPoint?.lng) bounds.extend([startPoint.lat, startPoint.lng]);
      if (destPoint?.lat && destPoint?.lng) bounds.extend([destPoint.lat, destPoint.lng]);
      mapInstanceRef.current.fitBounds(bounds, { padding: [60, 60], animate: true });
    } else if (startPoint && destPoint) {
      const bounds = L.latLngBounds([
        [startPoint.lat, startPoint.lng],
        [destPoint.lat, destPoint.lng],
      ]);
      mapInstanceRef.current.fitBounds(bounds, { padding: [60, 60], animate: true });
    } else {
      mapInstanceRef.current.setView(INITIAL_MAP_CENTER, INITIAL_MAP_ZOOM, { animate: true });
    }
  };

  const handleSelectQuickPair = (startId, destId) => {
    const s = MONTGOMERY_COUNTY_PRESETS.find((p) => p.id === startId);
    const d = MONTGOMERY_COUNTY_PRESETS.find((p) => p.id === destId);
    if (s && d) {
      requestIdRef.current += 1;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (routeLayerRef.current) routeLayerRef.current.clearLayers();
      setStartPoint(s);
      setDestPoint(d);
      setRoadRoute(null);
      setRoadError(null);
      setComparedAstar(null);
    }
  };

  // ---------------------------------------------------------------------------
  // A* Algorithm Demonstration Handlers (Preserved from Step 15)
  // ---------------------------------------------------------------------------
  const handleFindAstarRoute = async (e) => {
    if (e) e.preventDefault();
    if (!startNode || !destinationNode) {
      setAstarError('Please select both a start node and destination node.');
      return;
    }
    setLoadingAstar(true);
    setAstarError(null);
    setAstarResult(null);

    try {
      const res = await fetch('http://127.0.0.1:8000/routes/astar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_node: startNode,
          destination_node: destinationNode,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Couldn't compute A* route on this graph.");
      }
      setAstarResult(data);
    } catch (err) {
      setAstarError(err.message || 'Failed to calculate route via A*.');
    } finally {
      setLoadingAstar(false);
    }
  };

  const handleSwapAstar = () => {
    const prevStart = startNode;
    setStartNode(destinationNode);
    setDestinationNode(prevStart);
    setAstarResult(null);
  };

  return (
    <div className="view-container route-planning-view">
      {/* View Header */}
      <header className="view-header">
        <span className="view-badge">Dispatch Routing</span>
        <h2 className="view-title">Find an Ambulance Route</h2>
        <p className="view-description">
          Calculate actual road routes across Montgomery County, Pennsylvania, or inspect the academic A* pathfinding algorithm.
        </p>
      </header>

      {/* Mode Switcher Tabs */}
      <div className="route-mode-switcher-bar">
        <button
          type="button"
          className={`route-mode-tab ${activeMode === 'road' ? 'active' : ''}`}
          onClick={() => setActiveMode('road')}
        >
          <MapPin size={16} />
          <span>Real Road Route (Interactive Map)</span>
          <span className="mode-pill-accent">OSRM Road Data</span>
        </button>

        <button
          type="button"
          className={`route-mode-tab ${activeMode === 'astar' ? 'active' : ''}`}
          onClick={() => setActiveMode('astar')}
        >
          <GitBranch size={16} />
          <span>A* Algorithm Demonstration</span>
          <span className="mode-pill-accent">Graph Solver</span>
        </button>
      </div>

      {/* ====================================================================
          MODE 1: REAL ROAD ROUTE ON INTERACTIVE MAP
          ==================================================================== */}
      {activeMode === 'road' && (
        <div className="real-road-route-section">
          {/* Honest Route Data & Limitation Notice */}
          <div className="dashboard-notice-card" role="region" aria-label="Road Routing Transparency Notice">
            <div className="dashboard-notice-icon">
              <Info size={20} />
            </div>
            <div>
              <div className="dashboard-notice-title">
                OpenStreetMap Road Centerline Routing (Montgomery County, PA)
              </div>
              <div className="dashboard-notice-text">
                Road routes follow real Pennsylvania highways, county arterials, and local streets via OpenStreetMap road vectors.
                <strong> Estimated travel times use standard speed limits and do not reflect live siren right-of-way, real-time traffic jams, or construction closures.</strong>
              </div>
            </div>
          </div>

          {/* Location Selection & Control Card */}
          <div className="route-form-card">
            <div className="card-header-row">
              <div>
                <h3 className="card-heading">Select Starting Point & Destination</h3>
                <p className="card-subheading">
                  Choose from verified Montgomery County emergency facilities, or click anywhere on the map to set a custom coordinate.
                </p>
              </div>

              {/* Quick Sample Route Presets */}
              <div className="route-presets">
                <span className="presets-label">Quick Routes:</span>
                <button
                  type="button"
                  className="btn-preset"
                  onClick={() => handleSelectQuickPair('NORRISTOWN_EMS', 'SUBURBAN_HOSPITAL')}
                >
                  Norristown &rarr; Suburban Hospital
                </button>
                <button
                  type="button"
                  className="btn-preset"
                  onClick={() => handleSelectQuickPair('NORRISTOWN_EMS', 'POTTSTOWN_HOSPITAL')}
                >
                  Norristown &rarr; Pottstown Hospital
                </button>
                <button
                  type="button"
                  className="btn-preset"
                  onClick={() => handleSelectQuickPair('KOP_INTERCHANGE', 'MAIN_LINE_HOSPITAL')}
                >
                  King of Prussia &rarr; Bryn Mawr
                </button>
                <button
                  type="button"
                  className="btn-preset"
                  onClick={() => handleSelectQuickPair('LANSDALE_EMS', 'ABINGTON_HOSPITAL')}
                >
                  Lansdale &rarr; Abington Hospital
                </button>
              </div>
            </div>

            <form onSubmit={handleFindRoadRoute} className="route-selectors-form">
              <div className="selectors-grid">
                {/* Starting Location Picker */}
                <div className="form-group selector-box">
                  <label htmlFor="road-start-select" className="form-label selector-label">
                    <span className="origin-marker-dot"></span>
                    Starting Location (Ambulance Origin A)
                  </label>
                  <select
                    id="road-start-select"
                    value={startPoint?.id || ''}
                    onChange={(e) => {
                      const sel = MONTGOMERY_COUNTY_PRESETS.find((p) => p.id === e.target.value);
                      if (sel) handleStartChange(sel);
                    }}
                    className="form-select selector-input"
                  >
                    {startPoint?.isCustom && (
                      <option value={startPoint.id}>{startPoint.name} (Map Clicked)</option>
                    )}
                    {MONTGOMERY_COUNTY_PRESETS.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.category})
                      </option>
                    ))}
                  </select>
                  <div className="selected-node-hint">
                    <span className="node-badge station">{startPoint?.category || 'Origin'}</span>
                    <span>{startPoint?.address || `${startPoint?.lat?.toFixed(4)}, ${startPoint?.lng?.toFixed(4)}`}</span>
                  </div>
                </div>

                {/* Swap Locations Button */}
                <div className="swap-btn-wrap">
                  <button
                    type="button"
                    onClick={handleSwapLocations}
                    className="btn-swap"
                    title="Swap start and destination and recalculate route"
                    aria-label="Swap start and destination and recalculate route"
                  >
                    <ArrowLeftRight size={18} />
                  </button>
                </div>

                {/* Destination Location Picker */}
                <div className="form-group selector-box">
                  <label htmlFor="road-dest-select" className="form-label selector-label">
                    <span className="dest-marker-dot"></span>
                    Destination (Incident / Hospital B)
                  </label>
                  <select
                    id="road-dest-select"
                    value={destPoint?.id || ''}
                    onChange={(e) => {
                      const sel = MONTGOMERY_COUNTY_PRESETS.find((p) => p.id === e.target.value);
                      if (sel) handleDestinationChange(sel);
                    }}
                    className="form-select selector-input"
                  >
                    {destPoint?.isCustom && (
                      <option value={destPoint.id}>{destPoint.name} (Map Clicked)</option>
                    )}
                    {MONTGOMERY_COUNTY_PRESETS.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.category})
                      </option>
                    ))}
                  </select>
                  <div className="selected-node-hint">
                    <span className="node-badge hospital">{destPoint?.category || 'Target'}</span>
                    <span>{destPoint?.address || `${destPoint?.lat?.toFixed(4)}, ${destPoint?.lng?.toFixed(4)}`}</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons Row */}
              <div className="road-action-buttons-row">
                <div className="left-map-hints">
                  <MapPin size={14} style={{ color: 'var(--teal-primary)' }} />
                  <span>Tip: Click any marker or blank spot on the map to set Start (A) or Destination (B)</span>
                </div>

                <div className="right-action-btns">
                  {roadRoute && (
                    <button
                      type="button"
                      onClick={handleClearRoute}
                      className="btn-clear-route"
                      title="Clear route line and reset map"
                    >
                      <Trash2 size={15} style={{ marginRight: '0.35rem' }} />
                      Clear Route
                    </button>
                  )}

                  <button
                    type="submit"
                    disabled={loadingRoad}
                    className="btn-primary find-route-btn"
                  >
                    <Sparkles size={16} style={{ marginRight: '0.4rem' }} />
                    {loadingRoad ? 'Finding Road Route...' : 'Find Route'}
                  </button>
                </div>
              </div>
            </form>
          </div>

          {/* Error Banner */}
          {roadError && (
            <div className="error-banner" role="alert" style={{ marginTop: '1.25rem' }}>
              <div className="error-title">Road Routing Notice</div>
              <div>{roadError}</div>
            </div>
          )}

          {/* Interactive Leaflet Road Map Canvas */}
          <div className="road-map-card">
            <div className="road-map-header-bar">
              <div className="map-title-wrap">
                <Compass size={18} style={{ color: 'var(--teal-primary)' }} />
                <span className="map-title-text">Interactive Montgomery County Road Map</span>
                {roadRoute && (
                  <span className="map-route-status-tag">
                    Route Highlighted: {roadRoute.distance_km} km ({roadRoute.distance_miles} mi)
                  </span>
                )}
              </div>

              <div className="map-header-tools">
                <button
                  type="button"
                  className="map-tool-btn"
                  onClick={handleFitToRoute}
                  title="Fit entire route and markers on map"
                >
                  <Maximize2 size={14} />
                  <span>Fit Route</span>
                </button>
                <button
                  type="button"
                  className="map-tool-btn"
                  onClick={handleClearRoute}
                  title="Recenter to Montgomery County overview"
                >
                  <RotateCcw size={14} />
                  <span>Recenter County</span>
                </button>
              </div>
            </div>

            {/* Map Element Container */}
            <div className="road-map-wrapper">
              <div
                ref={mapContainerRef}
                className="road-map-container"
                style={{ height: '520px', width: '100%' }}
                aria-label="Montgomery County Road Route Interactive Map"
              />

              {/* Floating Map Legend */}
              <div className="road-map-floating-legend">
                <div className="legend-title">Map Legend</div>
                <div className="legend-row">
                  <span className="legend-circle start-dot"></span>
                  <span>Origin (Start Marker A)</span>
                </div>
                <div className="legend-row">
                  <span className="legend-circle dest-dot"></span>
                  <span>Destination (Goal Marker B)</span>
                </div>
                <div className="legend-row">
                  <span className="legend-line route-line-sample"></span>
                  <span>Road Path (Electric Cyan on Navy)</span>
                </div>
                <div className="legend-row">
                  <span className="legend-symbol">&#10010;</span>
                  <span>Hospital Trauma Center</span>
                </div>
                <div className="legend-row">
                  <span className="legend-symbol">&#9679;</span>
                  <span>EMS Dispatch Station</span>
                </div>
              </div>
            </div>
          </div>

          {/* Calculated Route Details & Summary Metrics */}
          {roadRoute && (
            <div className="road-summary-panel">
              <div className="route-metrics-grid">
                <div className="metric-card card-accent-teal">
                  <span className="metric-label">Calculated Road Distance</span>
                  <span className="metric-value" style={{ color: 'var(--teal-primary)' }}>
                    {roadRoute.distance_km} km
                  </span>
                  <span className="metric-sub">{roadRoute.distance_miles} miles along road curves</span>
                </div>

                <div className="metric-card card-accent-blue">
                  <span className="metric-label">Estimated Travel Time</span>
                  <span className="metric-value" style={{ color: '#0284c7' }}>
                    {roadRoute.duration_minutes} min
                  </span>
                  <span className="metric-sub">Standard speed limit road estimate</span>
                </div>

                <div className="metric-card card-accent-lavender">
                  <span className="metric-label">Road Geometry Points</span>
                  <span className="metric-value">{roadRoute.coordinate_count}</span>
                  <span className="metric-sub">OpenStreetMap GPS centerline points</span>
                </div>

                <div className="metric-card">
                  <span className="metric-label">Routing Provider</span>
                  <span className="metric-value" style={{ fontSize: '1.05rem', color: 'var(--primary-navy)' }}>
                    OSRM Driving Engine
                  </span>
                  <span className="metric-sub">OpenStreetMap road centerline vectors</span>
                </div>
              </div>

              {/* Route Summary Itinerary Card */}
              <div className="road-path-info-card">
                <div className="info-header-row">
                  <div className="info-icon-bubble">
                    <CheckCircle2 size={18} style={{ color: 'var(--teal-primary)' }} />
                  </div>
                  <div>
                    <h4 className="info-card-title">Road Route Summary</h4>
                    <p className="info-card-sub">
                      Curved road route from <strong>{roadRoute.start_name}</strong> to <strong>{roadRoute.dest_name}</strong>
                    </p>
                  </div>
                </div>

                <div className="info-itinerary-box">
                  <div className="itinerary-node start">
                    <span className="itinerary-tag">START (A)</span>
                    <div>
                      <strong>{roadRoute.start_name}</strong>
                      <div className="itinerary-coord">
                        Lat: {roadRoute.start_lat.toFixed(5)}, Lng: {roadRoute.start_lng.toFixed(5)}
                      </div>
                    </div>
                  </div>

                  <div className="itinerary-transit">
                    <ChevronRight size={18} className="itinerary-arrow" />
                    <span className="itinerary-transit-details">
                      {roadRoute.distance_km} km along highway & street centerlines (~{roadRoute.duration_minutes} min)
                    </span>
                  </div>

                  <div className="itinerary-node dest">
                    <span className="itinerary-tag goal">GOAL (B)</span>
                    <div>
                      <strong>{roadRoute.dest_name}</strong>
                      <div className="itinerary-coord">
                        Lat: {roadRoute.dest_lat.toFixed(5)}, Lng: {roadRoute.dest_lng.toFixed(5)}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="road-disclaimer-box">
                  <ShieldCheck size={16} style={{ color: 'var(--teal-primary)', flexShrink: 0 }} />
                  <span>{roadRoute.disclaimer}</span>
                </div>
              </div>

              {/* Explicit A* Algorithm Comparison Banner */}
              {comparedAstar && comparedAstar.found && (
                <div className="astar-comparison-card">
                  <div className="comp-header">
                    <GitBranch size={18} style={{ color: 'var(--accent-blue)' }} />
                    <h4 className="comp-title">A* Algorithm Cross-Check</h4>
                    <span className="comp-tag">Academic Graph Comparison</span>
                  </div>
                  <p className="comp-text">
                    This location pair is also connected in our internal 17-node dispatch graph.
                    Here is how the theoretical A* shortest path compares with the real curved road geometry:
                  </p>
                  <div className="comp-stats-grid">
                    <div className="comp-stat-col">
                      <span className="comp-label">Real Road Distance (OSRM)</span>
                      <span className="comp-val">{roadRoute.distance_km} km</span>
                      <span className="comp-sub">Follows real highway curves & ramps</span>
                    </div>
                    <div className="comp-stat-col">
                      <span className="comp-label">A* Graph Distance</span>
                      <span className="comp-val">{comparedAstar.total_cost_km.toFixed(1)} km</span>
                      <span className="comp-sub">Segment graph cost via {comparedAstar.path.length} stops</span>
                    </div>
                    <div className="comp-stat-col">
                      <span className="comp-label">A* Search Efficiency</span>
                      <span className="comp-val">{comparedAstar.visited_count} evaluated</span>
                      <span className="comp-sub">Guided by straight-line Haversine</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn-inspect-astar"
                    onClick={() => {
                      setActiveMode('astar');
                      setStartNode(startPoint.graphNodeId);
                      setDestinationNode(destPoint.graphNodeId);
                      setAstarResult(comparedAstar);
                    }}
                  >
                    View Full A* Graph Traversal Details &rarr;
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ====================================================================
          MODE 2: A* ALGORITHM DEMONSTRATION (PRESERVED STEP 15)
          ==================================================================== */}
      {activeMode === 'astar' && (
        <div className="astar-demonstration-section">
          {/* Honest Graph Algorithm Notice */}
          <div className="dashboard-notice-card" role="region" aria-label="A* Graph Demonstration Notice">
            <div className="dashboard-notice-icon">
              <Info size={20} />
            </div>
            <div>
              <div className="dashboard-notice-title">
                Academic A* Algorithm Demonstration (17-Node Dispatch Graph)
              </div>
              <div className="dashboard-notice-text">
                This solver runs the A* pathfinding algorithm over a representative 17-node network of Montgomery County
                emergency facilities using an admissible Haversine straight-line heuristic.
                <strong> It is an internal computer science graph demonstration, distinct from the external OSRM road router.</strong>
              </div>
            </div>
          </div>

          {/* Graph Route Form */}
          <div className="route-form-card">
            <div className="card-header-row">
              <div>
                <h3 className="card-heading">Choose Graph Start and Destination</h3>
                <p className="card-subheading">
                  Pick starting station and destination node to inspect A* search exploration.
                </p>
              </div>

              {/* Sample Graph Presets */}
              <div className="route-presets">
                <span className="presets-label">Graph Scenarios:</span>
                <button
                  type="button"
                  className="btn-preset"
                  onClick={() => {
                    setStartNode('NORRISTOWN_EMS');
                    setDestinationNode('POTTSTOWN_HOSPITAL');
                    setAstarResult(null);
                  }}
                >
                  Norristown &rarr; Pottstown Hospital
                </button>
                <button
                  type="button"
                  className="btn-preset"
                  onClick={() => {
                    setStartNode('NORRISTOWN_EMS');
                    setDestinationNode('ABINGTON_HOSPITAL');
                    setAstarResult(null);
                  }}
                >
                  Norristown &rarr; Abington Hospital
                </button>
                <button
                  type="button"
                  className="btn-preset alert"
                  title="Test unreachable destination"
                  onClick={() => {
                    setStartNode('NORRISTOWN_EMS');
                    setDestinationNode('ISOLATED_RIVER_ISLAND');
                    setAstarResult(null);
                  }}
                >
                  Test Disconnected Island
                </button>
              </div>
            </div>

            <form onSubmit={handleFindAstarRoute} className="route-selectors-form">
              <div className="selectors-grid">
                <div className="form-group selector-box">
                  <label htmlFor="astar-start-select" className="form-label selector-label">
                    <span className="origin-marker-dot"></span>
                    Starting Node
                  </label>
                  <select
                    id="astar-start-select"
                    value={startNode}
                    onChange={(e) => {
                      setStartNode(e.target.value);
                      setAstarResult(null);
                    }}
                    className="form-select selector-input"
                    disabled={loadingNodes}
                  >
                    {nodes.map((node) => (
                      <option key={node.id} value={node.id}>
                        {node.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="swap-btn-wrap">
                  <button
                    type="button"
                    onClick={handleSwapAstar}
                    className="btn-swap"
                    title="Swap start and destination"
                    aria-label="Swap start and destination"
                  >
                    <ArrowLeftRight size={18} />
                  </button>
                </div>

                <div className="form-group selector-box">
                  <label htmlFor="astar-dest-select" className="form-label selector-label">
                    <span className="dest-marker-dot"></span>
                    Destination Node
                  </label>
                  <select
                    id="astar-dest-select"
                    value={destinationNode}
                    onChange={(e) => {
                      setDestinationNode(e.target.value);
                      setAstarResult(null);
                    }}
                    className="form-select selector-input"
                    disabled={loadingNodes}
                  >
                    {nodes.map((node) => (
                      <option key={node.id} value={node.id}>
                        {node.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-actions-row">
                <button
                  type="submit"
                  disabled={loadingAstar || loadingNodes}
                  className="btn-primary find-route-btn"
                >
                  <Sparkles size={16} style={{ marginRight: '0.4rem' }} />
                  {loadingAstar ? 'Evaluating Graph Nodes...' : 'Find Route via A*'}
                </button>
              </div>
            </form>
          </div>

          {/* Error Banner */}
          {astarError && (
            <div className="error-banner" role="alert" style={{ marginTop: '1.25rem' }}>
              <div className="error-title">A* Graph Notice</div>
              <div>{astarError}</div>
            </div>
          )}

          {/* A* Results Display */}
          {astarResult && !loadingAstar && (
            <div className="route-results-section">
              <div className="route-metrics-grid">
                <div className="metric-card card-accent-teal">
                  <span className="metric-label">Graph Shortest Distance</span>
                  <span className="metric-value" style={{ color: 'var(--teal-primary)' }}>
                    {astarResult.total_cost_km.toFixed(1)} km
                  </span>
                  <span className="metric-sub">
                    {astarResult.path.length <= 1 ? 'Start and goal are same' : `${astarResult.path.length - 1} road segments`}
                  </span>
                </div>

                <div className="metric-card card-accent-blue">
                  <span className="metric-label">Nodes Evaluated by Search</span>
                  <span className="metric-value">{astarResult.visited_count}</span>
                  <span className="metric-sub">Evaluated out of {nodes.length} graph points</span>
                </div>

                <div className="metric-card card-accent-lavender">
                  <span className="metric-label">Waypoints in Optimal Path</span>
                  <span className="metric-value">{astarResult.path.length}</span>
                  <span className="metric-sub">Consecutive facilities</span>
                </div>

                <div className="metric-card">
                  <span className="metric-label">Calculation Time</span>
                  <span className="metric-value" style={{ fontFamily: 'var(--font-mono)' }}>
                    {astarResult.execution_time_ms.toFixed(2)} ms
                  </span>
                  <span className="metric-sub">Exact PriorityQueue search</span>
                </div>
              </div>

              {/* Explanation Card */}
              <div className="route-explanation-card">
                <div className="explanation-header">
                  <CheckCircle2 size={18} style={{ color: 'var(--teal-primary)', marginRight: '0.4rem' }} />
                  <strong>How the A* Algorithm Solved This Path</strong>
                </div>
                <p className="explanation-text">{astarResult.explanation}</p>
                <div className="explanation-meta">
                  <span><strong>Method:</strong> A* (A-Star) with Priority Queue (min-heap)</span> &bull;{' '}
                  <span><strong>Heuristic:</strong> Admissible Haversine distance $h(n) \le d(n)$</span>
                </div>
              </div>

              {/* Stepper Breadcrumbs */}
              <div className="route-stepper-card">
                <h3 className="card-heading">A* Optimal Path Sequence</h3>
                <div className="path-breadcrumbs-wrap">
                  {astarResult.path.map((nodeId, idx) => {
                    const nodeObj = nodes.find((n) => n.id === nodeId);
                    const isStart = idx === 0;
                    const isGoal = idx === astarResult.path.length - 1;
                    return (
                      <React.Fragment key={nodeId}>
                        <div className={`breadcrumb-node ${isStart ? 'start' : ''} ${isGoal ? 'goal' : ''}`}>
                          <div className="node-step-num">{idx + 1}</div>
                          <div className="node-step-info">
                            <span className="node-step-name">{nodeObj ? nodeObj.name : nodeId}</span>
                          </div>
                        </div>
                        {idx < astarResult.path.length - 1 && (
                          <div className="breadcrumb-arrow">
                            <ChevronRight size={16} />
                          </div>
                        )}
                      </React.Fragment>
                    );
                  })}
                </div>
              </div>

              {/* Segments Table */}
              {astarResult.path_details.length > 0 && (
                <div className="segments-table-card">
                  <h3 className="card-heading">Step-by-Step Road Segments</h3>
                  <div className="table-responsive">
                    <table className="segments-table">
                      <thead>
                        <tr>
                          <th style={{ width: '8%', textAlign: 'center' }}>Step</th>
                          <th style={{ width: '30%' }}>From</th>
                          <th style={{ width: '30%' }}>To</th>
                          <th style={{ width: '20%' }}>Road Name</th>
                          <th style={{ width: '12%', textAlign: 'right' }}>Distance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {astarResult.path_details.map((step, idx) => (
                          <tr key={idx}>
                            <td style={{ textAlign: 'center', fontWeight: 800, color: 'var(--text-muted)' }}>
                              #{idx + 1}
                            </td>
                            <td><strong>{step.from_name}</strong></td>
                            <td><strong>{step.to_name}</strong></td>
                            <td style={{ fontWeight: 600, color: 'var(--primary-navy)' }}>
                              {step.road_name}
                            </td>
                            <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                              <strong>{step.distance_km.toFixed(1)} km</strong>
                              <div className="cell-sub">cum: {step.cumulative_cost_km.toFixed(1)} km</div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Evaluated Nodes Chips */}
              <div className="visited-nodes-card">
                <div className="card-header-row">
                  <h4 className="card-heading" style={{ fontSize: '0.95rem' }}>
                    Graph Nodes Explored During Search Space Expansion
                  </h4>
                  <span className="visited-count-tag">
                    {astarResult.visited_count} evaluated
                  </span>
                </div>
                <div className="visited-chips-list">
                  {astarResult.nodes_visited.map((vId, idx) => {
                    const inFinal = astarResult.path.includes(vId);
                    const nodeObj = nodes.find((n) => n.id === vId);
                    return (
                      <span
                        key={vId}
                        className={`visited-chip ${inFinal ? 'in-path' : 'explored-only'}`}
                      >
                        <span className="chip-order">#{idx + 1}</span>
                        {nodeObj ? nodeObj.name : vId}
                        {inFinal && <span className="chip-check">&#10003;</span>}
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
