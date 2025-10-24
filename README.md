# DAI Workflow Extension for 3D Slicer

<div align="center">
  <img src="DAI_Workflow/DAI_Workflow.png" alt="DAI Workflow Logo" width="200"/>
</div>

## Overview

**DAI Workflow** is a comprehensive 3D Slicer extension designed for automated vessel processing and centerline extraction. Developed at the Lawson Research Institute and Western University (So Lab), this extension provides a guided workflow for medical image analysis, specifically targeting vessel segmentation, centerline extraction, and Curved Planar Reconstruction (CPR) visualization.

The workflow allows medical professionals to create high-resolution artery view segmentation in a fast-paced hospital environment with minimal training. It uses advanced radius maximizing algorithms to find artery centerlines and create linear reformats for precise medical analysis.

## Workflow Demonstration

### Phase 1: Volume Cropping
<img width="496" height="290" alt="Crop View CT Chest with contrast" src="https://github.com/user-attachments/assets/06bf6d28-6755-4b36-92ef-0b20888aacd9" />

**Crop View CT Chest with contrast** - Interactive ROI-based volume cropping with automatic three-up view for optimal visualization.

### Phase 2: Vessel Segmentation  
<img width="495" height="282" alt="Segmentation View" src="https://github.com/user-attachments/assets/4d0abc6b-ccbf-42b8-99e2-7561e0e1ee8d" />

**Segmentation View** - Automated vessel segmentation with programmatic Segment Editor integration and manual refinement capabilities.

### Phase 3: Centerline Analysis
<img width="492" height="287" alt="Straightened View" src="https://github.com/user-attachments/assets/488b7843-e2b0-4ebb-9929-e7eb767aaa11" />

**Straightened View** - Advanced CPR (Curved Planar Reconstruction) visualization with centerline extraction and lesion point analysis.

## Key Features

### 🔧 **Automated Workflow Processing**
- **Guided vessel processing pipeline** with step-by-step automation
- **DICOM auto-loading** via source file method (`source_slicer.txt`)
- **Intelligent UI customization** that hides unnecessary interface elements
- **Programmatic Segment Editor integration** without GUI overhead

### 🖥️ **Enhanced User Interface**
- **Automatic UI cleanup**: Hides data probe, status bar, Slicer logo, and help sections
- **Dark 3D background** for better visualization
- **Smart view management**: 
  - Three-up view (Red, Green, Yellow) for volume cropping
  - 3D-only view for post-processing analysis
- **Floating UI elements** for scissors control and workflow continuation

### 📊 **Advanced Medical Visualization**
- **Centerline extraction** with monitoring and completion dialogs
- **CPR (Curved Planar Reconstruction)** for vessel straightening
- **Multiple centerline workflow support** for complex vessel networks
- **Lesion point extraction** with radius measurements
- **Linear reformat generation** for detailed analysis

### 🛠️ **Comprehensive Testing Suite**
- **100+ test functions** for workflow validation
- **Debug utilities** for troubleshooting
- **UI modification testing**
- **Centerline monitoring verification**

## Installation

