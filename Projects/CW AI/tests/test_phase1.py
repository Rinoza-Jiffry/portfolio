
from __future__ import annotations

import sys
import json
from pathlib import Path

import pytest
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import ZONES, ZONE_IDS, ZONE_CENTROIDS, PATHS, POSITIONING, GEO

def matrix_available() -> bool:
    return PATHS["travel_matrix"].exists()

def geojson_available() -> bool:
    return PATHS["zone_geojson"].exists()

def graphml_available() -> bool:
    return PATHS["osm_graph"].exists()

skip_no_matrix  = pytest.mark.skipif(not matrix_available(),  reason="Travel-time matrix not generated yet")
skip_no_geojson = pytest.mark.skipif(not geojson_available(), reason="Zone GeoJSON not generated yet")
skip_no_graph   = pytest.mark.skipif(not graphml_available(), reason="OSM graph not downloaded yet")

class TestZoneConfiguration:

    def test_exactly_10_zones(self):
        assert len(ZONES) == 10

    def test_zone_ids_are_z1_to_z10(self):
        expected = {f"Z{i}" for i in range(1, 11)}
        assert set(ZONE_IDS) == expected

    def test_zone_centroids_within_colombo_bbox(self):
        bbox = GEO["colombo_bbox"]
        for zone in ZONES:
            assert bbox["south"] <= zone.centroid_lat <= bbox["north"], \
                f"{zone.id} lat {zone.centroid_lat} outside bbox"
            assert bbox["west"] <= zone.centroid_lon <= bbox["east"], \
                f"{zone.id} lon {zone.centroid_lon} outside bbox"

    def test_zone_centroids_are_unique(self):
        centroids = [(z.centroid_lat, z.centroid_lon) for z in ZONES]
        assert len(set(centroids)) == len(centroids), "Duplicate zone centroids"

    def test_zone_colours_are_hex(self):
        import re
        for zone in ZONES:
            assert re.match(r"^#[0-9A-Fa-f]{6}$", zone.colour), \
                f"{zone.id} has invalid colour: {zone.colour}"

    def test_zone_colours_are_unique(self):
        colours = [z.colour for z in ZONES]
        assert len(set(colours)) == len(colours), "Duplicate zone colours"

    def test_zone_names_non_empty(self):
        for zone in ZONES:
            assert zone.name.strip(), f"{zone.id} has empty name"
            assert zone.key_venue.strip(), f"{zone.id} has empty key_venue"

class TestColomboBoundingBox:

    def test_kelaniya_within_bbox(self):
        z8 = next(z for z in ZONES if z.id == "Z8")
        bbox = GEO["colombo_bbox"]
        assert z8.centroid_lat < bbox["north"]
        assert z8.centroid_lon < bbox["east"]

    def test_nugegoda_within_bbox(self):
        z6 = next(z for z in ZONES if z.id == "Z6")
        bbox = GEO["colombo_bbox"]
        assert z6.centroid_lat > bbox["south"]

    def test_bbox_area_is_reasonable(self):
        bbox = GEO["colombo_bbox"]
        lat_span = bbox["north"] - bbox["south"]
        lon_span = bbox["east"]  - bbox["west"]

        area_km2 = lat_span * 111 * lon_span * 110.2
        assert 50 < area_km2 < 2000, \
            f"Bounding box area {area_km2:.0f} km² outside expected range"

class TestRainfallClassifier:

    def test_boundary_conditions(self):
        from weather_prep import classify_rainfall
        assert classify_rainfall(0.0) == "none"
        assert classify_rainfall(2.5) == "moderate"
        assert classify_rainfall(5.0) == "heavy"

