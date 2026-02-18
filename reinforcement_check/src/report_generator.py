"""Report Generator for IFC Analysis Results."""

from typing import Dict, List, Any
from datetime import datetime


class ReportGenerator:
    """Generates formatted reports for IFC analysis results."""

    @staticmethod
    def generate_slab_foundation_report(
        slabs: List[Dict[str, Any]],
        foundations: List[Dict[str, Any]],
        ground_slabs: List[Dict[str, Any]],
        ifc_filename: str
    ) -> str:
        """Generate a comprehensive report on slabs and foundations."""

        report_lines = []

        # Header
        report_lines.append("=" * 80)
        report_lines.append("IFC STRUCTURAL ANALYSIS REPORT")
        report_lines.append("Reinforcement & Load Capacity Analysis")
        report_lines.append("=" * 80)
        report_lines.append(f"\nFile: {ifc_filename}")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("\n" + "-" * 80)

        # Executive Summary
        report_lines.append("\n📊 EXECUTIVE SUMMARY")
        report_lines.append("-" * 80)
        report_lines.append(f"Total Slabs Found: {len(slabs)}")
        report_lines.append(f"Ground Floor Slabs: {len(ground_slabs)}")
        report_lines.append(f"Foundation Elements: {len(foundations)}")

        # Ground Floor Slab Analysis
        if ground_slabs:
            report_lines.append("\n" + "=" * 80)
            report_lines.append("🏢 GROUND FLOOR SLAB ANALYSIS")
            report_lines.append("=" * 80)

            for idx, slab in enumerate(ground_slabs, 1):
                report_lines.append(f"\n--- Ground Floor Slab #{idx} ---")
                report_lines.append(f"Name: {slab['name']}")
                report_lines.append(f"ID: {slab['id']}")
                report_lines.append(f"Type: {slab['type']}")

                if slab['thickness']:
                    report_lines.append(f"✓ Thickness: {slab['thickness']} mm")
                    # Provide assessment
                    if slab['thickness'] < 100:
                        report_lines.append("  ⚠️  WARNING: Thickness below typical minimum (100mm)")
                    elif slab['thickness'] < 150:
                        report_lines.append("  ℹ️  NOTE: Suitable for light residential use")
                    elif slab['thickness'] < 200:
                        report_lines.append("  ✓ GOOD: Adequate for standard residential/commercial")
                    else:
                        report_lines.append("  ✓ EXCELLENT: Heavy-duty structural capacity")
                else:
                    report_lines.append("✗ Thickness: Not available in model")

                if slab['load_capacity']:
                    report_lines.append(f"✓ Estimated Load Capacity: {slab['load_capacity']} kN/m²")
                    # Provide context
                    report_lines.append(f"  (Includes self-weight + live load capacity)")

                    if slab['load_capacity'] < 5.0:
                        report_lines.append("  ⚠️  WARNING: Low capacity - verify structural design")
                    elif slab['load_capacity'] < 8.0:
                        report_lines.append("  ℹ️  NOTE: Suitable for residential use (typical: 2-5 kN/m²)")
                    else:
                        report_lines.append("  ✓ GOOD: Suitable for commercial/industrial use")
                else:
                    report_lines.append("✗ Load Capacity: Cannot estimate without thickness data")

                if slab['elevation'] is not None:
                    report_lines.append(f"Elevation: {slab['elevation']} m")

                if slab['area']:
                    report_lines.append(f"Area: {slab['area']} m²")

                if slab['material']:
                    report_lines.append(f"Material: {slab['material']}")

        else:
            report_lines.append("\n⚠️  No ground floor slabs identified in the model")

        # Foundation Analysis
        if foundations:
            report_lines.append("\n" + "=" * 80)
            report_lines.append("🏗️  FOUNDATION ANALYSIS")
            report_lines.append("=" * 80)

            for idx, foundation in enumerate(foundations, 1):
                report_lines.append(f"\n--- Foundation Element #{idx} ---")
                report_lines.append(f"Name: {foundation['name']}")
                report_lines.append(f"ID: {foundation['id']}")
                report_lines.append(f"Type: {foundation['type']}")

                if foundation['thickness']:
                    report_lines.append(f"✓ Thickness: {foundation['thickness']} mm")
                    # Foundation thickness assessment
                    if foundation['thickness'] < 200:
                        report_lines.append("  ⚠️  WARNING: Unusually thin for foundation")
                    elif foundation['thickness'] < 300:
                        report_lines.append("  ℹ️  NOTE: Minimum acceptable for light structures")
                    elif foundation['thickness'] < 500:
                        report_lines.append("  ✓ GOOD: Standard foundation thickness")
                    else:
                        report_lines.append("  ✓ EXCELLENT: Heavy-duty foundation")
                else:
                    report_lines.append("✗ Thickness: Not available in model")

                if foundation['elevation'] is not None:
                    report_lines.append(f"Elevation: {foundation['elevation']} m")

                if foundation['area']:
                    report_lines.append(f"Area: {foundation['area']} m²")

                if foundation['material']:
                    report_lines.append(f"Material: {foundation['material']}")

        else:
            report_lines.append("\n⚠️  No foundation elements found in the model")

        # All Slabs Summary (if there are more than ground floor)
        if len(slabs) > len(ground_slabs):
            report_lines.append("\n" + "=" * 80)
            report_lines.append("📋 ALL SLABS SUMMARY")
            report_lines.append("=" * 80)

            report_lines.append(f"\n{'#':<4} {'Name':<30} {'Type':<15} {'Thickness (mm)':<16} {'Elevation (m)':<15}")
            report_lines.append("-" * 80)

            for idx, slab in enumerate(slabs, 1):
                name = slab['name'][:28] + '..' if len(slab['name']) > 30 else slab['name']
                slab_type = slab['type'][:13] + '..' if len(slab['type']) > 15 else slab['type']
                thickness = f"{slab['thickness']}" if slab['thickness'] else "N/A"
                elevation = f"{slab['elevation']}" if slab['elevation'] is not None else "N/A"

                report_lines.append(f"{idx:<4} {name:<30} {slab_type:<15} {thickness:<16} {elevation:<15}")

        # Recommendations
        report_lines.append("\n" + "=" * 80)
        report_lines.append("💡 RECOMMENDATIONS")
        report_lines.append("=" * 80)

        report_lines.append("\n1. Structural Verification:")
        report_lines.append("   - Verify all thickness values with detailed structural drawings")
        report_lines.append("   - Confirm reinforcement details (bar sizes, spacing, cover)")
        report_lines.append("   - Check for any missing data in the BIM model")

        report_lines.append("\n2. Load Capacity Notes:")
        report_lines.append("   - Estimates are based on simplified calculations")
        report_lines.append("   - Actual capacity depends on: reinforcement, span, support conditions")
        report_lines.append("   - Consult structural engineer for precise load ratings")

        report_lines.append("\n3. Standards Compliance:")
        report_lines.append("   - Verify compliance with local building codes")
        report_lines.append("   - Check minimum thickness requirements for your jurisdiction")
        report_lines.append("   - Ensure adequate safety factors are applied")

        # Missing Data Warning
        missing_data = []
        if any(not s['thickness'] for s in ground_slabs):
            missing_data.append("ground floor slab thickness")
        if any(not f['thickness'] for f in foundations):
            missing_data.append("foundation thickness")

        if missing_data:
            report_lines.append("\n⚠️  WARNING: Missing Data")
            report_lines.append("   The following critical data is missing from the IFC model:")
            for item in missing_data:
                report_lines.append(f"   - {item}")
            report_lines.append("   Please update the BIM model or verify with construction drawings.")

        # Footer
        report_lines.append("\n" + "=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)

        report_lines.append("\nDISCLAIMER:")
        report_lines.append("This is an automated analysis tool for preliminary assessment only.")
        report_lines.append("All structural calculations must be verified by a licensed structural engineer.")
        report_lines.append("Load capacity estimates are simplified and should not be used for design purposes.")

        return "\n".join(report_lines)

    @staticmethod
    def generate_html_report(
        slabs: List[Dict[str, Any]],
        foundations: List[Dict[str, Any]],
        ground_slabs: List[Dict[str, Any]],
        ifc_filename: str
    ) -> str:
        """Generate an HTML-formatted report for better visualization in Gradio."""

        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; background-color: #f8f9fa;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px;">
                <h1 style="margin: 0; font-size: 28px;">🏗️ IFC Structural Analysis Report</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Reinforcement & Load Capacity Analysis</p>
            </div>

            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="margin-top: 0; color: #333;">📁 File Information</h3>
                <p><strong>File:</strong> {ifc_filename}</p>
                <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="margin-top: 0; color: #333;">📊 Executive Summary</h3>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
                    <div style="background: #e3f2fd; padding: 15px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: #1976d2;">{len(slabs)}</div>
                        <div style="color: #555; margin-top: 5px;">Total Slabs</div>
                    </div>
                    <div style="background: #f3e5f5; padding: 15px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: #7b1fa2;">{len(ground_slabs)}</div>
                        <div style="color: #555; margin-top: 5px;">Ground Floor Slabs</div>
                    </div>
                    <div style="background: #fff3e0; padding: 15px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 32px; font-weight: bold; color: #f57c00;">{len(foundations)}</div>
                        <div style="color: #555; margin-top: 5px;">Foundations</div>
                    </div>
                </div>
            </div>
        """

        # Ground Floor Slabs
        if ground_slabs:
            html += """
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="margin-top: 0; color: #333;">🏢 Ground Floor Slab Analysis</h3>
            """

            for idx, slab in enumerate(ground_slabs, 1):
                thickness_color = "#4caf50" if slab['thickness'] and slab['thickness'] >= 150 else "#ff9800"
                capacity_color = "#4caf50" if slab['load_capacity'] and slab['load_capacity'] >= 5.0 else "#ff9800"

                html += f"""
                <div style="background: #f5f5f5; padding: 15px; border-radius: 6px; margin-bottom: 15px; border-left: 4px solid #667eea;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">Ground Floor Slab #{idx}: {slab['name']}</h4>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 10px;">
                        <div>
                            <strong>🔍 Thickness:</strong>
                            <span style="color: {thickness_color}; font-weight: bold;">
                                {slab['thickness'] if slab['thickness'] else 'N/A'} {' mm' if slab['thickness'] else ''}
                            </span>
                        </div>
                        <div>
                            <strong>⚡ Load Capacity:</strong>
                            <span style="color: {capacity_color}; font-weight: bold;">
                                {slab['load_capacity'] if slab['load_capacity'] else 'N/A'} {' kN/m²' if slab['load_capacity'] else ''}
                            </span>
                        </div>
                        <div><strong>📏 Elevation:</strong> {slab['elevation'] if slab['elevation'] is not None else 'N/A'} m</div>
                        <div><strong>📐 Area:</strong> {slab['area'] if slab['area'] else 'N/A'} m²</div>
                        <div style="grid-column: 1 / -1;"><strong>🧱 Material:</strong> {slab['material']}</div>
                    </div>
                </div>
                """

        # Foundations
        if foundations:
            html += """
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h3 style="margin-top: 0; color: #333;">🏗️ Foundation Analysis</h3>
            """

            for idx, foundation in enumerate(foundations, 1):
                thickness_color = "#4caf50" if foundation['thickness'] and foundation['thickness'] >= 300 else "#ff9800"

                html += f"""
                <div style="background: #f5f5f5; padding: 15px; border-radius: 6px; margin-bottom: 15px; border-left: 4px solid #f57c00;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">Foundation #{idx}: {foundation['name']}</h4>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 10px;">
                        <div>
                            <strong>🔍 Thickness:</strong>
                            <span style="color: {thickness_color}; font-weight: bold;">
                                {foundation['thickness'] if foundation['thickness'] else 'N/A'} {' mm' if foundation['thickness'] else ''}
                            </span>
                        </div>
                        <div><strong>🏷️ Type:</strong> {foundation['type']}</div>
                        <div><strong>📏 Elevation:</strong> {foundation['elevation'] if foundation['elevation'] is not None else 'N/A'} m</div>
                        <div><strong>📐 Area:</strong> {foundation['area'] if foundation['area'] else 'N/A'} m²</div>
                        <div style="grid-column: 1 / -1;"><strong>🧱 Material:</strong> {foundation['material']}</div>
                    </div>
                </div>
                """

        html += """
            <div style="background: #fff9c4; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #fbc02d;">
                <h4 style="margin: 0 0 10px 0; color: #333;">⚠️ Important Notes</h4>
                <ul style="margin: 0; padding-left: 20px;">
                    <li>Load capacity estimates are simplified calculations for preliminary assessment only</li>
                    <li>Actual structural capacity depends on reinforcement details, span, and support conditions</li>
                    <li>All values must be verified by a licensed structural engineer</li>
                    <li>Consult local building codes for minimum requirements</li>
                </ul>
            </div>
        </div>
        """

        return html
