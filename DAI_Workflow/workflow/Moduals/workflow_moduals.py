import slicer
import qt
import vtk
import math
import numpy as np
import time

"""
Slicer Guided Workflow for Vessel Centerline Extraction and CPR Visualization

Christian Rogers - So Lab - Lawson - UWO (2025)

I apoligise in advance for the code you are about to read but there was a bit of a time crunch

UPDATE: Programmatic Segment Editor Integration
- Replaced GUI-based Segment Editor with programmatic API
- Added scissors tool toggle button for user control
- No Segment Editor GUI is opened - all operations are programmatic
- Floating UI elements for scissors control and workflow continuation
- Scissors tool can be activated/deactivated as needed by user
"""

def hide_status_bar():
    """
    Hide the status bar at the bottom of the Slicer main window.
    Can be called from console to manually hide the status bar.
    """
    try:
        # Access the main window and hide its status bar
        mainWindow = slicer.util.mainWindow()
        if mainWindow:
            statusBar = mainWindow.statusBar()
            if statusBar:
                statusBar.hide()
                return True
        return False
    except Exception as e:
        print(f"Warning: Could not hide status bar: {str(e)}")
        return False

def show_status_bar():
    """
    Show the status bar at the bottom of the Slicer main window.
    Can be called from console to manually show the status bar.
    """
    try:
        # Access the main window and show its status bar
        mainWindow = slicer.util.mainWindow()
        if mainWindow:
            statusBar = mainWindow.statusBar()
            if statusBar:
                statusBar.show()
                return True
        return False
    except Exception as e:
        print(f"Warning: Could not show status bar: {str(e)}")
        return False

def set_dark_background():
    """
    Convenience function to set 3D view background to dark.
    Can be called from console or other parts of the workflow.
    """
    return set_3d_view_background_black()

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
            else:
                pass
        
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
            pass
        
        # Strategy 4: Fallback to first volume, but warn user
        first_volume = volume_nodes[0]
        
        return first_volume
        
    except Exception as e:
        return slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")

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
    Ask the user if they want to import markup workflow files
    Returns True if yes, False if no
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
        return result
    except Exception as e:
        return False

def import_markup_file():
    """
    Let the user select and import a markup file
    Returns the imported markup node or None if cancelled/failed
    """
    try:
        # Create file dialog for markup import
        file_dialog = qt.QFileDialog(slicer.util.mainWindow())
        file_dialog.setWindowTitle("Select Markup File")
        file_dialog.setFileMode(qt.QFileDialog.ExistingFile)
        file_dialog.setAcceptMode(qt.QFileDialog.AcceptOpen)
        
        # Set file filters for common markup formats
        file_dialog.setNameFilters([
            "All Markup Files (*.mrk.json *.fcsv *.json)",
            "Slicer Markup JSON (*.mrk.json)",
            "Fiducial CSV (*.fcsv)",
            "JSON Files (*.json)",
            "All Files (*.*)"
        ])
        
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                markup_file = selected_files[0]
                
                # Try to load the markup file
                try:
                    # Get existing markup nodes count to find the new one
                    existing_markups = slicer.util.getNodesByClass('vtkMRMLMarkupsNode')
                    
                    # Load the markup file
                    success = slicer.util.loadMarkups(markup_file)
                    
                    if success:
                        # Find the newly loaded markup node
                        new_markups = slicer.util.getNodesByClass('vtkMRMLMarkupsNode')
                        new_markup_nodes = [node for node in new_markups if node not in existing_markups]
                        
                        if new_markup_nodes:
                            markup_node = new_markup_nodes[0]  # Get the first new markup node
                            slicer.util.infoDisplay(f"Successfully imported markup: {markup_node.GetName()}")
                            
                            # Create curve models from the imported markup points
                            curve_models = create_curve_models_from_markup(markup_node)
                            
                            return markup_node
                        else:
                            slicer.util.errorDisplay("Markup file loaded but no new markup node found.")
                            return None
                    else:
                        slicer.util.errorDisplay("Failed to load the selected markup file.")
                        return None
                        
                except Exception as e:
                    slicer.util.errorDisplay(f"Error loading markup file: {str(e)}")
                    return None
            
        return None
        
    except Exception as e:
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

def create_basic_segmentation_for_markup(volume_node):
    """
    Create a basic segmentation node that can be used with markup workflow for statistics
    """
    try:
        # Create a new segmentation node
        segmentation_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        segmentation_node.SetName("Markup_Segmentation")
        segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(volume_node)
        
        # Create a default segment (user can modify as needed)
        segmentation = segmentation_node.GetSegmentation()
        segment_id = segmentation.AddEmptySegment("Markup_Region")
        
        # Set segment color to white
        segment = segmentation.GetSegment(segment_id)
        if segment:
            segment.SetColor(1.0, 1.0, 1.0)
        
        # Set up display
        display_node = segmentation_node.GetDisplayNode()
        if display_node:
            display_node.SetAllSegmentsVisibility(True)
            display_node.SetVisibility2DOutline(True)
            display_node.SetVisibility2DFill(True)
        
        return segmentation_node
        
    except Exception as e:
        return None

def create_threshold_segment():
    """
    Main workflow function to create a threshold segment with default values
    """
    volume_node = find_working_volume()
    
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    
    # Ask user if they want to import markup
    want_markup = ask_user_for_markup_import()
    
    if want_markup:
        # User wants to import markup - handle all imports (markup, volume, transform)
        markup_node = import_markup_file()
        if markup_node:
            # Store markup workflow flag for later use
            slicer.modules.WorkflowUsingMarkup = True
            slicer.modules.WorkflowMarkupNode = markup_node
            
            # Also import straightened volume
            straightened_volume = import_straightened_volume()
            if straightened_volume:
                slicer.modules.WorkflowStraightenedVolume = straightened_volume
                slicer.util.infoDisplay("Straightened volume imported successfully.")
            else:
                slicer.util.infoDisplay("Straightened volume import cancelled or failed.")
            
            # Also import transform
            transform_node = import_transform_file()
            if transform_node:
                slicer.modules.WorkflowTransform = transform_node
                slicer.util.infoDisplay("Transform imported successfully.")
            else:
                slicer.util.infoDisplay("Transform import cancelled or failed.")
            
            slicer.util.infoDisplay("Markup workflow imports completed. Continuing with threshold segmentation workflow.")
        else:
            # Markup import failed, continue with normal workflow
            slicer.util.infoDisplay("Markup import cancelled or failed. Continuing with normal workflow.")
            slicer.modules.WorkflowUsingMarkup = False
    else:
        # Normal workflow path (no markup)
        slicer.modules.WorkflowUsingMarkup = False
    
    # Continue with normal threshold workflow (regardless of markup import)
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
                pass
                
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
        return False

