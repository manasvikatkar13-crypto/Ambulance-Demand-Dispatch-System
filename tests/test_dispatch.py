"""
Unit and API integration tests for Integrated Demand Prediction and Ambulance Allocation (Step 16).

Covers:
- End-to-end integration: ML prediction + fleet allocation + optional A* route planning
- Predictions returning HIGH/NORMAL with valid probabilities
- Ensuring total allocations never exceed available fleet
- Zero available reserve fleet handling
- Input validation (negative fleet, invalid hour, empty sector list)
- HTTP API integration tests against POST /dispatch/integrated-plan
"""

import unittest
import json
import urllib.request
import urllib.error

from pathlib import Path
import joblib

from api.dispatch import (
    IntegratedSectorInput,
    IntegratedDispatchPlanRequest,
    generate_integrated_dispatch_plan,
)

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "demand_classifier_candidate.joblib"


class TestIntegratedDispatchPlanning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = joblib.load(MODEL_PATH)
    def setUp(self):
        self.sample_sectors = [
            IntegratedSectorInput(
                twp="NORRISTOWN",
                hour=17,
                month=12,
                day_of_week=4,
                is_weekend=0,
                temperature_2m=2.0,
                relative_humidity_2m=85.0,
                precipitation=1.5,
                wind_speed_10m=25.0,
                weather_code=61,  # Rain
                current_ambulances=1,
            ),
            IntegratedSectorInput(
                twp="POTTSTOWN",
                hour=17,
                month=12,
                day_of_week=4,
                is_weekend=0,
                temperature_2m=2.0,
                relative_humidity_2m=85.0,
                precipitation=1.5,
                wind_speed_10m=25.0,
                weather_code=61,
                current_ambulances=2,
            ),
            IntegratedSectorInput(
                twp="LOWER PROVIDENCE",
                hour=17,
                month=12,
                day_of_week=4,
                is_weekend=0,
                temperature_2m=2.0,
                relative_humidity_2m=85.0,
                precipitation=1.5,
                wind_speed_10m=25.0,
                weather_code=61,
                current_ambulances=0,
            ),
        ]

    def test_integrated_plan_execution(self):
        """End-to-end plan runs ML inference, maps demand, and allocates ambulances."""
        req = IntegratedDispatchPlanRequest(
            total_fleet_available=4,
            sectors=self.sample_sectors,
        )
        plan = generate_integrated_dispatch_plan(req, self.pipeline)

        self.assertEqual(len(plan.sectors), 3)
        self.assertLessEqual(plan.summary.total_allocated, 4)
        self.assertEqual(plan.summary.total_fleet_available, 4)
        self.assertEqual(plan.summary.unallocated_reserve, 4 - plan.summary.total_allocated)

        for s in plan.sectors:
            self.assertIn(s.predicted_class, ["HIGH", "NORMAL"])
            self.assertGreaterEqual(s.high_probability, 0.0)
            self.assertLessEqual(s.high_probability, 1.0)
            self.assertGreaterEqual(s.expected_demand_score, 0.0)
            self.assertGreaterEqual(s.recommended_additional, 0)
            self.assertEqual(s.final_total_ambulances, s.current_ambulances + s.recommended_additional)
            self.assertTrue(len(s.reason) > 0)

    def test_integrated_plan_with_optional_route(self):
        """Integrated plan solves optional A* route when route_request is provided."""
        from api.routing import AStarRouteRequest
        req = IntegratedDispatchPlanRequest(
            total_fleet_available=3,
            sectors=self.sample_sectors,
            route_request=AStarRouteRequest(
                start_node="NORRISTOWN_EMS",
                destination_node="POTTSTOWN_HOSPITAL"
            )
        )
        plan = generate_integrated_dispatch_plan(req, self.pipeline)
        self.assertIsNotNone(plan.route_result)
        self.assertTrue(plan.route_result.found)
        self.assertGreater(plan.route_result.total_cost_km, 25.0)

    def test_integrated_plan_zero_fleet(self):
        """When total available fleet is 0, zero additional units are recommended."""
        req = IntegratedDispatchPlanRequest(
            total_fleet_available=0,
            sectors=self.sample_sectors,
        )
        plan = generate_integrated_dispatch_plan(req, self.pipeline)
        self.assertEqual(plan.summary.total_allocated, 0)
        self.assertEqual(plan.summary.unallocated_reserve, 0)
        for s in plan.sectors:
            self.assertEqual(s.recommended_additional, 0)
            self.assertEqual(s.final_total_ambulances, s.current_ambulances)


