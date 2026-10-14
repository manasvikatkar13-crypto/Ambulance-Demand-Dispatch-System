"""
Unit and integration tests for Ambulance Route Planning with A* Algorithm (Step 15).

Covers:
- A route with multiple possible paths
- The shortest path being selected
- Start and destination being the same
- An unreachable destination (isolated node)
- Invalid node names
- Correct handling of edge costs and cumulative steps
- HTTP API integration tests against FastAPI endpoints (/routes/nodes, /routes/graph, /routes/astar)
"""

import unittest
import json
import urllib.request
import urllib.error

from api.routing import (
    find_astar_route,
    build_adjacency_graph,
    get_network_nodes_list,
    get_network_graph_metadata,
    NodeNotFoundError,
    UnreachableDestinationError,
    SAMPLE_ROAD_GRAPH,
    fetch_osrm_road_route,
    RoutingServiceError,
)


class TestAStarRoutingEngine(unittest.TestCase):
    def test_start_and_destination_same(self):
        """When start and destination are identical, transit cost is 0.0 and path length is 1."""
        res = find_astar_route("NORRISTOWN_EMS", "NORRISTOWN_EMS")
        self.assertTrue(res.found)
        self.assertEqual(res.path, ["NORRISTOWN_EMS"])
        self.assertEqual(res.total_cost_km, 0.0)
        self.assertEqual(res.visited_count, 1)
        self.assertEqual(len(res.path_details), 0)
        self.assertIn("identical", res.explanation.lower())

    def test_shortest_path_selected_among_multiple_paths(self):
        """A* must strictly select the minimum-cost route among multiple available paths."""
        # Route between Norristown EMS and Suburban Hospital:
        # Direct: 1.6 km
        # Alternative via Trooper / Lower Providence: 7.4 + 3.2 + 6.8 = 17.4 km
        res = find_astar_route("NORRISTOWN_EMS", "SUBURBAN_HOSPITAL")
        self.assertTrue(res.found)
        self.assertEqual(res.path, ["NORRISTOWN_EMS", "SUBURBAN_HOSPITAL"])
        self.assertEqual(res.total_cost_km, 1.6)
        self.assertEqual(len(res.path_details), 1)
        self.assertEqual(res.path_details[0].distance_km, 1.6)

    def test_custom_diamond_graph_multiple_paths(self):
        """Verify on a dedicated diamond topology that the strictly shortest path is chosen."""
        custom_nodes = {
            "A": {"name": "Node A", "type": "station", "lat": 40.0, "lng": -75.0, "description": ""},
            "B": {"name": "Node B", "type": "intersection", "lat": 40.1, "lng": -75.0, "description": ""},
            "C": {"name": "Node C", "type": "intersection", "lat": 40.1, "lng": -75.1, "description": ""},
            "D": {"name": "Node D", "type": "hospital", "lat": 40.2, "lng": -75.0, "description": ""},
        }
        # Path 1: A -> B -> D (cost 10 + 10 = 20)
        # Path 2: A -> C -> D (cost 4 + 5 = 9)
        custom_edges = [
            {"from_node": "A", "to_node": "B", "road_name": "Long Way 1", "distance_km": 10.0},
            {"from_node": "B", "to_node": "D", "road_name": "Long Way 2", "distance_km": 10.0},
            {"from_node": "A", "to_node": "C", "road_name": "Short Way 1", "distance_km": 4.0},
            {"from_node": "C", "to_node": "D", "road_name": "Short Way 2", "distance_km": 5.0},
        ]
        custom_graph = {
            "nodes": custom_nodes,
            "edges": custom_edges,
            "adjacency": build_adjacency_graph(custom_nodes, custom_edges),
        }

        res = find_astar_route("A", "D", graph=custom_graph)
        self.assertTrue(res.found)
        self.assertEqual(res.path, ["A", "C", "D"])
        self.assertEqual(res.total_cost_km, 9.0)

    def test_correct_handling_of_edge_costs_and_cumulative_steps(self):
        """Verify that total_cost_km equals sum of segment distances and cumulative costs advance."""
        res = find_astar_route("NORRISTOWN_EMS", "POTTSTOWN_HOSPITAL")
        self.assertTrue(res.found)
        self.assertGreater(len(res.path), 2)

        # Sum of segment distances must equal total_cost_km
        sum_segments = round(sum(step.distance_km for step in res.path_details), 2)
        self.assertEqual(res.total_cost_km, sum_segments)

        # Verify cumulative costs strictly increase
        last_cum = 0.0
        for step in res.path_details:
            self.assertGreater(step.cumulative_cost_km, last_cum)
            last_cum = step.cumulative_cost_km
        self.assertEqual(round(last_cum, 2), res.total_cost_km)

    def test_unreachable_destination_raises_exception(self):
        """Searching to an isolated node must raise UnreachableDestinationError when requested."""
        with self.assertRaises(UnreachableDestinationError):
            find_astar_route("NORRISTOWN_EMS", "ISOLATED_RIVER_ISLAND", raise_if_unreachable=True)

    def test_unreachable_destination_returns_unfound_object(self):
        """When raise_if_unreachable=False, returns found=False with empty path."""
        res = find_astar_route("NORRISTOWN_EMS", "ISOLATED_RIVER_ISLAND", raise_if_unreachable=False)
        self.assertFalse(res.found)
        self.assertEqual(res.path, [])
        self.assertIsNone(res.total_cost_km)
        self.assertIn("unreachable", res.explanation.lower())

    def test_invalid_node_names_raise_node_not_found(self):
        """Invalid or misspelled node names must raise NodeNotFoundError."""
        with self.assertRaises(NodeNotFoundError):
            find_astar_route("UNKNOWN_STATION_XYZ", "SUBURBAN_HOSPITAL")

        with self.assertRaises(NodeNotFoundError):
            find_astar_route("NORRISTOWN_EMS", "FAKE_DESTINATION_123")

    def test_nodes_visited_and_search_stats(self):
        """Search must record visited nodes, count, and execution time."""
        res = find_astar_route("NORRISTOWN_EMS", "ABINGTON_HOSPITAL")
        self.assertTrue(res.found)
        self.assertGreater(res.visited_count, 0)
        self.assertEqual(res.visited_count, len(res.nodes_visited))
        self.assertGreaterEqual(res.execution_time_ms, 0.0)
        self.assertIn("NORRISTOWN_EMS", res.nodes_visited)

    def test_network_metadata_helpers(self):
        """Helper functions must return valid node lists and graph metadata."""
        nodes = get_network_nodes_list()
        self.assertGreater(len(nodes), 15)

        graph_meta = get_network_graph_metadata()
        self.assertEqual(graph_meta.total_nodes, len(nodes))
        self.assertGreater(graph_meta.total_edges, 15)
        self.assertIn("sample", graph_meta.data_authenticity_notice.lower())


