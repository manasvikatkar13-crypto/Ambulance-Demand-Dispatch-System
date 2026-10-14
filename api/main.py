"""
AI-Based Emergency Ambulance Demand & Dispatch System
FastAPI Backend Service

This module exposes a RESTful API for real-time ambulance demand classification.
It loads the trained Random Forest pipeline ('models/demand_classifier_candidate.joblib')
once on application startup and serves predictions over HTTP.

Key Endpoints:
- GET  /         : Welcome message, system status, and API metadata.
- GET  /health   : Health check endpoint reporting model loading status.
- POST /predict  : Generates demand class predictions ('HIGH' vs 'NORMAL') with class probabilities.
"""

import os
import json
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.allocation import (
    AllocationRecommendationRequest,
    AllocationRecommendationResponse,
    compute_allocation_recommendations,
)
from api.routing import (
    AStarRouteRequest,
    AStarRouteResponse,
    RoadNetworkGraphResponse,
    NetworkNode,
    find_astar_route,
    get_network_nodes_list,
    get_network_graph_metadata,
    NodeNotFoundError,
    UnreachableDestinationError,
    RoadRouteRequest,
    RoadRouteResponse,
    RoutingServiceError,
    fetch_osrm_road_route,
)
from api.dispatch import (
    IntegratedDispatchPlanRequest,
    IntegratedDispatchPlanResponse,
    generate_integrated_dispatch_plan,
)
from api.evaluation import (
    ModelEvaluationResponse,
    ModelMetricsItem,
    get_model_evaluations,
    get_single_model_evaluation,
)

# ---------------------------------------------------------------------------
# Path Resolution
# ---------------------------------------------------------------------------
# Resolve the project root dynamically (one directory up from api/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "demand_classifier_candidate.joblib"
HISTORICAL_DEMAND_PATH = PROJECT_ROOT / "data" / "hourly_zone_demand.csv"
EMS_FEATURES_PATH = PROJECT_ROOT / "data" / "ems_features.csv"
HOTSPOTS_CACHE_PATH = PROJECT_ROOT / "data" / "historical_hotspots.json"

# Global references for loaded model pipeline and cached dashboard metrics
model_pipeline: Optional[Any] = None
model_load_error: Optional[str] = None

dashboard_cache: Dict[str, Any] = {}