def add_continue_button_to_segment_editor():
    """
    Add a continue button to the workflow (not to Segment Editor GUI since we're not using it)
    """
    try:
        # Create a floating continue button since we're not using the Segment Editor GUI
        create_continue_workflow_button()
        
    except Exception as e:
        pass

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
    Add the continue button container to the Crop Volume module GUI
    """
    try:
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
        
        # Try to add to the GUI layout
        if main_ui_widget and hasattr(main_ui_widget, 'layout'):
            layout = main_ui_widget.layout()
            if layout:
                # Add after the scissors buttons (towards bottom)
                layout.addWidget(continue_container)
                pass
                return True
            else:
                # Try to create a new layout
                new_layout = qt.QVBoxLayout(main_ui_widget)
                new_layout.addWidget(continue_container)
                pass
                return True
        else:
            # Fallback: try to find a suitable container widget
            container_widgets = crop_widget.findChildren(qt.QWidget)
            for widget in container_widgets:
                if hasattr(widget, 'layout') and widget.layout() and widget.layout().count() > 0:
                    widget.layout().addWidget(continue_container)
                    pass
                    return True
        
        pass
        return False
        
    except Exception as e:
        pass
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

def create_mask_segmentation(mask_name, threshold_low, threshold_high=None, rgb_color=(0.0, 1.0, 1.0), volume_node=None, volume_name=None):
    """
    Create a new mask segmentation with custom name, threshold values, and RGB color.
    The segmentation is created but NOT added to the 3D scene for visualization.
    
    Args:
        mask_name (str): Name for the mask segmentation
        threshold_low (float): Lower threshold value
        threshold_high (float, optional): Upper threshold value. If None, only lower threshold is used
        rgb_color (tuple): RGB color values (r, g, b) as floats between 0.0 and 1.0
        volume_node (vtkMRMLScalarVolumeNode, optional): Volume to apply threshold to. If None, uses volume_name or active volume
        volume_name (str, optional): Name of the volume to use. If specified, will search for volume by name
    
    Returns:
        vtkMRMLSegmentationNode: The created segmentation node, or None if failed
    """
    try:
        # Get the volume node to work with
        if volume_node is None:
            volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
            if not volume_nodes:
                pass
                return None
            
            # If volume_name is specified, search for it by name
            if volume_name:
                for volume in volume_nodes:
                    if volume.GetName() == volume_name:
                        volume_node = volume
                        pass
                        break
                    elif volume_name.lower() in volume.GetName().lower():
                        volume_node = volume
                        pass
                        break
                
                if volume_node is None:
                    pass
                    for i, vol in enumerate(volume_nodes):
                        pass
                    pass
            
            # Fallback: Try to find cropped volume first, otherwise use first available
            if volume_node is None:
                for volume in volume_nodes:
                    if 'cropped' in volume.GetName().lower():
                        volume_node = volume
                        break
                
                if volume_node is None:
                    volume_node = volume_nodes[0]
        
        pass
        
        # Create new segmentation node
        segmentation_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
        segmentation_node.SetName(mask_name)
        segmentation_node.CreateDefaultDisplayNodes()
        segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(volume_node)
        
        # Create segment with custom name
        segmentation = segmentation_node.GetSegmentation()
        segment_id = segmentation.AddEmptySegment(mask_name)
        segment = segmentation.GetSegment(segment_id)
        
        # Set custom RGB color
        if len(rgb_color) >= 3:
            segment.SetColor(rgb_color[0], rgb_color[1], rgb_color[2])
            pass
        
        # Apply threshold to create binary mask
        volume_array = slicer.util.arrayFromVolume(volume_node)
        if threshold_high is not None:
            binary_mask = (volume_array >= threshold_low) & (volume_array <= threshold_high)
            pass
        else:
            binary_mask = volume_array >= threshold_low
            pass
        
        pass
        
        # Convert binary mask to labelmap and import to segmentation
        temp_labelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        temp_labelmap.SetName(f"TempLabelmap_{mask_name}")
        slicer.util.updateVolumeFromArray(temp_labelmap, binary_mask.astype('uint8'))
        temp_labelmap.CopyOrientation(volume_node)
        
        # Import labelmap to segmentation
        segmentationLogic = slicer.modules.segmentations.logic()
        if segmentationLogic.ImportLabelmapToSegmentationNode(temp_labelmap, segmentation_node):
            pass
            
            # Clean up temporary labelmap
            slicer.mrmlScene.RemoveNode(temp_labelmap)
            
            # Ensure segmentation is NOT visible in 3D scene
            display_node = segmentation_node.GetDisplayNode()
            if display_node:
                display_node.SetVisibility3D(False)  # Disable 3D visibility
                display_node.SetVisibility(True)     # Keep 2D slice visibility
                pass
            
            return segmentation_node
        else:
            pass
            slicer.mrmlScene.RemoveNode(temp_labelmap)
            slicer.mrmlScene.RemoveNode(segmentation_node)
            return None
            
    except Exception as e:
        pass
        return None

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
        slicer.util.selectModule("ExtractCenterline")
        pass
        slicer.app.processEvents()
        
        # Set up minimal UI with only inputs section
        setup_minimal_extract_centerline_ui()
        
        remove_duplicate_centerline_buttons()
        setup_centerline_module()
        
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
                            setup_centerline_completion_monitor()
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

def clean_centerline_buttons():
    """
    Utility function to manually clean up duplicate centerline buttons (can be called from console)
    """
    pass
    remove_duplicate_centerline_buttons()
    pass

def stop_centerline_monitoring_manually():
    """
    Utility function to manually stop centerline monitoring (can be called from console)
    """
    pass
    stop_centerline_monitoring()
    pass

def check_monitoring_status():
    """
    Utility function to check if centerline monitoring is currently active
    """
    if hasattr(slicer.modules, 'CenterlineMonitorTimer'):
        timer = slicer.modules.CenterlineMonitorTimer
        if timer and timer.isActive():
            check_count = getattr(slicer.modules, 'CenterlineCheckCount', 0)
            start_time = getattr(slicer.modules, 'CenterlineMonitoringStartTime', 0)
            pass
            pass
        else:
            pass
    else:
        pass
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
        
        # Give GUI more time to fully initialize before verification
        slicer.app.processEvents()
        time.sleep(0.3)
        verification_results = verify_extract_centerline_point_list_autoselection()
        
        if not verification_results["success"]:
            pass
            fix_extract_centerline_setup_issues()
            # Re-verify after fixes
            time.sleep(0.2)
            slicer.app.processEvents()
            verification_results = verify_extract_centerline_point_list_autoselection()
        
        prompt_for_endpoints()
        
    except Exception as e:
        pass

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

def remove_default_segment(segmentation_node):
    """
    Remove any default segments like "Segment_1" to keep only our workflow segment
    """
    try:
        segmentation = segmentation_node.GetSegmentation()
        segment_ids = vtk.vtkStringArray()
        segmentation.GetSegmentIDs(segment_ids)
        workflow_segment_id = segmentation_node.GetAttribute("WorkflowCreatedSegmentID")
        
        segments_to_remove = []
        for i in range(segment_ids.GetNumberOfValues()):
            segment_id = segment_ids.GetValue(i)
            segment = segmentation.GetSegment(segment_id)
            if segment:
                segment_name = segment.GetName()
                if (segment_name.startswith("Segment_") and 
                    segment_id != workflow_segment_id and 
                    not segment_name.startswith("ThresholdSegment_")):
                    segments_to_remove.append(segment_id)
        for segment_id in segments_to_remove:
            segmentation.RemoveSegment(segment_id)
            
    except Exception as e:
        pass

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
    Add a large green Apply button directly to the Crop Volume module GUI
    Only creates the button if scissors workflow is not active
    """
    try:
        # Check if scissors workflow is active - if so, don't create the apply button
        if hasattr(slicer.modules, 'WorkflowScissorsButton') or hasattr(slicer.modules, 'WorkflowFinishButton'):
            return True
        
        if hasattr(slicer.modules, 'CropLargeApplyButton'):
            existing_button = slicer.modules.CropLargeApplyButton
            if existing_button and existing_button.parent():
                return True
        
        def create_large_button():
            try:
                if hasattr(slicer.modules, 'CropLargeApplyButton'):
                    existing_button = slicer.modules.CropLargeApplyButton
                    if existing_button and existing_button.parent():
                        return True
                
                crop_widget = slicer.modules.cropvolume.widgetRepresentation()

                if crop_widget:
                    crop_module = None
                    
                    if hasattr(crop_widget, 'self'):
                        try:
                            crop_module = crop_widget.self()
                            pass
                        except Exception as e:
                            pass
                    
                    if not crop_module:
                        try:
                            crop_module = crop_widget
                            pass
                        except Exception as e:
                            pass

                    if not crop_module:
                        try:
                            crop_module = slicer.modules.cropvolume.createNewWidgetRepresentation()
                            pass
                        except Exception as e:
                            pass
                    
                    if crop_module:
                        pass
                        
                        original_apply_button = None
                        pass
                        
                        apply_button_attrs = ['applyButton', 'ApplyButton', 'applyCropButton', 'cropApplyButton']
                        
                        if hasattr(crop_module, 'ui'):
                            pass
                            for attr_name in apply_button_attrs:
                                if hasattr(crop_module.ui, attr_name):
                                    original_apply_button = getattr(crop_module.ui, attr_name)
                                    pass
                                    break
                        else:
                            pass
                            for attr_name in apply_button_attrs:
                                if hasattr(crop_module, attr_name):
                                    original_apply_button = getattr(crop_module, attr_name)
                                    pass
                                    break

                        if not original_apply_button:
                            pass
                            all_buttons = crop_widget.findChildren(qt.QPushButton)
                            pass
                            for i, button in enumerate(all_buttons):
                                button_text = button.text if hasattr(button, 'text') else ""
                                pass
                                if button_text and 'apply' in button_text.lower():
                                    original_apply_button = button
                                    pass
                                    break
                    
                    if original_apply_button:
                        # Create a new large green button
                        large_apply_button = qt.QPushButton("APPLY CROP")
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
                        
                        # Connect the new button to trigger the original Apply button's click
                        large_apply_button.connect('clicked()', lambda: original_apply_button.click())
                        
                    else:
                        pass
                        # Create button anyway and try to trigger apply through the module
                        large_apply_button = qt.QPushButton("APPLY CROP")
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
                        
                        # Try to connect to crop logic directly
                        def trigger_crop_apply():
                            try:
                                if hasattr(crop_module, 'onApplyButton'):
                                    crop_module.onApplyButton()
                                    pass
                                elif hasattr(crop_module, 'apply'):
                                    crop_module.apply()
                                    pass
                                else:
                                    pass
                            except Exception as e:
                                pass
                        
                        large_apply_button.connect('clicked()', trigger_crop_apply)
                        pass
                    
                    # Add the button to the GUI (common for both cases)
                    # Try to find the main UI container in the crop module
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
                    
                    if main_ui_widget and hasattr(main_ui_widget, 'layout'):
                        layout = main_ui_widget.layout()
                        if layout:
                            layout.insertWidget(0, large_apply_button)
                        else:
                            new_layout = qt.QVBoxLayout(main_ui_widget)
                            new_layout.insertWidget(0, large_apply_button)
                            pass
                    else:
                        container_widgets = crop_widget.findChildren(qt.QWidget)
                        for widget in container_widgets:
                            if hasattr(widget, 'layout') and widget.layout() and widget.layout().count() > 0:
                                widget.layout().insertWidget(0, large_apply_button)
                                pass
                                break
                        else:
                            pass
                            return False
                    
                    slicer.modules.CropLargeApplyButton = large_apply_button
                    return True
                else:
                    if crop_widget:
                        try:
                            attrs = [attr for attr in dir(crop_widget) if not attr.startswith('_')]
                            pass
                        except:
                            pass
                    return False
                        
            except Exception as e:
                return False
        
        success = create_large_button()
        
        # If that didn't work, try again after delays
        if not success:
            qt.QTimer.singleShot(1000, create_large_button)
            qt.QTimer.singleShot(3000, create_large_button)
            pass
            
    except Exception as e:
        pass

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
                            large_apply_button = qt.QPushButton("APPLY CPR")
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
                            large_apply_button = qt.QPushButton("APPLY CPR")
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