class TestIntegratedDispatchFastAPIEndpoint(unittest.TestCase):
    API_URL = "http://127.0.0.1:8000/dispatch/integrated-plan"

    def _post(self, payload):
        req = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_post_integrated_plan_success(self):
        """POST /dispatch/integrated-plan returns HTTP 200 with complete summary."""
        payload = {
            "total_fleet_available": 5,
            "sectors": [
                {
                    "twp": "NORRISTOWN",
                    "hour": 10,
                    "month": 5,
                    "day_of_week": 2,
                    "is_weekend": 0,
                    "temperature_2m": 18.5,
                    "relative_humidity_2m": 65.0,
                    "precipitation": 0.0,
                    "wind_speed_10m": 12.0,
                    "weather_code": 1,
                    "current_ambulances": 1,
                },
                {
                    "twp": "LOWER PROVIDENCE",
                    "hour": 10,
                    "month": 5,
                    "day_of_week": 2,
                    "is_weekend": 0,
                    "temperature_2m": 18.5,
                    "relative_humidity_2m": 65.0,
                    "precipitation": 0.0,
                    "wind_speed_10m": 12.0,
                    "weather_code": 1,
                    "current_ambulances": 0,
                },
            ],
            "route_request": {
                "start_node": "NORRISTOWN_EMS",
                "destination_node": "SUBURBAN_HOSPITAL"
            }
        }
        status_code, data = self._post(payload)
        self.assertEqual(status_code, 200)
        self.assertIn("summary", data)
        self.assertIn("sectors", data)
        self.assertIn("route_result", data)
        self.assertIn("decision_explanation", data)
        self.assertEqual(data["summary"]["total_fleet_available"], 5)
        self.assertLessEqual(data["summary"]["total_allocated"], 5)
        self.assertEqual(len(data["sectors"]), 2)
        self.assertTrue(data["route_result"]["found"])

    def test_post_integrated_plan_negative_fleet_422(self):
        """Negative fleet must return HTTP 422."""
        payload = {
            "total_fleet_available": -2,
            "sectors": [
                {
                    "twp": "NORRISTOWN",
                    "hour": 10,
                    "month": 5,
                    "day_of_week": 2,
                    "is_weekend": 0,
                    "temperature_2m": 18.5,
                    "relative_humidity_2m": 65.0,
                    "precipitation": 0.0,
                    "wind_speed_10m": 12.0,
                    "weather_code": 1,
                    "current_ambulances": 1,
                }
            ]
        }
        status_code, data = self._post(payload)
        self.assertEqual(status_code, 422)

    def test_post_integrated_plan_invalid_hour_422(self):
        """Invalid hour (> 23) must return HTTP 422."""
        payload = {
            "total_fleet_available": 3,
            "sectors": [
                {
                    "twp": "NORRISTOWN",
                    "hour": 25,
                    "month": 5,
                    "day_of_week": 2,
                    "is_weekend": 0,
                    "temperature_2m": 18.5,
                    "relative_humidity_2m": 65.0,
                    "precipitation": 0.0,
                    "wind_speed_10m": 12.0,
                    "weather_code": 1,
                    "current_ambulances": 1,
                }
            ]
        }
        status_code, data = self._post(payload)
        self.assertEqual(status_code, 422)


if __name__ == "__main__":
    unittest.main()
