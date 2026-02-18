"""
IFC Wall Compliance Checker

This module analyzes IFC wall elements and generates compliance reports
including dimensions, properties, and requirements.
"""

import ifcopenshell
import ifcopenshell.util.element as Element

from extractor import extract_walls
from rules import rule_min_thickness
from report import make_report

def run(ifc_path):
    model = ifcopenshell.open(ifc_path)
    walls = extract_walls(model)
    results = rule_min_thickness(walls, min_mm=100)
    return make_report(walls, results)

if __name__ == "__main__":
    import sys
    for line in run(sys.argv[1]):
        print(line)

