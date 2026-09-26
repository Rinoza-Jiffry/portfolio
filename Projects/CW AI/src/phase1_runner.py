
from __future__ import annotations

import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import PATHS, ZONE_IDS, POSITIONING
from logger import get_logger

log = get_logger(__name__)

def run_step_1_graph(force_download: bool = False) -> object:
    log.info("=" * 58)
    log.info("STEP 1: Colombo OSM Road Graph")
    log.info("=" * 58)
    from road_network import load_or_download_graph, get_graph_stats
    G = load_or_download_graph(force_download=force_download)
    stats = get_graph_stats(G)
    log.info(
        f"Step 1 complete | nodes={stats['node_count']:,} | "
        f"edges={stats['edge_count']:,} | "
        f"network={stats['total_network_km']} km"
    )
    return G, stats

def run_step_2_zones(matrix_df=None) -> dict:
    log.info("=" * 58)
    log.info("STEP 2: Zone Boundaries & Folium Map")
    log.info("=" * 58)
    from zone_builder import prepare_zones, validate_zone_geojson
    geojson = prepare_zones(matrix_df=matrix_df)
    ok = validate_zone_geojson(geojson)
    log.info(f"Step 2 complete | zones={len(geojson['features'])} | validation={'PASS' if ok else 'FAIL'}")
    return geojson

def run_step_3_matrix(G) -> object:
    log.info("=" * 58)
    log.info("STEP 3: Travel-Time Matrix (Dijkstra)")
    log.info("=" * 58)
    from travel_time_matrix import prepare_travel_time_matrix, validate_matrix
    df = prepare_travel_time_matrix(G)
    ok = validate_matrix(df)
    log.info(f"Step 3 complete | shape={df.shape} | validation={'PASS' if ok else 'FAIL'}")
    return df, ok

def run_step_4_validate(G_stats: dict, matrix_df) -> bool:
    log.info("=" * 58)
    log.info("STEP 4: Phase 1 Cross-Validation")
    log.info("=" * 58)

    checks = {
        "GraphML file exists": PATHS["osm_graph"].exists(),
        "Zone GeoJSON exists": PATHS["zone_geojson"].exists(),
        "Travel matrix exists": PATHS["travel_matrix"].exists(),
        "Zone map HTML exists": (PATHS["outputs_maps"] / "zone_map.html").exists(),
        "Graph is weakly connected": G_stats.get("is_weakly_connected", False),
        "Matrix diagonal = 0": all(
            matrix_df.loc[z, z] == 0.0 for z in ZONE_IDS
        ),
        "All zones reachable in <60 min": bool(
            (matrix_df.values[matrix_df.values > 0] < 60.0).all()
        ),
        f"Repositioning limit ({POSITIONING['reposition_limit_min']} min) feasible": (
            matrix_df[(matrix_df > 0) & (matrix_df <= POSITIONING["reposition_limit_min"])]
            .count().sum() > 0
        ),
    }

    all_pass = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        log.info(f"  [{status}] {check}")
        if not passed:
            all_pass = False

    return all_pass

def print_phase1_summary(G_stats: dict, matrix_df) -> None:
    import pandas as pd

    print("\n" + "=" * 65)
    print("  PHASE 1 SUMMARY — GEOSPATIAL FOUNDATION")
    print("  7COSC013W.1 Foundations of AI, University of Westminster")
    print("=" * 65)

    print("\n[Road Network]")
    print(f"  Nodes:          {G_stats['node_count']:,}")
    print(f"  Edges:          {G_stats['edge_count']:,}")
    print(f"  Network length: {G_stats['total_network_km']} km")
    print(f"  Avg speed:      {G_stats['avg_speed_kph']} km/h")
    print(f"  Connected:      {G_stats['is_weakly_connected']}")

    print("\n[Travel-Time Matrix]  (minutes, all values)")
    off_diag = matrix_df.values[matrix_df.values > 0]
    print(f"  Min:  {off_diag.min():.1f} min")
    print(f"  Mean: {off_diag.mean():.1f} min")
    print(f"  Max:  {off_diag.max():.1f} min")

    reachable_10 = (matrix_df[(matrix_df > 0) & (matrix_df <= 10)].count().sum())
    print(f"  Zone pairs within 10-min repositioning limit: {reachable_10}/{10*9}")

    print("\n[Generated Files]")
    files = [
        ("OSM Road Graph",   PATHS["osm_graph"]),
        ("Zone GeoJSON",     PATHS["zone_geojson"]),
        ("Travel Matrix",    PATHS["travel_matrix"]),
        ("Zone Map (HTML)",  PATHS["outputs_maps"] / "zone_map.html"),
    ]
    for name, path in files:
        if path.exists():
            size = path.stat().st_size / 1024
            print(f"  {name:<22} {size:>8.1f} KB  {path.name}")
        else:
            print(f"  {name:<22} MISSING")

    print("=" * 65)

def main(force_download: bool = False) -> None:
    start_total = time.perf_counter()
    results: dict[int, bool] = {}

    log.info("=" * 58)
    log.info("  PHASE 1: GEOSPATIAL FOUNDATION")
    log.info("  7COSC013W.1 Foundations of AI")
    log.info("=" * 58)

    t0 = time.perf_counter()
    G, G_stats = run_step_1_graph(force_download=force_download)
    results[1] = G is not None
    log.info(f"Step 1: {'PASS' if results[1] else 'FAIL'} ({time.perf_counter()-t0:.1f}s)")

    t0 = time.perf_counter()
    run_step_2_zones(matrix_df=None)
    results[2] = PATHS["zone_geojson"].exists()
    log.info(f"Step 2: {'PASS' if results[2] else 'FAIL'} ({time.perf_counter()-t0:.1f}s)")

    t0 = time.perf_counter()
    matrix_df, matrix_ok = run_step_3_matrix(G)
    results[3] = matrix_ok
    log.info(f"Step 3: {'PASS' if results[3] else 'FAIL'} ({time.perf_counter()-t0:.1f}s)")

    from zone_builder import create_zone_map, save_zone_map
    m = create_zone_map(matrix_df=matrix_df)
    save_zone_map(m, "zone_map.html")
    log.info("Zone map updated with travel-time popup data")

    t0 = time.perf_counter()
    cross_ok = run_step_4_validate(G_stats, matrix_df)
    results[4] = cross_ok
    log.info(f"Step 4: {'PASS' if results[4] else 'FAIL'} ({time.perf_counter()-t0:.1f}s)")

    total_elapsed = time.perf_counter() - start_total
    passed = sum(results.values())
    total  = len(results)

    print("\n" + "=" * 58)
    print(f"  PHASE 1 RESULTS: {passed}/{total} steps passed ({total_elapsed:.1f}s)")
    for s, ok in results.items():
        print(f"    Step {s}: {'PASS' if ok else 'FAIL'}")

    if passed == total:
        print("  STATUS: Phase 1 complete. Ready for Phase 3.")
    else:
        print("  STATUS: Fix FAIL steps above, then re-run.")
    print("=" * 58)

    if passed == total:
        print_phase1_summary(G_stats, matrix_df)

    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 1: Geospatial Foundation")
    parser.add_argument(
        "--force", action="store_true",
        help="Force re-download of OSM graph (ignores cache)"
    )
    args = parser.parse_args()
    main(force_download=args.force)
