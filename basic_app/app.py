"""
IFC Wall Compliance Checker

This Gradio app analyzes IFC wall elements (IfcWall, IfcWallType, IfcWallStandardCase)
and generates comprehensive compliance reports with dimensions and requirements.
"""

import gradio as gr
import sys
from pathlib import Path

# Add walls_check to path
sys.path.insert(0, str(Path(__file__).parent.parent / "walls_check"))

from Walls import check_wall_compliance


def analyze_ifc_walls(ifc_file):
    """
    Process uploaded IFC file and generate wall compliance report.
    
    Args:
        ifc_file: Uploaded IFC file from Gradio
        
    Returns:
        str: Formatted wall compliance report
    """
    if ifc_file is None:
        return "⚠️ Please upload an IFC file first."
    
    # Get file path
    ifc_path = ifc_file if isinstance(ifc_file, str) else ifc_file.name
    
    try:
        # Run wall compliance check
        report_lines = check_wall_compliance(ifc_path)
        
        # Join report lines into single string
        report = "\n".join(report_lines)
        
        return report
    
    except Exception as e:
        return f"❌ Error analyzing IFC file:\n{str(e)}\n\nPlease ensure the file is a valid IFC model."


# Create Gradio interface
with gr.Blocks(
    title="IFC Wall Compliance Checker",
    theme=gr.themes.Soft(primary_hue="blue")
) as app:
    
    gr.Markdown(
        """
        # 🏗️ IFC Wall Compliance Checker
        
        Upload an IFC building model to analyze wall elements and generate a detailed compliance report.
        
        **This tool checks:**
        - IfcWall elements
        - IfcWallStandardCase elements  
        - IfcWallType definitions
        - Dimensions (length, height, width/thickness)
        - Material specifications
        - Load bearing properties
        - Fire ratings and other compliance properties
        """
    )
    
    with gr.Row():
        with gr.Column(scale=1):
            ifc_input = gr.File(
                label="📁 Upload IFC File",
                file_types=[".ifc"],
                type="filepath"
            )
            
            analyze_btn = gr.Button(
                "🔍 Analyze Walls",
                variant="primary",
                size="lg"
            )
            
            gr.Markdown(
                """
                ### Instructions:
                1. Click the upload area above
                2. Select your IFC model file (.ifc)
                3. Click "Analyze Walls" button
                4. Review the compliance report
                """
            )
        
        with gr.Column(scale=2):
            output = gr.Textbox(
                label="📊 Wall Compliance Report",
                lines=25,
                max_lines=50,
                placeholder="Upload an IFC file and click 'Analyze Walls' to see the report...",
                show_copy_button=True
            )
    
    # Button click event
    analyze_btn.click(
        fn=analyze_ifc_walls,
        inputs=[ifc_input],
        outputs=[output]
    )
    
    # Auto-analyze on file upload
    ifc_input.change(
        fn=analyze_ifc_walls,
        inputs=[ifc_input],
        outputs=[output]
    )
    
    gr.Markdown(
        """
        ---
        **Note:** This tool analyzes IFC models to extract wall element information including dimensions,
        materials, and compliance properties. Ensure your IFC file contains proper wall definitions for
        comprehensive analysis.
        """
    )


if __name__ == "__main__":
    app.launch()
