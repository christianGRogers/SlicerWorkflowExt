# DAI Workflow Extension for 3D Slicer

<div align="center">
  <img src="DAI_Workflow/DAI_Workflow.png" alt="DAI Workflow Logo" width="200"/>
</div>

## Documentation

 **[Complete User Manual](DAI_Workflow_User_Manual.md)** - Step-by-step instructions for all workflow features  
 **[Technical Documentation](DAI_Workflow_Module_Documentation.md)** - Complete feature reference and developer guide

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

The DAI Workflow provides a complete 4-phase pipeline for vessel analysis:

1. **Volume Preparation** - DICOM loading and ROI-based cropping
2. **Vessel Segmentation** - Automated thresholding with manual refinement
3. **Centerline Processing** - Advanced extraction algorithms with progress monitoring  
4. **Analysis & Visualization** - CPR generation, measurements, and linear reformats

*For detailed step-by-step instructions, see the [User Manual](DAI_Workflow_User_Manual.md).*

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

- **Automated UI Customization** - Interface optimization for medical workflows
- **Smart View Management** - Context-aware layout switching (three-up, 3D-only)
- **Medical Image Processing** - Advanced vessel analysis algorithms
- **Comprehensive Testing** - 100+ validation functions for clinical accuracy

*For complete feature documentation, see the [Technical Documentation](DAI_Workflow_Module_Documentation.md).*

## Testing Framework

Comprehensive validation suite with 100+ test functions covering:
- **Centerline Workflow Tests** - Extraction validation and monitoring
- **Medical UI Tests** - Interface component verification  
- **Debug & Verification** - Algorithm accuracy and performance testing

*For detailed testing procedures, see the [Technical Documentation](DAI_Workflow_Module_Documentation.md).*

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

## Troubleshooting

Common issues and solutions for clinical workflows are covered in detail in the [User Manual](DAI_Workflow_User_Manual.md), including:
- DICOM loading and contrast detection
- Centerline extraction for complex vessels
- CPR visualization optimization
- Performance tuning for large datasets

## Clinical Applications & System Requirements

**Supported Procedures:** Coronary, peripheral, carotid, and renal artery analysis  
**Image Compatibility:** CT/MR angiography, multi-vendor DICOM support  
**System Requirements:** Windows 10+, 16GB+ RAM, SSD storage recommended

*Complete specifications available in the [User Manual](DAI_Workflow_User_Manual.md).*

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

## Support & Documentation

- **[User Manual](DAI_Workflow_User_Manual.md)** - Complete workflow instructions and troubleshooting
- **[Technical Documentation](DAI_Workflow_Module_Documentation.md)** - Developer reference and feature catalog
- **Clinical Support** - Contact development team for medical workflow questions
- **Training Materials** - Available for medical professionals and institutions

---

**Last Updated**: September 2025  
**Version**: 1.0.0  
**Clinical Compatibility**: 3D Slicer 5.6.1 - 5.8.1+  

For technical documentation, visit the [3D Slicer Extensions Documentation](https://www.slicer.org/wiki/Documentation/Nightly/Extensions)
