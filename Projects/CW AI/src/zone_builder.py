
from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any

import folium
from folium.plugins import MiniMap
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, mapping
from shapely.ops import transform
import pyproj

sys.path.insert(0, str(Path(__file__).parent))
from config import ZONES, ZONE_BY_ID, PATHS, GEO
from logger import get_logger

log = get_logger(__name__)

_WGS84_TO_UTM = pyproj.Transformer.from_crs(
    "EPSG:4326", GEO["crs_metric"], always_xy=True
)

_UTM_TO_WGS84 = pyproj.Transformer.from_crs(
    GEO["crs_metric"], "EPSG:4326", always_xy=True
)

ZONE_BUFFER_RADIUS_M = 1_000

def build_zone_polygon(zone_id: str, radius_m: int = ZONE_BUFFER_RADIUS_M) -> dict:
    zone = ZONE_BY_ID[zone_id]

    lon, lat = zone.centroid_lon, zone.centroid_lat

    easting, northing = _WGS84_TO_UTM.transform(lon, lat)
    pt_utm = Point(easting, northing)

    buffer_utm = pt_utm.buffer(radius_m, resolution=64)

    buffer_wgs84 = transform(_UTM_TO_WGS84.transform, buffer_utm)

    feature = {
        "type": "Feature",
        "geometry": mapping(buffer_wgs84),
        "properties": {
            "zone_id":       zone.id,
            "zone_name":     zone.name,
            "key_venue":     zone.key_venue,
            "centroid_lat":  zone.centroid_lat,
            "centroid_lon":  zone.centroid_lon,
            "colour":        zone.colour,
            "radius_m":      radius_m,
        },
    }
    return feature

def build_zone_geojson() -> dict:
    log.info(f"Building zone GeoJSON ({len(ZONES)} zones, radius={ZONE_BUFFER_RADIUS_M}m)...")
    features = [build_zone_polygon(z.id) for z in ZONES]
    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "description": "Colombo ride-hailing demand zones",
            "crs":         "EPSG:4326",
            "zone_count":  len(features),
            "radius_m":    ZONE_BUFFER_RADIUS_M,
        },
    }
    log.info(f"GeoJSON built: {len(features)} zone polygons")
    return geojson

def save_zone_geojson(geojson: dict) -> Path:
    out_path = PATHS["zone_geojson"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)
    size_kb = out_path.stat().st_size / 1024
    log.info(f"Zone GeoJSON saved: {out_path.name} ({size_kb:.1f} KB)")
    return out_path

