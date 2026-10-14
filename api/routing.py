"""
AI-Based Emergency Ambulance Demand & Dispatch System
Ambulance Route Planning with A* Algorithm (Step 15)

This module implements A* pathfinding on an emergency dispatch network graph.
Nodes represent key EMS stations, hospital emergency departments, major highway
interchanges, and response sectors across Montgomery County, PA.
Edges represent arterial roads and expressways with travel distance weights in km.

Heuristic:
Haversine (great-circle straight-line) distance between geographic coordinates.
Because the straight-line distance is mathematically guaranteed to be <= the actual
curved road distance between any two geographic coordinates, the heuristic is strictly
admissible and consistent, ensuring A* returns the optimal (minimum-cost) route.

HONEST DATA DISCLOSURE:
Reliable road-network GIS centerline data is not present in the historical EMS dataset.
Therefore, this clearly labeled sample road network graph is implemented specifically
for demonstrating the A* search algorithm and is kept separate from empirical call logs.
It does NOT claim live traffic conditions, real-time road closures, or actual 911 CAD dispatching.
"""

import math
import heapq
import time
import json
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------
class NodeNotFoundError(KeyError):
    """Raised when a requested node is not in the road network graph."""
    pass


class UnreachableDestinationError(Exception):
    """Raised when no connected road route exists to the destination."""
    pass


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class AStarRouteRequest(BaseModel):
    start_node: str = Field(..., min_length=1, description="Starting location node identifier")
    destination_node: str = Field(..., min_length=1, description="Destination location node identifier")


class RouteStepDetail(BaseModel):
    from_node: str
    from_name: str
    to_node: str
    to_name: str
    road_name: str
    distance_km: float
    cumulative_cost_km: float


class AStarRouteResponse(BaseModel):
    found: bool
    start_node: str
    start_name: str
    destination_node: str
    destination_name: str
    path: List[str]
    total_cost_km: Optional[float]
    nodes_visited: List[str]
    visited_count: int
    path_details: List[RouteStepDetail]
    execution_time_ms: float
    algorithm: str
    heuristic_used: str
    explanation: str
    disclaimer: str


class NetworkNode(BaseModel):
    id: str
    name: str
    type: str  # "station" | "hospital" | "intersection" | "sector" | "isolated"
    lat: float
    lng: float
    description: str


class NetworkEdge(BaseModel):
    from_node: str
    to_node: str
    road_name: str
    distance_km: float


class RoadNetworkGraphResponse(BaseModel):
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]
    total_nodes: int
    total_edges: int
    data_authenticity_notice: str


# ---------------------------------------------------------------------------
# Haversine Admissible Heuristic
# ---------------------------------------------------------------------------
def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Computes straight-line great-circle distance in kilometers.
    Provably admissible heuristic for road distances between geographic coordinates.
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6371.0  # Earth's radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 3)


