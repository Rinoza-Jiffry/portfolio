"""
setup.py
========
Makes the `src/` directory importable as a package from notebooks and tests.

Install in editable mode (development):
    pip install -e .

This lets Jupyter notebooks import from `src/` without path manipulation:
    from config import ZONES
    from demand_rule_base import evaluate_demand
"""

from setuptools import setup, find_packages

setup(
    name="colombo_ridehailing_ai",
    version="0.1.0",
    author="Rinoza Jiffry",
    description=(
        "Event-Aware Proactive Driver Positioning & Rule-Based Dynamic Pricing "
        "— 7COSC013W.1 Foundations of AI, University of Westminster"
    ),
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        # Core dependencies (see requirements.txt for pinned versions)
        "osmnx", "networkx", "geopandas", "shapely",
        "pandas", "numpy", "scipy",
        "beautifulsoup4", "requests", "requests-cache", "retry-requests",
        "openmeteo-requests",
        "matplotlib", "folium",
        "jupyter", "ipykernel",
    ],
)
