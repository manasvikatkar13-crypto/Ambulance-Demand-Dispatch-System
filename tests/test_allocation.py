"""
Unit tests for the Ambulance Allocation Recommendation Engine (Step 14).

Covers:
- Zero available reserve ambulances
- More candidate areas than available ambulances
- Priority handling for high-demand areas with coverage deficits
- Preventing over-allocation and negative allocations under all conditions
- Distinction between existing stationed units and recommended additional units
- Validation errors for invalid/negative inputs and empty area lists
- Live HTTP endpoint integration testing with Python standard library urllib
"""

import unittest
import json
import urllib.request
import urllib.error
from pydantic import ValidationError

from api.allocation import (
    AreaAllocationInput,
    AllocationRecommendationRequest,
    compute_allocation_recommendations,
)


class TestAmbulanceAllocationEngine(unittest.TestCase):
    def setUp(self):
        self.sample_areas = [
            AreaAllocationInput(area_name="NORRISTOWN", predicted_demand=4.0, current_ambulances=1),
            AreaAllocationInput(area_name="LOWER PROVIDENCE", predicted_demand=3.0, current_ambulances=0),
            AreaAllocationInput(area_name="POTTSTOWN", predicted_demand=2.0, current_ambulances=2),
            AreaAllocationInput(area_name="CHELTENHAM", predicted_demand=1.5, current_ambulances=1),
            AreaAllocationInput(area_name="UPPER MERION", predicted_demand=0.0, current_ambulances=1),
        ]

    def test_zero_available_ambulances(self):
        """When total_fleet_available is 0, zero additional ambulances should be allocated."""
        resp = compute_allocation_recommendations(
            total_fleet_available=0,
            areas=self.sample_areas
        )
        self.assertEqual(resp.summary.total_fleet_available, 0)
        self.assertEqual(resp.summary.total_allocated, 0)
        self.assertEqual(resp.summary.unallocated_reserve, 0)
        for r in resp.recommendations:
            self.assertEqual(r.recommended_additional, 0)
            self.assertEqual(r.final_total_ambulances, r.current_ambulances)
            self.assertIn("0", r.reason)

    def test_more_areas_than_available_ambulances(self):
        """When fleet is smaller than the number of areas, prioritize highest deficits."""
        resp = compute_allocation_recommendations(
            total_fleet_available=2,
            areas=self.sample_areas
        )
        self.assertEqual(resp.summary.total_allocated, 2)
        self.assertEqual(resp.summary.unallocated_reserve, 0)
        total_recommended = sum(r.recommended_additional for r in resp.recommendations)
        self.assertEqual(total_recommended, 2)

        # The 2 units should go to highest deficit areas (NORRISTOWN or LOWER PROVIDENCE)
        top_areas = {r.area_name: r.recommended_additional for r in resp.recommendations}
        self.assertGreater(top_areas["NORRISTOWN"] + top_areas["LOWER PROVIDENCE"], 0)
        self.assertEqual(top_areas["UPPER MERION"], 0)
        self.assertEqual(top_areas["POTTSTOWN"], 0)

    def test_high_demand_priority(self):
        """High-demand deficit areas should receive more units than low-demand areas."""
        areas = [
            AreaAllocationInput(area_name="SURGE_ZONE", predicted_demand=6.0, current_ambulances=1),  # deficit 5
            AreaAllocationInput(area_name="MODERATE_ZONE", predicted_demand=2.0, current_ambulances=1),  # deficit 1
            AreaAllocationInput(area_name="QUIET_ZONE", predicted_demand=0.5, current_ambulances=1),  # deficit 0
        ]
        resp = compute_allocation_recommendations(total_fleet_available=4, areas=areas)
        rec_map = {r.area_name: r.recommended_additional for r in resp.recommendations}

        # Surge zone should get the highest allocation
        self.assertGreater(rec_map["SURGE_ZONE"], rec_map["MODERATE_ZONE"])
        self.assertEqual(rec_map["QUIET_ZONE"], 0)
        self.assertLessEqual(sum(rec_map.values()), 4)

    def test_allocations_never_exceed_available_fleet(self):
        """Check across multiple fleet scales that allocations never exceed available units."""
        for fleet_size in [1, 3, 5, 10, 50]:
            resp = compute_allocation_recommendations(
                total_fleet_available=fleet_size,
                areas=self.sample_areas
            )
            total_rec = sum(r.recommended_additional for r in resp.recommendations)
            self.assertLessEqual(total_rec, fleet_size)
            self.assertEqual(resp.summary.total_allocated, total_rec)
            self.assertEqual(resp.summary.unallocated_reserve, fleet_size - total_rec)
            for r in resp.recommendations:
                self.assertGreaterEqual(r.recommended_additional, 0)
                self.assertEqual(r.final_total_ambulances, r.current_ambulances + r.recommended_additional)

    def test_negative_fleet_raises_value_error(self):
        """Negative total available fleet must raise ValueError."""
        with self.assertRaises(ValueError):
            compute_allocation_recommendations(total_fleet_available=-3, areas=self.sample_areas)

    def test_empty_areas_raises_value_error(self):
        """Empty list of areas must raise ValueError."""
        with self.assertRaises(ValueError):
            compute_allocation_recommendations(total_fleet_available=5, areas=[])

    def test_negative_area_inputs_rejected_by_pydantic(self):
        """Pydantic validation should reject negative demand and negative current ambulances."""
        with self.assertRaises(ValidationError):
            AreaAllocationInput(area_name="TEST", predicted_demand=-2.5, current_ambulances=1)

        with self.assertRaises(ValidationError):
            AreaAllocationInput(area_name="TEST", predicted_demand=2.0, current_ambulances=-1)

        with self.assertRaises(ValidationError):
            AreaAllocationInput(area_name="   ", predicted_demand=2.0, current_ambulances=1)

    def test_existing_ambulances_distinct_from_recommended(self):
        """Existing ambulances must remain untouched and clearly distinguished from new additions."""
        resp = compute_allocation_recommendations(
            total_fleet_available=3,
            areas=self.sample_areas
        )
        for r in resp.recommendations:
            orig = next(a for a in self.sample_areas if a.area_name == r.area_name)
            self.assertEqual(r.current_ambulances, orig.current_ambulances)
            self.assertEqual(r.final_total_ambulances, orig.current_ambulances + r.recommended_additional)

    def test_zero_demand_areas_do_not_drain_reserve(self):
        """Areas with zero demand must not consume ambulances if deficit areas exist."""
        areas = [
            AreaAllocationInput(area_name="ZERO_DEMAND", predicted_demand=0.0, current_ambulances=0),
            AreaAllocationInput(area_name="ACTIVE_DEMAND", predicted_demand=2.0, current_ambulances=0),
        ]
        resp = compute_allocation_recommendations(total_fleet_available=2, areas=areas)
        rec_map = {r.area_name: r.recommended_additional for r in resp.recommendations}
        self.assertEqual(rec_map["ZERO_DEMAND"], 0)
        self.assertEqual(rec_map["ACTIVE_DEMAND"], 2)


