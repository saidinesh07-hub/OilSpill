"""Tests for demo/synthetic data labeling integrity."""
import pytest
from backend.app.services.demo_sar_generator import generate_demo_sar_scene
from backend.app.environmental.cmems_adapter import CMEMSAdapter
from backend.app.environmental.era5_gfs_adapter import WindForcingAdapter
from datetime import datetime, timezone


def test_demo_sar_generator_labels():
    sar, meta = generate_demo_sar_scene(seed=1)
    assert meta["data_mode"] == "DEMO_DATA"
    assert "SYNTHETIC" in meta["data_provenance"]
    assert sar.shape == (512, 512)


def test_environmental_adapters_demo_mode_without_credentials():
    bbox = [80.25, 13.15, 80.45, 13.35]
    t = datetime(2017, 1, 28, tzinfo=timezone.utc)

    cmems = CMEMSAdapter(username=None, password=None)
    currents = cmems.get_surface_currents(bbox, t)
    assert currents["data_mode"] == "DEMO_DATA"
    assert "SYNTHETIC" in currents["data_provenance"]

    wind = WindForcingAdapter(api_key=None)
    winds = wind.get_surface_winds(bbox, t)
    assert winds["data_mode"] == "DEMO_DATA"