# ---------------------------------------------------------------------------
# Sample Road Network Graph Definition
# Montgomery County, PA Representative EMS Dispatch Graph
# ---------------------------------------------------------------------------
SAMPLE_ROAD_NODES: Dict[str, Dict[str, Any]] = {
    "NORRISTOWN_EMS": {
        "name": "Norristown Central EMS Station",
        "type": "station",
        "lat": 40.1215,
        "lng": -75.3400,
        "description": "Primary EMS dispatch hub serving central Norristown",
    },
    "SUBURBAN_HOSPITAL": {
        "name": "Suburban Community Hospital",
        "type": "hospital",
        "lat": 40.1340,
        "lng": -75.3340,
        "description": "Acute care emergency center on DeKalb Pike, East Norriton",
    },
    "JCT_US202_I76": {
        "name": "Interchange US-202 / I-76 (King of Prussia)",
        "type": "intersection",
        "lat": 40.0900,
        "lng": -75.3880,
        "description": "Major highway junction connecting Schuylkill Expressway and Route 202",
    },
    "ZONE_KING_OF_PRUSSIA": {
        "name": "King of Prussia Commercial Sector",
        "type": "sector",
        "lat": 40.0880,
        "lng": -75.3960,
        "description": "Dense commercial hub surrounding King of Prussia Mall",
    },
    "LOWER_PROVIDENCE_EMS": {
        "name": "Lower Providence EMS Station",
        "type": "station",
        "lat": 40.1580,
        "lng": -75.4050,
        "description": "Station serving Eagleville, Audubon, and Lower Providence",
    },
    "JCT_US422_PA363": {
        "name": "Junction US-422 / PA-363 (Trooper)",
        "type": "intersection",
        "lat": 40.1380,
        "lng": -75.4250,
        "description": "Expressway interchange connecting Route 422 and Trooper Road",
    },
    "ZONE_VALLEY_FORGE": {
        "name": "Valley Forge Sector",
        "type": "sector",
        "lat": 40.1010,
        "lng": -75.4480,
        "description": "Response zone covering Valley Forge Park and Route 23 corridor",
    },
    "POTTSTOWN_EMS": {
        "name": "Pottstown Goodwill EMS Station",
        "type": "station",
        "lat": 40.2450,
        "lng": -75.6490,
        "description": "EMS depot serving western Montgomery County and Pottstown borough",
    },
    "POTTSTOWN_HOSPITAL": {
        "name": "Pottstown Hospital Emergency Dept",
        "type": "hospital",
        "lat": 40.2520,
        "lng": -75.6420,
        "description": "Tower Health Pottstown Hospital acute emergency room",
    },
    "JCT_US422_PA100": {
        "name": "Junction US-422 Bypass / PA-100",
        "type": "intersection",
        "lat": 40.2450,
        "lng": -75.6350,
        "description": "High-volume western highway interchange on Pottstown bypass",
    },
    "ZONE_PLYMOUTH_MEETING": {
        "name": "Plymouth Meeting Sector",
        "type": "sector",
        "lat": 40.1090,
        "lng": -75.2810,
        "description": "Commercial and arterial corridor on Germantown Pike",
    },
    "JCT_I476_PA3": {
        "name": "Mid-County Interchange I-476 / I-276",
        "type": "intersection",
        "lat": 40.1180,
        "lng": -75.2840,
        "description": "Toll interchange linking Blue Route (I-476) and PA Turnpike (I-276)",
    },
    "LANSDALE_EMS": {
        "name": "Lansdale VMSC Station",
        "type": "station",
        "lat": 40.2415,
        "lng": -75.2838,
        "description": "Emergency services depot serving North Penn region",
    },
    "JCT_PA63_US202": {
        "name": "Junction PA-63 / US-202 Parkway",
        "type": "intersection",
        "lat": 40.2150,
        "lng": -75.2650,
        "description": "North Wales connector linking Route 63 and Route 202 Parkway",
    },
    "JCT_PA309_PA73": {
        "name": "Interchange PA-309 / PA-73 (Fort Washington)",
        "type": "intersection",
        "lat": 40.1350,
        "lng": -75.2050,
        "description": "Expressway hub connecting Route 309 Expressway and Church Rd",
    },
    "ABINGTON_HOSPITAL": {
        "name": "Jefferson Abington Hospital Trauma Center",
        "type": "hospital",
        "lat": 40.1200,
        "lng": -75.1180,
        "description": "Regional Level II trauma and tertiary emergency referral center",
    },
    "CHELTENHAM_EMS": {
        "name": "Cheltenham Township EMS Station",
        "type": "station",
        "lat": 40.0600,
        "lng": -75.1100,
        "description": "Station serving eastern township border and Route 611",
    },
    "ZONE_WILLOW_GROVE": {
        "name": "Willow Grove Sector",
        "type": "sector",
        "lat": 40.1440,
        "lng": -75.1160,
        "description": "Response sector near Route 611 and Pennsylvania Turnpike Exit 343",
    },
    "MAIN_LINE_HOSPITAL": {
        "name": "Bryn Mawr Hospital (Main Line)",
        "type": "hospital",
        "lat": 40.0210,
        "lng": -75.3160,
        "description": "Main Line Health hospital serving southern Montgomery County",
    },
    "ISOLATED_RIVER_ISLAND": {
        "name": "Schuylkill River Isolated Island Outpost",
        "type": "isolated",
        "lat": 40.1100,
        "lng": -75.3600,
        "description": "Isolated sector disconnected from road network (for reachability testing)",
    },
}