def create_zone_map(
    matrix_df: pd.DataFrame | None = None,
    geojson: dict | None = None,
) -> folium.Map:
    if geojson is None:
        geojson = build_zone_geojson()

    centre_lat = (GEO["colombo_bbox"]["north"] + GEO["colombo_bbox"]["south"]) / 2
    centre_lon = (GEO["colombo_bbox"]["east"]  + GEO["colombo_bbox"]["west"])  / 2

    m = folium.Map(
        location=[centre_lat, centre_lon],
        zoom_start=13,
        tiles="CartoDB positron",
        control_scale=True,
    )

    zone_layer = folium.FeatureGroup(name="Zone Boundaries", show=True)

    for feature in geojson["features"]:
        props = feature["properties"]
        zone_id   = props["zone_id"]
        zone_name = props["zone_name"]
        colour    = props["colour"]

        popup_html = f"""
        <div style='font-family:monospace; min-width:220px'>
          <b style='color:{colour}'>{zone_id}: {zone_name}</b><br>
          <i>{props['key_venue']}</i><br>
          <small>Centroid: ({props['centroid_lat']:.4f}, {props['centroid_lon']:.4f})</small>
        """
        if matrix_df is not None and zone_id in matrix_df.index:
            popup_html += "<hr><b>Travel time (min) to other zones:</b><br><table style='font-size:11px'>"
            row = matrix_df.loc[zone_id]
            for target_zone, t_min in sorted(row.items()):
                if target_zone != zone_id:
                    popup_html += f"<tr><td>{target_zone}</td><td>{t_min:.1f} min</td></tr>"
            popup_html += "</table>"
        popup_html += "</div>"

        folium.GeoJson(
            feature,
            style_function=lambda f, col=colour: {
                "fillColor":   col,
                "color":       col,
                "weight":      2,
                "fillOpacity": 0.20,
                "opacity":     0.80,
            },
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"{zone_id}: {zone_name}",
        ).add_to(zone_layer)

    zone_layer.add_to(m)

    marker_layer = folium.FeatureGroup(name="Zone Centroids", show=True)

    for zone in ZONES:

        popup_html = f"""
        <b style='color:{zone.colour}'>{zone.id}: {zone.name}</b><br>
        <i>{zone.key_venue}</i>
        """
        folium.CircleMarker(
            location=[zone.centroid_lat, zone.centroid_lon],
            radius=10,
            color=zone.colour,
            fill=True,
            fill_color=zone.colour,
            fill_opacity=0.90,
            popup=folium.Popup(popup_html, max_width=200),
            tooltip=f"{zone.id}: {zone.name}",
        ).add_to(marker_layer)

        folium.Marker(
            location=[zone.centroid_lat, zone.centroid_lon],
            icon=folium.DivIcon(
                html=f"<div style='font-size:9px;font-weight:bold;"
                     f"color:white;text-shadow:0 0 3px black;'>{zone.id}</div>",
                icon_size=(30, 12),
                icon_anchor=(15, 6),
            ),
        ).add_to(marker_layer)

    marker_layer.add_to(m)

    legend_html = """
    <div style='position:fixed;bottom:30px;left:30px;z-index:9999;
                background-color:white;padding:10px;border:1px solid #ccc;
                border-radius:5px;font-family:monospace;font-size:12px'>
      <b>Colombo Demand Zones</b><br>
    """
    for zone in ZONES:
        legend_html += (
            f"<span style='display:inline-block;width:12px;height:12px;"
            f"background-color:{zone.colour};margin-right:5px;'></span>"
            f"{zone.id}: {zone.name}<br>"
        )
    legend_html += "</div>"
    m.get_root().html.add_child(folium.Element(legend_html))

    MiniMap(toggle_display=True).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    return m

def save_zone_map(m: folium.Map, filename: str = "zone_map.html") -> Path:
    out_path = PATHS["outputs_maps"] / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out_path))
    size_kb = out_path.stat().st_size / 1024
    log.info(f"Zone map saved: {out_path.name} ({size_kb:.1f} KB)")
    return out_path

def validate_zone_geojson(geojson: dict) -> bool:
    checks = {
        "Is FeatureCollection":       geojson.get("type") == "FeatureCollection",
        f"Exactly {len(ZONES)} features": len(geojson.get("features", [])) == len(ZONES),
        "All features have geometry": all(
            f.get("geometry") is not None for f in geojson.get("features", [])
        ),
        "All geometries are Polygons": all(
            f["geometry"]["type"] == "Polygon"
            for f in geojson.get("features", [])
        ),
        "All zone IDs present":       set(
            f["properties"]["zone_id"] for f in geojson.get("features", [])
        ) == set(z.id for z in ZONES),
        "All colours present":        all(
            f["properties"].get("colour") for f in geojson.get("features", [])
        ),
    }

    all_pass = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        log.info(f"  [{status}] {check}")
        if not passed:
            all_pass = False
    return all_pass

def prepare_zones(matrix_df: pd.DataFrame | None = None) -> dict:
    geojson = build_zone_geojson()
    validate_zone_geojson(geojson)
    save_zone_geojson(geojson)

    m = create_zone_map(matrix_df=matrix_df, geojson=geojson)
    save_zone_map(m, "zone_map.html")

    return geojson

if __name__ == "__main__":
    gj = prepare_zones()
    print(f"\nZone GeoJSON: {len(gj['features'])} features")
    for f in gj["features"]:
        p = f["properties"]
        print(f"  {p['zone_id']}: {p['zone_name']} — {p['key_venue']}")