def open_cross_section_analysis_module():
    """
    Helper function to open the Cross-Section Analysis module.
    Can be called from console to test the module switching functionality.
    """
    try:
        # Apply transform to centerline nodes before opening Cross-Section Analysis
        apply_cpr_transform_to_centerlines()
        
        # Try the most likely module name first
        slicer.util.selectModule("CrossSectionAnalysis")
        return True
    except Exception as e:
        # Try alternative module names
        try:
            slicer.util.selectModule("Cross-sectionanalysis")
            return True
        except Exception as e2:
            try:
                slicer.util.selectModule("CrossSection")
                return True
            except Exception as e3:

                return False



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
    Collapse the Parameters tab in the Cross-Section Analysis module after Apply has been clicked
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
                    if cb.collapsed == False:  # If it's currently expanded
                        cb.collapsed = True    # Collapse it
                        return True
                    else:
                        return True
        except Exception as ctk_error:
            pass
        
        # Also try QGroupBox as fallback
        group_boxes = module_widget.findChildren(qt.QGroupBox)
        for gb in group_boxes:
            box_title = gb.title if hasattr(gb, 'title') else ""
            if "parameter" in box_title.lower():
                # For QGroupBox, try to hide or minimize
                if hasattr(gb, 'setVisible'):
                    gb.setVisible(False)
                    return True
        
        # Try finding any widget with "parameter" in the name or text
        all_widgets = module_widget.findChildren(qt.QWidget)
        for widget in all_widgets:
            # Check object name
            if hasattr(widget, 'objectName') and widget.objectName():
                if "parameter" in widget.objectName().lower():
                    if hasattr(widget, 'setVisible'):
                        widget.setVisible(False)
                        return True
            
            # Check if it's a collapsible widget with parameter text
            if hasattr(widget, 'text') and widget.text:
                if "parameter" in widget.text().lower():
                    if hasattr(widget, 'collapsed'):
                        widget.collapsed = True
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