class TestGeodeticBuffering:

    def test_polygon_is_approximately_circular(self):
        from zone_builder import build_zone_polygon
        from shapely.geometry import shape

        feature = build_zone_polygon("Z1", radius_m=1000)
        polygon = shape(feature["geometry"])

        minx, miny, maxx, maxy = polygon.bounds
        lon_span = maxx - minx
        lat_span = maxy - miny

        lon_m = lon_span * 111_000 * abs(np.cos(np.radians((miny + maxy) / 2)))
        lat_m = lat_span * 111_000
        aspect_ratio = lon_m / lat_m
        assert 0.85 < aspect_ratio < 1.15, \
            f"Zone polygon aspect ratio {aspect_ratio:.3f} too far from circular"

    def test_polygon_centroid_near_zone_centroid(self):
        from zone_builder import build_zone_polygon
        from shapely.geometry import shape

        zone = next(z for z in ZONES if z.id == "Z2")
        feature = build_zone_polygon("Z2", radius_m=1000)
        polygon = shape(feature["geometry"])
        poly_centroid = polygon.centroid

        dlat = abs(poly_centroid.y - zone.centroid_lat) * 111_000
        dlon = abs(poly_centroid.x - zone.centroid_lon) * 111_000 * np.cos(
            np.radians(zone.centroid_lat)
        )
        dist_m = np.sqrt(dlat**2 + dlon**2)
        assert dist_m < 100, f"Polygon centroid {dist_m:.1f}m from zone centroid"

    def test_all_10_polygons_build_without_error(self):
        from zone_builder import build_zone_polygon
        for zone in ZONES:
            feature = build_zone_polygon(zone.id)
            assert feature["type"] == "Feature"
            assert feature["geometry"]["type"] == "Polygon"
            assert feature["properties"]["zone_id"] == zone.id

class TestMatrixValidationLogic:

    def _make_valid_matrix(self) -> pd.DataFrame:
        np.random.seed(42)
        raw = np.random.uniform(5, 35, (10, 10))
        np.fill_diagonal(raw, 0)
        df = pd.DataFrame(raw, index=ZONE_IDS, columns=ZONE_IDS)
        return df.round(1)

    def test_valid_matrix_passes(self):
        from travel_time_matrix import validate_matrix
        df = self._make_valid_matrix()
        assert validate_matrix(df) is True

    def test_non_zero_diagonal_fails(self):
        from travel_time_matrix import validate_matrix
        df = self._make_valid_matrix()
        df.loc["Z1", "Z1"] = 5.0
        assert validate_matrix(df) is False

    def test_nan_value_fails(self):
        from travel_time_matrix import validate_matrix
        df = self._make_valid_matrix()
        df.loc["Z2", "Z3"] = float("nan")
        assert validate_matrix(df) is False

    def test_sentinel_value_fails(self):
        from travel_time_matrix import validate_matrix
        from travel_time_matrix import UNREACHABLE_SENTINEL
        df = self._make_valid_matrix()
        df.loc["Z5", "Z8"] = UNREACHABLE_SENTINEL
        assert validate_matrix(df) is False

class TestDijkstraProperties:

    def test_triangle_inequality_holds_approximately(self):

        np.random.seed(0)
        n = 10

        adj = np.random.uniform(1, 20, (n, n))
        np.fill_diagonal(adj, 0)

        adj = (adj + adj.T) / 2

        dist = adj.copy()
        for k in range(n):
            for i in range(n):
                for j in range(n):
                    dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])

        df = pd.DataFrame(dist, index=ZONE_IDS, columns=ZONE_IDS)

        violations = 0
        for a in ZONE_IDS:
            for b in ZONE_IDS:
                for c in ZONE_IDS:
                    if a != b and b != c and a != c:
                        if df.loc[a, c] > df.loc[a, b] + df.loc[b, c] + 0.1:
                            violations += 1
        assert violations == 0, \
            f"Triangle inequality violated {violations} times (synthetic matrix)"

    def test_repositioning_limit_is_meaningful(self):
        limit_min = POSITIONING["reposition_limit_min"]
        avg_speed_kmh = 25
        distance_km = avg_speed_kmh * (limit_min / 60)
        assert 3.0 < distance_km < 8.0, \
            f"10-min limit covers {distance_km:.1f} km — outside expected Colombo range"