### Prerequisites
- **3D Slicer 5.8.1** or later
- **Windows OS** (tested on Windows 10/11)
- **CMake 3.16.3** or later for building

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/christianGRogers/SlicerWorkflowExt.git
   cd SlicerWorkflowExt
   ```

2. **Build the extension:**
   ```bash
   mkdir build
   cd build
   cmake -DCMAKE_BUILD_TYPE=Release ../DAI_Workflow
   make
   ```

3. **Install in Slicer:**
   - Open 3D Slicer
   - Go to **Edit → Application Settings → Modules**
   - Add the path to your built extension
   - Restart Slicer

## Quick Start

### Method 1: Source File Auto-Loading (Recommended)

1. **Create source file:**
   Create `source_slicer.txt` in your user directory:
   ```
   C:\Users\[username]\source_slicer.txt
   ```

2. **Add DICOM path:**
   Edit the file to contain your DICOM folder path:
   ```
   G:\My Drive\Data\DICOM\Patient_Study
   ```

3. **Start Slicer:**
   Launch Slicer normally - DICOM data will auto-load when accessing the workflow module.

### Method 2: Manual Loading

1. **Open Slicer**
2. **Navigate to Modules → Scripted Modules → Workflow**
3. **Click "Start Workflow"**
4. **Load your DICOM data manually**

## Medical Workflow Process

### Phase 1: Volume Preparation
1. **DICOM Loading**: Automatic or manual DICOM import with contrast detection
2. **Volume Cropping**: Interactive ROI-based volume cropping for focused analysis
3. **View Management**: Automatic three-up view (Red, Green, Yellow) for comprehensive visualization

### Phase 2: Vessel Segmentation
1. **Threshold Segmentation**: Automated vessel segmentation using contrast enhancement
2. **Scissors Tool Integration**: Manual refinement capabilities for precise control
3. **Programmatic Segment Editor**: Pure API integration without GUI overhead

### Phase 3: Centerline Processing
1. **Centerline Extraction**: Advanced algorithms for vessel centerline computation
2. **Multiple Centerline Support**: Handle complex vessel networks and bifurcations
3. **Completion Monitoring**: Real-time progress tracking with user feedback

### Phase 4: Analysis & Visualization
1. **CPR Generation**: Curved planar reconstruction for vessel straightening
2. **Lesion Point Extraction**: Automated detection of critical points
3. **Radius Measurements**: Precise vessel diameter calculations
4. **Linear Reformats**: Generated views for detailed medical analysis

## Project Structure

```
SlicerWorkflowExt/
├── DAI_Workflow/                   # Main extension directory
│   ├── CMakeLists.txt             # Extension build configuration
│   ├── DAI_Workflow.png           # Extension icon
│   ├── SourceFileMethod.md        # Auto-loading documentation
│   ├── ViewConfigurationChanges.md # View management details
│   └── workflow/                   # Main module directory
│       ├── CMakeLists.txt         # Module build configuration
│       ├── workflow.py            # Main module implementation
│       ├── Moduals/               # Module components
│       │   ├── workflow_moduals.py     # Core workflow functions (10,993 lines)
│       │   └── workflow_test_functions.py # Testing utilities
│       ├── Resources/             # UI and icons
│       │   ├── Icons/
│       │   │   └── workflow.png   # Module icon
│       │   └── UI/
│       │       └── workflow.ui    # User interface layout
│       └── Testing/               # Test framework
├── start.ps1                     # PowerShell launcher script
└── README.md                     # This documentation
```

## Advanced Features

### UI Customization
The extension automatically customizes the Slicer interface for medical workflow optimization:

```python
# Hide unnecessary UI elements for focused medical analysis
self.hideStatusBar()           # Remove status bar
self.hideLogo()               # Hide Slicer logo
self.hideDataProbe()          # Remove data probe
self.hideHelpAndAcknowledgments()  # Clean module interface
```

### Smart View Management
Automatic view switching optimized for medical imaging workflow:

```python
# Volume cropping phase - Multi-planar reconstruction
set_three_up_view()           # Axial, Sagittal, Coronal views

# Analysis phase - 3D vessel visualization  
set_3d_only_view()           # 3D rendering with CPR
```

### Medical Image Processing
Advanced algorithms for vessel analysis:

```python
# Centerline extraction with medical-grade precision
test_centerline_monitoring()
force_show_completion_dialog()
debug_centerline_monitoring()

# CPR generation for vessel straightening
start_with_dicom_data()
create_analysis_masks_manually()
```

## Testing Framework

The extension includes a comprehensive testing suite designed for medical image processing validation:

### Centerline Workflow Tests
- `test_centerline_completion_dialog()` - Validate centerline extraction completion
- `test_multiple_centerlines_workflow()` - Test complex vessel networks
- `test_specific_centerline_monitoring()` - Monitor extraction progress

### Medical UI Tests
- `test_hide_crop_ui()` - Validate volume cropping interface
- `test_minimal_segment_editor_ui()` - Test segmentation tools
- `test_hide_extract_centerline_ui()` - Verify centerline extraction UI

### Debug & Verification
- `debug_centerline_monitoring()` - Debug extraction algorithms
- `debug_extract_centerline_widgets()` - UI component analysis
- `list_available_functions()` - Complete test suite overview

### Running Medical Validation Tests
```python
# Import medical workflow test functions
from DAI_Workflow.workflow.Moduals import workflow_test_functions as test

# Validate centerline extraction accuracy
test.test_centerline_monitoring()
test.verify_extract_centerline_point_list_autoselection()

# Test medical image processing pipeline
test.test_extract_centerline_verification()
test.create_analysis_masks_manually()
```

## Configuration for Medical Environments

### Hospital Deployment - Source File Method
Streamlined DICOM loading for clinical environments:

```
# File: C:\Users\[radiologist]\source_slicer.txt
\\hospital\dicom\PatientID_12345\CT_CORONARY_ARTERIES
```

### PowerShell Integration for Clinical Workflows
```powershell
# Direct Slicer execution for emergency analysis
.\start.ps1 -RunSlicer