def apply_transform_to_specific_centerline_nodes(centerline_model=None, centerline_curve=None):
    """
    Apply CPR transform to specific centerline nodes (used when specific nodes are known)
    
    Args:
        centerline_model: Specific centerline model node to transform
        centerline_curve: Specific centerline curve node to transform
    """
    try:
        # Find the straightening transform
        transform_nodes = slicer.util.getNodesByClass('vtkMRMLTransformNode')
        straightening_transform = None
        
        for transform_node in transform_nodes:
            transform_name = transform_node.GetName().lower()
            if ('straighten' in transform_name or 
                'cpr' in transform_name or 
                'curved' in transform_name):
                straightening_transform = transform_node
                break
        
        if not straightening_transform and transform_nodes:
            straightening_transform = transform_nodes[-1]  # Get the most recent
        
        if not straightening_transform:
            pass
            return False
        
        # Apply transform to specific nodes
        transformed_count = 0
        
        if centerline_model:
            centerline_model.SetAndObserveTransformNodeID(straightening_transform.GetID())
            transformed_count += 1
            pass
        
        if centerline_curve:
            centerline_curve.SetAndObserveTransformNodeID(straightening_transform.GetID())
            transformed_count += 1
            pass
        
        if transformed_count > 0:
            pass
            slicer.app.processEvents()
            return True
        else:
            return False
            
    except Exception as e:
        pass
        return False

def apply_cpr_transforms_manually():
    """
    Console helper function to manually apply CPR transforms to centerline nodes.
    Can be called from the Python console if automatic application fails.
    """
    try:
        return apply_cpr_transform_to_centerlines()
    except Exception as e:
        return False

def list_available_transforms():
    """
    Console helper to list all available transform nodes in the scene
    """
    try:
        transform_nodes = slicer.util.getNodesByClass('vtkMRMLTransformNode')
        return transform_nodes
    except Exception as e:
        return []

def style_crop_apply_button():
    """
    Style the Apply button in the Crop Volume module to be large and green
    """
    try:
        def apply_styling():
            try:
                crop_widget = slicer.modules.cropvolume.widgetRepresentation()
                if crop_widget:
                    apply_button = None
                    
                    if hasattr(crop_widget, 'self') and hasattr(crop_widget.self(), 'ui'):
                        crop_module = crop_widget.self()
                        if hasattr(crop_module.ui, 'applyButton'):
                            apply_button = crop_module.ui.applyButton
                            pass
                        elif hasattr(crop_module.ui, 'ApplyButton'):
                            apply_button = crop_module.ui.ApplyButton
                            pass
                    
                    if not apply_button:
                        all_buttons = crop_widget.findChildren(qt.QPushButton)
                        pass
                        for button in all_buttons:
                            button_text = button.text if hasattr(button, 'text') else ""
                            button_name = button.objectName() if hasattr(button, 'objectName') else ""
                            pass
                            if 'apply' in button_text.lower() or 'apply' in button_name.lower():
                                apply_button = button
                                pass
                                break
                    
                    if not apply_button:
                        main_window = slicer.util.mainWindow()
                        all_buttons = main_window.findChildren(qt.QPushButton)
                        for button in all_buttons:
                            button_text = button.text if hasattr(button, 'text') else ""
                            parent_name = button.parent().objectName() if button.parent() and hasattr(button.parent(), 'objectName') else ""
                            if 'apply' in button_text.lower() and ('crop' in parent_name.lower() or 'volume' in parent_name.lower()):
                                apply_button = button
                                pass
                                break
                    
                    if apply_button:
                        style_sheet = """
                            QPushButton { 
                                background-color: #28a745 !important; 
                                color: white !important; 
                                border: 2px solid #1e7e34 !important; 
                                padding: 20px !important; 
                                font-weight: bold !important;
                                border-radius: 10px !important;
                                margin: 10px !important;
                                font-size: 18px !important;
                                min-height: 70px !important;
                                min-width: 200px !important;
                            }
                            QPushButton:hover { 
                                background-color: #218838 !important; 
                                border: 2px solid #155724 !important;
                                transform: scale(1.05);
                            }
                            QPushButton:pressed { 
                                background-color: #1e7e34 !important; 
                                border: 2px solid #0f4c2c !important;
                            }
                        """
                        apply_button.setStyleSheet(style_sheet)
                        
                        apply_button.setMinimumHeight(70)
                        apply_button.setMinimumWidth(200)
                        
                        return True
                    else:
                        return False
                        
            except Exception as e:
                pass
                return False
        
        success = apply_styling()
        
        if not success:
            timer = qt.QTimer()
            timer.singleShot(1000, apply_styling)  # Try again after 1 second
            
    except Exception as e:
        pass

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
                start_with_volume_crop()
                return
        
        slicer.util.selectModule("DICOM")
        slicer.app.processEvents()
        
        # Set up monitoring for volume addition
        setup_volume_addition_monitor()
        
    except Exception as e:
        slicer.util.errorDisplay(f"Could not open DICOM module: {str(e)}")

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
            pass
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