class TestGeneratedMatrix:

    @pytest.fixture(scope="class")
    def matrix(self):
        df = pd.read_csv(PATHS["travel_matrix"], index_col=0)
        return df

    @skip_no_matrix
    def test_shape_is_10x10(self, matrix):
        assert matrix.shape == (10, 10)

    @skip_no_matrix
    def test_all_zone_ids_present(self, matrix):
        assert set(matrix.index)   == set(ZONE_IDS)
        assert set(matrix.columns) == set(ZONE_IDS)

    @skip_no_matrix
    def test_diagonal_is_zero(self, matrix):
        for z in ZONE_IDS:
            assert matrix.loc[z, z] == 0.0, f"Diagonal {z} = {matrix.loc[z, z]}"

    @skip_no_matrix
    def test_no_nan_values(self, matrix):
        assert not matrix.isna().any().any()

    @skip_no_matrix
    def test_all_off_diagonal_positive(self, matrix):
        for r in ZONE_IDS:
            for c in ZONE_IDS:
                if r != c:
                    assert matrix.loc[r, c] > 0, \
                        f"Non-positive travel time: {r}→{c} = {matrix.loc[r, c]}"

    @skip_no_matrix
    def test_all_within_colombo_range(self, matrix):
        off_diag = matrix.values[matrix.values > 0]
        assert off_diag.max() < 60.0, \
            f"Max travel time {off_diag.max():.1f} min exceeds Colombo range"

    @skip_no_matrix
    def test_some_pairs_within_reposition_limit(self, matrix):
        limit = POSITIONING["reposition_limit_min"]
        within_limit = matrix[(matrix > 0) & (matrix <= limit)].count().sum()
        assert within_limit > 0, \
            f"No zone pairs within {limit}-minute repositioning limit"

    @skip_no_matrix
    def test_fort_and_kollupitiya_are_close(self, matrix):
        t = matrix.loc["Z1", "Z2"]
        assert 2.0 < t < 20.0, \
            f"Z1→Z2 travel time {t:.1f} min outside expected 2-20 min range"

    @skip_no_matrix
    def test_kelaniya_to_nugegoda_is_longer(self, matrix):
        t_far  = matrix.loc["Z8", "Z6"]
        t_near = matrix.loc["Z1", "Z2"]
        assert t_far > t_near, \
            f"Z8→Z6 ({t_far:.1f} min) should be > Z1→Z2 ({t_near:.1f} min)"

    @skip_no_matrix
    def test_approximate_symmetry(self, matrix):
        asymmetries = []
        for r in ZONE_IDS:
            for c in ZONE_IDS:
                if r < c:
                    asym = abs(matrix.loc[r, c] - matrix.loc[c, r])
                    asymmetries.append(asym)
        max_asym = max(asymmetries)
        mean_asym = np.mean(asymmetries)
        assert mean_asym < 8.0, \
            f"Mean asymmetry {mean_asym:.1f} min too high (expected < 8 min)"

class TestGeneratedGeoJSON:

    @pytest.fixture(scope="class")
    def geojson(self):
        with open(PATHS["zone_geojson"], encoding="utf-8") as f:
            return json.load(f)

    @skip_no_geojson
    def test_is_feature_collection(self, geojson):
        assert geojson["type"] == "FeatureCollection"

    @skip_no_geojson
    def test_exactly_10_features(self, geojson):
        assert len(geojson["features"]) == 10

    @skip_no_geojson
    def test_all_geometries_are_polygons(self, geojson):
        for f in geojson["features"]:
            assert f["geometry"]["type"] == "Polygon"

    @skip_no_geojson
    def test_all_zone_ids_present(self, geojson):
        ids = {f["properties"]["zone_id"] for f in geojson["features"]}
        assert ids == set(ZONE_IDS)

    @skip_no_geojson
    def test_zone_polygons_within_colombo(self, geojson):
        bbox = GEO["colombo_bbox"]
        margin = 0.05
        for f in geojson["features"]:
            coords = f["geometry"]["coordinates"][0]
            for lon, lat in coords:
                assert bbox["west"] - margin <= lon <= bbox["east"]  + margin
                assert bbox["south"] - margin <= lat <= bbox["north"] + margin

class TestGeneratedGraph:

    @skip_no_graph
    def test_graph_has_minimum_nodes(self):
        import osmnx as ox
        G = ox.load_graphml(str(PATHS["osm_graph"]))
        assert G.number_of_nodes() >= 10_000, \
            f"Graph only has {G.number_of_nodes()} nodes — possibly incomplete download"

    @skip_no_graph
    def test_graph_has_travel_time_attribute(self):
        import osmnx as ox
        G = ox.load_graphml(str(PATHS["osm_graph"]))
        sample = list(G.edges(data=True))[:20]
        for u, v, data in sample:
            assert "travel_time" in data, \
                f"Edge ({u},{v}) missing travel_time attribute"

    @skip_no_graph
    def test_zone_centroids_have_nearby_nodes(self):
        import osmnx as ox
        G = ox.load_graphml(str(PATHS["osm_graph"]))
        for zone in ZONES:
            node_id = ox.nearest_nodes(G, X=zone.centroid_lon, Y=zone.centroid_lat)
            node_data = G.nodes[node_id]

            dlat = abs(node_data["y"] - zone.centroid_lat) * 111_000
            dlon = abs(node_data["x"] - zone.centroid_lon) * 111_000 * 0.992
            dist_m = (dlat**2 + dlon**2) ** 0.5
            assert dist_m < 1000, \
                f"{zone.id} nearest node is {dist_m:.0f}m away (>1000m threshold)"
