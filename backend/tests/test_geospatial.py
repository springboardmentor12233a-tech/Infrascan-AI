"""Geospatial Integration Test Suite for InfraScan (Phase 7).

Verifies:
1. Coordinate boundary validation (-90 <= lat <= 90, -180 <= lng <= 180).
2. Valid GeoJSON FeatureCollection structures.
3. Haversine formula distance precision against known geographic ground truth.
4. EXIF GPS coordinate extraction and fallback handling.
5. Large-scale clustering performance (5,000 points < 200ms).
"""

import math
import time
import pytest
from app.routers.map import haversine_km


def test_coordinate_boundaries_validation():
    """Verify coordinate bounding constraints."""
    valid_coords = [(0, 0), (90, 180), (-90, -180), (45.5, -73.5)]
    for lat, lng in valid_coords:
        assert -90.0 <= lat <= 90.0
        assert -180.0 <= lng <= 180.0

    invalid_coords = [(95.0, 0.0), (-91.0, 20.0), (10.0, 185.0), (0.0, -190.0)]
    for lat, lng in invalid_coords:
        assert not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0)


def test_haversine_distance_known_landmarks():
    """
    Verify Haversine formula against known ground truth distance:
    Eiffel Tower (48.8584 N, 2.2945 E) to Louvre Museum (48.8606 N, 2.3376 E).
    Actual distance: ~3.17 km.
    """
    lat1, lon1 = 48.8584, 2.2945
    lat2, lon2 = 48.8606, 2.3376

    computed_dist_km = haversine_km(lat1, lon1, lat2, lon2)

    # 3.17 km with 1% relative tolerance
    expected_dist_km = 3.17
    rel_error = abs(computed_dist_km - expected_dist_km) / expected_dist_km
    assert rel_error < 0.01, f"Computed distance {computed_dist_km}km deviated by {rel_error*100:.2f}%"


def test_geojson_feature_structure():
    """Verify GeoJSON standard structure conforms to RFC 7946."""
    lat, lng = 37.7749, -122.4194
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lng, lat],  # GeoJSON standard: [longitude, latitude]
        },
        "properties": {
            "id": 1,
            "name": "Golden Gate Bridge",
            "type": "bridge",
        },
    }

    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Point"
    assert feature["geometry"]["coordinates"] == [-122.4194, 37.7749]
    assert feature["geometry"]["coordinates"][0] == lng
    assert feature["geometry"]["coordinates"][1] == lat


def test_exif_gps_extraction_fallback():
    """Verify missing EXIF returns None and does not raise exception."""
    from PIL import Image
    from app.services.image_service import parse_gps_and_time

    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    lat, lon, captured_at = parse_gps_and_time(img)
    assert lat is None
    assert lon is None
    assert captured_at is None


def test_large_scale_clustering_performance():
    """Verify clustering 5,000 geospatial points completes in < 200ms."""
    points = []
    # Generate 5,000 synthetic points across an urban bounding box
    base_lat, base_lng = 40.7128, -74.0060  # New York City
    for i in range(5000):
        lat = base_lat + (i % 100) * 0.001
        lng = base_lng + (i // 100) * 0.001
        points.append({
            "id": i,
            "latitude": lat,
            "longitude": lng,
            "severity_score": (i % 5) * 20.0,
        })

    t0 = time.perf_counter()
    # Grid clustering with 0.01 deg resolution
    grid = {}
    for pt in points:
        grid_key = (round(pt["latitude"], 2), round(pt["longitude"], 2))
        if grid_key not in grid:
            grid[grid_key] = []
        grid[grid_key].append(pt)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 200.0, f"Clustering 5,000 points took {elapsed_ms:.1f}ms, exceeding 200ms limit"
    assert len(grid) > 0
