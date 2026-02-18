"""
IFC Reinforcement & Structural Analysis Application
Analyzes IFC models for ground floor slab and foundation properties
"""

import sys
import os
from pathlib import Path
import gradio as gr

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ifc_analyzer import IFCAnalyzer
from report_generator import ReportGenerator


def analyze_ifc_model(ifc_file):
    """
    Main analysis function that processes the uploaded IFC file.

    Args:
        ifc_file: Uploaded IFC file from Gradio

    Returns:
        tuple: (text_report, html_report, status_message)
    """
    if ifc_file is None:
        return (
            "⚠️ Please upload an IFC file to begin analysis.",
            "<p style='color: #ff9800; padding: 20px;'>⚠️ Please upload an IFC file to begin analysis.</p>",
            "No file uploaded"
        )

    try:
        # Get file path
        ifc_path = ifc_file if isinstance(ifc_file, str) else ifc_file.name
        filename = os.path.basename(ifc_path)

        # Initialize analyzer
        analyzer = IFCAnalyzer(ifc_path)

        # Extract data
        all_slabs = analyzer.get_slabs()
        ground_slabs = analyzer.get_ground_floor_slabs()
        foundations = analyzer.get_foundations()

        # Generate reports
        text_report = ReportGenerator.generate_slab_foundation_report(
            slabs=all_slabs,
            foundations=foundations,
            ground_slabs=ground_slabs,
            ifc_filename=filename
        )

        html_report = ReportGenerator.generate_html_report(
            slabs=all_slabs,
            foundations=foundations,
            ground_slabs=ground_slabs,
            ifc_filename=filename
        )

        status = f"✓ Analysis complete: {len(all_slabs)} slabs, {len(ground_slabs)} ground floor slabs, {len(foundations)} foundations found"

        return text_report, html_report, status

    except Exception as e:
        error_msg = f"❌ Error analyzing IFC file: {str(e)}"
        error_html = f"<div style='color: #f44336; padding: 20px; background: #ffebee; border-radius: 8px;'><strong>Error:</strong> {str(e)}</div>"
        return error_msg, error_html, "Analysis failed"


# Custom CSS for better styling
CSS = """
.gradio-container {
    font-family: 'Segoe UI', Arial, sans-serif;
}

.main-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px;
    border-radius: 10px;
    margin-bottom: 20px;
    text-align: center;
}

.upload-section {
    border: 2px dashed #667eea;
    border-radius: 10px;
    padding: 20px;
    background: #f8f9fa;
}

.report-section {
    border-radius: 8px;
    background: white;
}

.status-box {
    padding: 10px;
    border-radius: 6px;
    background: #e8f5e9;
    border-left: 4px solid #4caf50;
    margin: 10px 0;
}
"""

# Build Gradio Interface
with gr.Blocks(title="IFC Reinforcement Analysis") as app:

    # Header
    gr.HTML("""
        <div class="main-header">
            <h1 style="margin: 0; font-size: 36px;">🏗️ IFC Reinforcement Analysis</h1>
            <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.95;">
                Analyze ground floor slabs and foundations for load capacity and thickness
            </p>
        </div>
    """)

    # Description
    gr.Markdown("""
    ### 📋 What This Tool Does

    This application analyzes your IFC (Industry Foundation Classes) building model to extract and report:

    - **Ground Floor Slab Properties**: Thickness, load capacity, and material composition
    - **Foundation Details**: Thickness, type, and structural properties
    - **Load Capacity Estimates**: Preliminary assessment based on slab thickness and material

    Simply upload your IFC file and click "Analyze Model" to generate a comprehensive report.
    """)

    # Main content area
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📤 Upload IFC Model")

            ifc_input = gr.File(
                label="Upload IFC File",
                file_types=[".ifc"],
                file_count="single",
                elem_classes=["upload-section"]
            )

            analyze_btn = gr.Button(
                "🔍 Analyze Model",
                variant="primary",
                size="lg",
                scale=1
            )

            status_text = gr.Textbox(
                label="Status",
                value="Ready to analyze",
                interactive=False,
                elem_classes=["status-box"]
            )

            gr.Markdown("""
            #### 💡 Tips:
            - Ensure your IFC file includes slab and foundation elements
            - Analysis works best with IFC 2x3 or IFC 4 files
            - Results include both text and visual HTML reports
            """)

        with gr.Column(scale=2):
            gr.Markdown("### 📊 Analysis Results")

            # Tabs for different report views
            with gr.Tabs():
                with gr.Tab("📄 Visual Report"):
                    html_output = gr.HTML(
                        value="<p style='color: #999; text-align: center; padding: 40px;'>Upload an IFC file and click 'Analyze Model' to see results here.</p>",
                        elem_classes=["report-section"]
                    )

                with gr.Tab("📝 Text Report"):
                    text_output = gr.Textbox(
                        label="Detailed Report",
                        lines=25,
                        value="Upload an IFC file and click 'Analyze Model' to generate a detailed text report.",
                        elem_classes=["report-section"]
                    )

    # Connect the button to the analysis function
    analyze_btn.click(
        fn=analyze_ifc_model,
        inputs=[ifc_input],
        outputs=[text_output, html_output, status_text]
    )

    # Footer
    gr.Markdown("""
    ---
    **Disclaimer:** This tool provides preliminary structural analysis for informational purposes only.
    All structural calculations must be verified by a licensed structural engineer.
    Load capacity estimates are simplified and should not be used for final design decisions.
    """)


# Launch the application
if __name__ == "__main__":
    print("=" * 80)
    print("IFC Reinforcement Analysis Application")
    print("=" * 80)
    print("\nStarting Gradio server...")
    print("Upload your IFC model to analyze ground floor slabs and foundations.")
    print("\nPress Ctrl+C to stop the server.")
    print("=" * 80)

    app.launch(
        server_name="127.0.0.1",  # localhost only
        server_port=7861,          # use 7861 instead of 7860
        share=False,               # don't create public link
        show_error=True,           # show detailed errors
        inbrowser=True             # auto-open in browser
    )