def start_with_volume_crop():
    """
    Start the workflow by opening the Volume Crop module and creating an ROI that fits the entire volume.
    """
    # Set 3D view background to black at the start of workflow
    set_3d_view_background_black()
    
    volume_node = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    slicer.util.selectModule("CropVolume")
    slicer.app.processEvents()
    hide_crop_volume_ui_elements()
    qt.QTimer.singleShot(1000, hide_crop_volume_ui_elements)
    qt.QTimer.singleShot(3000, hide_crop_volume_ui_elements)
    
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

def setup_centerline_completion_monitor_without_reset(target_models=None, target_curves=None):
    """
    Set up monitoring to detect when specific centerlines have sufficient data without resetting baseline
    """
    try:
        stop_centerline_monitoring()

        # Do NOT clear the dialog flag - we want to show dialog when these centerlines get sufficient data
        # Do NOT reset baseline - keep existing baseline from apply button monitoring

        # Store the target centerlines to monitor
        if target_models:
            slicer.modules.TargetCenterlineModels = [model.GetID() for model in target_models]
        if target_curves:
            slicer.modules.TargetCenterlineCurves = [curve.GetID() for curve in target_curves]

        timer = qt.QTimer()
        timer.timeout.connect(check_specific_centerline_completion)
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

def display_centerline_placement_status():
    """
    Display current status of centerline references for point placement.
    Useful for debugging and validation.
    """
    try:
        validation_info = validate_point_placement_centerline_reference()
        
        status_message = "Centerline Placement Status:\n\n"
        
        if validation_info.get("error"):
            status_message += f"Error: {validation_info['error']}\n"
        else:
            status_message += f"Has current point list: {validation_info['has_current_point_list']}\n"
            status_message += f"Point list has centerline ref: {validation_info['point_list_has_centerline_ref']}\n"
            status_message += f"Centerline model available: {validation_info['centerline_model_available']}\n"
            status_message += f"Centerline curve available: {validation_info['centerline_curve_available']}\n"
            
            if validation_info['centerline_model_name']:
                status_message += f"Model name: {validation_info['centerline_model_name']}\n"
            if validation_info['centerline_curve_name']:
                status_message += f"Curve name: {validation_info['centerline_curve_name']}\n"
            
            status_message += "\nRecommendations:\n"
            for rec in validation_info['recommendations']:
                status_message += f"• {rec}\n"
        
        print(status_message)
        return status_message
        
    except Exception as e:
        error_msg = f"Error displaying centerline status: {str(e)}"
        print(error_msg)
        return error_msg

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
        print(f"Error populating centerline dropdown: {str(e)}")

def get_selected_centerline():
    """
    Get the currently selected centerline from the dropdown
    Returns tuple of (model, curve) where one might be None
    """
    try:
        centerline_combo = getattr(slicer.modules, 'WorkflowCenterlineCombo', None)
        if not centerline_combo:
            return (None, None)
        
        current_index = centerline_combo.currentIndex
        if current_index < 0:
            return (None, None)
        
        # Get the data associated with the current selection
        selected_item = centerline_combo.itemData(current_index)
        
        if selected_item is None:
            # Auto-select mode or no centerlines - use the existing logic
            current_centerline_model = find_recent_centerline_model()
            current_centerline_curve = find_recent_centerline_curve()
            return (current_centerline_model, current_centerline_curve)
        
        # Determine if selected item is a model or curve
        if selected_item.GetClassName() == 'vtkMRMLModelNode':
            return (selected_item, None)
        elif selected_item.GetClassName() == 'vtkMRMLMarkupsCurveNode':
            return (None, selected_item)
        
        return (None, None)
        
    except Exception as e:
        pass
        print(f"Error getting selected centerline: {str(e)}")
        return (None, None)

def refresh_centerline_dropdown():
    """
    Refresh the centerline dropdown by repopulating it with current centerlines
    """
    try:
        centerline_combo = getattr(slicer.modules, 'WorkflowCenterlineCombo', None)
        if not centerline_combo:
            return
        
        # Store the currently selected item text to try to restore selection
        current_text = centerline_combo.currentText if centerline_combo.currentIndex >= 0 else ""
        
        # Repopulate the dropdown
        populate_centerline_dropdown()
        
        # Try to restore the previous selection if it still exists
        if current_text:
            index = centerline_combo.findText(current_text)
            if index >= 0:
                centerline_combo.setCurrentIndex(index)
        
    except Exception as e:
        pass
        print(f"Error refreshing centerline dropdown: {str(e)}")

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

def start_point_placement(point_list, start_button, stop_button, count_label):
    """
    Start interactive point placement mode with continuous placement enabled
    """
    try:
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            selectionNode.SetActivePlaceNodeID(point_list.GetID())

        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
            interactionNode.SetPlaceModePersistence(1)

        start_button.setEnabled(False)
        stop_button.setEnabled(True)
        update_point_count_display(point_list, count_label)
        
        # Set up observer for automatic tool re-selection
        setup_point_count_observer(point_list, count_label)
        
        pass
        pass
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not start point placement: {str(e)}")

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
        
        # Also clear any existing circles from previous runs
        clear_centerline_circles()
        
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
        
        # Also clear any existing circles from previous runs
        clear_centerline_circles()
        
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


def clear_all_points(point_list, count_label):
    """
    Clear all points from the point list
    """
    try:
        point_count = point_list.GetNumberOfControlPoints()
        if point_count == 0:
            pass
            return
        
        result = slicer.util.confirmYesNoDisplay(f"Clear all {point_count} points?")
        if result:
            point_list.RemoveAllControlPoints()
            update_point_count_display(point_list, count_label)
            pass
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not clear points: {str(e)}")


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

def clear_all_points_from_scene(count_label):
    """
    Clear all lesion analysis point lists from the scene
    """
    try:
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        lesion_analysis_nodes = []
        
        for node in fiducial_nodes:
            node_name = node.GetName()
            if node_name == "F-1":
                lesion_analysis_nodes.append(node)
        
        if not lesion_analysis_nodes:
            pass
            return
        
        node_count = len(lesion_analysis_nodes)
        total_points = sum(node.GetNumberOfControlPoints() for node in lesion_analysis_nodes)
        
        for node in lesion_analysis_nodes:
            slicer.mrmlScene.RemoveNode(node)
            pass
        
        if hasattr(slicer.modules, 'CurrentLesionAnalysisPointList'):
            del slicer.modules.CurrentLesionAnalysisPointList

        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
        
        count_label.setText("Points placed: 0")
        pass
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not clear points: {str(e)}")

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



