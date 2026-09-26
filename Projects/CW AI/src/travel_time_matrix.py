
from __future__ import annotations

import sys
import time
from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import ZONES, ZONE_IDS, ZONE_CENTROIDS, PATHS, POSITIONING
from logger import get_logger

log = get_logger(__name__)

MAX_VALID_TIME_MIN = 60.0

UNREACHABLE_SENTINEL = 999.0

def find_zone_nodes(G: nx.MultiDiGraph) -> dict[str, int]:
    log.info("Locating nearest OSM nodes for all zone centroids...")

    lons = [ZONE_CENTROIDS[z][1] for z in ZONE_IDS]
    lats = [ZONE_CENTROIDS[z][0] for z in ZONE_IDS]

    node_ids = ox.nearest_nodes(G, X=lons, Y=lats)

    zone_nodes: dict[str, int] = {}
    for zone_id, node_id in zip(ZONE_IDS, node_ids):
        zone_nodes[zone_id] = node_id
        zone = next(z for z in ZONES if z.id == zone_id)
        log.info(
            f"  {zone_id} ({zone.name:<22}) → OSM node {node_id} "
            f"(centroid: {zone.centroid_lat:.4f}, {zone.centroid_lon:.4f})"
        )

    return zone_nodes

def compute_row(
    G:           nx.MultiDiGraph,
    source_zone: str,
    zone_nodes:  dict[str, int],
) -> dict[str, float]:
    source_node = zone_nodes[source_zone]

    lengths: dict[int, float] = nx.single_source_dijkstra_path_length(
        G, source_node, weight="travel_time"
    )

    row: dict[str, float] = {}
    for target_zone in ZONE_IDS:
        target_node = zone_nodes[target_zone]
        if target_zone == source_zone:
            row[target_zone] = 0.0
        elif target_node in lengths:
            row[target_zone] = lengths[target_node] / 60.0
        else:
            log.warning(
                f"No path found: {source_zone} → {target_zone} "
                f"(nodes {source_node} → {target_node}). "
                f"Assigning sentinel value {UNREACHABLE_SENTINEL}."
            )
            row[target_zone] = UNREACHABLE_SENTINEL

    return row

def compute_full_matrix(
    G:          nx.MultiDiGraph,
    zone_nodes: dict[str, int],
) -> pd.DataFrame:
    log.info(
        f"Computing {len(ZONE_IDS)}×{len(ZONE_IDS)} travel-time matrix "
        f"using Dijkstra's algorithm (weight='travel_time')..."
    )

    matrix: dict[str, dict[str, float]] = {}
    total_start = time.perf_counter()

    for i, source_zone in enumerate(ZONE_IDS):
        t0 = time.perf_counter()
        row = compute_row(G, source_zone, zone_nodes)
        elapsed = time.perf_counter() - t0
        matrix[source_zone] = row

        zone_name = next(z.name for z in ZONES if z.id == source_zone)
        log.info(
            f"  [{i+1:2d}/{len(ZONE_IDS)}] {source_zone} ({zone_name:<22}) "
            f"→ completed in {elapsed:.2f}s"
        )

    total_elapsed = time.perf_counter() - total_start
    log.info(f"Matrix computation complete in {total_elapsed:.2f}s")

    df = pd.DataFrame(matrix).T
    df = df[ZONE_IDS]
    df = df.loc[ZONE_IDS]
    df = df.round(1)

    return df

def validate_matrix(df: pd.DataFrame) -> bool:
    reposition_limit = POSITIONING["reposition_limit_min"]

    checks = {
        "Shape is 10×10":
            df.shape == (10, 10),
        "All zone IDs in index":
            set(df.index) == set(ZONE_IDS),
        "All zone IDs in columns":
            set(df.columns) == set(ZONE_IDS),
        "Diagonal is zero":
            all(df.loc[z, z] == 0.0 for z in ZONE_IDS),
        "No NaN values":
            not df.isna().any().any(),
        "No sentinel values":
            (df.values < UNREACHABLE_SENTINEL).all(),
        "All off-diagonal > 0":
            all(
                df.loc[r, c] > 0
                for r in ZONE_IDS for c in ZONE_IDS if r != c
            ),
        f"All values < {MAX_VALID_TIME_MIN} min (within Colombo)":
            bool((df.values[df.values > 0] < MAX_VALID_TIME_MIN).all()),
        f"Some pairs within {reposition_limit} min (repositioning feasible)":
            (df[(df > 0) & (df <= reposition_limit)].count().sum() > 0),
    }

    all_pass = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        log.info(f"  [{status}] {check}")
        if not passed:
            all_pass = False

    off_diag = df.values[df.values > 0]
    log.info(
        f"  Matrix stats — min: {off_diag.min():.1f} min | "
        f"mean: {off_diag.mean():.1f} min | "
        f"max: {off_diag.max():.1f} min"
    )
    reachable_in_10 = (df[(df > 0) & (df <= 10)].count().sum())
    log.info(
        f"  Zone pairs reachable in ≤10 min: {reachable_in_10} / {10*9} "
        f"({100*reachable_in_10/(10*9):.0f}%)"
    )
    return all_pass

def save_matrix(df: pd.DataFrame) -> Path:
    out_path = PATHS["travel_matrix"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path)
    log.info(f"Travel-time matrix saved: {out_path.name}")
    return out_path

def load_matrix() -> pd.DataFrame | None:
    path = PATHS["travel_matrix"]
    if not path.exists():
        return None
    df = pd.read_csv(path, index_col=0)
    log.info(f"Travel-time matrix loaded from {path.name}")
    return df

def print_matrix(df: pd.DataFrame) -> None:
    print("\n" + "=" * 70)
    print("  COLOMBO TRAVEL-TIME MATRIX  (minutes, driving, off-peak)")
    print("  Rows = from zone | Columns = to zone")
    print("=" * 70)

    display = df.copy()
    display.index = [
        f"{z_id} {next(z.name for z in ZONES if z.id==z_id)[:12]}"
        for z_id in df.index
    ]
    print(df.to_string(float_format="{:.1f}".format))
    print()

    print("  Zones reachable within 10-minute repositioning limit:")
    for from_zone in ZONE_IDS:
        targets = [
            t for t in ZONE_IDS
            if t != from_zone and df.loc[from_zone, t] <= 10.0
        ]
        if targets:
            print(f"  {from_zone}: {', '.join(targets)}")
    print("=" * 70)

def prepare_travel_time_matrix(G: nx.MultiDiGraph) -> pd.DataFrame:
    zone_nodes = find_zone_nodes(G)
    df         = compute_full_matrix(G, zone_nodes)
    validate_matrix(df)
    save_matrix(df)
    print_matrix(df)
    return df

if __name__ == "__main__":
    from road_network import load_or_download_graph
    G  = load_or_download_graph()
    df = prepare_travel_time_matrix(G)
