# DAI Workflow Extension - Complete User Manual

## Table of Contents
1. [Overview](#overview)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Workflow Option 1: Standard DICOM Workflow](#workflow-option-1-standard-dicom-workflow)
5. [Workflow Option 2: Markup Import Workflow](#workflow-option-2-markup-import-workflow)
6. [Workflow Option 3: Segmentation Import Workflow](#workflow-option-3-segmentation-import-workflow)
7. [Advanced Features](#advanced-features)
8. [Measurement and Analysis Tools](#measurement-and-analysis-tools)
9. [Troubleshooting](#troubleshooting)
10. [Tips and Best Practices](#tips-and-best-practices)

---

## Overview

The DAI (Digital Angiography Intelligence) Workflow Extension is a comprehensive 3D Slicer module designed for vessel centerline extraction and analysis. It provides a guided workflow for medical image processing, specifically optimized for vascular analysis with Curved Planar Reformat (CPR) visualization.

### Key Features
- **Guided Workflow** - Step-by-step process from DICOM import to final analysis
- **Multiple Entry Points** - Standard workflow, markup import, or segmentation import
- **Advanced Vessel Analysis** - Centerline extraction, CPR processing, cross-sectional analysis
- **Measurement Tools** - Stenosis measurements, circle drawing, point placement
- **Custom UI** - Streamlined interface with programmatic tool integration

### Target Users
- Radiologists and medical imaging specialists
- Researchers working with vascular imaging
- Clinical staff performing vessel analysis
- Students learning medical image processing

---

## Installation

### Prerequisites
- 3D Slicer (version 5.0 or later recommended)
- Sufficient system memory (8GB+ recommended for large datasets)
- Compatible operating system (Windows, macOS, or Linux)

### Installing the Extension
1. **Download** the SlicerWorkflowExt extension files
2. **Copy** the `DAI_Workflow` folder to your Slicer extensions directory
3. **Restart** 3D Slicer
4. **Navigate** to the Modules menu and select "DAI Workflow" under the appropriate category

### Verification
- Check that the DAI Workflow module appears in the module selector
- Verify that required dependencies (Segment Editor, Extract Centerline, CPR) are available
- Test basic functionality with sample data

---

## Getting Started

### Initial Setup
1. **Launch 3D Slicer** and navigate to the DAI Workflow module
2. **Prepare Your Data** - Ensure DICOM files or volumes are accessible
3. **Choose Workflow Path** - Decide between standard workflow, markup import, or segmentation import

### Understanding the Interface
- **Left Panel** - Automatically collapsed to maximize viewing space
- **Main View** - Configures automatically based on workflow step
- **Custom Controls** - Floating buttons and tools appear as needed
- **Status Updates** - Progress messages guide you through each step

---

## Workflow Option 1: Standard DICOM Workflow

This is the most common workflow path, starting from raw DICOM data and proceeding through the complete analysis pipeline.

### Step 1: DICOM Data Import

#### Option A: Using the DICOM Module
1. **Click** "Start with DICOM Data" in the workflow module
2. **Import DICOM** files using the standard Slicer DICOM browser
3. **Load** the desired series into the scene
4. **Wait** for the workflow to detect the loaded volume

#### Option B: Direct Path Loading
1. **Ensure** your DICOM path is specified in `source_slicer.txt`
2. **Use** the automatic DICOM loading function
3. **Monitor** the loading progress in the console

**Supported DICOM Types:**
- CT Angiography (CTA)
- MR Angiography (MRA) 
- Digital Subtraction Angiography (DSA)
- Multi-vendor support (Philips, Siemens, GE)

### Step 2: Volume Cropping

The workflow automatically switches to a custom crop interface to focus on the region of interest.

#### Using the Custom Crop Interface
1. **View Layout** - The interface shows three orthogonal views (Axial, Sagittal, Coronal)
2. **ROI Manipulation** - A crop ROI (Region of Interest) box appears around your volume
3. **Adjust the ROI:**
   - **Click and drag** the colored handles to resize
   - **Click and drag** the center to move the entire ROI
   - **Use mouse wheel** to zoom in/out for precision
4. **Position the ROI** to encompass your vessel of interest with some margin
5. **Click "Apply Crop"** when satisfied with the ROI placement

#### Crop Best Practices
- Leave **sufficient margin** around your vessel to avoid cutting off important anatomy
- Focus on the **main vessel segment** you want to analyze
- Consider **downstream analysis** - ensure start and end points will be visible

### Step 3: Segmentation Creation

After cropping, you'll create a segmentation to isolate vessel structures.

#### Threshold Segmentation
1. **Dialog Prompt** - Enter threshold values for vessel segmentation
   - **Lower Threshold** - Minimum HU/intensity value (e.g., 200 for contrast-enhanced vessels)
   - **Upper Threshold** - Maximum HU/intensity value (e.g., 3000 for bone exclusion)
2. **Preview** the segmentation in 3D view
3. **Refine if needed** using the scissors tool

#### Using the Scissors Tool
1. **Scissors Button** - A floating scissors tool button appears
2. **Toggle On** - Click to activate scissors mode
3. **Edit Segmentation:**
   - **Left-click and drag** to erase unwanted regions
   - **Shift + left-click and drag** to add regions back
   - **Use different slice views** for comprehensive editing
4. **Toggle Off** - Click scissors button again to finish editing
5. **Continue Workflow** - Click the continue button when satisfied

### Step 4: Centerline Extraction

The Extract Centerline module opens automatically with your segmentation loaded.

#### Setting Up Centerline Extraction
1. **Module Configuration** - The module is pre-configured with your segmentation
2. **Point Placement Tool** - Automatically selected for placing control points
3. **Surface Preview** - Your segmentation appears as a 3D surface

#### Placing Control Points
1. **Start Point** - Click on the vessel inlet (proximal end)
2. **End Point** - Click on the vessel outlet (distal end)
3. **Additional Points** (optional) - Place intermediate points for complex geometries
4. **Point Placement Tips:**
   - Place points **inside the vessel lumen**
   - Use **different slice views** for accuracy
   - **Zoom in** for precise placement

#### Extracting the Centerline
1. **Large Apply Button** - A prominent green "Apply" button appears
2. **Click Apply** - Starts the centerline extraction process
3. **Wait** - Processing may take several seconds to minutes depending on complexity
4. **Completion Dialog** - Choose your next action when extraction completes

### Step 5: Centerline Review and Editing

A completion dialog offers several options for proceeding.

#### Completion Dialog Options
1. **Continue to CPR** - Proceed with the extracted centerline
2. **Verify/Edit Centerline** - Review and modify the centerline if needed
3. **Add More Centerlines** - Extract additional centerlines for branches
4. **Retry Extraction** - Start over with different control points

#### Centerline Editing (if selected)
1. **Editing Mode** - The centerline becomes editable
2. **Point Manipulation:**
   - **Click and drag** points to reposition
   - **Add points** by clicking on the curve
   - **Delete points** by right-clicking
3. **Real-time Preview** - Changes update immediately
4. **Editing Controls:**
   - **Extract New** - Create new centerline from edited version
   - **Reset to Original** - Revert all changes
   - **Continue to CPR** - Proceed with current version

### Step 6: Curved Planar Reformat (CPR)

The CPR module straightens your vessel for analysis.

#### CPR Processing
1. **Automatic Setup** - Module configures with your centerline
2. **Layout Change** - Switches to Red and Green slice views
3. **Large Apply Button** - Green CPR apply button appears
4. **Click Apply** - Processes the curved planar reformat
5. **Straightened Views** - Vessel appears straightened in slice views

#### CPR Results
- **Red View** - Axial cross-sections through the straightened vessel
- **Green View** - Longitudinal view of the straightened vessel
- **Transform Applied** - Centerline and related objects are transformed

### Step 7: Point Placement and Analysis

After CPR, advanced analysis tools become available.

#### Point Placement Interface
A floating control panel appears with several options:

1. **Place Pre/Post Points** - Mark analysis locations on the vessel
2. **Place Branch Points** - Mark branch vessel locations
3. **Place Post-Branch Points** - Mark points after branch vessels
4. **Circle Drawing** - Create measurement circles at marked points

#### Placing Analysis Points
1. **Toggle Point Placement** - Click button to start placing points
2. **Click on Vessel** - Place points at locations of interest
3. **Point Counter** - Shows number of points placed
4. **Multiple Point Types:**
   - **Pre/Post Points** - For stenosis analysis
   - **Branch Points** - For branch vessel analysis
   - **Post-Branch Points** - For post-bifurcation analysis

#### Circle Drawing
1. **Select Point** - Choose from placed points using dropdown
2. **Draw Circle** - Click button to create measurement circle
3. **Adjust Radius** - Use slider to modify circle size
4. **Circle Properties:**
   - Perpendicular to centerline
   - Color-coded by type
   - Visible in 3D and slice views

---

## Workflow Option 2: Markup Import Workflow

This workflow allows you to import pre-existing markup files and analysis data.

### When to Use Markup Import
- You have previously saved markup files from earlier analysis
- Working with pre-defined analysis points
- Continuing analysis from a checkpoint
- Collaborative workflow with shared markup data

### Step 1: Starting Markup Import
1. **Choose Import Option** - Select "Yes" when prompted for markup import
2. **File Selection** - Browse to folder containing markup files
3. **Expected Files:**
   - `Circle_start-slice-X.mrk.json` - Start slice markup files
   - `Circle_end-slice-X.mrk.json` - End slice markup files
   - Transform files (`.h5` or `.tfm`)
   - Straightened volume files (`.nrrd` or similar)

### Step 2: Automatic Processing
1. **File Processing** - System automatically processes markup files
2. **Tube Creation** - Tubes are created from markup pairs
3. **Transform Loading** - Associated transforms are applied
4. **Volume Import** - Straightened volumes are loaded if available

### Step 3: Continue Analysis
1. **Review Results** - Check created tubes and transforms in 3D view
2. **Additional Analysis** - Use standard analysis tools as needed
3. **Modify if Needed** - Edit or add new markup as required

---

## Workflow Option 3: Segmentation Import Workflow

This workflow starts with a pre-existing segmentation file.

### When to Use Segmentation Import
- You have a previously created segmentation
- Working with externally created segmentations
- Skipping the threshold creation step
- Using AI/automated segmentation results

### Step 1: Import Segmentation
1. **Choose Import Option** - Select "Yes" when prompted for segmentation import
2. **File Selection** - Browse and select segmentation file (`.seg.nrrd` or similar)
3. **Volume Association** - Ensure corresponding volume is loaded

### Step 2: Skip to Centerline Extraction
1. **Automatic Navigation** - Jumps directly to Extract Centerline module
2. **Pre-configured Setup** - Module loads with imported segmentation
3. **Standard Process** - Continue with centerline extraction as in standard workflow

### Step 3: Continue Standard Analysis
- Follow steps 4-7 from the standard workflow
- All analysis tools work the same way

---

## Advanced Features

### Multiple Centerline Extraction

#### When to Extract Multiple Centerlines
- Complex vessel geometries with multiple branches
- Separate analysis of different vessel segments
- Comparative analysis between vessel regions

#### Process
1. **After First Centerline** - Choose "Add More Centerlines" from completion dialog
2. **New Setup** - Extract Centerline module resets for new extraction
3. **Place New Points** - Set control points for additional vessel
4. **Repeat Process** - Extract as many centerlines as needed
5. **Management** - System tracks and manages multiple centerlines

### Centerline Editing Features

#### Detailed Editing Options
1. **Point Manipulation** - Precise control over centerline geometry
2. **Curve Smoothing** - Automatic smoothing of edited curves
3. **Validation** - Real-time feedback on centerline quality
4. **Backup System** - Original centerline preserved for restoration

#### Editing Best Practices
- Make **small adjustments** rather than major changes
- **Zoom in** for precise point placement
- **Use multiple views** to verify changes in 3D
- **Test extraction** if major changes are needed

### Cross-Sectional Analysis

#### Automatic Configuration
After CPR processing, cross-sectional analysis is automatically set up:

1. **Module Launch** - Cross-Section Analysis module opens
2. **Centerline Selection** - Automatically configured with current centerline
3. **Apply Processing** - Automatic application of analysis
4. **View Configuration:**
   - **Red View** - Axial cross-sections
   - **Green View** - Longitudinal sections
   - **Point Index** - Set to middle of centerline

#### Navigation Controls
- **Point Index Slider** - Navigate along centerline
- **Cross-section Views** - Real-time updates as you navigate
- **Measurement Tools** - Available in cross-sectional views

---

## Measurement and Analysis Tools

### Stenosis Measurement Tool

#### Purpose
Measure vessel narrowing (stenosis) using dual-line measurements.

#### Process
1. **Activate Tool** - Click "Stenosis Measurement" button
2. **First Line** - Draw line across normal vessel segment
3. **Second Line** - Draw line across stenosed segment
4. **Automatic Calculation** - Stenosis ratio computed automatically
5. **Results Display** - Percentage stenosis shown

#### Measurement Tips
- Draw lines **perpendicular to vessel axis**
- Measure **lumen diameter**, not wall thickness
- Use **consistent measurement locations**
- Take **multiple measurements** for accuracy

### Window/Level Tool

#### Purpose
Adjust image contrast and brightness for better visualization.

#### Usage
1. **Toggle Tool** - Click "Window/Level" button to activate
2. **Mouse Controls:**
   - **Left-click and drag horizontally** - Adjust window (contrast)
   - **Left-click and drag vertically** - Adjust level (brightness)
3. **Visual Feedback** - Image updates in real-time
4. **Toggle Off** - Click button again to deactivate

### Analysis Mask Visibility

#### Purpose
Control visibility of analysis-related objects.

#### Controls
1. **Toggle Button** - Show/hide analysis masks
2. **Selective Visibility** - Control different object types
3. **Clean View** - Hide unnecessary objects for presentations

### Circle Measurement Tools

#### Advanced Circle Features
1. **Radius Adjustment** - Precise control using slider
2. **Multiple Circles** - Create circles at different locations
3. **Color Coding** - Different colors for different analysis types
4. **3D Visualization** - Circles visible in both 2D and 3D views

#### Circle Types
- **Pre-lesion Circles** - Normal vessel measurements
- **Post-lesion Circles** - Post-treatment measurements
- **Branch Circles** - Branch vessel measurements
- **Reference Circles** - Comparison measurements

---

## Troubleshooting

### Common Issues and Solutions

#### DICOM Loading Problems
**Problem:** DICOM files won't load or only single slice loads
**Solutions:**
1. **Check File Format** - Ensure files are valid DICOM format
2. **Try Different Path** - Use shorter file paths without special characters
3. **Use Manual Loading** - Try the simple_dicom_load function
4. **Check File Permissions** - Ensure read access to DICOM directory
5. **Philips DICOM** - Use specialized Philips loading function if applicable

#### Segmentation Issues
**Problem:** Threshold segmentation includes too much/too little
**Solutions:**
1. **Adjust Threshold Values** - Try different HU ranges
2. **Use Scissors Tool** - Manually refine segmentation
3. **Multiple Thresholds** - Create separate segments for different structures
4. **Pre-processing** - Apply image filters before segmentation

#### Centerline Extraction Fails
**Problem:** No centerline generated or poor quality centerline
**Solutions:**
1. **Check Control Points** - Ensure points are inside vessel lumen
2. **Add More Points** - Place intermediate control points
3. **Improve Segmentation** - Refine vessel segmentation quality
4. **Simplify Geometry** - Extract shorter segments for complex vessels

#### CPR Processing Issues
**Problem:** CPR fails or produces distorted results
**Solutions:**
1. **Verify Centerline** - Ensure centerline quality is good
2. **Check Centerline Length** - Very short centerlines may fail
3. **Restart Process** - Clear and restart from centerline extraction
4. **Memory Issues** - Close other applications if system is low on memory

#### UI Elements Not Appearing
**Problem:** Buttons or controls don't show up
**Solutions:**
1. **Wait for Processing** - Some controls appear after processing completes
2. **Restart Module** - Navigate away and back to workflow module
3. **Check Console** - Look for error messages in Python console
4. **Restart Slicer** - Complete restart if issues persist

### Performance Optimization

#### For Large Datasets
1. **Crop Aggressively** - Reduce volume size as much as possible
2. **Lower Resolution** - Consider resampling very high-resolution data
3. **Close Other Applications** - Free up system memory
4. **Use SSD Storage** - Faster disk access improves performance

#### For Complex Geometries
1. **Multiple Segments** - Break complex vessels into segments
2. **Simplified Segmentation** - Use cleaner, simpler segmentations
3. **Strategic Point Placement** - Use more control points for guidance

### Error Recovery

#### Workflow Interruption
If the workflow is interrupted or gets stuck:

1. **Check Current State** - Identify which step you're on
2. **Manual Navigation** - Go to appropriate Slicer module manually
3. **Restart from Checkpoint** - Use saved scene if available
4. **Clear and Restart** - Use workflow reset functions if needed

#### Data Recovery
1. **Save Early and Often** - Save scene at each major step
2. **Export Key Data** - Export centerlines, segmentations separately
3. **Backup Strategy** - Keep copies of important analysis results

---

## Tips and Best Practices

### Workflow Efficiency

#### Preparation
1. **Organize Data** - Keep DICOM files in clearly labeled folders
2. **Quality Check** - Verify image quality before starting analysis
3. **Plan Analysis** - Identify key measurements needed before starting
4. **Save Strategy** - Plan where and how to save results

#### During Analysis
1. **Work Systematically** - Complete each step fully before proceeding
2. **Document Decisions** - Note threshold values, ROI choices, etc.
3. **Multiple Views** - Use different slice orientations for verification
4. **Incremental Saves** - Save scene after each major step

### Quality Assurance

#### Segmentation Quality
1. **Visual Inspection** - Carefully review segmentation in 3D
2. **Edge Definition** - Ensure clean vessel boundaries
3. **Connectivity** - Verify vessel segments are connected
4. **Artifact Removal** - Remove non-vessel structures

#### Centerline Quality
1. **Smoothness** - Centerline should follow vessel smoothly
2. **Centering** - Centerline should run through vessel center
3. **Completeness** - Should extend through region of interest
4. **Branch Handling** - Proper handling of vessel bifurcations

#### Measurement Accuracy
1. **Consistent Methods** - Use same measurement approach throughout
2. **Multiple Measurements** - Take several measurements for averaging
3. **Reference Standards** - Compare with known measurement methods
4. **Validation** - Cross-check critical measurements

### Advanced Usage

#### Batch Processing
While not directly supported, you can optimize for multiple cases:
1. **Standardize Parameters** - Use consistent threshold values
2. **Template Approach** - Save successful parameter sets
3. **Systematic Workflow** - Develop standard operating procedures

#### Integration with Other Tools
1. **Export Data** - Export results for use in other software
2. **Import Results** - Import external analysis results
3. **Comparative Analysis** - Use multiple workflow runs for comparison

#### Customization
1. **Parameter Tuning** - Adjust thresholds and settings for your data type
2. **Workflow Modification** - Skip or repeat steps as needed for specific use cases
3. **Output Formats** - Choose appropriate export formats for downstream analysis

### Educational Use

#### Learning the Workflow
1. **Start Simple** - Begin with clear, high-quality datasets
2. **Understand Each Step** - Learn what each processing step accomplishes
3. **Experiment Safely** - Use copies of data for learning
4. **Compare Methods** - Try different approaches on same data

#### Teaching Others
1. **Demonstrate Step-by-Step** - Show each workflow step clearly
2. **Explain Rationale** - Explain why each step is necessary
3. **Common Mistakes** - Point out typical errors and how to avoid them
4. **Best Practices** - Share tips for efficient and accurate analysis

---

## Appendices

### Appendix A: File Formats Supported

#### Input Formats
- **DICOM** - Standard medical imaging format (.dcm, .dicom, or no extension)
- **NRRD** - Nearly Raw Raster Data (.nrrd)
- **NIfTI** - Neuroimaging Informatics Technology Initiative (.nii, .nii.gz)
- **MetaImage** - Medical image format (.mhd, .mha)

#### Output Formats
- **Scene Files** - Slicer scene format (.mrml, .mrb)
- **Segmentations** - Segmentation files (.seg.nrrd)
- **Models** - 3D model files (.vtk, .ply, .stl)
- **Transforms** - Transform files (.h5, .tfm)
- **Markups** - Markup files (.mrk.json)

### Appendix B: Keyboard Shortcuts

#### General Navigation
- **Ctrl + Mouse Wheel** - Zoom in/out
- **Middle Mouse Button** - Pan view
- **Left Mouse Button** - Rotate 3D view
- **Shift + Left Mouse** - Pan in slice views

#### Point Placement
- **Left Click** - Place point
- **Right Click** - Delete point (when in edit mode)
- **Esc** - Exit placement mode

### Appendix C: Hardware Requirements

#### Minimum Requirements
- **CPU** - Intel i5 or AMD equivalent
- **Memory** - 8GB RAM
- **Graphics** - OpenGL 3.2 compatible
- **Storage** - 5GB free space

#### Recommended Requirements
- **CPU** - Intel i7 or AMD equivalent
- **Memory** - 16GB+ RAM
- **Graphics** - Dedicated GPU with 2GB+ VRAM
- **Storage** - SSD with 20GB+ free space

### Appendix D: Version History and Updates

This manual corresponds to the DAI Workflow Extension as of November 2025. Check for updates and new features in future versions.

---

**End of User Manual**

*For technical support, advanced customization, or feature requests, please contact the development team or refer to the technical documentation.*