def setup_stenosis_line_sequence_observer(first_line_node, second_line_node):
    """
    Set up observer to automatically switch to second line when first is complete
    """
    try:
        if hasattr(first_line_node, 'StenosisSequenceObserver'):
            first_line_node.RemoveObserver(first_line_node.StenosisSequenceObserver)
        
        observer_id = first_line_node.AddObserver(
            first_line_node.PointAddedEvent, 
            lambda caller, event: check_first_line_completion_carefully(caller, second_line_node)
        )
        first_line_node.StenosisSequenceObserver = observer_id
        
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



def on_continue_stenosis_measurements(dialog):
    """
    Continue with another stenosis measurement pair
    """
    try:
        dialog.close()
        dialog.setParent(None)
        
        pass
        pass
        
        # Create another pair of stenosis measurements
        create_stenosis_ratio_measurement()
        
    except Exception as e:
        pass

def on_stop_stenosis_measurements(dialog):
    """
    Stop stenosis measurements and close the measurement tool
    """
    try:
        dialog.close()
        dialog.setParent(None)
        
        pass
        stop_stenosis_measurement_tool()
        show_stenosis_measurements_summary()
        
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

def show_stenosis_measurements_summary():
    """
    Show a summary of all stenosis measurements created
    """
    try:
        line_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsLineNode')
        stenosis_lines = []
        
        for node in line_nodes:
            if "StenosisLine" in node.GetName() and node.GetNumberOfControlPoints() == 2:
                measurement = node.GetMeasurement("length")
                if measurement:
                    length_value = measurement.GetValue()
                    stenosis_lines.append((node.GetName(), length_value))
        
        if stenosis_lines:
            pass
            pass
            pass
            for name, length in stenosis_lines:
                pass
            pass
            pass
            
            # Show summary dialog
            summary_text = "Stenosis Measurements Complete!\n\n"
            summary_text += f"Created {len(stenosis_lines)} stenosis measurements:\n\n"
            for name, length in stenosis_lines:
                summary_text += f"• {name}: {length:.2f} mm\n"
            summary_text += f"\nAll measurements are available in the scene for analysis."
            
            slicer.util.infoDisplay(summary_text)
        else:
            pass
        
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

def export_project_and_continue():
    """
    Save the Slicer project using normal save functionality and continue to workflow2.py
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

        success = slicer.app.ioManager().openSaveDataDialog()
        
        if success:
            pass
            
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
        dialog.resize(500, 350)
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
            summary_label = qt.QLabel(summary_text)
            summary_label.setStyleSheet("QLabel { color: #666; margin: 5px 10px; font-size: 11px; font-weight: bold; }")
            layout.addWidget(summary_label)
        
        layout.addSpacing(10)
        instruction_label = qt.QLabel("Choose your next action:")
        instruction_label.setStyleSheet("QLabel { color: #555; margin: 10px; font-size: 12px; font-weight: bold; }")
        layout.addWidget(instruction_label)
        
        # Create two rows of buttons
        first_row_layout = qt.QHBoxLayout()
        second_row_layout = qt.QHBoxLayout()
        
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
        second_row_layout.addWidget(continue_button)
        
        layout.addLayout(first_row_layout)
        layout.addLayout(second_row_layout)
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
        # Reset the dialog flag to allow future dialogs
        if hasattr(slicer.modules, 'CenterlineDialogShown'):
            slicer.modules.CenterlineDialogShown = False
        
        dialog.close()
        dialog.setParent(None)
        
        # Create a new centerline extraction setup for additional centerlines
        create_additional_centerline_setup()
    except Exception as e:
        pass
        


def create_additional_centerline_setup():
    """
    Create new centerline model and curve nodes and set up Extract Centerline module for additional centerlines
    """
    try:
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
        
        slicer.app.processEvents()
        
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
            pass
            for model in new_models:
                pass
            for curve in new_curves:
                pass
            
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
                pass
                if best_model:
                    pass
                if best_curve:
                    pass
                
                # Stop any existing centerline monitoring to prevent duplicate dialogs
                stop_centerline_monitoring()
                
                # Mark that we're showing a dialog for this extraction cycle
                slicer.modules.CenterlineDialogShown = True
                
                show_centerline_completion_dialog(best_model, best_curve)
                return
            else:
                # No sufficient data yet, continue monitoring for completion
                pass
                # Don't clear the dialog flag - we still want to show dialog when sufficient data is available
                # Set up monitoring but don't reset baseline (keep existing baseline)
                setup_centerline_completion_monitor_without_reset(new_models, new_curves)
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
                    stop_apply_button_monitoring()
                    setup_centerline_completion_monitor()
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

def start_centerline_monitoring_for_additional():
    """
    Manual function to start centerline monitoring for additional centerlines
    """
    try:
        setup_centerline_completion_monitor()
        pass
        pass
        
        # Update button to indicate monitoring is active
        if hasattr(slicer.modules, 'CenterlineMonitoringButton'):
            button = slicer.modules.CenterlineMonitoringButton
            if button:
                button.setText("Monitoring Active...")
                button.setEnabled(False)
                button.setStyleSheet("""
                    QPushButton { 
                        background-color: #28a745; 
                        color: white; 
                        border: none; 
                        padding: 10px 15px; 
                        font-weight: bold;
                        border-radius: 6px;
                        margin: 5px;
                        font-size: 12px;
                        min-width: 150px;
                    }
                """)
        
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

def stop_volume_monitoring():
    """Console helper to manually stop volume addition monitoring"""
    try:
        pass
        stop_volume_addition_monitoring()
        return True
    except Exception as e:
        pass
        return False

def skip_to_volume_crop():
    """Console helper to skip DICOM loading and go directly to volume crop"""
    try:
        pass
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        if not volume_nodes:
            pass
            return False
        
        # Stop any existing monitoring
        stop_volume_addition_monitoring()
        
        # Continue with volume crop
        start_with_volume_crop()
        return True
    except Exception as e:
        pass
        return False

def cleanup_status_widget():
    """Console helper to clean up the status widget"""
    try:
        cleanup_volume_waiting_status_widget()
        pass
        return True
    except Exception as e:
        pass
        return False

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

def get_centerline_summary():
    """
    Get a summary of all existing centerlines in the scene
    """
    try:
        all_models = find_all_centerline_models()
        all_curves = find_all_centerline_curves()
        
        summary = f"Centerlines in scene:\n"
        summary += f"• Models: {len(all_models)}\n"
        summary += f"• Curves: {len(all_curves)}\n"
        
        if all_models:
            summary += "\nCenterline Models:\n"
            for i, model in enumerate(all_models, 1):
                polydata = model.GetPolyData()
                point_count = polydata.GetNumberOfPoints() if polydata else 0
                summary += f"  {i}. {model.GetName()} ({point_count} points)\n"
                
        if all_curves:
            summary += "\nCenterline Curves:\n"
            for i, curve in enumerate(all_curves, 1):
                point_count = curve.GetNumberOfControlPoints()
                summary += f"  {i}. {curve.GetName()} ({point_count} control points)\n"
        
        return summary
        
    except Exception as e:
        pass
        return "Error retrieving centerline information"


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

def set_straightened_volume_visible():
    """
    Set the straightened volume as visible in all slice views
    """
    try:
        if hasattr(slicer.modules, 'WorkflowStraightenedVolume'):
            straightened_volume = slicer.modules.WorkflowStraightenedVolume
        else:
            volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
            straightened_volume = None
            for volume in volume_nodes:
                if 'straightened' in volume.GetName().lower():
                    straightened_volume = volume
                    break
        
        if straightened_volume:
            layout_manager = slicer.app.layoutManager()
            slice_view_names = ['Red', 'Yellow', 'Green']
            
            for slice_view_name in slice_view_names:
                slice_widget = layout_manager.sliceWidget(slice_view_name)
                if slice_widget:
                    slice_logic = slice_widget.sliceLogic()
                    if slice_logic:
                        slice_logic.GetSliceCompositeNode().SetBackgroundVolumeID(straightened_volume.GetID())
                        pass
            
            for slice_view_name in slice_view_names:
                slice_widget = layout_manager.sliceWidget(slice_view_name)
                if slice_widget:
                    slice_view = slice_widget.sliceView()
                    if slice_view:
                        slice_view.fitToWindow()
            
            selection_node = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
            if selection_node:
                selection_node.SetActiveVolumeID(straightened_volume.GetID())
            
            pass
            
        else:
            pass
            
    except Exception as e:
        pass

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

def create_axial_circle_points(circle_node, center_point, radius):
    """
    Create circle points in the axial plane (XY plane) for a single circle
    """
    try:
        import math
        num_points = 24
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = center_point[0] + radius * math.cos(angle)
            y = center_point[1] + radius * math.sin(angle)
            z = center_point[2] 
            
            circle_node.AddControlPoint([x, y, z])
        
        if hasattr(circle_node, 'SetCurveClosed'):
            circle_node.SetCurveClosed(True)
        
        return True
        
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
            if ('circle' in node.GetName().lower() and 'centerline' in node.GetName().lower()) or \
               ('axialcircle' in node.GetName().lower()):
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

        return success
    except Exception as e:
        pass  # Error creating post branch circle: {str(e)}
        return False

def apply_transform_to_node(node, node_description="node"):
    """
    Apply the straightening transform to any node
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
            node.SetAndObserveTransformNodeID(straightening_transform.GetID())
            pass
            return True
        else:
            transform_names = [node.GetName() for node in transform_nodes]
            pass
            return False
            
    except Exception as e:
        pass
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

