import numpy as np
import pytest

from tripwire.mapview import MAX_ZOOM, MIN_ZOOM, fit_view


def test_world_spanning_points_get_the_minimum_zoom():
    v = fit_view([-170, 170, 0, 20], [-50, 60, 0, 10])
    assert v["zoom"] == MIN_ZOOM


def test_small_cluster_zooms_in_and_centres_on_it():
    lons = np.linspace(30.0, 31.0, 50)  # about 1 degree wide
    lats = np.linspace(50.0, 50.5, 50)
    v = fit_view(lons, lats)
    assert 5 < v["zoom"] <= MAX_ZOOM
    assert v["longitude"] == pytest.approx(30.5, abs=0.1)
    assert v["latitude"] == pytest.approx(50.25, abs=0.1)


def test_one_stray_far_point_does_not_zoom_everything_out():
    lons = [30 + i / 100 for i in range(200)] + [-120]  # 1 outlier in 201 points
    lats = [50 + i / 200 for i in range(200)] + [-40]
    assert fit_view(lons, lats)["zoom"] > 4


def test_single_point_and_empty():
    assert fit_view([10.0], [20.0])["zoom"] == MAX_ZOOM
    assert fit_view([], [])["zoom"] == MIN_ZOOM
