
from __future__ import annotations

import sys
import time
from pathlib import Path

import networkx as nx
import osmnx as ox

sys.path.insert(0, str(Path(__file__).parent))
from config import GEO, PATHS
from logger import get_logger

log = get_logger(__name__)

COLOMBO_HIGHWAY_SPEEDS: dict[str, int] = {
    "motorway":       80,
    "motorway_link":  60,
    "trunk":          50,
    "trunk_link":     40,
    "primary":        40,
    "primary_link":   30,
    "secondary":      30,
    "secondary_link": 25,
    "tertiary":       25,
    "tertiary_link":  20,
    "residential":    20,
    "unclassified":   20,
    "service":        15,
    "living_street":  10,
    "pedestrian":      5,
}

FALLBACK_SPEED_KMH = 25

def download_graph() -> nx.MultiDiGraph:

    CENTRE_LAT = 6.9271
    CENTRE_LON = 79.8612
    RADIUS_M   = 13_000

    log.info(
        f"Downloading OSM graph — centre: ({CENTRE_LAT}, {CENTRE_LON}), "
        f"radius: {RADIUS_M/1000:.0f} km"
    )
    log.info("This may take 30-90 seconds depending on network speed...")

    t0 = time.perf_counter()
    try:
        G = ox.graph_from_point(
            (CENTRE_LAT, CENTRE_LON),
            dist=RADIUS_M,
            network_type=GEO["network_type"],
            retain_all=False,
        )
    except Exception as e:
        log.warning(f"Point query failed ({e}), falling back to place query...")
        G = ox.graph_from_place(GEO["place_query"], network_type=GEO["network_type"])

    elapsed = time.perf_counter() - t0
    log.info(
        f"Graph downloaded in {elapsed:.1f}s | "
        f"Nodes: {G.number_of_nodes():,} | Edges: {G.number_of_edges():,}"
    )
    return G

def add_travel_time_attributes(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    log.info("Imputing edge speeds and computing travel times...")
    G = ox.add_edge_speeds(
        G,
        hwy_speeds=COLOMBO_HIGHWAY_SPEEDS,
        fallback=FALLBACK_SPEED_KMH,
    )
    G = ox.add_edge_travel_times(G)

    sample = list(G.edges(data=True))[:5]
    travel_times = [d.get("travel_time", None) for _, _, d in sample]
    log.info(f"Sample travel times (first 5 edges, seconds): {travel_times}")
    return G

def simplify_and_project(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    log.info("Simplifying graph topology...")
    t0 = time.perf_counter()
    G_simple = ox.simplify_graph(G)
    log.info(
        f"Simplified in {time.perf_counter()-t0:.1f}s | "
        f"Nodes: {G.number_of_nodes():,} → {G_simple.number_of_nodes():,} | "
        f"Edges: {G.number_of_edges():,} → {G_simple.number_of_edges():,}"
    )

    log.info(f"Projecting to {GEO['crs_metric']}...")
    G_proj = ox.project_graph(G_simple, to_crs=GEO["crs_metric"])
    return G_proj

def save_graph(G: nx.MultiDiGraph) -> None:
    path = PATHS["osm_graph"]
    path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(G, filepath=str(path))
    size_mb = path.stat().st_size / (1024 * 1024)
    log.info(f"Graph saved: {path.name} ({size_mb:.1f} MB)")

def load_graph() -> nx.MultiDiGraph:
    path = PATHS["osm_graph"]
    log.info(f"Loading cached graph from {path.name}...")
    t0 = time.perf_counter()
    G = ox.load_graphml(str(path))

    sample_edges = list(G.edges(data=True))[:3]
    has_travel_time = all("travel_time" in d for _, _, d in sample_edges)

    if not has_travel_time:
        log.info("travel_time attribute missing in cached graph — recomputing...")
        G = add_travel_time_attributes(G)

    log.info(
        f"Graph loaded in {time.perf_counter()-t0:.1f}s | "
        f"Nodes: {G.number_of_nodes():,} | Edges: {G.number_of_edges():,}"
    )
    return G

def load_or_download_graph(force_download: bool = False) -> nx.MultiDiGraph:
    path = PATHS["osm_graph"]

    if not force_download and path.exists():
        log.info(f"Cache hit: {path.name} exists — loading from disk")
        return load_graph()

    log.info("Cache miss or force_download=True — downloading from OpenStreetMap")
    G = download_graph()
    G = add_travel_time_attributes(G)
    save_graph(G)
    return G

def get_graph_stats(G: nx.MultiDiGraph) -> dict:
    edge_lengths   = [d.get("length", 0) for _, _, d in G.edges(data=True)]
    travel_times   = [d.get("travel_time", 0) for _, _, d in G.edges(data=True)]
    speeds         = [d.get("speed_kph", 0) for _, _, d in G.edges(data=True)]

    import statistics
    stats = {
        "node_count":           G.number_of_nodes(),
        "edge_count":           G.number_of_edges(),
        "avg_edge_length_m":    round(statistics.mean(edge_lengths), 1) if edge_lengths else 0,
        "avg_travel_time_s":    round(statistics.mean(travel_times), 1) if travel_times else 0,
        "avg_speed_kph":        round(statistics.mean(speeds), 1) if speeds else 0,
        "total_network_km":     round(sum(edge_lengths) / 1000, 1),
        "is_weakly_connected":  nx.is_weakly_connected(G),
    }

    log.info("Graph statistics:")
    for k, v in stats.items():
        log.info(f"  {k}: {v}")

    return stats

if __name__ == "__main__":
    G = load_or_download_graph()
    stats = get_graph_stats(G)
    print("\nColombo OSM Drive Graph Statistics:")
    for k, v in stats.items():
        print(f"  {k:<30} {v}")