def set_tube_radius(radius):
    """
    Helper function to set a custom tube radius.
    """
    global tube_radius
    tube_radius = radius
    pass

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

def create_bone_mask(volume_name=None):
    """
    Helper function to create a bone density mask.
    
    Args:
        volume_name (str, optional): Name of the volume to use
    """
    return create_mask_segmentation(
        mask_name="BoneMask",
        threshold_low=200,
        rgb_color=(1.0, 1.0, 1.0),  # Bright white
        volume_name=volume_name
    )

def create_soft_tissue_mask(volume_name=None):
    """
    Helper function to create a soft tissue density mask.
    
    Args:
        volume_name (str, optional): Name of the volume to use
    """
    return create_mask_segmentation(
        mask_name="SoftTissueMask",
        threshold_low=-100,
        threshold_high=100,
        rgb_color=(0.0, 1.0, 0.0),  # Green
        volume_name=volume_name
    )

def create_contrast_mask(volume_name=None):
    """
    Helper function to create a contrast-enhanced tissue mask.
    
    Args:
        volume_name (str, optional): Name of the volume to use
    """
    return create_mask_segmentation(
        mask_name="ContrastMask",
        threshold_low=100,
        threshold_high=400,
        rgb_color=(0.0, 0.0, 1.0),  # Blue
        volume_name=volume_name
    )

def create_analysis_masks_manually(volume_name=None):
    """
    Helper function to manually create analysis masks (LAP, NCP, STENOSIS).
    Can be called from console to create masks on any volume.
    All masks are created as segments within a single segmentation node.
    
    Args:
        volume_name (str, optional): Name of the volume to use. If None, will try to find straightened volume
    
    Returns:
        vtkMRMLSegmentationNode: The created segmentation node containing all analysis segments, or None if failed
    """
    try:
        # If no volume name specified, try to find straightened volume
        target_volume = None
        if volume_name:
            volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
            for volume in volume_nodes:
                if volume.GetName() == volume_name or volume_name.lower() in volume.GetName().lower():
                    target_volume = volume
                    break
        else:
            # Look for straightened volume
            volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
            for volume in volume_nodes:
                if 'straightened' in volume.GetName().lower():
                    target_volume = volume
                    break
        
        if not target_volume:
            pass
            return None
        
        # Create masks using the create_analysis_masks function
        segmentation_node = create_analysis_masks([target_volume])
        
        # Return the created segmentation node
        return segmentation_node
            
    except Exception as e:
        pass
        return None