class TestAllocationFastAPIEndpoint(unittest.TestCase):
    API_URL = "http://127.0.0.1:8000/allocation/recommendations"

    def _make_request(self, payload):
        req = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_post_recommendations_success(self):
        """Test HTTP POST /allocation/recommendations with valid payload."""
        payload = {
            "total_fleet_available": 5,
            "areas": [
                {"area_name": "NORRISTOWN", "predicted_demand": 3.5, "current_ambulances": 1},
                {"area_name": "LOWER PROVIDENCE", "predicted_demand": 2.5, "current_ambulances": 0},
                {"area_name": "POTTSTOWN", "predicted_demand": 1.0, "current_ambulances": 1},
            ]
        }
        status_code, data = self._make_request(payload)
        self.assertEqual(status_code, 200)
        self.assertIn("summary", data)
        self.assertIn("recommendations", data)
        self.assertIn("algorithm_metadata", data)
        self.assertIn("disclaimer", data)
        self.assertEqual(data["summary"]["total_fleet_available"], 5)
        self.assertEqual(len(data["recommendations"]), 3)

    def test_post_recommendations_negative_fleet_422(self):
        """Test HTTP POST /allocation/recommendations with negative fleet."""
        payload = {
            "total_fleet_available": -5,
            "areas": [
                {"area_name": "NORRISTOWN", "predicted_demand": 2.0, "current_ambulances": 1}
            ]
        }
        status_code, data = self._make_request(payload)
        self.assertEqual(status_code, 422)

    def test_post_recommendations_empty_areas_422(self):
        """Test HTTP POST /allocation/recommendations with empty areas array."""
        payload = {
            "total_fleet_available": 5,
            "areas": []
        }
        status_code, data = self._make_request(payload)
        self.assertEqual(status_code, 422)


if __name__ == "__main__":
    unittest.main()
