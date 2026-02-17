"""IFC Model Analyzer for Slab and Foundation Analysis."""

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.unit
from typing import Dict, List, Any, Optional


class IFCAnalyzer:
    """Analyzes IFC models to extract slab and foundation information."""

    def __init__(self, ifc_path: str):
        """Initialize the analyzer with an IFC file path."""
        self.model = ifcopenshell.open(ifc_path)
        self.length_scale = self._get_length_scale()

    def _get_length_scale(self) -> float:
        """Get the length unit scale factor (converts to meters)."""
        try:
            units = self.model.by_type("IfcUnitAssignment")
            if units:
                for unit in units[0].Units:
                    if hasattr(unit, 'UnitType') and unit.UnitType == 'LENGTHUNIT':
                        if hasattr(unit, 'Prefix') and unit.Prefix:
                            # Handle prefixes like MILLI
                            prefix_map = {
                                'MILLI': 0.001,
                                'CENTI': 0.01,
                                'DECI': 0.1,
                                'KILO': 1000.0
                            }
                            return prefix_map.get(unit.Prefix, 1.0)
            return 1.0  # Default to meters
        except:
            return 1.0

    def get_slabs(self) -> List[Dict[str, Any]]:
        """Extract all slab elements from the IFC model."""
        slabs = []

        for slab in self.model.by_type("IfcSlab"):
            slab_data = {
                'id': slab.GlobalId,
                'name': slab.Name or 'Unnamed Slab',
                'type': self._get_slab_predefined_type(slab),
                'thickness': self._get_slab_thickness(slab),
                'elevation': self._get_element_elevation(slab),
                'area': self._get_element_area(slab),
                'material': self._get_element_material(slab),
                'load_capacity': self._estimate_load_capacity(slab)
            }
            slabs.append(slab_data)

        return slabs

    def get_foundations(self) -> List[Dict[str, Any]]:
        """Extract all foundation elements from the IFC model."""
        foundations = []

        # Check for IfcFooting elements
        for footing in self.model.by_type("IfcFooting"):
            foundation_data = {
                'id': footing.GlobalId,
                'name': footing.Name or 'Unnamed Foundation',
                'type': 'Footing',
                'thickness': self._get_element_thickness(footing),
                'elevation': self._get_element_elevation(footing),
                'area': self._get_element_area(footing),
                'material': self._get_element_material(footing),
            }
            foundations.append(foundation_data)

        # Also check for foundation slabs
        for slab in self.model.by_type("IfcSlab"):
            predefined_type = self._get_slab_predefined_type(slab)
            if predefined_type and 'BASESLAB' in predefined_type.upper():
                foundation_data = {
                    'id': slab.GlobalId,
                    'name': slab.Name or 'Foundation Slab',
                    'type': 'Base Slab',
                    'thickness': self._get_slab_thickness(slab),
                    'elevation': self._get_element_elevation(slab),
                    'area': self._get_element_area(slab),
                    'material': self._get_element_material(slab),
                }
                foundations.append(foundation_data)

        return foundations

    def _get_slab_predefined_type(self, slab) -> str:
        """Get the predefined type of a slab."""
        if hasattr(slab, 'PredefinedType') and slab.PredefinedType:
            return slab.PredefinedType

        if hasattr(slab, 'ObjectType') and slab.ObjectType:
            return slab.ObjectType

        return 'FLOOR'

    def _get_slab_thickness(self, slab) -> Optional[float]:
        """Extract slab thickness from various possible locations."""
        # Try to get from material layer set
        thickness = self._get_material_layer_thickness(slab)
        if thickness:
            return round(thickness * self.length_scale * 1000, 2)  # Convert to mm

        # Try to get from property sets
        thickness = self._get_property_value(slab, 'Thickness')
        if thickness:
            return round(float(thickness) * 1000, 2)  # Assume meters, convert to mm

        # Try to get from representations
        thickness = self._get_thickness_from_representation(slab)
        if thickness:
            return round(thickness * self.length_scale * 1000, 2)  # Convert to mm

        return None

    def _get_element_thickness(self, element) -> Optional[float]:
        """Get thickness of any element."""
        # Try material layer set first
        thickness = self._get_material_layer_thickness(element)
        if thickness:
            return round(thickness * self.length_scale * 1000, 2)  # Convert to mm

        # Try property sets
        thickness = self._get_property_value(element, 'Thickness')
        if thickness:
            return round(float(thickness) * 1000, 2)

        return None

    def _get_material_layer_thickness(self, element) -> Optional[float]:
        """Get thickness from material layer set."""
        try:
            if hasattr(element, 'HasAssociations'):
                for rel in element.HasAssociations:
                    if rel.is_a('IfcRelAssociatesMaterial'):
                        material = rel.RelatingMaterial

                        if material.is_a('IfcMaterialLayerSetUsage'):
                            layer_set = material.ForLayerSet
                            total_thickness = sum(layer.LayerThickness for layer in layer_set.MaterialLayers)
                            return total_thickness

                        elif material.is_a('IfcMaterialLayerSet'):
                            total_thickness = sum(layer.LayerThickness for layer in material.MaterialLayers)
                            return total_thickness
        except:
            pass

        return None

    def _get_thickness_from_representation(self, element) -> Optional[float]:
        """Try to extract thickness from element representation."""
        try:
            if hasattr(element, 'Representation') and element.Representation:
                for rep in element.Representation.Representations:
                    for item in rep.Items:
                        if item.is_a('IfcExtrudedAreaSolid'):
                            depth = item.Depth
                            return depth
        except:
            pass

        return None

    def _get_element_elevation(self, element) -> Optional[float]:
        """Get the elevation of an element."""
        try:
            if hasattr(element, 'ObjectPlacement'):
                placement = element.ObjectPlacement
                if placement and placement.is_a('IfcLocalPlacement'):
                    if hasattr(placement, 'RelativePlacement'):
                        rel_placement = placement.RelativePlacement
                        if hasattr(rel_placement, 'Location'):
                            coords = rel_placement.Location.Coordinates
                            if len(coords) > 2:
                                return round(coords[2] * self.length_scale, 2)  # Z coordinate in meters
        except:
            pass

        return None

    def _get_element_area(self, element) -> Optional[float]:
        """Calculate or retrieve the area of an element."""
        # Try to get from quantity sets
        area = self._get_quantity_value(element, 'NetArea')
        if not area:
            area = self._get_quantity_value(element, 'GrossArea')

        if area:
            return round(float(area), 2)  # Assume square meters

        return None

    def _get_element_material(self, element) -> str:
        """Get the material name of an element."""
        try:
            if hasattr(element, 'HasAssociations'):
                for rel in element.HasAssociations:
                    if rel.is_a('IfcRelAssociatesMaterial'):
                        material = rel.RelatingMaterial

                        if material.is_a('IfcMaterial'):
                            return material.Name

                        elif material.is_a('IfcMaterialLayerSetUsage'):
                            layers = material.ForLayerSet.MaterialLayers
                            materials = [layer.Material.Name for layer in layers if layer.Material]
                            return ', '.join(materials)

                        elif material.is_a('IfcMaterialLayerSet'):
                            materials = [layer.Material.Name for layer in material.MaterialLayers if layer.Material]
                            return ', '.join(materials)
        except:
            pass

        return 'Unknown'

    def _get_property_value(self, element, prop_name: str) -> Optional[Any]:
        """Get a property value from property sets."""
        try:
            psets = ifcopenshell.util.element.get_psets(element)
            for pset_name, properties in psets.items():
                if prop_name in properties:
                    return properties[prop_name]
        except:
            pass

        return None

    def _get_quantity_value(self, element, quantity_name: str) -> Optional[float]:
        """Get a quantity value from quantity sets."""
        try:
            if hasattr(element, 'IsDefinedBy'):
                for definition in element.IsDefinedBy:
                    if definition.is_a('IfcRelDefinesByProperties'):
                        prop_def = definition.RelatingPropertyDefinition

                        if prop_def.is_a('IfcElementQuantity'):
                            for quantity in prop_def.Quantities:
                                if quantity.Name == quantity_name:
                                    if hasattr(quantity, 'AreaValue'):
                                        return quantity.AreaValue
                                    elif hasattr(quantity, 'LengthValue'):
                                        return quantity.LengthValue
                                    elif hasattr(quantity, 'VolumeValue'):
                                        return quantity.VolumeValue
        except:
            pass

        return None

    def _estimate_load_capacity(self, slab) -> Optional[float]:
        """Estimate load capacity based on thickness and material (simplified)."""
        thickness = self._get_slab_thickness(slab)
        material = self._get_element_material(slab)

        if not thickness:
            return None

        # Simplified load capacity estimation (kN/m²)
        # This is a very rough estimate - real calculations require structural analysis
        # Typical concrete slab: ~24 kN/m³ * thickness_in_m * safety_factor

        # Base capacity on concrete properties
        concrete_density = 24.0  # kN/m³ for reinforced concrete
        thickness_m = thickness / 1000.0  # Convert mm to m

        # Very simplified formula: self-weight + live load capacity
        # Real capacity depends on reinforcement, span, support conditions, etc.
        self_weight = concrete_density * thickness_m

        # Rough estimate of live load capacity based on thickness
        # Thicker slabs can generally carry more load
        if thickness < 100:
            live_load_capacity = 2.0  # kN/m²
        elif thickness < 150:
            live_load_capacity = 3.5  # kN/m²
        elif thickness < 200:
            live_load_capacity = 5.0  # kN/m²
        elif thickness < 250:
            live_load_capacity = 7.0  # kN/m²
        else:
            live_load_capacity = 10.0  # kN/m²

        total_capacity = self_weight + live_load_capacity

        return round(total_capacity, 2)

    def get_ground_floor_slabs(self) -> List[Dict[str, Any]]:
        """Filter and return only ground floor slabs."""
        all_slabs = self.get_slabs()

        # Filter for ground floor (typically at or near elevation 0)
        ground_slabs = []
        for slab in all_slabs:
            elevation = slab.get('elevation')
            slab_type = slab.get('type', '').upper()

            # Check if it's a floor slab at low elevation or explicitly named as ground floor
            if elevation is not None and elevation < 2.0:  # Within 2 meters of reference
                if 'FLOOR' in slab_type or 'BASESLAB' not in slab_type:
                    ground_slabs.append(slab)
            elif 'GROUND' in slab.get('name', '').upper():
                ground_slabs.append(slab)

        return ground_slabs if ground_slabs else all_slabs[:3]  # Return first 3 if no ground floor found
