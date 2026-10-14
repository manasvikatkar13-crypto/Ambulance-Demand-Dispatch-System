"""
AI-Based Emergency Ambulance Demand & Dispatch System
Integrated Dispatch Planning Module (Step 16)

Integrates:
1. ML Demand Surge Prediction (Random Forest classifier pipeline)
2. Priority-Based Ambulance Fleet Allocation (Greedy marginal deficit algorithm)
3. Emergency Route Planning (A* search with Haversine heuristic)

DISCLAIMER:
Academic decision-support prototype demonstration using historical data,
user-supplied parameters, and a representative sample road graph. Does not
track live emergency calls, active GPS telemetry, or computer-aided dispatch (CAD) queues.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
from pydantic import BaseModel, Field

from api.allocation import (
    AreaAllocationInput,
    compute_allocation_recommendations,
)
from api.routing import (
    AStarRouteRequest,
    AStarRouteResponse,
    find_astar_route,
)


class IntegratedSectorInput(BaseModel):
    twp: str = Field(..., min_length=1, max_length=100, description="Township or municipality name")
    hour: int = Field(..., ge=0, le=23, description="Hour of the day (0 to 23)")
    month: int = Field(..., ge=1, le=12, description="Month of the year (1 to 12)")
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Mon, 6=Sun)")
    is_weekend: int = Field(..., ge=0, le=1, description="1 if weekend else 0")
    temperature_2m: float = Field(..., ge=-50.0, le=60.0, description="Temperature in °C")
    relative_humidity_2m: float = Field(..., ge=0.0, le=100.0, description="Relative humidity %")
    precipitation: float = Field(..., ge=0.0, le=500.0, description="Precipitation in mm")
    wind_speed_10m: float = Field(..., ge=0.0, le=200.0, description="Wind speed in km/h")
    weather_code: int = Field(..., ge=0, le=99, description="WMO weather code")
    current_ambulances: int = Field(..., ge=0, description="Currently stationed ambulances in this sector (>= 0)")


class IntegratedSectorResult(BaseModel):
    area_name: str
    predicted_class: str
    high_probability: float
    probabilities: Dict[str, float]
    expected_demand_score: float
    current_ambulances: int
    recommended_additional: int
    final_total_ambulances: int
    coverage_status: str
    priority_rank: int
    reason: str


class IntegratedDispatchSummary(BaseModel):
    total_fleet_available: int
    total_allocated: int
    unallocated_reserve: int
    total_sectors_evaluated: int
    high_demand_sectors_count: int
    normal_demand_sectors_count: int
    sectors_with_deficit: int
    sectors_fully_covered: int
    system_coverage_rate: float
    system_status: str


class IntegratedDispatchPlanRequest(BaseModel):
    total_fleet_available: int = Field(..., ge=0, description="Total unallocated reserve fleet available (>= 0)")
    sectors: List[IntegratedSectorInput] = Field(..., min_length=1, description="List of sectors to evaluate")
    route_request: Optional[AStarRouteRequest] = Field(None, description="Optional origin & destination for A* route planning")


class IntegratedDispatchPlanResponse(BaseModel):
    summary: IntegratedDispatchSummary
    sectors: List[IntegratedSectorResult]
    route_result: Optional[AStarRouteResponse]
    decision_explanation: str
    algorithm_metadata: Dict[str, Any]
    disclaimer: str


def generate_integrated_dispatch_plan(
    request: IntegratedDispatchPlanRequest,
    model_pipeline: Any,
    road_graph: Optional[Dict[str, Any]] = None,
) -> IntegratedDispatchPlanResponse:
    """
    Executes the integrated dispatch planning pipeline:
    1. Runs ML predictions (HIGH/NORMAL + probabilities) for all input sectors.
    2. Translates class predictions and probabilities into operational demand scores.
    3. Feeds demand scores and stationed fleet into the greedy allocation algorithm.
    4. Optionally solves A* route planning on the sample road network.
    5. Returns unified dispatch plan with explainable justifications.
    """
    if model_pipeline is None:
        raise ValueError("ML prediction model pipeline is currently unavailable.")

    # 1. Run predictions for each sector using the fitted pipeline
    sector_predictions = []
    allocation_inputs = []

    for s in request.sectors:
        twp_clean = s.twp.strip().upper()
        df = pd.DataFrame({
            "twp": [twp_clean],
            "hour": [s.hour],
            "month": [s.month],
            "day_of_week": [s.day_of_week],
            "is_weekend": [s.is_weekend],
            "temperature_2m": [s.temperature_2m],
            "relative_humidity_2m": [s.relative_humidity_2m],
            "precipitation": [s.precipitation],
            "wind_speed_10m": [s.wind_speed_10m],
            "weather_code": [s.weather_code],
        })

        pred_class = str(model_pipeline.predict(df)[0])
        probs: Dict[str, float] = {}
        high_prob = 0.5
        if hasattr(model_pipeline, "predict_proba"):
            raw_probs = model_pipeline.predict_proba(df)[0]
            classifier_step = model_pipeline.named_steps.get("classifier")
            classes = classifier_step.classes_
            for cls_name, p in zip(classes, raw_probs):
                probs[str(cls_name)] = round(float(p), 4)
            high_prob = probs.get("HIGH", 0.0)

        # Operational demand derivation:
        # HIGH demand is defined as >= 2 calls in a township-hour.
        # Scale demand with surge probability for fine-grained resource prioritization.
        if pred_class == "HIGH":
            expected_demand = round(2.0 + (high_prob * 2.0), 1)
        else:
            expected_demand = round(max(0.3, high_prob * 1.5), 1)

        sector_predictions.append({
            "area_name": twp_clean,
            "predicted_class": pred_class,
            "high_probability": high_prob,
            "probabilities": probs,
            "expected_demand_score": expected_demand,
            "current_ambulances": s.current_ambulances,
        })

        allocation_inputs.append(
            AreaAllocationInput(
                area_name=twp_clean,
                predicted_demand=expected_demand,
                current_ambulances=s.current_ambulances,
            )
        )

    # 2. Run allocation algorithm with the derived demands and current coverage
    alloc_resp = compute_allocation_recommendations(
        total_fleet_available=request.total_fleet_available,
        areas=allocation_inputs,
    )

    # Merge prediction metrics with allocation recommendations
    pred_map = {p["area_name"]: p for p in sector_predictions}
    sector_results: List[IntegratedSectorResult] = []

    for rec in alloc_resp.recommendations:
        p_info = pred_map.get(rec.area_name, {})
        sector_results.append(
            IntegratedSectorResult(
                area_name=rec.area_name,
                predicted_class=p_info.get("predicted_class", "NORMAL"),
                high_probability=p_info.get("high_probability", 0.0),
                probabilities=p_info.get("probabilities", {}),
                expected_demand_score=rec.predicted_demand,
                current_ambulances=rec.current_ambulances,
                recommended_additional=rec.recommended_additional,
                final_total_ambulances=rec.final_total_ambulances,
                coverage_status=rec.coverage_status,
                priority_rank=rec.priority_rank,
                reason=rec.reason,
            )
        )

    # 3. If route planning was requested, execute A* pathfinding
    route_result: Optional[AStarRouteResponse] = None
    if request.route_request:
        route_result = find_astar_route(
            start_node=request.route_request.start_node,
            destination_node=request.route_request.destination_node,
            graph=road_graph,
            raise_if_unreachable=False,
        )

    # 4. Synthesize overall explanation and summary
    high_count = sum(1 for s in sector_predictions if s["predicted_class"] == "HIGH")
    normal_count = len(sector_predictions) - high_count

    explanation = (
        f"Evaluated {len(sector_predictions)} candidate sectors: {high_count} predicted HIGH demand (>= 2 calls), "
        f"{normal_count} predicted NORMAL demand (< 2 calls). Allocated {alloc_resp.summary.total_allocated} "
        f"reserve ambulances out of {request.total_fleet_available} available units strictly prioritizing coverage deficits. "
    )
    if alloc_resp.summary.unallocated_reserve > 0:
        explanation += f"{alloc_resp.summary.unallocated_reserve} units remain in central reserve buffer. "
    if route_result and route_result.found:
        explanation += f"A* identified optimal transit route ({route_result.total_cost_km} km) via {len(route_result.path) - 1} road segments."
    elif route_result and not route_result.found:
        explanation += "Requested route destination was unreachable on sample road graph."

    summary = IntegratedDispatchSummary(
        total_fleet_available=alloc_resp.summary.total_fleet_available,
        total_allocated=alloc_resp.summary.total_allocated,
        unallocated_reserve=alloc_resp.summary.unallocated_reserve,
        total_sectors_evaluated=alloc_resp.summary.total_areas_evaluated,
        high_demand_sectors_count=high_count,
        normal_demand_sectors_count=normal_count,
        sectors_with_deficit=alloc_resp.summary.areas_with_deficit,
        sectors_fully_covered=alloc_resp.summary.areas_fully_covered,
        system_coverage_rate=alloc_resp.summary.system_coverage_rate,
        system_status=alloc_resp.summary.overall_system_status,
    )

    metadata = {
        "pipeline_integrated": True,
        "prediction_model": "Random Forest Class-Weighted Classifier",
        "allocation_algorithm": alloc_resp.algorithm_metadata.get("algorithm"),
        "routing_algorithm": "A* Pathfinding (Haversine Admissible Heuristic)",
    }

    disclaimer = (
        "Academic decision-support prototype demonstration using historical EMS data, "
        "user-supplied inputs, and a representative sample routing graph. Does not reflect "
        "live 911 emergency calls, real-world traffic, or actual ambulance GPS telemetry."
    )

    return IntegratedDispatchPlanResponse(
        summary=summary,
        sectors=sector_results,
        route_result=route_result,
        decision_explanation=explanation,
        algorithm_metadata=metadata,
        disclaimer=disclaimer,
    )