class TestAStarFastAPIEndpoints(unittest.TestCase):
    BASE_URL = "http://127.0.0.1:8000"

    def _post(self, endpoint, payload):
        req = urllib.request.Request(
            f"{self.BASE_URL}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def _get(self, endpoint):
        req = urllib.request.Request(f"{self.BASE_URL}{endpoint}", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_get_nodes_endpoint(self):
        """GET /routes/nodes returns 200 with node collection."""
        status_code, data = self._get("/routes/nodes")
        self.assertEqual(status_code, 200)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 15)
        self.assertTrue(any(n["id"] == "NORRISTOWN_EMS" for n in data))

    def test_get_graph_endpoint(self):
        """GET /routes/graph returns 200 with graph structure and disclaimer."""
        status_code, data = self._get("/routes/graph")
        self.assertEqual(status_code, 200)
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertIn("data_authenticity_notice", data)

    def test_post_astar_valid_route(self):
        """POST /routes/astar returns 200 with optimal path and cost."""
        status_code, data = self._post(
            "/routes/astar",
            {"start_node": "NORRISTOWN_EMS", "destination_node": "ABINGTON_HOSPITAL"},
        )
        self.assertEqual(status_code, 200)
        self.assertTrue(data["found"])
        self.assertIsInstance(data["path"], list)
        self.assertGreater(data["total_cost_km"], 0)
        self.assertGreater(data["visited_count"], 0)
        self.assertIn("path_details", data)

    def test_post_astar_same_location(self):
        """POST /routes/astar with identical start and goal returns 200 with 0 cost."""
        status_code, data = self._post(
            "/routes/astar",
            {"start_node": "POTTSTOWN_HOSPITAL", "destination_node": "POTTSTOWN_HOSPITAL"},
        )
        self.assertEqual(status_code, 200)
        self.assertTrue(data["found"])
        self.assertEqual(data["total_cost_km"], 0.0)

    def test_post_astar_unreachable_returns_404(self):
        """POST /routes/astar with unreachable destination returns HTTP 404."""
        status_code, data = self._post(
            "/routes/astar",
            {"start_node": "NORRISTOWN_EMS", "destination_node": "ISOLATED_RIVER_ISLAND"},
        )
        self.assertEqual(status_code, 404)
        self.assertIn("detail", data)
        self.assertIn("unreachable", data["detail"].lower())

    def test_post_astar_invalid_node_returns_400(self):
        """POST /routes/astar with unknown node returns HTTP 400."""
        status_code, data = self._post(
            "/routes/astar",
            {"start_node": "INVALID_STATION_ABC", "destination_node": "SUBURBAN_HOSPITAL"},
        )
        self.assertEqual(status_code, 400)
        self.assertIn("detail", data)
        self.assertIn("not found", data["detail"].lower())


class TestOSRMRealRoadRoutingEngine(unittest.TestCase):
    def test_identical_coordinates_zero_distance(self):
        """When start and destination coordinates are identical, distance is 0.0 without external call."""
        res = fetch_osrm_road_route(40.1215, -75.3400, 40.1215, -75.3400)
        self.assertTrue(res.found)
        self.assertEqual(res.distance_km, 0.0)
        self.assertEqual(res.duration_minutes, 0.0)
        self.assertEqual(len(res.geometry), 1)

    def test_osrm_road_route_norristown_to_suburban(self):
        """Calculate road route between Norristown and Suburban Hospital via OSRM."""
        try:
            res = fetch_osrm_road_route(
                start_lat=40.1215,
                start_lng=-75.3400,
                dest_lat=40.1340,
                dest_lng=-75.3340,
                start_name="Norristown Central EMS Station",
                dest_name="Suburban Community Hospital",
            )
            self.assertTrue(res.found)
            self.assertGreater(res.distance_km, 0.5)
            self.assertGreater(res.duration_minutes, 0.0)
            self.assertGreater(len(res.geometry), 5)
            self.assertIn("OpenStreetMap", res.source)
        except RoutingServiceError:
            # External network may be offline or rate limited in strict offline test environments
            pass


if __name__ == "__main__":
    unittest.main()