def load_dashboard_cache():
    """
    Loads and aggregates historical EMS demand statistics once from 'data/hourly_zone_demand.csv'.
    Caches the summary, 24-hour pattern, and top zones in memory to avoid repeated disk I/O.
    """
    global dashboard_cache

    if not HISTORICAL_DEMAND_PATH.exists():
        dashboard_cache["error"] = (
            f"Historical demand data file not found at '{HISTORICAL_DEMAND_PATH}'. "
            "Please ensure 'data/hourly_zone_demand.csv' exists."
        )
        print(f"[WARNING] {dashboard_cache['error']}")
        return

    try:
        print(f"[STARTUP] Aggregating historical dashboard data from: {HISTORICAL_DEMAND_PATH}")
        df = pd.read_csv(HISTORICAL_DEMAND_PATH)

        # 1. Summary Metrics
        total_calls = int(df["demand"].sum())
        total_townships = int(df["twp"].nunique())
        start_date = str(df["date"].min())
        end_date = str(df["date"].max())

        hourly_series = df.groupby("hour")["demand"].sum().reindex(range(24), fill_value=0)
        busiest_hour = int(hourly_series.idxmax())
        busiest_hour_calls = int(hourly_series.max())
        busiest_hour_label = f"{busiest_hour:02d}:00"

        dashboard_cache["summary"] = {
            "total_calls": total_calls,
            "total_townships": total_townships,
            "start_date": start_date,
            "end_date": end_date,
            "date_range_display": f"{start_date} to {end_date}",
            "busiest_hour": busiest_hour,
            "busiest_hour_label": busiest_hour_label,
            "busiest_hour_calls": busiest_hour_calls,
            "is_historical": True,
        }

        # 2. Hourly Pattern (24 hourly totals for hours 0 through 23)
        pattern_list = [
            {
                "hour": h,
                "label": f"{h:02d}:00",
                "demand": int(hourly_series[h]),
            }
            for h in range(24)
        ]
        dashboard_cache["hourly_pattern"] = {
            "hourly_values": [int(hourly_series[h]) for h in range(24)],
            "hourly_pattern": pattern_list,
        }

        # 3. Top 5 Townships by Total Demand
        top5_series = df.groupby("twp")["demand"].sum().nlargest(5)
        top_zones_list = [
            {
                "twp": str(twp),
                "call_count": int(cnt),
                "total_demand": int(cnt),
                "rank": i + 1,
            }
            for i, (twp, cnt) in enumerate(top5_series.items())
        ]
        dashboard_cache["top_zones"] = {
            "top_zones": top_zones_list
        }

        # 4. Historical Hotspot Grid Cells (Top Density Concentrations)
        if HOTSPOTS_CACHE_PATH.exists():
            with open(HOTSPOTS_CACHE_PATH, "r", encoding="utf-8") as f:
                dashboard_cache["hotspots_data"] = json.load(f)
            print(f"[SUCCESS] Loaded {len(dashboard_cache['hotspots_data'].get('hotspots', []))} geographic hotspots from cache.")
        elif EMS_FEATURES_PATH.exists():
            print(f"[STARTUP] Computing geographic hotspots from: {EMS_FEATURES_PATH}")
            features_df = pd.read_csv(EMS_FEATURES_PATH, usecols=["lat", "lng", "date", "twp"])
            total_raw = len(features_df)
            valid_mask = (
                features_df["lat"].notna() &
                features_df["lng"].notna() &
                (features_df["lat"] >= 39.5) &
                (features_df["lat"] <= 41.0) &
                (features_df["lng"] >= -76.5) &
                (features_df["lng"] <= -74.5)
            )
            v_df = features_df[valid_mask].copy()
            valid_cnt = len(v_df)
            excl_cnt = total_raw - valid_cnt

            v_df["cell_lat"] = v_df["lat"].round(2)
            v_df["cell_lng"] = v_df["lng"].round(2)

            def get_mode(s):
                m = s.mode()
                return str(m.iloc[0]) if not m.empty else "Unknown"

            h_grouped = v_df.groupby(["cell_lat", "cell_lng"]).agg(
                call_count=("date", "count"),
                primary_twp=("twp", get_mode),
                start_date=("date", "min"),
                end_date=("date", "max")
            ).reset_index()

            h_grouped = h_grouped.sort_values(by="call_count", ascending=False).reset_index(drop=True)
            max_c = int(h_grouped["call_count"].max()) if not h_grouped.empty else 1

            hotspots_list = []
            for i, r in h_grouped.iterrows():
                cnt = int(r["call_count"])
                lat_v = round(float(r["cell_lat"]), 2)
                lng_v = round(float(r["cell_lng"]), 2)
                hotspots_list.append({
                    "cell_id": f"{lat_v:.2f}_{lng_v:.2f}",
                    "lat": lat_v,
                    "lng": lng_v,
                    "call_count": cnt,
                    "primary_township": str(r["primary_twp"]),
                    "start_date": str(r["start_date"]),
                    "end_date": str(r["end_date"]),
                    "percentage_of_total": round((cnt / valid_cnt) * 100, 2),
                    "relative_intensity": round(cnt / max_c, 3),
                    "rank": i + 1
                })

            cached_payload = {
                "summary": {
                    "total_calls_analyzed": total_raw,
                    "valid_records_count": valid_cnt,
                    "excluded_records_count": excl_cnt,
                    "total_grid_cells_identified": len(h_grouped),
                    "top_hotspots_returned": len(hotspots_list[:150]),
                    "start_date": str(features_df["date"].min()),
                    "end_date": str(features_df["date"].max()),
                    "rounding_precision": 2,
                    "approx_cell_dimensions": "~1.1 km x ~0.85 km (0.01 deg)",
                    "coordinate_bounds": {
                        "lat_min": round(float(features_df["lat"].min()), 4),
                        "lat_max": round(float(features_df["lat"].max()), 4),
                        "lng_min": round(float(features_df["lng"].min()), 4),
                        "lng_max": round(float(features_df["lng"].max()), 4)
                    },
                    "disclaimer": "Historical EMS call concentrations (Dec 2015 - Jul 2020), not live emergencies or guaranteed future demand. Does not represent official municipal boundaries."
                },
                "hotspots": hotspots_list[:150],
                "all_hotspots": hotspots_list
            }

            try:
                with open(HOTSPOTS_CACHE_PATH, "w", encoding="utf-8") as f_out:
                    json.dump(cached_payload, f_out, indent=2)
            except Exception as e_w:
                print(f"[WARNING] Could not persist hotspots cache file: {e_w}")

            dashboard_cache["hotspots_data"] = cached_payload

        dashboard_cache["error"] = None
        print(f"[SUCCESS] Historical dashboard metrics cached ({total_calls:,} calls across {total_townships} zones).")

    except Exception as e:
        dashboard_cache["error"] = f"Failed to load historical dashboard data: {str(e)}"
        print(f"[ERROR] {dashboard_cache['error']}")


