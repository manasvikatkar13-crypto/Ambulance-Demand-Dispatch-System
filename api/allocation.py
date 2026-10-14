"""
AI-Based Emergency Ambulance Demand & Dispatch System
Ambulance Allocation Recommendation Engine

This module implements the decision-support resource allocation algorithm for Step 14.
It prioritizes candidate sectors according to predicted emergency demand, calculates
unmet coverage deficits against existing stationed ambulances, and greedily assigns
discrete units from the available reserve fleet without ever over-allocating or
producing negative values.

DISCLAIMER:
Academic capstone decision-support prototype. Recommendations are mathematical
planning suggestions based strictly on supplied inputs and do not denote live
911 dispatch, CAD telecommunications, or real-time GPS locations.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class AreaAllocationInput(BaseModel):
    area_name: str = Field(..., min_length=1, max_length=100, description="Name of the township or patrol sector")
    predicted_demand: float = Field(..., ge=0.0, description="Predicted demand score or expected call count (>= 0)")
    current_ambulances: int = Field(..., ge=0, description="Number of currently stationed/available ambulances in this area (>= 0)")

    @field_validator("area_name")
    @classmethod
    def validate_area_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Area name cannot be empty or whitespace only")
        return trimmed


class AllocationRecommendationRequest(BaseModel):
    total_fleet_available: int = Field(
        ...,
        ge=0,
        description="Total number of available unallocated ambulances in reserve fleet (>= 0)"
    )
    areas: List[AreaAllocationInput] = Field(
        ...,
        min_length=1,
        description="List of areas requiring allocation evaluation"
    )


class AreaAllocationResult(BaseModel):
    area_name: str
    predicted_demand: float
    current_ambulances: int
    recommended_additional: int
    final_total_ambulances: int
    coverage_status: str
    priority_rank: int
    initial_deficit: float
    reason: str


class AllocationSummary(BaseModel):
    total_fleet_available: int
    total_allocated: int
    unallocated_reserve: int
    total_areas_evaluated: int
    areas_with_deficit: int
    areas_fully_covered: int
    system_coverage_rate: float
    overall_system_status: str


class AllocationRecommendationResponse(BaseModel):
    summary: AllocationSummary
    recommendations: List[AreaAllocationResult]
    algorithm_metadata: Dict[str, Any]
    disclaimer: str


def compute_allocation_recommendations(
    total_fleet_available: int,
    areas: List[AreaAllocationInput]
) -> AllocationRecommendationResponse:
    """
    Computes explainable, priority-based ambulance allocations across evaluated areas.

    Algorithm:
    1. Validates inputs to ensure non-negative fleet and area inputs.
    2. Identifies initial coverage deficits: max(0, predicted_demand - current_ambulances).
    3. Iteratively allocates available reserve units one by one to the area with the
       highest marginal need (prioritizing uncovered demand first, then high-demand buffer).
    4. Ensures total allocated <= total_fleet_available and recommended_additional >= 0.
    5. Formulates human-readable reasons explaining each area's recommendation.
    """
    if total_fleet_available < 0:
        raise ValueError("Total available ambulances cannot be negative.")
    if not areas:
        raise ValueError("At least one area must be provided for allocation.")

    n = len(areas)

    # Prepare tracking state for each area
    current_state = []
    for i, area in enumerate(areas):
        demand = round(float(area.predicted_demand), 2)
        current = int(area.current_ambulances)
        initial_deficit = max(0.0, round(demand - current, 2))
        current_state.append({
            "index": i,
            "area_name": area.area_name,
            "predicted_demand": demand,
            "current_ambulances": current,
            "recommended_additional": 0,
            "initial_deficit": initial_deficit,
        })

    remaining_fleet = int(total_fleet_available)

    # Discrete marginal allocation loop
    while remaining_fleet > 0:
        best_idx = None
        best_score = -1e9

        for item in current_state:
            demand = item["predicted_demand"]
            coverage = item["current_ambulances"] + item["recommended_additional"]
            deficit = demand - coverage

            # Priority 1: Unmet deficit (demand > prospective coverage)
            if deficit > 0:
                score = 1000.0 * deficit + 10.0 * (demand / (coverage + 1.0))
            # Priority 2: Demand is met, but area has active demand and could receive a surge buffer
            elif demand > 0:
                score = 1.0 * (demand / (coverage + 1.0))
            # Zero demand and already non-negative coverage
            else:
                score = 0.0

            if score > best_score and score > 0.0:
                best_score = score
                best_idx = item["index"]
            elif abs(score - best_score) < 1e-6 and best_idx is not None and score > 0.0:
                # Deterministic tie-breaking: lower total coverage, higher demand, then alphabetical
                curr_best = current_state[best_idx]
                curr_best_cov = curr_best["current_ambulances"] + curr_best["recommended_additional"]
                this_cov = item["current_ambulances"] + item["recommended_additional"]
                if this_cov < curr_best_cov:
                    best_idx = item["index"]
                elif this_cov == curr_best_cov and item["predicted_demand"] > curr_best["predicted_demand"]:
                    best_idx = item["index"]
                elif (
                    this_cov == curr_best_cov
                    and item["predicted_demand"] == curr_best["predicted_demand"]
                    and item["area_name"] < curr_best["area_name"]
                ):
                    best_idx = item["index"]

        # If no area has positive score (e.g. all areas have zero demand), stop
        if best_idx is None:
            break

        current_state[best_idx]["recommended_additional"] += 1
        remaining_fleet -= 1

    total_allocated = total_fleet_available - remaining_fleet
    unallocated_reserve = remaining_fleet

    # Generate results and human-readable justifications
    results: List[AreaAllocationResult] = []
    areas_with_initial_deficit = sum(1 for item in current_state if item["initial_deficit"] > 0)
    areas_fully_covered = 0

    # Sort results for display: largest initial deficit first, then highest demand, then alphabetical
    sorted_items = sorted(
        current_state,
        key=lambda x: (
            -x["initial_deficit"],
            -(x["predicted_demand"]),
            x["area_name"]
        )
    )

    for rank, item in enumerate(sorted_items, start=1):
        demand = item["predicted_demand"]
        current = item["current_ambulances"]
        added = item["recommended_additional"]
        final_cov = current + added
        initial_def = item["initial_deficit"]
        remaining_gap = max(0.0, round(demand - final_cov, 2))

        if final_cov >= demand:
            areas_fully_covered += 1

        # Synthesize clear, transparent reason
        if total_fleet_available == 0:
            if initial_def > 0:
                status_str = "Unmet Deficit"
                reason = (
                    f"Predicted demand of {demand:.1f} calls exceeds existing coverage of {current} "
                    f"by {initial_def:.1f} calls. No additional ambulances were allocated because 0 reserve units were available."
                )
            elif demand == 0:
                status_str = "Zero Demand"
                reason = "Predicted demand is 0.0 calls. Existing resources are adequate with 0 reserve units available."
            else:
                status_str = "Adequate Coverage"
                reason = (
                    f"Existing coverage ({current} ambulances) already meets or exceeds predicted demand of {demand:.1f} calls. "
                    "No additional units required."
                )
        elif initial_def > 0:
            if final_cov >= demand:
                status_str = "Deficit Covered"
                reason = (
                    f"Allocated {added} additional ambulance{'s' if added > 1 else ''} to close the initial deficit of "
                    f"{initial_def:.1f} (predicted demand {demand:.1f} vs {current} existing). Final coverage: {final_cov} units."
                )
            elif added > 0:
                status_str = "Partial Deficit"
                reason = (
                    f"Allocated {added} additional ambulance{'s' if added > 1 else ''} toward initial deficit of {initial_def:.1f}. "
                    f"A gap of {remaining_gap:.1f} calls remains due to limited reserve fleet capacity."
                )
            else:
                status_str = "Unmet Deficit"
                reason = (
                    f"Identified initial deficit of {initial_def:.1f} calls (demand {demand:.1f} vs {current} existing), "
                    "but available reserve units were exhausted by higher-priority deficit areas."
                )
        elif demand > 0:
            if added > 0:
                status_str = "Surge Buffer"
                reason = (
                    f"Existing coverage ({current} units) covered baseline demand ({demand:.1f} calls). "
                    f"Allocated {added} additional buffer unit{'s' if added > 1 else ''} to absorb potential surge volatility."
                )
            else:
                status_str = "Adequate Coverage"
                reason = (
                    f"Existing coverage of {current} ambulance{'s' if current > 1 else ''} already satisfies predicted demand of "
                    f"{demand:.1f} calls. Fleet capacity was prioritized for deficit zones."
                )
        else:
            status_str = "Zero Demand"
            reason = "Predicted demand is 0.0 calls. Existing resources are sufficient; no additional ambulances required."

        results.append(AreaAllocationResult(
            area_name=item["area_name"],
            predicted_demand=demand,
            current_ambulances=current,
            recommended_additional=added,
            final_total_ambulances=final_cov,
            coverage_status=status_str,
            priority_rank=rank,
            initial_deficit=initial_def,
            reason=reason
        ))

    total_demand = sum(a.predicted_demand for a in areas)
    total_final_units = sum(r.final_total_ambulances for r in results)
    coverage_rate = round(min(100.0, (total_final_units / total_demand * 100.0)) if total_demand > 0 else 100.0, 1)

    if total_fleet_available == 0:
        overall_status = "Zero Reserve Deployed — Baseline Stationed Units Only"
    elif unallocated_reserve > 0:
        overall_status = f"Deficits Resolved with {unallocated_reserve} Unit{'s' if unallocated_reserve > 1 else ''} Remaining in Central Reserve"
    elif areas_fully_covered == n:
        overall_status = "All Evaluated Areas Fully Covered by Stationed + Recommended Fleet"
    else:
        overall_status = f"Reserve Fleet Fully Deployed ({total_allocated} Units); Priority Deficits Addressed"

    summary = AllocationSummary(
        total_fleet_available=total_fleet_available,
        total_allocated=total_allocated,
        unallocated_reserve=unallocated_reserve,
        total_areas_evaluated=n,
        areas_with_deficit=areas_with_initial_deficit,
        areas_fully_covered=areas_fully_covered,
        system_coverage_rate=coverage_rate,
        overall_system_status=overall_status
    )

    metadata = {
        "algorithm": "Greedy Marginal Deficit Allocation (Discrete Apportionment)",
        "priority_criteria": [
            "1. Coverage Deficit (predicted_demand - current_ambulances > 0)",
            "2. Unmet demand magnitude and inverse coverage ratio",
            "3. High-demand surge resilience buffer",
            "4. Central reserve preservation when no active demand exists"
        ],
        "constraints_guaranteed": [
            "recommended_additional >= 0 (no negative allocations)",
            "sum(recommended_additional) <= total_fleet_available (no fleet over-allocation)",
            "deterministic and explainable unit-by-unit justifications"
        ]
    }

    disclaimer = (
        "Academic decision-support prototype demonstration for simulated emergency planning. "
        "Recommendations are mathematical optimization suggestions based exclusively on the provided inputs "
        "and do not replace CAD dispatch software, telecommunicators, or live emergency telemetry."
    )

    return AllocationRecommendationResponse(
        summary=summary,
        recommendations=results,
        algorithm_metadata=metadata,
        disclaimer=disclaimer
    )