# Bidirectional edges with road names and travel distance costs (in km)
SAMPLE_ROAD_EDGES: List[Dict[str, Any]] = [
    {"from_node": "NORRISTOWN_EMS", "to_node": "SUBURBAN_HOSPITAL", "road_name": "DeKalb St / US-202 Corridor", "distance_km": 1.6},
    {"from_node": "NORRISTOWN_EMS", "to_node": "JCT_US202_I76", "road_name": "US-202 South / Dannehower Bridge", "distance_km": 5.8},
    {"from_node": "NORRISTOWN_EMS", "to_node": "JCT_US422_PA363", "road_name": "West Main St / Ridge Pike", "distance_km": 7.4},
    {"from_node": "NORRISTOWN_EMS", "to_node": "ZONE_PLYMOUTH_MEETING", "road_name": "Germantown Pike East", "distance_km": 5.4},
    {"from_node": "SUBURBAN_HOSPITAL", "to_node": "LOWER_PROVIDENCE_EMS", "road_name": "Ridge Pike West", "distance_km": 6.8},
    {"from_node": "SUBURBAN_HOSPITAL", "to_node": "JCT_I476_PA3", "road_name": "Germantown Pike to Mid-County", "distance_km": 5.1},
    {"from_node": "JCT_US202_I76", "to_node": "ZONE_KING_OF_PRUSSIA", "road_name": "Mall Blvd / Goddard Blvd", "distance_km": 1.2},
    {"from_node": "JCT_US202_I76", "to_node": "ZONE_VALLEY_FORGE", "road_name": "US-422 West to Route 23", "distance_km": 5.9},
    {"from_node": "JCT_US202_I76", "to_node": "MAIN_LINE_HOSPITAL", "road_name": "I-76 East / Route 320", "distance_km": 9.8},
    {"from_node": "ZONE_VALLEY_FORGE", "to_node": "JCT_US422_PA363", "road_name": "PA-23 East to Betzwood Bridge", "distance_km": 4.8},
    {"from_node": "JCT_US422_PA363", "to_node": "LOWER_PROVIDENCE_EMS", "road_name": "PA-363 Trooper Rd North", "distance_km": 3.2},
    {"from_node": "JCT_US422_PA363", "to_node": "JCT_US422_PA100", "road_name": "US-422 Expressway Westbound", "distance_km": 21.5},
    {"from_node": "LOWER_PROVIDENCE_EMS", "to_node": "JCT_PA63_US202", "road_name": "Skippack Pike / PA-73 East", "distance_km": 13.8},
    {"from_node": "JCT_US422_PA100", "to_node": "POTTSTOWN_HOSPITAL", "road_name": "High St / Armand Hammer Blvd", "distance_km": 1.4},
    {"from_node": "JCT_US422_PA100", "to_node": "POTTSTOWN_EMS", "road_name": "East High St Arterial", "distance_km": 1.8},
    {"from_node": "POTTSTOWN_EMS", "to_node": "POTTSTOWN_HOSPITAL", "road_name": "State St / E High St", "distance_km": 1.2},
    {"from_node": "ZONE_PLYMOUTH_MEETING", "to_node": "JCT_I476_PA3", "road_name": "Chemical Rd / Germantown Pike", "distance_km": 1.5},
    {"from_node": "JCT_I476_PA3", "to_node": "JCT_PA309_PA73", "road_name": "PA Turnpike I-276 Eastbound", "distance_km": 7.8},
    {"from_node": "JCT_I476_PA3", "to_node": "JCT_PA63_US202", "road_name": "DeKalb Pike / US-202 Parkway", "distance_km": 11.2},
    {"from_node": "LANSDALE_EMS", "to_node": "JCT_PA63_US202", "road_name": "Main St / PA-63 West", "distance_km": 3.5},
    {"from_node": "LANSDALE_EMS", "to_node": "JCT_PA309_PA73", "road_name": "PA-309 Expressway Southbound", "distance_km": 13.2},
    {"from_node": "JCT_PA309_PA73", "to_node": "ABINGTON_HOSPITAL", "road_name": "PA-73 / Church Rd to Old York Rd", "distance_km": 8.4},
    {"from_node": "ABINGTON_HOSPITAL", "to_node": "ZONE_WILLOW_GROVE", "road_name": "Old York Rd / PA-611 North", "distance_km": 3.6},
    {"from_node": "ABINGTON_HOSPITAL", "to_node": "CHELTENHAM_EMS", "road_name": "PA-611 South / Easton Rd", "distance_km": 6.8},
    {"from_node": "ZONE_WILLOW_GROVE", "to_node": "JCT_PA309_PA73", "road_name": "PA-63 Moreland Rd", "distance_km": 7.9},
]