def get_dashboard_cache_data(key: str) -> Dict[str, Any]:
    """
    Returns cached dashboard data by key, attempting lazy load if not yet initialized.
    """
    if key not in dashboard_cache and dashboard_cache.get("error") is None:
        load_dashboard_cache()

    if dashboard_cache.get("error"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=dashboard_cache["error"],
        )

    if key not in dashboard_cache:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dashboard key '{key}' not found in cache.",
        )

    return dashboard_cache[key]


# ---------------------------------------------------------------------------
# Application Lifespan (Startup & Shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Loads the machine learning model pipeline and pre-aggregates historical
    dashboard analytics once on startup.
    """
    global model_pipeline, model_load_error
    print(f"[STARTUP] Initializing API from root: {PROJECT_ROOT}")
    print(f"[STARTUP] Attempting to load model from: {MODEL_PATH}")

    if not MODEL_PATH.exists():
        model_load_error = (
            f"Model file not found at '{MODEL_PATH}'. "
            "Please ensure 'src/compare_demand_classifiers.py' has been executed to generate the model artifact."
        )
        print(f"[ERROR] {model_load_error}")
    else:
        try:
            model_pipeline = joblib.load(MODEL_PATH)
            print("[SUCCESS] Machine learning model pipeline loaded successfully into memory.")
        except Exception as e:
            model_load_error = f"Failed to load model artifact: {str(e)}"
            print(f"[ERROR] {model_load_error}")

    # Load historical dashboard cache
    load_dashboard_cache()

    yield

    # Clean up resources on shutdown if needed
    print("[SHUTDOWN] API backend shutting down gracefully.")


# ---------------------------------------------------------------------------
# FastAPI Application Initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI-Based Emergency Ambulance Demand & Dispatch System API",
    description=(
        "Production-style backend for predicting hourly ambulance demand surges "
        "(HIGH vs. NORMAL) in Montgomery County, PA, using temporal and weather signals."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend development server (port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic Schemas (Input Request & Output Response)
# ---------------------------------------------------------------------------
class DemandPredictionRequest(BaseModel):
    """
    Input schema defining the 10 exact features required by the trained model pipeline.
    All fields include realistic boundary validation to prevent invalid inputs.
    """
    twp: str = Field(
        ...,
        description="Township/municipality name in Montgomery County (e.g., 'NORRISTOWN', 'LOWER MERION')",
        min_length=1,
        examples=["NORRISTOWN"]
    )
    hour: int = Field(
        ...,
        ge=0,
        le=23,
        description="Hour of the day in 24-hour format (0 to 23)",
        examples=[10]
    )
    month: int = Field(
        ...,
        ge=1,
        le=12,
        description="Month of the year (1 = January to 12 = December)",
        examples=[5]
    )
    day_of_week: int = Field(
        ...,
        ge=0,
        le=6,
        description="Day of the week (0 = Monday, 1 = Tuesday, ..., 6 = Sunday)",
        examples=[2]
    )
    is_weekend: int = Field(
        ...,
        ge=0,
        le=1,
        description="Weekend indicator flag (1 if Saturday or Sunday, else 0)",
        examples=[0]
    )
    temperature_2m: float = Field(
        ...,
        ge=-50.0,
        le=60.0,
        description="Ambient air temperature at 2 metres above ground in degrees Celsius (°C)",
        examples=[18.5]
    )
    relative_humidity_2m: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Relative humidity percentage (0.0 to 100.0%)",
        examples=[65.0]
    )
    precipitation: float = Field(
        ...,
        ge=0.0,
        le=500.0,
        description="Hourly precipitation liquid equivalent in millimetres (mm)",
        examples=[0.0]
    )
    wind_speed_10m: float = Field(
        ...,
        ge=0.0,
        le=200.0,
        description="Wind speed at 10 metres above ground in kilometres per hour (km/h)",
        examples=[12.4]
    )
    weather_code: int = Field(
        ...,
        ge=0,
        le=99,
        description="WMO Weather interpretation code (e.g., 0=Clear, 1-3=Cloudy, 51-67=Rain, 71-77=Snow)",
        examples=[1]
    )


class DemandPredictionResponse(BaseModel):
    """
    Output schema containing the predicted demand classification and diagnostic metadata.
    """
    predicted_class: str = Field(
        ...,
        description="Predicted demand level: 'HIGH' (surge of >= 2 calls) or 'NORMAL' (< 2 calls)"
    )
    probabilities: Dict[str, float] = Field(
        ...,
        description="Estimated class probabilities from the Random Forest model"
    )
    threshold_definition: str = Field(
        ...,
        description="Clinical definition of the predicted threshold"
    )
    probability_note: str = Field(
        ...,
        description="Important statistical caveat regarding model probability calibration"
    )
    input_features: Dict[str, Any] = Field(
        ...,
        description="Echo of the input features received for traceability and logging"
    )


# ---------------------------------------------------------------------------
# Dashboard Response Schemas
# ---------------------------------------------------------------------------
class DashboardSummaryResponse(BaseModel):
    total_calls: int = Field(..., description="Total historical EMS calls (sum of demand)")
    total_townships: int = Field(..., description="Number of distinct townships/zones")
    start_date: str = Field(..., description="Historical start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Historical end date (YYYY-MM-DD)")
    date_range_display: str = Field(..., description="Human-readable historical date span")
    busiest_hour: int = Field(..., description="Busiest hour of the day (0 to 23)")
    busiest_hour_label: str = Field(..., description="Formatted label for busiest hour (e.g. '10:00')")
    busiest_hour_calls: int = Field(..., description="Total historical demand in busiest hour")
    is_historical: bool = Field(True, description="Flag confirming historical dataset")


class HourlyPatternPoint(BaseModel):
    hour: int = Field(..., description="Hour of day (0 to 23)")
    label: str = Field(..., description="Formatted hour label (e.g. '00:00', '10:00')")
    demand: int = Field(..., description="Cumulative historical calls for this hour across all zones and dates")


class DashboardHourlyPatternResponse(BaseModel):
    hourly_values: List[int] = Field(..., description="List of 24 demand counts for hours 0 through 23")
    hourly_pattern: List[HourlyPatternPoint] = Field(..., description="24 hourly data points with labels")


class TopZoneItem(BaseModel):
    twp: str = Field(..., description="Township/zone name")
    call_count: int = Field(..., description="Total historical call count")
    total_demand: int = Field(..., description="Total historical call count (alias)")
    rank: int = Field(..., description="Rank from 1 to 5")


class DashboardTopZonesResponse(BaseModel):
    top_zones: List[TopZoneItem] = Field(..., description="Top 5 townships ranked by total historical demand")


class HotspotCell(BaseModel):
    cell_id: str = Field(..., description="Unique cell identifier based on rounded coordinates, e.g. '40.13_-75.41'")
    lat: float = Field(..., description="Cell centroid latitude (rounded to 2 decimal places)")
    lng: float = Field(..., description="Cell centroid longitude (rounded to 2 decimal places)")
    call_count: int = Field(..., description="Total cumulative historical EMS calls in this geographic cell")
    primary_township: str = Field(..., description="Predominant township or municipality recorded in this cell")
    start_date: str = Field(..., description="Earliest call date recorded in this cell")
    end_date: str = Field(..., description="Latest call date recorded in this cell")
    percentage_of_total: float = Field(..., description="Percentage of total historical EMS calls represented by this cell")
    relative_intensity: float = Field(..., description="Normalized call density (0.0 to 1.0) relative to maximum cell volume")
    rank: int = Field(..., description="1-based rank among all identified demand cells")


class HotspotSummaryMetadata(BaseModel):
    total_calls_analyzed: int
    valid_records_count: int
    excluded_records_count: int
    total_grid_cells_identified: int
    top_hotspots_returned: int
    start_date: str
    end_date: str
    rounding_precision: int
    approx_cell_dimensions: str
    coordinate_bounds: Dict[str, float]
    disclaimer: str


class DashboardHotspotsResponse(BaseModel):
    summary: HotspotSummaryMetadata
    hotspots: List[HotspotCell]


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.get(
    "/",
    summary="Project Welcome & System Status",
    tags=["General"]
)
def root():
    """
    Root endpoint returning project welcome message, API version, and documentation link.
    """
    return {
        "project": "AI-Based Emergency Ambulance Demand & Dispatch System",
        "message": "Welcome to the Ambulance Demand Prediction Backend API.",
        "status": "online",
        "version": "1.0.0",
        "model_loaded": model_pipeline is not None,
        "docs_url": "/docs",
        "health_check": "/health",
        "predict_endpoint": "/predict",
        "dashboard_summary": "/dashboard/summary",
        "dashboard_hourly_pattern": "/dashboard/hourly-pattern",
        "dashboard_top_zones": "/dashboard/top-zones",
        "dashboard_hotspots": "/dashboard/hotspots"
    }


@app.get(
    "/health",
    summary="Service & Model Health Check",
    tags=["General"]
)
def health_check():
    """
    Health check endpoint reporting model availability and pipeline details.
    """
    if model_pipeline is None:
        return {
            "status": "degraded",
            "model_loaded": False,
            "error": model_load_error or "Model is not loaded."
        }

    # Extract classifier details
    classifier_step = model_pipeline.named_steps.get("classifier")
    classifier_type = type(classifier_step).__name__ if classifier_step else "Unknown"
    classes_list = list(classifier_step.classes_) if hasattr(classifier_step, "classes_") else []

    return {
        "status": "healthy",
        "model_loaded": True,
        "model_path": str(MODEL_PATH.name),
        "model_type": classifier_type,
        "supported_classes": classes_list,
        "supports_predict_proba": hasattr(model_pipeline, "predict_proba")
    }


@app.post(
    "/predict",
    response_model=DemandPredictionResponse,
    summary="Predict Ambulance Demand Surge",
    tags=["Prediction"]
)
def predict_demand(request: DemandPredictionRequest):
    """
    Predicts whether a specified zone-hour will experience HIGH or NORMAL ambulance demand.
    
    - Validates inputs via Pydantic.
    - Transforms inputs using the fitted preprocessing pipeline (One-Hot Encoding & Scaling).
    - Returns the predicted class ('HIGH' or 'NORMAL') and estimated class probabilities.
    """
    global model_pipeline

    if model_pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Prediction model is currently unavailable. Reason: {model_load_error}"
        )

    # 1. Structure the input data exactly matching the model's expected column names
    input_data = {
        "twp": [request.twp.strip().upper()],
        "hour": [request.hour],
        "month": [request.month],
        "day_of_week": [request.day_of_week],
        "is_weekend": [request.is_weekend],
        "temperature_2m": [request.temperature_2m],
        "relative_humidity_2m": [request.relative_humidity_2m],
        "precipitation": [request.precipitation],
        "wind_speed_10m": [request.wind_speed_10m],
        "weather_code": [request.weather_code],
    }
    input_df = pd.DataFrame(input_data)

    try:
        # 2. Generate class prediction
        raw_pred = model_pipeline.predict(input_df)[0]

        # 3. Generate class probabilities if supported
        probabilities = {}
        if hasattr(model_pipeline, "predict_proba"):
            raw_probs = model_pipeline.predict_proba(input_df)[0]
            classifier_step = model_pipeline.named_steps.get("classifier")
            classes = classifier_step.classes_
            for cls_name, prob in zip(classes, raw_probs):
                probabilities[str(cls_name)] = round(float(prob), 4)

        return DemandPredictionResponse(
            predicted_class=str(raw_pred),
            probabilities=probabilities,
            threshold_definition="HIGH demand indicates >= 2 ambulance calls expected in this zone-hour; NORMAL indicates < 2 calls.",
            probability_note=(
                "Estimated class probabilities reflect internal decision tree voting ratios from the class-weighted "
                "Random Forest. They are raw model heuristics and are not guaranteed to be strictly calibrated probabilities."
            ),
            input_features=request.model_dump()
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while executing model inference: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Historical Dashboard Analytics Endpoints
# ---------------------------------------------------------------------------
@app.get(
    "/dashboard/summary",
    response_model=DashboardSummaryResponse,
    summary="Historical EMS Demand Summary Metrics",
    tags=["Dashboard"]
)
def get_dashboard_summary():
    """
    Returns high-level summary metrics of the historical EMS demand dataset:
    total calls (332,436), township count (69), temporal coverage range (2015-12-10 to 2020-07-29),
    and the busiest hour based on cumulative historical demand.
    """
    return get_dashboard_cache_data("summary")


@app.get(
    "/dashboard/hourly-pattern",
    response_model=DashboardHourlyPatternResponse,
    summary="24-Hour Cumulative Demand Distribution",
    tags=["Dashboard"]
)
def get_dashboard_hourly_pattern():
    """
    Returns 24 hourly values (from hour 0 through hour 23) representing the sum of
    historical demand across all dates and townships for each hour.
    """
    return get_dashboard_cache_data("hourly_pattern")


@app.get(
    "/dashboard/top-zones",
    response_model=DashboardTopZonesResponse,
    summary="Top 5 Townships by EMS Demand",
    tags=["Dashboard"]
)
def get_dashboard_top_zones():
    """
    Returns the top five townships ranked by total historical demand, including
    township names and cumulative call counts.
    """
    return get_dashboard_cache_data("top_zones")


@app.get(
    "/dashboard/hotspots",
    response_model=DashboardHotspotsResponse,
    summary="Historical EMS Demand Geographic Hotspots",
    tags=["Dashboard"]
)
def get_dashboard_hotspots(
    limit: int = Query(
        100,
        ge=10,
        le=500,
        description="Maximum number of top-volume geographic grid cells to return"
    )
):
    """
    Returns the highest-volume geographic grid cells across Montgomery County, PA,
    aggregated at 0.01-degree precision (~1.1 km x 0.85 km).
    Includes cell coordinates, call counts, primary township, and represented date span.
    """
    hotspots_data = get_dashboard_cache_data("hotspots_data")
    all_hotspots = hotspots_data.get("all_hotspots", hotspots_data.get("hotspots", []))
    sliced = all_hotspots[:max(1, min(limit, len(all_hotspots)))]

    meta = dict(hotspots_data["summary"])
    meta["top_hotspots_returned"] = len(sliced)

    return DashboardHotspotsResponse(
        summary=HotspotSummaryMetadata(**meta),
        hotspots=[HotspotCell(**cell) for cell in sliced]
    )


# ---------------------------------------------------------------------------
# Ambulance Allocation Recommendation Endpoint
# ---------------------------------------------------------------------------
@app.post(
    "/allocation/recommendations",
    response_model=AllocationRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Explainable Ambulance Allocation Recommendations",
    tags=["Allocation"]
)
def generate_allocation_recommendations(request: AllocationRecommendationRequest):
    """
    Accepts candidate sectors, their predicted demand scores, currently stationed
    ambulances, and the total unallocated reserve fleet. Computes an explainable,
    priority-based allocation without over-allocating or producing negative values.
    """
    try:
        return compute_allocation_recommendations(
            total_fleet_available=request.total_fleet_available,
            areas=request.areas
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while computing ambulance allocation recommendations: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Ambulance Route Planning Endpoints (A* Algorithm - Step 15)
# ---------------------------------------------------------------------------
@app.get(
    "/routes/nodes",
    response_model=List[NetworkNode],
    summary="Get All Available Road Network Graph Nodes",
    tags=["Route Planning"]
)
def get_routes_nodes():
    """
    Returns the list of all nodes in the sample emergency road network graph
    (EMS stations, hospital trauma centers, major highway interchanges, and response sectors).
    """
    return get_network_nodes_list()


@app.get(
    "/routes/graph",
    response_model=RoadNetworkGraphResponse,
    summary="Get Full Road Network Graph Topology",
    tags=["Route Planning"]
)
def get_routes_graph():
    """
    Returns all nodes, edges, segment distances, and data authenticity notices for
    the representative emergency dispatch road network.
    """
    return get_network_graph_metadata()


@app.post(
    "/routes/astar",
    response_model=AStarRouteResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Optimal Ambulance Route using A* Algorithm",
    tags=["Route Planning"]
)
def calculate_astar_route(request: AStarRouteRequest):
    """
    Calculates the shortest path between start_node and destination_node using
    the A* algorithm with an admissible Haversine straight-line distance heuristic.

    Validations:
    - Returns HTTP 400 if start or destination node is invalid / not found.
    - Returns HTTP 404 if the destination is unreachable from the start node.
    """
    try:
        return find_astar_route(
            start_node=request.start_node,
            destination_node=request.destination_node,
            raise_if_unreachable=True
        )
    except NodeNotFoundError as nfe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(nfe)
        )
    except UnreachableDestinationError as ude:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ude)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while calculating route via A*: {str(e)}"
        )


@app.post(
    "/routes/road",
    response_model=RoadRouteResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Drivable Road Route via OpenStreetMap / OSRM",
    tags=["Route Planning"]
)
def calculate_road_route(request: RoadRouteRequest):
    """
    Retrieves actual road centerline geometry, drivable distance, and estimated travel duration
    between starting coordinates and destination coordinates using the Open Source Routing Machine
    (OSRM) with OpenStreetMap road data.
    """
    try:
        return fetch_osrm_road_route(
            start_lat=request.start_lat,
            start_lng=request.start_lng,
            dest_lat=request.dest_lat,
            dest_lng=request.dest_lng,
            start_name=request.start_name or "Starting Location",
            dest_name=request.dest_name or "Destination",
        )
    except RoutingServiceError as rse:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(rse)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving the road route: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Integrated Dispatch Planning Endpoint (Step 16)
# ---------------------------------------------------------------------------
@app.post(
    "/dispatch/integrated-plan",
    response_model=IntegratedDispatchPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Integrated Demand Prediction & Fleet Allocation Plan",
    tags=["Integrated Dispatch"]
)
def generate_dispatch_plan(request: IntegratedDispatchPlanRequest):
    """
    Executes an end-to-end integrated dispatch planning cycle:
    1. Evaluates ML demand classification (HIGH/NORMAL + probabilities) for all input sectors.
    2. Derives operational demand scores and allocates available reserve fleet.
    3. Optionally computes optimal A* route between chosen dispatch waypoints.
    4. Enforces strict fleet non-over-allocation and non-negative constraints with transparent reasoning.
    """
    global model_pipeline

    if model_pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Prediction model is unavailable: {model_load_error}"
        )

    try:
        return generate_integrated_dispatch_plan(
            request=request,
            model_pipeline=model_pipeline
        )
    except (ValueError, KeyError, NodeNotFoundError) as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating the integrated dispatch plan: {str(e)}"
        )


# ---------------------------------------------------------------------------
# ML Model Evaluation Endpoints (Step 17)
# ---------------------------------------------------------------------------
@app.get(
    "/evaluation/models",
    response_model=ModelEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get ML Model Evaluation & Architecture Comparison",
    tags=["Model Evaluation"]
)
def get_model_evaluation_summary():
    """
    Returns empirical evaluation results comparing all 4 classification models:
    - Majority-Class Baseline
    - KNN (k=5, Distance-Weighted)
    - Random Forest (Class-Weighted Candidate)
    - HistGradientBoosting (Class-Weighted)
    
    Includes accuracy, balanced accuracy, HIGH precision, HIGH recall, HIGH F1-score,
    exact 2x2 confusion matrix counts, and trade-off educational guidance.
    """
    return get_model_evaluations()


@app.get(
    "/evaluation/models/{model_id}",
    response_model=ModelMetricsItem,
    status_code=status.HTTP_200_OK,
    summary="Get Specific Model Evaluation Details",
    tags=["Model Evaluation"]
)
def get_model_evaluation_detail(model_id: str):
    """
    Returns detailed evaluation metrics and confusion matrix for a specific model:
    - majority_baseline
    - knn
    - random_forest
    - hist_gradient_boosting
    """
    model = get_single_model_evaluation(model_id)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model identifier '{model_id}' not found. Available models: majority_baseline, knn, random_forest, hist_gradient_boosting.",
        )
    return model