def hide_crop_volume_ui_elements():
    """
    Hide all UI elements in the Crop Volume module except the green Apply button
    """
    try:
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if not crop_widget:
            pass
            return False
        
        # Names of the collapsible buttons to hide based on the XML structure
        collapsible_buttons_to_hide = [
            "ParameterSetCollapsibleButton",
            "InputOutputCollapsibleButton", 
            "InterpolationOptionsCollapsibleButton",
            "VolumeInformationCollapsibleButton"
        ]
        
        # Hide error message elements
        error_elements_to_hide = [
            "InputErrorLabel",
            "InputErrorFixButton"
        ]
        
        elements_hidden = 0
        
        # Hide collapsible button sections
        for button_name in collapsible_buttons_to_hide:
            try:
                # Find the collapsible button by object name
                collapsible_buttons = crop_widget.findChildren(qt.QWidget, button_name)
                for button in collapsible_buttons:
                    button.setVisible(False)
                    elements_hidden += 1
                    pass
            except Exception as e:
                pass
        
        # Hide error message elements 
        for element_name in error_elements_to_hide:
            try:
                elements = crop_widget.findChildren(qt.QWidget, element_name)
                for element in elements:
                    element.setVisible(False)
                    elements_hidden += 1
                    pass
            except Exception as e:
                pass
        
        # Also hide by finding ctkCollapsibleButton widgets directly
        try:
            collapsible_buttons = crop_widget.findChildren("ctkCollapsibleButton")
            for button in collapsible_buttons:
                button.setVisible(False)
                elements_hidden += 1
                pass
        except Exception as e:
            pass
        
        # Hide the horizontal layout containing error elements
        try:
            horizontal_layouts = crop_widget.findChildren(qt.QHBoxLayout)
            for layout in horizontal_layouts:
                if layout.objectName() == "horizontalLayout":
                    # Hide the parent widget of this layout
                    parent_widget = layout.parent()
                    if parent_widget:
                        parent_widget.setVisible(False)
                        elements_hidden += 1
                        pass
        except Exception as e:
            pass
        
        pass
        pass
        return True
        
    except Exception as e:
        pass
        return False

def setup_minimal_crop_volume_ui():
    """
    Set up the Crop Volume module with minimal UI (only the green Apply button)
    """
    try:
        # First ensure we're in the Crop Volume module
        slicer.util.selectModule("CropVolume")
        slicer.app.processEvents()
        
        # Hide all UI elements except the Apply button
        hide_success = hide_crop_volume_ui_elements()
        
        if hide_success:
            # Add the large green Apply button
            add_large_crop_apply_button()
            pass
            return True
        else:
            pass
            return False
            
    except Exception as e:
        pass
        return False


def cleanup_all_workflow_scissors_ui():
    """Console helper to clean up all scissors workflow UI"""
    try:
        cleanup_continue_ui()
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
        
        pass
        pass
        
        return True
        
    except Exception as e:
        pass
        return False

def setup_minimal_segment_editor_ui():
    """
    Set up the Segment Editor module with minimal UI (only the scissors tool)
    """
    try:
        # First ensure we're in the Segment Editor module
        slicer.util.selectModule("SegmentEditor")
        slicer.app.processEvents()
        
        # Get the segment editor widget
        segment_editor_widget = slicer.modules.segmenteditor.widgetRepresentation()
        if not segment_editor_widget:
            pass
            return False
        
        # Hide all effect buttons except scissors
        try:
            # Find all effect buttons and hide them except scissors
            all_buttons = segment_editor_widget.findChildren("QPushButton")
            hidden_count = 0
            
            for button in all_buttons:
                button_text = button.text if hasattr(button, 'text') else ""
                button_name = button.objectName if hasattr(button, 'objectName') else ""
                
                # Keep only scissors tool button visible
                if not any(keyword in button_text.lower() or keyword in button_name.lower() 
                          for keyword in ['scissor', 'cut', 'clip']):
                    if button_text and 'apply' not in button_text.lower():
                        button.hide()
                        hidden_count += 1
            
            pass
            
        except Exception as e:
            pass
        
        # Hide other UI sections we don't need
        try:
            # Hide segments section (we'll manage segments programmatically)
            collapsible_buttons = segment_editor_widget.findChildren("ctkCollapsibleButton")
            for button in collapsible_buttons:
                button_text = button.text if hasattr(button, 'text') else ""
                if 'segment' in button_text.lower() and 'editor' not in button_text.lower():
                    button.collapsed = True
                    button.hide()
            
            pass
            
        except Exception as e:
            pass
        
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

        scissors_button.connect('toggled(bool)', lambda checked: toggle_scissors_tool(checked))
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

def toggle_scissors_tool(activated):
    """
    Toggle the scissors tool on/off programmatically
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
                pass
                return False
                
        else:
            # Deactivate scissors tool
            segmentEditorWidget.setActiveEffectByName("")  # Clear active effect
            
            # Return to normal interaction mode
            interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
            if interactionNode:
                interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
            
            slicer.modules.WorkflowScissorsActive = False
            pass
            
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
        # Check if we're still in the Crop Volume module
        current_module = slicer.util.selectedModule()
        if current_module != "CropVolume":
            return
        if hasattr(slicer.modules, 'CropLargeApplyButton'):
            button = slicer.modules.CropLargeApplyButton
            if button and button.parent():
                button.show()
                return
    except Exception as e:
        pass

def setup_extract_centerline_with_verification():
    """
    Set up the Extract Centerline module and verify proper auto-selection functionality
    """
    try:
        setup_centerline_module()
        
        slicer.app.processEvents()
    except Exception as e:
        return False

def fix_extract_centerline_setup_issues():
    """
    Attempt to fix common issues with Extract Centerline module setup
    """
    try:
        endpoints_node = slicer.util.getNode("CenterlineEndpoints")
        if not endpoints_node:
            endpoints_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
            endpoints_node.SetName("CenterlineEndpoints")
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode and endpoints_node:
            selectionNode.SetActivePlaceNodeID(endpoints_node.GetID())
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
            interactionNode.SetPlaceModePersistence(1)
        extract_centerline_widget = slicer.modules.extractcenterline.widgetRepresentation()
        if extract_centerline_widget:
            endpoints_selector = extract_centerline_widget.findChild(qt.QWidget, "endPointsMarkupsSelector")
            if endpoints_selector and hasattr(endpoints_selector, 'setCurrentNode'):
                endpoints_selector.setCurrentNode(endpoints_node)
            place_widget = extract_centerline_widget.findChild(qt.QWidget, "endPointsMarkupsPlaceWidget")
            if place_widget:
                if hasattr(place_widget, 'setCurrentNode'):
                    place_widget.setCurrentNode(endpoints_node)
                if hasattr(place_widget, 'setPlaceModeEnabled'):
                    place_widget.setPlaceModeEnabled(True)
        slicer.app.processEvents()     
    except Exception as e:
        pass



def fix_centerline_issues():
    """
    Comprehensive function to fix various Extract Centerline module issues
    """
    try:
        
        # Ensure we're in the right module
        slicer.util.selectModule("ExtractCenterline")
        slicer.app.processEvents()
        
        # Run the setup fixes
        fix_extract_centerline_setup_issues()
        

        setup_centerline_module()

        results = verify_extract_centerline_point_list_autoselection()
        
        return results['success']
        
    except Exception as e:
        return False