def build_adjacency_graph(nodes_dict: Dict[str, Any], edges_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Constructs an undirected adjacency dictionary from nodes and edge definitions.
    """
    adj: Dict[str, Dict[str, Dict[str, Any]]] = {node_id: {} for node_id in nodes_dict}
    for edge in edges_list:
        u = edge["from_node"]
        v = edge["to_node"]
        data = {
            "road_name": edge["road_name"],
            "distance_km": round(float(edge["distance_km"]), 2),
        }
        if u in adj and v in adj:
            adj[u][v] = data
            adj[v][u] = data  # Bidirectional undirected road
    return adj


# Prebuilt sample graph singleton
SAMPLE_ROAD_GRAPH = {
    "nodes": SAMPLE_ROAD_NODES,
    "edges": SAMPLE_ROAD_EDGES,
    "adjacency": build_adjacency_graph(SAMPLE_ROAD_NODES, SAMPLE_ROAD_EDGES),
}


# ---------------------------------------------------------------------------
# Core A* Pathfinding Algorithm
# ---------------------------------------------------------------------------
def find_astar_route(
    start_node: str,
    destination_node: str,
    graph: Optional[Dict[str, Any]] = None,
    raise_if_unreachable: bool = True
) -> AStarRouteResponse:
    """
    Finds the shortest path between start_node and destination_node using the A* algorithm.

    Parameters:
    - start_node: Identifier of starting location
    - destination_node: Identifier of target destination location
    - graph: Graph dictionary containing 'nodes' and 'adjacency' (defaults to SAMPLE_ROAD_GRAPH)
    - raise_if_unreachable: If True, raises UnreachableDestinationError when no route exists;
      if False, returns an AStarRouteResponse with found=False and empty path.

    Returns:
    - AStarRouteResponse containing optimal path, cost, nodes visited, and search statistics.
    """
    if graph is None:
        graph = SAMPLE_ROAD_GRAPH

    nodes = graph["nodes"]
    adjacency = graph["adjacency"]

    # 1. Validate node existence
    start_key = start_node.strip().upper()
    dest_key = destination_node.strip().upper()

    if start_key not in nodes:
        raise NodeNotFoundError(f"Start location node '{start_node}' not found in road network graph.")
    if dest_key not in nodes:
        raise NodeNotFoundError(f"Destination location node '{destination_node}' not found in road network graph.")

    start_info = nodes[start_key]
    dest_info = nodes[dest_key]
    start_time = time.perf_counter()

    # 2. Handle trivial case: Start == Destination
    if start_key == dest_key:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
        return AStarRouteResponse(
            found=True,
            start_node=start_key,
            start_name=start_info["name"],
            destination_node=dest_key,
            destination_name=dest_info["name"],
            path=[start_key],
            total_cost_km=0.0,
            nodes_visited=[start_key],
            visited_count=1,
            path_details=[],
            execution_time_ms=elapsed_ms,
            algorithm="A* (A-Star) Pathfinding",
            heuristic_used="Haversine Straight-Line Distance (Admissible)",
            explanation=(
                f"Start and destination are identical ('{start_info['name']}'). "
                "Transit distance is 0.0 km; zero intermediate navigation required."
            ),
            disclaimer=(
                "Academic decision-support prototype demonstration. Path calculated on a representative "
                "sample road graph. Does not reflect live traffic congestion or active GPS telemetry."
            ),
        )

    # 3. Initialize A* search state
    goal_coord = (dest_info["lat"], dest_info["lng"])
    start_coord = (start_info["lat"], start_info["lng"])
    start_h = haversine_distance(start_coord, goal_coord)

    # Priority queue item: (f_score, tie_breaker, node_id)
    tie_breaker = 0
    open_heap: List[Tuple[float, int, str]] = [(start_h, tie_breaker, start_key)]

    g_score: Dict[str, float] = {start_key: 0.0}
    f_score: Dict[str, float] = {start_key: start_h}
    came_from: Dict[str, Tuple[str, Dict[str, Any]]] = {}

    visited_order: List[str] = []
    visited_set = set()

    # 4. Search loop
    while open_heap:
        current_f, _, current = heapq.heappop(open_heap)

        if current in visited_set:
            continue
        visited_set.add(current)
        visited_order.append(current)

        # Goal reached
        if current == dest_key:
            # Reconstruct path and step-by-step segment details
            path = []
            path_details = []
            curr_node = dest_key
            while curr_node in came_from:
                prev_node, edge_info = came_from[curr_node]
                path.append(curr_node)
                path_details.append({
                    "from_node": prev_node,
                    "from_name": nodes[prev_node]["name"],
                    "to_node": curr_node,
                    "to_name": nodes[curr_node]["name"],
                    "road_name": edge_info["road_name"],
                    "distance_km": edge_info["distance_km"],
                })
                curr_node = prev_node
            path.append(start_key)
            path.reverse()
            path_details.reverse()

            # Compute cumulative costs along path
            cum_cost = 0.0
            formatted_details: List[RouteStepDetail] = []
            for step in path_details:
                cum_cost = round(cum_cost + step["distance_km"], 2)
                formatted_details.append(
                    RouteStepDetail(
                        from_node=step["from_node"],
                        from_name=step["from_name"],
                        to_node=step["to_node"],
                        to_name=step["to_name"],
                        road_name=step["road_name"],
                        distance_km=step["distance_km"],
                        cumulative_cost_km=cum_cost,
                    )
                )

            total_cost = round(g_score[dest_key], 2)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 3)

            explanation = (
                f"Optimal minimum-distance route identified by A* algorithm using an admissible Haversine heuristic. "
                f"Evaluated {len(visited_order)} graph nodes during search exploration. "
                f"Selected the shortest path of {total_cost} km spanning {len(formatted_details)} road segments."
            )

            return AStarRouteResponse(
                found=True,
                start_node=start_key,
                start_name=start_info["name"],
                destination_node=dest_key,
                destination_name=dest_info["name"],
                path=path,
                total_cost_km=total_cost,
                nodes_visited=visited_order,
                visited_count=len(visited_order),
                path_details=formatted_details,
                execution_time_ms=elapsed_ms,
                algorithm="A* (A-Star) Pathfinding",
                heuristic_used="Haversine Straight-Line Distance (Admissible)",
                explanation=explanation,
                disclaimer=(
                    "Academic decision-support prototype demonstration. Path calculated on a representative "
                    "sample road graph. Does not reflect live traffic congestion or active GPS telemetry."
                ),
            )

        # Explore neighbors
        for neighbor, edge_data in adjacency.get(current, {}).items():
            tentative_g = round(g_score[current] + edge_data["distance_km"], 3)
            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = (current, edge_data)
                g_score[neighbor] = tentative_g
                neighbor_coord = (nodes[neighbor]["lat"], nodes[neighbor]["lng"])
                h = haversine_distance(neighbor_coord, goal_coord)
                f = tentative_g + h
                f_score[neighbor] = f
                tie_breaker += 1
                heapq.heappush(open_heap, (f, tie_breaker, neighbor))

    # 5. Destination unreachable
    elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 3)

    if raise_if_unreachable:
        raise UnreachableDestinationError(
            f"Destination '{dest_info['name']}' ({dest_key}) is unreachable from "
            f"start '{start_info['name']}' ({start_key}) in this road network."
        )

    return AStarRouteResponse(
        found=False,
        start_node=start_key,
        start_name=start_info["name"],
        destination_node=dest_key,
        destination_name=dest_info["name"],
        path=[],
        total_cost_km=None,
        nodes_visited=visited_order,
        visited_count=len(visited_order),
        path_details=[],
        execution_time_ms=elapsed_ms,
        algorithm="A* (A-Star) Pathfinding",
        heuristic_used="Haversine Straight-Line Distance (Admissible)",
        explanation=(
            f"Destination '{dest_info['name']}' is unreachable from '{start_info['name']}' "
            "within the evaluated road network graph (no connected road path exists)."
        ),
        disclaimer=(
            "Academic decision-support prototype demonstration. Path calculated on a representative "
            "sample road graph. Does not reflect live traffic congestion or active GPS telemetry."
        ),
    )


# ---------------------------------------------------------------------------
# Network Metadata Helpers
# ---------------------------------------------------------------------------
def get_network_nodes_list(graph: Optional[Dict[str, Any]] = None) -> List[NetworkNode]:
    """Returns all nodes in the road network graph for UI select lists."""
    if graph is None:
        graph = SAMPLE_ROAD_GRAPH
    return [
        NetworkNode(
            id=node_id,
            name=data["name"],
            type=data["type"],
            lat=data["lat"],
            lng=data["lng"],
            description=data["description"],
        )
        for node_id, data in graph["nodes"].items()
    ]


def get_network_graph_metadata(graph: Optional[Dict[str, Any]] = None) -> RoadNetworkGraphResponse:
    """Returns the full road network graph topology with honesty disclaimer."""
    if graph is None:
        graph = SAMPLE_ROAD_GRAPH

    nodes_list = get_network_nodes_list(graph)
    edges_list = [
        NetworkEdge(
            from_node=e["from_node"],
            to_node=e["to_node"],
            road_name=e["road_name"],
            distance_km=e["distance_km"],
        )
        for e in graph["edges"]
    ]

    return RoadNetworkGraphResponse(
        nodes=nodes_list,
        edges=edges_list,
        total_nodes=len(nodes_list),
        total_edges=len(edges_list),
        data_authenticity_notice=(
            "Representative sample dispatch road graph of Montgomery County, PA emergency facilities. "
            "Created specifically for demonstrating the A* search algorithm. Completely separate from "
            "historical 911 dispatch calls; not live drivable road geometry or real-time traffic."
        ),
    )


# ---------------------------------------------------------------------------
# Road-Following Route Planning (OSRM / OpenStreetMap Engine)
# ---------------------------------------------------------------------------
class RoadRouteRequest(BaseModel):
    start_lat: float = Field(..., ge=-90.0, le=90.0, description="Starting point latitude")
    start_lng: float = Field(..., ge=-180.0, le=180.0, description="Starting point longitude")
    dest_lat: float = Field(..., ge=-90.0, le=90.0, description="Destination latitude")
    dest_lng: float = Field(..., ge=-180.0, le=180.0, description="Destination longitude")
    start_name: Optional[str] = Field("Starting Location", description="Descriptive label for start point")
    dest_name: Optional[str] = Field("Destination", description="Descriptive label for destination")


class RoadRouteResponse(BaseModel):
    found: bool
    source: str = "OpenStreetMap / OSRM (Open Source Routing Machine)"
    start_lat: float
    start_lng: float
    start_name: str
    dest_lat: float
    dest_lng: float
    dest_name: str
    distance_meters: float
    distance_km: float
    distance_miles: float
    duration_seconds: float
    duration_minutes: float
    geometry: List[List[float]]  # List of [lat, lng] coordinates for Leaflet Polyline
    coordinate_count: int
    disclaimer: str


class RoutingServiceError(Exception):
    """Raised when the external road routing service returns an error or is unreachable."""
    pass


def fetch_osrm_road_route(
    start_lat: float,
    start_lng: float,
    dest_lat: float,
    dest_lng: float,
    start_name: str = "Starting Location",
    dest_name: str = "Destination",
    timeout_seconds: float = 8.0,
) -> RoadRouteResponse:
    """
    Fetches actual road-following route geometry, distance, and duration between two coordinates
    using the public Open Source Routing Machine (OSRM) driving API backed by OpenStreetMap data.

    Returns Leaflet-compatible [latitude, longitude] geometry coordinates.
    """
    # 1. Edge case: Start and destination are identical
    if abs(start_lat - dest_lat) < 1e-6 and abs(start_lng - dest_lng) < 1e-6:
        return RoadRouteResponse(
            found=True,
            source="OpenStreetMap / OSRM (Open Source Routing Machine)",
            start_lat=start_lat,
            start_lng=start_lng,
            start_name=start_name or "Starting Location",
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            dest_name=dest_name or "Destination",
            distance_meters=0.0,
            distance_km=0.0,
            distance_miles=0.0,
            duration_seconds=0.0,
            duration_minutes=0.0,
            geometry=[[start_lat, start_lng]],
            coordinate_count=1,
            disclaimer=(
                "Start and destination coordinates are identical. Distance and estimated travel time are zero."
            ),
        )

    # 2. Build OSRM request URL (OSRM expects {longitude},{latitude})
    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{start_lng:.6f},{start_lat:.6f};{dest_lng:.6f},{dest_lat:.6f}"
        f"?overview=full&geometries=geojson"
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AmbulanceDemandDispatchSystem/1.0 (academic decision-support research demo)"
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as he:
        raise RoutingServiceError(f"OSRM routing service returned HTTP error {he.code}: {he.reason}")
    except (urllib.error.URLError, TimeoutError) as ue:
        raise RoutingServiceError(f"Could not connect to OSRM routing service: {str(ue)}")
    except Exception as exc:
        raise RoutingServiceError(f"Unexpected error while contacting routing service: {str(exc)}")

    # 3. Check OSRM response status
    if payload.get("code") != "Ok" or not payload.get("routes"):
        error_code = payload.get("code", "NoRoute")
        raise RoutingServiceError(
            f"Routing service could not find a drivable road path ({error_code})."
        )

    route_data = payload["routes"][0]
    distance_meters = float(route_data.get("distance", 0.0))
    duration_seconds = float(route_data.get("duration", 0.0))
    raw_geojson_coords = route_data.get("geometry", {}).get("coordinates", [])

    # Invert GeoJSON [longitude, latitude] to Leaflet [latitude, longitude]
    leaflet_geometry = [[pt[1], pt[0]] for pt in raw_geojson_coords if len(pt) >= 2]

    distance_km = round(distance_meters / 1000.0, 2)
    distance_miles = round(distance_km * 0.621371, 2)
    duration_minutes = round(duration_seconds / 60.0, 1)

    return RoadRouteResponse(
        found=True,
        source="OpenStreetMap / OSRM (Open Source Routing Machine)",
        start_lat=start_lat,
        start_lng=start_lng,
        start_name=start_name or "Starting Location",
        dest_lat=dest_lat,
        dest_lng=dest_lng,
        dest_name=dest_name or "Destination",
        distance_meters=round(distance_meters, 1),
        distance_km=distance_km,
        distance_miles=distance_miles,
        duration_seconds=round(duration_seconds, 1),
        duration_minutes=duration_minutes,
        geometry=leaflet_geometry,
        coordinate_count=len(leaflet_geometry),
        disclaimer=(
            "Road route calculated along OpenStreetMap road centerlines via OSRM. "
            "Estimated travel duration uses standard speed limits without live traffic congestion, "
            "construction detours, or emergency siren priority. Academic decision-support prototype."
        ),
    )

