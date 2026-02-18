# 🏗️ IFC Reinforcement Analysis - Quick Start Guide

## What This Application Does

This Gradio-based web application analyzes IFC (Industry Foundation Classes) building models and generates comprehensive reports on:

- **Ground Floor Slab Analysis**
  - Thickness measurements (in mm)
  - Estimated load capacity (in kN/m²)
  - Material composition
  - Elevation and area measurements

- **Foundation Analysis**
  - Foundation thickness
  - Foundation type and properties
  - Material details
  - Structural assessment

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## 🚀 Installation & Setup

### Step 1: Install Dependencies

Open your terminal in the reinforcement_check directory and run:

```bash
cd d:\Github\structure_compliance_check\reinforcement_check
pip install -r requirements.txt
```

Or if you're using pip3:

```bash
pip3 install -r requirements.txt
```

**Required packages:**
- ifcopenshell (IFC file parsing)
- gradio (Web interface)
- numpy (Numerical computations)
- And other supporting libraries

### Step 2: Launch the Application

Simply run:

```bash
python app.py
```

Or with python3:

```bash
python3 app.py
```

### Step 3: Open in Browser

The application will automatically start a local web server. You should see output like:

```
================================================================================
🏗️  IFC Reinforcement Analysis Application
================================================================================

Starting Gradio server...
Upload your IFC model to analyze ground floor slabs and foundations.

Press Ctrl+C to stop the server.
================================================================================

Running on local URL:  http://127.0.0.1:7860
```

Open your web browser and navigate to: **http://127.0.0.1:7860**

## 📤 How to Use

1. **Upload IFC File**: Click the upload area and select your `.ifc` file
2. **Analyze**: Click the "🔍 Analyze Model" button
3. **View Results**: Switch between tabs to see:
   - **Visual Report** (📄): Formatted HTML report with color-coded results
   - **Text Report** (📝): Detailed text report you can copy/export

## 📊 Understanding the Report

### Ground Floor Slab Metrics

- **Thickness**:
  - ⚠️ < 100mm: Below typical minimum
  - ℹ️ 100-150mm: Light residential use
  - ✓ 150-200mm: Standard residential/commercial
  - ✓ > 200mm: Heavy-duty capacity

- **Load Capacity** (includes self-weight + live load):
  - ⚠️ < 5.0 kN/m²: Low capacity
  - ℹ️ 5.0-8.0 kN/m²: Residential use
  - ✓ > 8.0 kN/m²: Commercial/industrial use

### Foundation Metrics

- **Thickness**:
  - ⚠️ < 200mm: Unusually thin
  - ℹ️ 200-300mm: Minimum acceptable for light structures
  - ✓ 300-500mm: Standard foundation
  - ✓ > 500mm: Heavy-duty foundation

## 🔧 Troubleshooting

### Common Issues

1. **"Module not found" error**
   ```bash
   pip install ifcopenshell gradio numpy
   ```

2. **"Python not found"**
   - Make sure Python is installed and in your PATH
   - Try using `python3` instead of `python`

3. **Port already in use**
   - Edit `app.py` line with `server_port=7860` to a different port (e.g., 7861)

4. **IFC file fails to parse**
   - Ensure the file is a valid IFC format (IFC 2x3 or IFC 4)
   - Check that the file isn't corrupted
   - Verify the file contains slab and foundation elements

## 📁 Project Structure

```
structure_compliance_check/
├── reinforcement_check/           # Reinforcement analysis app
│   ├── app.py                     # Main application (RUN THIS!)
│   ├── src/
│   │   ├── ifc_analyzer.py       # IFC model parser
│   │   └── report_generator.py  # Report generation
│   ├── requirements.txt          # Dependencies
│   ├── run_app.bat              # Windows launcher
│   ├── run_app.sh               # Linux/Mac launcher
│   └── QUICKSTART.md            # This file
├── basic_app/                    # Other compliance apps
├── beam_check/
├── column_check/
├── slab_check/
└── walls_check/
```

## ⚠️ Important Notes

- **Disclaimer**: This tool provides preliminary analysis only
- All structural calculations must be verified by a licensed structural engineer
- Load capacity estimates are simplified and for informational purposes only
- Do not use for final design decisions without professional verification

## 🆘 Getting Help

If you encounter issues:

1. Check that all dependencies are installed: `pip list | grep -E "(ifcopenshell|gradio)"`
2. Verify your IFC file is valid and contains the required elements
3. Check the terminal output for detailed error messages
4. Ensure you're running from the correct directory

## 🎯 Next Steps

- Try uploading different IFC models to compare results
- Export the text report for documentation
- Review the analysis with a structural engineer
- Modify the code to add custom checks or reporting features

Happy analyzing! 🏗️
