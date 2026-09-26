
from __future__ import annotations
import sys
import time
import importlib
from pathlib import Path

REQUIRED_PACKAGES = [

    ("osmnx",                 "osmnx",           "OSM road graph download & travel-time matrix"),
    ("networkx",              "networkx",        "Shortest-path algorithms (Dijkstra)"),
    ("geopandas",             "geopandas",       "Spatial joins, GeoJSON I/O"),
    ("shapely",               "shapely",         "Zone polygon geometry"),
    ("pyproj",                "pyproj",          "CRS projection (WGS84 to/from UTM Zone 44N)"),
    ("folium",                "folium",          "Interactive map visualisation"),
    ("pandas",                "pandas",          "DataFrames, CSV I/O"),
    ("numpy",                 "numpy",           "Numerical arrays"),
    ("scipy",                 "scipy",           "Gini coefficient, statistics"),
    ("beautifulsoup4",        "bs4",             "HTML parsing for event scraper"),
    ("requests",              "requests",        "HTTP client"),
    ("requests-cache",        "requests_cache",  "API response caching"),
    ("matplotlib",            "matplotlib",      "Static plots"),
    ("seaborn",               "seaborn",         "Statistical visualisations"),
    ("jupyter",               "jupyter",         "Notebook server"),
    ("pytest",                "pytest",          "Unit test runner"),
    ("tqdm",                  "tqdm",            "Progress bars"),
    ("colorlog",              "colorlog",        "Coloured log output"),
    ("tabulate",              "tabulate",        "Terminal table formatting"),
    ("python-dateutil",       "dateutil",        "Date parsing"),
    ("pytz",                  "pytz",            "Timezone handling (Asia/Colombo)"),
]

OPTIONAL_PACKAGES = [
    ("openmeteo-requests",    "openmeteo_requests", "Open-Meteo weather API client"),
    ("retry-requests",        "retry_requests",      "Retry with exponential backoff"),
]

def check_python_version() -> bool:
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 11):
        print(f"  [FAIL] Python {major}.{minor} — need 3.11+")
        return False
    print(f"  [PASS] Python {major}.{minor}.{sys.version_info.micro}")
    return True

def check_package(pip_name: str, import_name: str, purpose: str) -> bool:
    try:
        mod = importlib.import_module(import_name)
        version = getattr(mod, "__version__", "unknown")
        print(f"  [PASS] {pip_name:<25} v{version:<12}  {purpose}")
        return True
    except ImportError:
        print(f"  [FAIL] {pip_name:<25} {'NOT INSTALLED':<12}  {purpose}")
        print(f"         Fix: pip install {pip_name}")
        return False

def check_config() -> bool:
    try:

        src_path = Path(__file__).parent
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        from config import validate_config, ZONES, ZONE_IDS, FLEET_DISTRIBUTIONS
        ok = validate_config()
        if ok:
            print(f"  [PASS] config.py — {len(ZONES)} zones, distributions validated")
        return ok
    except Exception as e:
        print(f"  [FAIL] config.py — {e}")
        return False

def check_directories() -> bool:
    project_root = Path(__file__).resolve().parent.parent
    required_dirs = [
        "data/raw/colombo_osm",
        "data/raw/weather_kaggle",
        "data/raw/events_scraped",
        "data/processed",
        "data/scenarios",
        "src",
        "notebooks",
        "tests",
        "logs",
        "outputs/figures",
        "outputs/maps",
        "outputs/reports",
        ".cache",
    ]
    missing = [d for d in required_dirs if not (project_root / d).exists()]
    if missing:
        print(f"  [FAIL] Missing directories: {missing}")
        return False
    print(f"  [PASS] All {len(required_dirs)} required directories exist")
    return True

def check_osmnx_connectivity() -> bool:
    try:
        import osmnx as ox

        point = ox.geocode("Colombo, Sri Lanka")
        lat, lon = point
        if 6.8 < lat < 7.1 and 79.8 < lon < 80.0:
            print(f"  [PASS] OSMnx geocoder reachable — Colombo at ({lat:.4f}, {lon:.4f})")
            return True
        else:
            print(f"  [WARN] OSMnx returned unexpected coords: ({lat}, {lon})")
            return False
    except Exception as e:
        print(f"  [WARN] OSMnx connectivity check failed: {e}")
        print("         This may indicate no internet access — Phase 1 requires connectivity.")
        return False

def check_open_meteo() -> bool:
    try:
        import requests
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": 6.9271, "longitude": 79.8612,
                "current": "precipitation", "forecast_days": 1
            },
            timeout=10
        )
        if resp.status_code == 200:
            rain = resp.json().get("current", {}).get("precipitation", "N/A")
            print(f"  [PASS] Open-Meteo API reachable — current precipitation: {rain} mm/hr")
            return True
        else:
            print(f"  [WARN] Open-Meteo returned HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"  [WARN] Open-Meteo check failed: {e}")
        return False

def main() -> None:
    start = time.perf_counter()
    results: list[bool] = []

    print("=" * 65)
    print("  COLOMBO RIDE-HAILING AI — Phase 0 Environment Sanity Check")
    print("  7COSC013W.1 Foundations of AI, University of Westminster")
    print("=" * 65)

    print("\n[1] Python Version")
    results.append(check_python_version())

    print("\n[2] Required Packages")
    for pip_name, import_name, purpose in REQUIRED_PACKAGES:
        results.append(check_package(pip_name, import_name, purpose))

    print("\n[3] Optional Packages")
    for pip_name, import_name, purpose in OPTIONAL_PACKAGES:
        check_package(pip_name, import_name, purpose)

    print("\n[4] Configuration Integrity")
    results.append(check_config())

    print("\n[5] Directory Structure")
    results.append(check_directories())

    print("\n[6] Network Connectivity (non-fatal)")
    check_osmnx_connectivity()
    check_open_meteo()

    elapsed = time.perf_counter() - start
    passed = sum(results)
    total = len(results)

    print("\n" + "=" * 65)
    print(f"  Results: {passed}/{total} checks passed  ({elapsed:.2f}s)")
    if passed == total:
        print("  STATUS: Environment ready. Proceed to Phase 1.")
    else:
        print("  STATUS: Fix the FAIL items above, then re-run this script.")
    print("=" * 65)

    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