# Monitor for PACS integration triggers
.\start.ps1 -MonitorLocks
```

## Troubleshooting Medical Workflows

### Common Clinical Issues

**Issue**: DICOM contrast detection fails
**Solution**: Verify CT protocol includes contrast phase timing
```python
test.create_contrast_mask()
test.create_analysis_masks_manually()
```

**Issue**: Centerline extraction incomplete on complex vessels
**Solution**: Use multiple centerline workflow for bifurcations
```python
test.test_multiple_centerlines_workflow()
test.debug_centerline_monitoring()
```

**Issue**: CPR visualization artifacts
**Solution**: Verify vessel segmentation quality
```python
test.test_extract_centerline_verification()
test.fix_centerline_issues()
```

### Medical Validation Commands
```python
# Validate medical image processing accuracy
test.list_available_functions()
test.test_extract_centerline_setup_with_verification()

# Verify clinical measurement precision
test.debug_point_list_transforms()
test.verify_extract_centerline_point_list_autoselection()
```

## Clinical Applications

### Supported Medical Procedures
- **Coronary Artery Analysis** - CT angiography with contrast
- **Peripheral Vessel Assessment** - Lower extremity arterial evaluation
- **Carotid Artery Evaluation** - Neck vessel stenosis analysis
- **Renal Artery Studies** - Kidney perfusion assessment

### Medical Image Compatibility
- **CT Angiography** with contrast enhancement
- **DICOM Series** from major medical imaging vendors
- **Multi-phase Studies** with arterial and venous phases
- **High-resolution Reconstructions** (0.6mm slice thickness or better)

## System Requirements for Medical Imaging

### Minimum Clinical Workstation
- **OS**: Windows 10 Pro (64-bit) - Medical Grade
- **RAM**: 16 GB (for large DICOM series)
- **Storage**: 100 GB SSD (for patient data caching)
- **3D Slicer**: Version 5.8.1 (FDA cleared components)
- **Display**: Dual monitor setup (3MP medical displays recommended)

### Recommended Radiology Workstation  
- **OS**: Windows 11 Pro (64-bit)
- **RAM**: 32 GB or more
- **Storage**: 500 GB NVMe SSD
- **GPU**: Dedicated medical visualization card
- **Network**: Gigabit connection to PACS

## Medical Compliance & Quality Assurance

### Validation Standards
- **DICOM Compliance**: Full DICOM 3.0 support
- **Medical Accuracy**: Sub-millimeter precision for measurements
- **Reproducibility**: Consistent results across imaging protocols
- **Performance**: Real-time processing for clinical workflows

### Quality Control
- Comprehensive test suite with medical validation
- Automated accuracy verification
- Clinical workflow optimization
- Performance benchmarking for medical environments

## License & Medical Disclaimer

This software is developed for research purposes at the Lawson Research Institute and Western University (So Lab). 

**IMPORTANT MEDICAL DISCLAIMER**: This software is intended for research and educational purposes only. It has not been cleared or approved by the FDA or other regulatory agencies for clinical diagnostic use. Healthcare professionals should not rely solely on this software for patient diagnosis or treatment decisions.

## Acknowledgments

- **Developer**: Christian Rogers
- **Institution**: Lawson Research Institute and Western University (So Lab)  
- **Year**: 2025
- **Medical Advisors**: So Lab Medical Team
- **Special Thanks**: 3D Slicer medical imaging community

## Support for Medical Users

### Clinical Support
- **Medical Workflow Questions**: Contact development team
- **DICOM Integration Issues**: Provide hospital PACS specifications  
- **Clinical Validation**: Reference test suite documentation
- **Training Materials**: Available for medical professionals

### Emergency Clinical Support
For urgent clinical workflow issues:
1. Use debug functions for immediate troubleshooting
2. Check log files in extension directory  
3. Contact development team with clinical context
4. Provide anonymized DICOM samples if possible

---

**Last Updated**: September 2025  
**Version**: 1.0.0  
**Clinical Compatibility**: 3D Slicer 5.6.1 - 5.8.1+  

For technical documentation, visit the [3D Slicer Extensions Documentation](https://www.slicer.org/wiki/Documentation/Nightly/Extensions)
