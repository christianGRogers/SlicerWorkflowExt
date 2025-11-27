# Standard library imports
import math
import os
import time

# Third-party imports
import numpy as np
import vtk

# Slicer imports
import slicer
import qt

# Import DICOM utilities with error handling
try:
    import DICOMLib
    from DICOMLib.DICOMUtils import TemporaryDICOMDatabase
    DICOM_UTILS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: DICOMLib not available: {e}")
    DICOM_UTILS_AVAILABLE = False

try:
    import ctk
except ImportError as e:
    print(f"Warning: ctk not available: {e}")
    ctk = None

"""
Slicer Guided Workflow for Vessel Centerline Extraction and CPR Visualization

Christian Rogers - So Lab - Lawson - UWO (2025)

"""

# Initialize workflow by collapsing left panel on module load
def initialize_workflow_ui():
    """Initialize the workflow UI state - collapse left panel on startup"""
    try:
        # Use QTimer to ensure this runs after the UI is fully loaded
        qt.QTimer.singleShot(1000, force_collapse_left_panel_on_startup)
    except Exception as e:
        print(f"Warning: Could not initialize workflow UI: {e}")

# Call initialization when module is imported
try:
    initialize_workflow_ui()
except Exception as e:
    print(f"Warning: Could not call initialize_workflow_ui: {e}")

# Set up scene save observer after functions are defined
def setup_module_observers():
    """Set up observers after all functions are defined"""
    try:
        setup_scene_save_observer()
    except Exception as e:
        print(f"Warning: Could not set up scene save observer: {e}")









def find_working_volume():
    """
    Find the appropriate volume to work with, preferring cropped and visible volumes
    """
    try:
        # Strategy 0: Check if we have a stored reference to the cropped volume
        if hasattr(slicer.modules, 'WorkflowCroppedVolume'):
            cropped_volume = slicer.modules.WorkflowCroppedVolume
            if cropped_volume and not cropped_volume.IsA('vtkObject'):  # Check if node still exists
                return cropped_volume
            # Reference exists but node is invalid, continue to other strategies
        
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        
        if not volume_nodes:
            return None
        
        # Strategy 1: Look for cropped volumes (these are most recent and relevant)
        for volume in volume_nodes:
            if 'crop' in volume.GetName().lower():
                return volume
        
        # Strategy 2: Look for visible volumes (not hidden)
        visible_volumes = []
        for volume in volume_nodes:
            display_node = volume.GetDisplayNode()
            if display_node and display_node.GetVisibility():
                visible_volumes.append(volume)
        
        if len(visible_volumes) == 1:
            return visible_volumes[0]
        elif len(visible_volumes) > 1:
            # If multiple visible volumes, prefer non-straightened ones for initial segmentation
            for volume in visible_volumes:
                if 'straight' not in volume.GetName().lower():
                    return volume
            # Fallback to first visible volume
            return visible_volumes[0]
        
        # Strategy 3: Check the active volume in slice views
        try:
            selection_node = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
            if selection_node:
                active_volume_id = selection_node.GetActiveVolumeID()
                if active_volume_id:
                    active_volume = slicer.mrmlScene.GetNodeByID(active_volume_id)
                    if active_volume and active_volume.IsA("vtkMRMLScalarVolumeNode"):
                        return active_volume
        except Exception as e:
            print(f"Warning: Could not get active volume from selection node: {e}")
        
        # Strategy 4: Fallback to first volume, but warn user
        first_volume = volume_nodes[0]
        
        return first_volume
        
    except Exception as e:
        return slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")

def force_collapse_left_panel_on_startup():
    """Force collapse of left panel on startup - more aggressive approach"""
    try:
        main_window = slicer.util.mainWindow()
        if not main_window:
            return False
            
        success = False
        
        # Method 1: Try to find and hide the module panel dock widget
        try:
            dock_widgets = main_window.findChildren(qt.QDockWidget)
            for widget in dock_widgets:
                widget_name = widget.objectName()
                if widget_name and ('module' in widget_name.lower() or 'panel' in widget_name.lower()):
                    widget.hide()
                    success = True
        except Exception as e:
            print(f"Warning: Could not hide dock widgets: {e}")
        
        # Method 2: Try specific known panel names
        try:
            known_panel_names = ['PanelDockWidget', 'ModulePanelDockWidget']
            for panel_name in known_panel_names:
                panels = main_window.findChildren(qt.QWidget, panel_name)
                for panel in panels:
                    panel.hide()
                    success = True
        except Exception as e:
            print(f"Warning: Could not hide known panel widgets: {e}")
        
        # Method 3: Try to find all QWidget children and hide panel-related ones
        try:
            all_widgets = main_window.findChildren(qt.QWidget)
            for widget in all_widgets:
                widget_name = widget.objectName()
                if widget_name and ("PanelDockWidget" in widget_name or "ModulePanel" in widget_name):
                    widget.hide()
                    success = True
        except Exception as e:
            print(f"Warning: Could not hide panel-related widgets: {e}")
        
        return success
        
    except Exception as e:
        print(f"Error in force_collapse_left_panel_on_startup: {e}")
        return False

def collapse_left_module_panel():
    """
    Collapse the left module panel to maximize view space during workflow.
    """
    try:
        main_window = slicer.util.mainWindow()
        if not main_window:
            return False
        
        success = False
        
        # Method 1: Find and collapse/hide dock widgets
        try:
            dock_widgets = main_window.findChildren(qt.QDockWidget)
            for widget in dock_widgets:
                widget_name = widget.objectName()
                if widget_name and ('module' in widget_name.lower() or 'panel' in widget_name.lower()):
                    widget.hide()
                    success = True
        except Exception as e:
            print(f"Warning: Could not hide dock widgets in collapse_left_module_panel: {e}")
        
        # Method 2: Try specific panel names
        try:
            panel_names = ['ModulePanelDockWidget', 'PanelDockWidget']
            for panel_name in panel_names:
                panels = main_window.findChildren(qt.QWidget, panel_name)
                for panel in panels:
                    panel.hide()
                    success = True
        except Exception as e:
            print(f"Warning: Could not hide specific panels in collapse_left_module_panel: {e}")
        
        return success
        
    except Exception as e:
        print(f"Error in collapse_left_module_panel: {e}")
        return False

def expand_left_module_panel():
    """
    Expand the left module panel when needed (e.g., for Extract Centerline step).
    """
    try:
        main_window = slicer.util.mainWindow()
        if not main_window:
            return False
        
        success = False
        
        # Method 1: Find and show dock widgets
        try:
            dock_widgets = main_window.findChildren(qt.QDockWidget)
            for widget in dock_widgets:
                widget_name = widget.objectName()
                if widget_name and ('module' in widget_name.lower() or 'panel' in widget_name.lower()):
                    widget.show()
                    success = True
        except Exception as e:
            print(f"Warning: Could not show dock widgets in expand_left_module_panel: {e}")
        
        # Method 2: Try specific panel names
        try:
            panel_names = ['ModulePanelDockWidget', 'PanelDockWidget']
            for panel_name in panel_names:
                panels = main_window.findChildren(qt.QWidget, panel_name)
                for panel in panels:
                    panel.show()
                    success = True
        except Exception as e:
            print(f"Warning: Could not show specific panels in expand_left_module_panel: {e}")
        
        return success
        
    except Exception as e:
        print(f"Error in expand_left_module_panel: {e}")
        return False

def get_volume_slice_thickness(volume_node):
    """
    Get the slice thickness from a volume node's spacing information.
    Returns the minimum spacing value (typically the slice thickness) in mm.
    
    Args:
        volume_node: The vtkMRMLScalarVolumeNode to get spacing from
        
    Returns:
        float: The slice thickness in mm, or 0.4 as fallback if cannot be determined
    """
    try:
        if not volume_node:
            return 0.4  # Fallback to original hardcoded value
        
        # Get the spacing information from the volume
        spacing = volume_node.GetSpacing()
        
        if spacing:
            # Spacing is typically [x, y, z] where z is the slice thickness
            # Use the minimum spacing value as it's typically the slice thickness
            slice_thickness = min(abs(spacing[0]), abs(spacing[1]), abs(spacing[2]))
            
            # Ensure we have a reasonable value (between 0.1 and 10.0 mm)
            if 0.1 <= slice_thickness <= 10.0:
                return slice_thickness
        
        # Try alternative method using image data
        image_data = volume_node.GetImageData()
        if image_data:
            spacing = image_data.GetSpacing()
            if spacing:
                slice_thickness = min(abs(spacing[0]), abs(spacing[1]), abs(spacing[2]))
                if 0.1 <= slice_thickness <= 10.0:
                    return slice_thickness
        
        # Fallback to original value if we can't determine spacing
        return 0.4
        
    except Exception as e:
        # Fallback to original hardcoded value on any error
        return 0.4

def hide_centerlines_from_views():
    """
    Hide all centerline-related nodes from views by setting visibility to False.
    Keeps nodes in scene but makes them invisible.
    """
    try:

        hidden_count = 0
        
        # Hide all markup fiducial nodes (centerline points)
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for fiducial_node in fiducial_nodes:
            display_node = fiducial_node.GetDisplayNode()
            if display_node:
                display_node.SetVisibility(False)
                hidden_count += 1
        
        # Hide all markup curve nodes (centerline curves)
        curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsCurveNode')
        for curve_node in curve_nodes:
            display_node = curve_node.GetDisplayNode()
            if display_node:
                display_node.SetVisibility(False)

                hidden_count += 1
        
        # Hide all general markup nodes (catch-all for any other markup types)
        markup_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsNode')
        for markup_node in markup_nodes:
            # Skip if already processed as fiducial or curve node
            if markup_node in fiducial_nodes or markup_node in curve_nodes:
                continue
                
            display_node = markup_node.GetDisplayNode()
            if display_node:
                display_node.SetVisibility(False)
                hidden_count += 1
        
        # Hide all curve model nodes (centerline curves converted to models)
        model_nodes = slicer.util.getNodesByClass('vtkMRMLModelNode')
        for model_node in model_nodes:
            # Check if this looks like a centerline curve model
            node_name = model_node.GetName().lower()
            if ('curve' in node_name and 'model' in node_name) or 'centerline' in node_name or 'start-slice' in node_name:
                display_node = model_node.GetDisplayNode()
                if display_node:
                    display_node.SetVisibility(False)
                    hidden_count += 1
        
        # Also check for stored workflow markup node
        if hasattr(slicer.modules, 'WorkflowMarkupNode'):
            workflow_markup = slicer.modules.WorkflowMarkupNode
            if workflow_markup:
                display_node = workflow_markup.GetDisplayNode()
                if display_node:
                    display_node.SetVisibility(False)
                    hidden_count += 1
        
        
    except Exception as e:
        pass

def hide_cpr_slice_size_controls():
    """
    Hide the slice size controls (label and coordinates widget) from the CPR module UI.
    This removes the slice size text boxes when CPR is opened.
    """
    try:
        
        # Get the CPR module widget
        cpr_widget = slicer.modules.curvedplanarreformat.widgetRepresentation()
        if not cpr_widget:
            return False
        
        # Try to get the CPR module instance
        cpr_module = None
        if hasattr(cpr_widget, 'self'):
            try:
                cpr_module = cpr_widget.self()
            except Exception as e:
                pass
        
        if not cpr_module:
            cpr_module = cpr_widget
        
        # Look for the slice size controls in the UI
        controls_hidden = False
        
        # Method 1: Try to access via ui attribute (most common pattern)
        if hasattr(cpr_module, 'ui'):
            ui = cpr_module.ui
            
            
            if hasattr(ui, 'label_3'):
                ui.label_3.setVisible(False)
                controls_hidden = True
            
            
            if hasattr(ui, 'sliceSizeCoordinatesWidget'):
                ui.sliceSizeCoordinatesWidget.setVisible(False)
                controls_hidden = True
        
        # Method 2: Search for controls by object name if direct access didn't work
        if not controls_hidden:
            # Find all QLabel widgets and look for the one with "Slice size:" text
            labels = cpr_widget.findChildren(qt.QLabel)
            for label in labels:
                if hasattr(label, 'text') and label.text() == "Slice size:":
                    label.setVisible(False)
                    controls_hidden = True
                    break
            
            # Find the coordinates widget by class name
            coord_widgets = cpr_widget.findChildren("qMRMLCoordinatesWidget")
            for widget in coord_widgets:
                # Check if this is likely the slice size widget by checking nearby labels
                parent = widget.parent()
                if parent:
                    # Look for siblings that might be the slice size label
                    siblings = parent.findChildren(qt.QLabel)
                    for sibling in siblings:
                        if hasattr(sibling, 'text') and sibling.text() == "Slice size:":
                            widget.setVisible(False)
                            controls_hidden = True
                            break
                    if controls_hidden:
                        break
        
        # Method 3: Alternative approach - hide by object name
        if not controls_hidden:
            slice_label = cpr_widget.findChild(qt.QLabel, "label_3")
            if slice_label:
                slice_label.setVisible(False)
                controls_hidden = True
            
            coord_widget = cpr_widget.findChild("qMRMLCoordinatesWidget", "sliceSizeCoordinatesWidget")
            if coord_widget:
                coord_widget.setVisible(False)
                controls_hidden = True
        
        if controls_hidden:
            return True
        else:
            return False
            
    except Exception as e:
        return False

def ask_user_for_markup_import():
    """
    Ask the user if they want to import markup workflow files.
    Now handles workflow continuation directly instead of just returning boolean.
    """
    try:
        result = slicer.util.confirmYesNoDisplay(
            "Would you like to import markup workflow files?\n\n"
            "This will prompt you to import:\n"
            "• Markup/point list file (.mrk.json, .fcsv, etc.)\n"
            "• Straightened volume file (.nrrd, .nii, etc.)\n"
            "• Transform file (.tfm, .h5, etc.)\n\n"
            "• YES: Import all files, create curve models, and open Data module\n"
            "• NO: Continue with normal segmentation workflow",
            windowTitle="Import Markup Workflow Files"
        )
        
        if result:
            # User wants to import markup - use the full markup workflow function
            # Call the function that handles markup import and continues workflow
            markup_workflow_after_crop()
        else:
            # User declined markup import - continue with normal threshold workflow
            continue_workflow_without_markup()
            
        return result
    except Exception as e:
        pass
        return False

def ask_user_for_segmentation_import():
    """
    Ask the user if they want to import an existing segmentation file to start alternate workflow
    Returns True if yes, False if no
    """
    try:
        result = slicer.util.confirmYesNoDisplay(
            "Would you like to import an existing segmentation file?\n\n"
            "This will:\n"
            "• Skip the threshold segmentation step\n"
            "• Load your existing segmentation\n"
            "• Proceed directly to centerline extraction\n\n"
            "• YES: Import segmentation file (.seg.nrrd, .nrrd, etc.)\n"
            "• NO: Continue with normal threshold segmentation workflow",
            windowTitle="Import Existing Segmentation"
        )
        return result
    except Exception as e:
        return False

def import_markup_file():
    """
    Let the user select a source folder containing markup files and automatically create tube masks
    Expects files like: Circle_start-slice-1.mrk.json, Circle_end-slice-1.mrk.json, etc.
    Also automatically imports transform file and "Straightened Volume"
    """
    try:
        # Create folder dialog for markup import
        folder_dialog = qt.QFileDialog(slicer.util.mainWindow())
        folder_dialog.setWindowTitle("Select Source Folder with Markup Files")
        folder_dialog.setFileMode(qt.QFileDialog.Directory)
        folder_dialog.setAcceptMode(qt.QFileDialog.AcceptOpen)
        
        if folder_dialog.exec_():
            selected_folder = folder_dialog.selectedFiles()[0]
            
            # Process the folder and create tube masks
            success = process_markup_folder_and_create_tubes(selected_folder)
            
            if success:
                slicer.util.infoDisplay("Successfully imported markup files and created tube masks from source folder.")
                return True
            else:
                slicer.util.errorDisplay("Failed to process markup files from source folder.")
                return None
        
        return None
        
    except Exception as e:
        slicer.util.errorDisplay(f"Error importing markup folder: {str(e)}")
        return None

def process_markup_folder_and_create_tubes(folder_path):
    """
    Process a folder containing markup files and create tube masks automatically
    """
    import os
    import json
    
    try:
        
        # Find all markup files in the folder
        markup_files = {}
        transform_file = None
        pre_lesion_file = None
        post_lesion_file = None

        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            
            if filename.endswith('.mrk.json'):
                # Parse the filename to extract slice information
                if 'Circle_start-slice-' in filename:
                    slice_num = filename.split('start-slice-')[1].split('.')[0]
                    if slice_num not in markup_files:
                        markup_files[slice_num] = {}
                    markup_files[slice_num]['start'] = file_path
                elif 'Circle_end-slice-' in filename:
                    slice_num = filename.split('end-slice-')[1].split('.')[0]
                    if slice_num not in markup_files:
                        markup_files[slice_num] = {}
                    markup_files[slice_num]['end'] = file_path
                elif 'Circle_pre-lesion' in filename:
                    pre_lesion_file = file_path
                elif 'Circle_post-lesion' in filename:
                    post_lesion_file = file_path
            elif filename.endswith('.tfm') or filename.endswith('.h5'):
                # Found transform file
                transform_file = file_path
        
        
        if not markup_files:
            slicer.util.errorDisplay("No markup files found in the selected folder.")
            return False
        
        # Load pre and post lesion circles if they exist
        if pre_lesion_file:
            try:
                pre_lesion_markup = slicer.util.loadMarkups(pre_lesion_file)
                if pre_lesion_markup:
                    pre_lesion_markup.SetName("Circle_pre-lesion")
            except Exception as e:
                pass
        
        if post_lesion_file:
            try:
                post_lesion_markup = slicer.util.loadMarkups(post_lesion_file)
                if post_lesion_markup:
                    post_lesion_markup.SetName("Circle_post-lesion")
            except Exception as e:
                pass
        
        # Load the "Straightened Volume" if it exists
        straightened_volume_path = None
        for filename in os.listdir(folder_path):
            if 'Straightened Volume' in filename and (filename.endswith('.nrrd') or filename.endswith('.nii')):
                straightened_volume_path = os.path.join(folder_path, filename)
                break
        
        if straightened_volume_path:
            try:
                straightened_volume = slicer.util.loadVolume(straightened_volume_path)
                if straightened_volume:
                    slicer.modules.WorkflowStraightenedVolume = straightened_volume
            except Exception as e:
                pass
        
        # Load transform file if found
        if transform_file:
            try:
                transform_node = slicer.util.loadTransform(transform_file)
                if transform_node:
                    slicer.modules.WorkflowTransform = transform_node
            except Exception as e:
                pass
        
        # Create tube masks from markup file pairs
        created_tubes = []
        tube_colors = [
            (1.0, 0.0, 0.0),  # Red
            (0.0, 1.0, 0.0),  # Green  
            (0.0, 0.0, 1.0),  # Blue
            (1.0, 1.0, 0.0),  # Yellow
            (1.0, 0.0, 1.0),  # Magenta
            (0.0, 1.0, 1.0),  # Cyan
            (1.0, 0.5, 0.0),  # Orange
            (0.5, 0.0, 1.0),  # Purple
        ]
        
        for slice_num in sorted(markup_files.keys(), key=int):
            slice_data = markup_files[slice_num]
            
            if 'start' in slice_data and 'end' in slice_data:
                # Load both markup files and extract first points
                start_point = load_first_point_from_markup(slice_data['start'])
                end_point = load_first_point_from_markup(slice_data['end'])

                if start_point and end_point:
                    # Create tube mask from these two points
                    tube_index = int(slice_num) - 1
                    color_index = tube_index % len(tube_colors)
                    tube_model = create_tube_from_two_points(
                        start_point, end_point, 
                        f"TubeMask_slice_{slice_num}", 
                        tube_colors[color_index]
                    )
                    
                    if tube_model:
                        created_tubes.append(tube_model)

        
        print(f"Created {len(created_tubes)} tubes total")
        
        if created_tubes:
            # Set workflow flag to indicate markup was imported
            slicer.modules.WorkflowUsingMarkup = True
            return True
        else:
            return False
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False

def load_first_point_from_markup(markup_file_path):
    """
    Load the first point from a markup file
    """
    import json
    
    try:
        print(f"Loading markup file: {markup_file_path}")
        with open(markup_file_path, 'r') as f:
            markup_data = json.load(f)

        
        # Extract the first control point
        if 'markups' in markup_data and len(markup_data['markups']) > 0:
            markup = markup_data['markups'][0]
            
            if 'controlPoints' in markup and len(markup['controlPoints']) > 0:
                first_point = markup['controlPoints'][0]
                
                if 'position' in first_point:
                    position = first_point['position']
                    return position
        
        return None
        
    except Exception as e:
        print(f"Error loading markup file {markup_file_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_tube_from_two_points(start_point, end_point, tube_name, color):
    """
    Create a tube model from two points
    """
    try:
        print(f"Creating tube '{tube_name}' from points {start_point} to {end_point}")
        
        # Create a curve markup with the two points
        curve_markup = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode")
        curve_markup.SetName(f"Curve_{tube_name}")
        print(f"Created curve markup: {curve_markup.GetName()}")
        
        # Add the two points to the curve (points are already in world coordinates)
        curve_markup.AddControlPoint(start_point[0], start_point[1], start_point[2])
        curve_markup.AddControlPoint(end_point[0], end_point[1], end_point[2])
        print(f"Added {curve_markup.GetNumberOfControlPoints()} points to curve")
        
        # Create tube from the curve
        tube_model = create_tube_from_curve_with_color(curve_markup, tube_name, color)
        print(f"Tube creation result: {tube_model}")
        
        # Clean up the temporary curve
        slicer.mrmlScene.RemoveNode(curve_markup)
        print(f"Cleaned up temporary curve")
        
        return tube_model
        
    except Exception as e:
        print(f"Error creating tube from two points: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_tube_from_curve_with_color(curve_markup, tube_name, color):
    """
    Create a tube model from a curve markup with specified color
    """
    try:
        print(f"Creating tube model from curve: {curve_markup.GetName()}")
        
        # Get the curve polydata
        curve_polydata = curve_markup.GetCurveWorld()
        if not curve_polydata:
            print("Failed to get curve polydata")
            return None
            
        if curve_polydata.GetNumberOfPoints() < 2:
            print(f"Curve has insufficient points: {curve_polydata.GetNumberOfPoints()}")
            return None
        
        print(f"Curve has {curve_polydata.GetNumberOfPoints()} points")
        
        # Create tube filter
        import vtk
        tube_filter = vtk.vtkTubeFilter()
        tube_filter.SetInputData(curve_polydata)
        tube_filter.SetRadius(2.0)  # 2mm radius
        tube_filter.SetNumberOfSides(12)
        tube_filter.CappingOn()
        tube_filter.Update()
        print("Tube filter created and updated")
        
        # Create model node
        tube_model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
        tube_model.SetName(tube_name)
        tube_model.SetAndObservePolyData(tube_filter.GetOutput())
        print(f"Created model node: {tube_model.GetName()}")
        
        # Create display node and set color
        tube_model.CreateDefaultDisplayNodes()
        display_node = tube_model.GetDisplayNode()
        if display_node:
            display_node.SetColor(color)
            display_node.SetOpacity(0.8)
            display_node.SetVisibility(True)
            print(f"Set display properties: color={color}, opacity=0.8")
        else:
            print("Failed to get display node")
        
        return tube_model
        
    except Exception as e:
        print(f"Error creating tube from curve: {e}")
        import traceback
        traceback.print_exc()
        return None
        slicer.util.errorDisplay(f"Error in markup file selection: {str(e)}")
        return None

def import_straightened_volume():
    """
    Let the user select and import a straightened volume file
    Returns the imported volume node or None if cancelled/failed
    """
    try:
        # Create file dialog for volume import
        file_dialog = qt.QFileDialog(slicer.util.mainWindow())
        file_dialog.setWindowTitle("Select Straightened Volume File")
        file_dialog.setFileMode(qt.QFileDialog.ExistingFile)
        file_dialog.setAcceptMode(qt.QFileDialog.AcceptOpen)
        
        # Set file filters for common volume formats
        file_dialog.setNameFilters([
            "All Volume Files (*.nrrd *.nii *.nii.gz *.mhd *.vtk)",
            "NRRD Files (*.nrrd)",
            "NIfTI Files (*.nii *.nii.gz)",
            "MetaImage Files (*.mhd)",
            "VTK Files (*.vtk)",
            "All Files (*.*)"
        ])
        
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                volume_file = selected_files[0]
                
                try:
                    # Get existing volume nodes count to find the new one
                    existing_volumes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
                    
                    # Load the volume file
                    volume_node = slicer.util.loadVolume(volume_file)
                    
                    if volume_node:
                        # Set a recognizable name
                        volume_node.SetName("StraightenedVolume")
                        
                        # Make the volume visible in all slice views
                        set_volume_visible_in_slice_views(volume_node)
                        
                        slicer.util.infoDisplay(f"Successfully imported straightened volume: {volume_node.GetName()}")
                        return volume_node
                    else:
                        slicer.util.errorDisplay("Failed to load the selected volume file.")
                        return None
                        
                except Exception as e:
                    slicer.util.errorDisplay(f"Error loading volume file: {str(e)}")
                    return None
            
        return None
        
    except Exception as e:
        slicer.util.errorDisplay(f"Error in volume file selection: {str(e)}")
        return None

def import_transform_file():
    """
    Let the user select and import a transform file
    Returns the imported transform node or None if cancelled/failed
    """
    try:
        # Create file dialog for transform import
        file_dialog = qt.QFileDialog(slicer.util.mainWindow())
        file_dialog.setWindowTitle("Select Transform File")
        file_dialog.setFileMode(qt.QFileDialog.ExistingFile)
        file_dialog.setAcceptMode(qt.QFileDialog.AcceptOpen)
        
        # Set file filters for common transform formats
        file_dialog.setNameFilters([
            "All Transform Files (*.tfm *.h5 *.txt *.mat)",
            "ITK Transform Files (*.tfm)",
            "HDF5 Transform Files (*.h5)",
            "Text Transform Files (*.txt)",
            "MATLAB Transform Files (*.mat)",
            "All Files (*.*)"
        ])
        
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                transform_file = selected_files[0]
                
                try:
                    # Get existing transform nodes count to find the new one
                    existing_transforms = slicer.util.getNodesByClass('vtkMRMLTransformNode')
                    
                    # Load the transform file
                    success = slicer.util.loadTransform(transform_file)
                    
                    if success:
                        # Find the newly loaded transform node
                        new_transforms = slicer.util.getNodesByClass('vtkMRMLTransformNode')
                        new_transform_nodes = [node for node in new_transforms if node not in existing_transforms]
                        
                        if new_transform_nodes:
                            transform_node = new_transform_nodes[0]  # Get the first new transform node
                            
                            # Set a recognizable name if it doesn't have one
                            if "Transform" not in transform_node.GetName():
                                transform_node.SetName("StraighteningTransform")
                            
                            # Make the transform visible
                            display_node = transform_node.GetDisplayNode()
                            if not display_node:
                                transform_node.CreateDefaultDisplayNodes()
                                display_node = transform_node.GetDisplayNode()
                            
                            if display_node:
                                display_node.SetVisibility(True)
                                display_node.SetVisibility3D(True)
                            
                            slicer.util.infoDisplay(f"Successfully imported transform: {transform_node.GetName()}")
                            return transform_node
                        else:
                            slicer.util.errorDisplay("Transform file loaded but no new transform node found.")
                            return None
                    else:
                        slicer.util.errorDisplay("Failed to load the selected transform file.")
                        return None
                        
                except Exception as e:
                    slicer.util.errorDisplay(f"Error loading transform file: {str(e)}")
                    return None
            
        return None
        
    except Exception as e:
        slicer.util.errorDisplay(f"Error in transform file selection: {str(e)}")
        return None

def import_segmentation_file():
    """
    Let the user select and import a segmentation file
    Returns the imported segmentation node or None if cancelled/failed
    """
    try:
        # Use Slicer's file dialog to select segmentation file
        file_dialog = qt.QFileDialog()
        file_dialog.setFileMode(qt.QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Segmentation Files (*.seg.nrrd *.nrrd *.nii *.nii.gz);;All Files (*)")
        file_dialog.setWindowTitle("Select Segmentation File")
        
        if file_dialog.exec():
            file_paths = file_dialog.selectedFiles()
            if file_paths:
                segmentation_file_path = file_paths[0]
                
                # Load the segmentation file
                try:
                    segmentation_node = None
                    
                    # Method 1: Direct segmentation loading
                    if segmentation_file_path.endswith('.seg.nrrd'):
                        segmentation_node = slicer.util.loadSegmentation(segmentation_file_path)
                    
                    # Method 2: Load as volume then convert to segmentation
                    elif segmentation_file_path.endswith(('.nrrd', '.nii', '.nii.gz')):
                        # Load as labelmap volume first
                        labelmap_node = slicer.util.loadLabelVolume(segmentation_file_path)
                        if labelmap_node:
                            # Convert labelmap to segmentation
                            segmentation_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
                            segmentation_node.SetName(f"ImportedSegmentation_{labelmap_node.GetName()}")
                            
                            # Import labelmap into segmentation
                            segmentationLogic = slicer.modules.segmentations.logic()
                            if segmentationLogic.ImportLabelmapToSegmentationNode(labelmap_node, segmentation_node):
                                # Remove the temporary labelmap
                                slicer.mrmlScene.RemoveNode(labelmap_node)
                            else:
                                slicer.mrmlScene.RemoveNode(segmentation_node)
                                segmentation_node = None
                    
                    if segmentation_node:
                        # Set reference geometry if volume exists
                        volume_node = find_working_volume()
                        if volume_node:
                            segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(volume_node)
                        
                        slicer.util.infoDisplay(f"Segmentation file loaded successfully: {segmentation_node.GetName()}")
                        
                        # Store workflow flags for imported segmentation
                        slicer.modules.WorkflowUsingImportedSegmentation = True
                        slicer.modules.WorkflowImportedSegmentationNode = segmentation_node
                        
                        return segmentation_node
                    else:
                        slicer.util.errorDisplay(f"Failed to load segmentation file: {segmentation_file_path}")
                        return None
                        
                except Exception as load_error:
                    slicer.util.errorDisplay(f"Error loading segmentation file: {load_error}")
                    return None
        
        return None
        
    except Exception as e:
        slicer.util.errorDisplay(f"Error in segmentation file selection: {e}")
        return None

def start_imported_segmentation_workflow(segmentation_node, volume_node):
    """
    Start alternate workflow with imported segmentation - skip threshold creation and go directly to centerline extraction
    """
    try:
        # Ensure 3D view shows the segmentation
        show_segmentation_in_3d(segmentation_node)
        
        # Load the imported segmentation into the segment editor for potential editing
        load_into_segment_editor(segmentation_node, volume_node)
        
        # Set appropriate view layout
        set_3d_view_background_black()
        
        # Mark that dialog has been shown to prevent loops when continuing workflow
        slicer.modules.WorkflowDialogShown = True
        
        # Provide user feedback about the alternate workflow
        slicer.util.infoDisplay(
            "Imported segmentation workflow started.\n\n"
            "Next steps:\n"
            "1. Use scissors tools if you need to edit the segmentation\n"
            "2. When ready, continue to centerline extraction\n\n"
            "The threshold segmentation step has been skipped."
        )
        
    except Exception as e:
        slicer.util.errorDisplay(f"Error starting imported segmentation workflow: {e}")
        pass

def set_volume_visible_in_slice_views(volume_node):
    """
    Set the volume as visible and active in all slice views
    """
    try:
        # Get the application logic
        app_logic = slicer.app.applicationLogic()
        if app_logic:
            selection_node = app_logic.GetSelectionNode()
            if selection_node:
                # Set as active volume
                selection_node.SetActiveVolumeID(volume_node.GetID())
                selection_node.SetSecondaryVolumeID(volume_node.GetID())
                
                # Propagate the selection
                app_logic.PropagateVolumeSelection()
        
        # Also set in slice composite nodes directly
        layout_manager = slicer.app.layoutManager()
        if layout_manager:
            for slice_view_name in ['Red', 'Yellow', 'Green']:
                slice_logic = layout_manager.sliceWidget(slice_view_name).sliceLogic()
                if slice_logic:
                    composite_node = slice_logic.GetSliceCompositeNode()
                    if composite_node:
                        composite_node.SetBackgroundVolumeID(volume_node.GetID())
        
        # Reset field of view to show the volume properly
        slicer.util.resetSliceViews()
    
        
    except Exception as e:
        pass

def show_red_green_views_only():
    """
    Switch Slicer layout to show only Red and Green slice views side-by-side.
    Also set the current working volume in both views and fit to slice.
    """
    try:
        lm = slicer.app.layoutManager()
        if not lm:
            return False

        # Define a custom two-slice layout (Red | Green)
        layout_xml = (
            '<layout type="horizontal">'
            '  <item>'
            '    <view class="vtkMRMLSliceNode" singletontag="Red">'
            '      <property name="orientation" action="default">Axial</property>'
            '      <property name="viewlabel" action="default">R</property>'
            '      <property name="layoutlabel" action="default">Red</property>'
            '    </view>'
            '  </item>'
            '  <item>'
            '    <view class="vtkMRMLSliceNode" singletontag="Green">'
            '      <property name="orientation" action="default">Sagittal</property>'
            '      <property name="viewlabel" action="default">G</property>'
            '      <property name="layoutlabel" action="default">Green</property>'
            '    </view>'
            '  </item>'
            '</layout>'
        )

        layout_node = lm.layoutLogic().GetLayoutNode()
        custom_layout_id = 55901  # Arbitrary, low collision risk
        # Register or replace the custom layout
        layout_node.AddLayoutDescription(custom_layout_id, layout_xml)
        layout_node.SetViewArrangement(custom_layout_id)

        # Assign background volume and fit to slice for both Red and Green
        vol = find_working_volume()
        for name in ("Red", "Green"):
            w = lm.sliceWidget(name)
            if not w:
                continue
            comp = w.mrmlSliceCompositeNode()
            if vol and comp:
                comp.SetBackgroundVolumeID(vol.GetID())
            logic = w.sliceLogic()
            if logic:
                logic.FitSliceToAll()

        slicer.app.processEvents()
        return True
    except Exception:
        return False

def set_three_up_view():
    """
    Switch Slicer layout to show three slice views side by side: Red, Green, Yellow (Axial, Sagittal, Coronal).
    This is used before cropping to give a complete view of the volume without 3D view.
    """
    try:
        lm = slicer.app.layoutManager()
        if not lm:
            return False

        # Define a custom three-slice layout (Red | Green | Yellow) side by side
        layout_xml = (
            '<layout type="horizontal">'
            '  <item>'
            '    <view class="vtkMRMLSliceNode" singletontag="Red">'
            '      <property name="orientation" action="default">Axial</property>'
            '      <property name="viewlabel" action="default">R</property>'
            '      <property name="layoutlabel" action="default">Red</property>'
            '    </view>'
            '  </item>'
            '  <item>'
            '    <view class="vtkMRMLSliceNode" singletontag="Green">'
            '      <property name="orientation" action="default">Sagittal</property>'
            '      <property name="viewlabel" action="default">G</property>'
            '      <property name="layoutlabel" action="default">Green</property>'
            '    </view>'
            '  </item>'
            '  <item>'
            '    <view class="vtkMRMLSliceNode" singletontag="Yellow">'
            '      <property name="orientation" action="default">Coronal</property>'
            '      <property name="viewlabel" action="default">Y</property>'
            '      <property name="layoutlabel" action="default">Yellow</property>'
            '    </view>'
            '  </item>'
            '</layout>'
        )

        layout_node = lm.layoutLogic().GetLayoutNode()
        custom_layout_id = 55902  # Custom ID for three-slice layout
        # Register or replace the custom layout
        layout_node.AddLayoutDescription(custom_layout_id, layout_xml)
        layout_node.SetViewArrangement(custom_layout_id)
        
        # Assign background volume for all three views
        vol = find_working_volume()
        for name in ("Red", "Green", "Yellow"):
            w = lm.sliceWidget(name)
            if not w:
                continue
            comp = w.mrmlSliceCompositeNode()
            if vol and comp:
                comp.SetBackgroundVolumeID(vol.GetID())
            logic = w.sliceLogic()
            if logic:
                logic.FitSliceToAll()

        # Give time for volumes to load into views before resetting
        slicer.app.processEvents()
        
        # Now call resetSliceViews after volumes are loaded for it to be effective
        slicer.util.resetSliceViews()

        # Final processing to ensure proper rendering
        slicer.app.processEvents()
        qt.QTimer.singleShot(100, lambda: slicer.app.processEvents())
        
        return True
    except Exception as e:
        pass
        return False



def set_3d_only_view():
    """
    Switch Slicer layout to show only the 3D view.
    This is used after cropping to focus on 3D visualization.
    """
    try:
        lm = slicer.app.layoutManager()
        if not lm:
            return False

        # Set to 3D-only layout (layout ID 4 in Slicer)
        layout_node = lm.layoutLogic().GetLayoutNode()
        layout_node.SetViewArrangement(4)  # 3D only view
        
        # Make sure 3D view shows the current working volume
        vol = find_working_volume()
        if vol:
            # Ensure volume is visible in 3D
            vol.SetDisplayVisibility(True)
            
            # Get 3D view and reset camera
            threeDWidget = lm.threeDWidget(0)
            if threeDWidget:
                threeDView = threeDWidget.threeDView()
                if threeDView:
                    threeDView.resetFocalPoint()
                    threeDView.resetCamera()

        slicer.app.processEvents()
        return True
    except Exception as e:
        pass
        return False

def create_curve_models_from_markup(markup_node):
    """
    Create curve models from markup points using the MarkupsToModel module.
    Creates n-1 curve models using pairs of consecutive points as start-slice-1 end-slice-1 format.
    
    Args:
        markup_node: vtkMRMLMarkupsNode containing the control points
        
    Returns:
        list: List of created vtkMRMLModelNode objects
        
    Example:
        If markup has 4 points, this creates 3 curve models:
        - CurveModel_start-slice-1_end-slice-2 (points 1-2)
        - CurveModel_start-slice-2_end-slice-3 (points 2-3)
        - CurveModel_start-slice-3_end-slice-4 (points 3-4)
    """
    try:
        if not markup_node:
            return []
        
        # Get number of control points
        num_points = markup_node.GetNumberOfControlPoints()
        if num_points < 2:
            slicer.util.infoDisplay("Need at least 2 points to create curve models.")
            return []
        
        
        # Load MarkupsToModel module
        try:
            markups_to_model = slicer.modules.markupstomodel
            markups_to_model_logic = markups_to_model.logic()
        except AttributeError:
            # Try alternative approach if MarkupsToModel is not available
            try:
                # Check if we can access the MarkupsToModel logic directly
                import MarkupsToModel
                markups_to_model_logic = MarkupsToModel.MarkupsToModelLogic()
                markups_to_model = True  # Flag that we have the module
            except ImportError:
                slicer.util.errorDisplay("MarkupsToModel module not found. Please install the MarkupsToModel extension.")
                return []
        
        created_models = []
        
        # Define distinct colors for each curve model (RGB values)
        distinct_colors = [
            (1.0, 0.0, 0.0),    # Red
            (0.0, 1.0, 0.0),    # Green  
            (0.0, 0.0, 1.0),    # Blue
            (1.0, 1.0, 0.0),    # Yellow
            (1.0, 0.0, 1.0),    # Magenta
            (0.0, 1.0, 1.0),    # Cyan
            (1.0, 0.5, 0.0),    # Orange
            (0.5, 0.0, 1.0),    # Purple
            (0.0, 0.5, 1.0),    # Sky Blue
            (1.0, 0.0, 0.5),    # Pink
            (0.5, 1.0, 0.0),    # Lime
            (1.0, 0.5, 0.5),    # Light Red
            (0.5, 0.5, 1.0),    # Light Blue
            (0.8, 0.8, 0.0),    # Olive
            (0.8, 0.0, 0.8),    # Dark Magenta
        ]
        
        # Create curve models for consecutive point pairs
        for i in range(num_points - 1):
            try:
                # Create a new markup node with just two points
                curve_markup = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
                curve_markup.SetName(f"start-slice-{i+1}_end-slice-{i+2}")
                
                # Copy the two consecutive points
                point1_pos = [0, 0, 0]
                point2_pos = [0, 0, 0]
                markup_node.GetNthControlPointPosition(i, point1_pos)
                markup_node.GetNthControlPointPosition(i+1, point2_pos)
                
                curve_markup.AddControlPoint(point1_pos)
                curve_markup.AddControlPoint(point2_pos)
                
                # Create output model node
                output_model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
                output_model.SetName(f"CurveModel_start-slice-{i+1}_end-slice-{i+2}")
                
                # Create display node for the model
                output_model.CreateDefaultDisplayNodes()
                
                # Try to create the curve model
                success = False
                try:
                    # Set up parameters for curve creation
                    markups_to_model_logic.SetInputMarkupsNode(curve_markup)
                    markups_to_model_logic.SetOutputModelNode(output_model)
                    
                    # Try to set model type to Curve
                    if hasattr(markups_to_model_logic, 'SetModelType'):
                        if hasattr(markups_to_model_logic, 'Curve'):
                            markups_to_model_logic.SetModelType(markups_to_model_logic.Curve)
                        else:
                            # Try alternative naming
                            markups_to_model_logic.SetModelType(1)  # Curve type is usually 1
                    
                    # Set curve parameters if available
                    if hasattr(markups_to_model_logic, 'SetTubeRadius'):
                        markups_to_model_logic.SetTubeRadius(4.0)  # Set radius to 4mm
                    if hasattr(markups_to_model_logic, 'SetTubeNumberOfSides'):
                        markups_to_model_logic.SetTubeNumberOfSides(8)
                    if hasattr(markups_to_model_logic, 'SetCurveType'):
                        if hasattr(markups_to_model_logic, 'Linear'):
                            markups_to_model_logic.SetCurveType(markups_to_model_logic.Linear)
                        else:
                            markups_to_model_logic.SetCurveType(0)  # Linear is usually 0
                    
                    # Update the model
                    markups_to_model_logic.UpdateOutputModel()
                    success = True
                    
                except Exception as model_error:
                    # Fallback: Create a simple line model using VTK
                    try:
                        points = vtk.vtkPoints()
                        points.InsertNextPoint(point1_pos)
                        points.InsertNextPoint(point2_pos)
                        
                        lines = vtk.vtkCellArray()
                        lines.InsertNextCell(2)
                        lines.InsertCellPoint(0)
                        lines.InsertCellPoint(1)
                        
                        polydata = vtk.vtkPolyData()
                        polydata.SetPoints(points)
                        polydata.SetLines(lines)
                        
                        # Create tube filter for thickness
                        tube_filter = vtk.vtkTubeFilter()
                        tube_filter.SetInputData(polydata)
                        tube_filter.SetRadius(4.0)  # Set radius to 4mm
                        tube_filter.SetNumberOfSides(8)
                        tube_filter.Update()
                        
                        output_model.SetAndObservePolyData(tube_filter.GetOutput())
                        success = True
                        
                    except Exception as vtk_error:
                        # Create basic polydata line
                        points = vtk.vtkPoints()
                        points.InsertNextPoint(point1_pos)
                        points.InsertNextPoint(point2_pos)
                        
                        lines = vtk.vtkCellArray()
                        lines.InsertNextCell(2)
                        lines.InsertCellPoint(0)
                        lines.InsertCellPoint(1)
                        
                        polydata = vtk.vtkPolyData()
                        polydata.SetPoints(points)
                        polydata.SetLines(lines)
                        
                        output_model.SetAndObservePolyData(polydata)
                        success = True
                
                if success:
                    # Ensure display node exists and set model display properties with distinct colors
                    display_node = output_model.GetDisplayNode()
                    if not display_node:
                        # If no display node, create one
                        output_model.CreateDefaultDisplayNodes()
                        display_node = output_model.GetDisplayNode()
                    
                    if display_node:
                        # Get color for this model (cycle through colors if we have more models than colors)
                        color_index = i % len(distinct_colors)
                        color = distinct_colors[color_index]
                        
                        # Set color and visibility properties
                        display_node.SetColor(color[0], color[1], color[2])
                        display_node.SetOpacity(0.8)
                        display_node.SetVisibility(True)
                        display_node.SetVisibility2D(True)
                        display_node.SetVisibility3D(True)
                        
                        # Set line/tube width if it's a line model
                        display_node.SetLineWidth(3)
                    
                    created_models.append(output_model)
                else:
                    # Remove failed model node
                    slicer.mrmlScene.RemoveNode(output_model)
                
                # Clean up the temporary markup node
                slicer.mrmlScene.RemoveNode(curve_markup)
                
            except Exception as e:
                continue
        
        # After creating all models, delete the first two and ensure remaining are visible
        models_to_delete = []
        if created_models and len(created_models) >= 2:
            # Mark first two models for deletion
            models_to_delete = created_models[:2]
            for i, model in enumerate(models_to_delete):
                slicer.mrmlScene.RemoveNode(model)
            
            # Update the created_models list to only include remaining models
            created_models = created_models[2:]
            
            # Double-check visibility and color for all remaining models
            for j, model in enumerate(created_models):
                display_node = model.GetDisplayNode()
                if not display_node:
                    # Create display node if it doesn't exist
                    model.CreateDefaultDisplayNodes()
                    display_node = model.GetDisplayNode()
                
                if display_node:
                    # Recalculate color index based on remaining models (j + 2 to account for deleted models)
                    color_index = (j + 2) % len(distinct_colors)
                    color = distinct_colors[color_index]
                    
                    # Ensure all visibility and color properties are set
                    display_node.SetVisibility(True)
                    display_node.SetVisibility2D(True)
                    display_node.SetVisibility3D(True)
                    display_node.SetColor(color[0], color[1], color[2])
                    display_node.SetOpacity(0.8)
                    display_node.SetLineWidth(3)
                    
        
        # Force a scene update to ensure all changes are applied
        slicer.app.processEvents()
        
        if created_models:
            
            
            total_created = len(created_models) + 2  # Account for deleted models
            slicer.util.infoDisplay(f"Successfully created {total_created} curve models from markup points.\n" + 
                                   f"Radius: 4mm\n" +
                                   f"Deleted: First 2 models\n" +
                                   f"Visible: {len(created_models)} models with distinct colors")
        else:
            slicer.util.errorDisplay("Failed to create any curve models.")
        
        return created_models
        
    except Exception as e:
        slicer.util.errorDisplay(f"Error creating curve models from markup: {str(e)}")
        return []

def open_data_module():
    """
    Open the Data module to display the imported markup and created curve models
    """
    try:
        # Switch to the Data module
        slicer.util.selectModule('Data')
        slicer.app.processEvents()
        
        # Expand the scene model hierarchy to show all nodes
        try:
            data_widget = slicer.modules.data.widgetRepresentation()
            if data_widget and hasattr(data_widget, 'self'):
                data_self = data_widget.self()
                if hasattr(data_self, 'sceneModel'):
                    scene_model = data_self.sceneModel
                    if hasattr(scene_model, 'expandAll'):
                        scene_model.expandAll()
        except Exception as expand_error:
            pass
        
        
    except Exception as e:
        slicer.util.errorDisplay(f"Error opening Data module: {str(e)}")

def set_3d_view_background_black():
    """
    Set the 3D view background to black using the working approach from ChangeViewColors example
    """
    try:
        # Get the first 3D view node (typically "View1")
        viewNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLViewNode")
        if not viewNode:
            # If no view node exists, try to get by name
            viewNode = slicer.util.getNode("View1")
        
        if viewNode:
            # Create black color (same as your working example)
            black_color = qt.QColor(0, 0, 0)  # RGB values 0,0,0 for black
            
            # Convert to normalized values (0-1 range) as in your working example
            r = black_color.red() / 255.0    # 0.0
            g = black_color.green() / 255.0  # 0.0  
            b = black_color.blue() / 255.0   # 0.0
            
            # Set background colors using the working method
            viewNode.SetBackgroundColor(r, g, b)
            viewNode.SetBackgroundColor2(r, g, b)  # Also set gradient background
    except Exception as e:
        pass

def create_threshold_segment_with_markup_only():
    """
    Main workflow function with markup import only (no segmentation import)
    """
    volume_node = find_working_volume()
    
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    
    # Initialize workflow flags
    slicer.modules.WorkflowUsingMarkup = False
    slicer.modules.WorkflowUsingImportedSegmentation = False
    
    # Ask user if they want to import markup
    want_markup = ask_user_for_markup_import()
    
    if want_markup:
        # User wants to import markup - handle all imports from source folder
        markup_success = import_markup_file()
        if markup_success:
            # Store markup workflow flag for later use
            slicer.modules.WorkflowUsingMarkup = True
            
            slicer.util.infoDisplay("Markup workflow imports completed. Tube masks created automatically.")
        else:
            # Markup import failed, continue with normal workflow
            slicer.util.infoDisplay("Markup import cancelled or failed. Continuing with normal workflow.")
            slicer.modules.WorkflowUsingMarkup = False
    
    # Continue with threshold workflow
    threshold_values = prompt_for_threshold_range()
    if threshold_values is None:
        return
    
    threshold_value_low, threshold_value_high = threshold_values
    
    segmentation_node = create_segmentation_from_threshold(volume_node, threshold_value_low, threshold_value_high)
    
    if segmentation_node:
        show_segmentation_in_3d(segmentation_node)
        load_into_segment_editor(segmentation_node, volume_node)
        
        # Only add post-threshold tools if markup was actually imported
        if hasattr(slicer.modules, 'WorkflowUsingMarkup') and slicer.modules.WorkflowUsingMarkup:
            add_post_threshold_tools_to_left_panel(segmentation_node, volume_node)
        else:
            pass

def markup_workflow_after_crop():
    """
    Handle markup import workflow after crop completion.
    This is called when user chooses to import markup from the post-ROI dialog.
    """
    try:
        volume_node = find_working_volume()
        if not volume_node:
            slicer.util.errorDisplay("No volume found for markup workflow.")
            return
            
        # Set workflow flags
        slicer.modules.WorkflowUsingMarkup = False
        slicer.modules.WorkflowUsingImportedSegmentation = False
        
        # Import markup file
        markup_success = import_markup_file()
        if markup_success:
            # Store markup workflow flag for later use
            slicer.modules.WorkflowUsingMarkup = True
            
            slicer.util.infoDisplay("Markup workflow imports completed. Tube masks created automatically.")
        else:
            # Markup import failed, continue with normal workflow
            slicer.util.infoDisplay("Markup import cancelled or failed. Continuing with normal workflow.")
            slicer.modules.WorkflowUsingMarkup = False
        
        # Continue with threshold workflow (same as create_threshold_segment_with_markup_only)
        threshold_values = prompt_for_threshold_range()
        if threshold_values is None:
            return
        
        threshold_value_low, threshold_value_high = threshold_values
        
        segmentation_node = create_segmentation_from_threshold(volume_node, threshold_value_low, threshold_value_high)
        
        if segmentation_node:
            show_segmentation_in_3d(segmentation_node)
            load_into_segment_editor(segmentation_node, volume_node)
            
            # After threshold segmentation, add scissors and markup tools to left panel
            add_post_threshold_tools_to_left_panel(segmentation_node, volume_node)
            
        else:
            pass
            
    except Exception as e:
        pass

def continue_workflow_without_markup():
    """
    Continue the workflow with threshold segmentation only (no markup import).
    Called when user declines markup import from the post-ROI dialog.
    """
    try:
        volume_node = find_working_volume()
        if not volume_node:
            slicer.util.errorDisplay("No volume found to continue workflow.")
            return
            
        # Set workflow flags for no markup
        slicer.modules.WorkflowUsingMarkup = False
        slicer.modules.WorkflowUsingImportedSegmentation = False
        
        # Continue with threshold segmentation workflow
        threshold_values = prompt_for_threshold_range()
        if threshold_values is None:
            return
        
        threshold_value_low, threshold_value_high = threshold_values
        
        segmentation_node = create_segmentation_from_threshold(volume_node, threshold_value_low, threshold_value_high)
        
        if segmentation_node:
            show_segmentation_in_3d(segmentation_node)
            load_into_segment_editor(segmentation_node, volume_node)
            
            # No post-threshold tools for non-markup workflow
        else:
            pass
            
    except Exception as e:
        pass

def add_post_threshold_tools_to_left_panel(segmentation_node, volume_node):
    """
    Add scissors tools and markup placement controls to the left module panel after threshold segmentation.
    Only shows when markup workflow is being used.
    """
    try:
        # Safety check: only show post-threshold tools if markup workflow is active
        if not (hasattr(slicer.modules, 'WorkflowUsingMarkup') and slicer.modules.WorkflowUsingMarkup):
            return
            
        # Expand left panel to show the new tools
        expand_left_module_panel()
        
        # Get the main window and find a suitable location for the tools
        main_window = slicer.util.mainWindow()
        if not main_window:
            return
        
        # Create a widget container for post-threshold tools
        if hasattr(slicer.modules, 'PostThresholdToolsWidget'):
            # Clean up existing widget first
            slicer.modules.PostThresholdToolsWidget.deleteLater()
        
        tools_widget = qt.QWidget()
        tools_widget.setWindowTitle("Post-Threshold Tools")
        tools_widget.setMinimumWidth(300)
        tools_widget.setMaximumWidth(350)
        
        # Create layout for tools
        layout = qt.QVBoxLayout(tools_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Add title
        title_label = qt.QLabel("Segmentation Editing Tools")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px;
                background-color: #ecf0f1;
                border-radius: 5px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Add scissors tool toggle button
        scissors_button = qt.QPushButton("Toggle Scissors Tool")
        scissors_button.setCheckable(True)
        scissors_button.setChecked(False)
        scissors_button.setStyleSheet("""
            QPushButton { 
                background-color: #e74c3c; 
                color: white; 
                border: none; 
                padding: 12px; 
                font-weight: bold;
                border-radius: 6px;
                font-size: 14px;
                min-height: 45px;
                margin: 5px;
            }
            QPushButton:hover { 
                background-color: #c0392b; 
            }
            QPushButton:pressed { 
                background-color: #a93226; 
            }
            QPushButton:checked { 
                background-color: #27ae60; 
                border: 2px solid #1e7e34;
            }
            QPushButton:checked:hover { 
                background-color: #218838; 
            }
        """)
        
        # Connect scissors button
        scissors_button.connect('toggled(bool)', lambda checked: toggle_scissors_tool_programmatic(checked))
        layout.addWidget(scissors_button)
        
        # Store button reference
        slicer.modules.LeftPanelScissorsButton = scissors_button
        
        # Add separator
        separator = qt.QFrame()
        separator.setFrameShape(qt.QFrame.HLine)
        separator.setFrameShadow(qt.QFrame.Sunken)
        layout.addWidget(separator)
        
        # Add markup placement section
        markup_label = qt.QLabel("Additional Markup Placement")
        markup_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #34495e;
                padding: 5px;
                margin-top: 10px;
            }
        """)
        layout.addWidget(markup_label)
        
        # Add fiducial point placement button
        fiducial_button = qt.QPushButton("Place Additional Fiducial Points")
        fiducial_button.setStyleSheet("""
            QPushButton { 
                background-color: #3498db; 
                color: white; 
                border: none; 
                padding: 10px; 
                font-weight: bold;
                border-radius: 6px;
                font-size: 12px;
                min-height: 40px;
                margin: 5px;
            }
            QPushButton:hover { 
                background-color: #2980b9; 
            }
            QPushButton:pressed { 
                background-color: #1f4e79; 
            }
        """)
        
        fiducial_button.connect('clicked()', lambda: create_additional_fiducial_list())
        layout.addWidget(fiducial_button)
        
        # Add curve placement button
        curve_button = qt.QPushButton("Place Additional Curves")
        curve_button.setStyleSheet("""
            QPushButton { 
                background-color: #9b59b6; 
                color: white; 
                border: none; 
                padding: 10px; 
                font-weight: bold;
                border-radius: 6px;
                font-size: 12px;
                min-height: 40px;
                margin: 5px;
            }
            QPushButton:hover { 
                background-color: #8e44ad; 
            }
            QPushButton:pressed { 
                background-color: #6a1b9a; 
            }
        """)
        
        curve_button.connect('clicked()', lambda: create_additional_curve_markup())
        layout.addWidget(curve_button)
        
        # Add continue workflow button
        continue_button = qt.QPushButton("Continue to Centerline Extraction")
        continue_button.setStyleSheet("""
            QPushButton { 
                background-color: #27ae60; 
                color: white; 
                border: 2px solid #1e7e34; 
                padding: 15px; 
                font-weight: bold;
                border-radius: 8px;
                font-size: 14px;
                min-height: 50px;
                margin: 10px 5px;
            }
            QPushButton:hover { 
                background-color: #218838; 
            }
            QPushButton:pressed { 
                background-color: #1e7e34; 
            }
        """)
        
        continue_button.connect('clicked()', lambda: continue_to_centerline_from_left_panel())
        layout.addWidget(continue_button)
        
        # Add stretch to push everything to top
        layout.addStretch()
        
        # Show the widget as a floating window on the left
        tools_widget.setWindowFlags(qt.Qt.Tool | qt.Qt.WindowStaysOnTopHint)
        tools_widget.show()
        
        # Position on the left side of screen
        screen_geometry = qt.QApplication.desktop().screenGeometry()
        tools_widget.move(50, 100)
        
        # Store reference to widget
        slicer.modules.PostThresholdToolsWidget = tools_widget
        
    except Exception as e:
        pass

def create_additional_fiducial_list():
    """
    Create a new fiducial list for additional markup placement
    """
    try:
        # Create a new fiducial list
        fiducial_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        fiducial_node.SetName(f"AdditionalMarkups_{slicer.mrmlScene.GetUniqueNameByString('Fiducial')}")
        
        # Configure the fiducial list
        fiducial_node.GetDisplayNode().SetTextScale(2.0)
        fiducial_node.GetDisplayNode().SetGlyphScale(3.0)
        fiducial_node.GetDisplayNode().SetSelectedColor(0.0, 1.0, 0.0)  # Green
        
        # Activate placement mode
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            selectionNode.SetActivePlaceNodeID(fiducial_node.GetID())
        
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
        
        slicer.util.infoDisplay(f"Additional fiducial placement activated.\nClick in 3D or slice views to place points.")
        
        return fiducial_node
        
    except Exception as e:
        pass
        return None

def create_additional_curve_markup():
    """
    Create a new curve markup for additional curve placement
    """
    try:
        # Create a new curve markup
        curve_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode")
        curve_node.SetName(f"AdditionalCurve_{slicer.mrmlScene.GetUniqueNameByString('Curve')}")
        
        # Configure the curve
        curve_node.GetDisplayNode().SetTextScale(2.0)
        curve_node.GetDisplayNode().SetLineThickness(3.0)
        curve_node.GetDisplayNode().SetSelectedColor(1.0, 0.5, 0.0)  # Orange
        
        # Activate placement mode
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsCurveNode")
            selectionNode.SetActivePlaceNodeID(curve_node.GetID())
        
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
        
        slicer.util.infoDisplay(f"Additional curve placement activated.\nClick in 3D or slice views to place curve points.")
        
        return curve_node
        
    except Exception as e:
        pass
        return None

def continue_to_centerline_from_left_panel():
    """
    Continue to centerline extraction from the left panel tools
    """
    try:
        # Clean up the left panel tools
        cleanup_post_threshold_tools()
        
        # Continue with the normal workflow path
        slicer.util.infoDisplay("Proceeding to centerline extraction.\n\nNext: Extract Centerline module will open.")
        
        # Set up for centerline extraction
        qt.QTimer.singleShot(1000, lambda: on_continue_from_scissors())
        
    except Exception as e:
        pass

def cleanup_post_threshold_tools():
    """
    Clean up the post-threshold tools widget
    """
    try:
        if hasattr(slicer.modules, 'PostThresholdToolsWidget'):
            slicer.modules.PostThresholdToolsWidget.deleteLater()
            del slicer.modules.PostThresholdToolsWidget
        
        if hasattr(slicer.modules, 'LeftPanelScissorsButton'):
            del slicer.modules.LeftPanelScissorsButton
            
    except Exception as e:
        pass

def create_threshold_segment():
    """
    Main workflow function to create a threshold segment with default values or import existing segmentation
    """
    volume_node = find_working_volume()
    
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    
    # Initialize workflow flags
    slicer.modules.WorkflowUsingMarkup = False
    slicer.modules.WorkflowUsingImportedSegmentation = False
    
    # Check if this is being called from an alternate path (prevent dialog loops)
    calling_from_crop = hasattr(slicer.modules, 'WorkflowDialogShown') and slicer.modules.WorkflowDialogShown
    
    # First ask if user wants to import an existing segmentation (alternate workflow)
    want_segmentation = ask_user_for_segmentation_import()
    
    if want_segmentation:
        # User wants to import existing segmentation - alternate workflow
        segmentation_node = import_segmentation_file()
        if segmentation_node:
            slicer.util.infoDisplay("Segmentation imported successfully. Proceeding directly to centerline extraction.")
            
            # Show segmentation in 3D
            show_segmentation_in_3d(segmentation_node)
            
            # Skip threshold creation and go directly to centerline extraction
            start_imported_segmentation_workflow(segmentation_node, volume_node)
            return
        else:
            # Segmentation import failed, continue with normal workflow
            slicer.util.infoDisplay("Segmentation import cancelled or failed. Continuing with normal workflow.")
    
    # Ask user if they want to import markup
    want_markup = ask_user_for_markup_import()
    
    if want_markup:
        # User wants to import markup - handle all imports from source folder
        markup_success = import_markup_file()
        if markup_success:
            # Store markup workflow flag for later use
            slicer.modules.WorkflowUsingMarkup = True
            
            slicer.util.infoDisplay("Markup workflow imports completed. Tube masks created automatically.")
        else:
            # Markup import failed, continue with normal workflow
            slicer.util.infoDisplay("Markup import cancelled or failed. Continuing with normal workflow.")
            slicer.modules.WorkflowUsingMarkup = False
    
    # If neither segmentation nor markup is imported, continue with normal threshold workflow
    # But if user cancelled both and we were called from crop workflow, go to crop workflow
    if (not want_segmentation and not want_markup) and calling_from_crop:
        # Reset the flag and continue with crop workflow
        slicer.modules.WorkflowDialogShown = False
        start_crop_workflow_directly()
        return
    
    # Continue with normal threshold workflow
    threshold_values = prompt_for_threshold_range()
    if threshold_values is None:
        return
    
    threshold_value_low, threshold_value_high = threshold_values
    
    segmentation_node = create_segmentation_from_threshold(volume_node, threshold_value_low, threshold_value_high)
    
    if segmentation_node:
        show_segmentation_in_3d(segmentation_node)
        load_into_segment_editor(segmentation_node, volume_node)

def prompt_for_threshold_range():
    """
    Show a single dialog to get both threshold values from user
    """
    try:
        dialog = qt.QDialog(slicer.util.mainWindow())
        dialog.setWindowTitle("Threshold Segmentation")
        dialog.setModal(True)
        dialog.resize(350, 200)
        
        layout = qt.QVBoxLayout(dialog)
        title_label = qt.QLabel("Set Threshold Range")
        title_label.setStyleSheet("QLabel { font-weight: bold; font-size: 14px; margin: 10px; }")
        layout.addWidget(title_label)
        
        lower_layout = qt.QHBoxLayout()
        lower_label = qt.QLabel("Lower threshold:")
        lower_label.setMinimumWidth(100)
        lower_spinbox = qt.QDoubleSpinBox()
        lower_spinbox.setRange(-1024.0, 3071.0)
        lower_spinbox.setValue(290.0)
        lower_spinbox.setDecimals(2)
        lower_layout.addWidget(lower_label)
        lower_layout.addWidget(lower_spinbox)
        layout.addLayout(lower_layout)
        
        upper_layout = qt.QHBoxLayout()
        upper_label = qt.QLabel("Upper threshold:")
        upper_label.setMinimumWidth(100)
        upper_spinbox = qt.QDoubleSpinBox()
        upper_spinbox.setRange(-1024.0, 3071.0)
        upper_spinbox.setValue(3071.0)
        upper_spinbox.setDecimals(2)
        upper_layout.addWidget(upper_label)
        upper_layout.addWidget(upper_spinbox)
        layout.addLayout(upper_layout)
        
        info_label = qt.QLabel("Range: -1024 to 3071 Hounsfield units")
        info_label.setStyleSheet("QLabel { color: #333; font-size: 11px; margin: 5px; }")
        layout.addWidget(info_label)
        
        button_layout = qt.QHBoxLayout()
        ok_button = qt.QPushButton("OK")
        cancel_button = qt.QPushButton("Cancel")
        
        ok_button.connect('clicked()', dialog.accept)
        cancel_button.connect('clicked()', dialog.reject)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)
        
        if dialog.exec_() == qt.QDialog.Accepted:
            return (lower_spinbox.value, upper_spinbox.value)
        else:
            return None
            
    except Exception as e:
        return (290.0, 3071.0)

def create_segmentation_from_threshold(volume_node, threshold_value_low, threshold_value_high=None):
    """
    Apply threshold to existing Segment_1
    """
    segmentation_node = None
    segmentation_nodes = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
    
    for seg_node in segmentation_nodes:
        segmentation = seg_node.GetSegmentation()
        segment_ids = vtk.vtkStringArray()
        segmentation.GetSegmentIDs(segment_ids)
        for i in range(segment_ids.GetNumberOfValues()):
            segment_id = segment_ids.GetValue(i)
            segment = segmentation.GetSegment(segment_id)
            if segment and segment.GetName() == "Segment_1":
                segmentation_node = seg_node
                break
        
        if segmentation_node:
            break
    
    if not segmentation_node:
        segmentation_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        segmentation_node.SetName(f"ThresholdSegmentation_{threshold_value_low}_{threshold_value_high}")
        segmentation_node.CreateDefaultDisplayNodes()
        segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(volume_node)
        segmentation = segmentation_node.GetSegmentation()
        segment_id = segmentation.AddEmptySegment("Segment_1")
    else:
        segmentation = segmentation_node.GetSegmentation()
        segment_ids = vtk.vtkStringArray()
        segmentation.GetSegmentIDs(segment_ids)
        
        segment_id = None
        for i in range(segment_ids.GetNumberOfValues()):
            test_segment_id = segment_ids.GetValue(i)
            segment = segmentation.GetSegment(test_segment_id)
            if segment and segment.GetName() == "Segment_1":
                segment_id = test_segment_id
                break
        
        pass
    segmentation_node.SetAttribute("WorkflowCreatedSegmentID", segment_id)
    
    segment = segmentation.GetSegment(segment_id)
    if not segment:
        return segmentation_node
    try:
        volume_array = slicer.util.arrayFromVolume(volume_node)
        if threshold_value_high is not None:
            binary_mask = (volume_array >= threshold_value_low) & (volume_array <= threshold_value_high)
        else:
            binary_mask = volume_array >= threshold_value_low
        
        temp_labelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        temp_labelmap.SetName("TempThresholdLabelmap")
        slicer.util.updateVolumeFromArray(temp_labelmap, binary_mask.astype('uint8'))
        temp_labelmap.CopyOrientation(volume_node)
        segment.GetRepresentation(slicer.vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName()).Initialize()
        segmentationLogic = slicer.modules.segmentations.logic()
        if segmentationLogic.ImportLabelmapToSegmentationNode(temp_labelmap, segmentation_node):
            pass
        else:
            pass
        slicer.mrmlScene.RemoveNode(temp_labelmap)
    except Exception as e:
        pass
    set_3d_view_background_black()
    
    return segmentation_node

def show_segmentation_in_3d(segmentation_node):
    """
    Display the segmentation as a 3D volume rendering
    """
    layout_manager = slicer.app.layoutManager()
    display_node = segmentation_node.GetDisplayNode()
    if display_node:
        display_node.SetVisibility3D(True)
        display_node.SetOpacity3D(0.7)
        # Set 2D display properties
        display_node.SetVisibility2DFill(True)
        display_node.SetVisibility2DOutline(True)
        
        segmentation = segmentation_node.GetSegmentation()
        segment_ids = vtk.vtkStringArray()
        segmentation.GetSegmentIDs(segment_ids)
        
        if segment_ids.GetNumberOfValues() > 0:
            segment_id = segment_ids.GetValue(0)
            segment = segmentation.GetSegment(segment_id)
            # Set segment color to white (1.0, 1.0, 1.0)
            segment.SetColor(1.0, 1.0, 1.0) 
            segment.SetTag("Segmentation.Status", "inprogress")
    segmentation_node.CreateClosedSurfaceRepresentation()
    threeDWidget = layout_manager.threeDWidget(0)
    if threeDWidget:
        threeDView = threeDWidget.threeDView()
        if threeDView:
            view_node = threeDView.mrmlViewNode()
            if view_node:
                view_node.SetBoxVisible(True)
                view_node.SetAxisLabelsVisible(True)
            threeDView.resetFocalPoint()
            threeDView.forceRender()
            threeDWidget.show()
    slicer.app.processEvents()
    if threeDWidget and threeDView:
        threeDView.forceRender()

def load_into_segment_editor(segmentation_node, volume_node):
    """
    Load the segmentation using programmatic API instead of opening GUI
    """
    try:
        
        # Remove any existing segment from all segmentations if needed
        remove_segment_from_all_segmentations("Segment_1")
        
        # Use the new programmatic approach
        success = start_with_segment_editor_scissors()
        
        if not success:
            return False
        
        # If a specific segmentation was provided, use it
        if segmentation_node and hasattr(slicer.modules, 'WorkflowSegmentationNode'):
            # Replace the default segmentation with the provided one
            slicer.modules.WorkflowSegmentationNode = segmentation_node
            
            # Update the segment editor node
            if hasattr(slicer.modules, 'WorkflowSegmentEditorNode'):
                segmentEditorNode = slicer.modules.WorkflowSegmentEditorNode
                segmentEditorNode.SetAndObserveSegmentationNode(segmentation_node)
                segmentEditorNode.SetAndObserveSourceVolumeNode(volume_node)
                
                # Select the first segment
                segmentation = segmentation_node.GetSegmentation()
                segment_ids = vtk.vtkStringArray()
                segmentation.GetSegmentIDs(segment_ids)
                if segment_ids.GetNumberOfValues() > 0:
                    segment_id = segment_ids.GetValue(0)
                    segmentEditorNode.SetSelectedSegmentID(segment_id)
        
        # Enable segmentation visibility
        if segmentation_node:
            display_node = segmentation_node.GetDisplayNode()
            if display_node:
                display_node.SetAllSegmentsVisibility(True)
                display_node.SetVisibility2DOutline(True)
                display_node.SetVisibility2DFill(True)
                
                # Ensure all segments are white
                segmentation = segmentation_node.GetSegmentation()
                segment_ids = vtk.vtkStringArray()
                segmentation.GetSegmentIDs(segment_ids)
                for i in range(segment_ids.GetNumberOfValues()):
                    segment_id = segment_ids.GetValue(i)
                    segment = segmentation.GetSegment(segment_id)
                    if segment:
                        segment.SetColor(1.0, 1.0, 1.0)  # Set to white
        
        # Force refresh slice views
        layout_manager = slicer.app.layoutManager()
        for sliceViewName in ['Red', 'Yellow', 'Green']:
            slice_widget = layout_manager.sliceWidget(sliceViewName)
            if slice_widget:
                slice_view = slice_widget.sliceView()
                slice_view.forceRender()
        
        return True
        
    except Exception as e:
        return False

def select_scissors_tool(segment_editor_widget=None):
    """
    Select the Scissors tool programmatically (no GUI needed)
    """
    try:
        # Use the workflow's programmatic segment editor if available
        if hasattr(slicer.modules, 'WorkflowSegmentEditorWidget'):
            segmentEditorWidget = slicer.modules.WorkflowSegmentEditorWidget
            
            # Activate scissors effect
            segmentEditorWidget.setActiveEffectByName("Scissors")
            effect = segmentEditorWidget.activeEffect()
            
            if effect:
                # Configure scissors tool for workflow use - set to ERASE/SUBTRACT mode
                if hasattr(effect, 'setParameter'):
                    effect.setParameter("Operation", "EraseInside")  # Erase inside (subtract/cut)
                
                # Enable slice view interactions for scissors
                interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
                if interactionNode:
                    interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
                
                # Set the scissors button to active state if it exists
                if hasattr(slicer.modules, 'WorkflowScissorsButton'):
                    button = slicer.modules.WorkflowScissorsButton
                    button.setChecked(True)
                    slicer.modules.WorkflowScissorsActive = True
                
                return True
            else:
                return False
        else:
            return False
            
    except Exception as e:
        pass
        return False

def create_continue_workflow_button():
    """
    Create a continue button and add it to the Crop Volume module GUI
    """
    try:
        # Get the crop volume module widget
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if not crop_widget:
            create_floating_continue_button()
            return
        
        # Create continue button
        continue_button = qt.QPushButton("FINISH SEGMENTATION - CONTINUE")
        continue_button.setStyleSheet("""
            QPushButton { 
                background-color: #28a745; 
                color: white; 
                border: 2px solid #1e7e34; 
                padding: 18px; 
                font-weight: bold;
                border-radius: 8px;
                margin: 5px;
                font-size: 16px;
                min-height: 60px;
                min-width: 300px;
            }
            QPushButton:hover { 
                background-color: #218838; 
                border: 2px solid #155724;
                transform: scale(1.02);
            }
            QPushButton:pressed { 
                background-color: #1e7e34; 
                border: 2px solid #0f4c2c;
            }
        """)
        
        # Connect to continue function
        continue_button.connect('clicked()', lambda: on_continue_from_scissors())
        
        # Add status label
        status_label = qt.QLabel("Segmentation tools active. Use scissors button to edit segments.")
        status_label.setWordWrap(True)
        status_label.setStyleSheet("color: #333; font-size: 14px; padding: 10px; font-weight: bold;")
        
        # Create container for continue workflow elements
        continue_container = qt.QWidget()
        continue_layout = qt.QVBoxLayout(continue_container)
        continue_layout.addWidget(status_label)
        continue_layout.addWidget(continue_button)
        
        # Try to add to the crop module GUI
        success = add_continue_button_to_crop_module(crop_widget, continue_container)
        
        if success:
            # Store references
            slicer.modules.WorkflowContinueButton = continue_button
            slicer.modules.WorkflowContinueWidget = continue_container
            pass
        else:
            # Fallback to floating widget
            pass
            create_floating_continue_button()
        
    except Exception as e:
        pass
        # Fallback to floating widget
        create_floating_continue_button()

def create_floating_continue_button():
    """
    Create a floating continue button as fallback
    """
    try:
        # Create continue button
        continue_button = qt.QPushButton("FINISH SEGMENTATION - CONTINUE")
        continue_button.setStyleSheet("""
            QPushButton { 
                background-color: #28a745; 
                color: white; 
                border: none; 
                padding: 18px; 
                font-weight: bold;
                border-radius: 8px;
                margin: 15px;
                font-size: 16px;
                min-height: 60px;
                min-width: 300px;
            }
            QPushButton:hover { 
                background-color: #218838; 
                transform: scale(1.02);
            }
            QPushButton:pressed { 
                background-color: #1e7e34; 
            }
        """)
        
        # Connect to continue function
        continue_button.connect('clicked()', lambda: on_continue_from_scissors())
        
        # Create floating widget for continue button
        continue_widget = qt.QWidget()
        continue_widget.setWindowTitle("Workflow Progress")
        continue_widget.setWindowFlags(qt.Qt.WindowStaysOnTopHint | qt.Qt.Tool)
        
        # Set layout
        layout = qt.QVBoxLayout()
        
        # Add status label
        status_label = qt.QLabel("Segmentation tools active. Use scissors button to edit segments.")
        status_label.setWordWrap(True)
        status_label.setStyleSheet("color: #333; font-size: 14px; padding: 10px;")
        layout.addWidget(status_label)
        
        layout.addWidget(continue_button)
        continue_widget.setLayout(layout)
        continue_widget.resize(350, 150)
        
        # Position in bottom-right corner
        main_window = slicer.util.mainWindow()
        if main_window:
            main_geometry = main_window.geometry()
            continue_widget.move(main_geometry.right() - 370, main_geometry.bottom() - 200)
        
        continue_widget.show()
        
        # Store references
        slicer.modules.WorkflowContinueButton = continue_button
        slicer.modules.WorkflowContinueWidget = continue_widget
        
        pass
        
    except Exception as e:
        pass

def add_continue_button_to_crop_module(crop_widget, continue_container):
    """
    DISABLED: Do not add any buttons to the Crop Volume module GUI.
    All functionality is handled by the custom crop interface.
    """
    # Return immediately - no buttons should be added to crop module
    return False

def on_continue_from_scissors():
    """
    Called when user clicks the continue button after using scissors
    """
    pass
    cleanup_workflow_ui()
    
    # Set 3D view background to black
    set_3d_view_background_black()
    
    # Check if we're in markup workflow mode
    if hasattr(slicer.modules, 'WorkflowUsingMarkup') and slicer.modules.WorkflowUsingMarkup:
        # Open the Data module to show imported markup and created curve models
        open_data_module()
    else:
        # Normal workflow - proceed to centerline extraction
        open_centerline_module()

def on_finish_cropping():
    """
    Called when user clicks the finish cropping button after using scissors tool
    """
    try:
        pass
        
        # First collapse/hide the crop volume GUI completely
        collapse_crop_volume_gui()
        
        # Clean up scissors tool UI
        cleanup_scissors_tool_ui()
        
        # Continue to the next step in the workflow
        cleanup_workflow_ui()
        
        # Set 3D view background to black
        set_3d_view_background_black()
        
        # Check if we're in markup workflow mode
        if hasattr(slicer.modules, 'WorkflowUsingMarkup') and slicer.modules.WorkflowUsingMarkup:
            # Open the Data module to show imported markup and created curve models
            open_data_module()
        else:
            # Normal workflow - proceed to centerline extraction
            open_centerline_module()
        
        pass
        
    except Exception as e:
        pass

def collapse_crop_volume_gui():
    """
    Completely collapse/hide the Crop Volume module GUI when cropping is finished
    """
    try:
        pass
        
        # First try to hide all UI elements
        hide_crop_volume_ui_elements()
        
        # Additionally, try to collapse the entire module widget
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if crop_widget:
            # Try to find and collapse the main collapsible sections
            all_collapsible_buttons = crop_widget.findChildren("ctkCollapsibleButton")
            collapsed_count = 0
            
            for button in all_collapsible_buttons:
                try:
                    if hasattr(button, 'setCollapsed'):
                        button.setCollapsed(True)
                        collapsed_count += 1
                    elif hasattr(button, 'collapsed') and hasattr(button, 'setProperty'):
                        button.setProperty('collapsed', True)
                        collapsed_count += 1
                except Exception as e:
                    continue
            
            # Also try to minimize the main widget if possible
            try:
                if hasattr(crop_widget, 'setVisible'):
                    # Don't make completely invisible, but minimize visibility
                    crop_widget.setMaximumHeight(50)  # Minimize height
                    pass
            except Exception as e:
                pass
            
            pass
            
        # Force GUI update
        slicer.app.processEvents()
        
        pass
        
    except Exception as e:
        pass

def cleanup_continue_ui():
    """
    Clean up continue button UI elements
    """
    try:
        # Clean up old segment editor button if it exists
        if hasattr(slicer.modules, 'SegmentEditorContinueButton'):
            button = slicer.modules.SegmentEditorContinueButton
            if button.parent():
                button.parent().layout().removeWidget(button)
            button.setParent(None)
            del slicer.modules.SegmentEditorContinueButton
            pass
        
        # Clean up old dialog if it exists
        if hasattr(slicer.modules, 'SegmentEditorContinueDialog'):
            dialog = slicer.modules.SegmentEditorContinueDialog
            dialog.close()
            dialog.setParent(None)
            del slicer.modules.SegmentEditorContinueDialog
            pass
        
        # Clean up new workflow continue button
        if hasattr(slicer.modules, 'WorkflowContinueButton'):
            button = slicer.modules.WorkflowContinueButton
            button.setParent(None)
            del slicer.modules.WorkflowContinueButton
        
        # Clean up new workflow continue widget
        if hasattr(slicer.modules, 'WorkflowContinueWidget'):
            widget = slicer.modules.WorkflowContinueWidget
            widget.close()
            widget.setParent(None)
            del slicer.modules.WorkflowContinueWidget
            pass
            
        # Also clean up scissors tool UI
        cleanup_scissors_tool_ui()
            
    except Exception as e:
        pass
        pass

def create_analysis_masks(straightened_volumes):
    try:
        if not straightened_volumes:
            pass
            return
        
        straightened_volume = straightened_volumes[0]
        pass
        
        segmentation_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        segmentation_node.SetName("AnalysisMasks")
        segmentation_node.CreateDefaultDisplayNodes()
        segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(straightened_volume)
        
        display_node = segmentation_node.GetDisplayNode()
        if display_node:
            display_node.SetVisibility3D(False)
            display_node.SetVisibility(True)
        
        segmentation = segmentation_node.GetSegmentation()
        segment_id = segmentation.AddEmptySegment("st-analysis")
        segment = segmentation.GetSegment(segment_id)
        segment.SetColor(0.0, 1.0, 0.0)  # Bright green color
        
        mask_definitions = [
            ("LAP", -30, 30),
            ("NCP", 282, 590),
            ("STENOSIS", 600, 1200)
        ]
        
        volume_array = slicer.util.arrayFromVolume(straightened_volume)
        
        for mask_name, threshold_low, threshold_high in mask_definitions:
            pass
            
            binary_mask = (volume_array >= threshold_low) & (volume_array <= threshold_high)
            voxel_count = binary_mask.sum()
            pass
            
            temp_labelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
            temp_labelmap.SetName(f"TempLabelmap_{mask_name}")
            slicer.util.updateVolumeFromArray(temp_labelmap, binary_mask.astype('uint8'))
            temp_labelmap.CopyOrientation(straightened_volume)
            
            segmentationLogic = slicer.modules.segmentations.logic()
            if segmentationLogic.ImportLabelmapToSegmentationNode(temp_labelmap, segmentation_node):
                pass
            else:
                pass
            
            slicer.mrmlScene.RemoveNode(temp_labelmap)
        
        pass
        pass
        pass
        pass
        
        slicer.modules.WorkflowAnalysisSegmentation = segmentation_node
        slicer.modules.WorkflowAnalysisSegments = [segment_id]
        
        return segmentation_node
            
    except Exception as e:
        pass
        return None

def cleanup_workflow_ui():
    """
    Clean up workflow UI elements
    """
    try:
        if hasattr(slicer.modules, 'WorkflowDockWidget'):
            dock_widget = slicer.modules.WorkflowDockWidget
            dock_widget.close()
            dock_widget.setParent(None)
            del slicer.modules.WorkflowDockWidget
            pass
        if hasattr(slicer.modules, 'WorkflowDialog'):
            dialog = slicer.modules.WorkflowDialog
            dialog.close()
            dialog.setParent(None)
            del slicer.modules.WorkflowDialog
            pass
        cleanup_point_placement_ui()
        cleanup_centerline_ui()
            
    except Exception as e:
        pass

def open_centerline_module():
    """
    Open the Extract Centerline module
    """
    try:
        segmentation_nodes = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
        workflow_segmentation = None
        for seg_node in segmentation_nodes:
            if seg_node.GetName().startswith("ThresholdSegmentation_"):
                workflow_segmentation = seg_node
                break
        
        if workflow_segmentation:
            prepare_surface_for_centerline(workflow_segmentation)
        
        # Expand the left module panel for ExtractCenterline step
        expand_left_module_panel()
        
        slicer.util.selectModule("ExtractCenterline")
        pass
        slicer.app.processEvents()
        
        # Set up minimal UI with only inputs section
        setup_minimal_extract_centerline_ui()
        
        remove_duplicate_centerline_buttons()
        setup_centerline_module()
        
        # Allow module to fully initialize before forcing point placement
        slicer.app.processEvents()
        time.sleep(0.5)  # Give module time to complete initialization
        
        # Now force point placement tool selection after full initialization
        force_point_placement_tool_selection()
        
        # Additional verification and fixes
        verification_results = verify_extract_centerline_point_list_autoselection()
        if not verification_results["success"]:
            fix_extract_centerline_setup_issues()
            force_point_placement_tool_selection()  # Force again after fixes
            slicer.app.processEvents()
            time.sleep(0.2)
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not open Extract Centerline module: {str(e)}")

def remove_duplicate_centerline_buttons():
    """
    Depricate after bug fix - not yet
    """
    try:
        centerline_widget = slicer.modules.extractcenterline.widgetRepresentation()
        if centerline_widget:
            all_buttons = centerline_widget.findChildren(qt.QPushButton)
            duplicate_buttons = []
            
            for button in all_buttons:
                if hasattr(button, 'text'):
                    button_text = button.text
                    if ("EXTRACT CENTERLINE" in button_text or 
                        (button.styleSheet() and "#28a745" in button.styleSheet())):
                        duplicate_buttons.append(button)

            if len(duplicate_buttons) > 1:
                pass
                for i, button in enumerate(duplicate_buttons):
                    if i > 0:
                        if button.parent() and hasattr(button.parent(), 'layout'):
                            button.parent().layout().removeWidget(button)
                        button.setParent(None)
                        button.deleteLater()
                        pass
            elif len(duplicate_buttons) == 1:
                pass
            else:
                pass
                
    except Exception as e:
        pass

def add_large_centerline_apply_button():
    """
    Add a large green Apply button directly to the Extract Centerline module GUI
    """
    try:
        if hasattr(slicer.modules, 'CenterlineLargeApplyButton'):
            existing_button = slicer.modules.CenterlineLargeApplyButton
            if existing_button and existing_button.parent():
                pass
                return
        remove_duplicate_centerline_buttons()
        
        def create_large_button():
            try:
                if hasattr(slicer.modules, 'CenterlineLargeApplyButton'):
                    existing_button = slicer.modules.CenterlineLargeApplyButton
                    if existing_button and existing_button.parent():
                        pass
                        return True
                
                centerline_widget = slicer.modules.extractcenterline.widgetRepresentation()
                if centerline_widget and hasattr(centerline_widget, 'self'):
                    centerline_module = centerline_widget.self()
                    original_apply_button = None
                    if hasattr(centerline_module.ui, 'applyButton'):
                        original_apply_button = centerline_module.ui.applyButton
                    elif hasattr(centerline_module.ui, 'ApplyButton'):
                        original_apply_button = centerline_module.ui.ApplyButton
                    
                    if not original_apply_button:
                        all_buttons = centerline_widget.findChildren(qt.QPushButton)
                        for button in all_buttons:
                            button_text = button.text if hasattr(button, 'text') else ""
                            if 'apply' in button_text.lower():
                                original_apply_button = button
                                break
                    
                    if original_apply_button:
                        large_apply_button = qt.QPushButton("EXTRACT CENTERLINE")
                        large_apply_button.setStyleSheet("""
                            QPushButton { 
                                background-color: #28a745; 
                                color: white; 
                                border: 2px solid #1e7e34; 
                                padding: 20px; 
                                font-weight: bold;
                                border-radius: 10px;
                                margin: 10px;
                                font-size: 18px;
                                min-height: 70px;
                                min-width: 250px;
                            }
                            QPushButton:hover { 
                                background-color: #218838; 
                                border: 2px solid #155724;
                                transform: scale(1.05);
                            }
                            QPushButton:pressed { 
                                background-color: #1e7e34; 
                                border: 2px solid #0f4c2c;
                            }
                        """)
                        
                        def on_apply_button_clicked():
                            pass
                            # Stop any existing monitoring to prevent duplicates
                            stop_all_centerline_monitoring()
                            # Use apply button monitoring instead of centerline completion monitoring
                            # This provides more direct detection of when Apply is clicked
                            setup_apply_button_monitoring()
                            original_apply_button.click()
                        
                        large_apply_button.connect('clicked()', on_apply_button_clicked)
                        
                        main_ui_widget = None
                        
                        # Strategy 1: Look for the main widget container
                        if hasattr(centerline_module, 'ui') and hasattr(centerline_module.ui, 'widget'):
                            main_ui_widget = centerline_module.ui.widget
                        elif hasattr(centerline_module, 'widget'):
                            main_ui_widget = centerline_module.widget
                        elif hasattr(centerline_widget, 'widget'):
                            main_ui_widget = centerline_widget.widget
                        
                        # Strategy 2: Get the module widget representation directly
                        if not main_ui_widget:
                            main_ui_widget = centerline_widget
                        
                        # Add button to the main UI widget
                        if main_ui_widget and hasattr(main_ui_widget, 'layout'):
                            layout = main_ui_widget.layout()
                            if layout:
                                # Insert at the top of the module for maximum visibility
                                layout.insertWidget(0, large_apply_button)
                            else:
                                # Create a layout if none exists
                                new_layout = qt.QVBoxLayout(main_ui_widget)
                                new_layout.insertWidget(0, large_apply_button)
                        else:
                            container_widgets = centerline_widget.findChildren(qt.QWidget)
                            for widget in container_widgets:
                                if hasattr(widget, 'layout') and widget.layout() and widget.layout().count() > 0:
                                    widget.layout().insertWidget(0, large_apply_button)
                                    break
                            else:
                                return False
                        slicer.modules.CenterlineLargeApplyButton = large_apply_button
                        return True
                    else:
                        return False
                        
            except Exception as e:
                pass
                return False
        success = create_large_button()
        
        if not success and not hasattr(slicer.modules, 'CenterlineLargeApplyButton'):
            def delayed_create():
                if not hasattr(slicer.modules, 'CenterlineLargeApplyButton'):
                    create_large_button()
            qt.QTimer.singleShot(1000, delayed_create)
            qt.QTimer.singleShot(3000, delayed_create)
            
    except Exception as e:
        pass

def cleanup_centerline_ui():
    """
    Clean up centerline UI elements including duplicate buttons
    """
    try:
        remove_duplicate_centerline_buttons()
        
        if hasattr(slicer.modules, 'CenterlineLargeApplyButton'):
            button = slicer.modules.CenterlineLargeApplyButton
            if button and button.parent():
                if hasattr(button.parent(), 'layout'):
                    button.parent().layout().removeWidget(button)
                button.setParent(None)
                button.deleteLater()
            del slicer.modules.CenterlineLargeApplyButton
            pass
            
    except Exception as e:
        pass

def setup_centerline_module():
    """
    Set up the Extract Centerline module with the current segmentation
    """
    try:
        centerline_widget = slicer.modules.extractcenterline.widgetRepresentation()
        if centerline_widget:
            centerline_module = centerline_widget.self()

            segmentation_nodes = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
            if segmentation_nodes:
                workflow_segmentation = None
                for seg_node in segmentation_nodes:
                    if seg_node.GetName().startswith("ThresholdSegmentation_"):
                        workflow_segmentation = seg_node
                        break
                
                if workflow_segmentation:
                    pass
                    workflow_segmentation.CreateClosedSurfaceRepresentation()
                    segmentation_set = False
                    for selector_name in ['inputSegmentationSelector', 'inputSurfaceSelector', 'segmentationSelector']:
                        if hasattr(centerline_module, 'ui') and hasattr(centerline_module.ui, selector_name):
                            getattr(centerline_module.ui, selector_name).setCurrentNode(workflow_segmentation)
                            pass
                            segmentation_set = True
                            break

                    slicer.app.processEvents()
                    workflow_segment_id = workflow_segmentation.GetAttribute("WorkflowCreatedSegmentID")
                    if workflow_segment_id:
                        segmentation = workflow_segmentation.GetSegmentation()
                        segment = segmentation.GetSegment(workflow_segment_id)
                        if segment:
                            segment.SetTag("Segmentation.Status", "completed")
                            segment_set = False
                            for selector_name in ['inputSegmentSelector', 'segmentSelector', 'inputSurfaceSegmentSelector']:
                                if hasattr(centerline_module.ui, selector_name):
                                    try:
                                        getattr(centerline_module.ui, selector_name).setCurrentSegmentID(workflow_segment_id)
                                        segment_set = True
                                        break
                                    except Exception as e:
                                        pass

                    else:
                        segmentation = workflow_segmentation.GetSegmentation()
                        segment_ids = vtk.vtkStringArray()
                        segmentation.GetSegmentIDs(segment_ids)
                        if segment_ids.GetNumberOfValues() > 0:
                            first_segment_id = segment_ids.GetValue(0)
                            first_segment = segmentation.GetSegment(first_segment_id)
                            if first_segment:
                                first_segment.SetTag("Segmentation.Status", "completed")
                    
                    try:
                        endpoint_point_list = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
                        endpoint_point_list.SetName("CenterlineEndpoints")
                        
                        # Try to find and set the endpoint selector using the XML object name
                        endpoints_selector = None
                        extract_centerline_widget = slicer.modules.extractcenterline.widgetRepresentation()
                        if extract_centerline_widget:
                            # Use the exact object name from the XML
                            endpoints_selector = extract_centerline_widget.findChild(qt.QWidget, "endPointsMarkupsSelector")
                            if endpoints_selector and hasattr(endpoints_selector, 'setCurrentNode'):
                                endpoints_selector.setCurrentNode(endpoint_point_list)
                                endpoint_set = True
                        
                        # Fallback to old method if XML-based approach failed
                        if not endpoints_selector:
                            endpoint_set = False
                            for endpoint_selector_attr in ['inputEndPointsSelector', 'endpointsSelector', 'inputFiducialSelector']:
                                if hasattr(centerline_module.ui, endpoint_selector_attr):
                                    getattr(centerline_module.ui, endpoint_selector_attr).setCurrentNode(endpoint_point_list)
                                    endpoint_set = True
                                    break
                        
                        # FORCE point placement mode activation
                        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
                        if interactionNode:
                            # Force interaction mode to Place
                            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
                            interactionNode.SetPlaceModePersistence(1)  # Enable "place multiple control points"
                        
                        # Set this as the active node for point placement
                        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
                        if selectionNode:
                            selectionNode.SetActivePlaceNodeID(endpoint_point_list.GetID())
                        
                        # Force GUI updates to ensure the tool is visually selected
                        slicer.app.processEvents()
                        
                        # Try to configure the place widget
                        if extract_centerline_widget:
                            place_widget = extract_centerline_widget.findChild(qt.QWidget, "endPointsMarkupsPlaceWidget")
                            if place_widget:
                                if hasattr(place_widget, 'setCurrentNode'):
                                    place_widget.setCurrentNode(endpoint_point_list)
                                if hasattr(place_widget, 'setPlaceModeEnabled'):
                                    place_widget.setPlaceModeEnabled(True)
                        
                        for create_new_attr in ['createNewEndpointsCheckBox', 'createNewPointListCheckBox']:
                            if hasattr(centerline_module.ui, create_new_attr):
                                getattr(centerline_module.ui, create_new_attr).setChecked(True)
                                
                    except Exception as e:
                        pass
                    
                    try:
                        centerline_model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
                        centerline_model.SetName("CenterlineModel")
                        
                        model_set = False
                        for model_selector_attr in ['outputCenterlineModelSelector', 'centerlineModelSelector', 'outputModelSelector']:
                            if hasattr(centerline_module.ui, model_selector_attr):
                                getattr(centerline_module.ui, model_selector_attr).setCurrentNode(centerline_model)
                                pass
                                model_set = True
                                break
                        
                        if not model_set:
                            pass
                        
                        for create_new_model_attr in ['createNewModelCheckBox', 'createNewCenterlineModelCheckBox']:
                            if hasattr(centerline_module.ui, create_new_model_attr):
                                getattr(centerline_module.ui, create_new_model_attr).setChecked(True)
                    except Exception as e:
                        pass
                    try:
                        if hasattr(centerline_module.ui, 'outputTreeModelSelector'):
                            tree_model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
                            tree_model.SetName("CenterlineTree")
                            centerline_module.ui.outputTreeModelSelector.setCurrentNode(tree_model)

                        if hasattr(centerline_module.ui, 'outputTreeCurveSelector'):
                            tree_curve = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode")
                            tree_curve.SetName("CenterlineCurve")
                            centerline_module.ui.outputTreeCurveSelector.setCurrentNode(tree_curve)
                        
                        for tree_model_attr in ['treeModelSelector']:
                            if hasattr(centerline_module.ui, tree_model_attr):
                                tree_model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
                                tree_model.SetName("CenterlineTree")
                                getattr(centerline_module.ui, tree_model_attr).setCurrentNode(tree_model)
                        
                        for tree_curve_attr in ['outputCenterlineCurveSelector', 'centerlineCurveSelector', 'treeCurveSelector']:
                            if hasattr(centerline_module.ui, tree_curve_attr):
                                tree_curve = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode")
                                tree_curve.SetName("CenterlineCurve")
                                getattr(centerline_module.ui, tree_curve_attr).setCurrentNode(tree_curve)
                                
                    except Exception as e:
                        pass
                    
                    # Force GUI update and give time for widgets to initialize
                    slicer.app.processEvents()
                    time.sleep(0.2)
                    slicer.app.processEvents()
        add_large_centerline_apply_button()
        
        # Final verification and force point placement if needed
        slicer.app.processEvents()
        time.sleep(0.2)
        
        # Final point placement tool enforcement
        force_point_placement_tool_selection()
        
        prompt_for_endpoints()
        
    except Exception as e:
        pass

def force_point_placement_tool_selection():
    """
    Force the point placement tool to be selected in the Extract Centerline module.
    This ensures that "Place control points" is selected instead of "Draw line" or other tools.
    """
    try:
        # Get interaction and selection nodes
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        
        if not interactionNode or not selectionNode:
            return False
        
        # Find the endpoints node
        endpoints_node = None
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for node in fiducial_nodes:
            if "Endpoints" in node.GetName():
                endpoints_node = node
                break
        
        if not endpoints_node:
            return False
        
        # Set the active placement node FIRST
        selectionNode.SetActivePlaceNodeID(endpoints_node.GetID())
        selectionNode.SetActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        
        # Force interaction mode to Place
        interactionNode.SetCurrentInteractionMode(interactionNode.Place)
        # Enable place mode persistence (multiple points)
        interactionNode.SetPlaceModePersistence(1)
        
        # Force GUI update
        slicer.app.processEvents()
        
        # Additional step: Try to access the Extract Centerline widget and force the tool selection
        try:
            extract_centerline_widget = slicer.modules.extractcenterline.widgetRepresentation()
            if extract_centerline_widget:
                # Look for the endpoints place widget and activate it
                place_widget = extract_centerline_widget.findChild(qt.QWidget, "endPointsMarkupsPlaceWidget")
                if place_widget and hasattr(place_widget, 'setPlaceModeEnabled'):
                    place_widget.setPlaceModeEnabled(True)
                    place_widget.setCurrentNode(endpoints_node)
        except Exception as e:
            pass  # If this fails, the main interaction mode setting should still work
        
        # Final GUI update
        slicer.app.processEvents()
        
        return True
        
    except Exception as e:
        return False

def verify_extract_centerline_point_list_autoselection():
    """
    Verify that the Extract Centerline module has "Add multiple points" (SetPlaceModePersistence) properly enabled
    """
    try:
        verification_results = {
            "success": False,
            "interaction_mode_enabled": False,
            "place_mode_persistence": False,
            "active_node_set": False,
            "details": []
        }
        
        # Check interaction node settings
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            # Check if interaction mode is set to Place
            current_mode = interactionNode.GetCurrentInteractionMode()
            place_mode = interactionNode.Place
            if current_mode == place_mode:
                verification_results["interaction_mode_enabled"] = True
                verification_results["details"].append("✓ Interaction mode set to Place")
            else:
                verification_results["details"].append(f"✗ Interaction mode is {current_mode}, expected {place_mode}")
            
            # Check if place mode persistence is enabled (this is the "Add multiple points" setting)
            place_persistence = interactionNode.GetPlaceModePersistence()
            if place_persistence == 1:
                verification_results["place_mode_persistence"] = True
                verification_results["details"].append("✓ Place mode persistence enabled (Add multiple points)")
            else:
                verification_results["details"].append(f"✗ Place mode persistence is {place_persistence}, expected 1")
        else:
            verification_results["details"].append("✗ Could not find interaction node")
        
        # Check if active node is set for point placement
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            active_node_id = selectionNode.GetActivePlaceNodeID()
            if active_node_id:
                active_node = slicer.mrmlScene.GetNodeByID(active_node_id)
                if active_node and "Endpoints" in active_node.GetName():
                    verification_results["active_node_set"] = True
                    verification_results["details"].append(f"✓ Active place node set: {active_node.GetName()}")
                else:
                    verification_results["details"].append(f"✗ Active place node set but not endpoints node: {active_node.GetName() if active_node else 'Unknown'}")
            else:
                verification_results["details"].append("✗ No active place node set")
        else:
            verification_results["details"].append("✗ Could not find selection node")
        
        # Overall success check
        verification_results["success"] = (
            verification_results["interaction_mode_enabled"] and 
            verification_results["place_mode_persistence"] and 
            verification_results["active_node_set"]
        )

        return verification_results
        
    except Exception as e:
        pass
        return {
            "success": False,
            "interaction_mode_enabled": False,
            "place_mode_persistence": False,
            "active_node_set": False,
            "details": [f"Error during verification: {str(e)}"]
        }

def fix_extract_centerline_setup_issues():
    """
    Fix common issues with Extract Centerline setup to ensure "Add multiple points" is properly enabled
    """
    try:
        fixes_applied = []
        
        # Fix interaction node settings
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            # Ensure interaction mode is set to Place
            current_mode = interactionNode.GetCurrentInteractionMode()
            if current_mode != interactionNode.Place:
                interactionNode.SetCurrentInteractionMode(interactionNode.Place)
                fixes_applied.append("Set interaction mode to Place")
            
            # Ensure place mode persistence is enabled (Add multiple points)
            if interactionNode.GetPlaceModePersistence() != 1:
                interactionNode.SetPlaceModePersistence(1)
                fixes_applied.append("Enabled place mode persistence (Add multiple points)")
        
        # Fix active node setting
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            active_node_id = selectionNode.GetActivePlaceNodeID()
            if not active_node_id:
                # Try to find the endpoints node and set it as active
                fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
                for node in fiducial_nodes:
                    if "Endpoints" in node.GetName():
                        selectionNode.SetActivePlaceNodeID(node.GetID())
                        fixes_applied.append(f"Set active place node to {node.GetName()}")
                        break
        
        # Force GUI updates to ensure changes take effect
        slicer.app.processEvents()
        
        # Also force point placement tool selection
        force_point_placement_tool_selection()
                        
    except Exception as e:
        pass

def prepare_surface_for_centerline(segmentation_node):
    """
    Prepare the segmentation surface for optimal centerline extraction
    """
    try:
        segmentation_node.CreateClosedSurfaceRepresentation()
        segmentation = segmentation_node.GetSegmentation()
        segment_ids = vtk.vtkStringArray()
        segmentation.GetSegmentIDs(segment_ids)
        for i in range(segment_ids.GetNumberOfValues()):
            segment_id = segment_ids.GetValue(i)
            segment = segmentation.GetSegment(segment_id)
            if segment:
                segment.SetTag("Segmentation.Status", "completed")
                closed_surface_rep_name = slicer.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName()
                if not segment.HasRepresentation(closed_surface_rep_name):
                    segmentation_node.CreateClosedSurfaceRepresentation()
        segmentation_node.Modified()
        return True
        
    except Exception as e:
        return False

def remove_segment_from_all_segmentations(segment_name):
    """
    Remove a segment by name from all segmentation nodes in the scene
    """
    try:
        segmentation_nodes = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
        removed_count = 0
        
        for seg_node in segmentation_nodes:
            segmentation = seg_node.GetSegmentation()
            segment_ids = vtk.vtkStringArray()
            segmentation.GetSegmentIDs(segment_ids)
            
            for i in range(segment_ids.GetNumberOfValues()):
                segment_id = segment_ids.GetValue(i)
                segment = segmentation.GetSegment(segment_id)
                if segment and segment.GetName() == segment_name:
                    segmentation.RemoveSegment(segment_id)
                    removed_count += 1
                    break 
            
    except Exception as e:
        pass


def add_large_crop_apply_button():
    """
    DISABLED: Do not add any buttons to the Crop Volume module GUI.
    All cropping functionality is handled by the custom crop interface.
    """
    # Return immediately - no buttons should be added to crop module
    return True

def add_large_cpr_apply_button():
    """
    Add a large green Apply button directly to the Curved Planar Reformat module GUI
    """
    hide_centerlines_from_views()
    hide_cpr_slice_size_controls()
    show_red_green_views_only()

    try:
        if hasattr(slicer.modules, 'CPRLargeApplyButton'):
            existing_button = slicer.modules.CPRLargeApplyButton
            if existing_button and existing_button.parent():
                pass
                return
        
        def create_large_button():
            try:
                if hasattr(slicer.modules, 'CPRLargeApplyButton'):
                    existing_button = slicer.modules.CPRLargeApplyButton
                    if existing_button and existing_button.parent():
                        return True

                cpr_widget = slicer.modules.curvedplanarreformat.widgetRepresentation()
                
                if cpr_widget:
                    cpr_module = None
                    if hasattr(cpr_widget, 'self'):
                        try:
                            cpr_module = cpr_widget.self()
                        except Exception as e:
                            pass
                    
                    if not cpr_module:
                        try:
                            cpr_module = cpr_widget
                            pass
                        except Exception as e:
                            pass

                    if not cpr_module:
                        try:
                            cpr_module = slicer.modules.curvedplanarreformat.createNewWidgetRepresentation()
                            pass
                        except Exception as e:
                            pass
                    
                    if cpr_module:
                        pass
                        
                        original_apply_button = None
                        pass
                        
                        apply_button_attrs = ['applyButton', 'ApplyButton', 'applyCPRButton', 'cprApplyButton']

                        if hasattr(cpr_module, 'ui'):
                            for attr_name in apply_button_attrs:
                                if hasattr(cpr_module.ui, attr_name):
                                    original_apply_button = getattr(cpr_module.ui, attr_name)
                                    pass
                                    break
                        else:

                            for attr_name in apply_button_attrs:
                                if hasattr(cpr_module, attr_name):
                                    original_apply_button = getattr(cpr_module, attr_name)
                                    pass
                                    break
                        
                        if not original_apply_button:
                            pass
                            all_buttons = cpr_widget.findChildren(qt.QPushButton)
                            pass
                            for i, button in enumerate(all_buttons):
                                button_text = button.text if hasattr(button, 'text') else ""
                                pass
                                if button_text and 'apply' in button_text.lower():
                                    original_apply_button = button
                                    pass
                                    break
                        
                        if original_apply_button:
                            large_apply_button = qt.QPushButton("Apply Curved Planar Reformat")
                            large_apply_button.setStyleSheet("""
                                QPushButton { 
                                    background-color: #28a745; 
                                    color: white; 
                                    border: 2px solid #1e7e34; 
                                    padding: 20px; 
                                    font-weight: bold;
                                    border-radius: 10px;
                                    margin: 10px;
                                    font-size: 18px;
                                    min-height: 70px;
                                    min-width: 200px;
                                }
                                QPushButton:hover { 
                                    background-color: #218838; 
                                    border: 2px solid #155724;
                                    transform: scale(1.05);
                                }
                                QPushButton:pressed { 
                                    background-color: #1e7e34; 
                                    border: 2px solid #0f4c2c;
                                }
                            """)
                            
                            def apply_cpr_and_transform():
                                """
                                Apply CPR only - transform application moved to Cross-Section Analysis button
                                """
                                try:
                                    
                                    # Apply the original CPR
                                    original_apply_button.click()
                                    
                                    # Give time for CPR processing
                                    slicer.app.processEvents()
                                    import time
                                    time.sleep(1.0)

                                    slicer.app.processEvents()
                                    
                                except Exception as e:
                                    pass
                            
                            large_apply_button.connect('clicked()', apply_cpr_and_transform)
                            
                            # Create Cross-Section Analysis button
                            cross_section_button = qt.QPushButton("OPEN CROSS-SECTION ANALYSIS")
                            cross_section_button.setStyleSheet("""
                                QPushButton { 
                                    background-color: #28a745; 
                                    color: white; 
                                    border: 2px solid #1e7e34; 
                                    padding: 20px; 
                                    font-weight: bold;
                                    border-radius: 10px;
                                    margin: 10px;
                                    font-size: 18px;
                                    min-height: 70px;
                                    min-width: 300px;
                                }
                                QPushButton:hover { 
                                    background-color: #218838; 
                                    border: 2px solid #155724;
                                    transform: scale(1.05);
                                }
                                QPushButton:pressed { 
                                    background-color: #1e7e34; 
                                    border: 2px solid #0f4c2c;
                                }
                            """)
                            
                            def open_cross_section_analysis():
                                try:
                                    # Apply transform to centerline nodes before opening Cross-Section Analysis
                                    transform_result = apply_cpr_transform_to_centerlines()
                                    
                                    # Switch to Cross-Section Analysis module
                                    slicer.util.selectModule("CrossSectionAnalysis")
                                    
                                    # Configure the Cross-Section Analysis module
                                    setup_cross_section_analysis_module()
                                    
                                    pass
                                except Exception as e:
                                    # Try alternative module names if the first doesn't work
                                    try:
                                        slicer.util.selectModule("Cross-sectionanalysis")
                                        setup_cross_section_analysis_module()
                                        pass
                                    except Exception as e2:
                                        try:
                                            slicer.util.selectModule("CrossSection")
                                            setup_cross_section_analysis_module()
                                            pass
                                        except Exception as e3:
                                            pass

                            cross_section_button.connect('clicked()', open_cross_section_analysis)
                            
                        else:
                            pass
                            large_apply_button = qt.QPushButton("Apply Curved Planar Reformat")
                            large_apply_button.setStyleSheet("""
                                QPushButton { 
                                    background-color: #28a745; 
                                    color: white; 
                                    border: 2px solid #1e7e34; 
                                    padding: 20px; 
                                    font-weight: bold;
                                    border-radius: 10px;
                                    margin: 10px;
                                    font-size: 18px;
                                    min-height: 70px;
                                    min-width: 200px;
                                }
                                QPushButton:hover { 
                                    background-color: #218838; 
                                    border: 2px solid #155724;
                                    transform: scale(1.05);
                                }
                                QPushButton:pressed { 
                                    background-color: #1e7e34; 
                                    border: 2px solid #0f4c2c;
                                }
                            """)

                            def trigger_cpr_apply():
                                try:
                                    # Apply CPR using fallback method
                                    if hasattr(cpr_module, 'onApplyButton'):
                                        cpr_module.onApplyButton()
                                        pass
                                    elif hasattr(cpr_module, 'apply'):
                                        cpr_module.apply()
                                        pass
                                    else:
                                        pass
                                    
                                    # Give time for CPR processing
                                    slicer.app.processEvents()
                                    import time
                                    time.sleep(1.0)
                                    
                                    pass
                                    
                                except Exception as e:
                                    pass
                            
                            large_apply_button.connect('clicked()', trigger_cpr_apply)
                            
                            # Create Cross-Section Analysis button
                            cross_section_button = qt.QPushButton("OPEN CROSS-SECTION ANALYSIS")
                            cross_section_button.setStyleSheet("""
                                QPushButton { 
                                    background-color: #28a745; 
                                    color: white; 
                                    border: 2px solid #1e7e34; 
                                    padding: 20px; 
                                    font-weight: bold;
                                    border-radius: 10px;
                                    margin: 10px;
                                    font-size: 18px;
                                    min-height: 70px;
                                    min-width: 300px;
                                }
                                QPushButton:hover { 
                                    background-color: #218838; 
                                    border: 2px solid #155724;
                                    transform: scale(1.05);
                                }
                                QPushButton:pressed { 
                                    background-color: #1e7e34; 
                                    border: 2px solid #0f4c2c;
                                }
                            """)
                            
                            def open_cross_section_analysis():
                                try:
                                    # Apply transform to centerline nodes before opening Cross-Section Analysis
                                    transform_result = apply_cpr_transform_to_centerlines()                                    
                                    # Switch to Cross-Section Analysis module
                                    slicer.util.selectModule("CrossSectionAnalysis")
                                    
                                    # Configure the Cross-Section Analysis module
                                    setup_cross_section_analysis_module()
                                    
                                    pass
                                except Exception as e:
                                    try:
                                        slicer.util.selectModule("Cross-sectionanalysis")
                                        setup_cross_section_analysis_module()
                                        pass
                                    except Exception as e2:
                                        
                                        try:
                                            slicer.util.selectModule("CrossSection")
                                            setup_cross_section_analysis_module()
                                            pass
                                        except Exception as e3:
                                            pass

                            cross_section_button.connect('clicked()', open_cross_section_analysis)
                        
                        main_ui_widget = None
                        
                        if hasattr(cpr_module, 'ui') and hasattr(cpr_module.ui, 'widget'):
                            main_ui_widget = cpr_module.ui.widget
                        elif hasattr(cpr_module, 'widget'):
                            main_ui_widget = cpr_module.widget
                        elif hasattr(cpr_widget, 'widget'):
                            main_ui_widget = cpr_widget.widget
                        
                        if not main_ui_widget:
                            main_ui_widget = cpr_widget

                        # Create a container widget for both buttons
                        button_container = qt.QWidget()
                        button_layout = qt.QVBoxLayout(button_container)
                        button_layout.addWidget(large_apply_button)
                        button_layout.addWidget(cross_section_button)

                        if main_ui_widget and hasattr(main_ui_widget, 'layout'):
                            layout = main_ui_widget.layout()
                            if layout:
                                layout.insertWidget(0, button_container)
                            else:
                                new_layout = qt.QVBoxLayout(main_ui_widget)
                                new_layout.insertWidget(0, button_container)
                        else:
                            container_widgets = cpr_widget.findChildren(qt.QWidget)
                            for widget in container_widgets:
                                if hasattr(widget, 'layout') and widget.layout() and widget.layout().count() > 0:
                                    widget.layout().insertWidget(0, button_container)
                                    break
                            else:
                                return False
                        
                        slicer.modules.CPRLargeApplyButton = large_apply_button
                        slicer.modules.CPRCrossSectionButton = cross_section_button
                        return True
                    else:
                        if cpr_widget:
                            try:
                                attrs = [attr for attr in dir(cpr_widget) if not attr.startswith('_')]
                                pass
                            except:
                                pass
                        return False
                        
            except Exception as e:
                pass
                return False
        
        success = create_large_button()
        
        if not success:
            qt.QTimer.singleShot(1000, create_large_button)
            qt.QTimer.singleShot(3000, create_large_button)
            
    except Exception as e:
        pass

def apply_cpr_transform_to_centerlines():
    """
    Apply the CPR (Curved Planar Reformat) transform to centerline curve and model nodes.
    This function finds the straightening transform created by CPR and applies it to 
    the specific centerline nodes: "CenterlineCurve" and "CenterlineModel".
    """
    try:
        
        # Find the straightening transform created by CPR
        transform_nodes = slicer.util.getNodesByClass('vtkMRMLTransformNode')
        straightening_transform = None
        
        
        
        # Look specifically for "Straightening transform"
        for transform_node in transform_nodes:
            if transform_node.GetName() == "Straightening transform":
                straightening_transform = transform_node
                break
        
        if not straightening_transform:
            return False

        nodes_to_transform = []

        try:
            centerline_curve = slicer.util.getNode("CenterlineCurve (0)")
            if centerline_curve:
                nodes_to_transform.append(centerline_curve)
        except:
            # Try to find by pattern if exact name doesn't exist
            curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsCurveNode')
            for curve_node in curve_nodes:
                node_name = curve_node.GetName()
                if node_name.startswith("CenterlineCurve (0)"):
                    nodes_to_transform.append(curve_node)
                    pass
                    break
        
        # Look for "CenterlineModel"
        try:
            centerline_model = slicer.util.getNode("CenterlineModel")
            if centerline_model:
                nodes_to_transform.append(centerline_model)
                pass
        except:
            # Try to find by pattern if exact name doesn't exist
            model_nodes = slicer.util.getNodesByClass('vtkMRMLModelNode')
            for model_node in model_nodes:
                node_name = model_node.GetName()
                if node_name.startswith("CenterlineModel"):
                    nodes_to_transform.append(model_node)
                    pass
                    break
        
        # Also check stored workflow references as fallback
        if hasattr(slicer.modules, 'WorkflowCenterlineModel'):
            centerline_model = slicer.modules.WorkflowCenterlineModel
            if centerline_model and centerline_model not in nodes_to_transform:
                nodes_to_transform.append(centerline_model)
                pass
        
        if hasattr(slicer.modules, 'WorkflowCenterlineCurve'):
            centerline_curve = slicer.modules.WorkflowCenterlineCurve
            if centerline_curve and centerline_curve not in nodes_to_transform:
                nodes_to_transform.append(centerline_curve)
                pass
        
        if not nodes_to_transform:
            return False
        
        # Apply the transform to each centerline node
        transformed_count = 0
        for node in nodes_to_transform:
            try:
                # Check if node already has this transform applied
                current_transform = node.GetParentTransformNode()
                if current_transform and current_transform.GetID() == straightening_transform.GetID():
                    pass
                    continue
                
                # Apply the transform
                node.SetAndObserveTransformNodeID(straightening_transform.GetID())
                transformed_count += 1
                pass
                
            except Exception as e:
                pass
        
        if transformed_count > 0:
            
            # Force update of the 3D view
            slicer.app.processEvents()
            
            # Force render the 3D view
            layout_manager = slicer.app.layoutManager()
            if layout_manager:
                threeDWidget = layout_manager.threeDWidget(0)
                if threeDWidget:
                    threeDView = threeDWidget.threeDView()
                    if threeDView:
                        threeDView.forceRender()
            
            return True
        else:
            return False
            
    except Exception as e:
        return False

def setup_cross_section_analysis_module():
    """
    Automatically configure the Cross-Section Analysis module after it opens.
    This function:
    1. Selects the centerline curve (everything else default)
    2. Clicks Apply
    3. Configures browse cross sections: Axial: Red, Long: Green, Point Index: half of total
    """
    try:
        
        # Give the module a moment to fully load
        qt.QTimer.singleShot(500, lambda: configure_cross_section_module())
        
    except Exception as e:
        return False

def configure_cross_section_module():
    """Helper function to configure the Cross-Section Analysis module"""
    try:
        
        # Find the Cross-Section Analysis module widget
        module_widget = None
        try:
            # Try to get the module widget directly
            module_manager = slicer.app.moduleManager()
            module = module_manager.module('CrossSectionAnalysis')
            if module:
                module_widget = module.widgetRepresentation()
        except:
            return False
        
        if not module_widget:
            return False
        
        try:
            # Look for parameter set selector (might be a combo box with parameter set options)
            combo_boxes = module_widget.findChildren(qt.QComboBox)
            parameter_set_selector = None
            
            for i, combo in enumerate(combo_boxes):
                # Look for combo box that might contain parameter sets
                for j in range(combo.count()):
                    item_text = combo.itemText(j)
                    if item_text and ('parameter' in item_text.lower() or 'default' in item_text.lower() or 'standard' in item_text.lower()):
                        parameter_set_selector = combo
                        break
                if parameter_set_selector:
                    break
            
            # If we found a parameter set selector, set it to a reasonable default
            if parameter_set_selector:
                # Try to find and select a default or standard parameter set
                for j in range(parameter_set_selector.count()):
                    item_text = parameter_set_selector.itemText(j)
                    if item_text and ('default' in item_text.lower() or 'standard' in item_text.lower() or j == 0):
                        parameter_set_selector.setCurrentIndex(j)
                        break
                
                # Give UI time to update after parameter set selection
                slicer.app.processEvents()
                time.sleep(0.2)
                
        except Exception as e:
            pass

        try:
            # Look for the input curve selector (first qMRMLNodeComboBox)
            curve_selectors = module_widget.findChildren(slicer.qMRMLNodeComboBox)
            if curve_selectors:
                
                # Find centerline curve node first
                centerline_curve = None
                try:
                    centerline_curve = slicer.util.getNode("CenterlineCurve (0)")
                except:
                    # Try to find any curve node with "Centerline" in the name
                    curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsCurveNode')
                    for curve_node in curve_nodes:
                        if "Centerline" in curve_node.GetName():
                            centerline_curve = curve_node
                            break
                
                if not centerline_curve:
                    return False
                
                # Try to find the correct input selector by looking for one that accepts curves
                input_curve_selector = None
                for i, selector in enumerate(curve_selectors):
                    try:
                        # Check if this selector accepts the type of node we have
                        if hasattr(selector, 'nodeTypes'):
                            node_types = selector.nodeTypes  # Fixed: removed () - it's a property not method
                            if node_types and any('Curve' in node_type or 'Markup' in node_type for node_type in node_types):
                                input_curve_selector = selector
                                break
                        else:
                            # If we can't check types, try the first one
                            if i == 0:
                                input_curve_selector = selector
                    except Exception as e:
                        continue
                
                if not input_curve_selector:
                    # Fallback to first selector
                    input_curve_selector = curve_selectors[0]
                
                # Set the centerline curve
                try:
                    input_curve_selector.setCurrentNode(centerline_curve)
                    
                    # Give the UI more time to update and enable the Apply button
                    slicer.app.processEvents()
                    qt.QApplication.instance().processEvents()
                    
                    # Additional wait to ensure module processes the selection
                    import time
                    time.sleep(0.5)
                    slicer.app.processEvents()
                    
                except Exception as e:
                    
                    return False
                    
        
        except Exception as e:
            return False
        
        # Step 2: Click Apply button

        try:
            # Give the module a moment to update after setting the curve
            slicer.app.processEvents()
            qt.QApplication.instance().processEvents()
            
            # Look for Apply button with more flexible search
            apply_buttons = module_widget.findChildren(qt.QPushButton)
            apply_button = None
            

            
            for i, button in enumerate(apply_buttons):
                button_text = button.text if hasattr(button, 'text') else ""
                
                if button_text and 'apply' in button_text.lower():
                    apply_button = button

                    break
            
            if not apply_button:
                for i, button in enumerate(apply_buttons):
                    button_text = button.text if hasattr(button, 'text') else ""
                    if (button_text and 
                        (button_text.lower() in ['apply', 'run', 'execute', 'start', 'compute'] or
                         'apply' in button_text.lower() or
                         'run' in button_text.lower())):
                        apply_button = button
                        break
            
            if apply_button:
                if apply_button.enabled:
                    apply_button.click()
                    slicer.app.processEvents()
                    qt.QApplication.instance().processEvents()
                    try:
                        # Try to get the module logic to check if Apply succeeded
                        module_manager = slicer.app.moduleManager()
                        module = module_manager.module('CrossSectionAnalysis')
                        if module and hasattr(module, 'logic'):
                            module_logic = module.logic()
                    except Exception as logic_error:
                        pass
                    
                    # Wait for processing to complete
                    qt.QTimer.singleShot(2000, lambda: configure_browse_cross_sections())
                    
                    # Collapse the Parameters tab after Apply has been clicked
                    qt.QTimer.singleShot(1000, lambda: collapse_parameters_tab())
                    return True             
        except Exception as e:
            return False
            
    except Exception as e:
        return False

def collapse_parameters_tab():
    """
    Remove the Parameters section in the Cross-Section Analysis module after Apply has been clicked
    """
    try:
        # Find the Cross-Section Analysis module widget
        module_manager = slicer.app.moduleManager()
        module = module_manager.module('CrossSectionAnalysis')
        if not module:
            return False
            
        module_widget = module.widgetRepresentation()
        if not module_widget:
            return False
        
        # Look for collapsible buttons or group boxes that might contain "Parameters"
        try:
            import ctk
            collapsible_buttons = module_widget.findChildren(ctk.ctkCollapsibleButton)
            for cb in collapsible_buttons:
                button_text = cb.text if hasattr(cb, 'text') else ""
                if "parameter" in button_text.lower():
                    # Fully hide/remove the parameters section instead of just collapsing
                    cb.setVisible(False)
                    cb.hide()
                    return True
        except Exception as ctk_error:
            pass
        
        # Also try QGroupBox as fallback
        group_boxes = module_widget.findChildren(qt.QGroupBox)
        for gb in group_boxes:
            box_title = gb.title if hasattr(gb, 'title') else ""
            if "parameter" in box_title.lower():
                # Completely hide the parameters section
                gb.setVisible(False)
                gb.hide()
                return True
        
        # Try finding any widget with "parameter" in the name or text
        all_widgets = module_widget.findChildren(qt.QWidget)
        for widget in all_widgets:
            # Check object name
            if hasattr(widget, 'objectName') and widget.objectName():
                if "parameter" in widget.objectName().lower():
                    # Fully hide the widget
                    widget.setVisible(False)
                    widget.hide()
                    return True
            
            # Check if it's a collapsible widget with parameter text
            if hasattr(widget, 'text') and widget.text:
                if "parameter" in widget.text().lower():
                    # Fully hide instead of just collapsing
                    widget.setVisible(False)
                    if hasattr(widget, 'hide'):
                        widget.hide()
                    return True
        
        return False
        
    except Exception as e:
        return False

def configure_browse_cross_sections():
    """Configure the browse cross sections settings"""
    try:
        module_manager = slicer.app.moduleManager()
        module = module_manager.module('CrossSectionAnalysis')
        if not module:
            return False
            
        module_widget = module.widgetRepresentation()
        if not module_widget:
            return False
        
        # Look for the browse cross sections area (likely a collapsible button or group box)
        browse_widgets = []
        
        # Try to find collapsible buttons or group boxes
        # Import ctk module for collapsible button access
        try:
            import ctk
            collapsible_buttons = module_widget.findChildren(ctk.ctkCollapsibleButton)
            for cb in collapsible_buttons:
                if "browse" in cb.text.lower() or "cross" in cb.text.lower():
                    browse_widgets.append(cb)
        except Exception as e:
            pass

        group_boxes = module_widget.findChildren(qt.QGroupBox)
        for gb in group_boxes:
            if "browse" in gb.title.lower() or "cross" in gb.title.lower():
                browse_widgets.append(gb)

        # Configure the settings
        for widget in browse_widgets:
            try:
                # Look for the axial and longitudinal slice view selectors
                # Based on XML: axialSliceViewSelector and longitudinalSliceViewSelector
                axial_selector = widget.findChild(slicer.qMRMLNodeComboBox, "axialSliceViewSelector")
                longitudinal_selector = widget.findChild(slicer.qMRMLNodeComboBox, "longitudinalSliceViewSelector")
                
                try:
                    if axial_selector:
                        # Set Axial to Red using direct node selection (similar to provided script)
                        red_slice_node = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeRed')
                        if red_slice_node:
                            axial_selector.setCurrentNode(red_slice_node)
                except Exception as axial_error:
                    pass
                try:
                    if longitudinal_selector:
                        # Set Longitudinal to Green using direct node selection (similar to provided script)
                        green_slice_node = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeGreen')
                        if green_slice_node:
                            longitudinal_selector.setCurrentNode(green_slice_node)
                except Exception as longitudinal_error:
                    pass
                
                # Find slider for Point Index (moveToPointSliderWidget in XML)
                try:
                    # Import ctk module first
                    import ctk
                    point_slider = widget.findChild(ctk.ctkSliderWidget, "moveToPointSliderWidget")
                    if point_slider:
                        if hasattr(point_slider, 'maximum') and point_slider.maximum > 0:
                            # Set point index to 230, but ensure it's within the slider's range
                            target_value = min(230, point_slider.maximum)
                            point_slider.setValue(target_value)
                except Exception as slider_error:
                    pass
            except Exception as e:
                continue
        return True
    except Exception as e:
        return False

def start_with_dicom_data():
    """
    Start the workflow by opening the Add DICOM Data module and waiting for a volume to be loaded.
    """
    try:
        # Set 3D view background to black at the start of workflow
        set_3d_view_background_black()
        
        pass
        
        # Check if there are already volumes in the scene
        existing_volumes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        if existing_volumes:
            pass

            result = slicer.util.confirmYesNoDisplay(
                f"Found {len(existing_volumes)} existing volume(s) in the scene.\n\n"
                "Would you like to:\n"
                "• YES: Continue workflow with existing volumes\n"
                "• NO: Load new DICOM data",
                windowTitle="Existing Volumes Found"
            )
            if result:
                start_workflow_with_segmentation_dialog()
                return
        
        slicer.util.selectModule("DICOM")
        slicer.app.processEvents()
        
        # Set up monitoring for volume addition
        setup_volume_addition_monitor()
        
    except Exception as e:
        slicer.util.errorDisplay(f"Could not open DICOM module: {str(e)}")

def load_dicom_from_source_file(dicom_path):
    """
    Load DICOM data from a path specified in the source_slicer.txt file.
    Uses a robust plugin-based approach similar to mpReviewPreprocessor for better compatibility.
    """
    import os
    import vtk
    try:
        
        # Check if path exists
        if not os.path.exists(dicom_path):
            qt.QMessageBox.warning(
                None,
                "DICOM Path Not Found",
                f"The DICOM path specified in source_slicer.txt does not exist:\n\n{dicom_path}\n\nPlease check the path and update the file."
            )
            return False
        
        # Enhanced Philips detection - prioritize this approach for Philips files
        # This checks for v_headers files and manufacturer info to identify Philips DICOMs
        dicom_files = _find_dicom_files_in_directory(dicom_path)
        if dicom_files:
            file_analysis = _analyze_dicom_files(dicom_files)
            if file_analysis['is_philips']:
                
                # Try the simple method first (exact copy of user's working script)
                simple_result = load_philips_dicom_simple(dicom_path)
                if simple_result:
                    return True
                
                # Fall back to enhanced method if simple fails
                philips_result = _load_philips_dicom_series(dicom_path)
                if philips_result:
                    return True
        
        # Check if enhanced DICOM utilities are available
        if not DICOM_UTILS_AVAILABLE:
            return _fallback_dicom_loading(dicom_path)
        
        # Use robust plugin-based approach inspired by mpReviewPreprocessor
        try:
            
            # Check if we can use TemporaryDICOMDatabase
            if DICOM_UTILS_AVAILABLE:
                try:
                    # Use temporary database for clean operation
                    temp_db_dir = os.path.join(slicer.app.temporaryPath, "WorkflowDICOMTemp")
                    if os.path.exists(temp_db_dir):
                        import shutil
                        shutil.rmtree(temp_db_dir)
                    
                    with TemporaryDICOMDatabase(temp_db_dir) as temp_db:
                        success = _import_and_load_dicom_data(dicom_path, temp_db)
                        if success:
                            return success
                except Exception as temp_db_error:
                    pass
            
            # Fallback to direct plugin examination without temporary database
            success = _import_and_load_dicom_data(dicom_path, None)
            if success:
                return success
                    
        except Exception as e:
            pass
            pass
            return _fallback_dicom_loading(dicom_path)
        
        # If we get here, all methods failed
        
        # Provide specific guidance based on file types found
        dicom_info = ""
        if os.path.isdir(dicom_path):
            files = os.listdir(dicom_path)
            numeric_extensions = [f for f in files if '.' in f and f.split('.')[-1].isdigit()]
            if numeric_extensions:
                dicom_info = f"\n\nDetected {len(numeric_extensions)} files with numeric extensions (e.g., .1, .2, .3).\nThis appears to be a DICOM series that should load as a complete volume."
        
        qt.QMessageBox.information(
            None,
            "DICOM Loading Failed",
            f"Could not automatically load DICOM from:\n{dicom_path}{dicom_info}\n\n"
            "Please manually:\n"
            "1. Go to DICOM module\n"
            "2. Import the DICOM folder\n"
            "3. Load the complete series as a volume\n"
            "4. Return to workflow module"
        )
        return False
        
    except Exception as e:
        pass
        qt.QMessageBox.critical(
            None,
            "Error",
            f"Error loading DICOM from source file:\n{str(e)}"
        )
        return False

def _import_and_load_dicom_data(input_dir, temp_db=None):
    """
    Import and load DICOM data using enhanced plugin-based approach.
    Based on mpReviewPreprocessor methodology for robust DICOM handling.
    """
    try:
        
        # Use temporary database if provided, otherwise get main database safely
        dicom_database = temp_db
        if not dicom_database:
            try:
                # Try different ways to get the DICOM database
                if hasattr(slicer, 'dicomDatabase'):
                    dicom_database = slicer.dicomDatabase
                elif hasattr(slicer.modules, 'dicom'):
                    dicom_module = slicer.modules.dicom
                    if hasattr(dicom_module, 'logic'):
                        dicom_logic = dicom_module.logic()
                        if hasattr(dicom_logic, 'database'):
                            dicom_database = dicom_logic.database
                else:
                    dicom_database = None
            except Exception as db_error:
                pass
                dicom_database = None
        
        # Try different import methods based on available components
        if ctk and dicom_database:
            # Method 1: Use ctk indexer if both are available
            try:
                indexer = ctk.ctkDICOMIndexer()
                indexer.addDirectory(dicom_database, input_dir)
                
                # Continue with database analysis
                patients = dicom_database.patients()
                
                if patients:
                    # Process patients as before...
                    return _process_dicom_database_patients(dicom_database, patients, input_dir)
                    
            except Exception as indexer_error:
                pass

        # Method 2: Direct file analysis without plugins (bypass database issues)
        dicom_files = _find_dicom_files_in_directory(input_dir)
        
        if dicom_files:
            
            # Check if these are Philips files first - use specialized loader if so
            file_analysis = _analyze_dicom_files(dicom_files)
            if file_analysis.get('is_philips', False):
                try:
                    philips_result = _load_philips_dicom_series(input_dir)
                    if philips_result:
                        set_3d_view_background_black()
                        qt.QTimer.singleShot(1000, start_markup_workflow)
                        return True
                
                except Exception as philips_error:
                    pass
                    pass
            
            # Skip plugin system entirely and use Slicer's built-in loading
            try:
                
                # Method 2a: Try loading the directory directly
                volume_node = slicer.util.loadVolume(input_dir)
                
                if volume_node:
                    
                    # Check if we got a proper multi-slice volume
                    image_data = volume_node.GetImageData()
                    if image_data:
                        dims = image_data.GetDimensions()
                        

                    
                    volume_node.SetName("CT_Cardiac_Series")
                    set_3d_view_background_black()
                    qt.QTimer.singleShot(1000, start_markup_workflow)
                    return True
                    
            except Exception as dir_load_error:
                pass
            
            # Method 2b: Try loading first DICOM file (should trigger series loading)
            try:
                first_file = dicom_files[0]
                
                volume_node = slicer.util.loadVolume(first_file)
                
                if volume_node:
                    
                    # Check what we got
                    image_data = volume_node.GetImageData()
                    if image_data:
                        dims = image_data.GetDimensions()
                        
                        if dims[2] > 1:
                            volume_node.SetName("CT_Series")
                            set_3d_view_background_black()
                            qt.QTimer.singleShot(1000, start_with_volume_crop)
                            return True
                        else:
                            
                            # Try to load the full series using DICOM module
                            success = _load_dicom_series_manually(dicom_files, input_dir)
                            if success:
                                return True
                    
                    # If we still only have one slice, keep it but warn user
                    volume_node.SetName("CT_SingleSlice")
                    set_3d_view_background_black()
                    qt.QTimer.singleShot(1000, start_with_volume_crop)
                    return True
                    
            except Exception as file_load_error:
                pass
            
            # Method 2c: Try manual series loading for numbered DICOM files
            success = _load_dicom_series_manually(dicom_files, input_dir)
            if success:
                return True
            
            # Method 2d: Try Slicer's volume sequence loading
            success = _load_as_volume_sequence(dicom_files, input_dir)
            if success:
                return True
            
            # Method 2e: Last resort - try loading with VTK directly
            success = _load_with_vtk_direct(dicom_files)
            if success:
                return True

        
        return False
    
    except Exception as e:
        pass
        return False

def _process_dicom_database_patients(dicom_database, patients, input_dir=None):
    """
    Process patients from DICOM database to find and load suitable series.
    """
    try:
        # Process each patient to find loadable series
        for patient in patients:
            studies = dicom_database.studiesForPatient(patient)
            
            for study in studies:
                series_list = dicom_database.seriesForStudy(study)
                
                for series_uid in series_list:
                    files = dicom_database.filesForSeries(series_uid)
                    if not files:
                        continue
                    
                    series_description = dicom_database.seriesDescription(series_uid)
                    
                    # Use plugin-based approach to find best loader
                    plugin, loadable = _get_plugin_and_loadable_for_files(series_description, files)
                    
                    if loadable and plugin:
                        
                        try:
                            # Load the series using the best plugin
                            volume_node = plugin.load(loadable)
                            
                            if volume_node:
                                # Set appropriate name
                                if series_description:
                                    volume_node.SetName(series_description)
                                else:
                                    volume_node.SetName(f"DICOM_Series_{series_uid[:8]}")
                                
                                # Store DICOM metadata
                                volume_node.SetAttribute("DICOM_SeriesUID", series_uid)
                                volume_node.SetAttribute("DICOM_PatientID", patient)
                                
                                
                                # Verify we have a proper volume
                                image_data = volume_node.GetImageData()
                                if image_data:
                                    dims = image_data.GetDimensions()
                                    spacing = volume_node.GetSpacing()
                                    
                                    # Apply any necessary corrections
                                    fix_dicom_spacing_and_orientation(volume_node, input_dir)
                                    
                                    # Continue workflow
                                    set_3d_view_background_black()
                                    qt.QTimer.singleShot(1000, start_with_volume_crop)
                                    return True
                                    
                        except Exception as load_error:
                            pass
                            continue
        
        return False
        
    except Exception as e:
        pass
        return False

def _get_plugin_and_loadable_for_files(series_description, files):
    """
    Find the best DICOM plugin and loadable for given files.
    Based on mpReviewPreprocessor's _getPluginAndLoadableForFiles method.
    Enhanced to handle various DICOM file types and conventions.
    """
    try:
        
        # Enhanced plugin list to handle various DICOM file types and conventions
        plugin_names = [
            'MultiVolumeImporterPlugin',    # For 4D/multi-volume DICOM (enhanced MR, etc.)
            'DICOMScalarVolumePlugin',      # Standard single-volume DICOM (CT, MR, etc.)
            'DICOMSegmentationPlugin',      # DICOM SEG objects
            'DICOMRTStructureSetPlugin',    # RT Structure Sets
            'DICOMParametricMapPlugin',     # Parametric maps
            'DICOMTractographyPlugin',      # Diffusion tractography
            'DICOMQuantitativeReporting',   # Structured reports
            'DICOMLongitudinalPETCTPlugin', # Longitudinal studies
            'DICOMPETSUVPlugin',           # PET SUV analysis
            'DICOMPET',                    # General PET
            'DICOMEnhancedUSVolumePlugin', # Enhanced ultrasound
        ]
        
        # First, analyze files to understand the data type
        file_analysis = _analyze_dicom_files(files)
        
        best_plugin = None
        best_loadable = None
        best_confidence = 0
        
        # Plugin system disabled due to slicer.modules.dicomPlugins compatibility issues
        
        if best_plugin and best_loadable:
            return best_plugin, best_loadable
        
        return None, None
        
    except Exception as e:
        pass
        return None, None

def _load_via_standardized_temp_folder(dicom_files, series_directory):
    """
    Create a temporary folder with standardized DICOM files (.dcm extension) 
    and proper sequential naming for better Slicer compatibility.
    """
    try:
        import tempfile
        import shutil
        import pydicom
        
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix="slicer_dicom_")
        
        # Read all DICOM files and extract metadata for proper sorting
        dicom_data = []
        for file_path in dicom_files:
            try:
                # Read DICOM metadata
                ds = pydicom.dcmread(file_path, force=True, stop_before_pixels=True)
                
                # Extract key sorting information
                instance_number = getattr(ds, 'InstanceNumber', 0)
                slice_location = getattr(ds, 'SliceLocation', 0.0)
                
                # Handle string slice locations
                if isinstance(slice_location, str):
                    try:
                        slice_location = float(slice_location)
                    except:
                        slice_location = 0.0
                
                # Extract slice number from filename as fallback
                filename_slice = _extract_slice_number(file_path)
                
                dicom_data.append({
                    'file_path': file_path,
                    'instance_number': instance_number,
                    'slice_location': slice_location,
                    'filename_slice': filename_slice,
                    'filename': os.path.basename(file_path)
                })
                
            except Exception as e:
                pass
                # Add file anyway with basic info
                dicom_data.append({
                    'file_path': file_path,
                    'instance_number': 0,
                    'slice_location': 0.0,
                    'filename_slice': _extract_slice_number(file_path),
                    'filename': os.path.basename(file_path)
                })
        
        # Sort by multiple criteria for proper slice ordering
        def sort_key(item):
            return (item['instance_number'], item['slice_location'], item['filename_slice'])
        
        dicom_data.sort(key=sort_key)
        
        # Copy files to temp directory with standardized naming
        standardized_files = []
        for i, item in enumerate(dicom_data, 1):
            # Create standardized filename: IMG_0001.dcm, IMG_0002.dcm, etc.
            standardized_name = f"IMG_{i:04d}.dcm"
            dest_path = os.path.join(temp_dir, standardized_name)
            
            # Copy file to standardized location
            shutil.copy2(item['file_path'], dest_path)
            standardized_files.append(dest_path)
        
        
        # Now try loading from the standardized temp folder
        
        # Method 1: Load directory as DICOM series
        try:
            volume_node = slicer.util.loadVolume(temp_dir)
            if volume_node:
                image_data = volume_node.GetImageData()
                if image_data:
                    dims = image_data.GetDimensions()
                    
                    if dims[2] > 1:
                        volume_node.SetName("CT_Series_Standardized")
                        
                        # Clean up temp folder after successful load
                        def cleanup_temp():
                            try:
                                shutil.rmtree(temp_dir, ignore_errors=True)
                            except:
                                pass
                        
                        # Cleanup after a delay
                        qt.QTimer.singleShot(5000, cleanup_temp)
                        
                        return volume_node
        except Exception as e:
            pass
        
        # Method 2: Load using first file in standardized series
        try:
            if standardized_files:
                volume_node = slicer.util.loadVolume(standardized_files[0])
                if volume_node:
                    image_data = volume_node.GetImageData()
                    if image_data:
                        dims = image_data.GetDimensions()
                        
                        if dims[2] > 1:
                            volume_node.SetName("CT_Series_StandardizedFile")
                            
                            # Clean up temp folder after successful load
                            def cleanup_temp():
                                try:
                                    shutil.rmtree(temp_dir, ignore_errors=True)
                                except:
                                    pass
                            
                            qt.QTimer.singleShot(5000, cleanup_temp)
                            
                            return volume_node
        except Exception as e:
            pass
        
        # Method 3: Try VTK DICOM reader with standardized files
        try:
            result = _load_volume_from_file_list(standardized_files)
            if result:
                
                # Clean up temp folder
                def cleanup_temp():
                    try:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                    except:
                        pass
                
                qt.QTimer.singleShot(5000, cleanup_temp)
                
                return result
        except Exception as e:
            pass
        
        # Clean up temp folder if all methods failed
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
            
        return None
        
    except Exception as e:
        pass
        import traceback
        traceback.print_exc()
        return None

def _load_philips_dicom_series(dicom_directory):
    """
    Load Philips DICOM series using the exact method that works.
    Based on user's proven successful script - simplified and direct.
    """
    try:
        # Import required modules (exactly as in working script)
        import DICOMLib
        from DICOMLib import DICOMUtils
        import slicer
        
        # Track existing volumes
        existing_volumes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        
        # Ensure DICOM database is properly initialized before importing
        try:
            # Initialize DICOM database if it doesn't exist
            if not hasattr(slicer, 'dicomDatabase') or slicer.dicomDatabase is None:
                # Open DICOM module to initialize the database
                slicer.util.selectModule("DICOM")
                slicer.app.processEvents()
                
                # Alternative initialization if module approach doesn't work
                if not hasattr(slicer, 'dicomDatabase') or slicer.dicomDatabase is None:
                    import DICOMLib
                    # This should initialize slicer.dicomDatabase
                    DICOMLib.DICOMUtils.openDatabase()
        except Exception as init_error:
            pass
        
        # Import DICOM directory (ignores unreadable files like v_headers)
        DICOMUtils.importDicom(dicom_directory)
        
        # Access the Slicer DICOM database instance (exactly as in working script)
        db = slicer.dicomDatabase  #  this is the correct database handle
        
        # Get all patient UIDs in the database
        patientUIDs = db.patients()
        
        if len(patientUIDs) == 0:
            return None
        else:
            firstPatientUID = patientUIDs[0]
            
            # Load the patient data (exactly as in working script)
            DICOMUtils.loadPatientByUID(firstPatientUID)
            
            # Check if volume was loaded successfully
            new_volumes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
            
            # Find the newly loaded volume
            for volume in new_volumes:
                if volume not in existing_volumes:  # This is a new volume
                    image_data = volume.GetImageData()
                    if image_data:
                        dims = image_data.GetDimensions()
                        
                        if dims[2] > 1:  # Ensure it's a multi-slice volume
                            volume.SetName("CT_Series_Philips")
                            
                            # Continue workflow after successful loading
                            qt.QTimer.singleShot(1000, start_with_volume_crop)
                            
                            return volume
            
            # If no new volumes found, try the most recently loaded volume
            if new_volumes:
                latest_volume = new_volumes[-1]
                image_data = latest_volume.GetImageData()
                if image_data:
                    dims = image_data.GetDimensions()
                    if dims[2] > 1:
                        latest_volume.SetName("CT_Series_Philips")
                        
                        # Continue workflow after successful loading
                        qt.QTimer.singleShot(1000, start_with_volume_crop)
                        
                        return latest_volume
            
            return None
            
    except Exception as e:
        return None

def _load_dicom_series_manually(dicom_files, series_directory):
    """
    Manually load DICOM series when automatic loading only gets single slice.
    This handles numbered series like i1559699.CTDC.1, i1559700.CTDC.2, etc.
    Now includes Philips-specific loading and standardized temp folder conversion for better compatibility.
    """
    try:
        
        # Method -1: Check if this is Philips DICOM and use specialized loading
        file_analysis = _analyze_dicom_files(dicom_files)
        
        if file_analysis.get('is_philips', False):
            try:
                philips_result = _load_philips_dicom_series(series_directory)
                if philips_result:
                    set_3d_view_background_black()
                    qt.QTimer.singleShot(1000, start_with_volume_crop)
                    return True
            except Exception as philips_error:
                pass
        
        # Method 0: Try standardized temp folder conversion first
        try:
            standardized_result = _load_via_standardized_temp_folder(dicom_files, series_directory)
            if standardized_result:
                set_3d_view_background_black()
                qt.QTimer.singleShot(1000, start_with_volume_crop)
                return True
        except Exception as std_error:
            pass
        
        # Method 1: Try using DICOMLib to create a temporary database and load series
        try:
            
            import DICOMLib
            
            # Create a temporary database in memory
            db = DICOMLib.DICOMDatabase()
            
            # Set up temporary database location
            import tempfile
            temp_dir = tempfile.mkdtemp()
            db_path = os.path.join(temp_dir, "temp_dicom.db")
            
            if db.openDatabase(db_path):
                
                # Index the DICOM files
                indexer = ctk.ctkDICOMIndexer()
                indexer.addDirectory(db, series_directory)
                
                # Get patients and series
                patients = db.patients()
                if patients:
                    for patient in patients:
                        studies = db.studiesForPatient(patient)
                        for study in studies:
                            series_list = db.seriesForStudy(study)
                            for series in series_list:
                                files_in_series = db.filesForSeries(series)
                                
                                if len(files_in_series) >= len(dicom_files) * 0.8:  # Got most files
                                    
                                    # Load using slicer with the series files
                                    volume_node = slicer.util.loadVolume(files_in_series[0])
                                    
                                    if volume_node:
                                        # Check if we got the full volume
                                        image_data = volume_node.GetImageData()
                                        if image_data:
                                            dims = image_data.GetDimensions()
                                            
                                            if dims[2] > 1:
                                                volume_node.SetName("CT_Series_Manual")
                                                set_3d_view_background_black()
                                                qt.QTimer.singleShot(1000, start_with_volume_crop)
                                                
                                                # Cleanup temp database
                                                db.closeDatabase()
                                                import shutil
                                                shutil.rmtree(temp_dir, ignore_errors=True)
                                                
                                                return True
                                    
                # Cleanup if failed
                db.closeDatabase()
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as dicomlib_error:
            pass
        
        # Method 2: Try loading with explicit file list
        try:
            
            # Sort files by slice number if possible
            sorted_files = sorted(dicom_files, key=lambda x: _extract_slice_number(x))
            
            # Try different approaches for multi-file loading
            approaches = [
                ("Load file list directly", lambda: slicer.util.loadVolume(sorted_files)),
                ("VTK DICOM reader", lambda: _load_volume_from_file_list(sorted_files)),
                ("Load directory with series hint", lambda: _load_with_series_hint(series_directory, sorted_files)),
            ]
            
            for approach_name, approach_func in approaches:
                try:
                    volume_node = approach_func()
                    
                    if volume_node:
                        image_data = volume_node.GetImageData()
                        if image_data:
                            dims = image_data.GetDimensions()
                            
                            if dims[2] > 1:
                                volume_node.SetName("CT_Series_FileList")
                                set_3d_view_background_black()
                                qt.QTimer.singleShot(1000, start_with_volume_crop)
                                return True

                except Exception as approach_error:
                    pass
                    
        except Exception as filelist_error:
            pass
        
        # Method 3: Try DICOM browser loading
        try:
            success = _load_with_dicom_browser(series_directory)
            if success:
                return True
        except Exception as browser_error:
            pass
        
        return False
        
    except Exception as e:
        pass
        return False

def _extract_slice_number(file_path):
    """Extract slice number from DICOM filename for sorting."""
    try:
        filename = os.path.basename(file_path)
        # For files like i1559699.CTDC.1, extract the final number
        if '.' in filename:
            parts = filename.split('.')
            for part in reversed(parts):
                if part.isdigit():
                    return int(part)
        return 0
    except:
        return 0

def _load_volume_from_file_list(file_list):
    """Try to load volume from an explicit list of DICOM files."""
    try:
        
        # Method 1: Use VTK DICOM reader with directory
        import vtk
        
        # Try directory-based reading first
        directory = os.path.dirname(file_list[0])
        reader = vtk.vtkDICOMImageReader()
        reader.SetDirectoryName(directory)
        
        try:
            reader.Update()
            output = reader.GetOutput()
            
            if output and output.GetNumberOfPoints() > 0:
                dims = output.GetDimensions()
                
                if dims[2] > 1:
                    # Create volume node
                    volume_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
                    volume_node.SetAndObserveImageData(output)
                    volume_node.CreateDefaultDisplayNodes()
                    return volume_node
        except Exception as dir_error:
            pass
        
        # Method 2: Use SimpleITK for DICOM series reading
        try:
            import SimpleITK as sitk
            
            # Read the DICOM series
            series_reader = sitk.ImageSeriesReader()
            series_reader.SetFileNames(file_list)
            
            # Read the image
            sitk_image = series_reader.Execute()
            
            if sitk_image:
                
                # Convert to VTK and create Slicer volume
                sitk_utils = slicer.util.getModuleLogic('SimpleITK')
                if sitk_utils:
                    volume_node = sitk_utils.sitkImageToVolumeNode(sitk_image)
                    if volume_node:
                        volume_node.SetName("DICOM_Series_SimpleITK")
                        return volume_node
                
        except ImportError:
            pass
        except Exception as sitk_error:
            pass
        
        # Method 3: Try VTK ImageReader2 with file pattern
        try:
            
            # Find a pattern in the files
            first_file = os.path.basename(file_list[0])
            if 'CTDC' in first_file:
                # For files like i1559699.CTDC.1, create pattern like i%d.CTDC.%d
                base_pattern = first_file.split('.')[0]
                pattern_file = os.path.join(os.path.dirname(file_list[0]), f"{base_pattern[:8]}*.CTDC.*")
        
        except Exception as pattern_error:
            pass
        
        return None
        
    except Exception as e:
        return None

def _load_with_series_hint(directory, file_list):
    """Try to load DICOM with series loading hints."""
    try:
        
        # Try loading with properties that indicate this is a series
        properties = {
            'singleFile': False,
            'multipleFiles': True,
            'seriesInDirectory': True
        }
        
        # Load the directory but with series properties
        volume_node = slicer.util.loadVolume(directory, properties=properties)
        return volume_node
        
    except Exception as e:
        pass
        return None

def _load_with_dicom_browser(directory):
    """Try to load using DICOM browser module."""
    try:
        
        # Get DICOM browser module
        if hasattr(slicer.modules, 'dicom'):
            dicom_module = slicer.modules.dicom
            
            # Create widget instance
            dicom_widget = slicer.modules.DICOMWidget()
            
            # Try to import directory
            dicom_widget.onImportDirectory(directory)
            
            # This is a simplified approach - in practice, the DICOM browser
            # would require user interaction or more complex automation
            return False
            
    except Exception as e:
        return False

def _load_as_volume_sequence(dicom_files, directory):
    """Try to load DICOM files as a volume sequence."""
    try:
        
        # Sort files by slice number
        sorted_files = sorted(dicom_files, key=lambda x: _extract_slice_number(x))
        
        # Try to load using Slicer's sequence utilities
        try:
            # Load first file to get the base volume
            base_volume = slicer.util.loadVolume(sorted_files[0])
            if not base_volume:
                return False
            
            # Check if Slicer automatically loaded the series
            image_data = base_volume.GetImageData()
            if image_data:
                dims = image_data.GetDimensions()
                
                if dims[2] >= len(sorted_files) * 0.8:  # Got most of the series
                    base_volume.SetName("CT_AutoSeries")
                    set_3d_view_background_black()
                    qt.QTimer.singleShot(1000, start_with_volume_crop)
                    return True
                elif dims[2] > 1:
                    base_volume.SetName("CT_PartialSeries")
                    set_3d_view_background_black()
                    qt.QTimer.singleShot(1000, start_with_volume_crop)
                    return True

            chunk_size = 10
            for i in range(0, len(sorted_files), chunk_size):
                chunk = sorted_files[i:i+chunk_size]
                
                try:
                    # Try loading the chunk
                    for file_path in chunk:
                        temp_volume = slicer.util.loadVolume(file_path)
                        if temp_volume:
                            temp_data = temp_volume.GetImageData()
                            if temp_data and temp_data.GetDimensions()[2] > 1:
                                temp_volume.SetName("CT_ChunkSeries")
                                # Remove other volumes
                                if base_volume != temp_volume:
                                    slicer.mrmlScene.RemoveNode(base_volume)
                                set_3d_view_background_black()
                                qt.QTimer.singleShot(1000, start_with_volume_crop)
                                return True
                            else:
                                # Clean up single slice
                                slicer.mrmlScene.RemoveNode(temp_volume)
                except Exception as chunk_error:
                    pass
                    
                # Don't try too many chunks
                if i > 100:
                    break
            
            # Keep the single slice if nothing else worked
            return False
            
        except Exception as seq_error:
            pass
            return False
            
    except Exception as e:
        pass
        return False

def _load_with_vtk_direct(dicom_files):
    """Last resort: direct VTK DICOM loading with comprehensive error handling."""
    try:
        
        import vtk
        
        # Sort files numerically 
        sorted_files = sorted(dicom_files, key=lambda x: _extract_slice_number(x))
        
        # Method 1: Try VTK DICOM directory reader
        try:
            reader = vtk.vtkDICOMImageReader()
            directory = os.path.dirname(sorted_files[0])
            reader.SetDirectoryName(directory)
            reader.Update()
            
            output = reader.GetOutput()
            if output and output.GetNumberOfPoints() > 0:
                dims = output.GetDimensions()
                
                if dims[2] > 1:
                    # Create volume node
                    volume_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
                    volume_node.SetAndObserveImageData(output)
                    volume_node.SetName("VTK_DICOM_Series")
                    
                    # Create display node
                    volume_node.CreateDefaultDisplayNodes()
                    
                    # Set up visualization
                    set_3d_view_background_black()
                    qt.QTimer.singleShot(1000, start_with_volume_crop)
                    
                    return True
        except Exception as vtk_error:
            pass
        
        # Method 2: Try creating a volume from individual slice loading
        try:
            
            # Load first slice to get dimensions
            first_reader = vtk.vtkDICOMImageReader()
            first_reader.SetFileName(sorted_files[0])
            first_reader.Update()
            first_output = first_reader.GetOutput()
            
            if first_output:
                dims_2d = first_output.GetDimensions()
                
                # Create 3D volume by stacking slices
                num_slices = len(sorted_files)
                
                # Use VTK image append to stack slices
                append_filter = vtk.vtkImageAppend()
                append_filter.SetAppendAxis(2)  # Stack along Z axis
                
                loaded_count = 0
                
                for i, file_path in enumerate(sorted_files):
                    try:
                        slice_reader = vtk.vtkDICOMImageReader()
                        slice_reader.SetFileName(file_path)
                        slice_reader.Update()
                        
                        slice_output = slice_reader.GetOutput()
                        if slice_output and slice_output.GetNumberOfPoints() > 0:
                            append_filter.AddInputData(slice_output)
                            loaded_count += 1
                            

                        
                    except Exception as slice_error:
                        pass
                
                if loaded_count > 1:
                    append_filter.Update()
                    stacked_output = append_filter.GetOutput()
                    
                    if stacked_output:
                        final_dims = stacked_output.GetDimensions()
                        
                        # Create volume node
                        volume_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
                        volume_node.SetAndObserveImageData(stacked_output)
                        volume_node.SetName("VTK_Stacked_Series")
                        
                        # Create display node
                        volume_node.CreateDefaultDisplayNodes()
                        
                        # Set up visualization
                        set_3d_view_background_black()
                        qt.QTimer.singleShot(1000, start_with_volume_crop)
                        
                        return True
                        
        except Exception as stack_error:
            pass
        
        return False
        
    except Exception as e:
        pass
        return False

def _analyze_dicom_files(files):
    """
    Analyze DICOM files to understand data characteristics and help with plugin selection.
    """
    analysis = {
        'file_count': len(files),
        'has_numeric_extensions': False,
        'has_ctdc_pattern': False,
        'has_header_files': False,
        'modality': 'unknown',
        'manufacturer': 'unknown',
        'series_type': 'unknown',
        'is_philips': False
    }
    
    try:
        # Analyze file naming patterns
        for file_path in files[:5]:  # Check first 5 files
            file_name = os.path.basename(file_path)
            
            # Check for numeric extensions (.1, .2, .3, etc.)
            if '.' in file_name and file_name.split('.')[-1].isdigit():
                analysis['has_numeric_extensions'] = True
            
            # Check for CTDC pattern
            if 'CTDC' in file_name.upper():
                analysis['has_ctdc_pattern'] = True
            
            # Check for header files
            if 'v_headers' in file_name.lower():
                analysis['has_header_files'] = True
        
        # Enhanced Philips detection - check for v_headers file
        for file_path in files:
            file_name = os.path.basename(file_path)
            if 'v_headers' in file_name.lower() or 'volume_headers' in file_name.lower():
                analysis['has_header_files'] = True
                analysis['is_philips'] = True  # v_headers is a strong indicator of Philips
                break
        
        # Try to read DICOM header information from first file if possible
        try:
            if DICOM_UTILS_AVAILABLE and not analysis['is_philips']:  # Skip DICOM header read if already detected as Philips
                # Try to use pydicom if available
                try:
                    import pydicom
                    ds = pydicom.dcmread(files[0], stop_before_pixels=True)
                    
                    if hasattr(ds, 'Modality'):
                        analysis['modality'] = str(ds.Modality)
                    
                    if hasattr(ds, 'Manufacturer'):
                        analysis['manufacturer'] = str(ds.Manufacturer)
                        # Check for Philips manufacturer
                        if 'philips' in analysis['manufacturer'].lower():
                            analysis['is_philips'] = True
                    
                    if hasattr(ds, 'SeriesDescription'):
                        series_desc = str(ds.SeriesDescription).lower()
                        if any(term in series_desc for term in ['enhanced', '4d', 'dynamic']):
                            analysis['series_type'] = 'enhanced'
                        elif any(term in series_desc for term in ['seg', 'segmentation']):
                            analysis['series_type'] = 'segmentation'
                        elif any(term in series_desc for term in ['rt', 'rtstruct']):
                            analysis['series_type'] = 'rt_structure'
                        else:
                            analysis['series_type'] = 'standard'
                    
                except Exception:
                    pass  # pydicom not available or file not readable
        except Exception:
            pass  # DICOM analysis failed, use basic analysis
        
    except Exception as e:
        pass
    
    return analysis

def _adjust_plugin_confidence(plugin_name, original_confidence, file_analysis, series_description):
    """
    Adjust plugin confidence based on file analysis and series description.
    This helps select the most appropriate plugin for different DICOM conventions.
    """
    try:
        adjusted = original_confidence
        
        # Boost confidence for specific patterns
        if plugin_name == 'DICOMScalarVolumePlugin':
            # Prefer for standard CT/MR volumes
            if file_analysis.get('modality', '').upper() in ['CT', 'MR', 'CR', 'XR']:
                adjusted += 0.1
            
            # Boost for numeric extension pattern (common DICOM series)
            if file_analysis.get('has_numeric_extensions', False):
                adjusted += 0.15
            
            # Boost for CTDC pattern
            if file_analysis.get('has_ctdc_pattern', False):
                adjusted += 0.1
        
        elif plugin_name == 'MultiVolumeImporterPlugin':
            # Prefer for enhanced/4D volumes
            if file_analysis.get('series_type') == 'enhanced':
                adjusted += 0.2
            
            # Prefer for large file counts (likely multi-volume)
            if file_analysis.get('file_count', 0) > 100:
                adjusted += 0.1
        
        elif plugin_name == 'DICOMSegmentationPlugin':
            # Prefer for segmentation series
            if file_analysis.get('series_type') == 'segmentation':
                adjusted += 0.3
            
            if series_description and 'seg' in series_description.lower():
                adjusted += 0.2
        
        elif plugin_name == 'DICOMRTStructureSetPlugin':
            # Prefer for RT structure sets
            if file_analysis.get('series_type') == 'rt_structure':
                adjusted += 0.3
            
            if series_description and any(term in series_description.lower() for term in ['rt', 'rtstruct']):
                adjusted += 0.2
        
        # Cap at 1.0
        return min(adjusted, 1.0)
        
    except Exception as e:
        pass
        return original_confidence

def _find_dicom_files_in_directory(directory):
    """
    Find DICOM files in a directory using enhanced detection patterns.
    Improved to handle complex medical imaging folder structures.
    """
    dicom_files = []
    try:
        file_count = 0
        
        for root, dirs, files in os.walk(directory):
            
            for file in files:
                file_count += 1
                file_path = os.path.join(root, file)
                filename = os.path.basename(file)
                filename_lower = filename.lower()
                
                # Check file size - DICOM files are typically larger than a few KB
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size < 1024:  # Skip very small files (likely not DICOM)
                        continue
                except:
                    continue
                
                # Enhanced DICOM file detection patterns
                is_dicom = False
                
                # Standard DICOM extensions
                if filename_lower.endswith(('.dcm', '.dicom', '.ima', '.dcm30', '.dic')):
                    is_dicom = True
                
                # Files with no extension (common in medical imaging)
                elif '.' not in filename and len(filename) > 3:
                    is_dicom = True
                
                # Files starting with medical imaging prefixes
                elif filename_lower.startswith(('i', 'im', 'ima', 'dicom', 'ct', 'mr')):
                    is_dicom = True
                
                # Files containing medical patterns (but exclude known non-DICOM files)
                elif any(pattern in filename_lower for pattern in ['ctdc', 'ct_', 'mr_', 'cta', 'coronary']):
                    # Exclude known non-DICOM files
                    if not any(exclude in filename_lower for exclude in ['header', 'readme', 'info', 'summary']):
                        is_dicom = True
                
                # Numbered series (.1, .2, .3, etc.) but not headers
                elif '.' in filename and filename.split('.')[-1].isdigit() and 'header' not in filename_lower:
                    is_dicom = True
                
                # Try to detect DICOM by reading file header
                elif file_size > 132:  # DICOM files have at least 132 byte preamble
                    # Skip files that are clearly not DICOM
                    if not any(exclude in filename_lower for exclude in ['header', 'readme', 'info', 'summary', 'text', 'log']):
                        try:
                            with open(file_path, 'rb') as f:
                                f.seek(128)  # Skip preamble
                                dicm_tag = f.read(4)
                                if dicm_tag == b'DICM':
                                    is_dicom = True
                        except:
                            pass
                
                if is_dicom:
                    dicom_files.append(file_path)
        
        
        # Sort files for proper series order
        dicom_files.sort()

        
        return dicom_files
        
    except Exception as e:
        pass
        return []

def test_philips_detection(dicom_path):
    """
    Test Philips DICOM detection for a given directory.
    Usage: test_philips_detection(r"C:\\Users\\username\\Desktop\\DICOM_folder")
    """
    
    if not os.path.exists(dicom_path):
        return False
    
    try:
        # Find DICOM files
        dicom_files = _find_dicom_files_in_directory(dicom_path)
        if not dicom_files:
            return False
        
        
        # Analyze files
        analysis = _analyze_dicom_files(dicom_files)
        
        if analysis.get('is_philips', False):
            return True
        else:
            return False
            
    except Exception as e:
        return False

def load_philips_dicom_simple(dicom_path):
    """
    Load Philips DICOM using the exact user's working method.
    This is a direct copy of the user's proven script.
    """
    try:
        import DICOMLib
        from DICOMLib import DICOMUtils
        import slicer

        dicomDataDir = dicom_path

        # Import DICOM directory (ignores unreadable files like v_headers)
        DICOMUtils.importDicom(dicomDataDir)

        # Access the Slicer DICOM database instance
        db = slicer.dicomDatabase

        # Get all patient UIDs in the database
        patientUIDs = db.patients()

        if len(patientUIDs) == 0:
            return None
        else:
            firstPatientUID = patientUIDs[0]
            DICOMUtils.loadPatientByUID(firstPatientUID)
            
            # Continue workflow after successful loading
            qt.QTimer.singleShot(1000, start_with_volume_crop)
            
            # Return success
            return True
            
    except Exception as e:
        return None

def test_philips_dicom_loading(dicom_path):
    """
    Test the complete Philips DICOM loading workflow.
    Usage: test_philips_dicom_loading(r"C:\\Users\\username\\Desktop\\Philips_DICOM_folder")
    """
    
    if not os.path.exists(dicom_path):
        return False
    
    try:
        # Step 1: Test detection
        dicom_files = _find_dicom_files_in_directory(dicom_path)
        if not dicom_files:
            return False
        
        analysis = _analyze_dicom_files(dicom_files)
        
        if not analysis.get('is_philips', False):
            return False
        
        # Step 2: Test Philips loading
        initial_volumes = len(slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode'))
        
        result = _load_philips_dicom_series(dicom_path)
        
        final_volumes = len(slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode'))
        
        if result:
            return True
        else:
            return False
            
    except Exception as e:
        return False

def diagnose_dicom_directory(dicom_path):
    """
    Diagnose what's in a DICOM directory to help troubleshoot loading issues.
    Usage: diagnose_dicom_directory(r"G:\\My Drive\\Lawson\\FOURDIX\\...")
    """
    
    if not os.path.exists(dicom_path) or not os.path.isdir(dicom_path):
        return
    
    try:
        # Get directory structure
        subdirs = []
        total_files = 0
        
        for root, dirs, files in os.walk(dicom_path):
            level = root.replace(dicom_path, '').count(os.sep)
            indent = ' ' * 2 * level
            folder_name = os.path.basename(root) if level > 0 else "ROOT"
            total_files += len(files)
            
            if level == 1:  # First level subdirectories
                subdirs.append(root)
            
            if level > 3:  # Don't go too deep in display
                continue
        
        
        # Analyze DICOM files
        dicom_files = _find_dicom_files_in_directory(dicom_path)
        
        if not dicom_files:
            
            # Suggest looking in subdirectories
            if subdirs:
                for subdir in subdirs[:3]:  # Check first 3 subdirs
                    sub_dicom_files = _find_dicom_files_in_directory(subdir)
                    if sub_dicom_files:
                        break

            
    except Exception as e:
        pass

def test_dicom_loading_with_path(dicom_path):
    """
    Test the enhanced DICOM loading with a specific path.
    Usage: test_dicom_loading_with_path(r"C:\\Users\\username\\Desktop\\DICOM_folder")
    """
    
    if not os.path.exists(dicom_path):
        return False
    
    # Test the enhanced loading function
    try:
        success = load_dicom_from_source_file(dicom_path)
        return success
    except Exception as e:
        pass
        return False

def simple_dicom_load(dicom_path):
    """
    Simplified DICOM loading that bypasses complex database operations.
    Usage: simple_dicom_load(r"G:\\My Drive\\Lawson\\FOURDIX\\...")
    """
    
    if not os.path.exists(dicom_path):
        return False
    
    try:
        # Method 1: Try direct directory loading
        volume_node = slicer.util.loadVolume(dicom_path)
        
        if volume_node:
            image_data = volume_node.GetImageData()
            if image_data:
                dims = image_data.GetDimensions()
            
            set_3d_view_background_black()
            qt.QTimer.singleShot(1000, start_with_volume_crop)
            return True
            
    except Exception as e:
        pass
    
    try:
        # Method 2: Find and load first DICOM file
        dicom_files = _find_dicom_files_in_directory(dicom_path)
        
        if not dicom_files:
            return False
            
        first_file = dicom_files[0]
        
        volume_node = slicer.util.loadVolume(first_file)
        
        if volume_node:
            image_data = volume_node.GetImageData()
            
            set_3d_view_background_black()
            qt.QTimer.singleShot(1000, start_with_volume_crop)
            return True
            
    except Exception as e:
        pass
    
    return False

def _fallback_dicom_loading(dicom_path):
    """
    Fallback DICOM loading when enhanced methods are not available.
    Uses simplified but robust approaches.
    """
    try:
        
        # Method 1: Simple directory loading (try multiple approaches)
        try:
            
            # Try loading the directory directly
            volume_node = slicer.util.loadVolume(dicom_path)
            if volume_node:
                set_3d_view_background_black()
                qt.QTimer.singleShot(1000, start_with_volume_crop)
                return True
                
        except Exception as e:
            pass
            
            # Try loading subdirectories if main directory fails
            try:
                pass
                subdirs = [d for d in os.listdir(dicom_path) if os.path.isdir(os.path.join(dicom_path, d))]
                
                for subdir in subdirs:
                    subdir_path = os.path.join(dicom_path, subdir)
                    pass
                    
                    try:
                        volume_node = slicer.util.loadVolume(subdir_path)
                        if volume_node:
                            pass
                            set_3d_view_background_black()
                            qt.QTimer.singleShot(1000, start_with_volume_crop)
                            return True
                    except Exception as subdir_error:
                        pass
                        continue
                        
            except Exception as subdir_scan_error:
                pass
        
        # Method 2: Enhanced directory analysis and direct loading
        try:
            
            # Analyze directory for DICOM files
            dicom_files = []
            for root, dirs, files in os.walk(dicom_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_lower = file.lower()
                    
                    # Enhanced DICOM file detection
                    is_dicom = (
                        file_lower.endswith(('.dcm', '.dicom', '.ima')) or
                        ('.' not in file and len(file) > 3) or  # Files without extension
                        file_lower.startswith(('i', 'ima', 'dicom')) or
                        'ctdc' in file_lower or
                        ('.' in file and file.split('.')[-1].isdigit())  # .1, .2, .3 files
                    )
                    
                    if is_dicom:
                        dicom_files.append(file_path)
            
            
            if dicom_files:
                # Sort files for proper series order
                dicom_files.sort()
                
                # Try to load using directory path first
                try:
                    # Use parent directory for series loading
                    parent_dir = os.path.dirname(dicom_files[0])
                    volume_node = slicer.util.loadVolume(parent_dir)
                    
                    if volume_node:
                        set_3d_view_background_black()
                        qt.QTimer.singleShot(1000, start_with_volume_crop)
                        return True
                except Exception as dir_load_error:
                    pass
                
                # Try loading first file (may only get single slice)
                try:
                    volume_node = slicer.util.loadVolume(dicom_files[0])
                    if volume_node:
                        set_3d_view_background_black()
                        qt.QTimer.singleShot(1000, start_with_volume_crop)
                        return True
                except Exception as file_load_error:
                    pass
                                
        except Exception as e:
            pass
            
        # Method 3: Try using Slicer's DICOM database directly (safer approach)
        try:
            
            # Clear any existing data
            current_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
            initial_count = len(current_nodes)
            
            # Open DICOM module
            slicer.util.selectModule("DICOM")
            slicer.app.processEvents()
            
            # Try to get DICOM database and add directory
            dicom_db = None
            try:
                if hasattr(slicer, 'dicomDatabase'):
                    dicom_db = slicer.dicomDatabase
                elif hasattr(slicer.modules, 'dicom'):
                    dicom_module = slicer.modules.dicom
                    if hasattr(dicom_module, 'logic'):
                        dicom_logic = dicom_module.logic()
                        if hasattr(dicom_logic, 'database'):
                            dicom_db = dicom_logic.database
            except:
                dicom_db = None
                
            if dicom_db:
                
                # Initialize database if needed
                if hasattr(dicom_db, 'initializeDatabase'):
                    dicom_db.initializeDatabase()
                
                # Try to import using the database's own methods
                try:
                    # Import files to database
                    import glob
                    all_files = glob.glob(os.path.join(dicom_path, '**', '*'), recursive=True)
                    dicom_files = [f for f in all_files if os.path.isfile(f)]
                    
                    
                    if dicom_files:
                        # Try loading a representative file to trigger series detection
                        test_file = dicom_files[0]
                        
                        # Use Slicer's own loading logic
                        volume_node = slicer.util.loadVolume(test_file)
                        
                        if volume_node:
                            
                            # Check if we got more than one slice
                            image_data = volume_node.GetImageData()
                            if image_data:
                                dims = image_data.GetDimensions()
    
                            
                            set_3d_view_background_black()
                            qt.QTimer.singleShot(1000, start_with_volume_crop)
                            return True
                            
                except Exception as db_import_error:
                    pass
            else:
                
                # Method 4: Direct Slicer loading without database
                try:
                    # Find DICOM files and try loading with Slicer's built-in methods
                    dicom_files = _find_dicom_files_in_directory(dicom_path)
                    
                    if dicom_files:
                        
                        # Try loading the first file (should trigger series loading)
                        first_file = dicom_files[0]
                        
                        volume_node = slicer.util.loadVolume(first_file)
                        
                        if volume_node:
                            
                            # Check dimensions
                            image_data = volume_node.GetImageData()
                            if image_data:
                                dims = image_data.GetDimensions()

                            
                            set_3d_view_background_black()
                            qt.QTimer.singleShot(1000, start_with_volume_crop)
                            return True
                            
                except Exception as direct_load_error:
                    pass
                    
        except Exception as e:
            pass
        
        return False
        
    except Exception as e:
        pass
        return False

def setup_volume_addition_monitor():
    """
    Monitor for the addition of a volume to the scene, then continue with volume crop workflow.
    """
    try:
        if hasattr(slicer.modules, 'VolumeAdditionMonitorTimer'):
            slicer.modules.VolumeAdditionMonitorTimer.stop()
            slicer.modules.VolumeAdditionMonitorTimer.timeout.disconnect()
            del slicer.modules.VolumeAdditionMonitorTimer
        
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        slicer.modules.BaselineVolumeCount = len(volume_nodes)

        create_volume_waiting_status_widget()
        
        timer = qt.QTimer()
        timer.timeout.connect(check_for_volume_addition)
        timer.start(1000)  # Check every second
        slicer.modules.VolumeAdditionMonitorTimer = timer
        slicer.modules.VolumeMonitorCheckCount = 0
        
    except Exception as e:
        pass

def create_volume_waiting_status_widget():
    """
    Create a status widget to show that the workflow is waiting for volume addition.
    """
    try:
        cleanup_volume_waiting_status_widget()

        status_widget = qt.QWidget()
        status_widget.setWindowTitle("Workflow Status")
        status_widget.setWindowFlags(qt.Qt.WindowStaysOnTopHint | qt.Qt.Tool)

        layout = qt.QVBoxLayout()

        status_label = qt.QLabel("🔄 Waiting for DICOM volume to be loaded...")
        status_label.setStyleSheet("""
            QLabel { 
                background-color: #007bff; 
                color: white; 
                border: none; 
                padding: 15px 20px; 
                font-weight: bold;
                border-radius: 8px;
                margin: 5px;
                font-size: 14px;
                text-align: center;
            }
        """)
        layout.addWidget(status_label)
        
        # Add instructions
        instructions = qt.QLabel("1. Import DICOM data using the DICOM module\n2. Load a volume into the scene\n3. Workflow will continue automatically")
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-size: 12px; padding: 10px; background-color: #f8f9fa; border-radius: 6px;")
        layout.addWidget(instructions)
        
        # Add cancel button
        cancel_button = qt.QPushButton("Cancel Workflow")
        cancel_button.setStyleSheet("""
            QPushButton { 
                background-color: #dc3545; 
                color: white; 
                border: none; 
                padding: 10px 15px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 12px;
            }
            QPushButton:hover { 
                background-color: #c82333; 
            }
        """)
        cancel_button.connect('clicked()', lambda: cancel_volume_waiting())
        layout.addWidget(cancel_button)
        
        status_widget.setLayout(layout)
        status_widget.resize(350, 180)
        
        # Position in top-right corner
        main_window = slicer.util.mainWindow()
        if main_window:
            main_geometry = main_window.geometry()
            status_widget.move(main_geometry.right() - 370, main_geometry.top() + 100)
        
        status_widget.show()
        
        # Store reference
        slicer.modules.VolumeWaitingStatusWidget = status_widget
        slicer.modules.VolumeWaitingStatusLabel = status_label
        
        pass
        
    except Exception as e:
        pass

def update_volume_waiting_status(message):
    """
    Update the status message in the volume waiting widget.
    """
    try:
        if hasattr(slicer.modules, 'VolumeWaitingStatusLabel'):
            label = slicer.modules.VolumeWaitingStatusLabel
            if label:
                label.setText(message)
    except Exception as e:
        pass

def cleanup_volume_waiting_status_widget():
    """
    Clean up the volume waiting status widget.
    """
    try:
        if hasattr(slicer.modules, 'VolumeWaitingStatusWidget'):
            widget = slicer.modules.VolumeWaitingStatusWidget
            if widget:
                widget.close()
                widget.setParent(None)
            del slicer.modules.VolumeWaitingStatusWidget
        
        if hasattr(slicer.modules, 'VolumeWaitingStatusLabel'):
            del slicer.modules.VolumeWaitingStatusLabel
            
    except Exception as e:
        pass

def cancel_volume_waiting():
    """
    Cancel the volume waiting workflow.
    """
    try:
        pass
        stop_volume_addition_monitoring()
        cleanup_volume_waiting_status_widget()
        pass
    except Exception as e:
        pass

def check_for_volume_addition():
    """
    Check if a new volume has been added to the scene.
    """
    try:
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        current_count = len(volume_nodes)
        
        slicer.modules.VolumeMonitorCheckCount += 1
        
        if slicer.modules.VolumeMonitorCheckCount % 5 == 0:
            update_volume_waiting_status(f"Waiting for volume... ({slicer.modules.VolumeMonitorCheckCount}s)")
        if current_count > slicer.modules.BaselineVolumeCount:
            update_volume_waiting_status("Volume detected! Continuing workflow...")

            # Set 3D view background to dark as soon as volume is detected
            set_3d_view_background_black()

            stop_volume_addition_monitoring()
            if volume_nodes:
                latest_volume = volume_nodes[-1]
            
            qt.QTimer.singleShot(2000, cleanup_volume_waiting_status_widget)
            # Start crop workflow directly when volume is detected
            qt.QTimer.singleShot(500, start_with_volume_crop)
            
    except Exception as e:
        pass

def stop_volume_addition_monitoring():
    """
    Stop monitoring for volume addition.
    """
    try:
        if hasattr(slicer.modules, 'VolumeAdditionMonitorTimer'):
            timer = slicer.modules.VolumeAdditionMonitorTimer
            timer.stop()
            timer.timeout.disconnect()
            del slicer.modules.VolumeAdditionMonitorTimer

        if hasattr(slicer.modules, 'BaselineVolumeCount'):
            del slicer.modules.BaselineVolumeCount
        if hasattr(slicer.modules, 'VolumeMonitorCheckCount'):
            del slicer.modules.VolumeMonitorCheckCount
        
        cleanup_volume_waiting_status_widget()
            
    except Exception as e:
        pass

def start_markup_workflow():
    """
    Start the workflow with crop first, then markup import after ROI is set
    """
    try:
        # Start with crop workflow - markup dialog will appear after ROI is set
        start_with_volume_crop()
    except Exception as e:
        pass
        # Fallback to the original function if needed
        create_threshold_segment_with_markup_only()

def start_crop_workflow_directly():
    """
    Start the crop workflow directly without showing segmentation dialog again
    """
    # Collapse the left module panel at workflow start to maximize view space
    collapse_left_module_panel()
    
    # Set 3D view background to black at the start of workflow
    set_3d_view_background_black()
    
    # Set three-up view (Red, Green, Yellow) before cropping
    set_three_up_view()
    
    volume_node = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    
    # Use custom crop interface instead of standard module
    create_initial_custom_crop_interface()

def start_workflow_with_segmentation_dialog():
    """
    Start the workflow by first showing the segmentation import dialog, then continuing accordingly
    """
    try:
        # Call the main workflow function which now includes segmentation import dialog
        create_threshold_segment()
    except Exception as e:
        pass
        # Fallback to original crop workflow if dialog fails
        start_with_volume_crop()

def start_with_volume_crop():
    """
    Start the workflow using the custom crop interface instead of the standard crop module.
    """
    # Collapse the left module panel at workflow start to maximize view space
    collapse_left_module_panel()
    
    # Set 3D view background to black at the start of workflow
    set_3d_view_background_black()
    
    # Set three-up view (Red, Green, Yellow) before cropping
    set_three_up_view()
    
    volume_node = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    
    # Use custom crop interface instead of standard module
    create_initial_custom_crop_interface()
    
    volume_node = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    
    # Use custom crop interface instead of standard module
    create_initial_custom_crop_interface()
    return
    
    roi_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode", "CropROI")
    
    bounds = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    volume_node.GetBounds(bounds)
    
    center = [
        (bounds[0] + bounds[1]) / 2.0,
        (bounds[2] + bounds[3]) / 2.0,
        (bounds[4] + bounds[5]) / 2.0
    ]
    
    size = [
        bounds[1] - bounds[0],
        bounds[3] - bounds[2],
        bounds[5] - bounds[4]
    ]
    
    roi_node.SetCenter(center)
    roi_node.SetSize(size)
    
    pass
    
    crop_widget = slicer.modules.cropvolume.widgetRepresentation()
    if crop_widget and hasattr(crop_widget, 'self'):
        crop_module = crop_widget.self()
        if hasattr(crop_module.ui, 'inputSelector'):
            crop_module.ui.inputSelector.setCurrentNode(volume_node)
        if hasattr(crop_module.ui, 'roiSelector'):
            crop_module.ui.roiSelector.setCurrentNode(roi_node)
    
    display_node = roi_node.GetDisplayNode()
    if display_node:
        display_node.SetVisibility(True)
        display_node.SetHandlesInteractive(True)
        display_node.SetColor(1.0, 1.0, 0.0)
        display_node.SetSelectedColor(1.0, 0.5, 0.0)
    
    pass
    
    slicer.app.processEvents()
    
    add_large_crop_apply_button()
    
    qt.QTimer.singleShot(2000, add_large_crop_apply_button)
    
    pass
    
    setup_crop_completion_monitor(volume_node)

def setup_crop_completion_monitor(original_volume_node):
    """
    Monitor for the creation of a new cropped volume, then delete the original and continue.
    """
    if hasattr(slicer.modules, 'CropMonitorTimer'):
        slicer.modules.CropMonitorTimer.stop()
        slicer.modules.CropMonitorTimer.timeout.disconnect()
        del slicer.modules.CropMonitorTimer
    timer = qt.QTimer()
    timer.setInterval(2000)
    timer.timeout.connect(lambda: check_crop_completion(original_volume_node))
    timer.start()
    slicer.modules.CropMonitorTimer = timer
    slicer.modules.CropCheckCount = 0

def check_crop_completion(original_volume_node):
    """
    Check if a new cropped volume exists, then delete the original, ROI, and continue.
    """
    slicer.modules.CropCheckCount += 1
    volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
    for node in volume_nodes:
        if node is not original_volume_node and 'crop' in node.GetName().lower():
            slicer.modules.CropMonitorTimer.stop()
            slicer.modules.CropMonitorTimer.timeout.disconnect()
            del slicer.modules.CropMonitorTimer
            del slicer.modules.CropCheckCount
            original_volume_node.SetDisplayVisibility(False)
            

            layout_manager = slicer.app.layoutManager()
            slice_view_names = ['Red', 'Yellow', 'Green']
            
            for slice_view_name in slice_view_names:
                slice_widget = layout_manager.sliceWidget(slice_view_name)
                if slice_widget:
                    slice_logic = slice_widget.sliceLogic()
                    if slice_logic:
                        composite_node = slice_logic.GetSliceCompositeNode()
                        if composite_node and composite_node.GetBackgroundVolumeID() == original_volume_node.GetID():
                            composite_node.SetBackgroundVolumeID(None)
            slicer.modules.WorkflowOriginalVolume = original_volume_node
            slicer.modules.WorkflowCroppedVolume = node
            
            set_cropped_volume_visible(node)
            
            roi_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsROINode')
            for roi_node in roi_nodes:
                if 'crop' in roi_node.GetName().lower():
                    slicer.mrmlScene.RemoveNode(roi_node)
                    pass
            
            # Disable the crop apply button from the Crop Volume module now that cropping is complete
            try:
                crop_widget = slicer.modules.cropvolume.widgetRepresentation()
                if crop_widget:
                    disable_crop_apply_button(crop_widget)
                    # Set flag to prevent button restoration
                    slicer.modules.WorkflowCropCompleted = True
            except Exception as e:
                pass
            
            # Switch to 3D-only view after cropping is complete
            qt.QTimer.singleShot(500, set_3d_only_view)
            
            pass
            create_threshold_segment()
            return


def set_cropped_volume_visible(cropped_volume):
    """
    Set the cropped volume as visible and active in all slice views
    """
    try:
        if not cropped_volume.GetDisplayNode():
            cropped_volume.CreateDefaultDisplayNodes()
        
        selection_node = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selection_node:
            selection_node.SetActiveVolumeID(cropped_volume.GetID())
            selection_node.SetSecondaryVolumeID(None)
        
        layout_manager = slicer.app.layoutManager()
        slice_view_names = ['Red', 'Yellow', 'Green']
        
        for slice_view_name in slice_view_names:
            slice_widget = layout_manager.sliceWidget(slice_view_name)
            if slice_widget:
                slice_logic = slice_widget.sliceLogic()
                if slice_logic:
                    slice_logic.GetSliceCompositeNode().SetBackgroundVolumeID(cropped_volume.GetID())
                    slice_logic.GetSliceCompositeNode().SetForegroundVolumeID(None)
                    slice_logic.FitSliceToAll()
        
        for slice_view_name in slice_view_names:
            slice_widget = layout_manager.sliceWidget(slice_view_name)
            if slice_widget:
                slice_view = slice_widget.sliceView()
                slice_view.forceRender()
        
        slicer.app.processEvents()
        
        pass
        return True
        
    except Exception as e:
        pass
        return False


def prompt_for_endpoints():
    """
    Simplified prompt for centerline extraction
    """
    try:
        pass
        pass
        
    except Exception as e:
        pass
        pass

def setup_centerline_completion_monitor():
    """
    Set up monitoring to detect when centerline extraction completes
    """
    try:
        stop_centerline_monitoring()

        # Clear the dialog shown flag for new extraction cycle
        if hasattr(slicer.modules, 'CenterlineDialogShown'):
            del slicer.modules.CenterlineDialogShown
            pass

        # Store baseline count of centerlines before monitoring starts
        current_models = find_all_centerline_models()
        current_curves = find_all_centerline_curves()
        slicer.modules.BaselineCenterlineModelCount = len(current_models)
        slicer.modules.BaselineCenterlineCurveCount = len(current_curves)

        timer = qt.QTimer()
        timer.timeout.connect(check_centerline_completion)
        timer.start(2000)
        slicer.modules.CenterlineMonitorTimer = timer
        slicer.modules.CenterlineCheckCount = 0
        slicer.modules.CenterlineMonitoringStartTime = time.time()
        pass
        
    except Exception as e:
        pass

def check_specific_centerline_completion():
    """
    Check if specific target centerlines now have sufficient data for dialog
    """
    try:
        if hasattr(slicer.modules, 'CenterlineCheckCount'):
            slicer.modules.CenterlineCheckCount += 1
        
        # Check if a dialog has already been shown for this extraction cycle
        if hasattr(slicer.modules, 'CenterlineDialogShown') and slicer.modules.CenterlineDialogShown:
            pass
            stop_centerline_monitoring()
            return
        
        # Get target centerlines to check
        target_model_ids = getattr(slicer.modules, 'TargetCenterlineModels', [])
        target_curve_ids = getattr(slicer.modules, 'TargetCenterlineCurves', [])
        
        if not target_model_ids and not target_curve_ids:
            pass
            stop_centerline_monitoring()
            return
        
        # Find the target nodes
        all_models = find_all_centerline_models()
        all_curves = find_all_centerline_curves()
        
        target_models = [model for model in all_models if model.GetID() in target_model_ids]
        target_curves = [curve for curve in all_curves if curve.GetID() in target_curve_ids]
        
        pass
        
        # Check if any target centerlines now have sufficient data
        best_model = None
        best_curve = None
        
        for model in target_models:
            polydata = model.GetPolyData()
            if polydata and polydata.GetNumberOfPoints() > 10:  # Require at least 10 points
                if not best_model or polydata.GetNumberOfPoints() > best_model.GetPolyData().GetNumberOfPoints():
                    best_model = model
                    pass
        
        for curve in target_curves:
            if curve.GetNumberOfControlPoints() > 5:  # Require at least 5 control points
                if not best_curve or curve.GetNumberOfControlPoints() > best_curve.GetNumberOfControlPoints():
                    best_curve = curve
                    pass
        
        if best_model or best_curve:
            pass
            
            # Mark that we're showing a dialog for this extraction cycle
            slicer.modules.CenterlineDialogShown = True
            
            stop_centerline_monitoring()
            show_centerline_completion_dialog(best_model, best_curve)
        
    except Exception as e:
        pass

def check_centerline_completion():
    """
    Check if centerline extraction has completed and switch to CPR module
    """
    try:
        if hasattr(slicer.modules, 'CenterlineCheckCount'):
            slicer.modules.CenterlineCheckCount += 1
        baseline_model_count = getattr(slicer.modules, 'BaselineCenterlineModelCount', 0)
        baseline_curve_count = getattr(slicer.modules, 'BaselineCenterlineCurveCount', 0)
        current_models = find_all_centerline_models()
        current_curves = find_all_centerline_curves()
        
        # Look for new centerlines with substantial data
        new_centerline_model = None
        new_centerline_curve = None
        
        if len(current_models) > baseline_model_count:
            # Check the newest models for substantial data - slice from the end to get new ones
            new_models_slice = current_models[baseline_model_count:]
            for model in new_models_slice:
                polydata = model.GetPolyData()
                if polydata and polydata.GetNumberOfPoints() > 10:  # Require at least 10 points
                    new_centerline_model = model
                    pass
                    break
        
        if len(current_curves) > baseline_curve_count:
            # Check the newest curves for substantial data - slice from the end to get new ones
            new_curves_slice = current_curves[baseline_curve_count:]
            for curve in new_curves_slice:
                if curve.GetNumberOfControlPoints() > 5:  # Require at least 5 control points
                    new_centerline_curve = curve
                    pass
                    break
        
        if new_centerline_model or new_centerline_curve:
            pass
            
            # Backup the original centerline for potential reset functionality
            if new_centerline_curve and new_centerline_curve.GetNumberOfControlPoints() > 0:
                backup_centerline_points(new_centerline_curve)
            
            # Check if a dialog has already been shown for this extraction cycle
            if hasattr(slicer.modules, 'CenterlineDialogShown') and slicer.modules.CenterlineDialogShown:
                pass
                stop_centerline_monitoring()
                return
            
            # Mark that we're showing a dialog for this extraction cycle
            slicer.modules.CenterlineDialogShown = True
            
            stop_centerline_monitoring()
            show_centerline_completion_dialog(new_centerline_model, new_centerline_curve)
        
    except Exception as e:
        pass

def get_current_centerline_for_placement():
    """
    Get the centerline that should be used for point placement based on the most recently used centerline for CPR.
    Returns tuple (centerline_model, centerline_curve) where either may be None.
    """
    try:
        centerline_model = None
        centerline_curve = None
        
        # First check if we have stored references from CPR module usage
        if hasattr(slicer.modules, 'WorkflowCenterlineModel'):
            stored_model = slicer.modules.WorkflowCenterlineModel
            # Verify the stored model still exists in the scene
            if stored_model and stored_model.GetScene() == slicer.mrmlScene:
                centerline_model = stored_model
        
        if hasattr(slicer.modules, 'WorkflowCenterlineCurve'):
            stored_curve = slicer.modules.WorkflowCenterlineCurve
            # Verify the stored curve still exists in the scene
            if stored_curve and stored_curve.GetScene() == slicer.mrmlScene:
                centerline_curve = stored_curve
        
        # If no valid stored references, find the most recent centerline
        if not centerline_model:
            centerline_model = find_recent_centerline_model()
            if centerline_model:
                slicer.modules.WorkflowCenterlineModel = centerline_model
        
        if not centerline_curve:
            centerline_curve = find_recent_centerline_curve()
            if centerline_curve:
                slicer.modules.WorkflowCenterlineCurve = centerline_curve
        
        return centerline_model, centerline_curve
        
    except Exception as e:
        pass
        return None, None

def ensure_point_placement_uses_current_centerline(point_list):
    """
    Ensure that the point list references the most recently used centerline for CPR.
    This ensures pre/post start/stop points are placed based on the correct centerline.
    """
    try:
        if not point_list:
            return False
        
        centerline_model, centerline_curve = get_current_centerline_for_placement()
        
        # Store references in the point list for consistency
        if centerline_model:
            try:
                point_list.ReferenceCenterlineModel = centerline_model
                pass  # Stored centerline model reference
            except:
                pass
        
        if centerline_curve:
            try:
                point_list.ReferenceCenterlineCurve = centerline_curve
                pass  # Stored centerline curve reference
            except:
                pass
        
        return (centerline_model is not None) or (centerline_curve is not None)
        
    except Exception as e:
        pass
        return False

def find_recent_centerline_model(created_after=0):
    """
    Find the most recently created centerline model with sufficient data
    """
    try:
        model_nodes = slicer.util.getNodesByClass('vtkMRMLModelNode')
        centerline_models = []
        for model in model_nodes:
            model_name = model.GetName().lower()
            if any(keyword in model_name for keyword in ['centerline', 'tree', 'vessel']):
                if model.GetMTime() > created_after:
                    polydata = model.GetPolyData()
                    if polydata and polydata.GetNumberOfPoints() > 10:
                        centerline_models.append(model)
                        pass
        
        if centerline_models:
            centerline_models.sort(key=lambda x: x.GetMTime(), reverse=True)
            return centerline_models[0]
        
        return None
        
    except Exception as e:
        pass
        return None

def find_all_centerline_models():
    """
    Find all centerline models in the scene
    """
    try:
        model_nodes = slicer.util.getNodesByClass('vtkMRMLModelNode')
        centerline_models = []
        for model in model_nodes:
            model_name = model.GetName().lower()
            if any(keyword in model_name for keyword in ['centerline', 'tree', 'vessel']):
                polydata = model.GetPolyData()
                if polydata and polydata.GetNumberOfPoints() > 0:
                    centerline_models.append(model)
        
        centerline_models.sort(key=lambda x: x.GetMTime(), reverse=True)
        return centerline_models
        
    except Exception as e:
        pass
        return []

def find_recent_centerline_curve(created_after=0):
    """
    Find the most recently created centerline curve with sufficient data
    """
    try:
        curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsCurveNode')
        centerline_curves = []
        for curve in curve_nodes:
            curve_name = curve.GetName().lower()
            if any(keyword in curve_name for keyword in ['centerline', 'curve', 'vessel']):
                # Check if curve was created after the specified time
                if curve.GetMTime() > created_after:
                    # Only consider curves with substantial data (more than just endpoint markers)
                    if curve.GetNumberOfControlPoints() > 5:
                        centerline_curves.append(curve)
                        pass
        
        if centerline_curves:
            centerline_curves.sort(key=lambda x: x.GetMTime(), reverse=True)
            return centerline_curves[0]
        
        return None
        
    except Exception as e:
        pass
        return None

def find_all_centerline_curves():
    """
    Find all centerline curves in the scene
    """
    try:
        curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsCurveNode')
        centerline_curves = []
        for curve in curve_nodes:
            curve_name = curve.GetName().lower()
            if any(keyword in curve_name for keyword in ['centerline', 'curve', 'vessel']):
                if curve.GetNumberOfControlPoints() > 0:
                    centerline_curves.append(curve)
        
        # Sort by creation time (most recent first)
        centerline_curves.sort(key=lambda x: x.GetMTime(), reverse=True)
        return centerline_curves
        
    except Exception as e:
        pass
        return []

def find_nearest_centerline_to_point(point_position):
    """
    Find the centerline model closest to a given point position.
    Returns the centerline model and the distance to its closest point.
    """
    try:
        all_models = find_all_centerline_models()
        if not all_models:
            return None, float('inf')
        
        nearest_model = None
        min_distance = float('inf')
        
        for model in all_models:
            try:
                points = slicer.util.arrayFromModelPoints(model)
                if points is None or len(points) == 0:
                    continue
                
                # Find closest point on this centerline
                for p in points:
                    distance = ((point_position[0] - p[0])**2 + 
                               (point_position[1] - p[1])**2 + 
                               (point_position[2] - p[2])**2) ** 0.5
                    if distance < min_distance:
                        min_distance = distance
                        nearest_model = model
                        
            except Exception as e:
                continue
        
        return nearest_model, min_distance
        
    except Exception as e:
        return None, float('inf')

def populate_centerline_dropdown():
    """
    Populate the centerline dropdown with available centerlines
    """
    try:
        centerline_combo = getattr(slicer.modules, 'WorkflowCenterlineCombo', None)
        if not centerline_combo:
            return
        
        # Clear existing items
        centerline_combo.clear()
        
        # Add a default option
        centerline_combo.addItem("Auto-select most recent", None)
        
        # Get all available centerlines
        all_models = find_all_centerline_models()
        all_curves = find_all_centerline_curves()
        
        # Add centerline models
        for model in all_models:
            display_name = f"Model: {model.GetName()}"
            centerline_combo.addItem(display_name, model)
        
        # Add centerline curves
        for curve in all_curves:
            display_name = f"Curve: {curve.GetName()}"
            centerline_combo.addItem(display_name, curve)
        
        # If no centerlines found, add a message
        if not all_models and not all_curves:
            centerline_combo.addItem("No centerlines found", None)
        
    except Exception as e:
        pass
        pass

def stop_centerline_monitoring():
    """
    Stop the centerline completion monitoring
    """
    try:
        if hasattr(slicer.modules, 'CenterlineMonitorTimer'):
            timer = slicer.modules.CenterlineMonitorTimer
            timer.stop()
            timer.timeout.disconnect()
            del slicer.modules.CenterlineMonitorTimer
            
        if hasattr(slicer.modules, 'CenterlineCheckCount'):
            del slicer.modules.CenterlineCheckCount
            
        if hasattr(slicer.modules, 'CenterlineMonitoringStartTime'):
            del slicer.modules.CenterlineMonitoringStartTime
            
        # Clean up baseline counts
        if hasattr(slicer.modules, 'BaselineCenterlineModelCount'):
            del slicer.modules.BaselineCenterlineModelCount
            
        if hasattr(slicer.modules, 'BaselineCenterlineCurveCount'):
            del slicer.modules.BaselineCenterlineCurveCount
        
        # Clean up target centerline tracking
        if hasattr(slicer.modules, 'TargetCenterlineModels'):
            del slicer.modules.TargetCenterlineModels
            
        if hasattr(slicer.modules, 'TargetCenterlineCurves'):
            del slicer.modules.TargetCenterlineCurves
            
        # Reset monitoring button if it exists
        if hasattr(slicer.modules, 'CenterlineMonitoringButton'):
            button = slicer.modules.CenterlineMonitoringButton
            if button:
                button.setText("Start Auto-Monitoring")
                button.setEnabled(True)
                button.setStyleSheet("""
                    QPushButton { 
                        background-color: #6f42c1; 
                        color: white; 
                        border: none; 
                        padding: 10px 15px; 
                        font-weight: bold;
                        border-radius: 6px;
                        margin: 5px;
                        font-size: 12px;
                        min-width: 150px;
                    }
                    QPushButton:hover { 
                        background-color: #5a32a3; 
                    }
                    QPushButton:pressed { 
                        background-color: #4e2a8e; 
                    }
                """)
            
        pass
        
    except Exception as e:
        pass

def hide_threshold_segmentation_mask():
    """
    Hide threshold segmentation masks of the form ThresholdSegmentation_XXX.X_XXXX.X
    after the CPR module is opened
    """
    try:
        # Find all segmentation nodes
        segmentation_nodes = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
        
        for seg_node in segmentation_nodes:
            node_name = seg_node.GetName()
            
            # Check if node name matches the pattern ThresholdSegmentation_XXX.X_XXXX.X
            if node_name.startswith("ThresholdSegmentation_") and "_" in node_name:
                
                # Hide the segmentation node
                display_node = seg_node.GetDisplayNode()
                if display_node:
                    # Hide in 2D views
                    display_node.SetVisibility2D(False)
                    # Hide in 3D views
                    display_node.SetVisibility3D(False)
                    # Hide overall visibility
                    display_node.SetVisibility(False)
                    
                    # Also hide individual segments
                    segmentation = seg_node.GetSegmentation()
                    if segmentation:
                        for i in range(segmentation.GetNumberOfSegments()):
                            segment_id = segmentation.GetNthSegmentID(i)
                            display_node.SetSegmentVisibility2D(segment_id, False)
                            display_node.SetSegmentVisibility3D(segment_id, False)
                            display_node.SetSegmentVisibility(segment_id, False)
            
        
        # Force refresh of slice views
        slicer.app.processEvents()
        
    except Exception as e:
        pass

def switch_to_cpr_module(centerline_model=None, centerline_curve=None):
    """
    Switch to Curved Planar Reformat module and configure it with the centerline.
    Stores centerline references to ensure subsequent point placement uses the correct centerline.
    """
    try:
        # Store references to centerline nodes for later transform application and point placement
        if centerline_model:
            slicer.modules.WorkflowCenterlineModel = centerline_model
            pass  # Stored centerline model reference for CPR and point placement
        if centerline_curve:
            slicer.modules.WorkflowCenterlineCurve = centerline_curve
            pass  # Stored centerline curve reference for CPR and point placement
        
        # If no specific centerlines provided, try to find and store the most recent ones
        if not centerline_model and not centerline_curve:
            recent_model = find_recent_centerline_model()
            recent_curve = find_recent_centerline_curve()
            
            if recent_model:
                slicer.modules.WorkflowCenterlineModel = recent_model
                centerline_model = recent_model
                pass  # Found and stored recent centerline model
            
            if recent_curve:
                slicer.modules.WorkflowCenterlineCurve = recent_curve
                centerline_curve = recent_curve
                pass  # Found and stored recent centerline curve
        
        slicer.util.selectModule("CurvedPlanarReformat")
        pass
        slicer.app.processEvents()
        
        # Hide slice size controls from CPR module UI
        hide_cpr_slice_size_controls()

    # Switch to Red|Green slice-only layout
        show_red_green_views_only()
        
        # Hide threshold segmentation mask after opening CPR module
        hide_threshold_segmentation_mask()
        
        setup_cpr_module()
        create_point_list_and_prompt()
        
        qt.QTimer.singleShot(1000, add_large_cpr_apply_button)
        
        qt.QTimer.singleShot(3000, auto_apply_cpr)
        
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not open Curved Planar Reformat module: {str(e)}")

def auto_apply_cpr():
    """
    Automatically apply the CPR processing while keeping the module open for re-application
    """
    try:
        pass
        
        cpr_widget = slicer.modules.curvedplanarreformat.widgetRepresentation()
        if not cpr_widget:
            pass
            return
        
        cpr_module = None
        if hasattr(cpr_widget, 'self'):
            cpr_module = cpr_widget.self()
        
        if not cpr_module:
            pass
            return
        
        apply_button = None
        
        if hasattr(cpr_module, 'ui') and hasattr(cpr_module.ui, 'applyButton'):
            apply_button = cpr_module.ui.applyButton
            pass
        
        if not apply_button and hasattr(slicer.modules, 'CPRLargeApplyButton'):
            apply_button = slicer.modules.CPRLargeApplyButton
            pass
        
        if not apply_button:
            all_buttons = cpr_widget.findChildren(qt.QPushButton)
            for button in all_buttons:
                if button.text.lower() == 'apply' and button.isEnabled():
                    apply_button = button
                    pass
                    break
        
        if apply_button and apply_button.isEnabled():
            pass
            apply_button.click()
            
            setup_cpr_completion_monitor()
            
            
        else:
            if not apply_button:
                pass
            else:
                pass
            pass
            
    except Exception as e:
        pass
        pass

def setup_cpr_completion_monitor():
    """
    Monitor for CPR completion to provide user feedback
    """
    try:
        if not hasattr(slicer.modules, 'CPRMonitorTimer'):
            timer = qt.QTimer()
            timer.timeout.connect(check_cpr_completion)
            timer.start(2000)  # Check every 2 seconds
            slicer.modules.CPRMonitorTimer = timer
            slicer.modules.CPRCheckCount = 0
            pass
        
    except Exception as e:
        pass

def check_cpr_completion():
    """
    Check if CPR processing has completed
    """
    try:
        if hasattr(slicer.modules, 'CPRCheckCount'):
            slicer.modules.CPRCheckCount += 1
        straightened_volumes = []
        projected_volumes = []
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        for volume in volume_nodes:
            volume_name = volume.GetName().lower()
            if 'straightened' in volume_name:
                straightened_volumes.append(volume)
            elif 'projected' in volume_name:
                projected_volumes.append(volume)
        
        if straightened_volumes or projected_volumes:
            pass
            if straightened_volumes:
                pass
            if projected_volumes:
                pass
            
            # Create analysis masks on the straightened volume
            create_analysis_masks(straightened_volumes)
            
            stop_cpr_monitoring()
            
        
    except Exception as e:
        pass

def stop_cpr_monitoring():
    """
    Stop the CPR completion monitoring
    """
    try:
        if hasattr(slicer.modules, 'CPRMonitorTimer'):
            timer = slicer.modules.CPRMonitorTimer
            timer.stop()
            timer.timeout.disconnect()
            del slicer.modules.CPRMonitorTimer
            
        if hasattr(slicer.modules, 'CPRCheckCount'):
            del slicer.modules.CPRCheckCount
            
        pass
        
    except Exception as e:
        pass

def setup_cpr_module():
    """
    Set up the Curved Planar Reformat module with the generated centerline and auto-apply
    """
    try:
        cpr_widget = slicer.modules.curvedplanarreformat.widgetRepresentation()
        if cpr_widget:
            cpr_module = cpr_widget.self()

            # First, let the module fully initialize
            slicer.app.processEvents()
            
            # Configure input volume - find the appropriate volume to use
            input_volume = find_working_volume()
            if input_volume:
                pass
                
                # Set input volume selector
                input_volume_set = False
                for input_selector_name in ['inputVolumeSelector', 'sourceVolumeSelector', 'volumeSelector']:
                    if hasattr(cpr_module.ui, input_selector_name):
                        selector = getattr(cpr_module.ui, input_selector_name)
                        
                        # Force refresh the selector's node list
                        if hasattr(selector, 'updateMRMLFromWidget'):
                            selector.updateMRMLFromWidget()
                        
                        # Set the node
                        selector.setCurrentNode(input_volume)
                        
                        # Force update again
                        slicer.app.processEvents()
                        
                        # Verify the selection took effect
                        if selector.currentNode() == input_volume:
                            pass
                            input_volume_set = True
                            break
                        else:
                            pass
                
                if not input_volume_set:
                    pass
                    pass
            else:
                pass
            
            # Configure centerline input - find the most recent centerline
            centerline_model = find_recent_centerline_model()  # Use default created_after=0 to find any existing model
            if centerline_model:
                pass
                
                # Store this as the current centerline for point placement
                slicer.modules.WorkflowCenterlineModel = centerline_model
                
                # Set centerline selector
                centerline_set = False
                for centerline_selector_name in ['inputCenterlineSelector', 'centerlineSelector', 'curveSelector']:
                    if hasattr(cpr_module.ui, centerline_selector_name):
                        selector = getattr(cpr_module.ui, centerline_selector_name)
                        
                        # Force refresh the selector's node list
                        if hasattr(selector, 'updateMRMLFromWidget'):
                            selector.updateMRMLFromWidget()

                        selector.setCurrentNode(centerline_model)
                        slicer.app.processEvents()
            
            # Also check for centerline curves and store reference
            centerline_curve = find_recent_centerline_curve()
            if centerline_curve:
                slicer.modules.WorkflowCenterlineCurve = centerline_curve

            # Configure output nodes and settings
            try:
                # Create new output volume for straightened result
                output_volume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
                output_volume.SetName("Straightened Volume")
                output_volume.CreateDefaultDisplayNodes()
                
                # Create new projected volume
                projected_volume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
                projected_volume.SetName("Projected Volume")
                projected_volume.CreateDefaultDisplayNodes()
                
                # Create new transform node
                transform_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTransformNode")
                transform_node.SetName("Straightening transform")
                
                # Store references for later use
                slicer.modules.WorkflowStraightenedVolume = output_volume
                slicer.modules.WorkflowProjectedVolume = projected_volume
                slicer.modules.WorkflowStraighteningTransform = transform_node
                
                # Process events to ensure nodes are properly added to scene
                slicer.app.processEvents()
                
                # Set the output selectors to the created nodes
                output_volume_set = False
                projected_volume_set = False
                transform_set = False
                
                # Set output straightened volume selector
                if hasattr(cpr_module.ui, 'outputStraightenedVolumeSelector'):
                    cpr_module.ui.outputStraightenedVolumeSelector.setCurrentNode(output_volume)
                    output_volume_set = True
                    pass
                
                # Set output projected volume selector
                if hasattr(cpr_module.ui, 'outputProjectedVolumeSelector'):
                    cpr_module.ui.outputProjectedVolumeSelector.setCurrentNode(projected_volume)
                    projected_volume_set = True
                    pass
                
                # Set output transform selector
                if hasattr(cpr_module.ui, 'outputTransformToStraightenedVolumeSelector'):
                    cpr_module.ui.outputTransformToStraightenedVolumeSelector.setCurrentNode(transform_node)
                    transform_set = True
                    pass
                
                # Set resolution and thickness parameters
                if hasattr(cpr_module.ui, 'curveResolutionSliderWidget'):
                    cpr_module.ui.curveResolutionSliderWidget.setValue(1.0)
                    pass
                
                # Get the slice thickness from the input volume instead of using hardcoded value
                volume_slice_thickness = get_volume_slice_thickness(input_volume)
                
                if hasattr(cpr_module.ui, 'sliceResolutionSliderWidget'):
                    cpr_module.ui.sliceResolutionSliderWidget.setValue(volume_slice_thickness)
                    pass
                
                # Legacy fallback for older parameter names
                if hasattr(cpr_module.ui, 'resolutionSpinBox'):
                    cpr_module.ui.resolutionSpinBox.setValue(volume_slice_thickness)
                    pass
                
                if hasattr(cpr_module.ui, 'thicknessSpinBox'):
                    cpr_module.ui.thicknessSpinBox.setValue(1.0)
                    pass
                
                # Final UI update
                slicer.app.processEvents()
                
                # Report setup status
                pass
                if output_volume_set:
                    pass
                else:
                    pass
                    
                if projected_volume_set:
                    pass
                else:
                    pass
                    
                if transform_set:
                    pass
                else:
                    pass
                
                if not input_volume:
                    pass
                if not centerline_model:
                    pass
                
                pass
                    
            except Exception as e:
                pass

            slicer.app.processEvents()
            
            add_large_cpr_apply_button()

        else:
            pass
            
    except Exception as e:
        pass
            


def create_point_list_and_prompt():
    """
    Create the point placement control interface (without creating an initial point list)
    """
    try:
        create_point_placement_controls()
        

        
        return True
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not create point placement controls: {str(e)}")
        return False

def create_point_placement_controls():
    """
    Create a control widget for point placement with the updated workflow buttons
    """
    try:
        main_window = slicer.util.mainWindow()
        
        dock_widget = qt.QDockWidget("Lesion Analysis Points", main_window)
        dock_widget.setAllowedAreas(qt.Qt.LeftDockWidgetArea | qt.Qt.RightDockWidgetArea)
        dock_widget.setFeatures(qt.QDockWidget.DockWidgetMovable | qt.QDockWidget.DockWidgetFloatable)

        widget_content = qt.QWidget()
        dock_widget.setWidget(widget_content)

        layout = qt.QVBoxLayout(widget_content)

        title_label = qt.QLabel("Lesion Analysis Points")
        title_label.setStyleSheet("QLabel { font-weight: bold; color: #0078d4; margin: 5px; font-size: 16px; }")
        layout.addWidget(title_label)

        instruction_label = qt.QLabel(
            "Place points: 1:test-point → 2:pre-lesion → 3:post-lesion → 4+:start-slice-1,2,3... → N+:end-slice-1,2,3..."
        )
        instruction_label.setStyleSheet("QLabel { color: #333; margin: 5px; }")
        instruction_label.setWordWrap(True)
        layout.addWidget(instruction_label)
        
        count_label = qt.QLabel("Points placed: 0")
        count_label.setStyleSheet("QLabel { color: #666; margin: 5px; font-weight: bold; }")
        layout.addWidget(count_label)
        
        start_button = qt.QPushButton("Start Placing Points")
        start_button.setStyleSheet("""
            QPushButton { 
                background-color: #28a745; 
                color: white; 
                border: none; 
                padding: 12px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 13px;
            }
            QPushButton:hover { 
                background-color: #218838; 
            }
            QPushButton:pressed { 
                background-color: #1e7e34; 
            }
        """)
        
        # Store references for toggle functionality
        slicer.modules.WorkflowStartButton = start_button
        slicer.modules.WorkflowCountLabel = count_label
        
        start_button.connect('clicked()', lambda: toggle_point_placement_mode())
        layout.addWidget(start_button)
        
        # Add Post Branch button
        post_branch_button = qt.QPushButton("Post Branch")
        post_branch_button.setStyleSheet("""
            QPushButton { 
                background-color: #28a745; 
                color: white; 
                border: none; 
                padding: 12px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 13px;
            }
            QPushButton:hover { 
                background-color: #218838; 
            }
            QPushButton:pressed { 
                background-color: #1e7e34; 
            }
        """)
        slicer.modules.WorkflowPostBranchButton = post_branch_button
        post_branch_button.connect('clicked()', lambda: toggle_post_branch_point_placement_mode())
        layout.addWidget(post_branch_button)
        
        # Add Branch button
        branch_button = qt.QPushButton("Branch")
        branch_button.setStyleSheet("""
            QPushButton { 
                background-color: #0078d4; 
                color: white; 
                border: none; 
                padding: 12px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 13px;
            }
            QPushButton:hover { 
                background-color: #006cbe; 
            }
            QPushButton:pressed { 
                background-color: #005a9e; 
            }
        """)
        slicer.modules.WorkflowBranchButton = branch_button
        branch_button.connect('clicked()', lambda: toggle_branch_point_placement_mode())
        layout.addWidget(branch_button)

        
        
        export_button = qt.QPushButton("Export & Continue")
        export_button.setStyleSheet("""
            QPushButton { 
                background-color: #dc3545; 
                color: white; 
                border: none; 
                padding: 12px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 13px;
            }
            QPushButton:hover { 
                background-color: #c82333; 
            }
            QPushButton:pressed { 
                background-color: #bd2130; 
            }
        """)
        export_button.connect('clicked()', lambda: export_project_and_continue())
        layout.addWidget(export_button)
        
        # Add AnalysisMasks toggle button
        masks_toggle_button = qt.QPushButton("Hide AnalysisMasks")
        masks_toggle_button.setStyleSheet("""
            QPushButton { 
                background-color: #17a2b8; 
                color: white; 
                border: none; 
                padding: 12px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 13px;
            }
            QPushButton:hover { 
                background-color: #138496; 
            }
            QPushButton:pressed { 
                background-color: #0f6674; 
            }
        """)
        masks_toggle_button.connect('clicked()', lambda: toggle_analysis_masks_visibility(masks_toggle_button))
        layout.addWidget(masks_toggle_button)
        
        # Store reference to the button for later access
        slicer.modules.AnalysisMasksToggleButton = masks_toggle_button
        
        # Add window level tool toggle button
        window_level_button = qt.QPushButton("Window Level")
        window_level_button.setStyleSheet("""
            QPushButton { 
                background-color: #fd7e14; 
                color: white; 
                border: none; 
                padding: 12px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 13px;
            }
            QPushButton:hover { 
                background-color: #e8680c; 
            }
            QPushButton:pressed { 
                background-color: #d35400; 
            }
            QPushButton:checked { 
                background-color: #d35400; 
                border: 2px solid #bf4f02;
            }
        """)
        window_level_button.setCheckable(True)
        window_level_button.connect('clicked(bool)', lambda checked: toggle_window_level_tool(checked, window_level_button))
        layout.addWidget(window_level_button)
        
        # Store reference to the button for later access
        slicer.modules.WindowLevelToggleButton = window_level_button
        
        # Add stenosis ratio button
        stenosis_button = qt.QPushButton("Add Stenosis Ratio")
        stenosis_button.setStyleSheet("""
            QPushButton { 
                background-color: #6f42c1; 
                color: white; 
                border: none; 
                padding: 12px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 13px;
            }
            QPushButton:hover { 
                background-color: #5a32a3; 
            }
            QPushButton:pressed { 
                background-color: #4c2a85; 
            }
        """)
        stenosis_button.connect('clicked()', lambda: create_stenosis_ratio_measurement())
        layout.addWidget(stenosis_button)
        
        # Add circle management section
        circle_section_label = qt.QLabel("Circle Controls:")
        circle_section_label.setStyleSheet("""
            QLabel { 
                color: #333333; 
                font-weight: bold; 
                font-size: 14px; 
                margin-top: 10px; 
                margin-bottom: 5px; 
            }
        """)
        layout.addWidget(circle_section_label)
        
        # Add circle selection dropdown
        circle_dropdown_label = qt.QLabel("Select Circle:")
        circle_dropdown_label.setStyleSheet("QLabel { color: #666666; font-size: 12px; margin-bottom: 2px; }")
        layout.addWidget(circle_dropdown_label)
        
        circle_dropdown = qt.QComboBox()
        circle_dropdown.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 8px;
                margin: 3px;
                font-size: 12px;
            }
            QComboBox:hover {
                border: 1px solid #0078d4;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666666;
                margin-right: 5px;
            }
        """)
        layout.addWidget(circle_dropdown)
        
        # Add radius slider
        radius_slider_label = qt.QLabel("Circle Radius:")
        radius_slider_label.setStyleSheet("QLabel { color: #666666; font-size: 12px; margin-bottom: 2px; margin-top: 8px; }")
        layout.addWidget(radius_slider_label)
        
        radius_slider = qt.QSlider(qt.Qt.Horizontal)
        radius_slider.setMinimum(5)  # 0.5 * 10 for precision
        radius_slider.setMaximum(100)  # 10.0 * 10 for precision  
        radius_slider.setValue(20)  # Default 2.0 * 10
        radius_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #cccccc;
                height: 6px;
                background: #f0f0f0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #0078d4;
                border: 1px solid #005a9e;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -6px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #106ebe;
            }
        """)
        layout.addWidget(radius_slider)
        
        # Add radius value display
        radius_value_label = qt.QLabel("2.0")
        radius_value_label.setStyleSheet("QLabel { color: #666666; font-size: 11px; text-align: center; }")
        layout.addWidget(radius_value_label)
        
        # Store references for later access
        slicer.modules.WorkflowCircleDropdown = circle_dropdown
        slicer.modules.WorkflowRadiusSlider = radius_slider
        slicer.modules.WorkflowRadiusValueLabel = radius_value_label
        
        # Connect the controls to their functions
        circle_dropdown.connect('currentTextChanged(QString)', lambda text: on_circle_selection_changed(text))
        radius_slider.connect('valueChanged(int)', lambda value: on_radius_slider_changed(value))
        
        # Initialize the dropdown with existing circles
        update_circle_dropdown()
        
        layout.addStretch()
        
        main_window.addDockWidget(qt.Qt.RightDockWidgetArea, dock_widget)
        dock_widget.show()
        
        slicer.modules.PointPlacementDockWidget = dock_widget
        slicer.modules.PointCountLabel = count_label
        
        pass
        
    except Exception as e:
        pass

def update_circle_dropdown():
    """
    Update the circle dropdown with all available circle nodes in the scene
    """
    try:
        dropdown = getattr(slicer.modules, 'WorkflowCircleDropdown', None)
        if not dropdown:
            return
            
        # Clear existing items
        dropdown.clear()
        dropdown.addItem("No circle selected")
        
        # Find all circle nodes (closed curve nodes with "Circle_" prefix)
        circle_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsClosedCurveNode')
        circle_items = []
        
        for node in circle_nodes:
            node_name = node.GetName()
            if node_name.startswith("Circle_"):
                # Extract the readable name (remove "Circle_" prefix)
                display_name = node_name.replace("Circle_", "")
                circle_items.append((display_name, node_name))
        
        # Sort for consistent ordering
        circle_items.sort(key=lambda x: x[0])
        
        # Add items to dropdown
        for display_name, node_name in circle_items:
            dropdown.addItem(display_name, node_name)  # userData stores the full node name
        
        pass
        
    except Exception as e:
        pass

def on_circle_selection_changed(selected_text):
    """
    Handle circle selection change in dropdown
    """
    try:
        dropdown = getattr(slicer.modules, 'WorkflowCircleDropdown', None)
        radius_slider = getattr(slicer.modules, 'WorkflowRadiusSlider', None)
        value_label = getattr(slicer.modules, 'WorkflowRadiusValueLabel', None)
        
        if not dropdown or not radius_slider or not value_label:
            return
            
        if selected_text == "No circle selected":
            return
            
        # Get the full node name from userData
        current_index = dropdown.currentIndex
        if current_index > 0:  # Skip "No circle selected" at index 0
            node_name = dropdown.itemData(current_index)
            if node_name:
                # Find the circle node and calculate its current geometric radius
                circle_node = slicer.util.getNode(node_name)
                if circle_node:
                    radius_value = calculate_circle_radius(circle_node)
                    if radius_value > 0:
                        # Convert radius to slider value (slider is 0.5-10.0 * 10)
                        slider_value = int(radius_value * 10)
                        slider_value = max(5, min(100, slider_value))  # Clamp to range
                        radius_slider.setValue(slider_value)
                        value_label.setText(f"{radius_value:.1f}")
        
        pass
        
    except Exception as e:
        pass

def calculate_circle_radius(circle_node):
    """
    Calculate the actual geometric radius of a circle node from its control points
    """
    try:
        num_points = circle_node.GetNumberOfControlPoints()
        if num_points < 3:
            return 2.0  # Default radius
            
        # Calculate center point
        center_x, center_y, center_z = 0.0, 0.0, 0.0
        for i in range(num_points):
            pos = [0, 0, 0]
            circle_node.GetNthControlPointPosition(i, pos)
            center_x += pos[0]
            center_y += pos[1]
            center_z += pos[2]
        
        center_point = [center_x / num_points, center_y / num_points, center_z / num_points]
        
        # Calculate radius as average distance from center to control points
        total_distance = 0.0
        for i in range(num_points):
            pos = [0, 0, 0]
            circle_node.GetNthControlPointPosition(i, pos)
            import numpy as np
            distance = np.linalg.norm(np.array(pos) - np.array(center_point))
            total_distance += distance
        
        radius = total_distance / num_points
        return max(0.5, min(10.0, radius))  # Clamp to reasonable range
        
    except Exception as e:
        return 2.0  # Default radius on error

def on_radius_slider_changed(slider_value):
    """
    Handle radius slider value change
    """
    try:
        dropdown = getattr(slicer.modules, 'WorkflowCircleDropdown', None)
        value_label = getattr(slicer.modules, 'WorkflowRadiusValueLabel', None)
        
        if not dropdown or not value_label:
            return
            
        # Convert slider value to actual radius (slider is multiplied by 10)
        radius_value = slider_value / 10.0
        value_label.setText(f"{radius_value:.1f}")
        
        # Apply radius to selected circle
        current_index = dropdown.currentIndex
        if current_index > 0:  # Skip "No circle selected" at index 0
            node_name = dropdown.itemData(current_index)
            if node_name:
                circle_node = slicer.util.getNode(node_name)
                if circle_node:
                    apply_radius_to_circle(circle_node, radius_value)
        
        pass
        
    except Exception as e:
        pass

def apply_radius_to_circle(circle_node, radius_value):
    """
    Apply the specified radius to a circle node by scaling its control points
    """
    try:
        if not circle_node:
            return
            
        # Calculate current radius to determine scale factor
        current_radius = calculate_circle_radius(circle_node)
        if current_radius <= 0:
            current_radius = 2.0  # Default fallback
            
        # Calculate scale factor
        scale_factor = radius_value / current_radius
        
        # Get the center point
        num_points = circle_node.GetNumberOfControlPoints()
        if num_points == 0:
            return
            
        # Calculate center point
        center_x, center_y, center_z = 0.0, 0.0, 0.0
        for i in range(num_points):
            pos = [0, 0, 0]
            circle_node.GetNthControlPointPosition(i, pos)
            center_x += pos[0]
            center_y += pos[1]
            center_z += pos[2]
        
        center_point = [center_x / num_points, center_y / num_points, center_z / num_points]
        
        # Scale each control point relative to center
        for i in range(num_points):
            pos = [0, 0, 0]
            circle_node.GetNthControlPointPosition(i, pos)
            
            # Calculate vector from center to point
            vector_x = pos[0] - center_point[0]
            vector_y = pos[1] - center_point[1]
            vector_z = pos[2] - center_point[2]
            
            # Scale the vector
            scaled_vector_x = vector_x * scale_factor
            scaled_vector_y = vector_y * scale_factor
            scaled_vector_z = vector_z  # Don't scale Z to keep circle in plane
            
            # Calculate new position
            new_pos = [
                center_point[0] + scaled_vector_x,
                center_point[1] + scaled_vector_y,
                center_point[2] + scaled_vector_z
            ]
            
            # Update the control point position
            circle_node.SetNthControlPointPosition(i, new_pos)
        
        # Force update
        circle_node.Modified()
        
        pass
        
    except Exception as e:
        pass

def toggle_point_placement_mode():
    """
    Toggle between starting and stopping point placement within the same button
    """
    try:
        # Check if placement is currently active
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        is_placing = False
        
        if interactionNode:
            current_mode = interactionNode.GetCurrentInteractionMode()
            is_placing = (current_mode == interactionNode.Place)
        
        start_button = getattr(slicer.modules, 'WorkflowStartButton', None)
        count_label = getattr(slicer.modules, 'WorkflowCountLabel', None)
        
        if not start_button or not count_label:
            pass  # Button references not found
            return
        
        if not is_placing:
            # Start placement
            start_new_point_list_placement(count_label)
            
            # Update button to "stop" state
            start_button.setText("Stop Placing Points")
            start_button.setStyleSheet("""
                QPushButton { 
                    background-color: #dc3545; 
                    color: white; 
                    border: none; 
                    padding: 12px; 
                    font-weight: bold;
                    border-radius: 6px;
                    margin: 5px;
                    font-size: 13px;
                }
                QPushButton:hover { 
                    background-color: #c82333; 
                }
                QPushButton:pressed { 
                    background-color: #bd2130; 
                }
            """)
        else:
            # Stop placement
            stop_point_placement_mode()
            
            # Update button to "start" state
            start_button.setText("Start Placing Points")
            start_button.setStyleSheet("""
                QPushButton { 
                    background-color: #28a745; 
                    color: white; 
                    border: none; 
                    padding: 12px; 
                    font-weight: bold;
                    border-radius: 6px;
                    margin: 5px;
                    font-size: 13px;
                }
                QPushButton:hover { 
                    background-color: #218838; 
                }
                QPushButton:pressed { 
                    background-color: #1e7e34; 
                }
            """)
            
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not toggle point placement: {str(e)}")

def toggle_post_branch_point_placement_mode():
    """
    Toggle between starting and stopping post branch point placement within the same button
    """
    try:
        # Check if placement is currently active
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        is_placing = False
        
        if interactionNode:
            current_mode = interactionNode.GetCurrentInteractionMode()
            is_placing = (current_mode == interactionNode.Place)
        
        post_branch_button = getattr(slicer.modules, 'WorkflowPostBranchButton', None)
        count_label = getattr(slicer.modules, 'WorkflowCountLabel', None)
        
        if not post_branch_button or not count_label:
            pass  # Button references not found
            return
        
        if not is_placing:
            # Start placement
            start_new_post_branch_point_list_placement(count_label)
            
            # Update button to "stop" state
            post_branch_button.setText("Stop Post Branch")
            post_branch_button.setStyleSheet("""
                QPushButton { 
                    background-color: #dc3545; 
                    color: white; 
                    border: none; 
                    padding: 12px; 
                    font-weight: bold;
                    border-radius: 6px;
                    margin: 5px;
                    font-size: 13px;
                }
                QPushButton:hover { 
                    background-color: #c82333; 
                }
                QPushButton:pressed { 
                    background-color: #bd2130; 
                }
            """)
        else:
            # Stop placement
            stop_post_branch_point_placement_mode()
            
            # Update button to "start" state
            post_branch_button.setText("Post Branch")
            post_branch_button.setStyleSheet("""
                QPushButton { 
                    background-color: #28a745; 
                    color: white; 
                    border: none; 
                    padding: 12px; 
                    font-weight: bold;
                    border-radius: 6px;
                    margin: 5px;
                    font-size: 13px;
                }
                QPushButton:hover { 
                    background-color: #218838; 
                }
                QPushButton:pressed { 
                    background-color: #1e7e34; 
                }
            """)
            
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not toggle post branch point placement: {str(e)}")

def start_new_post_branch_point_list_placement(count_label):
    """
    Create a new post branch point list and start placement mode with continuous placement enabled.
    Uses the current centerline reference (same as main placement system).
    """
    try:
        # First, remove any existing PB-1 nodes to start fresh
        existing_pb1_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for node in existing_pb1_nodes:
            if node.GetName() == "PB-1":
                slicer.mrmlScene.RemoveNode(node)
                pass  # Removed existing PB-1 node
        
        # Also clear any existing post-branch circles from previous runs
        clear_branch_circles()
        
        # Get the current centerline reference (same as main placement system)
        current_centerline_model, current_centerline_curve = get_current_centerline_for_placement()
        
        point_list = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        
        point_list.SetName("PB-1")
        
        # Store reference to the centerline that should be used for this point list
        # This ensures consistent positioning relative to the selected centerline
        if current_centerline_model:
            try:
                point_list.ReferenceCenterlineModel = current_centerline_model
            except:
                pass
        if current_centerline_curve:
            try:
                point_list.ReferenceCenterlineCurve = current_centerline_curve
            except:
                pass
        
        display_node = point_list.GetDisplayNode()
        if display_node:
            display_node.SetGlyphScale(3.0)  # Make points larger
            display_node.SetSelectedColor(1.0, 1.0, 0.0)  # Yellow when selected
            display_node.SetColor(0.0, 1.0, 0.0)  # Green when not selected (Post Branch)
            display_node.SetTextScale(2.0)  # Larger text labels
            display_node.SetVisibility(True)
            display_node.SetPointLabelsVisibility(True)
        
        # Clear any automatically added points that may have been created
        while point_list.GetNumberOfControlPoints() > 0:
            point_list.RemoveNthControlPoint(0)
        
        # Automatically apply the only transform to the point list if available
        apply_only_transform_to_point_list(point_list)
        
        slicer.modules.CurrentPostBranchAnalysisPointList = point_list
        
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            selectionNode.SetActivePlaceNodeID(point_list.GetID())
        
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
            # Enable continuous point placement mode (equivalent to "Place multiple control points" checkbox)
            interactionNode.SetPlaceModePersistence(1)
        
        setup_post_branch_point_count_observer(point_list, count_label)
        
        update_post_branch_point_count_display(point_list, count_label)
        
        pass
        pass
        pass
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not start post branch point placement: {str(e)}")

def stop_post_branch_point_placement_mode():
    """
    Stop the post branch point placement mode and return to normal interaction
    """
    try:
        # Disable placement mode
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
            interactionNode.SetPlaceModePersistence(0)
        
        # Reset selection node
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetActivePlaceNodeID("")
        
        pass
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not stop post branch point placement: {str(e)}")

def setup_post_branch_point_count_observer(point_list, count_label):
    """
    Set up observers for post branch point count changes and point additions
    """
    try:
        # Remove any existing observers first
        if hasattr(point_list, 'PostBranchPointCountObserver'):
            point_list.RemoveObserver(point_list.PostBranchPointCountObserver)
        
        observer_id = point_list.AddObserver(point_list.PointModifiedEvent, 
                                           lambda caller, event: update_post_branch_point_count_display_for_current_list(count_label))
        point_list.PostBranchPointCountObserver = observer_id
        
        observer_id2 = point_list.AddObserver(point_list.PointAddedEvent, 
                                            lambda caller, event: on_post_branch_point_added(caller, count_label))
        point_list.PostBranchPointAddObserver = observer_id2
        
    except Exception as e:
        pass

def update_post_branch_point_count_display(point_list, count_label):
    """
    Update the count display for post branch points
    """
    try:
        if point_list and count_label:
            count = point_list.GetNumberOfControlPoints()
            count_label.setText(f"Post Branch Points: {count}")
    except Exception as e:
        pass

def update_post_branch_point_count_display_for_current_list(count_label):
    """
    Update post branch point count display for the current point list
    """
    try:
        current_list = getattr(slicer.modules, 'CurrentPostBranchAnalysisPointList', None)
        if current_list:
            update_post_branch_point_count_display(current_list, count_label)
    except Exception as e:
        pass

def on_post_branch_point_added(point_list, count_label):
    """
    Handle post branch point addition events
    """
    try:
        # Ensure this point list uses the current centerline reference
        ensure_point_placement_uses_current_centerline(point_list)
        
        # Update the display first
        update_post_branch_point_count_display(point_list, count_label)
        
        # Ensure point placement mode remains active for continued point placement
        ensure_point_placement_mode_active(point_list)
        
        # Get current point count for feedback
        point_count = point_list.GetNumberOfControlPoints()
        
        # Check if centerline exists using the current centerline reference
        centerline_exists = False
        centerline_model, centerline_curve = get_current_centerline_for_placement()
        
        if centerline_model or centerline_curve:
            centerline_exists = True
            pass  # Found current centerline reference
        else:
            # Fallback: Try to find any centerline model if no reference stored
            try:
                centerline_model = slicer.util.getNode('Centerline model')
                if centerline_model:
                    centerline_exists = True
                    # Store this as current reference for consistency
                    slicer.modules.WorkflowCenterlineModel = centerline_model
                    pass  # Found centerline model by exact name
            except:
                # Try to find any centerline model by pattern
                all_models = slicer.util.getNodesByClass('vtkMRMLModelNode')
                for model in all_models:
                    if 'centerline' in model.GetName().lower() or 'tree' in model.GetName().lower():
                        centerline_exists = True
                        slicer.modules.WorkflowCenterlineModel = model
                        pass  # Found centerline model by pattern matching
                        break
        
        # Draw circle for the newly added point only if centerline exists
        # AND only if this is not the very first point being placed
        if point_count > 0 and centerline_exists:
            # Additional check: Don't create circle for the first point unless we're sure the user placed it
            # This prevents automatic circle creation when the workflow is just starting
            if point_count == 1:
                # For the first point, only create circle if we're in a resumed workflow state
                # (i.e., not during initial tool activation)
                pass  # Skip circle creation for first point during initial setup
            else:
                success = draw_circle_for_single_post_branch_point(point_count - 1)
                # Note: draw_circle_for_single_post_branch_point will hide the fiducial points after creating circles
                # This keeps the workflow logic intact while simplifying the visual display
        
        # Keep placement mode active for continuous point placement
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
            interactionNode.SetPlaceModePersistence(1)
            
    except Exception as e:
        pass

def toggle_branch_point_placement_mode():
    """
    Toggle between starting and stopping branch point placement within the same button
    (Exact copy of toggle_point_placement_mode with branch naming)
    """
    try:
        # Check if placement is currently active
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        is_placing = False
        
        if interactionNode:
            current_mode = interactionNode.GetCurrentInteractionMode()
            is_placing = (current_mode == interactionNode.Place)
        
        branch_button = getattr(slicer.modules, 'WorkflowBranchButton', None)
        count_label = getattr(slicer.modules, 'WorkflowCountLabel', None)
        
        if not branch_button or not count_label:
            pass  # Button references not found
            return
        
        if not is_placing:
            # Start placement
            start_new_branch_point_list_placement(count_label)
            
            # Update button to "stop" state
            branch_button.setText("Stop Branch")
            branch_button.setStyleSheet("""
                QPushButton { 
                    background-color: #dc3545; 
                    color: white; 
                    border: none; 
                    padding: 12px; 
                    font-weight: bold;
                    border-radius: 6px;
                    margin: 5px;
                    font-size: 13px;
                }
                QPushButton:hover { 
                    background-color: #c82333; 
                }
                QPushButton:pressed { 
                    background-color: #bd2130; 
                }
            """)
        else:
            # Stop placement
            stop_branch_point_placement_mode()
            
            # Update button to "start" state
            branch_button.setText("Branch")
            branch_button.setStyleSheet("""
                QPushButton { 
                    background-color: #0078d4; 
                    color: white; 
                    border: none; 
                    padding: 12px; 
                    font-weight: bold;
                    border-radius: 6px;
                    margin: 5px;
                    font-size: 13px;
                }
                QPushButton:hover { 
                    background-color: #106ebe; 
                }
                QPushButton:pressed { 
                    background-color: #005a9e; 
                }
            """)
            
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not toggle branch point placement: {str(e)}")

def start_new_branch_point_list_placement(count_label):
    """
    Create a new branch point list and start placement mode with continuous placement enabled.
    Uses the current centerline reference (same as main placement system).
    """
    try:
        # First, remove any existing B-1 nodes to start fresh
        existing_b1_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for node in existing_b1_nodes:
            if node.GetName() == "B-1":
                slicer.mrmlScene.RemoveNode(node)
                pass  # Removed existing B-1 node
        
        # Also clear any existing branch circles from previous runs
        clear_branch_circles()
        
        # Get the current centerline reference (same as main placement system)
        current_centerline_model, current_centerline_curve = get_current_centerline_for_placement()
        
        point_list = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        
        point_list.SetName("B-1")
        
        # Store reference to the centerline that should be used for this point list
        # This ensures consistent positioning relative to the CPR centerline
        if current_centerline_model:
            try:
                point_list.ReferenceCenterlineModel = current_centerline_model
            except:
                pass
        if current_centerline_curve:
            try:
                point_list.ReferenceCenterlineCurve = current_centerline_curve
            except:
                pass
        
        display_node = point_list.GetDisplayNode()
        if display_node:
            display_node.SetGlyphScale(3.0)  # Make points larger
            display_node.SetSelectedColor(1.0, 1.0, 0.0)  # Yellow when selected
            display_node.SetColor(0.0, 0.4, 1.0)  # Blue when not selected
            display_node.SetTextScale(2.0)  # Larger text labels
            display_node.SetVisibility(True)
            display_node.SetPointLabelsVisibility(True)
        
        # Clear any automatically added points that may have been created
        while point_list.GetNumberOfControlPoints() > 0:
            point_list.RemoveNthControlPoint(0)
        
        # Automatically apply the only transform to the point list if available
        apply_only_transform_to_point_list(point_list)
        
        slicer.modules.CurrentBranchAnalysisPointList = point_list
        
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            selectionNode.SetActivePlaceNodeID(point_list.GetID())
        
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
            # Enable continuous point placement mode (equivalent to "Place multiple control points" checkbox)
            interactionNode.SetPlaceModePersistence(1)
        
        setup_branch_point_count_observer(point_list, count_label)
        
        update_branch_point_count_display(point_list, count_label)
        
        pass
        pass
        pass
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not start branch point placement: {str(e)}")

def setup_branch_point_count_observer(point_list, count_label):
    """
    Set up observers for branch point count changes and point additions
    (Exact copy of setup_point_count_observer with branch naming)
    """
    try:
        # Remove any existing observers first
        if hasattr(point_list, 'BranchPointCountObserver'):
            point_list.RemoveObserver(point_list.BranchPointCountObserver)
        
        observer_id = point_list.AddObserver(point_list.PointModifiedEvent, 
                                           lambda caller, event: update_branch_point_count_display_for_current_list(count_label))
        point_list.BranchPointCountObserver = observer_id
        
        observer_id2 = point_list.AddObserver(point_list.PointAddedEvent, 
                                            lambda caller, event: on_branch_point_added(caller, count_label))
        point_list.BranchPointAddObserver = observer_id2
        
    except Exception as e:
        pass

def on_branch_point_added(point_list, count_label):
    """
    Handle branch point addition events - update display and ensure placement mode stays active.
    (Exact copy of on_point_added with branch naming)
    """
    try:
        # Ensure this point list uses the current centerline reference
        ensure_point_placement_uses_current_centerline(point_list)
        
        # Update the display first
        update_branch_point_count_display_for_current_list(count_label)
        
        # Ensure point placement mode remains active for continued point placement
        ensure_point_placement_mode_active(point_list)
        
        # Get current point count for feedback
        point_count = point_list.GetNumberOfControlPoints()
        
        # Check if centerline exists using the current centerline reference
        centerline_exists = False
        centerline_model, centerline_curve = get_current_centerline_for_placement()
        
        if centerline_model or centerline_curve:
            centerline_exists = True
            pass  # Found current centerline reference
        else:
            # Fallback: Try to find any centerline model if no reference stored
            try:
                centerline_model = slicer.util.getNode('Centerline model')
                if centerline_model:
                    centerline_exists = True
                    # Store this as current reference for consistency
                    slicer.modules.WorkflowCenterlineModel = centerline_model
                    pass  # Found centerline model by exact name
            except:
                # Try to find any centerline model by pattern
                all_models = slicer.util.getNodesByClass('vtkMRMLModelNode')
                for model in all_models:
                    if 'centerline' in model.GetName().lower() or 'tree' in model.GetName().lower():
                        centerline_exists = True
                        slicer.modules.WorkflowCenterlineModel = model
                        pass  # Found centerline model by pattern matching
                        break
        
        # Draw circle for the newly added point only if centerline exists
        # AND only if this is not the very first point being placed
        if point_count > 0 and centerline_exists:
            # Additional check: Don't create circle for the first point unless we're sure the user placed it
            # This prevents automatic circle creation when the workflow is just starting
            if point_count == 1:
                # For the first point, only create circle if we're in a resumed workflow state
                # (i.e., not during initial tool activation)
                pass  # Skip circle creation for first point during initial setup
            else:
                success = draw_circle_for_single_branch_point(point_count - 1)
                # Note: draw_circle_for_single_point will hide the fiducial points after creating circles
                # This keeps the workflow logic intact while simplifying the visual display
        
        # Provide feedback about what point was just placed and what's next
        if point_count == 1:
            pass  # Just placed post-branch
        elif point_count == 2:
            pass  # Just placed branch
        elif point_count >= 3:
            # For points 3 and beyond, they alternate between post-branch and branch
            if (point_count - 1) % 2 == 0:  # Odd total count = post-branch
                branch_num = ((point_count - 1) // 2) + 1
                pass  # Just placed post-branch-{branch_num}
            else:  # Even total count = branch
                branch_num = ((point_count - 1) // 2) + 1
                pass  # Just placed branch-{branch_num}
        
        # Provide next step guidance
        if point_count == 1:
            pass  # Next: place branch point
        elif point_count >= 2:
            if point_count % 2 == 0:  # Even count = just placed branch, next is post-branch
                next_branch_num = (point_count // 2) + 1
                pass  # Next: place post-branch-{next_branch_num}
            else:  # Odd count = just placed post-branch, next is branch
                current_branch_num = ((point_count - 1) // 2) + 1
                pass  # Next: place branch-{current_branch_num}
        
    except Exception as e:
        pass

def update_branch_point_count_display_for_current_list(count_label):
    """
    Update the branch point count display for the current active branch point list
    (Exact copy of update_point_count_display_for_current_list with branch naming)
    """
    try:
        current_point_list = None
        if hasattr(slicer.modules, 'CurrentBranchAnalysisPointList'):
            current_point_list = slicer.modules.CurrentBranchAnalysisPointList
        
        if current_point_list:
            update_branch_point_count_display(current_point_list, count_label)
            
            # Automatically re-enable point placement mode after each point is added
            ensure_point_placement_mode_active(current_point_list)
            
            # Note: Individual circles are now drawn immediately when each point is added
            # No need to wait for minimum points or redraw all circles here
                
        else:
            fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
            total_points = 0
            
            for node in fiducial_nodes:
                node_name = node.GetName()
                if node_name == "B-1":
                    total_points += node.GetNumberOfControlPoints()
            
            count_label.setText(f"Total branch points: {total_points}")
        
    except Exception as e:
        pass

def update_branch_point_count_display(point_list, count_label):
    """
    Update the branch point count display label and assign specific branch analysis labels
    (Exact copy of update_point_count_display with branch naming)
    """
    try:
        point_count = point_list.GetNumberOfControlPoints()
        count_label.setText(f"Branch points placed: {point_count}")
        
        for i in range(point_count):
            current_label = point_list.GetNthControlPointLabel(i)
            if not current_label or current_label.startswith("F") or current_label.startswith("P-"): 
                # Branch points alternate: post-branch-1, branch-1, post-branch-2, branch-2, etc.
                if i % 2 == 0:  # Even indices (0, 2, 4...) are post-branch
                    branch_number = (i // 2) + 1
                    point_list.SetNthControlPointLabel(i, f"post-branch-{branch_number}")
                else:  # Odd indices (1, 3, 5...) are branch
                    branch_number = ((i - 1) // 2) + 1
                    point_list.SetNthControlPointLabel(i, f"branch-{branch_number}")
        
    except Exception as e:
        pass

def draw_circle_for_single_branch_point(point_index):
    """
    Draw a circle for a single branch point using the current branch point list
    (Exact copy of draw_circle_for_single_point with branch naming)
    """
    try:
        current_point_list = getattr(slicer.modules, 'CurrentBranchAnalysisPointList', None)
        if not current_point_list:
            return False
        
        if point_index >= current_point_list.GetNumberOfControlPoints():
            return False
        
        return draw_circle_for_branch_point(current_point_list, point_index)
        
    except Exception as e:
        return False

def draw_circle_for_single_post_branch_point(point_index):
    """
    Draw a circle for a single post branch point using the current post branch point list
    """
    try:
        current_point_list = getattr(slicer.modules, 'CurrentPostBranchAnalysisPointList', None)
        if not current_point_list:
            return False
        
        if point_index >= current_point_list.GetNumberOfControlPoints():
            return False
        
        return draw_circle_for_post_branch_point(current_point_list, point_index)
        
    except Exception as e:
        return False

def stop_branch_point_placement_mode():
    """
    Stop the branch point placement mode and return to normal interaction
    (Exact copy of stop_point_placement_mode with branch naming)
    """
    try:
        # Clean up any orphaned start markers before stopping
        # cleanup_orphaned_start_markers()  # Skip this for branch points
        
        # Disable placement mode
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
            interactionNode.SetPlaceModePersistence(0)
        
        # Reset selection node
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetActivePlaceNodeID("")
        
        pass
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not stop branch point placement: {str(e)}")

def stop_point_placement_mode():
    """
    Stop the point placement mode and return to normal interaction
    """
    try:
        # Clean up any orphaned start markers before stopping
        cleanup_orphaned_start_markers()
        
        # Disable placement mode
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
            interactionNode.SetPlaceModePersistence(0)
        
        # Clear selection
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetActivePlaceNodeID("")
        
        # Update point count display if available
        count_label = getattr(slicer.modules, 'WorkflowCountLabel', None)
        if count_label:
            f1_points = None
            try:
                f1_points = slicer.util.getNode('F-1')
                if f1_points:
                    point_count = f1_points.GetNumberOfControlPoints()
                    count_label.setText(f"Points placed: {point_count}")
            except:
                pass
        
        pass
        
    except Exception as e:
        pass

def cleanup_orphaned_start_markers():
    """
    Remove any start-slice markers that don't have corresponding end-slice markers
    """
    try:
        f1_points = None
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for node in fiducial_nodes:
            if node.GetName() == "F-1":
                f1_points = node
                break
        
        if not f1_points:
            return False
        
        total_points = f1_points.GetNumberOfControlPoints()
        if total_points <= 3:  # Need at least test-point, pre-lesion, post-lesion, and one slice point
            return False
        
        # Count slice points (everything after the first 3 points)
        slice_points = total_points - 3
        
        # If odd number of slice points, we have an orphaned start marker
        if slice_points % 2 == 1:
            # Remove the last point (orphaned start marker)
            last_point_index = total_points - 1
            
            # Get the label to confirm it's a start marker
            last_label = f1_points.GetNthControlPointLabel(last_point_index)
            if last_label and "start-slice" in last_label:
                f1_points.RemoveNthControlPoint(last_point_index)
                pass  # Removed orphaned start marker
                return True
        
        return False
        
    except Exception as e:
        return False

def setup_point_count_observer(point_list, count_label):
    """
    Set up observer to automatically update point count display and maintain point placement mode
    """
    try:
        if hasattr(point_list, 'PointCountObserver'):
            point_list.RemoveObserver(point_list.PointCountObserver)
        
        observer_id = point_list.AddObserver(point_list.PointModifiedEvent, 
                                           lambda caller, event: update_point_count_display_for_current_list(count_label))
        point_list.PointCountObserver = observer_id
        
        observer_id2 = point_list.AddObserver(point_list.PointAddedEvent, 
                                            lambda caller, event: on_point_added(caller, count_label))
        point_list.PointAddObserver = observer_id2
        
        observer_id3 = point_list.AddObserver(point_list.PointRemovedEvent, 
                                            lambda caller, event: update_point_count_display_for_current_list(count_label))
        point_list.PointRemoveObserver = observer_id3
        
    except Exception as e:
        pass

def on_point_added(point_list, count_label):
    """
    Handle point addition events - update display and ensure placement mode stays active.
    Provides feedback for the enhanced workflow with multiple start/end slices.
    Ensures points are placed based on the most recently used centerline for CPR.
    """
    try:
        # Ensure this point list uses the current centerline reference
        ensure_point_placement_uses_current_centerline(point_list)
        
        # Update the display first
        update_point_count_display_for_current_list(count_label)
        
        # Ensure point placement mode remains active for continued point placement
        ensure_point_placement_mode_active(point_list)
        
        # Get current point count for feedback
        point_count = point_list.GetNumberOfControlPoints()
        
        # Check if centerline exists using the current centerline reference
        centerline_exists = False
        centerline_model, centerline_curve = get_current_centerline_for_placement()
        
        if centerline_model or centerline_curve:
            centerline_exists = True
            pass  # Found current centerline reference
        else:
            # Fallback: Try to find any centerline model if no reference stored
            try:
                centerline_model = slicer.util.getNode('Centerline model')
                if centerline_model:
                    centerline_exists = True
                    # Store this as current reference for consistency
                    slicer.modules.WorkflowCenterlineModel = centerline_model
                    pass  # Found centerline model by exact name
            except:
                # Try to find any centerline model by pattern
                all_models = slicer.util.getNodesByClass('vtkMRMLModelNode')
                for model in all_models:
                    if 'centerline' in model.GetName().lower() or 'tree' in model.GetName().lower():
                        centerline_exists = True
                        slicer.modules.WorkflowCenterlineModel = model
                        pass  # Found centerline model by pattern matching
                        break
        
        # Draw circle for the newly added point only if centerline exists
        # AND only if this is not the very first point being placed
        if point_count > 0 and centerline_exists:
            # Additional check: Don't create circle for the first point unless we're sure the user placed it
            # This prevents automatic circle creation when the workflow is just starting
            if point_count == 1:
                # For the first point, only create circle if we're in a resumed workflow state
                # (i.e., not during initial tool activation)
                pass  # Skip circle creation for first point during initial setup
            else:
                success = draw_circle_for_single_point(point_count - 1)
                # Note: draw_circle_for_single_point will hide the fiducial points after creating circles
                # This keeps the workflow logic intact while simplifying the visual display
        
        # Provide feedback about what point was just placed and what's next
        if point_count == 1:
            pass  # Just placed test-point
        elif point_count == 2:
            pass  # Just placed pre-lesion
        elif point_count == 3:
            pass  # Just placed post-lesion
        elif point_count >= 4:
            # For points 4 and beyond, they alternate between start and end slices
            if (point_count - 4) % 2 == 0:  # Just placed a start slice
                start_num = ((point_count - 4) // 2) + 1
                pass  # Just placed start-slice-{start_num}
            else:  # Just placed an end slice
                end_num = ((point_count - 4) // 2) + 1
                pass  # Just placed end-slice-{end_num}
        
        # Provide next step guidance
        if point_count == 1:
            pass  # Next: place pre-lesion point
        elif point_count == 2:
            pass  # Next: place post-lesion point
        elif point_count == 3:
            pass  # Next: place first start-slice point
        elif point_count >= 4:
            if (point_count - 3) % 2 == 1:  # Just placed a start slice
                end_num = ((point_count - 4) // 2) + 1
                pass  # Next: place corresponding end-slice-{end_num}
            else:  # Just placed an end slice
                start_num = ((point_count - 3) // 2) + 1
                pass  # Next: place start-slice-{start_num} or finish
        
    except Exception as e:
        pass

def update_point_count_display_for_current_list(count_label):
    """
    Update the point count display for the current active point list
    """
    try:
        current_point_list = None
        if hasattr(slicer.modules, 'CurrentLesionAnalysisPointList'):
            current_point_list = slicer.modules.CurrentLesionAnalysisPointList
        
        if current_point_list:
            update_point_count_display(current_point_list, count_label)
            
            # Automatically re-enable point placement mode after each point is added
            ensure_point_placement_mode_active(current_point_list)
            
            # Note: Individual circles are now drawn immediately when each point is added
            # No need to wait for minimum points or redraw all circles here
                
        else:
            fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
            total_points = 0
            
            for node in fiducial_nodes:
                node_name = node.GetName()
                if node_name == "F-1":
                    total_points += node.GetNumberOfControlPoints()
            
            count_label.setText(f"Total points: {total_points}")
        
    except Exception as e:
        pass

def update_point_count_display(point_list, count_label):
    """
    Update the point count display label and assign specific lesion analysis labels
    Supports multiple start and end slices with sequential numbering
    """
    try:
        point_count = point_list.GetNumberOfControlPoints()
        count_label.setText(f"Points placed: {point_count}")
        
        for i in range(point_count):
            current_label = point_list.GetNthControlPointLabel(i)
            if not current_label or current_label.startswith("F") or current_label.startswith("P-"): 
                if i == 0:
                    point_list.SetNthControlPointLabel(i, "test-point")
                elif i == 1:
                    point_list.SetNthControlPointLabel(i, "pre-lesion")
                elif i == 2:
                    point_list.SetNthControlPointLabel(i, "post-lesion")
                else:
                    # For points 4 and beyond, alternate between start and end slices
                    # Points 3, 5, 7, 9... are start slices (start-slice-1, start-slice-2, etc.)
                    # Points 4, 6, 8, 10... are end slices (end-slice-1, end-slice-2, etc.)
                    if (i - 3) % 2 == 0:  # Even offset from position 3 = start slice
                        start_slice_number = ((i - 3) // 2) + 1
                        point_list.SetNthControlPointLabel(i, f"start-slice-{start_slice_number}")
                    else:  # Odd offset from position 3 = end slice
                        end_slice_number = ((i - 3) // 2) + 1
                        point_list.SetNthControlPointLabel(i, f"end-slice-{end_slice_number}")
        
    except Exception as e:
        pass

def validate_point_placement_centerline_reference():
    """
    Validate that the current point placement is using the correct centerline reference.
    Returns information about the centerline being used for point placement.
    """
    try:
        validation_info = {
            "has_current_point_list": False,
            "point_list_has_centerline_ref": False,
            "centerline_model_available": False,
            "centerline_curve_available": False,
            "centerline_model_name": None,
            "centerline_curve_name": None,
            "recommendations": []
        }
        
        # Check if there's a current point list
        current_point_list = getattr(slicer.modules, 'CurrentLesionAnalysisPointList', None)
        if current_point_list:
            validation_info["has_current_point_list"] = True
            
            # Check if point list has centerline references
            if hasattr(current_point_list, 'ReferenceCenterlineModel') or hasattr(current_point_list, 'ReferenceCenterlineCurve'):
                validation_info["point_list_has_centerline_ref"] = True
        
        # Check current centerline availability
        centerline_model, centerline_curve = get_current_centerline_for_placement()
        
        if centerline_model:
            validation_info["centerline_model_available"] = True
            validation_info["centerline_model_name"] = centerline_model.GetName()
        
        if centerline_curve:
            validation_info["centerline_curve_available"] = True
            validation_info["centerline_curve_name"] = centerline_curve.GetName()
        
        # Generate recommendations
        if not validation_info["has_current_point_list"]:
            validation_info["recommendations"].append("No active point list found. Start point placement first.")
        
        if not validation_info["centerline_model_available"] and not validation_info["centerline_curve_available"]:
            validation_info["recommendations"].append("No centerline reference found. Extract centerline and run CPR first.")
        
        if validation_info["has_current_point_list"] and not validation_info["point_list_has_centerline_ref"]:
            validation_info["recommendations"].append("Point list does not have centerline reference. This may cause inconsistent placement.")
        
        if not validation_info["recommendations"]:
            validation_info["recommendations"].append("Point placement appears to be properly configured with centerline reference.")
        
        return validation_info
        
    except Exception as e:
        return {
            "error": str(e),
            "recommendations": ["Error occurred during validation. Check console for details."]
        }

def ensure_point_placement_mode_active(point_list):
    """
    Ensure that point placement mode remains active after each point is placed
    """
    try:
        # Re-select the active point list in the selection node
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            selectionNode.SetActivePlaceNodeID(point_list.GetID())

        # Ensure interaction mode is set to placement with continuous mode enabled
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            current_mode = interactionNode.GetCurrentInteractionMode()
            if current_mode != interactionNode.Place:
                interactionNode.SetCurrentInteractionMode(interactionNode.Place)
                pass
            
            # Enable continuous point placement mode (equivalent to "Place multiple control points" checkbox)
            interactionNode.SetPlaceModePersistence(1)
        
    except Exception as e:
        pass

def cleanup_point_placement_ui():
    """
    Clean up point placement UI elements
    """
    try:
        if hasattr(slicer.modules, 'PointPlacementDockWidget'):
            dock_widget = slicer.modules.PointPlacementDockWidget
            dock_widget.close()
            dock_widget.setParent(None)
            del slicer.modules.PointPlacementDockWidget
            pass
        
        if hasattr(slicer.modules, 'PointCountLabel'):
            del slicer.modules.PointCountLabel
            
    except Exception as e:
        pass

def apply_only_transform_to_point_list(point_list):
    """
    Automatically find and apply the "Straightening transform" to the point list
    """
    try:
        # Get all transform nodes in the scene
        transform_nodes = slicer.util.getNodesByClass('vtkMRMLTransformNode')
        
        if len(transform_nodes) == 0:
            pass
            return False
        
        # Look specifically for "Straightening transform"
        straightening_transform = None
        for transform_node in transform_nodes:
            if transform_node.GetName() == "Straightening transform":
                straightening_transform = transform_node
                break
        
        if straightening_transform:
            # Apply the Straightening transform
            point_list.SetAndObserveTransformNodeID(straightening_transform.GetID())
            pass
            return True
        else:
            # Straightening transform not found
            transform_names = [node.GetName() for node in transform_nodes]
            pass
            return False
            
    except Exception as e:
        pass
        return False

def start_new_point_list_placement(count_label):
    """
    Create a new point list and start placement mode with continuous placement enabled.
    Ensures that placement is based on the most recently used centerline for CPR.
    """
    try:
        # First, remove any existing F-1 nodes to start fresh
        existing_f1_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for node in existing_f1_nodes:
            if node.GetName() == "F-1":
                slicer.mrmlScene.RemoveNode(node)
                pass  # Removed existing F-1 node
        
        # Also clear any existing circles from previous runs
        clear_centerline_circles()
        
        # Store reference to the most recently used centerline for CPR
        # This ensures pre/post start/stop points are placed based on the current centerline
        current_centerline_model = None
        current_centerline_curve = None
        
        # Check if we have stored references from CPR module usage
        if hasattr(slicer.modules, 'WorkflowCenterlineModel'):
            current_centerline_model = slicer.modules.WorkflowCenterlineModel
        if hasattr(slicer.modules, 'WorkflowCenterlineCurve'):
            current_centerline_curve = slicer.modules.WorkflowCenterlineCurve
        
        # If no stored references, find the most recent centerline
        if not current_centerline_model and not current_centerline_curve:
            current_centerline_model = find_recent_centerline_model()
            current_centerline_curve = find_recent_centerline_curve()
            
            # Store these for future reference
            if current_centerline_model:
                slicer.modules.WorkflowCenterlineModel = current_centerline_model
            if current_centerline_curve:
                slicer.modules.WorkflowCenterlineCurve = current_centerline_curve
        
        point_list = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        
        point_list.SetName("F-1")
        
        # Store reference to the centerline that should be used for this point list
        # This ensures consistent positioning relative to the CPR centerline
        if current_centerline_model:
            try:
                point_list.ReferenceCenterlineModel = current_centerline_model
            except:
                pass
        if current_centerline_curve:
            try:
                point_list.ReferenceCenterlineCurve = current_centerline_curve
            except:
                pass
        
        display_node = point_list.GetDisplayNode()
        if display_node:
            display_node.SetGlyphScale(3.0)  # Make points larger
            display_node.SetSelectedColor(1.0, 1.0, 0.0)  # Yellow when selected
            display_node.SetColor(1.0, 0.0, 0.0)  # Red when not selected
            display_node.SetTextScale(2.0)  # Larger text labels
            display_node.SetVisibility(True)
            display_node.SetPointLabelsVisibility(True)
        
        # Clear any automatically added points that may have been created
        while point_list.GetNumberOfControlPoints() > 0:
            point_list.RemoveNthControlPoint(0)
        
        # Automatically apply the only transform to the point list if available
        apply_only_transform_to_point_list(point_list)
        
        slicer.modules.CurrentLesionAnalysisPointList = point_list
        
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            selectionNode.SetActivePlaceNodeID(point_list.GetID())
        
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
            # Enable continuous point placement mode (equivalent to "Place multiple control points" checkbox)
            interactionNode.SetPlaceModePersistence(1)
        
        setup_point_count_observer(point_list, count_label)
        
        update_point_count_display(point_list, count_label)
        
        pass
        pass
        pass
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not start point placement: {str(e)}")

def toggle_analysis_masks_visibility(toggle_button):
    """
    Toggle visibility of AnalysisMasks nodes in the scene
    """
    try:
        # Find all nodes that contain "AnalysisMasks" in their name
        all_nodes = []
        
        # Check different types of nodes that might contain AnalysisMasks
        node_classes = [
            'vtkMRMLSegmentationNode',
            'vtkMRMLModelNode', 
            'vtkMRMLVolumeNode',
            'vtkMRMLMarkupsNode'
        ]
        
        analysis_mask_nodes = []
        for node_class in node_classes:
            nodes = slicer.util.getNodesByClass(node_class)
            for node in nodes:
                if "AnalysisMasks" in node.GetName():
                    analysis_mask_nodes.append(node)
        if not analysis_mask_nodes:
            return
        
        # Determine current visibility state (check the first node)
        first_node = analysis_mask_nodes[0]
        current_visibility = True
        
        # Check visibility based on node type
        if hasattr(first_node, 'GetDisplayNode') and first_node.GetDisplayNode():
            display_node = first_node.GetDisplayNode()
            if hasattr(display_node, 'GetVisibility'):
                current_visibility = display_node.GetVisibility()
        
        # Toggle visibility for all AnalysisMasks nodes
        new_visibility = not current_visibility
        
        for node in analysis_mask_nodes:
            if hasattr(node, 'GetDisplayNode') and node.GetDisplayNode():
                display_node = node.GetDisplayNode()
                if hasattr(display_node, 'SetVisibility'):
                    display_node.SetVisibility(new_visibility)
            
            # For segmentation nodes, also handle segment visibility
            if node.IsA('vtkMRMLSegmentationNode'):
                segmentation = node.GetSegmentation()
                if segmentation:
                    for i in range(segmentation.GetNumberOfSegments()):
                        segment_id = segmentation.GetNthSegmentID(i)
                        display_node = node.GetDisplayNode()
                        if display_node:
                            display_node.SetSegmentVisibility(segment_id, new_visibility)
        
        # Update button text
        if new_visibility:
            toggle_button.setText("Hide AnalysisMasks")
        else:
            toggle_button.setText("Show AnalysisMasks")
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not toggle AnalysisMasks visibility: {str(e)}")

def toggle_window_level_tool(activated, toggle_button):
    """
    Toggle the window level tool on/off in all slice views
    
    Args:
        activated (bool): True to activate window level tool, False to deactivate
        toggle_button: The button that called this function to update its text
    """
    try:
        # Get the interaction node
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if not interactionNode:
            return
        
        if activated:
            # Activate window level tool (adjust window/level)
            interactionNode.SetCurrentInteractionMode(interactionNode.AdjustWindowLevel)
            toggle_button.setText("Window Level (ON)")
            toggle_button.setChecked(True)
        else:
            # Deactivate window level tool (return to view transform)
            interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
            toggle_button.setText("Window Level")
            toggle_button.setChecked(False)
        
        # Force update of slice views
        slicer.app.processEvents()
        
    except Exception as e:
        slicer.util.errorDisplay(f"Could not toggle window level tool: {str(e)}")
        # Reset button state on error
        toggle_button.setText("Window Level")
        toggle_button.setChecked(False)

def create_stenosis_ratio_measurement():
    """
    Create a single line measurement node for stenosis analysis and activate the line tool
    """
    try:
        # Create line measurement node
        line_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode")
        existing_stenosis_count = count_existing_stenosis_measurements()
        line_node.SetName(f"StenosisLine_{existing_stenosis_count + 1}")
        
        # Configure the line node
        configure_stenosis_line_node(line_node)
        
        # Set the line as the active measurement node
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsLineNode")
            selectionNode.SetActivePlaceNodeID(line_node.GetID())
        
        # Enable line placement mode
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
            # Enable continuous placement mode for multiple measurements
            interactionNode.SetPlaceModePersistence(1)
        
        # Set up observer to stop tool when line is complete
        setup_single_stenosis_line_observer(line_node)
        
        pass
        pass
        
        return line_node
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not create stenosis line measurements: {str(e)}")
        return None

def count_existing_stenosis_measurements():
    """
    Count existing stenosis line measurements in the scene
    """
    try:
        line_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsLineNode')
        stenosis_count = 0
        
        for node in line_nodes:
            if "StenosisLine" in node.GetName():
                stenosis_count += 1
        
        return stenosis_count
        
    except Exception as e:
        pass
        return 0

def configure_stenosis_line_node(line_node):
    """
    Configure the line node with appropriate display settings for stenosis measurement
    """
    try:
        # Get or create display node
        display_node = line_node.GetDisplayNode()
        if not display_node:
            line_node.CreateDefaultDisplayNodes()
            display_node = line_node.GetDisplayNode()
        
        if display_node:
            # Set line color to bright purple for stenosis line
            display_node.SetColor(1.0, 0.0, 1.0)  # Bright magenta/purple color
            display_node.SetSelectedColor(1.0, 0.5, 0.0)  # Orange when selected
            
            # Make line thicker and more visible
            display_node.SetLineWidth(4.0)  # Increased line width
            display_node.SetGlyphScale(3.0)  # Increased point size
            
            # Show measurement text
            display_node.SetTextScale(2.5)  # Larger text
            display_node.SetVisibility(True)
            display_node.SetPointLabelsVisibility(True)
            
            # Enable measurement display
            line_node.SetMeasurementEnabled(True)
            
            # Make sure line is interactive for placement
            display_node.SetPointLabelsVisibility(True)
            display_node.SetPropertiesLabelVisibility(True)
        
        # Set measurement units if available
        measurement = line_node.GetMeasurement("length")
        if measurement:
            measurement.SetDisplayCoefficient(1.0)  # Default to mm
            measurement.SetUnits("mm")
            measurement.SetEnabled(True)
        
        # Ensure the line node is set to allow exactly 2 points
        line_node.SetMaximumNumberOfControlPoints(2)
        line_node.SetRequiredNumberOfControlPoints(2)
        
        pass
        
    except Exception as e:
        pass

def setup_single_stenosis_line_observer(line_node):
    """
    Set up observer to detect when single stenosis line is complete and stop tool
    """
    try:
        # Remove any existing observer
        if hasattr(line_node, 'StenosisObserver'):
            line_node.RemoveObserver(line_node.StenosisObserver)
        
        # Add observer for when points are added to the line
        observer_id = line_node.AddObserver(
            line_node.PointAddedEvent, 
            lambda caller, event: check_single_line_completion(caller)
        )
        line_node.StenosisObserver = observer_id
        
        pass
        
    except Exception as e:
        pass

def check_single_line_completion(line_node):
    """
    Check if the stenosis line has exactly 2 points and distance > 0mm before stopping tool
    """
    try:
        current_points = line_node.GetNumberOfControlPoints()
        pass
        
        # Only stop when we have exactly 2 points AND a measurable distance > 0mm
        if current_points == 2:
            # Get the measurement value and check if it's > 0mm
            measurement = line_node.GetMeasurement("length")
            if measurement:
                length_value = measurement.GetValue()
                pass
                
                if length_value > 0.0:  # Only stop if distance is greater than 0mm
                    # Remove the observer to avoid multiple triggers
                    if hasattr(line_node, 'StenosisObserver'):
                        line_node.RemoveObserver(line_node.StenosisObserver)
                        delattr(line_node, 'StenosisObserver')
                    
                    pass
                    
                    # Stop the measurement tool
                    stop_stenosis_measurement_tool()
                else:
                    pass
                    pass
            else:
                pass
        elif current_points == 1:
            pass
        
    except Exception as e:
        pass

def check_first_line_completion_carefully(first_line_node, second_line_node):
    """
    Check if the first stenosis line has exactly 2 points and a distance > 0mm before switching
    """
    try:
        current_points = first_line_node.GetNumberOfControlPoints()
        pass
        
        if current_points == 2:
            measurement = first_line_node.GetMeasurement("length")
            if measurement:
                length_value = measurement.GetValue()
                pass
                
                if length_value > 0.0:
                    if hasattr(first_line_node, 'StenosisSequenceObserver'):
                        first_line_node.RemoveObserver(first_line_node.StenosisSequenceObserver)
                        delattr(first_line_node, 'StenosisSequenceObserver')
                    
                    pass
                    pass

                    slicer.modules.StenosisSecondLineNode = second_line_node

                    try:
                        switch_to_second_stenosis_line(second_line_node)
                    except Exception as e:
                        pass
                        qt.QTimer.singleShot(100, lambda: switch_to_second_stenosis_line(slicer.modules.StenosisSecondLineNode))
                else:
                    pass
                    pass
            else:
                pass
        elif current_points == 1:
            pass
        
    except Exception as e:
        pass

def switch_to_second_stenosis_line(second_line_node):
    """
    Automatically switch to the second line measurement
    """
    try:
        pass
        pass
        pass
        
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            pass
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsLineNode")
            selectionNode.SetActivePlaceNodeID(second_line_node.GetID())
            pass
        else:
            pass
        
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            pass
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
            interactionNode.SetPlaceModePersistence(1)
            pass
            pass
        else:
            pass
        
        pass
        pass
        
        setup_second_line_completion_observer(second_line_node)
        
    except Exception as e:
        pass

def setup_second_line_completion_observer(second_line_node):
    """
    Set up observer to detect when second line is complete and prompt for next action
    """
    try:
        observer_id = second_line_node.AddObserver(
            second_line_node.PointAddedEvent,
            lambda caller, event: check_second_line_completion_carefully(caller)
        )
        second_line_node.StenosisSequenceObserver = observer_id
        
    except Exception as e:
        pass

def check_second_line_completion_carefully(second_line_node):
    """
    Check if second line has exactly 2 points and distance > 0mm before completing
    """
    try:
        current_points = second_line_node.GetNumberOfControlPoints()
        pass
        if current_points == 2:
            measurement = second_line_node.GetMeasurement("length")
            if measurement:
                length_value = measurement.GetValue()
                pass
                
                if length_value > 0.0:  # Only complete if distance is greater than 0mm
                    # Remove the observer to avoid multiple triggers
                    if hasattr(second_line_node, 'StenosisSequenceObserver'):
                        second_line_node.RemoveObserver(second_line_node.StenosisSequenceObserver)
                        delattr(second_line_node, 'StenosisSequenceObserver')
                    
                    pass
                    pass
                    
                    # Stop the measurement tool automatically instead of showing dialog
                    stop_stenosis_measurement_tool()
                    pass
                else:
                    pass
                    pass
            else:
                pass
        elif current_points == 1:
            pass
        
    except Exception as e:
        pass



def stop_stenosis_measurement_tool():
    """
    Stop the stenosis measurement tool and return to normal interaction mode
    """
    try:
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
            interactionNode.SetPlaceModePersistence(0)
        
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetActivePlaceNodeID(None)
        
    except Exception as e:
        pass

def disable_all_placement_tools():
    """
    Disable all placement tools and return to normal interaction mode
    """
    try:
        # Disable placement mode in interaction node
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
            interactionNode.SetPlaceModePersistence(0)
            pass
        
        # Clear any active placement node
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetActivePlaceNodeID(None)
            selectionNode.SetReferenceActivePlaceNodeClassName("")
            pass
        
        # Process events to ensure UI is updated
        slicer.app.processEvents()
        
        pass
        
    except Exception as e:
        pass

def save_scene_location_to_user_home(scene_path):
    """
    Save the current scene location to a file in the user's home directory.
    
    Args:
        scene_path (str): The path where the scene was saved
    """
    try:
        import os
        import datetime
        
        # Get user home directory
        home_dir = os.path.expanduser("~")
        location_file = os.path.join(home_dir, "slicer_scene_locations.txt")
        
        # Get current timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Prepare the entry
        entry = f"{timestamp} - {scene_path}\n"
        
        # Append to the file (create if it doesn't exist)
        with open(location_file, "a", encoding="utf-8") as f:
            f.write(entry)
            
        print(f"Scene location saved to: {location_file}")
        
    except Exception as e:
        print(f"Could not save scene location to user home: {str(e)}")

def show_saved_scene_locations():
    """
    Display all saved scene locations from the user's home directory.
    Console function to view the history of saved scenes.
    """
    try:
        import os
        
        # Get user home directory
        home_dir = os.path.expanduser("~")
        location_file = os.path.join(home_dir, "slicer_scene_locations.txt")
        
        if not os.path.exists(location_file):
            print("No saved scene locations found.")
            print(f"Location file would be: {location_file}")
            return
        
        print(f"Saved scene locations from: {location_file}")
        print("=" * 60)
        
        with open(location_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        if not lines:
            print("No scene locations recorded yet.")
        else:
            for i, line in enumerate(lines, 1):
                print(f"{i:2d}. {line.strip()}")
                
        print("=" * 60)
        print(f"Total scenes recorded: {len(lines)}")
        
    except Exception as e:
        print(f"Could not read scene locations: {str(e)}")

def clear_saved_scene_locations():
    """
    Clear all saved scene locations from the user's home directory.
    Console function to reset the scene location history.
    """
    try:
        import os
        
        # Get user home directory
        home_dir = os.path.expanduser("~")
        location_file = os.path.join(home_dir, "slicer_scene_locations.txt")
        
        if os.path.exists(location_file):
            os.remove(location_file)
            print(f"Cleared scene location history: {location_file}")
        else:
            print("No scene location history file found to clear.")
            
    except Exception as e:
        print(f"Could not clear scene location history: {str(e)}")

def get_current_scene_location():
    """
    Get the current scene file location.
    Console function to check where the current scene is saved.
    """
    try:
        scene_path = slicer.mrmlScene.GetURL()
        
        if scene_path:
            # Convert file:// URL to local path if needed
            if scene_path.startswith("file://"):
                scene_path = scene_path[7:]  # Remove "file://" prefix
            print(f"Current scene location: {scene_path}")
            return scene_path
        else:
            print("Current scene has not been saved yet (no file location).")
            return None
            
    except Exception as e:
        print(f"Could not get current scene location: {str(e)}")
        return None

def setup_scene_save_observer():
    """
    Set up an observer to automatically track scene saves regardless of how they're initiated.
    This monitors both manual saves and programmatic saves.
    """
    try:
        # Remove any existing observer first
        if hasattr(slicer.modules, 'SceneSaveObserverTag') and slicer.modules.SceneSaveObserverTag:
            slicer.mrmlScene.RemoveObserver(slicer.modules.SceneSaveObserverTag)
        
        # Add observer for scene save events
        observer_tag = slicer.mrmlScene.AddObserver(slicer.mrmlScene.EndSaveEvent, on_scene_saved)
        slicer.modules.SceneSaveObserverTag = observer_tag
        
        print("Scene save observer has been set up - all scene saves will now be tracked.")
        
    except Exception as e:
        print(f"Could not set up scene save observer: {str(e)}")

def on_scene_saved(caller, event):
    """
    Called whenever the scene is saved. Automatically logs the save location.
    """
    try:
        # Small delay to ensure the URL is updated
        qt.QTimer.singleShot(100, lambda: track_scene_save_location())
        
    except Exception as e:
        print(f"Error in scene save callback: {str(e)}")

def track_scene_save_location():
    """
    Track the current scene save location after a save event.
    """
    try:
        scene_path = slicer.mrmlScene.GetURL()
        
        if scene_path:
            # Convert file:// URL to local path if needed
            if scene_path.startswith("file://"):
                scene_path = scene_path[7:]  # Remove "file://" prefix
            
            # Only save if it's a valid file path (not empty or just whitespace)
            if scene_path and scene_path.strip():
                save_scene_location_to_user_home(scene_path)
            else:
                print("Scene save detected but no valid file path found")
        else:
            print("Scene save detected but no URL available")
            
    except Exception as e:
        print(f"Could not track scene save location: {str(e)}")

def remove_scene_save_observer():
    """
    Remove the scene save observer.
    Console function to stop automatic scene save tracking.
    """
    try:
        if hasattr(slicer.modules, 'SceneSaveObserverTag') and slicer.modules.SceneSaveObserverTag:
            slicer.mrmlScene.RemoveObserver(slicer.modules.SceneSaveObserverTag)
            slicer.modules.SceneSaveObserverTag = None
            print("Scene save observer has been removed.")
        else:
            print("No scene save observer was active.")
            
    except Exception as e:
        print(f"Could not remove scene save observer: {str(e)}")

def enable_scene_save_tracking():
    """
    Manually enable scene save tracking.
    Console function to activate automatic scene save location tracking.
    """
    try:
        setup_scene_save_observer()
        print("Scene save tracking is now enabled.")
        print("All scene saves will be automatically logged to:")
        import os
        home_dir = os.path.expanduser("~")
        location_file = os.path.join(home_dir, "slicer_scene_locations.txt")
        print(f"  {location_file}")
    except Exception as e:
        print(f"Could not enable scene save tracking: {str(e)}")

def disable_scene_save_tracking():
    """
    Manually disable scene save tracking.
    Console function to deactivate automatic scene save location tracking.
    """
    try:
        remove_scene_save_observer()
        print("Scene save tracking is now disabled.")
    except Exception as e:
        print(f"Could not disable scene save tracking: {str(e)}")

def setup_storage_nodes_for_consistent_saving():
    """
    Setup storage nodes to ensure consistent file naming and directory structure.
    This ensures that the main volume and all other files are saved properly.
    """
    try:
        # Find the working volume and ensure it has proper storage node
        working_volume = find_working_volume()
        if working_volume:
            # Ensure the volume has a storage node with proper filename
            storage_node = working_volume.GetStorageNode()
            if not storage_node:
                # Create a storage node if it doesn't exist
                storage_node = slicer.vtkMRMLNRRDStorageNode()
                slicer.mrmlScene.AddNode(storage_node)
                working_volume.SetAndObserveStorageNodeID(storage_node.GetID())
            
            # Set the filename to CT_Series.nrrd based on current volume name
            current_filename = storage_node.GetFileName() or ""
            current_name = working_volume.GetName()
            
            # Use CT_Series.nrrd as the filename regardless of volume name
            if not os.path.basename(current_filename).startswith("CT_Series"):
                storage_node.SetFileName("CT_Series.nrrd")
                print(f"Set volume '{current_name}' filename to: CT_Series.nrrd")
        
        # Get all storable nodes and ensure they have proper storage nodes
        all_nodes = []
        all_nodes.extend(slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode'))
        all_nodes.extend(slicer.util.getNodesByClass('vtkMRMLSegmentationNode'))
        all_nodes.extend(slicer.util.getNodesByClass('vtkMRMLMarkupsNode'))
        all_nodes.extend(slicer.util.getNodesByClass('vtkMRMLModelNode'))
        all_nodes.extend(slicer.util.getNodesByClass('vtkMRMLTransformNode'))
        
        nodes_prepared = 0
        for node in all_nodes:
            if hasattr(node, 'GetStorageNode'):
                storage_node = node.GetStorageNode()
                if not storage_node:
                    # Create appropriate storage node based on node type
                    if node.IsA('vtkMRMLScalarVolumeNode'):
                        storage_node = slicer.vtkMRMLNRRDStorageNode()
                    elif node.IsA('vtkMRMLSegmentationNode'):
                        storage_node = slicer.vtkMRMLSegmentationStorageNode()
                    elif node.IsA('vtkMRMLMarkupsNode'):
                        storage_node = slicer.vtkMRMLMarkupsStorageNode()
                    elif node.IsA('vtkMRMLModelNode'):
                        storage_node = slicer.vtkMRMLModelStorageNode()
                    elif node.IsA('vtkMRMLTransformNode'):
                        storage_node = slicer.vtkMRMLTransformStorageNode()
                    
                    if storage_node:
                        slicer.mrmlScene.AddNode(storage_node)
                        node.SetAndObserveStorageNodeID(storage_node.GetID())
                        nodes_prepared += 1
        
        print(f"Prepared {nodes_prepared} nodes for saving")
        return True
        
    except Exception as e:
        print(f"Error setting up storage nodes: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def show_pre_save_info():
    """
    Show information about what will be saved before opening the save dialog.
    """
    try:
        # Count all the saveable nodes in the scene
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        segmentation_nodes = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
        markup_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsNode')
        model_nodes = slicer.util.getNodesByClass('vtkMRMLModelNode')
        transform_nodes = slicer.util.getNodesByClass('vtkMRMLTransformNode')
        
        # Build the info message
        info_parts = []
        
        if volume_nodes:
            info_parts.append(f"• {len(volume_nodes)} Volume(s)")
            working_volume = find_working_volume()
            for vol in volume_nodes:
                if vol == working_volume:
                    info_parts.append(f"  - {vol.GetName()} → will be saved as CT_Series.nrrd")
                else:
                    info_parts.append(f"  - {vol.GetName()}")
        
        if segmentation_nodes:
            info_parts.append(f"• {len(segmentation_nodes)} Segmentation(s)")
            for seg in segmentation_nodes:
                info_parts.append(f"  - {seg.GetName()}")
        
        if markup_nodes:
            info_parts.append(f"• {len(markup_nodes)} Markup(s)")
            for markup in markup_nodes:
                info_parts.append(f"  - {markup.GetName()}")
        
        if model_nodes:
            info_parts.append(f"• {len(model_nodes)} Model(s)")
            for model in model_nodes:
                info_parts.append(f"  - {model.GetName()}")
        
        if transform_nodes:
            info_parts.append(f"• {len(transform_nodes)} Transform(s)")
            for transform in transform_nodes:
                info_parts.append(f"  - {transform.GetName()}")
        
        if info_parts:
            info_message = "The save dialog will open with ALL scene data selected for saving:\n\n" + "\n".join(info_parts)
            info_message += "\n\nAll files will be saved to the same directory for easy organization."
            print("=== SAVE INFORMATION ===")
            print(info_message)
            print("========================")
        
    except Exception as e:
        print(f"Could not show pre-save info: {str(e)}")

def open_save_dialog_with_all_selected():
    """
    Open the save dialog and attempt to automatically select all items.
    """
    try:
        # Method 1: Try using the IO manager with modification
        io_manager = slicer.app.ioManager()
        
        # Create a QTimer to select all items after the dialog opens
        def select_all_after_delay():
            try:
                # Find the save dialog window
                for widget in qt.QApplication.allWidgets():
                    if hasattr(widget, 'selectAll') and widget.windowTitle() and 'save' in widget.windowTitle().lower():
                        print("Found save dialog, attempting to select all items...")
                        widget.selectAll()
                        break
                    # Also try to find qSlicerSaveDataDialog specifically
                    elif widget.__class__.__name__ == 'qSlicerSaveDataDialog':
                        print("Found qSlicerSaveDataDialog, attempting to select all items...")
                        if hasattr(widget, 'selectAll'):
                            widget.selectAll()
                        break
            except Exception as select_error:
                print(f"Could not auto-select all items in save dialog: {str(select_error)}")
        
        # Schedule the selection after a short delay to allow dialog to fully open
        timer = qt.QTimer()
        timer.timeout.connect(select_all_after_delay)
        timer.setSingleShot(True)
        timer.start(500)  # 500ms delay
        
        # Open the standard save dialog
        success = io_manager.openSaveDataDialog()
        
        # Clean up the timer
        timer.timeout.disconnect()
        return success
        
    except Exception as e:
        print(f"Error opening save dialog with auto-select: {str(e)}")
        # Fallback to standard dialog
        try:
            return slicer.app.ioManager().openSaveDataDialog()
        except:
            return False

def custom_save_all_scene_data():
    """
    Custom save function that ensures all files in the scene are selected for saving
    and that CT_Series.nrrd is saved to the same directory as all other files.
    """
    try:
        # First, setup storage nodes for consistent saving
        setup_storage_nodes_for_consistent_saving()
        
        # Show information about what will be saved
        show_pre_save_info()
        
        # Use the standard save dialog, but it should now have proper storage nodes
        # Try to automatically select all items when the dialog opens
        success = open_save_dialog_with_all_selected()
        
        if success:
            # After successful save, verify that CT_Series was saved properly
            scene_path = slicer.mrmlScene.GetURL()
            if scene_path:
                if scene_path.startswith("file://"):
                    scene_path = scene_path[7:]  # Remove "file://" prefix
                    
                scene_dir = os.path.dirname(scene_path)
                print(f"Scene saved to directory: {scene_dir}")
                
                # List all files saved in the directory
                try:
                    files_in_dir = os.listdir(scene_dir)
                    scene_files = [f for f in files_in_dir if not f.startswith('.')]
                    print(f"Files saved in scene directory: {scene_files}")
                    
                    # Check if CT_Series.nrrd exists
                    ct_series_files = [f for f in scene_files if f.startswith("CT_Series") and f.endswith('.nrrd')]
                    if ct_series_files:
                        print(f"✓ CT_Series volume saved as: {ct_series_files[0]}")
                    else:
                        # Try to find any .nrrd file that might be the CT volume
                        nrrd_files = [f for f in scene_files if f.endswith('.nrrd')]
                        if nrrd_files:
                            print(f"Found .nrrd files: {nrrd_files}")
                            # If there's exactly one .nrrd file, it's likely the CT volume
                            if len(nrrd_files) == 1:
                                old_path = os.path.join(scene_dir, nrrd_files[0])
                                new_path = os.path.join(scene_dir, "CT_Series.nrrd")
                                try:
                                    os.rename(old_path, new_path)
                                    print(f"Renamed {nrrd_files[0]} to CT_Series.nrrd")
                                except Exception as rename_error:
                                    print(f"Could not rename {nrrd_files[0]} to CT_Series.nrrd: {str(rename_error)}")
                        else:
                            print("Warning: No .nrrd files found in save directory")
                            
                except Exception as dir_error:
                    print(f"Could not list directory contents: {str(dir_error)}")
            
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error in custom save function: {str(e)}")
        import traceback
        traceback.print_exc()
        # Fallback to standard save dialog
        try:
            return slicer.app.ioManager().openSaveDataDialog()
        except:
            return False

def test_custom_save_functionality():
    """
    Test function to verify the custom save functionality works properly.
    Usage: test_custom_save_functionality()
    """
    try:
        print("Testing custom save functionality...")
        
        # Show what's in the scene
        show_pre_save_info()
        
        # Test storage node setup
        setup_result = setup_storage_nodes_for_consistent_saving()
        print(f"Storage nodes setup result: {setup_result}")
        
        # Test finding working volume
        working_vol = find_working_volume()
        if working_vol:
            print(f"Working volume found: {working_vol.GetName()}")
        else:
            print("No working volume found")
        
        print("Custom save functionality test completed.")
        return True
        
    except Exception as e:
        print(f"Error testing custom save functionality: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def manual_export_with_ct_series():
    """
    Manual export function that can be called from console to test the new export functionality.
    Usage: manual_export_with_ct_series()
    """
    try:
        print("Starting manual export with CT_Series handling...")
        result = custom_save_all_scene_data()
        return result
    except Exception as e:
        print(f"Error in manual export: {str(e)}")
        return False

def check_ct_series_setup():
    """
    Console function to check if CT_Series volume is properly set up for saving.
    Usage: check_ct_series_setup()
    """
    try:
        print("=== CT_Series Setup Check ===")
        
        # Find working volume
        working_vol = find_working_volume()
        if not working_vol:
            return False
        
        print(f"Working volume: {working_vol.GetName()}")
        
        # Note: Volume name is preserved, but will be saved as CT_Series.nrrd
        print(f"✓ Volume '{working_vol.GetName()}' will be saved as CT_Series.nrrd")
        
        # Check storage node
        storage_node = working_vol.GetStorageNode()
        if storage_node:
            filename = storage_node.GetFileName()
            print(f"✓ Storage node exists with filename: {filename}")
            
            if filename and os.path.basename(filename).startswith("CT_Series"):
                print("✓ Storage filename is properly set for CT_Series")
            else:
                print("⚠ Storage filename should be set to CT_Series.nrrd")
        else:
            print("⚠ No storage node found - will be created during save")
        
        # Count all saveable nodes
        all_volumes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        all_segs = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
        all_markups = slicer.util.getNodesByClass('vtkMRMLMarkupsNode')
        all_models = slicer.util.getNodesByClass('vtkMRMLModelNode')
        
        total_nodes = len(all_volumes) + len(all_segs) + len(all_markups) + len(all_models)
        print(f"Total saveable nodes in scene: {total_nodes}")
        print(f"  - Volumes: {len(all_volumes)}")
        print(f"  - Segmentations: {len(all_segs)}")
        print(f"  - Markups: {len(all_markups)}")
        print(f"  - Models: {len(all_models)}")
        
        print("==============================")
        return True
        
    except Exception as e:
        print(f"Error checking CT_Series setup: {str(e)}")
        return False

def close_slicer_after_export():
    """
    Close Slicer application after successful export and workflow completion.
    Simple and reliable exit using os._exit(0).
    """

    import os
    os._exit(0)
        

def export_project_and_continue():
    """
    Save the Slicer project using custom save functionality and continue to workflow2.py
    """
    try:
        # Clean up any orphaned start markers before export
        cleanup_orphaned_start_markers()
        
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        lesion_analysis_nodes = []
        
        for node in fiducial_nodes:
            node_name = node.GetName()
            if node_name == "F-1":
                lesion_analysis_nodes.append(node)
        
        if not lesion_analysis_nodes:
            pass
        else:
            total_points = sum(node.GetNumberOfControlPoints() for node in lesion_analysis_nodes)
            pass

        # Remove transforms from point lists before saving
        if lesion_analysis_nodes:
            pass
            
            transforms_removed = remove_transforms_from_point_lists()
            
            if not transforms_removed:
                pass
                force_remove_all_transforms()
            
            pass
            verification_passed = verify_pre_post_lesion_points_transform_free()
            
            if not verification_passed:
                pass
                force_remove_all_transforms()
                verification_passed = verify_pre_post_lesion_points_transform_free()
                
            if verification_passed:
                pass
            else:
                pass
            
            pass

        # Use custom save function that ensures all files are selected and CT_Series is properly named
        success = custom_save_all_scene_data()
        
        if success:
            # Get the scene file path after successful save
            try:
                scene_path = slicer.mrmlScene.GetURL()
                if scene_path:
                    # Convert file:// URL to local path if needed
                    if scene_path.startswith("file://"):
                        scene_path = scene_path[7:]  # Remove "file://" prefix
                    save_scene_location_to_user_home(scene_path)
                else:
                    print("Warning: Could not determine scene save location")
            except Exception as e:
                print(f"Error saving scene location: {str(e)}")
            
            # Deselect placement tools and return to normal interaction mode
            pass
            disable_all_placement_tools()

            # Reapply transforms after saving
            if lesion_analysis_nodes:
                pass
                reapply_transforms_to_point_lists()
                reapply_transforms_to_circles()

            pass
            cleanup_all_workflow_ui()

            # Run workflow2 functionality directly
            try:
                pass
                create_centerline_and_tube_mask()
                
            except Exception as e:
                pass
                slicer.util.errorDisplay(f"Could not run workflow2 functionality: {str(e)}\n\nPlease check the console for details.")
            
            # Close Slicer after successful save and workflow completion
            close_slicer_after_export()
            
        else:
            pass
            # Still deselect tools even if save was cancelled
            pass
            disable_all_placement_tools()
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not export project: {str(e)}")

def cleanup_all_workflow_ui():
    """
    Clean up all workflow UI elements before continuing to workflow2
    """
    try:
        cleanup_point_placement_ui()
        cleanup_workflow_ui()
        cleanup_continue_ui()
        cleanup_centerline_monitoring_button()
        stop_apply_button_monitoring()
        
        if hasattr(slicer.modules, 'CenterlineMonitorTimer'):
            timer = slicer.modules.CenterlineMonitorTimer
            timer.stop()
            timer.timeout.disconnect()
            del slicer.modules.CenterlineMonitorTimer
        
        if hasattr(slicer.modules, 'CropMonitorTimer'):
            timer = slicer.modules.CropMonitorTimer
            timer.stop()
            timer.timeout.disconnect()
            del slicer.modules.CropMonitorTimer
        
        pass
        
    except Exception as e:
        pass


def show_centerline_completion_dialog(centerline_model=None, centerline_curve=None):
    """
    Show a dialog asking user to retry centerline extraction, add more centerlines, or continue to CPR
    """
    try:
        dialog = qt.QDialog(slicer.util.mainWindow())
        dialog.setWindowTitle("Centerline Extraction Complete")
        dialog.setModal(True)
        dialog.resize(500, 400)
        dialog.setWindowFlags(qt.Qt.Dialog | qt.Qt.WindowTitleHint | qt.Qt.WindowCloseButtonHint)
        layout = qt.QVBoxLayout(dialog)
        title_label = qt.QLabel("Centerline Extraction Completed Successfully!")
        title_label.setStyleSheet("QLabel { font-weight: bold; color: #28a745; margin: 10px; font-size: 16px; }")
        title_label.setAlignment(qt.Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Show current centerline info
        status_text = "Latest centerline extraction completed:"
        if centerline_model and centerline_curve:
            status_text += f"\n\n✓ Model created: {centerline_model.GetName()}"
            status_text += f"\n✓ Curve created: {centerline_curve.GetName()}"
        elif centerline_model:
            status_text += f"\n\n✓ Model created: {centerline_model.GetName()}"
        elif centerline_curve:
            status_text += f"\n\n✓ Curve created: {centerline_curve.GetName()}"
        
        status_label = qt.QLabel(status_text)
        status_label.setStyleSheet("QLabel { color: #333; margin: 10px; font-size: 12px; }")
        status_label.setWordWrap(True)
        layout.addWidget(status_label)
        
        # Show summary of all centerlines if there are multiple
        all_models = find_all_centerline_models()
        all_curves = find_all_centerline_curves()
        total_centerlines = max(len(all_models), len(all_curves))
        
        if total_centerlines > 1:
            summary_text = f"\nTotal centerlines in scene: {total_centerlines}"
            if centerline_curve:
                summary_text += f"\nAnalysis will use: {centerline_curve.GetName()}"
            summary_label = qt.QLabel(summary_text)
            summary_label.setStyleSheet("QLabel { color: #666; margin: 5px 10px; font-size: 11px; font-weight: bold; }")
            layout.addWidget(summary_label)
        
        layout.addSpacing(10)
        instruction_label = qt.QLabel("Choose your next action:")
        instruction_label.setStyleSheet("QLabel { color: #555; margin: 10px; font-size: 12px; font-weight: bold; }")
        layout.addWidget(instruction_label)
        
        # Create four rows of buttons
        first_row_layout = qt.QHBoxLayout()
        second_row_layout = qt.QHBoxLayout()
        third_row_layout = qt.QHBoxLayout()
        fourth_row_layout = qt.QHBoxLayout()
        
        retry_button = qt.QPushButton("Retry Centerline Extraction")
        retry_button.setStyleSheet("""
            QPushButton { 
                background-color: #ffc107; 
                color: #212529; 
                border: none; 
                padding: 12px 20px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 13px;
                min-width: 180px;
            }
            QPushButton:hover { 
                background-color: #e0a800; 
            }
            QPushButton:pressed { 
                background-color: #d39e00; 
            }
        """)
        retry_button.connect('clicked()', lambda: on_retry_centerline(dialog))
        first_row_layout.addWidget(retry_button)
        
        add_centerline_button = qt.QPushButton("+ Add More Centerlines")
        add_centerline_button.setStyleSheet("""
            QPushButton { 
                background-color: #17a2b8; 
                color: white; 
                border: none; 
                padding: 12px 20px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 13px;
                min-width: 180px;
            }
            QPushButton:hover { 
                background-color: #138496; 
            }
            QPushButton:pressed { 
                background-color: #117a8b; 
            }
        """)
        add_centerline_button.connect('clicked()', lambda: on_add_more_centerlines(dialog))
        first_row_layout.addWidget(add_centerline_button)
        
        # Add the new Verify and Edit Centerline button
        verify_edit_button = qt.QPushButton("Verify & Edit Centerline")
        verify_edit_button.setStyleSheet("""
            QPushButton { 
                background-color: #fd7e14; 
                color: white; 
                border: none; 
                padding: 12px 20px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 13px;
                min-width: 380px;
            }
            QPushButton:hover { 
                background-color: #e8590c; 
            }
            QPushButton:pressed { 
                background-color: #dc5200; 
            }
        """)
        verify_edit_button.connect('clicked()', lambda: on_verify_edit_centerline(dialog, centerline_model, centerline_curve))
        second_row_layout.addWidget(verify_edit_button)
        
        restart_crop_button = qt.QPushButton("Restart Cropping")
        restart_crop_button.setStyleSheet("""
            QPushButton { 
                background-color: #6f42c1; 
                color: white; 
                border: none; 
                padding: 12px 20px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 13px;
                min-width: 380px;
            }
            QPushButton:hover { 
                background-color: #5a32a3; 
            }
            QPushButton:pressed { 
                background-color: #4e2a8e; 
            }
        """)
        restart_crop_button.connect('clicked()', lambda: on_restart_cropping(dialog, centerline_model, centerline_curve))
        third_row_layout.addWidget(restart_crop_button)
        
        continue_button = qt.QPushButton("Continue to Analysis")
        continue_button.setStyleSheet("""
            QPushButton { 
                background-color: #28a745; 
                color: white; 
                border: none; 
                padding: 12px 20px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 13px;
                min-width: 380px;
            }
            QPushButton:hover { 
                background-color: #218838; 
            }
            QPushButton:pressed { 
                background-color: #1e7e34; 
            }
        """)
        continue_button.connect('clicked()', lambda: on_continue_to_cpr(dialog, centerline_model, centerline_curve))
        fourth_row_layout.addWidget(continue_button)
        
        layout.addLayout(first_row_layout)
        layout.addLayout(second_row_layout)
        layout.addLayout(third_row_layout)
        layout.addLayout(fourth_row_layout)
        layout.addStretch()
        dialog.exec_()
        
    except Exception as e:
        pass
        switch_to_cpr_module(centerline_model, centerline_curve)

def on_retry_centerline(dialog):
    """
    Called when user chooses to retry centerline extraction
    """
    try:
        # Stop ALL centerline monitoring systems to prevent double dialogs
        stop_all_centerline_monitoring()
        
        # Reset the dialog flag to allow future dialogs
        if hasattr(slicer.modules, 'CenterlineDialogShown'):
            slicer.modules.CenterlineDialogShown = False
        
        dialog.close()
        dialog.setParent(None)
        
        clear_existing_centerlines()
        slicer.util.infoDisplay(
            "Returning to centerline extraction.\n\n"
            "You can adjust your endpoints or segmentation if needed,\n"
            "then click 'Apply' again to re-extract the centerline.\n\n"
            "The workflow will continue monitoring for completion."
        )
        
        setup_centerline_completion_monitor()
    except Exception as e:
        pass

        


def on_continue_to_cpr(dialog, centerline_model=None, centerline_curve=None):
    """
    Called when user chooses to continue to CPR analysis
    """
    try:
        if hasattr(slicer.modules, 'CenterlineDialogShown'):
            slicer.modules.CenterlineDialogShown = False
        
        dialog.close()
        dialog.setParent(None)
        switch_to_cpr_module(centerline_model, centerline_curve)
        
        draw_circles_on_centerline()
    except Exception as e:
        pass


def on_add_more_centerlines(dialog):
    """
    Called when user chooses to add more centerlines
    """
    try:
        # Stop ALL centerline monitoring systems to prevent double dialogs
        stop_all_centerline_monitoring()
        
        # Reset the dialog flag to allow future dialogs
        if hasattr(slicer.modules, 'CenterlineDialogShown'):
            slicer.modules.CenterlineDialogShown = False
        
        dialog.close()
        dialog.setParent(None)
        
        # Create a new centerline extraction setup for additional centerlines
        create_additional_centerline_setup()
    except Exception as e:
        pass
        

def on_verify_edit_centerline(dialog, centerline_model=None, centerline_curve=None):
    """
    Called when user chooses to verify and edit the centerline points.
    Opens an editing interface to allow manual adjustment of centerline points.
    """
    try:
        # Stop ALL centerline monitoring systems to prevent double dialogs
        stop_all_centerline_monitoring()
        
        # Reset the dialog flag to allow future dialogs
        if hasattr(slicer.modules, 'CenterlineDialogShown'):
            slicer.modules.CenterlineDialogShown = False
        
        dialog.close()
        dialog.setParent(None)
        
        # Show the centerline editing dialog
        show_centerline_editing_dialog(centerline_model, centerline_curve)
        
    except Exception as e:
        pass
        # Fallback - go to CPR module if editing fails
        switch_to_cpr_module(centerline_model, centerline_curve)


def show_centerline_editing_dialog(centerline_model=None, centerline_curve=None):
    """
    Show a dialog for editing centerline points with options to extract new centerline or continue to CPR
    """
    try:
        # Find the most recent centerline curve if none provided
        if not centerline_curve:
            centerline_curve = find_recent_centerline_curve()
            
        # Also check for all available centerline curves as fallback
        if not centerline_curve:
            all_curves = find_all_centerline_curves()
            # Try to find any centerline curve in the scene as fallback
            if all_curves:
                centerline_curve = all_curves[-1]  # Use the last one
            else:
                qt.QMessageBox.warning(
                    slicer.util.mainWindow(),
                    "No Centerline Found",
                    "No centerline curve found to edit. Please extract a centerline first."
                )
                return
        
        # Create the editing panel as a docked side panel
        main_window = slicer.util.mainWindow()
        edit_dialog = qt.QDockWidget("Verify and Edit Centerline", main_window)
        edit_dialog.setFeatures(qt.QDockWidget.DockWidgetMovable | qt.QDockWidget.DockWidgetFloatable | qt.QDockWidget.DockWidgetClosable)
        edit_dialog.setAllowedAreas(qt.Qt.LeftDockWidgetArea | qt.Qt.RightDockWidgetArea)
        
        # Create the main widget for the dock
        dock_widget = qt.QWidget()
        edit_dialog.setWidget(dock_widget)
        
        layout = qt.QVBoxLayout(dock_widget)
        
        # Title and instructions
        title_label = qt.QLabel("Centerline Verification and Editing")
        title_label.setStyleSheet("QLabel { font-weight: bold; color: #dc3545; margin: 10px; font-size: 16px; }")
        title_label.setAlignment(qt.Qt.AlignCenter)
        layout.addWidget(title_label)
        
        instructions_text = (
            "Red slice view maximized for optimal centerline editing.\n\n"
            "Editing controls:\n"
            "• Drag control points to move them\n"
            "• Right-click curve → 'Add Point'\n"
            "• Right-click point → 'Delete Point'\n"
            "• Scroll to navigate through slices\n"
            "• Use left panel Markups controls\n\n"
            "Choose your next action:\n"
            "• Add Additional: Saves current edits, lets you add more centerlines\n"
            "• Replace with New: Discards current centerline, starts fresh\n"
            "• Continue to Analysis: Use current centerline for measurements"
        )
        
        instructions_label = qt.QLabel(instructions_text)
        instructions_label.setStyleSheet("QLabel { color: #333; margin: 10px; font-size: 12px; line-height: 18px; }")
        instructions_label.setWordWrap(True)
        layout.addWidget(instructions_label)
        
        # Info about the current centerline and scene status
        if centerline_curve:
            num_points = centerline_curve.GetNumberOfControlPoints()
            
            # Safely get curve length
            try:
                if hasattr(centerline_curve, 'GetCurveLengthWorld'):
                    curve_length = centerline_curve.GetCurveLengthWorld()
                else:
                    curve_length = centerline_curve.GetCurveLength()
            except:
                curve_length = 0.0
            
            # Count total centerlines in scene
            all_centerlines = find_all_centerline_curves()
            total_centerlines = len(all_centerlines)
            
            info_text = f"Current centerline: {centerline_curve.GetName()}\n"
            info_text += f"Control points: {num_points}\n"
            info_text += f"Curve length: {curve_length:.2f} mm\n"
            info_text += f"Total centerlines in scene: {total_centerlines}"
            
            info_label = qt.QLabel(info_text)
            info_label.setStyleSheet("QLabel { color: #666; margin: 5px; font-size: 10px; font-family: monospace; background-color: #f8f9fa; padding: 6px; border-radius: 4px; }")
            layout.addWidget(info_label)
        
        layout.addSpacing(15)
        
        # Action buttons
        button_layout1 = qt.QHBoxLayout()
        button_layout2 = qt.QHBoxLayout()
        
        # Add Additional Centerline button (saves current edits)
        add_additional_button = qt.QPushButton("Add Additional\nCenterline")
        add_additional_button.setStyleSheet("""
            QPushButton { 
                background-color: #17a2b8; 
                color: white; 
                border: none; 
                padding: 10px 8px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 3px;
                font-size: 12px;
                min-height: 50px;
            }
            QPushButton:hover { 
                background-color: #138496; 
            }
            QPushButton:pressed { 
                background-color: #117a8b; 
            }
        """)
        add_additional_button.connect('clicked()', lambda: on_add_additional_centerline_from_edit(edit_dialog, centerline_curve))
        button_layout1.addWidget(add_additional_button)
        
        # Extract new centerline button (replaces current)
        extract_new_button = qt.QPushButton("Replace with New\nCenterline")
        extract_new_button.setStyleSheet("""
            QPushButton { 
                background-color: #ffc107; 
                color: #212529; 
                border: none; 
                padding: 10px 8px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 3px;
                font-size: 12px;
                min-height: 50px;
            }
            QPushButton:hover { 
                background-color: #e0a800; 
            }
            QPushButton:pressed { 
                background-color: #d39e00; 
            }
        """)
        extract_new_button.connect('clicked()', lambda: on_extract_new_centerline_from_edit(edit_dialog, centerline_curve))
        button_layout1.addWidget(extract_new_button)
        
        # Continue to CPR button
        continue_cpr_button = qt.QPushButton("Continue to\nAnalysis")
        continue_cpr_button.setStyleSheet("""
            QPushButton { 
                background-color: #28a745; 
                color: white; 
                border: none; 
                padding: 10px 8px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 3px;
                font-size: 12px;
                min-height: 50px;
            }
            QPushButton:hover { 
                background-color: #218838; 
            }
            QPushButton:pressed { 
                background-color: #1e7e34; 
            }
        """)
        continue_cpr_button.connect('clicked()', lambda: on_continue_to_cpr_from_edit(edit_dialog, centerline_model, centerline_curve))
        button_layout2.addWidget(continue_cpr_button)
        
        # Reset centerline button
        reset_button = qt.QPushButton("Reset to Original")
        reset_button.setStyleSheet("""
            QPushButton { 
                background-color: #6c757d; 
                color: white; 
                border: none; 
                padding: 8px 8px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 3px;
                font-size: 11px;
                min-height: 35px;
            }
            QPushButton:hover { 
                background-color: #5a6268; 
            }
            QPushButton:pressed { 
                background-color: #545b62; 
            }
        """)
        reset_button.connect('clicked()', lambda: on_reset_centerline_to_original_in_edit(centerline_curve, info_label))
        button_layout2.addWidget(reset_button)
        
        layout.addLayout(button_layout1)
        layout.addLayout(button_layout2)
        
        # Add close button
        close_layout = qt.QHBoxLayout()
        close_button = qt.QPushButton("Close Editor")
        close_button.setStyleSheet("""
            QPushButton { 
                background-color: #dc3545; 
                color: white; 
                border: none; 
                padding: 8px 8px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 3px;
                font-size: 11px;
                min-height: 35px;
            }
            QPushButton:hover { 
                background-color: #c82333; 
            }
            QPushButton:pressed { 
                background-color: #bd2130; 
            }
        """)
        close_button.connect('clicked()', lambda: on_close_centerline_editor(edit_dialog, centerline_curve))
        close_layout.addWidget(close_button)
        
        layout.addLayout(close_layout)
        layout.addStretch()
        
        # Note: Skip custom closeEvent handling to avoid Qt slot override issues
        # The close button and user actions will handle cleanup properly
        
        # Enable editing on the centerline curve
        enable_centerline_editing(centerline_curve)
        
        # Dock the panel to the right side and show it
        main_window.addDockWidget(qt.Qt.RightDockWidgetArea, edit_dialog)
        edit_dialog.show()
        
        # Make the dock widget compact
        edit_dialog.setMinimumWidth(300)
        edit_dialog.setMaximumWidth(400)
        
        # Store reference to dialog for cleanup
        slicer.modules.CenterlineEditDialog = edit_dialog
        
    except Exception as e:
        # Show error message and continue
        error_msg = f"Failed to open centerline editing interface.\n\nError: {str(e)}\n\nContinuing to analysis..."
        qt.QMessageBox.critical(
            slicer.util.mainWindow(),
            "Editing Error",
            error_msg
        )
        switch_to_cpr_module(centerline_model, centerline_curve)


def enable_centerline_editing(centerline_curve):
    """
    Enable interactive editing of the centerline curve points
    """
    try:
        if not centerline_curve:
            return
        
        # Store current layout for restoration later
        layout_manager = slicer.app.layoutManager()
        if layout_manager:
            current_layout = layout_manager.layout
            slicer.modules.CenterlineEditingOriginalLayout = current_layout
        
        # Switch to cross-sectional view layout for better editing
        switch_to_crosssectional_fullscreen()
        
        # Make the curve visible and editable with all control points visible
        display_node = centerline_curve.GetDisplayNode()
        if display_node:
            display_node.SetVisibility(True)
            display_node.SetPropertiesLabelVisibility(True)
            display_node.SetPointLabelsVisibility(True)
            display_node.SetTextScale(3.0)  # Larger text for better visibility
            display_node.SetGlyphScale(3.0)  # Larger control points for easier interaction
            display_node.SetSelectedColor(1.0, 0.0, 0.0)  # Red for selected points
            display_node.SetActiveColor(0.0, 1.0, 0.0)  # Green for active points
            display_node.SetColor(0.0, 0.8, 1.0)  # Cyan for normal points
            display_node.SetOpacity(1.0)  # Full opacity
            display_node.SetLineThickness(0.3)  # Thicker line for better visibility
            
            # Set glyph type to sphere for better visibility
            try:
                display_node.SetGlyphType(slicer.vtkMRMLMarkupsDisplayNode.Sphere3D)
            except:
                pass  # Continue if glyph type setting fails
            
        # Ensure all control points are visible
        for i in range(centerline_curve.GetNumberOfControlPoints()):
            centerline_curve.SetNthControlPointVisibility(i, True)
            
        # Enable interaction and place mode
        centerline_curve.SetLocked(False)
        
        # Set the curve as the active markups node for editing
        selection_node = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selection_node:
            selection_node.SetReferenceActivePlaceNodeID(centerline_curve.GetID())
        
        # Switch to markups module to show editing controls
        try:
            slicer.util.selectModule("Markups")
        except Exception as module_error:
            pass  # Continue even if module switch fails
        
        # Center the view on the centerline
        if centerline_curve.GetNumberOfControlPoints() > 0:
            try:
                # Get the center point of the curve
                bounds = [0, 0, 0, 0, 0, 0]
                centerline_curve.GetBounds(bounds)
                center = [(bounds[0] + bounds[1]) / 2, 
                         (bounds[2] + bounds[3]) / 2, 
                         (bounds[4] + bounds[5]) / 2]
                
                # Center all views on the centerline
                for viewNode in slicer.util.getNodesByClass('vtkMRMLAbstractViewNode'):
                    if viewNode.IsA('vtkMRMLSliceNode'):
                        try:
                            viewNode.JumpSliceByOffsetting(center[0], center[1], center[2])
                        except:
                            pass  # Continue if view centering fails
            except:
                pass  # Continue if bounds calculation fails
        
        # Show information message
        slicer.util.infoDisplay(
            "Centerline editing mode enabled!\n\n"
            "✓ View switched to maximized Red slice for optimal editing\n"
            "✓ All control points are now large, visible, and editable\n"
            "✓ The editing panel is docked on the right side\n\n"
            "Edit the centerline by:\n"
            "• Clicking and dragging control points to move them\n"
            "• Right-clicking on the curve to add new points\n"
            "• Right-clicking on points to delete them\n"
            "• Using the Markups module controls in the left panel\n"
            "• Scrolling through slices to verify positioning\n\n"
            "When finished editing, use the buttons in the side panel.\n"
            "The view will automatically switch to 3D fullscreen when you continue."
        )
        
    except Exception as e:
        raise  # Re-raise the exception so it gets caught by the calling function


def on_extract_new_centerline_from_edit(dock_widget, original_curve):
    """
    Called when user wants to extract a new centerline after editing
    """
    try:
        # Close and cleanup the dock widget
        cleanup_centerline_edit_dialog()
        
        # Exit editing mode and return to appropriate view
        disable_centerline_editing(original_curve)
        
        # Clear existing centerlines
        clear_existing_centerlines()
        
        # Return to centerline extraction module
        open_centerline_module()
        
        # Return to centerline extraction
        slicer.util.infoDisplay(
            "Returning to centerline extraction.\n\n"
            "You can now adjust your endpoints or segmentation if needed,\n"
            "then click 'Apply' again to extract a new centerline.\n\n"
            "The edited centerline has been removed."
        )
        
        # Set up monitoring for new centerline completion
        setup_centerline_completion_monitor()
        
    except Exception as e:
        pass


def on_add_additional_centerline_from_edit(dock_widget, original_curve):
    """
    Called when user wants to add additional centerlines while preserving the edited one
    """
    try:
        # Save the current edited centerline with a specific name
        save_edited_centerline_as_final(original_curve)
        
        # Close and cleanup the dock widget
        cleanup_centerline_edit_dialog()
        
        # Exit editing mode and return to appropriate view
        disable_centerline_editing(original_curve)
        
        # Return to centerline extraction module (don't clear existing centerlines)
        open_centerline_module()
        
        # Inform user about the preserved centerline
        slicer.util.infoDisplay(
            "Edited centerline saved and preserved!\n\n"
            "Your edited centerline has been saved and will remain in the scene.\n"
            "You can now add additional centerlines if needed.\n\n"
            "To add more centerlines:\n"
            "• Place new endpoints on the volume\n"
            "• Click 'Apply' to extract additional centerlines\n"
            "• When finished, all centerlines will be available for analysis\n\n"
            "The most recent centerline will be used by default for analysis."
        )
        
        # Set up monitoring for new centerline completion
        setup_centerline_completion_monitor()
        
    except Exception as e:
        pass


def on_continue_to_cpr_from_edit(dock_widget, centerline_model, centerline_curve):
    """
    Called when user wants to continue to CPR analysis with the edited centerline
    """
    try:
        # Close and cleanup the dock widget
        cleanup_centerline_edit_dialog()
        
        # Disable editing mode and switch to 3D fullscreen
        disable_centerline_editing(centerline_curve)
        
        # Continue to CPR with the edited centerline
        switch_to_cpr_module(centerline_model, centerline_curve)
        
        # Show circles on the centerline for analysis
        draw_circles_on_centerline()
        
    except Exception as e:
        pass


def on_reset_centerline_to_original(centerline_curve):
    """
    Called when user wants to reset the centerline to its original state
    """
    try:
        if not centerline_curve:
            return
        
        # Check if we have a backup of the original centerline
        curve_id = centerline_curve.GetID()
        backup_key = f"OriginalCenterlineBackup_{curve_id}"
        
        if hasattr(slicer.modules, backup_key):
            original_points = getattr(slicer.modules, backup_key)
            
            # Clear current points
            centerline_curve.RemoveAllControlPoints()
            
            # Restore original points
            for point in original_points:
                centerline_curve.AddControlPoint(point)
                
            slicer.util.infoDisplay("Centerline reset to original state.")
        else:
            qt.QMessageBox.information(
                slicer.util.mainWindow(),
                "Reset Not Available",
                "Original centerline backup not found. Cannot reset to original state."
            )
    
    except Exception as e:
        pass


def backup_centerline_points(centerline_curve):
    """
    Create a backup of the centerline control points for potential reset functionality
    """
    try:
        if not centerline_curve or centerline_curve.GetNumberOfControlPoints() == 0:
            return
        
        # Create a list to store the original points
        original_points = []
        
        # Store each control point
        for i in range(centerline_curve.GetNumberOfControlPoints()):
            point = [0, 0, 0]
            centerline_curve.GetNthControlPointPosition(i, point)
            original_points.append(point[:])  # Make a copy of the point
        
        # Store the backup using the curve ID to make it specific to this centerline
        curve_id = centerline_curve.GetID()
        backup_key = f"OriginalCenterlineBackup_{curve_id}"
        setattr(slicer.modules, backup_key, original_points)
        
        pass  # Backup created successfully
        
    except Exception as e:
        pass


def save_edited_centerline_as_final(centerline_curve):
    """
    Save the current edited centerline with a descriptive name to preserve it
    """
    try:
        if not centerline_curve or centerline_curve.GetNumberOfControlPoints() == 0:
            return
        
        # Get current timestamp for unique naming
        import datetime
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        
        # Rename the centerline to indicate it's been edited and finalized
        original_name = centerline_curve.GetName()
        if "edited" not in original_name.lower():
            new_name = f"{original_name}_Edited_{timestamp}"
        else:
            new_name = f"{original_name}_{timestamp}"
        
        centerline_curve.SetName(new_name)
        
        # Ensure the curve is visible and properly styled for preservation
        display_node = centerline_curve.GetDisplayNode()
        if display_node:
            display_node.SetVisibility(True)
            display_node.SetColor(0.0, 0.8, 0.2)  # Green color to indicate finalized
            display_node.SetOpacity(0.8)
            display_node.SetLineThickness(0.3)
            
        # Lock the curve to prevent accidental modifications
        centerline_curve.SetLocked(True)
        
        # Hide control points since it's finalized
        for i in range(centerline_curve.GetNumberOfControlPoints()):
            centerline_curve.SetNthControlPointVisibility(i, False)
            
        # Store this as a preserved centerline for future reference
        if not hasattr(slicer.modules, 'PreservedCenterlines'):
            slicer.modules.PreservedCenterlines = []
        slicer.modules.PreservedCenterlines.append(centerline_curve)
        
        pass  # Centerline saved successfully
        
    except Exception as e:
        pass


def cleanup_centerline_edit_dialog():
    """
    Clean up the centerline edit dialog reference and remove dock widget
    """
    try:
        if hasattr(slicer.modules, 'CenterlineEditDialog'):
            dock_widget = slicer.modules.CenterlineEditDialog
            if dock_widget:
                main_window = slicer.util.mainWindow()
                if main_window:
                    main_window.removeDockWidget(dock_widget)
                dock_widget.setParent(None)
            delattr(slicer.modules, 'CenterlineEditDialog')
    except Exception as e:
        pass


def on_reset_centerline_to_original_in_edit(centerline_curve, info_label):
    """
    Called when user wants to reset the centerline to its original state during editing.
    Updates the dialog with new information after reset.
    """
    try:
        if not centerline_curve:
            return
        
        # Check if we have a backup of the original centerline
        curve_id = centerline_curve.GetID()
        backup_key = f"OriginalCenterlineBackup_{curve_id}"
        
        if hasattr(slicer.modules, backup_key):
            original_points = getattr(slicer.modules, backup_key)
            
            # Clear current points
            centerline_curve.RemoveAllControlPoints()
            
            # Restore original points
            for point in original_points:
                centerline_curve.AddControlPoint(point)
            
            # Update the info label with new stats
            num_points = centerline_curve.GetNumberOfControlPoints()
            
            # Safely get curve length
            try:
                if hasattr(centerline_curve, 'GetCurveLengthWorld'):
                    curve_length = centerline_curve.GetCurveLengthWorld()
                else:
                    curve_length = centerline_curve.GetCurveLength()
            except:
                curve_length = 0.0
            
            # Count total centerlines in scene
            all_centerlines = find_all_centerline_curves()
            total_centerlines = len(all_centerlines)
            
            info_text = f"Current centerline: {centerline_curve.GetName()}\n"
            info_text += f"Control points: {num_points}\n"
            info_text += f"Curve length: {curve_length:.2f} mm\n"
            info_text += f"Total centerlines in scene: {total_centerlines}"
            info_label.setText(info_text)
                
            slicer.util.infoDisplay("Centerline reset to original state.", windowTitle="Reset Complete")
        else:
            qt.QMessageBox.information(
                slicer.util.mainWindow(),
                "Reset Not Available",
                "Original centerline backup not found. Cannot reset to original state."
            )
    
    except Exception as e:
        pass


def on_close_centerline_editor(dock_widget, centerline_curve):
    """
    Called when user clicks the close editor button
    """
    try:
        # Exit editing mode and return to 3D fullscreen
        disable_centerline_editing(centerline_curve)
        
        # Close and cleanup dock widget
        cleanup_centerline_edit_dialog()
        
        slicer.util.infoDisplay("Centerline editor closed. Returned to 3D view. You can now continue with your workflow.")
        
    except Exception as e:
        pass





def disable_centerline_editing(centerline_curve):
    """
    Disable editing mode for the centerline curve and switch to 3D fullscreen view
    """
    try:
        if centerline_curve:
            # Lock the curve and hide editing controls
            centerline_curve.SetLocked(True)
            display_node = centerline_curve.GetDisplayNode()
            if display_node:
                display_node.SetPropertiesLabelVisibility(False)
                display_node.SetPointLabelsVisibility(False)
                
            # Hide all control points
            for i in range(centerline_curve.GetNumberOfControlPoints()):
                centerline_curve.SetNthControlPointVisibility(i, False)
        
        # Clear active markups selection to exit editing mode
        selection_node = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selection_node:
            selection_node.SetReferenceActivePlaceNodeID(None)
            
        # Switch to 3D fullscreen view
        switch_to_3d_fullscreen()
        
    except Exception as e:
        pass


def switch_to_crosssectional_fullscreen():
    """
    Switch to Red slice view maximized for centerline editing
    """
    try:
        layout_manager = slicer.app.layoutManager()
        if not layout_manager:
            return
            
        # Set to Red slice view only for maximum editing space
        layout_manager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
        
        # Allow the layout to update
        slicer.app.processEvents()
        
        # Fit Red slice view to window and center on centerline
        try:
            slice_widget = layout_manager.sliceWidget('Red')
            if slice_widget:
                slice_view = slice_widget.sliceView()
                if slice_view:
                    slice_view.fitToWindow()
                    
                # Reset the field of view for better centerline visibility
                slice_logic = slice_widget.sliceLogic()
                if slice_logic:
                    slice_logic.FitSliceToAll()
                    
                # Set slice view to axial orientation for best centerline editing
                slice_node = slice_logic.GetSliceNode()
                if slice_node:
                    slice_node.SetOrientationToAxial()
                    
        except Exception as slice_error:
            pass  # Continue even if slice setup fails
                
    except Exception as e:
        pass  # Continue even if layout switch fails


def switch_to_3d_fullscreen():
    """
    Switch to 3D fullscreen view for analysis
    """
    try:
        layout_manager = slicer.app.layoutManager()
        if not layout_manager:
            return
            
        # Switch to 3D only layout
        layout_manager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
        
        # Allow the layout to update
        slicer.app.processEvents()
        
        # Fit 3D view to window and reset camera
        try:
            threeDWidget = layout_manager.threeDWidget(0)
            if threeDWidget:
                threeDView = threeDWidget.threeDView()
                if threeDView:
                    threeDView.resetFocalPoint()
                    # Also reset camera to show all content
                    threeDView.resetCamera()
        except Exception as view_error:
            pass  # Continue even if 3D view setup fails
                    
        # Restore original layout if it was stored (after showing 3D briefly)
        if hasattr(slicer.modules, 'CenterlineEditingOriginalLayout'):
            # Use a timer to restore original layout after user sees 3D view
            qt.QTimer.singleShot(3000, restore_original_layout)
                    
    except Exception as e:
        pass  # Continue even if layout switch fails


def restore_original_layout():
    """
    Restore the original layout that was active before centerline editing
    """
    try:
        if hasattr(slicer.modules, 'CenterlineEditingOriginalLayout'):
            layout_manager = slicer.app.layoutManager()
            if layout_manager:
                original_layout = slicer.modules.CenterlineEditingOriginalLayout
                layout_manager.setLayout(original_layout)
            
            # Clean up the stored layout
            delattr(slicer.modules, 'CenterlineEditingOriginalLayout')
            
    except Exception as e:
        pass


def debug_centerline_editing():
    """
    Debug function to test centerline editing - run this in Slicer console
    """
    try:
        print("DEBUG: Starting centerline editing debug...")
        
        # Check for centerlines
        all_curves = find_all_centerline_curves()
        print(f"DEBUG: Found {len(all_curves)} centerline curves")
        
        for i, curve in enumerate(all_curves):
            if curve:
                print(f"  Curve {i}: {curve.GetName()}, Points: {curve.GetNumberOfControlPoints()}")
            else:
                print(f"  Curve {i}: None")
        
        if not all_curves:
            print("DEBUG: No centerline curves found in scene")
            return False
        
        # Try to open editing dialog with the first curve
        curve = all_curves[0]
        print(f"DEBUG: Attempting to open editing dialog with curve: {curve.GetName()}")
        
        show_centerline_editing_dialog(None, curve)
        return True
        
    except Exception as e:
        print(f"DEBUG: Error in debug_centerline_editing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def on_restart_cropping(dialog, centerline_model=None, centerline_curve=None):
    """
    Called when user chooses to restart cropping while preserving existing centerlines.
    Uses staged approach with timers to prevent freezing.
    """
    try:
        # Stop ALL centerline monitoring systems to prevent double dialogs
        stop_all_centerline_monitoring()
        
        # Reset the dialog flag to allow future dialogs
        if hasattr(slicer.modules, 'CenterlineDialogShown'):
            slicer.modules.CenterlineDialogShown = False
        
        dialog.close()
        dialog.setParent(None)
        
        # Hide the custom crop interface during recropping
        cleanup_custom_crop_interface()
        
        # Show progress message
        
        # Stage 1: Store centerlines immediately
        store_existing_centerlines()
        
        # Stage 2: Clear workflow data with delay to prevent freezing
        qt.QTimer.singleShot(500, clear_workflow_for_cropping_restart)
        
        # Stage 3: Reset modules with delay
        qt.QTimer.singleShot(1500, lambda: reset_crop_module_safely())
        
        # Stage 4: Restart cropping workflow with delay
        qt.QTimer.singleShot(3000, lambda: restart_cropping_workflow_safely())
        
    except Exception as e:
        pass
        # Fallback - just restart cropping without preservation after delay
        qt.QTimer.singleShot(1000, start_with_volume_crop)


def reset_crop_module_safely():
    """
    Safely reset the crop module with error handling to prevent freezing.
    """
    try:
        slicer.app.processEvents()
        
        # Clean up custom elements first
        cleanup_crop_module_custom_elements()
        slicer.app.processEvents()
        
        # Switch to crop module for recropping (avoid Welcome module)
        slicer.util.selectModule("CropVolume")
        slicer.app.processEvents()
        
        
    except Exception as e:
        pass


def restart_cropping_workflow_safely():
    """
    Safely restart the cropping workflow with proper timing and error handling.
    Shows the custom crop interface and waits for user to perform recropping.
    """
    try:
        slicer.app.processEvents()
        
        # Collapse the left module panel for recropping to maximize view space
        collapse_left_module_panel()
        
        # Restore centerline visibility first
        restore_centerline_visibility()
        slicer.app.processEvents()
        
        # Show the crop module for recropping instead of custom interface
        try:
            # Open the crop module so user can see it in the left panel
            slicer.util.selectModule("CropVolume")
            slicer.app.processEvents()
            
            # Hide ALL UI elements from the crop module
            hide_crop_volume_ui_elements()
            qt.QTimer.singleShot(500, hide_crop_volume_ui_elements)
            qt.QTimer.singleShot(1500, hide_crop_volume_ui_elements)
            
            # Create initial custom crop interface (without scissors tools) to match first crop
            success = create_initial_custom_crop_interface()

        except Exception as e:
            pass
            # Fallback to standard crop workflow
            start_with_volume_crop()
        
        slicer.app.processEvents()
        
    except Exception as e:
        pass
        # Fallback to standard crop module
        try:
            start_with_volume_crop()
        except:
            pass


# Removed show_restart_completion_message function - no longer needed


def store_existing_centerlines():
    """
    Store references to existing centerlines to preserve them during workflow restart
    """
    try:
        # Find all existing centerline models and curves
        centerline_models = find_all_centerline_models()
        centerline_curves = find_all_centerline_curves()
        
        # Store them in the slicer modules for persistence
        slicer.modules.PreservedCenterlineModels = [model.GetID() for model in centerline_models]
        slicer.modules.PreservedCenterlineCurves = [curve.GetID() for curve in centerline_curves]
        
        # Also store their current visibility states
        model_visibility = {}
        curve_visibility = {}
        
        for model in centerline_models:
            display_node = model.GetDisplayNode()
            if display_node:
                model_visibility[model.GetID()] = display_node.GetVisibility()
        
        for curve in centerline_curves:
            display_node = curve.GetDisplayNode()
            if display_node:
                curve_visibility[curve.GetID()] = display_node.GetVisibility()
        
        slicer.modules.PreservedModelVisibility = model_visibility
        slicer.modules.PreservedCurveVisibility = curve_visibility
        
        
    except Exception as e:
        pass


def clear_workflow_for_cropping_restart():
    """
    Clear workflow-related nodes and UI but preserve centerlines and original volume.
    Uses safe node removal with error handling to prevent freezing.
    """
    try:
        slicer.app.processEvents()
        
        # Get the original volume (not cropped)
        original_volume = None
        volumes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        
        # Find the original volume (usually the one without "cropped" in the name)
        for volume in volumes:
            if 'crop' not in volume.GetName().lower():
                original_volume = volume
                break
        
        # If no clear original found, use the first volume
        if not original_volume and volumes:
            original_volume = volumes[0]
        
        # Safely remove cropped volumes but keep the original
        cropped_volumes = []
        for volume in volumes:
            if 'crop' in volume.GetName().lower():
                cropped_volumes.append(volume)
        
        for volume in cropped_volumes:
            try:
                slicer.mrmlScene.RemoveNode(volume)
                slicer.app.processEvents()  # Process events after each removal
            except Exception as e:
                pass
        
        # Safely clear existing ROI nodes
        roi_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsROINode')
        for roi in roi_nodes:
            try:
                slicer.mrmlScene.RemoveNode(roi)
                slicer.app.processEvents()
            except Exception as e:
                pass
        
        # Safely clear segmentation nodes (user will need to re-segment after cropping)
        segmentation_nodes = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
        for seg in segmentation_nodes:
            try:
                slicer.mrmlScene.RemoveNode(seg)
                slicer.app.processEvents()
            except Exception as e:
                pass
        
        # Safely clear endpoint markups but preserve centerlines
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for fid in fiducial_nodes:
            try:
                # Only remove if it's not a preserved centerline-related node
                if 'endpoint' in fid.GetName().lower() or 'F-' in fid.GetName():
                    slicer.mrmlScene.RemoveNode(fid)
                    slicer.app.processEvents()
            except Exception as e:
                pass
        
        # Store reference to original volume for workflow
        if original_volume:
            slicer.modules.WorkflowOriginalVolume = original_volume
        
        
    except Exception as e:
        pass
        # Don't let this stop the restart process - continue anyway


def restart_cropping_preserving_centerlines():
    """
    Restart the cropping workflow while maintaining existing centerlines
    """
    try:
        # Ensure centerlines remain visible
        restore_centerline_visibility()
        
        # Reset the Crop Volume module to default state first
        reset_crop_module_to_default()
        
        # Start the volume cropping workflow
        start_with_volume_crop()
        
        # Set up monitoring to restore centerlines after cropping completion
        setup_post_crop_centerline_restoration()
        
        
    except Exception as e:
        pass


def restore_centerline_visibility():
    """
    Restore visibility of preserved centerlines
    """
    try:
        if hasattr(slicer.modules, 'PreservedCenterlineModels'):
            model_ids = slicer.modules.PreservedCenterlineModels
            model_visibility = getattr(slicer.modules, 'PreservedModelVisibility', {})
            
            for model_id in model_ids:
                model = slicer.mrmlScene.GetNodeByID(model_id)
                if model:
                    display_node = model.GetDisplayNode()
                    if display_node:
                        # Restore original visibility or make visible by default
                        visibility = model_visibility.get(model_id, True)
                        display_node.SetVisibility(visibility)
        
        if hasattr(slicer.modules, 'PreservedCenterlineCurves'):
            curve_ids = slicer.modules.PreservedCenterlineCurves
            curve_visibility = getattr(slicer.modules, 'PreservedCurveVisibility', {})
            
            for curve_id in curve_ids:
                curve = slicer.mrmlScene.GetNodeByID(curve_id)
                if curve:
                    display_node = curve.GetDisplayNode()
                    if display_node:
                        # Restore original visibility or make visible by default
                        visibility = curve_visibility.get(curve_id, True)
                        display_node.SetVisibility(visibility)
        
        
    except Exception as e:
        pass


def setup_post_crop_centerline_restoration():
    """
    Set up monitoring to ensure centerlines remain functional after cropping
    """
    try:
        # This will be called after crop completion to ensure centerlines work with new cropped volume
        # For now, we'll rely on the existing crop completion monitoring
        pass
        
    except Exception as e:
        pass


def create_additional_centerline_setup():
    """
    Create new centerline model and curve nodes and set up Extract Centerline module for additional centerlines
    """
    try:
        # Expand the left module panel for additional centerline extraction
        expand_left_module_panel()
        
        # Ensure we're in the Extract Centerline module
        slicer.util.selectModule("ExtractCenterline")
        slicer.app.processEvents()
        
        # Set up minimal UI with only inputs section
        setup_minimal_extract_centerline_ui()
        
        centerline_widget = slicer.modules.extractcenterline.widgetRepresentation()
        if not centerline_widget:
            return
            
        centerline_module = centerline_widget.self()
        
        # Get the existing centerline count to create unique names
        existing_centerlines = count_existing_centerlines()
        centerline_number = existing_centerlines + 1
        
        # Create new centerline model node
        new_centerline_model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
        new_centerline_model.SetName(f"CenterlineModel_{centerline_number}")
        new_centerline_model.CreateDefaultDisplayNodes()
        
        # Create new centerline curve node  
        new_centerline_curve = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode")
        new_centerline_curve.SetName(f"CenterlineCurve_{centerline_number}")
        new_centerline_curve.CreateDefaultDisplayNodes()
        
        # Set curve properties for better visibility
        display_node = new_centerline_curve.GetDisplayNode()
        if display_node:
            display_node.SetColor(0.0, 1.0, 1.0)  # Cyan color to distinguish from previous centerlines
            display_node.SetLineWidth(3.0)
            display_node.SetVisibility(True)
        
        
        # Configure the Extract Centerline module with the new nodes
        setup_centerline_for_additional_extraction(centerline_module, new_centerline_model, new_centerline_curve)
        
        # Clear any existing endpoint markups and prepare for new placement
        clear_centerline_endpoints()
        
        # Set up automatic monitoring that waits for Apply button click
        setup_apply_button_monitoring()
        
        return new_centerline_model, new_centerline_curve
        
    except Exception as e:
        return None, None

def count_existing_centerlines():
    """
    Count the number of existing centerline models and curves to determine the next number
    """
    try:
        centerline_count = 0
        
        # Count centerline models
        model_nodes = slicer.util.getNodesByClass('vtkMRMLModelNode')
        for model in model_nodes:
            model_name = model.GetName().lower()
            if any(keyword in model_name for keyword in ['centerline', 'tree', 'vessel']):
                centerline_count += 1
                
        # Count centerline curves
        curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsCurveNode')
        for curve in curve_nodes:
            curve_name = curve.GetName().lower()
            if any(keyword in curve_name for keyword in ['centerline', 'curve']):
                centerline_count += 1
                
        # Return the higher count (since we have both models and curves)
        return centerline_count // 2 if centerline_count > 0 else 0
        
    except Exception as e:
        return 0

def setup_centerline_for_additional_extraction(centerline_module, new_model, new_curve):
    """
    Configure the Extract Centerline module for additional centerline extraction
    """
    try:
        # Set the same segmentation as before
        segmentation_nodes = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
        workflow_segmentation = None
        for seg_node in segmentation_nodes:
            if seg_node.GetName().startswith("ThresholdSegmentation_"):
                workflow_segmentation = seg_node
                break
        
        if workflow_segmentation:
            pass
            
            # Set input segmentation
            segmentation_set = False
            for selector_name in ['inputSegmentationSelector', 'inputSurfaceSelector', 'segmentationSelector']:
                if hasattr(centerline_module, 'ui') and hasattr(centerline_module.ui, selector_name):
                    getattr(centerline_module.ui, selector_name).setCurrentNode(workflow_segmentation)
                    pass
                    segmentation_set = True
                    break
            
            if not segmentation_set:
                pass
                
            # Set segment selector for the workflow segment
            workflow_segment_id = workflow_segmentation.GetAttribute("WorkflowCreatedSegmentID")
            if workflow_segment_id:
                segmentation = workflow_segmentation.GetSegmentation()
                segment = segmentation.GetSegment(workflow_segment_id)
                if segment:
                    segment_set = False
                    for selector_name in ['inputSegmentSelector', 'segmentSelector', 'inputSurfaceSegmentSelector']:
                        if hasattr(centerline_module.ui, selector_name):
                            try:
                                getattr(centerline_module.ui, selector_name).setCurrentSegmentID(workflow_segment_id)
                                segment_set = True
                                break
                            except Exception as e:
                                pass
                
        # Create and set up new endpoint fiducial list for point placement
        try:
            # Get the count of existing centerlines for unique naming
            existing_count = count_existing_centerlines()
            endpoint_point_list = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
            endpoint_point_list.SetName(f"CenterlineEndpoints_{existing_count + 1}")
            
            # Try to find and set the endpoint selector using the XML object name
            endpoints_selector = None
            extract_centerline_widget = slicer.modules.extractcenterline.widgetRepresentation()
            if extract_centerline_widget:
                # Use the exact object name from the XML
                endpoints_selector = extract_centerline_widget.findChild(qt.QWidget, "endPointsMarkupsSelector")
                if endpoints_selector and hasattr(endpoints_selector, 'setCurrentNode'):
                    endpoints_selector.setCurrentNode(endpoint_point_list)
                    endpoint_set = True
            
            # Fallback to old method if XML-based approach failed
            if not endpoints_selector:
                endpoint_set = False
                for endpoint_selector_attr in ['inputEndPointsSelector', 'endpointsSelector', 'inputFiducialSelector']:
                    if hasattr(centerline_module.ui, endpoint_selector_attr):
                        getattr(centerline_module.ui, endpoint_selector_attr).setCurrentNode(endpoint_point_list)
                        endpoint_set = True
                        break
            
            # Set this as the active node for point placement
            selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
            if selectionNode:
                selectionNode.SetActivePlaceNodeID(endpoint_point_list.GetID())
            
            # Enable point placement mode with multiple points
            interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
            if interactionNode:
                interactionNode.SetCurrentInteractionMode(interactionNode.Place)
                interactionNode.SetPlaceModePersistence(1)  # Enable "place multiple control points"
            
            # Try to configure the place widget
            if extract_centerline_widget:
                place_widget = extract_centerline_widget.findChild(qt.QWidget, "endPointsMarkupsPlaceWidget")
                if place_widget:
                    if hasattr(place_widget, 'setCurrentNode'):
                        place_widget.setCurrentNode(endpoint_point_list)
                    if hasattr(place_widget, 'setPlaceModeEnabled'):
                        place_widget.setPlaceModeEnabled(True)
            
            for create_new_attr in ['createNewEndpointsCheckBox', 'createNewPointListCheckBox']:
                if hasattr(centerline_module.ui, create_new_attr):
                    getattr(centerline_module.ui, create_new_attr).setChecked(True)
                    
        except Exception as e:
            pass
                
        # Set output nodes for the new centerline
        try:
            # Set output centerline model
            if hasattr(centerline_module.ui, 'outputCenterlineModelSelector'):
                centerline_module.ui.outputCenterlineModelSelector.setCurrentNode(new_model)
                pass
            elif hasattr(centerline_module.ui, 'centerlineModelSelector'):
                centerline_module.ui.centerlineModelSelector.setCurrentNode(new_model)
                pass
                
            # Set output centerline curve
            if hasattr(centerline_module.ui, 'outputCenterlineCurveSelector'):
                centerline_module.ui.outputCenterlineCurveSelector.setCurrentNode(new_curve)
                pass
            elif hasattr(centerline_module.ui, 'centerlineCurveSelector'):
                centerline_module.ui.centerlineCurveSelector.setCurrentNode(new_curve)
                pass
                
        except Exception as e:
            pass
        
        # Force GUI update and give time for widgets to initialize
        slicer.app.processEvents()
        time.sleep(0.2)
        slicer.app.processEvents()
        
        # Verify that point placement is properly set up
        verification_results = verify_extract_centerline_point_list_autoselection()
        if not verification_results["success"]:
            pass
            fix_extract_centerline_setup_issues()
            # Re-verify after fixes
            time.sleep(0.2)
            slicer.app.processEvents()
            verification_results = verify_extract_centerline_point_list_autoselection()
        
        # Force point placement tool selection one final time
        force_point_placement_tool_selection()
        
        # Add the large Apply button again
        add_large_centerline_apply_button()
        
    except Exception as e:
        pass

def clear_centerline_endpoints():
    """
    Clear existing endpoint markups from the Extract Centerline module
    """
    try:
        # Find and clear endpoint fiducial nodes
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        endpoints_cleared = 0
        
        for node in fiducial_nodes:
            node_name = node.GetName().lower()
            if any(keyword in node_name for keyword in ['endpoint', 'start', 'end', 'centerline']):
                node.RemoveAllControlPoints()
                endpoints_cleared += 1
                pass
        
        if endpoints_cleared == 0:
            pass
        else:
            pass
            
    except Exception as e:
        pass

def setup_apply_button_monitoring():
    """
    Set up monitoring to detect when the Apply button is clicked in Extract Centerline module
    """
    try:
        # Stop any existing Apply button monitoring
        if hasattr(slicer.modules, 'ApplyButtonMonitorTimer'):
            timer = slicer.modules.ApplyButtonMonitorTimer
            timer.stop()
            timer.timeout.disconnect()
            del slicer.modules.ApplyButtonMonitorTimer
        
        # Clear the dialog shown flag for new extraction cycle
        if hasattr(slicer.modules, 'CenterlineDialogShown'):
            del slicer.modules.CenterlineDialogShown
            pass
        
        # Get baseline counts before user starts
        current_models = find_all_centerline_models()
        current_curves = find_all_centerline_curves()
        slicer.modules.ApplyButtonBaselineModels = len(current_models)
        slicer.modules.ApplyButtonBaselineCurves = len(current_curves)
        
        # Store the IDs of existing centerlines to detect truly new ones
        slicer.modules.ExistingModelIDs = [model.GetID() for model in current_models]
        slicer.modules.ExistingCurveIDs = [curve.GetID() for curve in current_curves]
        
        # Create a timer to monitor for Apply button clicks
        timer = qt.QTimer()
        timer.timeout.connect(check_for_apply_button_click)
        timer.start(2000)  # Check every 2 seconds
        slicer.modules.ApplyButtonMonitorTimer = timer
        slicer.modules.ApplyMonitorCheckCount = 0
        
        
    except Exception as e:
        pass

def check_for_apply_button_click():
    """
    Check if Apply button has been clicked by monitoring for new centerline activity
    """
    try:
        # Increment check count and add timeout
        if hasattr(slicer.modules, 'ApplyMonitorCheckCount'):
            slicer.modules.ApplyMonitorCheckCount += 1
            
        # Get current centerlines
        current_models = find_all_centerline_models()
        current_curves = find_all_centerline_curves()
        
        # Check for truly new centerlines (not just count changes)
        existing_model_ids = getattr(slicer.modules, 'ExistingModelIDs', [])
        existing_curve_ids = getattr(slicer.modules, 'ExistingCurveIDs', [])
        
        new_models = [model for model in current_models if model.GetID() not in existing_model_ids]
        new_curves = [curve for curve in current_curves if curve.GetID() not in existing_curve_ids]
        
        # If we have truly new centerlines, Apply was clicked and processing started/completed
        if new_models or new_curves:
            # Check if dialog has already been shown for this extraction cycle
            if hasattr(slicer.modules, 'CenterlineDialogShown') and slicer.modules.CenterlineDialogShown:
                pass
                return  # Exit early to prevent duplicate dialogs
            
            # Stop Apply button monitoring
            stop_apply_button_monitoring()
            
            # Check if any of the new centerlines have sufficient data
            best_model = None
            best_curve = None
            
            # Find the best new model (one with most points)
            for model in new_models:
                polydata = model.GetPolyData()
                if polydata and polydata.GetNumberOfPoints() > 10:  # Require at least 10 points
                    if not best_model or polydata.GetNumberOfPoints() > best_model.GetPolyData().GetNumberOfPoints():
                        best_model = model
            
            # Find the best new curve (one with most control points)
            for curve in new_curves:
                if curve.GetNumberOfControlPoints() > 5:  # Require at least 5 control points
                    if not best_curve or curve.GetNumberOfControlPoints() > best_curve.GetNumberOfControlPoints():
                        best_curve = curve
            
            # If we have sufficient data, show dialog immediately
            if best_model or best_curve:
                # Stop ALL monitoring to prevent duplicate dialogs
                stop_all_centerline_monitoring()
                
                # Mark that we're showing a dialog for this extraction cycle BEFORE showing dialog
                slicer.modules.CenterlineDialogShown = True
                
                show_centerline_completion_dialog(best_model, best_curve)
                return
            else:
                # No sufficient data yet, but don't set up additional monitoring
                # Let the timer continue to check for data completion
                return
        
        # Alternative detection: Look for recently modified nodes (processing activity)
        for model in current_models:
            if model.GetID() in existing_model_ids:
                # Check if this existing model was recently modified (processing activity)
                import time
                current_time = time.time() * 1000  # Convert to milliseconds
                time_since_modified = current_time - model.GetMTime()
                if time_since_modified < 5000:  # Modified within last 5 seconds
                    pass
                    # Just continue with existing monitoring, don't start new ones
                    return
        
    except Exception as e:
        pass

def stop_apply_button_monitoring():
    """
    Stop monitoring for Apply button clicks
    """
    try:
        if hasattr(slicer.modules, 'ApplyButtonMonitorTimer'):
            timer = slicer.modules.ApplyButtonMonitorTimer
            timer.stop()
            timer.timeout.disconnect()
            del slicer.modules.ApplyButtonMonitorTimer
            
        # Clean up all Apply button monitoring variables
        for attr in ['ApplyButtonBaselineModels', 'ApplyButtonBaselineCurves', 
                    'ExistingModelIDs', 'ExistingCurveIDs', 'ApplyMonitorCheckCount']:
            if hasattr(slicer.modules, attr):
                delattr(slicer.modules, attr)
            
        pass
        
    except Exception as e:
        pass

def stop_all_centerline_monitoring():
    """
    Stop all centerline monitoring systems to prevent double dialogs
    """
    try:
        # Stop the main centerline completion monitoring
        stop_centerline_monitoring()
        
        # Stop the apply button monitoring
        stop_apply_button_monitoring()
        
        pass
        
    except Exception as e:
        pass

def cleanup_centerline_monitoring_button():
    """
    Clean up the centerline monitoring button
    """
    try:
        if hasattr(slicer.modules, 'CenterlineMonitoringButton'):
            button = slicer.modules.CenterlineMonitoringButton
            if button:
                button.close()
                button.setParent(None)
                del slicer.modules.CenterlineMonitoringButton
                pass
        
    except Exception as e:
        pass

def clear_existing_centerlines():
    """
    Clear existing centerline models and curves to prepare for retry
    """
    try:
        model_nodes = slicer.util.getNodesByClass('vtkMRMLModelNode')
        centerline_models = []
        for model in model_nodes:
            model_name = model.GetName().lower()
            if any(keyword in model_name for keyword in ['centerline', 'tree']):
                centerline_models.append(model)
        
        curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsCurveNode')
        centerline_curves = []
        for curve in curve_nodes:
            curve_name = curve.GetName().lower()
            if any(keyword in curve_name for keyword in ['centerline', 'curve']):
                centerline_curves.append(curve)
        removed_count = 0
        for model in centerline_models:
            slicer.mrmlScene.RemoveNode(model)
            pass
            removed_count += 1
        
        for curve in centerline_curves:
            slicer.mrmlScene.RemoveNode(curve)
            pass
            removed_count += 1
        
        if removed_count > 0:
            pass
        else:
            pass
            
    except Exception as e:
        pass

def remove_transforms_from_point_lists():
    """
    Remove all transforms from F-1 point lists before saving, with special focus on pre and post lesion points
    """
    try:
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        removed_count = 0
        pre_post_lesion_processed = 0
        
        for node in fiducial_nodes:
            node_name = node.GetName()
            if node_name == "F-1":
                # First, ensure individual pre and post lesion points have no transforms
                point_count = node.GetNumberOfControlPoints()
                if point_count >= 2:  # At least pre-lesion and post-lesion points
                    pass
                    
                    # Check points 1 and 2 (pre-lesion and post-lesion)
                    for point_index in [0, 1]:  # 0 = pre-lesion, 1 = post-lesion
                        point_name = "pre-lesion" if point_index == 0 else "post-lesion"
                        
                        # Note: Individual points within a fiducial list cannot have separate transforms
                        # The transform applies to the entire point list, but we verify the points exist
                        if point_index < point_count:
                            point_pos = [0.0, 0.0, 0.0]
                            node.GetNthControlPointPosition(point_index, point_pos)
                            pass
                            pre_post_lesion_processed += 1
                        else:
                            pass
                
                # Remove transform from the entire point list
                if node.GetTransformNodeID():
                    transform_name = ""
                    transform_node = node.GetTransformNode()
                    if transform_node:
                        transform_name = transform_node.GetName()
                    
                    pass
                    node.SetAndObserveTransformNodeID(None)
                    node.Modified()
                    removed_count += 1
                    pass
                else:
                    pass
        
        if removed_count > 0:
            slicer.app.processEvents()
            pass
            pass
            pass
            return True
        else:
            if pre_post_lesion_processed > 0:
                pass
                return True
            else:
                pass
                return False
            
    except Exception as e:
        pass
        return False

def verify_pre_post_lesion_points_transform_free():
    """
    Verify that pre and post lesion points are completely transform-free before saving
    """
    try:
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        verification_passed = True
        points_checked = 0
        
        for node in fiducial_nodes:
            node_name = node.GetName()
            if node_name == "F-1":
                # Check if the point list has any transforms
                if node.GetTransformNodeID():
                    transform_node = node.GetTransformNode()
                    transform_name = transform_node.GetName() if transform_node else "Unknown"
                    pass
                    verification_passed = False
                    continue
                
                # Verify pre and post lesion points exist and report their positions
                point_count = node.GetNumberOfControlPoints()
                if point_count >= 2:
                    for point_index in [0, 1]:  # 0 = pre-lesion, 1 = post-lesion
                        point_name = "pre-lesion" if point_index == 0 else "post-lesion"
                        point_pos = [0.0, 0.0, 0.0]
                        node.GetNthControlPointPosition(point_index, point_pos)
                        pass
                        points_checked += 1
                else:
                    pass
                    verification_passed = False
        
        if points_checked == 0:
            pass
            return False
        
        if verification_passed:
            pass
            return True
        else:
            pass
            return False
            
    except Exception as e:
        pass
        return False

def reapply_transforms_to_point_lists():
    """
    Reapply transforms to F-1 point lists after saving
    """
    try:
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        applied_count = 0
        
        # Find the straightening transform
        transform_nodes = slicer.util.getNodesByClass('vtkMRMLTransformNode')
        straightening_transform = None
        for transform_node in transform_nodes:
            if transform_node.GetName() == "Straightening transform":
                straightening_transform = transform_node
                break
        
        if not straightening_transform:
            pass
            return False
        
        for node in fiducial_nodes:
            node_name = node.GetName()
            if node_name == "F-1":
                node.SetAndObserveTransformNodeID(straightening_transform.GetID())
                node.Modified()
                applied_count += 1
                pass
        
        if applied_count > 0:
            slicer.app.processEvents()
            pass
            pass
            return True
        else:
            pass
            return False
            
    except Exception as e:
        pass
        return False

def reapply_transforms_to_circles():
    """
    Reapply transforms to existing centerline circles after saving
    """
    try:
        circles_reapplied = 0
        
        # Find the straightening transform
        transform_nodes = slicer.util.getNodesByClass('vtkMRMLTransformNode')
        straightening_transform = None
        for transform_node in transform_nodes:
            if transform_node.GetName() == "Straightening transform":
                straightening_transform = transform_node
                break
        
        if not straightening_transform:
            pass
            return False
        
        # Reapply to closed curve circles
        closed_curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsClosedCurveNode')
        for node in closed_curve_nodes:
            if 'circle' in node.GetName().lower():
                node.SetAndObserveTransformNodeID(straightening_transform.GetID())
                node.Modified()
                circles_reapplied += 1
                pass
        
        # Reapply to regular curve circles
        curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsCurveNode')
        for node in curve_nodes:
            if 'circle' in node.GetName().lower():
                node.SetAndObserveTransformNodeID(straightening_transform.GetID())
                node.Modified()
                circles_reapplied += 1
                pass
        
        if circles_reapplied > 0:
            slicer.app.processEvents()
            pass
            return True
        else:
            pass
            return False
            
    except Exception as e:
        pass
        return False



def force_remove_all_transforms():
    """
    Force remove all transforms from F-1 point lists and update GUI
    """
    try:
        pass
        
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        processed_count = 0
        
        for node in fiducial_nodes:
            if node.GetName() == "F-1":
                old_transform_id = node.GetTransformNodeID()
                
                node.SetAndObserveTransformNodeID(None)
                node.Modified()
                
                processed_count += 1
                
                if old_transform_id:
                    pass
                else:
                    pass
        
        slicer.app.processEvents()
        
        pass

        
        return processed_count > 0
        
    except Exception as e:
        pass
        return False

def draw_circles_on_centerline():
    """
    Draw circles at all fiducial points: pre-lesion, post-lesion, and all start/end slice markers
    """
    try:
        f1_points = None
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for node in fiducial_nodes:
            if node.GetName() == "F-1":
                f1_points = node
                break
        
        if not f1_points:
            pass
            return False
        
        if f1_points.GetNumberOfControlPoints() < 2:
            pass
            return False
        
        # Clean up orphaned start markers before drawing circles
        cleanup_orphaned_start_markers()
        
        centerline_model = None
        try:
            centerline_model = slicer.util.getNode('Centerline model')
        except:
            pass
        
        if not centerline_model:
            all_models = slicer.util.getNodesByClass('vtkMRMLModelNode')
            for model in all_models:
                if 'centerline' in model.GetName().lower():
                    centerline_model = model
                    pass
                    break
        
        if not centerline_model:
            for model in all_models:
                if 'tree' in model.GetName().lower():
                    centerline_model = model
                    pass
                    break
        
        if not centerline_model:
            pass
            return False
        
        points = slicer.util.arrayFromModelPoints(centerline_model)
        radii = slicer.util.arrayFromModelPointData(centerline_model, 'Radius')
        
        if points is None or len(points) == 0:
            pass
            return False
            
        if radii is None or len(radii) == 0:
            pass
            return False
        
        clear_centerline_circles()
        
        circles_created = 0
        circle_nodes = []
        
        # Get all fiducial points, not just the first 2
        all_points = []
        for i in range(f1_points.GetNumberOfControlPoints()):
            point = [0.0, 0.0, 0.0]
            f1_points.GetNthControlPointPosition(i, point)
            all_points.append(point)
        
        for i, fiducial_point in enumerate(all_points):
            min_distance = float('inf')
            closest_centerline_idx = 0
            
            for j, centerline_point in enumerate(points):
                distance = ((fiducial_point[0] - centerline_point[0])**2 + 
                           (fiducial_point[1] - centerline_point[1])**2 + 
                           (fiducial_point[2] - centerline_point[2])**2)**0.5
                
                if distance < min_distance:
                    min_distance = distance
                    closest_centerline_idx = j
            
            center_point = points[closest_centerline_idx]
            radius = radii[closest_centerline_idx] if closest_centerline_idx < len(radii) else 1.0;
            
            circle_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsClosedCurveNode")
            
            # Determine point name and color based on position
            if i == 0:
                point_name = "pre-lesion"
                color = (0.0, 1.0, 0.0)  # Green
            elif i == 1:
                point_name = "post-lesion"
                color = (1.0, 0.0, 0.0)  # Red
            else:
                # For points 2 and beyond, alternate between start and end slices
                if (i - 2) % 2 == 0:  # Even offset from position 2 = start slice
                    start_slice_number = ((i - 2) // 2) + 1
                    point_name = f"start-slice-{start_slice_number}"
                    color = (0.0, 0.0, 1.0)  # Blue for start slices
                else:  # Odd offset from position 2 = end slice
                    end_slice_number = ((i - 2) // 2) + 1
                    point_name = f"end-slice-{end_slice_number}"
                    color = (1.0, 1.0, 0.0)  # Yellow for end slices
            
            circle_node.SetName(f"Circle_{point_name}")

            display_node = circle_node.GetDisplayNode()
            if display_node:
                display_node.SetColor(color[0], color[1], color[2])
                display_node.SetSelectedColor(color[0], color[1], color[2])
                
                display_node.SetLineWidth(4.0) 
                display_node.SetVisibility(True)
                display_node.SetPointLabelsVisibility(False)
                display_node.SetFillVisibility(False)
                display_node.SetOutlineVisibility(True)
            
            apply_transform_to_circle(circle_node)
            
            # Calculate centerline direction for perpendicular circles
            centerline_direction = calculate_centerline_direction(points, closest_centerline_idx)
            
            success = create_perpendicular_circle(circle_node, center_point, radius, centerline_direction)
            if success:
                circles_created += 1
                circle_nodes.append(circle_node)
                pass
        
        slicer.modules.WorkflowCenterlineCircleNodes = circle_nodes
        
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode and f1_points:
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            selectionNode.SetActivePlaceNodeID(f1_points.GetID())
        
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
        
        # Update circle dropdown after creating circles
        update_circle_dropdown()
        
        return True
        
    except Exception as e:
        pass
        return False

def create_closed_curve_circle(circle_node, center_point, radius):
    """
    Create a closed curve circle in the axial plane using the closed curve markup tool
    """
    try:
        import math
        num_points = 32 
        
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = center_point[0] + radius * math.cos(angle)
            y = center_point[1] + radius * math.sin(angle)
            z = center_point[2] 
            
            circle_node.AddControlPoint([x, y, z])
        pass
        return True
        
    except Exception as e:
        pass
        return False

def calculate_centerline_direction(centerline_points, point_index):
    """
    Calculate the direction vector of the centerline at a given point index
    """
    try:
        # Get neighboring points for direction calculation
        num_points = len(centerline_points)
        
        # Use a few points before and after for better direction estimation
        window_size = min(5, num_points // 10)  # Use up to 5 points or 10% of total points
        
        start_idx = max(0, point_index - window_size)
        end_idx = min(num_points - 1, point_index + window_size)
        
        if start_idx == end_idx:
            # Fallback: use adjacent points if available
            if point_index > 0:
                start_idx = point_index - 1
            elif point_index < num_points - 1:
                end_idx = point_index + 1
            else:
                # Single point case - use default direction
                return np.array([0.0, 0.0, 1.0])
        
        start_point = np.array(centerline_points[start_idx])
        end_point = np.array(centerline_points[end_idx])
        
        direction = end_point - start_point
        
        # Normalize the direction vector
        magnitude = np.linalg.norm(direction)
        if magnitude > 0:
            direction = direction / magnitude
        else:
            # Fallback direction if points are too close
            direction = np.array([0.0, 0.0, 1.0])
        
        pass
        return direction
        
    except Exception as e:
        pass
        # Return default direction along Z-axis
        return np.array([0.0, 0.0, 1.0])

def create_perpendicular_circle(circle_node, center_point, radius, direction_vector):
    """
    Create a circle perpendicular to the centerline direction vector
    """
    try:
        center = np.array(center_point)
        direction = np.array(direction_vector)
        
        # Create two orthogonal vectors perpendicular to the direction
        # Find a vector that's not parallel to the direction
        if abs(direction[2]) < 0.9:  # Direction is not mainly along Z
            up_vector = np.array([0.0, 0.0, 1.0])
        else:  # Direction is mainly along Z, use X as up vector
            up_vector = np.array([1.0, 0.0, 0.0])
        
        # Create first perpendicular vector
        perp1 = np.cross(direction, up_vector)
        perp1 = perp1 / np.linalg.norm(perp1)  # Normalize
        
        # Create second perpendicular vector
        perp2 = np.cross(direction, perp1)
        perp2 = perp2 / np.linalg.norm(perp2)  # Normalize
        
        # Create circle points
        num_points = 32
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            
            # Calculate point on circle in the plane perpendicular to direction
            circle_point = (center + 
                          radius * math.cos(angle) * perp1 + 
                          radius * math.sin(angle) * perp2)
            
            circle_node.AddControlPoint([circle_point[0], circle_point[1], circle_point[2]])
        
        pass
        pass
        pass
        return True
        
    except Exception as e:
        pass
        # Fallback to axial circle
        return create_closed_curve_circle(circle_node, center_point, radius)

def clear_branch_circles():
    """
    Clear only branch and post-branch circles from the scene, preserving lesion circles
    """
    return clear_circles_selective(['branch-', 'post-branch-'])

def clear_circles_selective(circle_types=None):
    """
    Clear specific types of circles from the scene
    
    Args:
        circle_types: List of circle type prefixes to clear. If None, clears all.
                     Examples: ['branch-', 'post-branch-'], ['pre-lesion', 'post-lesion'], etc.
    """
    try:
        removed_count = 0
        
        all_closed_curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsClosedCurveNode')
        for node in all_closed_curve_nodes:
            node_name = node.GetName()
            should_remove = False
            
            if circle_types is None:
                # Clear all Circle_ prefixed nodes if no specific types given
                should_remove = node_name.startswith('Circle_')
            else:
                # Check if node matches any of the specified types
                for circle_type in circle_types:
                    if node_name.startswith(f'Circle_{circle_type}'):
                        should_remove = True
                        break
            
            if should_remove:
                slicer.mrmlScene.RemoveNode(node)
                removed_count += 1
        
        if removed_count > 0:
            update_circle_dropdown()
            
        return removed_count > 0
        
    except Exception as e:
        pass
        return False

def clear_centerline_circles():
    """
    Clear all centerline circles from the scene
    """
    try:
        removed_count = 0
        
        if hasattr(slicer.modules, 'WorkflowCenterlineCircles'):
            circles_node = slicer.modules.WorkflowCenterlineCircles
            if circles_node and not circles_node.IsA('vtkObject'):
                slicer.mrmlScene.RemoveNode(circles_node)
                removed_count += 1
            del slicer.modules.WorkflowCenterlineCircles
        
        if hasattr(slicer.modules, 'WorkflowCenterlineCircleNodes'):
            circle_nodes = slicer.modules.WorkflowCenterlineCircleNodes
            for node in circle_nodes:
                if node and not node.IsA('vtkObject'): 
                    slicer.mrmlScene.RemoveNode(node)
                    removed_count += 1
            del slicer.modules.WorkflowCenterlineCircleNodes
        
        all_curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsCurveNode')
        for node in all_curve_nodes:
            if ('circle' in node.GetName().lower() and 'centerline' in node.GetName().lower()) or \
               ('axialcircle' in node.GetName().lower()):
                slicer.mrmlScene.RemoveNode(node)
                removed_count += 1
        
        all_closed_curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsClosedCurveNode')
        for node in all_closed_curve_nodes:
            node_name = node.GetName().lower()
            if ('circle' in node_name and 'centerline' in node_name) or \
               ('axialcircle' in node_name) or \
               (node.GetName().startswith('Circle_')):  # Clear all workflow circles
                slicer.mrmlScene.RemoveNode(node)
                removed_count += 1
        
        if removed_count > 0:
            pass
            # Update circle dropdown after clearing circles
            update_circle_dropdown()
        else:
            pass
            
        return removed_count > 0
        
    except Exception as e:
        pass
        return False

def draw_circle_for_single_point(point_index):
    """
    Draw a circle for a single fiducial point immediately after it's placed
    """
    try:
        f1_points = None
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for node in fiducial_nodes:
            if node.GetName() == "F-1":
                f1_points = node
                break
        
        if not f1_points or point_index >= f1_points.GetNumberOfControlPoints():
            return False
        
        centerline_model = None
        try:
            centerline_model = slicer.util.getNode('Centerline model')
        except:
            pass
        
        if not centerline_model:
            all_models = slicer.util.getNodesByClass('vtkMRMLModelNode')
            for model in all_models:
                if 'centerline' in model.GetName().lower():
                    centerline_model = model
                    break
        
        if not centerline_model:
            for model in all_models:
                if 'tree' in model.GetName().lower():
                    centerline_model = model
                    break
        
        if not centerline_model:
            return False
        
        points = slicer.util.arrayFromModelPoints(centerline_model)
        radii = slicer.util.arrayFromModelPointData(centerline_model, 'Radius')
        
        if points is None or len(points) == 0:
            return False
            
        if radii is None or len(radii) == 0:
            return False
        
        # Get the fiducial point
        fiducial_point = [0.0, 0.0, 0.0]
        f1_points.GetNthControlPointPosition(point_index, fiducial_point)
        
        # Find closest centerline point
        min_distance = float('inf')
        closest_centerline_idx = 0
        
        for j, centerline_point in enumerate(points):
            distance = ((fiducial_point[0] - centerline_point[0])**2 + 
                       (fiducial_point[1] - centerline_point[1])**2 + 
                       (fiducial_point[2] - centerline_point[2])**2)**0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_centerline_idx = j
        
        center_point = points[closest_centerline_idx]
        radius = radii[closest_centerline_idx] if closest_centerline_idx < len(radii) else 1.0
        
        # Determine point name and color based on position
        if point_index == 0:
            point_name = "test-point"
            color = (0.5, 0.5, 0.5)  # Gray for test point
        elif point_index == 1:
            point_name = "pre-lesion"
            color = (0.0, 1.0, 0.0)  # Green
        elif point_index == 2:
            point_name = "post-lesion"
            color = (1.0, 0.0, 0.0)  # Red
        else:
            # For points 3 and beyond, alternate between start and end slices
            if (point_index - 3) % 2 == 0:  # Even offset from position 3 = start slice
                start_slice_number = ((point_index - 3) // 2) + 1
                point_name = f"start-slice-{start_slice_number}"
                color = (0.0, 0.0, 1.0)  # Blue for start slices
            else:  # Odd offset from position 3 = end slice
                end_slice_number = ((point_index - 3) // 2) + 1
                point_name = f"end-slice-{end_slice_number}"
                color = (1.0, 1.0, 0.0)  # Yellow for end slices
        
        # Check if circle already exists for this point
        circle_name = f"Circle_{point_name}"
        existing_circle = None
        try:
            existing_circle = slicer.util.getNode(circle_name)
        except:
            pass
        
        # Remove existing circle if it exists
        if existing_circle:
            slicer.mrmlScene.RemoveNode(existing_circle)
        
        # Create new circle
        circle_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsClosedCurveNode")
        circle_node.SetName(circle_name)

        display_node = circle_node.GetDisplayNode()
        if display_node:
            display_node.SetColor(color[0], color[1], color[2])
            display_node.SetSelectedColor(color[0], color[1], color[2])
            
            display_node.SetLineWidth(4.0) 
            display_node.SetVisibility(True)
            display_node.SetPointLabelsVisibility(False)
            display_node.SetFillVisibility(False)
            display_node.SetOutlineVisibility(True)
        
        apply_transform_to_circle(circle_node)
        
        # Calculate centerline direction for perpendicular circles
        centerline_direction = calculate_centerline_direction(points, closest_centerline_idx)
        
        success = create_perpendicular_circle(circle_node, center_point, radius, centerline_direction)
        
        # Update the stored circle nodes list
        if not hasattr(slicer.modules, 'WorkflowCenterlineCircleNodes'):
            slicer.modules.WorkflowCenterlineCircleNodes = []
        
        if success:
            slicer.modules.WorkflowCenterlineCircleNodes.append(circle_node)
            
            try:
                # Hide the specific control point
                f1_points.SetNthControlPointVisibility(point_index, False)
                # Also hide the point in 3D view
                display_node = f1_points.GetDisplayNode()
                if display_node:
                    display_node.SetPointLabelsVisibility(False)
                    display_node.SetVisibility(False)  

            except Exception as hide_error:
                pass
        
        # Update circle dropdown after creating a circle
        if success:
            update_circle_dropdown()
        
        return success
        
    except Exception as e:
        return False

def apply_transform_to_circle(circle_node):
    """
    Apply the same transform as the F-1 point list to the circle node
    """
    try:
        transform_nodes = slicer.util.getNodesByClass('vtkMRMLTransformNode')
        
        if len(transform_nodes) == 0:
            pass
            return False
        straightening_transform = None
        for transform_node in transform_nodes:
            if transform_node.GetName() == "Straightening transform":
                straightening_transform = transform_node
                break
        
        if straightening_transform:
            circle_node.SetAndObserveTransformNodeID(straightening_transform.GetID())
            pass
            return True
        else:
            transform_names = [node.GetName() for node in transform_nodes]
            pass
            return False
            
    except Exception as e:
        pass
        return False

def draw_circle_for_branch_point(branch_node, point_index):
    """
    Draw a circle for a branch fiducial (post-branch-n / branch-n) similar to standard point placement.
    Uses the nearest centerline to the placed point instead of the current reference.
    """
    try:
        if not branch_node or point_index >= branch_node.GetNumberOfControlPoints():
            return False

        # Get the fiducial point position
        pos = [0.0, 0.0, 0.0]
        branch_node.GetNthControlPointPosition(point_index, pos)

        # Find the nearest centerline to this point
        centerline_model, distance = find_nearest_centerline_to_point(pos)
        
        if not centerline_model:
            # Fallback: Try to find any centerline model
            try:
                centerline_model = slicer.util.getNode('Centerline model')
            except:
                pass
            if not centerline_model:
                all_models = slicer.util.getNodesByClass('vtkMRMLModelNode')
                for model in all_models:
                    if 'centerline' in model.GetName().lower() or 'tree' in model.GetName().lower():
                        centerline_model = model
                        break
        
        if not centerline_model:
            pass  # No centerline found for branch circle creation
            return False

        points = slicer.util.arrayFromModelPoints(centerline_model)
        radii = slicer.util.arrayFromModelPointData(centerline_model, 'Radius')
        if points is None or len(points) == 0:
            return False
        if radii is None or len(radii) == 0:
            return False

        # Find closest centerline point
        min_distance = float('inf')
        closest_idx = 0
        for j, p in enumerate(points):
            d = ((pos[0]-p[0])**2 + (pos[1]-p[1])**2 + (pos[2]-p[2])**2) ** 0.5
            if d < min_distance:
                min_distance = d
                closest_idx = j

        center_point = points[closest_idx]
        radius = radii[closest_idx] if closest_idx < len(radii) else 1.0

        # Determine name and color based on point index (since label might not be set yet)
        # Branch points alternate: post-branch-1, branch-1, post-branch-2, branch-2, etc.
        if point_index % 2 == 0:  # Even indices (0, 2, 4...) are post-branch
            branch_number = (point_index // 2) + 1
            expected_label = f"post-branch-{branch_number}"
            color = (0.0, 0.7, 1.0)  # Cyan for post-branch
        else:  # Odd indices (1, 3, 5...) are branch
            branch_number = ((point_index - 1) // 2) + 1
            expected_label = f"branch-{branch_number}"
            color = (1.0, 0.4, 0.0)  # Orange for branch
        
        circle_name = f"Circle_{expected_label}"

        # Replace existing circle with same name if any
        existing_circle = None
        try:
            existing_circle = slicer.util.getNode(circle_name)
        except:
            pass
        if existing_circle:
            slicer.mrmlScene.RemoveNode(existing_circle)

        # Create new circle node
        circle_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsClosedCurveNode")
        circle_node.SetName(circle_name)

        # Configure display properties
        display_node = circle_node.GetDisplayNode()
        if display_node:
            display_node.SetColor(*color)
            display_node.SetSelectedColor(*color)
            display_node.SetLineWidth(4.0)
            display_node.SetVisibility(True)
            display_node.SetPointLabelsVisibility(False)
            display_node.SetFillVisibility(False)
            display_node.SetOutlineVisibility(True)

        # Apply transform (same as main placement)
        apply_transform_to_circle(circle_node)

        # Calculate direction and create perpendicular circle
        direction = calculate_centerline_direction(points, closest_idx)
        success = create_perpendicular_circle(circle_node, center_point, radius, direction)

        # Track and hide fiducial (same as main placement)
        if success:
            if not hasattr(slicer.modules, 'WorkflowCenterlineCircleNodes'):
                slicer.modules.WorkflowCenterlineCircleNodes = []
            slicer.modules.WorkflowCenterlineCircleNodes.append(circle_node)

            # Hide the fiducial point after creating circle
            try:
                branch_node.SetNthControlPointVisibility(point_index, False)
                bdn = branch_node.GetDisplayNode()
                if bdn:
                    bdn.SetPointLabelsVisibility(False)
            except Exception:
                pass
            
            pass  # Created circle for {expected_label}

        # Update circle dropdown after creating a branch circle
        if success:
            update_circle_dropdown()

        return success
    except Exception as e:
        pass  # Error creating branch circle: {str(e)}
        return False

def draw_circle_for_post_branch_point(post_branch_node, point_index):
    """
    Draw a circle for a post branch fiducial similar to standard point placement.
    Uses the nearest centerline to the placed point instead of the current reference.
    """
    try:
        if not post_branch_node or point_index >= post_branch_node.GetNumberOfControlPoints():
            return False

        # Get the fiducial point position
        pos = [0.0, 0.0, 0.0]
        post_branch_node.GetNthControlPointPosition(point_index, pos)

        # Find the nearest centerline to this point
        centerline_model, distance = find_nearest_centerline_to_point(pos)
        
        if not centerline_model:
            # Fallback: Try to find any centerline model
            try:
                centerline_model = slicer.util.getNode('Centerline model')
            except:
                pass
            if not centerline_model:
                all_models = slicer.util.getNodesByClass('vtkMRMLModelNode')
                for model in all_models:
                    if 'centerline' in model.GetName().lower() or 'tree' in model.GetName().lower():
                        centerline_model = model
                        break
        
        if not centerline_model:
            pass  # No centerline found for post branch circle creation
            return False

        points = slicer.util.arrayFromModelPoints(centerline_model)
        radii = slicer.util.arrayFromModelPointData(centerline_model, 'Radius')
        if points is None or len(points) == 0:
            return False
        if radii is None or len(radii) == 0:
            return False

        # Find closest centerline point
        min_distance = float('inf')
        closest_idx = 0
        for j, p in enumerate(points):
            d = ((pos[0]-p[0])**2 + (pos[1]-p[1])**2 + (pos[2]-p[2])**2) ** 0.5
            if d < min_distance:
                min_distance = d
                closest_idx = j

        center_point = points[closest_idx]
        radius = radii[closest_idx] if closest_idx < len(radii) else 1.0

        # Post branch points are always green
        expected_label = f"post-branch-{point_index + 1}"
        color = (0.0, 1.0, 0.0)  # Green for post-branch
        
        circle_name = f"Circle_{expected_label}"

        # Replace existing circle with same name if any
        existing_circle = None
        try:
            existing_circle = slicer.util.getNode(circle_name)
        except:
            pass
        if existing_circle:
            slicer.mrmlScene.RemoveNode(existing_circle)

        # Create new circle node
        circle_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsClosedCurveNode")
        circle_node.SetName(circle_name)

        # Configure display properties
        display_node = circle_node.GetDisplayNode()
        if display_node:
            display_node.SetColor(*color)
            display_node.SetSelectedColor(*color)
            display_node.SetLineWidth(4.0)
            display_node.SetVisibility(True)
            display_node.SetPointLabelsVisibility(False)
            display_node.SetFillVisibility(False)
            display_node.SetOutlineVisibility(True)

        # Apply transform (same as main placement)
        apply_transform_to_circle(circle_node)

        # Calculate direction and create perpendicular circle
        direction = calculate_centerline_direction(points, closest_idx)
        success = create_perpendicular_circle(circle_node, center_point, radius, direction)

        # Track and hide fiducial (same as main placement)
        if success:
            if not hasattr(slicer.modules, 'WorkflowCenterlineCircleNodes'):
                slicer.modules.WorkflowCenterlineCircleNodes = []
            slicer.modules.WorkflowCenterlineCircleNodes.append(circle_node)

            # Hide the fiducial point after creating circle
            try:
                post_branch_node.SetNthControlPointVisibility(point_index, False)
                bdn = post_branch_node.GetDisplayNode()
                if bdn:
                    bdn.SetPointLabelsVisibility(False)
            except Exception:
                pass
            
            pass  # Created circle for {expected_label}

        # Update circle dropdown after creating a post-branch circle
        if success:
            update_circle_dropdown()

        return success
    except Exception as e:
        pass  # Error creating post branch circle: {str(e)}
        return False

# ===============================================================================
# WORKFLOW2 FUNCTIONS - Centerline and Tube Mask Creation
# ===============================================================================

def create_centerline_and_tube_mask():
    """
    Creates centerline curves and tube masks for each start-slice and end-slice point pair
    from the F-1 point list. Creates distinct tubes for each pair with different colors.
    """
    
    f1_points = slicer.util.getNode('F-1')
    if not f1_points:
        pass
        return

    if f1_points.GetNumberOfControlPoints() < 4:
        pass
        return
    
    pass
    
    # Clear any existing centerline/tube nodes
    clear_existing_tubes_and_centerlines()
    
    # Calculate how many start/end pairs we have
    total_points = f1_points.GetNumberOfControlPoints()
    slice_points = total_points - 2  # Exclude pre-lesion and post-lesion points
    num_pairs = slice_points // 2
    
    if num_pairs == 0:
        pass
        return
    
    pass
    
    # Define colors for different tubes (RGB values)
    tube_colors = [
        (1.0, 0.0, 0.0),  # Red
        (0.0, 1.0, 0.0),  # Green  
        (0.0, 0.0, 1.0),  # Blue
        (1.0, 1.0, 0.0),  # Yellow
        (1.0, 0.0, 1.0),  # Magenta
        (0.0, 1.0, 1.0),  # Cyan
        (1.0, 0.5, 0.0),  # Orange
        (0.5, 0.0, 1.0),  # Purple
    ]
    
    created_tubes = []
    created_segmentations = []
    
    # Create tubes for each start/end slice pair
    for pair_index in range(num_pairs):
        start_point_index = 2 + (pair_index * 2)      # 2, 4, 6, 8, ...
        end_point_index = start_point_index + 1        # 3, 5, 7, 9, ...
        
        # Get the point positions
        start_pos = [0, 0, 0]
        end_pos = [0, 0, 0]
        f1_points.GetNthControlPointPosition(start_point_index, start_pos)
        f1_points.GetNthControlPointPosition(end_point_index, end_pos)
        
        # Create centerline points for this pair
        centerline_points = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
        centerline_points.SetName(f'CenterlinePoints_{pair_index + 1}')
        centerline_points.AddControlPoint(start_pos)
        centerline_points.AddControlPoint(end_pos)
        
        # Create centerline curve for this pair
        centerline_curve = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsCurveNode')
        centerline_curve.SetName(f'CenterlineCurve_{pair_index + 1}')
        centerline_curve.AddControlPoint(start_pos)
        centerline_curve.AddControlPoint(end_pos)
        centerline_curve.SetCurveTypeToLinear()
        
        # Create tube for this pair
        tube_model = create_tube_from_curve(centerline_curve, pair_index + 1)
        
        if tube_model:
            # Set color for this tube
            color_index = pair_index % len(tube_colors)
            tube_color = tube_colors[color_index]
            
            tube_display = tube_model.GetDisplayNode()
            if tube_display:
                tube_display.SetColor(tube_color[0], tube_color[1], tube_color[2])
                tube_display.SetOpacity(0.5)
            
            created_tubes.append(tube_model)
            
            # Create segmentation from this tube
            stenosis_segmentation = create_segmentation_from_tube(tube_model, pair_index + 1)
            if stenosis_segmentation:
                created_segmentations.append(stenosis_segmentation)
        
        pass
    
    # Add cropped volume to 3D scene
    add_cropped_volume_to_3d_scene()
    
    # Show statistics for all segmentations
    for segmentation in created_segmentations:
        show_segment_statistics(segmentation)
    
    pass

def clear_existing_tubes_and_centerlines():
    """
    Clear any existing centerline and tube nodes from previous runs
    """
    try:
        # Clear centerline points
        nodes_to_remove = []
        for node in slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode'):
            if node.GetName().startswith('CenterlinePoints'):
                nodes_to_remove.append(node)
        
        # Clear centerline curves
        for node in slicer.util.getNodesByClass('vtkMRMLMarkupsCurveNode'):
            if node.GetName().startswith('CenterlineCurve'):
                nodes_to_remove.append(node)
        
        # Clear tube models
        for node in slicer.util.getNodesByClass('vtkMRMLModelNode'):
            if node.GetName().startswith('TubeMask'):
                nodes_to_remove.append(node)
        
        # Clear tube segmentations
        for node in slicer.util.getNodesByClass('vtkMRMLSegmentationNode'):
            if node.GetName().startswith('TubeMaskSegmentation'):
                nodes_to_remove.append(node)
        
        # Remove all identified nodes
        for node in nodes_to_remove:
            slicer.mrmlScene.RemoveNode(node)
            
    except Exception as e:
        pass

def create_tube_from_curve(centerline_curve, pair_number):
    """
    Create a tube model from a centerline curve
    """
    try:
        curve_points = centerline_curve.GetCurvePointsWorld()
        
        if not curve_points or curve_points.GetNumberOfPoints() == 0:
            return None
        
        curve_polydata = vtk.vtkPolyData()
        curve_polydata.SetPoints(curve_points)
        
        lines = vtk.vtkCellArray()
        for i in range(curve_points.GetNumberOfPoints() - 1):
            line = vtk.vtkLine()
            line.GetPointIds().SetId(0, i)
            line.GetPointIds().SetId(1, i + 1)
            lines.InsertNextCell(line)
        
        curve_polydata.SetLines(lines)
        
        tube_filter = vtk.vtkTubeFilter()
        tube_filter.SetInputData(curve_polydata)
        tube_filter.SetRadius(2.0)
        tube_filter.SetNumberOfSides(12)
        tube_filter.CappingOn()
        tube_filter.Update()
        
        tube_model = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
        tube_model.SetName(f'TubeMask_{pair_number}')
        tube_model.SetAndObservePolyData(tube_filter.GetOutput())
        
        # Create display node
        tube_display = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelDisplayNode')
        tube_model.SetAndObserveDisplayNodeID(tube_display.GetID())
        
        return tube_model
        
    except Exception as e:
        return None

def create_segmentation_from_tube(tube_model, pair_number=1):
    """
    Convert the tube model to a segmentation for use as a mask.
    Each tube gets a unique segmentation name and color.
    """
    try:
        segmentation_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
        segmentation_node.SetName(f'TubeMaskSegmentation_{pair_number}')
        
        slicer.modules.segmentations.logic().ImportModelToSegmentationNode(tube_model, segmentation_node)
        
        segmentation = segmentation_node.GetSegmentation()
        segment_ids = vtk.vtkStringArray()
        segmentation.GetSegmentIDs(segment_ids)
        
        if segment_ids.GetNumberOfValues() > 0:
            segment_id = segment_ids.GetValue(0)
            segment = segmentation.GetSegment(segment_id)
            segment.SetName(f'TubeMask_{pair_number}')
            
            # Set unique colors for each tube segmentation
            colors = [
                (1.0, 0.0, 0.0),  # Red
                (0.0, 1.0, 0.0),  # Green  
                (0.0, 0.0, 1.0),  # Blue
                (1.0, 1.0, 0.0),  # Yellow
                (1.0, 0.0, 1.0),  # Magenta
                (0.0, 1.0, 1.0),  # Cyan
                (1.0, 0.5, 0.0),  # Orange
                (0.5, 0.0, 1.0),  # Purple
            ]
            color_index = (pair_number - 1) % len(colors)
            color = colors[color_index]
            segment.SetColor(color[0], color[1], color[2])
        
        pass
        return segmentation_node
        
    except Exception as e:
        pass
        return None

def add_cropped_volume_to_3d_scene():
    """
    Add the cropped volume to the 3D scene for visualization.
    """
    try:
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        cropped_volume = None
        
        for volume in volume_nodes:
            if 'cropped' in volume.GetName().lower():
                cropped_volume = volume
                break
        
        if not cropped_volume:
            pass
            return
        
        threeDWidget = slicer.app.layoutManager().threeDWidget(0)
        threeDView = threeDWidget.threeDView()
        
        volumeRenderingLogic = slicer.modules.volumerendering.logic()
        
        displayNode = volumeRenderingLogic.CreateDefaultVolumeRenderingNodes(cropped_volume)
        
        if displayNode:
            displayNode.SetVisibility(True)
            
            displayNode.SetRaycastTechnique(slicer.vtkMRMLVolumeRenderingDisplayNode.Composite)
            
            try:
                presetName = "CT-Chest-Contrast-Enhanced"
                volumeRenderingLogic.ApplyVolumeRenderingDisplayPreset(displayNode, presetName)
                pass
            except:
                try:
                    presetName = "CT-Cardiac"
                    volumeRenderingLogic.ApplyVolumeRenderingDisplayPreset(displayNode, presetName)
                    pass
                except:
                    pass
            
            volumeProperty = displayNode.GetVolumePropertyNode().GetVolumeProperty()
            if volumeProperty:
                volumeProperty.SetScalarOpacityUnitDistance(0.1)
                
                volumeProperty.SetGradientOpacity(0, 0.0)
                volumeProperty.SetGradientOpacity(1, 0.5)
                
                volumeProperty.SetInterpolationTypeToLinear()
                
                volumeProperty.SetShade(True)
                volumeProperty.SetAmbient(0.3)
                volumeProperty.SetDiffuse(0.6)
                volumeProperty.SetSpecular(0.5)
                volumeProperty.SetSpecularPower(40)
            
            displayNode.SetExpectedFPS(10.0)
            displayNode.SetGPUMemorySize(1024)
            
            pass
        else:
            pass
            
    except Exception as e:
        pass

def show_segment_statistics(stenosis_segmentation):
    """
    Open the Segment Statistics module to display density statistics for the stenosis mask.
    """
    try:
        if not stenosis_segmentation:
            pass
            return
        
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        analysis_volume = None
        
        for volume in volume_nodes:
            if 'cropped' in volume.GetName().lower():
                analysis_volume = volume
                pass
                break
        
        if not analysis_volume:
            pass
            pass
            for volume in volume_nodes:
                pass
            return
        
        slicer.util.selectModule('SegmentStatistics')
        
        try:
            segmentStatisticsWidget = slicer.modules.segmentstatistics.widgetRepresentation().self()
            
            slicer.app.processEvents()
            
            if hasattr(segmentStatisticsWidget, 'segmentationSelector'):
                segmentStatisticsWidget.segmentationSelector.setCurrentNode(stenosis_segmentation)
                pass
            else:
                pass
            
            volume_set = False
            if hasattr(segmentStatisticsWidget, 'scalarVolumeSelector'):
                segmentStatisticsWidget.scalarVolumeSelector.setCurrentNode(analysis_volume)
                slicer.app.processEvents()
                current_volume = segmentStatisticsWidget.scalarVolumeSelector.currentNode()
                if current_volume and current_volume.GetID() == analysis_volume.GetID():
                    pass
                    volume_set = True
                else:
                    pass
            

            if not volume_set and hasattr(segmentStatisticsWidget, 'scalarVolumeSelector'):
                try:

                    segmentStatisticsWidget.scalarVolumeSelector.setCurrentNodeID(analysis_volume.GetID())
                    slicer.app.processEvents()
                    current_volume = segmentStatisticsWidget.scalarVolumeSelector.currentNode()
                    if current_volume and current_volume.GetID() == analysis_volume.GetID():
                        pass
                        volume_set = True
                except:
                    pass
            
            if not volume_set:
                pass
                pass
            
            if hasattr(segmentStatisticsWidget, 'labelmapStatisticsCheckBox'):
                segmentStatisticsWidget.labelmapStatisticsCheckBox.setChecked(True)
            if hasattr(segmentStatisticsWidget, 'scalarVolumeStatisticsCheckBox'):
                segmentStatisticsWidget.scalarVolumeStatisticsCheckBox.setChecked(True)
        except AttributeError as ae:
            pass
            pass
               
    except Exception as e:
        pass
        
        try:
            slicer.util.selectModule('SegmentStatistics')
            pass
            pass
            pass
            
        except Exception as fallback_error:
            pass
            pass

def hide_crop_volume_ui_elements():
    """
    Hide ALL UI elements in the Crop Volume module - remove everything from the interface
    """
    try:
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if not crop_widget:
            return False
        
        elements_hidden = 0

        try:
            collapsible_buttons = crop_widget.findChildren("ctkCollapsibleButton")
            for button in collapsible_buttons:
                button.setVisible(False)
                elements_hidden += 1
        except Exception:
            pass
        try:
            push_buttons = crop_widget.findChildren(qt.QPushButton)
            for button in push_buttons:
                button.setVisible(False)
                elements_hidden += 1
        except Exception:
            pass
        try:
            labels = crop_widget.findChildren(qt.QLabel)
            for label in labels:
                label.setVisible(False)
                elements_hidden += 1
        except Exception:
            pass

        try:
            input_widgets = crop_widget.findChildren(qt.QLineEdit)
            input_widgets.extend(crop_widget.findChildren(qt.QSpinBox))
            input_widgets.extend(crop_widget.findChildren(qt.QDoubleSpinBox))
            input_widgets.extend(crop_widget.findChildren(qt.QComboBox))
            input_widgets.extend(crop_widget.findChildren(qt.QCheckBox))
            for widget in input_widgets:
                widget.setVisible(False)
                elements_hidden += 1
        except Exception:
            pass

        try:
            layouts = crop_widget.findChildren(qt.QHBoxLayout)
            layouts.extend(crop_widget.findChildren(qt.QVBoxLayout))
            layouts.extend(crop_widget.findChildren(qt.QGridLayout))
            for layout in layouts:
                parent_widget = layout.parent()
                if parent_widget and parent_widget != crop_widget:
                    parent_widget.setVisible(False)
                    elements_hidden += 1
        except Exception:
            pass

        try:
            all_children = crop_widget.findChildren(qt.QWidget)
            for child in all_children:
                if child.isVisible() and child != crop_widget:
                    child.setVisible(False)
                    elements_hidden += 1
        except Exception:
            pass
        
        return True
        
    except Exception as e:
        pass
        return False


def restore_crop_ui():
    """Console helper to restore all hidden Crop Volume UI elements"""
    try:
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if not crop_widget:
            pass
            return False
        
        # Find all widgets and make them visible
        all_widgets = crop_widget.findChildren(qt.QWidget)
        restored_count = 0
        
        for widget in all_widgets:
            if hasattr(widget, 'setVisible'):
                widget.setVisible(True)
                restored_count += 1
        
        pass
        return True
        
    except Exception as e:
        pass
        return False

def hide_extract_centerline_ui_elements():
    """
    Hide all UI elements in the Extract Centerline module except the inputs section.
    Outputs section is collapsed, advanced section is completely removed.
    """
    try:
        extract_centerline_widget = slicer.modules.extractcenterline.widgetRepresentation()
        if not extract_centerline_widget:
            pass
            return False
        
        
        # Elements to hide completely (Apply button is NOT included - keep it visible)
        elements_to_hide = [
            "parameterSetLabel",                    # Parameter set label
            "parameterNodeSelector",                # Parameter node selector
            "advancedCollapsibleButton",            # Advanced section (completely hidden)
            "verticalSpacer"                        # Vertical spacer
        ]
        
        elements_hidden = 0
        
        # Hide elements by object name
        for element_name in elements_to_hide:
            try:
                elements = extract_centerline_widget.findChildren(qt.QWidget, element_name)
                for element in elements:
                    element.setVisible(False)
                    element.hide()  # Also use hide() method
                    if hasattr(element, 'setEnabled'):
                        element.setEnabled(False)  # Also disable the element
                    elements_hidden += 1
                    pass
            except Exception as e:
                pass
        
        # Handle the outputs section - make sure it's visible but collapsed
        try:
            outputs_buttons = extract_centerline_widget.findChildren("ctkCollapsibleButton", "outputsCollapsibleButton")
            for button in outputs_buttons:
                button.setVisible(True)  # Keep visible
                # Try multiple approaches to collapse the button
                collapsed_successfully = False
                
                # Method 1: Use collapsed property directly
                if hasattr(button, 'collapsed'):
                    button.collapsed = True
                    collapsed_successfully = True
                    pass
                
                # Method 2: Use setCollapsed method
                elif hasattr(button, 'setCollapsed'):
                    button.setCollapsed(True)
                    collapsed_successfully = True
                    pass
                
                # Method 3: Try Qt property system
                else:
                    try:
                        button.setProperty("collapsed", True)
                        collapsed_successfully = True
                        pass
                    except:
                        pass
                
                if not collapsed_successfully:
                    pass
                    
        except Exception as e:
            pass
        
        # Double-check advanced section is completely hidden
        try:
            advanced_buttons = extract_centerline_widget.findChildren("ctkCollapsibleButton", "advancedCollapsibleButton")
            for button in advanced_buttons:
                button.setVisible(False)
                button.hide()  # Also explicitly call hide()
                elements_hidden += 1
                pass
        except Exception as e:
            pass
        
        # Also hide the form layout rows containing parameter set elements (row 0)
        try:
            form_layouts = extract_centerline_widget.findChildren(qt.QFormLayout, "formLayout")
            for layout in form_layouts:
                # Hide row 0 (parameter set row)
                if layout.rowCount() > 0:
                    label_item = layout.itemAt(0, qt.QFormLayout.LabelRole)
                    field_item = layout.itemAt(0, qt.QFormLayout.FieldRole)
                    if label_item and label_item.widget():
                        label_item.widget().setVisible(False)
                        label_item.widget().hide()
                        elements_hidden += 1
                    if field_item and field_item.widget():
                        field_item.widget().setVisible(False)
                        field_item.widget().hide()
                        elements_hidden += 1
        except Exception as e:
            pass
        
        # Additional comprehensive search for elements to hide
        try:
            # Search for all widgets by objectName and hide them
            for element_name in elements_to_hide:
                widgets = extract_centerline_widget.findChildren(qt.QWidget)
                for widget in widgets:
                    if hasattr(widget, 'objectName') and widget.objectName() == element_name:
                        widget.setVisible(False)
                        widget.hide()
                        elements_hidden += 1
                        pass
        except Exception as e:
            pass
        
        # Ensure the inputs collapsible button is visible and expanded
        try:
            inputs_buttons = extract_centerline_widget.findChildren("ctkCollapsibleButton", "inputsCollapsibleButton")
            for button in inputs_buttons:
                button.setVisible(True)
                if hasattr(button, 'setCollapsed'):
                    button.setCollapsed(False)
                # Also try the 'collapsed' property directly
                if hasattr(button, 'collapsed'):
                    button.collapsed = False
                pass
        except Exception as e:
            pass
        
        # Double-check that advanced section is completely hidden (but keep Apply button visible)
        try:
            # Find and hide advanced section by multiple methods
            advanced_elements = extract_centerline_widget.findChildren("ctkCollapsibleButton", "advancedCollapsibleButton")
            for element in advanced_elements:
                element.setVisible(False)
                element.hide()  # Also call hide() method
                elements_hidden += 1
                pass
                
            # Note: Apply button is intentionally left visible and functional
                    
        except Exception as e:
            pass
        
        # Force a GUI update and try alternative collapse approach
        slicer.app.processEvents()
        
        # Alternative approach: Try to find and manually collapse the outputs section
        try:
            # Give the GUI time to fully load
            import time
            time.sleep(0.1)
            slicer.app.processEvents()
            
            # Try finding by different criteria
            all_collapsible_buttons = extract_centerline_widget.findChildren("ctkCollapsibleButton")
            for button in all_collapsible_buttons:
                button_text = ""
                if hasattr(button, 'text'):
                    button_text = button.text
                elif hasattr(button, 'getText'):
                    button_text = button.getText()
                
                if "output" in button_text.lower():
                    pass
                    # Try to collapse it if it's currently expanded
                    if hasattr(button, 'collapsed'):
                        if not button.collapsed:  # If currently expanded
                            button.collapsed = True
                            pass
                    elif hasattr(button, 'setCollapsed'):
                        button.setCollapsed(True)
                        pass
                        
        except Exception as e:
            pass
        
        # Force a GUI update
        slicer.app.processEvents()
        
        # FINAL STEP: Aggressively hide advanced section one more time (but keep Apply button visible)
        try:
            pass
            
            # Find ALL widgets that might be the advanced section
            all_widgets = extract_centerline_widget.findChildren(qt.QWidget)
            for widget in all_widgets:
                widget_name = ""
                try:
                    if hasattr(widget, 'objectName'):
                        widget_name = str(widget.objectName())
                except Exception as e:
                    continue
                
                # Hide any widget with "advanced" in the name
                if "advanced" in widget_name.lower():
                    try:
                        widget.setVisible(False)
                        widget.hide()
                        if hasattr(widget, 'setEnabled'):
                            widget.setEnabled(False)
                        pass
                    except Exception as e:
                        pass
                
                # Note: Apply button widgets are intentionally left visible and functional
            
            # Also check by widget text content
            all_collapsible_buttons = extract_centerline_widget.findChildren("ctkCollapsibleButton")
            for button in all_collapsible_buttons:
                button_text = ""
                try:
                    if hasattr(button, 'text'):
                        button_text = str(button.text).lower()
                except Exception as e:
                    continue
                
                if "advanced" in button_text:
                    try:
                        button.setVisible(False)
                        button.hide()
                        if hasattr(button, 'setEnabled'):
                            button.setEnabled(False)
                        pass
                    except Exception as e:
                        pass
            
            # Note: Apply button widgets are intentionally left visible and functional
                    
        except Exception as e:
            pass
        
        # One more GUI update
        slicer.app.processEvents()
        
        return True
        
    except Exception as e:
        pass
        return False

def setup_minimal_extract_centerline_ui():
    """
    Set up the Extract Centerline module with minimal UI (only the inputs section)
    """
    try:
        # Expand the left module panel for ExtractCenterline setup
        expand_left_module_panel()
        
        # First ensure we're in the Extract Centerline module
        slicer.util.selectModule("ExtractCenterline")
        slicer.app.processEvents()
        
        # Hide all UI elements except the inputs section
        hide_success = hide_extract_centerline_ui_elements()
        
        if hide_success:
            pass
            return True
        else:
            pass
            return False
            
    except Exception as e:
        pass
        return False

def restore_extract_centerline_ui():
    """
    Restore all hidden Extract Centerline UI elements
    """
    try:
        extract_centerline_widget = slicer.modules.extractcenterline.widgetRepresentation()
        if not extract_centerline_widget:
            pass
            return False
        
        # Find all widgets and make them visible
        all_widgets = extract_centerline_widget.findChildren(qt.QWidget)
        restored_count = 0
        
        for widget in all_widgets:
            if hasattr(widget, 'setVisible'):
                widget.setVisible(True)
                restored_count += 1
        
        pass
        return True
        
    except Exception as e:
        pass
        return False

def start_with_segment_editor_scissors():
    """
    Start segmentation workflow using programmatic Segment Editor API without opening GUI.
    Creates a scissors tool button for user control.
    """
    try:
        # Get the current volume node (should be the cropped volume from previous step)
        volume_node = None
        volume_nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
        
        # Look for cropped volume first
        for volume in volume_nodes:
            if 'cropped' in volume.GetName().lower():
                volume_node = volume
                break
        
        # If no cropped volume, use the first available volume
        if not volume_node and volume_nodes:
            volume_node = volume_nodes[0]
        
        if not volume_node:
            pass
            return False
        
        # Create or get segmentation node
        segmentation_node = None
        existing_segmentations = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
        
        # Look for existing workflow segmentation
        for seg in existing_segmentations:
            if "Workflow" in seg.GetName() or volume_node.GetName() in seg.GetName():
                segmentation_node = seg
                break
        
        # Create new segmentation if none found
        if not segmentation_node:
            segmentation_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
            segmentation_node.SetName(f"{volume_node.GetName()}_WorkflowSegmentation")
            
            # Create a default segment
            segmentation = segmentation_node.GetSegmentation()
            segment_id = segmentation.AddEmptySegment("Segment_1")
            segment = segmentation.GetSegment(segment_id)
            segment.SetColor(1.0, 0.0, 0.0)  # Red color
        
        # Set up programmatic segment editor (no GUI)
        segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
        slicer.mrmlScene.AddNode(segmentEditorNode)
        segmentEditorNode.SetAndObserveSegmentationNode(segmentation_node)
        segmentEditorNode.SetAndObserveSourceVolumeNode(volume_node)
        
        # Get the first segment ID
        segmentation = segmentation_node.GetSegmentation()
        segment_ids = vtk.vtkStringArray()
        segmentation.GetSegmentIDs(segment_ids)
        if segment_ids.GetNumberOfValues() > 0:
            segment_id = segment_ids.GetValue(0)
            segmentEditorNode.SetSelectedSegmentID(segment_id)
        
        # Create invisible segment editor widget for API access
        segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
        
        # Store references for scissors tool control
        slicer.modules.WorkflowSegmentEditorNode = segmentEditorNode
        slicer.modules.WorkflowSegmentEditorWidget = segmentEditorWidget
        slicer.modules.WorkflowSegmentationNode = segmentation_node
        slicer.modules.WorkflowScissorsActive = False
        
        # Create scissors tool button in the workflow UI
        create_scissors_tool_button()

        return True
        
    except Exception as e:
        pass
        return False

def add_buttons_to_crop_module(crop_widget, scissors_button, finish_button):
    """
    Add scissors and finish buttons to the Crop Volume module GUI
    """
    try:
        # First, remove/hide the original large green "APPLY CROP" button
        remove_original_crop_apply_button(crop_widget)
        
        # Try to get the crop module
        crop_module = None
        if hasattr(crop_widget, 'self'):
            try:
                crop_module = crop_widget.self()
            except Exception:
                pass
        
        if not crop_module:
            crop_module = crop_widget
        
        # Find the main UI container in the crop module
        main_ui_widget = None
        
        # Strategy 1: Look for the main widget container
        if hasattr(crop_module, 'ui') and hasattr(crop_module.ui, 'widget'):
            main_ui_widget = crop_module.ui.widget
        elif hasattr(crop_module, 'widget'):
            main_ui_widget = crop_module.widget
        elif hasattr(crop_widget, 'widget'):
            main_ui_widget = crop_widget.widget
        
        # Strategy 2: Get the module widget representation directly
        if not main_ui_widget:
            main_ui_widget = crop_widget
        
        # Create a container widget for our buttons
        button_container = qt.QWidget()
        button_layout = qt.QHBoxLayout(button_container)
        button_layout.addWidget(scissors_button)
        button_layout.addWidget(finish_button)
        
        # Add some instructions
        instructions = qt.QLabel("Workflow: Use scissors to edit segmentation, then finish cropping")
        instructions.setStyleSheet("color: #666; font-size: 12px; padding: 5px; font-weight: bold;")
        instructions.setWordWrap(True)
        
        # Create final container with instructions and buttons
        final_container = qt.QWidget()
        final_layout = qt.QVBoxLayout(final_container)
        final_layout.addWidget(instructions)
        final_layout.addWidget(button_container)
        
        # Try to add to the GUI layout
        if main_ui_widget and hasattr(main_ui_widget, 'layout'):
            layout = main_ui_widget.layout()
            if layout:
                # Insert at the top of the module
                layout.insertWidget(0, final_container)
                pass
                return True
            else:
                # Try to create a new layout
                new_layout = qt.QVBoxLayout(main_ui_widget)
                new_layout.insertWidget(0, final_container)
                pass
                return True
        else:
            # Fallback: try to find a suitable container widget
            container_widgets = crop_widget.findChildren(qt.QWidget)
            for widget in container_widgets:
                if hasattr(widget, 'layout') and widget.layout() and widget.layout().count() > 0:
                    widget.layout().insertWidget(0, final_container)
                    pass
                    return True
        
        pass
        return False
        
    except Exception as e:
        pass
        return False

def ensure_crop_button_disabled_if_completed():
    """
    Ensure crop apply button remains disabled if crop has been completed
    """
    try:
        if hasattr(slicer.modules, 'WorkflowCropCompleted') and slicer.modules.WorkflowCropCompleted:
            crop_widget = slicer.modules.cropvolume.widgetRepresentation()
            if crop_widget:
                disable_crop_apply_button(crop_widget)
    except Exception as e:
        pass

def disable_crop_apply_button(crop_widget):
    """
    Disable and grey out the crop apply button once it has been used
    """
    try:
        disabled_count = 0
        
        # Method 1: Disable the stored reference button
        if hasattr(slicer.modules, 'CropLargeApplyButton'):
            button = slicer.modules.CropLargeApplyButton
            if button and button.parent():
                # Disable the button
                button.setEnabled(False)
                
                # Change text to indicate completion
                button.setText("CROP APPLIED ✓")
                
                # Set grey styling
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #808080;
                        color: #FFFFFF;
                        border: 2px solid #606060;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;
                        padding: 10px 20px;
                        min-height: 40px;
                        min-width: 150px;
                    }
                """)
                
                disabled_count += 1
        
        # Method 2: Search for and disable any "APPLY CROP" buttons in the crop widget
        if crop_widget:
            all_buttons = crop_widget.findChildren(qt.QPushButton)
            for button in all_buttons:
                try:
                    button_text = button.text if hasattr(button, 'text') else ""
                    if button_text and ("APPLY CROP" in button_text or "Apply" in button_text):
                        # Disable the button
                        button.setEnabled(False)
                        
                        # Change text to indicate completion
                        if "APPLY CROP" in button_text:
                            button.setText("CROP APPLIED ✓")
                        else:
                            button.setText("APPLIED ✓")
                        
                        # Set grey styling
                        button.setStyleSheet("""
                            QPushButton {
                                background-color: #808080;
                                color: #FFFFFF;
                                border: 2px solid #606060;
                                border-radius: 8px;
                                font-size: 14px;
                                font-weight: bold;
                                padding: 8px 16px;
                                min-height: 30px;
                            }
                        """)
                        
                        disabled_count += 1
                except Exception as e:
                    continue
        
        return disabled_count > 0
        
    except Exception as e:
        return False

def remove_original_crop_apply_button(crop_widget):
    """
    Remove or hide the original large green "APPLY CROP" button from the Crop Volume module
    """
    try:
        removed_count = 0
        
        # Method 1: Remove the stored reference button
        if hasattr(slicer.modules, 'CropLargeApplyButton'):
            button = slicer.modules.CropLargeApplyButton
            if button and button.parent():
                # Remove from parent layout
                parent = button.parent()
                if hasattr(parent, 'layout') and parent.layout():
                    parent.layout().removeWidget(button)
                elif hasattr(parent, 'removeWidget'):
                    parent.removeWidget(button)
                
                # Hide and delete the button
                button.hide()
                button.setParent(None)
                
                # Remove the reference
                del slicer.modules.CropLargeApplyButton
                removed_count += 1
                pass
        
        # Method 2: Search for and remove any "APPLY CROP" buttons in the crop widget
        if crop_widget:
            all_buttons = crop_widget.findChildren(qt.QPushButton)
            for button in all_buttons:
                try:
                    button_text = button.text if hasattr(button, 'text') else ""
                    if button_text and "APPLY CROP" in button_text:
                        # Remove from parent layout
                        parent = button.parent()
                        if parent and hasattr(parent, 'layout') and parent.layout():
                            parent.layout().removeWidget(button)
                        elif parent and hasattr(parent, 'removeWidget'):
                            parent.removeWidget(button)
                        
                        # Hide and delete the button
                        button.hide()
                        button.setParent(None)
                        removed_count += 1
                        pass
                except Exception as e:
                    pass
        
        # Method 3: Also look for and hide any other large green buttons that might be apply buttons
        if crop_widget:
            all_buttons = crop_widget.findChildren(qt.QPushButton)
            for button in all_buttons:
                try:
                    button_text = button.text if hasattr(button, 'text') else ""
                    button_style = button.styleSheet() if hasattr(button, 'styleSheet') else ""
                    
                    # Check if it's a large green button (likely an apply button)
                    if (button_text and 
                        ("apply" in button_text.lower() or "crop" in button_text.lower()) and 
                        ("#28a745" in button_style or "background-color: #28a745" in button_style)):
                        
                        # Hide the button instead of removing it completely (safer)
                        button.hide()
                        removed_count += 1
                        pass
                except Exception as e:
                    pass
        
        if removed_count > 0:
            pass
        else:
            pass
        
        return removed_count > 0
        
    except Exception as e:
        pass
        return False

def create_scissors_tool_button():
    """
    Create a scissors tool toggle button for the workflow UI
    """
    try:
        # Find a suitable parent widget (main window or workflow panel)
        main_window = slicer.util.mainWindow()
        if not main_window:
            pass
            return False
        
        scissors_button = qt.QPushButton("SCISSORS (ERASE)")
        scissors_button.setCheckable(True)
        scissors_button.setChecked(False)
        scissors_button.setStyleSheet("""
            QPushButton { 
                background-color: #007bff; 
                color: white; 
                border: none; 
                padding: 12px 20px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 14px;
                min-height: 40px;
                min-width: 150px;
            }
            QPushButton:hover { 
                background-color: #0056b3; 
            }
            QPushButton:checked { 
                background-color: #dc3545; 
                border: 2px solid #c82333;
            }
            QPushButton:checked:hover { 
                background-color: #c82333; 
            }
        """)

        scissors_button.connect('toggled(bool)', lambda checked: toggle_scissors_tool_programmatic(checked))
        try:
            crop_widget = slicer.modules.cropvolume.widgetRepresentation()
            if crop_widget:
                finish_button = qt.QPushButton("FINISH CROPPING")
                finish_button.setStyleSheet("""
                    QPushButton { 
                        background-color: #28a745; 
                        color: white; 
                        border: 2px solid #1e7e34; 
                        padding: 15px 20px; 
                        font-weight: bold;
                        border-radius: 8px;
                        margin: 5px;
                        font-size: 16px;
                        min-height: 50px;
                        min-width: 180px;
                    }
                    QPushButton:hover { 
                        background-color: #218838; 
                        border: 2px solid #155724;
                    }
                    QPushButton:pressed { 
                        background-color: #1e7e34; 
                        border: 2px solid #0f4c2c;
                    }
                """)
                finish_button.connect('clicked()', lambda: on_finish_cropping())
                
                # Update scissors button styling to match the crop module look
                scissors_button.setStyleSheet("""
                    QPushButton { 
                        background-color: #007bff; 
                        color: white; 
                        border: 2px solid #0056b3; 
                        padding: 15px 20px; 
                        font-weight: bold;
                        border-radius: 8px;
                        margin: 5px;
                        font-size: 16px;
                        min-height: 50px;
                        min-width: 180px;
                    }
                    QPushButton:hover { 
                        background-color: #0056b3; 
                        border: 2px solid #004085;
                    }
                    QPushButton:checked { 
                        background-color: #dc3545; 
                        border: 2px solid #c82333;
                    }
                    QPushButton:checked:hover { 
                        background-color: #c82333; 
                        border: 2px solid #bd2130;
                    }
                """)
                
                success = add_buttons_to_crop_module(crop_widget, scissors_button, finish_button)
                
                if success:
                    slicer.modules.WorkflowFinishButton = finish_button
                else:
                    create_floating_scissors_widget(scissors_button)
            else:
                create_floating_scissors_widget(scissors_button)
                
        except Exception as e:
            create_floating_scissors_widget(scissors_button)
        
        slicer.modules.WorkflowScissorsButton = scissors_button
        return True
        
    except Exception as e:
        return False

def create_floating_scissors_widget(scissors_button):
    """
    Create a floating widget for the scissors button and finish cropping button
    """
    try:
        # Create floating widget
        floating_widget = qt.QWidget()
        floating_widget.setWindowTitle("Workflow Tools")
        floating_widget.setWindowFlags(qt.Qt.WindowStaysOnTopHint | qt.Qt.Tool)
        
        # Set layout
        layout = qt.QVBoxLayout()
        layout.addWidget(scissors_button)
        finish_button = qt.QPushButton("FINISH CROPPING")
        finish_button.setStyleSheet("""
            QPushButton { 
                background-color: #28a745; 
                color: white; 
                border: none; 
                padding: 12px 20px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 14px;
                min-height: 40px;
                min-width: 150px;
            }
            QPushButton:hover { 
                background-color: #218838; 
            }
            QPushButton:pressed { 
                background-color: #1e7e34; 
            }
        """)
        
        # Connect finish button to continue workflow
        finish_button.connect('clicked()', lambda: on_finish_cropping())
        layout.addWidget(finish_button)
        
        # Add instructions
        instructions = qt.QLabel("Use scissors tool to ERASE/SUBTRACT from segmentation, then click Finish Cropping to continue")
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-size: 12px; padding: 10px;")
        layout.addWidget(instructions)
        
        floating_widget.setLayout(layout)
        floating_widget.resize(250, 180)
        
        # Position in top-right corner
        main_window = slicer.util.mainWindow()
        if main_window:
            main_geometry = main_window.geometry()
            floating_widget.move(main_geometry.right() - 270, main_geometry.top() + 100)
        
        floating_widget.show()
        
        # Store references
        slicer.modules.WorkflowScissorsWidget = floating_widget
        slicer.modules.WorkflowFinishButton = finish_button
        
        pass
        
    except Exception as e:
        pass

def toggle_scissors_tool_programmatic(activated):
    """
    Toggle the scissors tool on/off programmatically using segment editor widget
    """
    try:
        if not hasattr(slicer.modules, 'WorkflowSegmentEditorWidget'):
            return False
        
        segmentEditorWidget = slicer.modules.WorkflowSegmentEditorWidget
        
        if activated:
            # Activate scissors tool
            segmentEditorWidget.setActiveEffectByName("Scissors")
            effect = segmentEditorWidget.activeEffect()
            
            if effect:
                # Configure scissors tool for workflow use - set to ERASE/SUBTRACT mode
                if hasattr(effect, 'setParameter'):
                    effect.setParameter("Operation", "EraseInside")  # Erase inside (subtract/cut)
                
                # Enable slice view interactions for scissors
                interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
                if interactionNode:
                    interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
                
                slicer.modules.WorkflowScissorsActive = True
                
                # Update button appearance
                if hasattr(slicer.modules, 'WorkflowScissorsButton'):
                    button = slicer.modules.WorkflowScissorsButton
                    button.setText("SCISSORS ACTIVE (ERASE)")
                
            else:
                return False
                
        else:
            # Deactivate scissors tool
            segmentEditorWidget.setActiveEffectByName("")  # Clear active effect
            
            # Return to normal interaction mode
            interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
            if interactionNode:
                interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
            
            slicer.modules.WorkflowScissorsActive = False
            
            # Update button appearance
            if hasattr(slicer.modules, 'WorkflowScissorsButton'):
                button = slicer.modules.WorkflowScissorsButton
                button.setText("SCISSORS (ERASE)")
            
        return True
    except Exception as e:
        return False

def cleanup_scissors_tool_ui():
    """
    Clean up scissors tool UI elements and restore original crop apply button
    """
    try:
        # Clean up button
        if hasattr(slicer.modules, 'WorkflowScissorsButton'):
            button = slicer.modules.WorkflowScissorsButton
            if button.parent():
                parent = button.parent()
                if hasattr(parent, 'removeWidget'):
                    parent.removeWidget(button)
                elif hasattr(parent, 'layout') and parent.layout():
                    parent.layout().removeWidget(button)
            button.setParent(None)
            del slicer.modules.WorkflowScissorsButton
        
        # Clean up floating widget
        if hasattr(slicer.modules, 'WorkflowScissorsWidget'):
            widget = slicer.modules.WorkflowScissorsWidget
            widget.close()
            widget.setParent(None)
            del slicer.modules.WorkflowScissorsWidget
        
        # Clean up finish button
        if hasattr(slicer.modules, 'WorkflowFinishButton'):
            button = slicer.modules.WorkflowFinishButton
            if button.parent():
                parent = button.parent()
                if hasattr(parent, 'removeWidget'):
                    parent.removeWidget(button)
                elif hasattr(parent, 'layout') and parent.layout():
                    parent.layout().removeWidget(button)
            button.setParent(None)
            del slicer.modules.WorkflowFinishButton
        
        # Clean up segment editor components
        if hasattr(slicer.modules, 'WorkflowSegmentEditorNode'):
            node = slicer.modules.WorkflowSegmentEditorNode
            slicer.mrmlScene.RemoveNode(node)
            del slicer.modules.WorkflowSegmentEditorNode
        
        if hasattr(slicer.modules, 'WorkflowSegmentEditorWidget'):
            widget = slicer.modules.WorkflowSegmentEditorWidget
            widget.setParent(None)
            del slicer.modules.WorkflowSegmentEditorWidget
        
        for attr in ['WorkflowSegmentationNode', 'WorkflowScissorsActive']:
            if hasattr(slicer.modules, attr):
                delattr(slicer.modules, attr)
        
        restore_original_crop_apply_button()
        
    except Exception as e:
        pass

def restore_original_crop_apply_button():
    """
    Restore the original large green "APPLY CROP" button to the Crop Volume module
    """
    try:
        # Check if crop has been completed and ensure button stays disabled
        if hasattr(slicer.modules, 'WorkflowCropCompleted') and slicer.modules.WorkflowCropCompleted:
            ensure_crop_button_disabled_if_completed()
            return
            
        # Check if we're still in the Crop Volume module
        current_module = slicer.util.selectedModule()
        if current_module != "CropVolume":
            return
        if hasattr(slicer.modules, 'CropLargeApplyButton'):
            button = slicer.modules.CropLargeApplyButton
            if button and button.parent():
                # Only restore if not already disabled from completion
                if button.isEnabled() or not button.text().endswith("✓"):
                    button.show()
                return
    except Exception as e:
        pass


# ===============================================================================
# DICOM DEBUGGING AND TESTING FUNCTIONS
# ===============================================================================

def test_dicom_directory_loading(directory_path):
    """
    Test DICOM loading from a directory (console helper function).
    Usage: test_dicom_directory_loading(r"C:\\Users\\croger52\\Desktop\\SYS_01")
    """
    import os
    
    if not os.path.exists(directory_path):
        return
    
    if not os.path.isdir(directory_path):
        return
    
    # List all files and identify potential DICOM files and header files
    try:
        all_files = []
        potential_dicom_files = []
        header_files = []
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                full_path = os.path.join(root, file)
                all_files.append(full_path)
                
                file_lower = file.lower()
                
                # Check for header files first
                if 'v_headers' in file_lower:
                    header_files.append((full_path, "DICOM header file"))
                    continue
                
                is_dicom = False
                reason = []
                
                # Check various DICOM patterns
                if file_lower.endswith(('.dcm', '.dicom', '.ima')):
                    is_dicom = True
                    reason.append("standard extension")
                elif '.' not in file:
                    is_dicom = True
                    reason.append("no extension")
                elif file_lower.startswith(('i', 'im', 'ima', 'dicom')):
                    is_dicom = True
                    reason.append("DICOM prefix")
                elif any(pattern in file_lower for pattern in ['ctdc', 'ct', 'mr', 'us', 'xr']):
                    is_dicom = True
                    reason.append("medical imaging pattern")
                elif file.count('.') >= 1:
                    parts = file.split('.')
                    if len(parts) >= 2 and parts[-1].isdigit():
                        is_dicom = True
                        reason.append("numeric extension")
                
                if is_dicom:
                    potential_dicom_files.append((full_path, ", ".join(reason)))
        


        
        # Analyze for DICOM series patterns
        numeric_files = []
        ctdc_files = []
        standard_dicom_files = []
        
        for file_path, reason in potential_dicom_files:
            filename = os.path.basename(file_path)
            if 'CTDC' in filename.upper():
                ctdc_files.append((filename, reason))
            elif '.' in filename and filename.split('.')[-1].isdigit():
                numeric_files.append((filename, reason))
            elif filename.lower().endswith(('.dcm', '.dicom')):
                standard_dicom_files.append((filename, reason))

            
        # Test loading the enhanced function
        success = load_dicom_from_source_file(directory_path)
        
        if success:
            # Check if we got a proper volume series
            volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
            if volume_nodes:
                latest_volume = volume_nodes[-1]  # Get the most recently loaded volume
                image_data = latest_volume.GetImageData()
                if image_data:
                    dimensions = image_data.GetDimensions()

        
    except Exception as e:
        pass

def debug_dicom_file(file_path):
    """
    Debug information about a specific DICOM file.
    Usage: debug_dicom_file(r"C:\\Users\\croger52\\Desktop\\SYS_01\\i1559699.CTDC.1")
    """
    import os
    try:
        
        if not os.path.exists(file_path):
            return
            
        
        # Try to read first few bytes to check if it looks like DICOM
        try:
            with open(file_path, 'rb') as f:
                first_bytes = f.read(200)
                
                # Check for DICOM magic number at offset 128
                if len(first_bytes) > 132:
                    magic = first_bytes[128:132]
                    is_dicom = magic == b'DICM'
                
        except Exception as e:
            pass
            
    except Exception as e:
        pass

def set_source_path(new_path):
    """
    Helper function to update the source_slicer.txt file with a new DICOM path.
    Usage: set_source_path(r"C:\\Users\\croger52\\Desktop\\SYS_01")
    """
    import os
    try:
        user_home = os.path.expanduser("~")
        source_file_path = os.path.join(user_home, "source_slicer.txt")
        
        with open(source_file_path, 'w', encoding='utf-8') as f:
            f.write(new_path)
            
        
        # Reset the processed flag so it can be loaded again
        if hasattr(slicer.modules, 'SourceSlicerFileProcessed'):
            delattr(slicer.modules, 'SourceSlicerFileProcessed')
            
    except Exception as e:
        pass

def fix_dicom_spacing_and_orientation(volume_node, dicom_directory=None):
    """
    Attempt to fix spacing and orientation issues in a loaded DICOM volume.
    This function tries to extract proper spacing from DICOM headers if available.
    
    Args:
        volume_node: The volume node to fix
        dicom_directory: Optional directory containing DICOM files for header analysis
        
    Returns:
        bool: True if corrections were applied, False otherwise
    """
    import os
    
    if not volume_node:
        return False
    
    try:
        
        # Get current properties
        current_spacing = volume_node.GetSpacing()
        image_data = volume_node.GetImageData()
        
        if not image_data:
            return False
        
        dims = image_data.GetDimensions()
        
        # Try to analyze DICOM files in directory for proper spacing
        corrections_applied = False
        
        if dicom_directory and os.path.exists(dicom_directory):
            try:
                
                # Find DICOM files
                dicom_files = []
                for root, dirs, files in os.walk(dicom_directory):
                    for file in files:
                        if (file.endswith(('.dcm', '.DICOM')) or 
                            ('.' in file and file.split('.')[-1].isdigit()) or
                            'CTDC' in file.upper()):
                            dicom_files.append(os.path.join(root, file))
                
                if len(dicom_files) >= 2:
                    # Sort files to get proper sequence
                    dicom_files.sort()
                    
                    # Try to read first few files to get spacing info
                    try:
                        import pydicom
                        
                        # Read first file
                        ds1 = pydicom.dcmread(dicom_files[0], force=True)
                        
                        # Get pixel spacing
                        pixel_spacing = None
                        if hasattr(ds1, 'PixelSpacing') and ds1.PixelSpacing:
                            pixel_spacing = [float(x) for x in ds1.PixelSpacing]
                        
                        # Calculate slice thickness from file positions if possible
                        slice_thickness = None
                        if len(dicom_files) > 1:
                            try:
                                ds2 = pydicom.dcmread(dicom_files[1], force=True)
                                
                                # Try to get slice positions
                                if (hasattr(ds1, 'ImagePositionPatient') and ds1.ImagePositionPatient and
                                    hasattr(ds2, 'ImagePositionPatient') and ds2.ImagePositionPatient):
                                    
                                    pos1 = [float(x) for x in ds1.ImagePositionPatient]
                                    pos2 = [float(x) for x in ds2.ImagePositionPatient]
                                    
                                    # Calculate distance between slices
                                    import math
                                    slice_thickness = math.sqrt(sum([(p2-p1)**2 for p1, p2 in zip(pos1, pos2)]))
                                
                                elif hasattr(ds1, 'SliceThickness') and ds1.SliceThickness:
                                    slice_thickness = float(ds1.SliceThickness)
                                    
                            except Exception as slice_error:
                                pass
                        
                        # Apply corrections if we found proper spacing
                        if pixel_spacing:
                            new_spacing = list(current_spacing)
                            
                            # Apply pixel spacing to x,y
                            new_spacing[0] = pixel_spacing[0] if len(pixel_spacing) > 0 else current_spacing[0]
                            new_spacing[1] = pixel_spacing[1] if len(pixel_spacing) > 1 else current_spacing[1]
                            
                            # Apply slice thickness to z if available
                            if slice_thickness and slice_thickness > 0:
                                new_spacing[2] = slice_thickness
                            elif len(pixel_spacing) > 1:
                                # Use average pixel spacing as estimate for slice thickness
                                new_spacing[2] = (pixel_spacing[0] + pixel_spacing[1]) / 2
                            
                            # Only apply if significantly different from current
                            spacing_diff = max([abs(new_spacing[i] - current_spacing[i]) for i in range(3)])
                            if spacing_diff > 0.01:  # Only if difference is > 0.01mm
                                volume_node.SetSpacing(new_spacing)
                                corrections_applied = True
                        
                    except ImportError:
                        pass
                    except Exception as dicom_error:
                        pass
                        
            except Exception as analysis_error:
                pass
        
        # Fallback: Apply reasonable defaults if spacing looks wrong
        if not corrections_applied:
            # Check if current spacing looks unreasonable
            if (current_spacing[0] == 1.0 and current_spacing[1] == 1.0 and current_spacing[2] == 1.0):
                # Common CT spacing
                volume_node.SetSpacing((0.5, 0.5, 1.0))  # 0.5mm pixel, 1mm slice
                corrections_applied = True
        
        if corrections_applied:
            
            # Update display
            volume_node.Modified()
            slicer.app.processEvents()
            
            # Reset slice views to show corrected volume properly
            slicer.util.resetSliceViews()
            
        return corrections_applied
        
    except Exception as e:
        pass
        return False

def fix_volume_spacing_manually(spacing_x=0.5, spacing_y=0.5, spacing_z=1.0):
    """
    Console helper to manually fix spacing for the most recent volume.
    Usage: fix_volume_spacing_manually(0.5, 0.5, 1.0)  # 0.5mm pixel, 1mm slice
    """
    try:
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        if volume_nodes:
            latest_volume = volume_nodes[-1]
            old_spacing = latest_volume.GetSpacing()
            
            latest_volume.SetSpacing((spacing_x, spacing_y, spacing_z))
            latest_volume.Modified()
            slicer.app.processEvents()
            slicer.util.resetSliceViews()
            
            return True
        else:
            return False
    except Exception as e:
        pass
        return False

def reset_volume_to_identity_matrix():
    """
    Console helper to reset volume orientation matrix to identity.
    Usage: reset_volume_to_identity_matrix()
    """
    try:
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        if volume_nodes:
            latest_volume = volume_nodes[-1]
            
            # Create identity matrix
            import vtk
            matrix = vtk.vtkMatrix4x4()
            matrix.Identity()
            
            # Apply to volume
            latest_volume.SetIJKToRASMatrix(matrix)
            latest_volume.Modified()
            slicer.app.processEvents()
            slicer.util.resetSliceViews()
            
            return True
        else:
            return False
    except Exception as e:
        pass
        return False

def analyze_volume_properties():
    """
    Console helper to analyze current volume properties.
    Usage: analyze_volume_properties()
    """
    try:
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        if volume_nodes:
            latest_volume = volume_nodes[-1]
            
            # Spacing
            spacing = latest_volume.GetSpacing()
            
            # Dimensions
            image_data = latest_volume.GetImageData()
            if image_data:
                dims = image_data.GetDimensions()
                
                # Physical size
                physical_size = (dims[0]*spacing[0], dims[1]*spacing[1], dims[2]*spacing[2])
            
            # Origin
            origin = latest_volume.GetOrigin()
            
            # Orientation matrix
            matrix = vtk.vtkMatrix4x4()
            latest_volume.GetIJKToRASMatrix(matrix)
            for i in range(4):
                row = [matrix.GetElement(i, j) for j in range(4)]
            
            return True
        else:
            return False
    except Exception as e:
        pass
        return False

def load_dicom_like_reference():
    """
    Load DICOM using the same method that produces the reference structure.
    This replicates the exact import process that creates properly structured DICOM series.
    """
    import os
    try:
        
        # Read the source path - use user's home directory (consistent with other functions)
        user_home = os.path.expanduser("~")
        source_file_path = os.path.join(user_home, "source_slicer.txt")
        dicom_path = None
        
        try:
            with open(source_file_path, 'r') as f:
                dicom_path = f.read().strip()
        except FileNotFoundError:
            pass
            return False
        
        if not dicom_path or not os.path.exists(dicom_path):
            return False
        
        
        # Method 1: Use the exact same approach as the DICOM module
        # This matches how the reference import was likely created
        
        # Open DICOM module first
        slicer.util.selectModule("DICOM")
        slicer.app.processEvents()
        
        # Get DICOM browser widget
        dicom_browser = slicer.modules.dicom.widgetRepresentation().self().browserWidget
        
        # Clear existing database to avoid conflicts
        slicer.dicomDatabase.initializeDatabase()
        
        # Import the directory with the same settings as manual import
        dicom_browser.importDirectory(dicom_path, copy=True)
        
        # Process events and wait for completion
        slicer.app.processEvents()
        import time
        time.sleep(2)
        slicer.app.processEvents()
        
        # Get the imported data and load it
        dicomDatabase = slicer.dicomDatabase
        patients = dicomDatabase.patients()
        
        if patients:
            
            # Get the patient (should be the one we just imported)
            patient_id = patients[-1]  # Most recent
            patient_name = dicomDatabase.patientName(patient_id)
            
            # Get studies for this patient
            studies = dicomDatabase.studiesForPatient(patient_id)
            if studies:
                study_uid = studies[-1]  # Most recent study
                study_description = dicomDatabase.studyDescription(study_uid)
                
                # Get series for this study
                series_list = dicomDatabase.seriesForStudy(study_uid)
                if series_list:
                    # Find the best series (usually the largest one)
                    best_series = None
                    max_files = 0
                    
                    for series_uid in series_list:
                        series_files = dicomDatabase.filesForSeries(series_uid)
                        series_description = dicomDatabase.seriesDescription(series_uid)
                        
                        if len(series_files) > max_files:
                            max_files = len(series_files)
                            best_series = series_uid
                    
                    if best_series:
                        series_files = dicomDatabase.filesForSeries(best_series)
                        series_description = dicomDatabase.seriesDescription(best_series)
                        
                        # Load using the standard Slicer method
                        # This should create the same structure as the reference
                        volume_node = slicer.util.loadVolume(series_files[0])
                        
                        if volume_node:
                            # Set proper name matching reference style
                            if series_description:
                                volume_node.SetName(series_description)
                            
                            # Verify the loading
                            image_data = volume_node.GetImageData()
                            if image_data:
                                dims = image_data.GetDimensions()
                                spacing = volume_node.GetSpacing()
                                
                                # Store DICOM metadata
                                volume_node.SetAttribute("DICOM_PatientName", patient_name)
                                volume_node.SetAttribute("DICOM_SeriesDescription", series_description)
                                volume_node.SetAttribute("DICOM_SeriesUID", best_series)
                                
                                set_3d_view_background_black()
                                qt.QTimer.singleShot(1000, start_with_volume_crop)
                                return True
        
        return False
        
    except Exception as e:
        pass
        return False

def force_dicom_reimport():
    """
    Force a clean DICOM reimport using the reference method.
    Console helper: force_dicom_reimport()
    """
    try:
        # Clear existing volumes first
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        for node in volume_nodes:
            slicer.mrmlScene.RemoveNode(node)
        
        # Clear DICOM database
        slicer.dicomDatabase.initializeDatabase()
        
        # Load using reference method
        return load_dicom_like_reference()
        
    except Exception as e:
        pass
        return False

def test_restart_cropping_with_preservation():
    """
    Test function to restart cropping while preserving existing centerlines.
    Usage: test_restart_cropping_with_preservation()
    
    This function provides the same functionality as the "Restart Cropping" button
    in the centerline completion dialog, but can be called from the console.
    """
    try:
        # Check if we have any centerlines to preserve
        centerline_models = find_all_centerline_models()
        centerline_curves = find_all_centerline_curves()
        
        if not centerline_models and not centerline_curves:
            start_with_volume_crop()
            return
        
        
        # Store existing centerlines
        store_existing_centerlines()
        
        # Clear workflow data but preserve centerlines
        clear_workflow_for_cropping_restart()
        
        # Restart cropping workflow
        restart_cropping_preserving_centerlines()
        
        
        return True
        
    except Exception as e:
        pass
        pass
        start_with_volume_crop()
        return False


def show_restart_cropping_help():
    """
    Show help information about the restart cropping functionality.
    Usage: show_restart_cropping_help()
    """
    help_text = """
=== Restart Cropping with Centerline Preservation ===

This feature allows you to return to the volume cropping step while keeping 
your existing centerlines intact. This is useful when you need to:

• Adjust the crop region after seeing centerline results
• Re-crop the volume with different boundaries
• Fix cropping issues without losing centerline work

USAGE METHODS:

1. FROM CENTERLINE COMPLETION DIALOG:
   - Click the "🔄 Restart Cropping" button
   - Your centerlines will be automatically preserved

2. FROM CONSOLE:
   - test_restart_cropping_with_preservation()
   - This provides the same functionality as the dialog button

3. MANUAL STEPS (if needed):
   - store_existing_centerlines()
   - clear_workflow_for_cropping_restart()
   - restart_cropping_preserving_centerlines()

WHAT HAPPENS:
✅ Existing centerlines are preserved and remain visible
✅ Original volume is restored for re-cropping
✅ Crop ROI and segmentation data are cleared
✅ Workflow returns to cropping step
✅ You can adjust crop region and continue normally

WHAT'S PRESERVED:
• All centerline models and curves
• Centerline visibility settings
• Original volume data

WHAT'S CLEARED:
• Cropped volumes
• ROI nodes
• Segmentation nodes
• Endpoint markups

After restarting, simply crop your volume again and the workflow will continue
with both your existing centerlines and new cropped volume.
"""


def reset_crop_module_to_default():
    """
    Reset the Crop Volume module to its default/original state by forcing a module reload.
    This completely resets the UI to its original state, removing all custom modifications.
    
    Usage:
        reset_crop_module_to_default()
        
    Returns:
        bool: True if reset was successful, False otherwise
    """
    try:
        
        # Method 1: Force module reload by switching modules
        current_module = slicer.util.moduleSelector().selectedModule
        
        # Clear any stored custom widgets/buttons from the module
        cleanup_crop_module_custom_elements()
        
        # Switch to Crop Volume module for recropping (avoid Welcome module)
        slicer.util.selectModule("CropVolume")
        slicer.app.processEvents()
        
        # Hide ALL UI elements from the crop module
        hide_crop_volume_ui_elements()
        qt.QTimer.singleShot(500, hide_crop_volume_ui_elements)
        qt.QTimer.singleShot(1500, hide_crop_volume_ui_elements)
        
        # Method 2: Reset module widget if available
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if crop_widget and hasattr(crop_widget, 'self'):
            crop_module = crop_widget.self()
            
            # Try to call any reset methods if they exist
            if hasattr(crop_module, 'reset'):
                crop_module.reset()
            elif hasattr(crop_module, 'onReload'):
                crop_module.onReload()
            elif hasattr(crop_module, 'setup'):
                crop_module.setup()
        
        # Method 3: Restore all UI elements to visible state
        restore_all_crop_ui_elements()
        
        # Switch back to original module if it wasn't Crop Volume
        if current_module and current_module != "CropVolume":
            slicer.util.selectModule(current_module)
            slicer.app.processEvents()
        
        return True
        
    except Exception as e:
        pass
        return False


def cleanup_crop_module_custom_elements():
    """
    Clean up custom elements that were added to the Crop Volume module during workflow.
    This removes custom buttons, widgets, and other modifications.
    """
    try:
        # Clear any stored custom UI references
        if hasattr(slicer.modules, 'WorkflowCropApplyButton'):
            delattr(slicer.modules, 'WorkflowCropApplyButton')
        
        if hasattr(slicer.modules, 'WorkflowContinueButton'):
            delattr(slicer.modules, 'WorkflowContinueButton')
        
        if hasattr(slicer.modules, 'WorkflowContinueContainer'):
            delattr(slicer.modules, 'WorkflowContinueContainer')
        
        # Clear crop monitoring timers
        if hasattr(slicer.modules, 'CropMonitorTimer'):
            timer = slicer.modules.CropMonitorTimer
            if timer:
                timer.stop()
                delattr(slicer.modules, 'CropMonitorTimer')
        
        # Clear other crop-related stored data
        crop_attributes = ['CropCheckCount', 'WorkflowCroppedVolume']
        for attr in crop_attributes:
            if hasattr(slicer.modules, attr):
                delattr(slicer.modules, attr)
        
        return True
        
    except Exception as e:
        pass
        return False


def restore_all_crop_ui_elements():
    """
    Restore all UI elements in the Crop Volume module to their original visible state.
    This is more comprehensive than the existing restore_crop_ui function.
    """
    try:
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if not crop_widget:
            return False
        
        # Make all widgets visible
        all_widgets = crop_widget.findChildren(qt.QWidget)
        restored_count = 0
        
        for widget in all_widgets:
            if hasattr(widget, 'setVisible'):
                widget.setVisible(True)
                restored_count += 1
                
            # Reset any custom styling
            if hasattr(widget, 'setStyleSheet'):
                widget.setStyleSheet("")
        
        # Restore collapsible buttons to their default state
        collapsible_buttons = crop_widget.findChildren("ctkCollapsibleButton")
        for button in collapsible_buttons:
            button.setVisible(True)
            # Reset to collapsed state (default for most modules)
            if hasattr(button, 'setCollapsed'):
                button.setCollapsed(False)
        
        # Remove any custom layouts or buttons that were added
        remove_custom_crop_buttons()
        
        return True
        
    except Exception as e:
        return False


def remove_custom_crop_buttons():
    """
    Remove custom buttons that were added to the Crop Volume module during workflow.
    """
    try:
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if not crop_widget:
            return False
        
        buttons_removed = 0
        
        # Find and remove custom buttons by object name or text
        custom_button_names = [
            "WorkflowCropApplyButton",
            "WorkflowContinueButton",
            "ContinueWorkflowButton",
            "FinishCroppingButton",
            "ScissorsToolButton"
        ]
        
        for button_name in custom_button_names:
            custom_buttons = crop_widget.findChildren(qt.QPushButton, button_name)
            for button in custom_buttons:
                button.setParent(None)
                button.deleteLater()
                buttons_removed += 1
        
        # Also remove buttons by text content
        all_buttons = crop_widget.findChildren(qt.QPushButton)
        for button in all_buttons:
            button_text = button.text
            if any(keyword in button_text for keyword in [
                "Continue Workflow", 
                "Finish Cropping", 
                "Scissors Tool",
                "Large Apply"  # Our custom large green apply button
            ]):
                button.setParent(None)
                button.deleteLater()
                buttons_removed += 1
        
        # Remove custom layouts
        custom_layouts = crop_widget.findChildren(qt.QHBoxLayout, "WorkflowButtonLayout")
        for layout in custom_layouts:
            # Remove all widgets in the layout first
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
                    item.widget().deleteLater()
            # Remove the layout itself
            layout.setParent(None)
            layout.deleteLater()
            buttons_removed += 1
        
        
        return True
        
    except Exception as e:
        return False


def reset_all_workflow_modules():
    """
    Reset all modules that get modified during the workflow to their default states.
    This includes Crop Volume, Extract Centerline, Segment Editor, and CPR modules.
    
    Usage:
        reset_all_workflow_modules()
        
    Returns:
        dict: Results of reset operations for each module
    """
    try:
        
        
        results = {
            'crop_volume': False,
            'extract_centerline': False,
            'segment_editor': False,
            'cpr': False
        }
        
        # Reset Crop Volume module
        results['crop_volume'] = reset_crop_module_to_default()
        
        # Reset Extract Centerline module
        results['extract_centerline'] = reset_extract_centerline_module()
        
        # Reset Segment Editor module (if it was used)
        results['segment_editor'] = reset_segment_editor_module()
        
        # Reset CPR module
        results['cpr'] = reset_cpr_module()
        
        # Clean up any global workflow state
        cleanup_global_workflow_state()
        
        successful_resets = sum(results.values())
        total_modules = len(results)
        



            
        return results
        
    except Exception as e:
        return {'error': str(e)}


def reset_extract_centerline_module():
    """Reset the Extract Centerline module to default state."""
    try:
        # Switch modules to trigger reload
        slicer.util.selectModule("Welcome")
        slicer.app.processEvents()
        
        # Clean up Extract Centerline specific elements
        cleanup_extract_centerline_custom_elements()
        
        slicer.util.selectModule("ExtractCenterline")
        slicer.app.processEvents()
        
        # Restore UI elements
        restore_extract_centerline_ui()
        
        return True
        
    except Exception as e:
        return False


def reset_segment_editor_module():
    """Reset the Segment Editor module to default state."""
    try:
        # Switch modules to trigger reload
        slicer.util.selectModule("Welcome")
        slicer.app.processEvents()
        
        # Clean up Segment Editor specific elements
        cleanup_segment_editor_custom_elements()
        
        # Note: Don't switch to Segment Editor unless user specifically wants to use it
        return True
        
    except Exception as e:
        pass
        return False


def reset_cpr_module():
    """Reset the Curved Planar Reformat module to default state."""
    try:
        # Clean up CPR monitoring and custom elements
        stop_cpr_monitoring()
        
        # Switch modules to trigger reload
        current_module = slicer.util.moduleSelector().selectedModule
        slicer.util.selectModule("Welcome")
        slicer.app.processEvents()
        
        # Clean up CPR specific elements
        cleanup_cpr_custom_elements()
        
        # Switch back to original module
        if current_module and current_module != "CurvedPlanarReformat":
            slicer.util.selectModule(current_module)
            slicer.app.processEvents()
        return True
        
    except Exception as e:
        return False


def cleanup_extract_centerline_custom_elements():
    """Clean up custom elements from Extract Centerline module."""
    try:
        centerline_attributes = [
            'CenterlineMonitorTimer',
            'CenterlineDialogShown', 
            'BaselineCenterlineModelCount',
            'BaselineCenterlineCurveCount',
            'CenterlineCheckCount',
            'TargetCenterlineModels',
            'TargetCenterlineCurves',
            'CenterlineMonitoringStartTime'
        ]
        
        for attr in centerline_attributes:
            if hasattr(slicer.modules, attr):
                delattr(slicer.modules, attr)
        
        # Stop any active monitoring
        stop_all_centerline_monitoring()
        
    except Exception as e:
        pass


def cleanup_segment_editor_custom_elements():
    """Clean up custom elements from Segment Editor module."""
    try:
        # Clean up scissors tool related elements
        cleanup_scissors_tool_ui()
        
        segment_attributes = [
            'WorkflowScissorsButton',
            'WorkflowScissorsWidget',
            'SegmentEditorActive'
        ]
        
        for attr in segment_attributes:
            if hasattr(slicer.modules, attr):
                delattr(slicer.modules, attr)
                
    except Exception as e:
        pass



def cleanup_cpr_custom_elements():
    """Clean up custom elements from CPR module."""
    try:
        cpr_attributes = [
            'CPRMonitorTimer',
            'CPRCheckCount',
            'LastUsedCenterlineModel',
            'LastUsedCenterlineCurve'
        ]
        
        for attr in cpr_attributes:
            if hasattr(slicer.modules, attr):
                delattr(slicer.modules, attr)
                
    except Exception as e:
        pass


def cleanup_global_workflow_state():
    """Clean up global workflow state and monitoring timers."""
    try:
        # Stop all monitoring timers
        stop_all_centerline_monitoring()
        stop_cpr_monitoring()
        stop_volume_addition_monitoring()
        
        # Clean up global workflow attributes
        global_attributes = [
            'WorkflowOriginalVolume',
            'PreservedCenterlineModels',
            'PreservedCenterlineCurves',
            'PreservedModelVisibility',
            'PreservedCurveVisibility',
            'WorkflowUsingMarkup',
            'VolumeMonitorTimer',
            'VolumeCheckCount'
        ]
        
        for attr in global_attributes:
            if hasattr(slicer.modules, attr):
                delattr(slicer.modules, attr)
        
    except Exception as e:
        pass


def restart_cropping_simple():
    """
    Simple restart cropping function that's less likely to cause freezing.
    This is a fallback when the full restart with preservation fails.
    
    Usage:
        restart_cropping_simple()  # Simple restart without preservation
    """
    try:
        
        # Stop all monitoring to prevent conflicts
        stop_all_centerline_monitoring()
        slicer.app.processEvents()
        
        # Clean up custom crop elements only
        cleanup_crop_module_custom_elements()
        slicer.app.processEvents()
        
        # Switch to welcome to reset state
        slicer.util.selectModule("Welcome")
        slicer.app.processEvents()
        
        # Wait a moment then start cropping
        qt.QTimer.singleShot(1000, start_with_volume_crop)
        
        return True
        
    except Exception as e:
        return False


def manual_restart_cropping_help():
    """
    Show manual steps to restart cropping if automatic restart fails.
    """
    help_text = """
MANUAL RESTART CROPPING STEPS

If automatic restart fails, follow these steps:

1. RESET MODULES:
   >>> test.reset_crop_module_to_default()
   
2. START FRESH CROPPING:
   >>> start_with_volume_crop()

3. IF STILL HAVING ISSUES:
   >>> test.reset_all_workflow_modules()
   >>> start_with_volume_crop()

4. NUCLEAR OPTION (if everything fails):
   - Close Slicer completely
   - Restart Slicer
   - Load your DICOM data
   - Run: start_with_volume_crop()

PRESERVE CENTERLINES MANUALLY:
If you need to preserve centerlines:
   >>> centerlines = find_all_centerline_models() + find_all_centerline_curves()
   >>> # Write down their names, then recreate after restart

QUICK COMMANDS:
   >>> restart_cropping_simple()          # Simple restart
   >>> test.test_crop_module_reset()      # Test reset
   >>> manual_restart_cropping_help()     # Show this help again
"""


def test_crop_module_reset():
    """
    Test function to quickly reset the Crop Volume module.
    This is the main function users should call to fix crop module issues.
    
    Usage:
        test_crop_module_reset()  # Reset just the crop module
        
    Or from test functions:
        import workflow_test_functions as test
        test.reset_crop_module_to_default()
    """
    try:

        success = reset_crop_module_to_default()     
        return success
        
    except Exception as e:
        return False


def test_full_workflow_reset():
    """
    Test function to reset all workflow modules at once.
    Use this when you want to completely reset the entire workflow system.
    
    Usage:
        test_full_workflow_reset()
        
    Or from test functions:
        import workflow_test_functions as test
        test.reset_all_workflow_modules()
    """
    try:
        
        results = reset_all_workflow_modules()
      
        return results
        
    except Exception as e:
        return {'error': str(e)}


def cropVolumeWithNamedROI(roiName="CropROI", outputName="CroppedVolume"):
    """
    Crops the first scalar volume in the scene using the ROI with the given name.
    This is a clean alternative to using the crop module GUI when it becomes distorted.
    
    Args:
        roiName (str): Name of the ROI node to use for cropping
        outputName (str): Name for the output cropped volume
        
    Returns:
        vtkMRMLScalarVolumeNode: The cropped volume node, or None if failed
    """
    try:
        # Get the input volume and ROI by name
        inputVolume = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")

        roiCollection = slicer.mrmlScene.GetNodesByName(roiName)
        roi = roiCollection.GetItemAsObject(0) if roiCollection.GetNumberOfItems() > 0 else None

        if not inputVolume:
            return None
        if not roi:
            return None

        # Set up CropVolume parameters
        cropVolumeLogic = slicer.modules.cropvolume.logic()
        cropVolumeParameterNode = slicer.vtkMRMLCropVolumeParametersNode()
        slicer.mrmlScene.AddNode(cropVolumeParameterNode)

        cropVolumeParameterNode.SetInputVolumeNodeID(inputVolume.GetID())
        cropVolumeParameterNode.SetROINodeID(roi.GetID())
        cropVolumeParameterNode.SetVoxelBased(True)

        # Create the output volume node
        outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", outputName)
        cropVolumeParameterNode.SetOutputVolumeNodeID(outputVolume.GetID())

        # Perform cropping
        cropVolumeLogic.Apply(cropVolumeParameterNode)
        
        # Set the cropped volume as the active background in slice views
        slicer.util.setSliceViewerLayers(background=outputVolume)
        
        # Store reference to cropped volume for workflow
        slicer.modules.WorkflowCroppedVolume = outputVolume
        
        return outputVolume
        
    except Exception as e:
        return None


def create_initial_custom_crop_interface():
    """
    Create the initial custom crop interface for the first crop operation.
    Uses dark color scheme and hides scissors tools until after cropping.
    """
    try:
        # Clean up any existing custom crop interface
        if hasattr(slicer.modules, 'CustomCropWidget'):
            existing_widget = slicer.modules.CustomCropWidget
            if existing_widget:
                existing_widget.close()
                existing_widget.deleteLater()
        
        # First, ensure ROI exists and is visible
        roi_node = ensure_crop_roi_exists()

        
        # Switch to the same three-up view used in the workflow
        setup_crop_display_layout()
        
        # Create the custom crop widget as a fixed left-side module with dark theme
        crop_widget = qt.QWidget()
        crop_widget.setWindowTitle("Crop Tools")
        
        # Set up as a dockable widget on the left side with dark theme
        crop_widget.setWindowFlags(qt.Qt.Widget)
        crop_widget.setFixedWidth(280)
        crop_widget.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 2px solid #555555;
                border-radius: 8px;
                color: #ffffff;
            }
        """)
        
        # Position on the left side of the screen
        main_window = slicer.util.mainWindow()
        if main_window:
            screen_geometry = qt.QApplication.desktop().availableGeometry()
            crop_widget.setGeometry(10, 100, 280, 300)
            crop_widget.setWindowFlags(qt.Qt.WindowStaysOnTopHint | qt.Qt.FramelessWindowHint)
        
        # Set up layout
        layout = qt.QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Header with title and close button - dark theme
        header_layout = qt.QHBoxLayout()
        
        # Title
        title_label = qt.QLabel("Crop Tools")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)
        
        # Close button - dark theme
        close_button = qt.QPushButton("×")
        close_button.setStyleSheet("""
            QPushButton { 
                background-color: #e74c3c; 
                color: white; 
                border: none; 
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
            }
            QPushButton:hover { 
                background-color: #c0392b; 
            }
        """)
        close_button.connect('clicked()', lambda: cleanup_custom_crop_interface())
        header_layout.addWidget(close_button)
        
        # Add header to main layout
        header_widget = qt.QWidget()
        header_widget.setLayout(header_layout)
        header_widget.setStyleSheet("padding: 10px; background-color: #3a3a3a; border-radius: 6px; margin-bottom: 10px;")
        layout.addWidget(header_widget)

        # Crop button - dark theme
        crop_button = qt.QPushButton("CROP VOLUME")
        crop_button.setStyleSheet("""
            QPushButton { 
                background-color: #3498db; 
                color: white; 
                border: none; 
                padding: 12px; 
                font-weight: bold;
                border-radius: 6px;
                font-size: 13px;
                min-height: 45px;
                margin: 5px;
            }
            QPushButton:hover { 
                background-color: #2980b9; 
            }
            QPushButton:pressed { 
                background-color: #21618c; 
            }
        """)
        
        # Connect crop button
        crop_button.connect('clicked()', lambda: execute_initial_custom_crop())
        layout.addWidget(crop_button)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Set layout and show
        crop_widget.setLayout(layout)
        
        # Show the fixed left-side module
        crop_widget.show()
        crop_widget.raise_()
        crop_widget.activateWindow()
        
        # Store references
        slicer.modules.CustomCropWidget = crop_widget
        slicer.modules.CustomCropButton = crop_button
        
        # Check if crop has already been completed and disable button if so
        if hasattr(slicer.modules, 'WorkflowCroppedVolume') and slicer.modules.WorkflowCroppedVolume:
            crop_button.setEnabled(False)
            crop_button.setText("CROP APPLIED ✓")
            crop_button.setStyleSheet("""
                QPushButton { 
                    background-color: #808080; 
                    color: white; 
                    border: none; 
                    padding: 12px; 
                    font-weight: bold;
                    border-radius: 6px;
                    font-size: 13px;
                    min-height: 45px;
                    margin: 5px;
                }
            """)
        
        return crop_widget
        
    except Exception as e:
        pass
        return None


def execute_initial_custom_crop():
    """
    Execute the initial custom crop operation and add scissors tools after cropping.
    """
    try:
        
        # Check if ROI exists, create if needed
        ensure_crop_roi_exists()
        
        # Perform the crop with timestamp to avoid naming conflicts
        import time
        timestamp = int(time.time())
        cropped_volume = cropVolumeWithNamedROI("CropROI", f"CroppedVolume_{timestamp}")
        
        if cropped_volume:
            # Store the cropped volume reference
            slicer.modules.WorkflowCroppedVolume = cropped_volume
            
            # Disable the crop button now that it has been used
            if hasattr(slicer.modules, 'CustomCropButton'):
                crop_button = slicer.modules.CustomCropButton
                if crop_button:
                    crop_button.setEnabled(False)
                    crop_button.setText("CROP APPLIED ✓")
                    crop_button.setStyleSheet("""
                        QPushButton { 
                            background-color: #808080; 
                            color: white; 
                            border: none; 
                            padding: 12px; 
                            font-weight: bold;
                            border-radius: 6px;
                            font-size: 13px;
                            min-height: 45px;
                            margin: 5px;
                        }
                    """)
            
            # Delete the ROI after cropping is complete
            roiCollection = slicer.mrmlScene.GetNodesByName("CropROI")
            if roiCollection.GetNumberOfItems() > 0:
                roi_node = roiCollection.GetItemAsObject(0)
                slicer.mrmlScene.RemoveNode(roi_node)
            
            # Reset slice views to show the cropped volume properly
            slicer.util.resetSliceViews()
            
            # Switch to 3D view to show results
            set_3d_only_view()
            
            # Set dark background
            set_3d_view_background_black()
            
            
            # Add scissors tools and continue button to the interface after cropping
            add_scissors_tools_to_initial_interface()
            
            # Continue with the normal workflow - threshold segmentation
            qt.QTimer.singleShot(500, lambda: continue_workflow_after_custom_crop())
            
    except Exception as e:
        pass


def add_scissors_tools_to_initial_interface():
    """
    Add scissors tools and continue button to the initial crop interface after cropping is complete.
    """
    try:
        if not hasattr(slicer.modules, 'CustomCropWidget'):
            return
            
        crop_widget = slicer.modules.CustomCropWidget
        if not crop_widget:
            return
            
        # Get the current layout
        layout = crop_widget.layout()
        if not layout:
            return
        
        # Remove the stretch at the end to add new buttons
        stretch_item = layout.takeAt(layout.count() - 1)
        
        # Add spacing
        layout.addSpacing(10)
        
        # Add scissors toggle button - dark theme
        scissors_button = qt.QPushButton("Toggle Scissors Tool")
        scissors_button.setCheckable(True)
        scissors_button.setChecked(False)
        scissors_button.setStyleSheet("""
            QPushButton { 
                background-color: #e74c3c; 
                color: white; 
                border: none; 
                padding: 10px; 
                font-weight: bold;
                border-radius: 6px;
                font-size: 12px;
                min-height: 40px;
                margin: 5px;
            }
            QPushButton:hover { 
                background-color: #c0392b; 
            }
            QPushButton:pressed { 
                background-color: #a93226; 
            }
            QPushButton:checked { 
                background-color: #27ae60; 
                border: 2px solid #1e7e34;
            }
            QPushButton:checked:hover { 
                background-color: #218838; 
            }
        """)
        
        # Connect scissors button with proper toggle signal
        scissors_button.connect('toggled(bool)', lambda checked: toggle_scissors_tool_programmatic(checked))
        layout.addWidget(scissors_button)
        
        # Store button reference for external access (override previous if exists)
        slicer.modules.CustomScissorsButton = scissors_button
        
        # Add spacing
        layout.addSpacing(15)
        
        # Add continue workflow button - dark theme
        continue_button = qt.QPushButton("FINISH & CONTINUE")
        continue_button.setStyleSheet("""
            QPushButton { 
                background-color: #27ae60; 
                color: white; 
                border: none; 
                padding: 12px; 
                font-weight: bold;
                border-radius: 6px;
                font-size: 13px;
                min-height: 45px;
                margin: 5px;
            }
            QPushButton:hover { 
                background-color: #229954; 
            }
            QPushButton:pressed { 
                background-color: #1e8449; 
            }
        """)
        
        # Connect continue button
        continue_button.connect('clicked()', lambda: finish_custom_crop_workflow())
        layout.addWidget(continue_button)
        
        # Re-add stretch to push everything to the top
        layout.addStretch()
        
        # Store references
        slicer.modules.CustomScissorsButton = scissors_button
        slicer.modules.CustomContinueButton = continue_button
        
        # Resize the widget to accommodate new buttons
        crop_widget.setFixedHeight(400)
        
    except Exception as e:
        pass


def create_custom_crop_interface():
    """
    Create a clean custom interface for cropping when the crop module GUI becomes distorted.
    This creates a fixed left-side module with crop button and scissors controls.
    Automatically creates and shows the ROI for cropping.
    """
    try:
        # Clean up any existing custom crop interface
        if hasattr(slicer.modules, 'CustomCropWidget'):
            existing_widget = slicer.modules.CustomCropWidget
            if existing_widget:
                existing_widget.close()
                existing_widget.deleteLater()
        
        # First, ensure ROI exists and is visible
        roi_node = ensure_crop_roi_exists()
        
        # Switch to the same three-up view used in the original workflow
        setup_crop_display_layout()
        
        # Create the custom crop widget as a fixed left-side module
        crop_widget = qt.QWidget()
        crop_widget.setWindowTitle("Crop Tools")
        
        # Set up as a dockable widget on the left side
        crop_widget.setWindowFlags(qt.Qt.Widget)
        crop_widget.setFixedWidth(280)
        crop_widget.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 2px solid #555555;
                border-radius: 8px;
                color: #ffffff;
            }
        """)
        
        # Position on the left side of the screen
        main_window = slicer.util.mainWindow()
        if main_window:
            screen_geometry = qt.QApplication.desktop().availableGeometry()
            crop_widget.setGeometry(10, 100, 280, 400)
            crop_widget.setWindowFlags(qt.Qt.WindowStaysOnTopHint | qt.Qt.FramelessWindowHint)
        
        # Set up layout
        layout = qt.QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Header with title and close button
        header_layout = qt.QHBoxLayout()
        
        # Title
        title_label = qt.QLabel("Crop Tools")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)
        
        # Close button
        close_button = qt.QPushButton("×")
        close_button.setStyleSheet("""
            QPushButton { 
                background-color: #e74c3c; 
                color: white; 
                border: none; 
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
            }
            QPushButton:hover { 
                background-color: #c0392b; 
            }
        """)
        close_button.connect('clicked()', lambda: cleanup_custom_crop_interface())
        header_layout.addWidget(close_button)
        
        # Add header to main layout
        header_widget = qt.QWidget()
        header_widget.setLayout(header_layout)
        header_widget.setStyleSheet("padding: 10px; background-color: #ecf0f1; border-radius: 6px; margin-bottom: 10px;")
        layout.addWidget(header_widget)
        

        
        # Crop button
        crop_button = qt.QPushButton("CROP VOLUME")
        crop_button.setStyleSheet("""
            QPushButton { 
                background-color: #3498db; 
                color: white; 
                border: none; 
                padding: 12px; 
                font-weight: bold;
                border-radius: 6px;
                font-size: 13px;
                min-height: 45px;
                margin: 5px;
            }
            QPushButton:hover { 
                background-color: #2980b9; 
            }
            QPushButton:pressed { 
                background-color: #21618c; 
            }
        """)
        
        # Connect crop button
        crop_button.connect('clicked()', lambda: execute_custom_crop())
        layout.addWidget(crop_button)
        
        # Add spacing
        layout.addSpacing(10)
        
        # Scissors toggle button
        scissors_button = qt.QPushButton("Toggle Scissors Tool")
        scissors_button.setCheckable(True)
        scissors_button.setChecked(False)
        scissors_button.setStyleSheet("""
            QPushButton { 
                background-color: #e74c3c; 
                color: white; 
                border: none; 
                padding: 10px; 
                font-weight: bold;
                border-radius: 6px;
                font-size: 12px;
                min-height: 40px;
                margin: 5px;
            }
            QPushButton:hover { 
                background-color: #c0392b; 
            }
            QPushButton:pressed { 
                background-color: #a93226; 
            }
            QPushButton:checked { 
                background-color: #27ae60; 
                border: 2px solid #1e7e34;
            }
            QPushButton:checked:hover { 
                background-color: #218838; 
            }
        """)
        
        # Connect scissors button with proper toggle signal
        scissors_button.connect('toggled(bool)', lambda checked: toggle_scissors_tool_programmatic(checked))
        layout.addWidget(scissors_button)
        
        # Store button reference for external access
        slicer.modules.CustomScissorsButton = scissors_button
        
        # Add spacing
        layout.addSpacing(15)
        
        # Continue workflow button
        continue_button = qt.QPushButton("FINISH & CONTINUE")
        continue_button.setStyleSheet("""
            QPushButton { 
                background-color: #27ae60; 
                color: white; 
                border: none; 
                padding: 12px; 
                font-weight: bold;
                border-radius: 6px;
                font-size: 13px;
                min-height: 45px;
                margin: 5px;
            }
            QPushButton:hover { 
                background-color: #229954; 
            }
            QPushButton:pressed { 
                background-color: #1e8449; 
            }
        """)
        
        # Connect continue button
        continue_button.connect('clicked()', lambda: finish_custom_crop_workflow())
        layout.addWidget(continue_button)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Set layout and show
        crop_widget.setLayout(layout)
        
        # Show the fixed left-side module
        crop_widget.show()
        crop_widget.raise_()
        crop_widget.activateWindow()
        
        # Store references
        slicer.modules.CustomCropWidget = crop_widget
        slicer.modules.CustomCropButton = crop_button
        slicer.modules.CustomScissorsButton = scissors_button
        slicer.modules.CustomContinueButton = continue_button
        
        # Check if crop has already been completed and disable button if so
        if hasattr(slicer.modules, 'WorkflowCroppedVolume') and slicer.modules.WorkflowCroppedVolume:
            crop_button.setEnabled(False)
            crop_button.setText("CROP APPLIED ✓")
            crop_button.setStyleSheet("""
                QPushButton { 
                    background-color: #808080; 
                    color: white; 
                    border: none; 
                    padding: 12px; 
                    font-weight: bold;
                    border-radius: 6px;
                    font-size: 13px;
                    min-height: 45px;
                    margin: 5px;
                }
            """)
        
        
        return crop_widget
        
    except Exception as e:
        pass
        return None


def execute_custom_crop():
    """
    Execute the custom crop operation using the ROI in the scene.
    If no ROI exists, create one automatically.
    Continues with the normal workflow after cropping.
    """
    try:
        
        # Check if ROI exists, create if needed
        ensure_crop_roi_exists()
        
        # Perform the crop with timestamp to avoid naming conflicts
        import time
        timestamp = int(time.time())
        cropped_volume = cropVolumeWithNamedROI("CropROI", f"CroppedVolume_{timestamp}")
        
        if cropped_volume:
            # Store the cropped volume reference
            slicer.modules.WorkflowCroppedVolume = cropped_volume
            
            # Disable the crop button now that it has been used
            if hasattr(slicer.modules, 'CustomCropButton'):
                crop_button = slicer.modules.CustomCropButton
                if crop_button:
                    crop_button.setEnabled(False)
                    crop_button.setText("CROP APPLIED ✓")
                    crop_button.setStyleSheet("""
                        QPushButton { 
                            background-color: #808080; 
                            color: white; 
                            border: none; 
                            padding: 12px; 
                            font-weight: bold;
                            border-radius: 6px;
                            font-size: 13px;
                            min-height: 45px;
                            margin: 5px;
                        }
                    """)
            
            # Delete the ROI after cropping is complete
            roiCollection = slicer.mrmlScene.GetNodesByName("CropROI")
            if roiCollection.GetNumberOfItems() > 0:
                roi_node = roiCollection.GetItemAsObject(0)
                slicer.mrmlScene.RemoveNode(roi_node)
            
            # Reset slice views to show the cropped volume properly
            slicer.util.resetSliceViews()
            
            # Switch to 3D view to show results
            set_3d_only_view()
            
            # Set dark background
            set_3d_view_background_black()

            # Continue with the normal workflow - threshold segmentation immediately
            qt.QTimer.singleShot(500, lambda: continue_workflow_after_custom_crop())
        
            
    except Exception as e:
        print(f"Error in execute_custom_crop: {e}")


def continue_workflow_after_custom_crop():
    """
    Continue the normal workflow after custom cropping is completed.
    This ensures the same behavior as the original workflow.
    """
    try:

        volume_node = find_working_volume()
        if not volume_node:
            return

        ask_user_for_markup_import()
            
    except Exception as e:
        print(f"Error in continue_workflow_after_custom_crop: {e}")

def update_crop_interface_for_segmentation_phase():
    """
    Update the custom crop interface for the segmentation phase.
    Disable the crop button and highlight the scissors and continue tools.
    """
    try:
        if not hasattr(slicer.modules, 'CustomCropWidget'):
            return
            
        crop_widget = slicer.modules.CustomCropWidget
        if not crop_widget:
            return
            
        # Update the crop button to show it's completed
        if hasattr(slicer.modules, 'CustomCropButton'):
            crop_button = slicer.modules.CustomCropButton
            if crop_button:
                crop_button.setText("✓ VOLUME CROPPED")
                crop_button.setEnabled(False)
                crop_button.setStyleSheet("""
                    QPushButton { 
                        background-color: #95a5a6; 
                        color: white; 
                        border: none; 
                        padding: 12px; 
                        font-weight: bold;
                        border-radius: 6px;
                        font-size: 13px;
                        min-height: 45px;
                        margin: 5px;
                    }
                """)
        
        # Highlight the scissors button to show it's the next step
        if hasattr(slicer.modules, 'CustomScissorsButton'):
            scissors_button = slicer.modules.CustomScissorsButton
            if scissors_button:
                scissors_button.setStyleSheet("""
                    QPushButton { 
                        background-color: #e74c3c; 
                        color: white; 
                        border: 3px solid #f39c12;
                        padding: 10px; 
                        font-weight: bold;
                        border-radius: 6px;
                        font-size: 12px;
                        min-height: 40px;
                        margin: 5px;
                    }
                    QPushButton:hover { 
                        background-color: #c0392b; 
                        border: 3px solid #e67e22;
                    }
                    QPushButton:pressed { 
                        background-color: #a93226; 
                    }
                """)
        
        # Highlight the continue button as well
        if hasattr(slicer.modules, 'CustomContinueButton'):
            continue_button = slicer.modules.CustomContinueButton
            if continue_button:
                continue_button.setStyleSheet("""
                    QPushButton { 
                        background-color: #27ae60; 
                        color: white; 
                        border: 3px solid #f39c12;
                        padding: 12px; 
                        font-weight: bold;
                        border-radius: 6px;
                        font-size: 13px;
                        min-height: 45px;
                        margin: 5px;
                    }
                    QPushButton:hover { 
                        background-color: #229954; 
                        border: 3px solid #e67e22;
                    }
                    QPushButton:pressed { 
                        background-color: #1e8449; 
                    }
                """)
        
        # Ensure the widget is visible and on top
        crop_widget.show()
        crop_widget.raise_()
        
        
    except Exception as e:
        print(f"Error in update_crop_interface_for_segmentation_phase: {e}")


def ensure_crop_roi_exists():
    """
    Ensure a CropROI exists in the scene. If not, create one automatically.
    """
    try:
        # Check if CropROI already exists
        roiCollection = slicer.mrmlScene.GetNodesByName("CropROI")
        if roiCollection.GetNumberOfItems() > 0:
            existing_roi = roiCollection.GetItemAsObject(0)
            # Make sure existing ROI is visible and interactive
            displayNode = existing_roi.GetDisplayNode()
            if displayNode:
                displayNode.SetVisibility(True)
                displayNode.SetHandlesInteractive(True)
                displayNode.SetSelectedColor(1.0, 1.0, 0.0)  # Yellow when selected
                displayNode.SetColor(0.0, 1.0, 1.0)  # Cyan when not selected
                displayNode.SetOpacity(0.8)
                displayNode.SetFillOpacity(0.2)
                displayNode.SetOutlineVisibility(True)
                displayNode.SetFillVisibility(True)
            
            return existing_roi
        
        inputVolume = find_working_volume()
        if not inputVolume:
            return None
        
        roiNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode", "CropROI")
        roiNode.CreateDefaultDisplayNodes()
        
        bounds = [0.0] * 6
        inputVolume.GetBounds(bounds)

        center = [(bounds[1] + bounds[0]) / 2.0, 
                  (bounds[3] + bounds[2]) / 2.0, 
                  (bounds[5] + bounds[4]) / 2.0]
        
        size = [bounds[1] - bounds[0], 
                bounds[3] - bounds[2], 
                bounds[5] - bounds[4]]
        
        size = [s * 0.8 for s in size]
        
        roiNode.SetXYZ(center)
        roiNode.SetRadiusXYZ(size[0]/2, size[1]/2, size[2]/2)
        
        displayNode = roiNode.GetDisplayNode()
        if displayNode:
            displayNode.SetVisibility(True)
            displayNode.SetHandlesInteractive(True)
            displayNode.SetSelectedColor(1.0, 1.0, 0.0)  # Yellow when selected
            displayNode.SetColor(0.0, 1.0, 1.0)  # Cyan when not selected  
            displayNode.SetOpacity(0.8)  # Semi-transparent
            displayNode.SetFillOpacity(0.2)  # Light fill
            displayNode.SetOutlineVisibility(True)
            displayNode.SetFillVisibility(True)
        

        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetActivePlaceNodeID(roiNode.GetID())
        return roiNode
        
    except Exception as e:
        print(f"Error in ensure_crop_roi_exists: {e}")
        return None


def setup_crop_display_layout():
    """
    Set up the display layout for cropping - uses the same three-up view as the original workflow.
    This ensures consistent behavior between first and subsequent croppings.
    """
    try:
        success = set_three_up_view()
        if success:
            vol = find_working_volume()
            if vol:
                set_volume_visible_in_slice_views(vol)
            
        else:
            lm = slicer.app.layoutManager()
            if lm:
                layout_node = lm.layoutLogic().GetLayoutNode()
                layout_node.SetViewArrangement(slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalView)
        return success
        
    except Exception as e:
        print(f"Error in setup_crop_display_layout: {e}")
        return False

def toggle_scissors_tool(activated=None):
    """
    Toggle the scissors tool on/off with proper state tracking
    Args:
        activated (bool, optional): True to activate, False to deactivate, None to toggle
    """
    try:
        if not hasattr(slicer.modules, 'ScissorsToolActive'):
            slicer.modules.ScissorsToolActive = False
        
        current_state = slicer.modules.ScissorsToolActive
        if activated is not None:
            target_state = activated
        else:
            target_state = not current_state
        
        if target_state != current_state:
            if target_state:
                success = select_scissors_tool()
                
                if success:
                    slicer.modules.ScissorsToolActive = True
                    
                    if hasattr(slicer.modules, 'CustomScissorsButton'):
                        button = slicer.modules.CustomScissorsButton
                        if hasattr(button, 'setChecked'):
                            button.setChecked(True)
                        button.setText("Scissors ON")

                    if hasattr(slicer.modules, 'WorkflowScissorsButton'):
                        button = slicer.modules.WorkflowScissorsButton
                        if hasattr(button, 'setChecked'):
                            button.setChecked(True)
            else:
                slicer.modules.ScissorsToolActive = False

                if hasattr(slicer.modules, 'WorkflowSegmentEditorWidget'):
                    segmentEditorWidget = slicer.modules.WorkflowSegmentEditorWidget
                    segmentEditorWidget.setActiveEffectByName("")  # Clear active effect

                interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
                if interactionNode:
                    interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)

                if hasattr(slicer.modules, 'CustomScissorsButton'):
                    button = slicer.modules.CustomScissorsButton
                    if hasattr(button, 'setChecked'):
                        button.setChecked(False)
                    button.setText("Toggle Scissors Tool")

                if hasattr(slicer.modules, 'WorkflowScissorsButton'):
                    button = slicer.modules.WorkflowScissorsButton
                    if hasattr(button, 'setChecked'):
                        button.setChecked(False)
    except Exception as e:
        print(f"Error in toggle_scissors_tool: {e}")

def finish_custom_crop_workflow():
    """
    Finish the custom crop workflow and continue to next steps.
    This is called by the "FINISH SEGMENTATION - CONTINUE" button.
    """
    try:
        cleanup_custom_crop_interface()
        on_continue_from_scissors()
        
    except Exception as e:
        print(f"Error in finish_custom_crop_workflow: {e}")


def cleanup_custom_crop_interface():
    """
    Clean up the custom crop interface widgets
    """
    try:

        if hasattr(slicer.modules, 'CustomCropWidget'):
            widget = slicer.modules.CustomCropWidget
            if widget:
                widget.close()
                widget.deleteLater()
            delattr(slicer.modules, 'CustomCropWidget')

        for attr_name in ['CustomCropButton', 'CustomScissorsButton', 'CustomContinueButton']:
            if hasattr(slicer.modules, attr_name):
                delattr(slicer.modules, attr_name)
    except Exception as e:
        print(f"Error in cleanup_custom_crop_interface: {e}")

def use_custom_crop_instead_of_module():
    """
    Utility function to switch from the problematic crop module GUI to the custom crop interface.
    Call this when the crop module GUI becomes distorted during recropping.
    """
    try:

        try:
            collapse_crop_volume_gui()
        except Exception as e:
            print(f"Warning: Could not collapse crop volume GUI: {e}")
        custom_interface = create_custom_crop_interface()
        if custom_interface:
            return True
        return False
            
    except Exception as e:
        print(f"Error in use_custom_crop_instead_of_module: {e}")
        return False


def force_custom_crop_interface():
    """
    Convenience function to directly force the custom crop interface.
    Can be called from console or when crop module GUI is definitely broken.
    
    Usage from Slicer console:
    exec(open(r'c:\\path\\to\\workflow_moduals.py').read())
    force_custom_crop_interface()
    """
    try:
        success = use_custom_crop_instead_of_module()
        return success
        
    except Exception as e:
        print(f"Error in force_custom_crop_interface: {e}")
        return False

# Initialize scene save observer when module is fully loaded
try:
    setup_module_observers()
except Exception as e:
    print(f"Scene save observer setup failed. You will have to manualy close the program after saving. Error: {e}")