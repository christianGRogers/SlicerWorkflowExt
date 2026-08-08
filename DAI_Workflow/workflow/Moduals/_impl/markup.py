from ._common import *  # noqa: F401,F403  (shared imports + logger)
from . import centerline, core, segmentation, ui, volume  # sibling modules (cross-calls)

__all__ = [
    'import_markup_file',
    'process_markup_folder_and_create_tubes',
    'load_first_point_from_markup',
    'create_tube_from_two_points',
    'create_tube_from_curve_with_color',
    'create_curve_models_from_markup',
    'markup_workflow_after_crop',
    'continue_workflow_without_markup',
    'create_additional_fiducial_list',
    'create_additional_curve_markup',
    'force_point_placement_tool_selection',
    'start_markup_workflow',
    'prompt_for_endpoints',
    'create_point_list_and_prompt',
    'create_point_placement_controls',
    'update_circle_dropdown',
    'on_circle_selection_changed',
    'calculate_circle_radius',
    'on_radius_slider_changed',
    'apply_radius_to_circle',
    'toggle_point_placement_mode',
    'toggle_post_branch_point_placement_mode',
    'start_new_post_branch_point_list_placement',
    'stop_post_branch_point_placement_mode',
    'setup_post_branch_point_count_observer',
    'update_post_branch_point_count_display',
    'update_post_branch_point_count_display_for_current_list',
    'on_post_branch_point_added',
    'toggle_branch_point_placement_mode',
    'start_new_branch_point_list_placement',
    'setup_branch_point_count_observer',
    'on_branch_point_added',
    'update_branch_point_count_display_for_current_list',
    'update_branch_point_count_display',
    'draw_circle_for_single_branch_point',
    'draw_circle_for_single_post_branch_point',
    'stop_branch_point_placement_mode',
    'stop_point_placement_mode',
    'setup_point_count_observer',
    'on_point_added',
    'update_point_count_display_for_current_list',
    'verify_f1_node_points',
    'apply_point_labels_to_list',
    'update_point_count_display',
    'ensure_point_placement_mode_active',
    'cleanup_point_placement_ui',
    'apply_only_transform_to_point_list',
    'start_new_point_list_placement',
    'remove_transforms_from_point_lists',
    'verify_pre_post_lesion_points_transform_free',
    'reapply_transforms_to_point_lists',
    'reapply_transforms_to_circles',
    'create_closed_curve_circle',
    'create_perpendicular_circle',
    'clear_branch_circles',
    'clear_circles_selective',
    'draw_circle_for_single_point',
    'apply_transform_to_circle',
    'draw_circle_for_branch_point',
    'draw_circle_for_post_branch_point',
    'create_tube_from_curve',
]

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
                logger.debug("Suppressed exception in process_markup_folder_and_create_tubes", exc_info=True)
        
        if post_lesion_file:
            try:
                post_lesion_markup = slicer.util.loadMarkups(post_lesion_file)
                if post_lesion_markup:
                    post_lesion_markup.SetName("Circle_post-lesion")
            except Exception as e:
                logger.debug("Suppressed exception in process_markup_folder_and_create_tubes", exc_info=True)
        
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
                logger.debug("Suppressed exception in process_markup_folder_and_create_tubes", exc_info=True)
        
        # Load transform file if found
        if transform_file:
            try:
                transform_node = slicer.util.loadTransform(transform_file)
                if transform_node:
                    slicer.modules.WorkflowTransform = transform_node
            except Exception as e:
                logger.debug("Suppressed exception in process_markup_folder_and_create_tubes", exc_info=True)
        
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

        
        logger.info(f"Created {len(created_tubes)} tubes total")
        
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
        logger.info(f"Loading markup file: {markup_file_path}")
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
        logger.info(f"Error loading markup file {markup_file_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_tube_from_two_points(start_point, end_point, tube_name, color):
    """
    Create a tube model from two points
    """
    try:
        logger.info(f"Creating tube '{tube_name}' from points {start_point} to {end_point}")
        
        # Create a curve markup with the two points
        curve_markup = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode")
        curve_markup.SetName(f"Curve_{tube_name}")
        logger.info(f"Created curve markup: {curve_markup.GetName()}")
        
        # Add the two points to the curve (points are already in world coordinates)
        curve_markup.AddControlPoint(start_point[0], start_point[1], start_point[2])
        curve_markup.AddControlPoint(end_point[0], end_point[1], end_point[2])
        logger.info(f"Added {curve_markup.GetNumberOfControlPoints()} points to curve")
        
        # Create tube from the curve
        tube_model = create_tube_from_curve_with_color(curve_markup, tube_name, color)
        logger.info(f"Tube creation result: {tube_model}")
        
        # Clean up the temporary curve
        slicer.mrmlScene.RemoveNode(curve_markup)
        logger.info(f"Cleaned up temporary curve")
        
        return tube_model
        
    except Exception as e:
        logger.info(f"Error creating tube from two points: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_tube_from_curve_with_color(curve_markup, tube_name, color):
    """
    Create a tube model from a curve markup with specified color
    """
    try:
        logger.info(f"Creating tube model from curve: {curve_markup.GetName()}")
        
        # Get the curve polydata
        curve_polydata = curve_markup.GetCurveWorld()
        if not curve_polydata:
            logger.info("Failed to get curve polydata")
            return None
            
        if curve_polydata.GetNumberOfPoints() < 2:
            logger.info(f"Curve has insufficient points: {curve_polydata.GetNumberOfPoints()}")
            return None
        
        logger.info(f"Curve has {curve_polydata.GetNumberOfPoints()} points")
        
        # Create tube filter
        import vtk
        tube_filter = vtk.vtkTubeFilter()
        tube_filter.SetInputData(curve_polydata)
        tube_filter.SetRadius(2.0)  # 2mm radius
        tube_filter.SetNumberOfSides(12)
        tube_filter.CappingOn()
        tube_filter.Update()
        logger.info("Tube filter created and updated")
        
        # Create model node
        tube_model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
        tube_model.SetName(tube_name)
        tube_model.SetAndObservePolyData(tube_filter.GetOutput())
        logger.info(f"Created model node: {tube_model.GetName()}")
        
        # Create display node and set color
        tube_model.CreateDefaultDisplayNodes()
        display_node = tube_model.GetDisplayNode()
        if display_node:
            display_node.SetColor(color)
            display_node.SetOpacity(0.8)
            display_node.SetVisibility(True)
            logger.info(f"Set display properties: color={color}, opacity=0.8")
        else:
            logger.info("Failed to get display node")
        
        return tube_model
        
    except Exception as e:
        logger.info(f"Error creating tube from curve: {e}")
        import traceback
        traceback.print_exc()
        return None
        slicer.util.errorDisplay(f"Error in markup file selection: {str(e)}")
        return None

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

def markup_workflow_after_crop():
    """
    Handle markup import workflow after crop completion.
    This is called when user chooses to import markup from the post-ROI dialog.
    """
    try:
        volume_node = volume.find_working_volume()
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
        # Use default threshold values instead of prompting user
        threshold_value_low, threshold_value_high = 290.0, 3071.0
        
        segmentation_node = segmentation.create_segmentation_from_threshold(volume_node, threshold_value_low, threshold_value_high)
        
        if segmentation_node:
            segmentation.show_segmentation_in_3d(segmentation_node)
            segmentation.load_into_segment_editor(segmentation_node, volume_node)
            
            # After threshold segmentation, add scissors and markup tools to left panel
            segmentation.add_post_threshold_tools_to_left_panel(segmentation_node, volume_node)
            
        else:
            pass
            
    except Exception as e:
        logger.debug("Suppressed exception in markup_workflow_after_crop", exc_info=True)

def continue_workflow_without_markup():
    """
    Continue the workflow with threshold segmentation only (no markup import).
    Called when user declines markup import from the post-ROI dialog.
    """
    try:
        volume_node = volume.find_working_volume()
        if not volume_node:
            slicer.util.errorDisplay("No volume found to continue workflow.")
            return
            
        # Set workflow flags for no markup
        slicer.modules.WorkflowUsingMarkup = False
        slicer.modules.WorkflowUsingImportedSegmentation = False
        
        # Continue with threshold segmentation workflow
        # Use default threshold values instead of prompting user
        threshold_value_low, threshold_value_high = 290.0, 3071.0
        
        segmentation_node = segmentation.create_segmentation_from_threshold(volume_node, threshold_value_low, threshold_value_high)
        
        if segmentation_node:
            segmentation.show_segmentation_in_3d(segmentation_node)
            segmentation.load_into_segment_editor(segmentation_node, volume_node)
            
            # No post-threshold tools for non-markup workflow
        else:
            pass
            
    except Exception as e:
        logger.debug("Suppressed exception in continue_workflow_without_markup", exc_info=True)

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

def start_markup_workflow():
    """
    Start the workflow with crop first, then markup import after ROI is set
    """
    try:
        # Start with crop workflow - markup dialog will appear after ROI is set
        volume.start_with_volume_crop()
    except Exception as e:
        pass
        # Fallback to the original function if needed
        segmentation.create_threshold_segment_with_markup_only()

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
        export_button.connect('clicked()', lambda: core.export_project_and_continue())
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
        masks_toggle_button.connect('clicked()', lambda: core.toggle_analysis_masks_visibility(masks_toggle_button))
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
        window_level_button.connect('clicked(bool)', lambda checked: ui.toggle_window_level_tool(checked, window_level_button))
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
        stenosis_button.connect('clicked()', lambda: core.create_stenosis_ratio_measurement())
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
        logger.debug("Suppressed exception in create_point_placement_controls", exc_info=True)

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
        logger.debug("Suppressed exception in update_circle_dropdown", exc_info=True)

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
        logger.debug("Suppressed exception in on_circle_selection_changed", exc_info=True)

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
        logger.debug("Suppressed exception in on_radius_slider_changed", exc_info=True)

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
        logger.debug("Suppressed exception in apply_radius_to_circle", exc_info=True)

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
        current_centerline_model, current_centerline_curve = centerline.get_current_centerline_for_placement()
        
        point_list = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        
        point_list.SetName("PB-1")
        
        # Store reference to the centerline that should be used for this point list
        # This ensures consistent positioning relative to the selected centerline
        if current_centerline_model:
            try:
                point_list.ReferenceCenterlineModel = current_centerline_model
            except:
                logger.debug("Suppressed exception in start_new_post_branch_point_list_placement", exc_info=True)
        if current_centerline_curve:
            try:
                point_list.ReferenceCenterlineCurve = current_centerline_curve
            except:
                logger.debug("Suppressed exception in start_new_post_branch_point_list_placement", exc_info=True)
        
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
        logger.debug("Suppressed exception in setup_post_branch_point_count_observer", exc_info=True)

def update_post_branch_point_count_display(point_list, count_label):
    """
    Update the count display for post branch points
    """
    try:
        if point_list and count_label:
            count = point_list.GetNumberOfControlPoints()
            count_label.setText(f"Post Branch Points: {count}")
    except Exception as e:
        logger.debug("Suppressed exception in update_post_branch_point_count_display", exc_info=True)

def update_post_branch_point_count_display_for_current_list(count_label):
    """
    Update post branch point count display for the current point list
    """
    try:
        current_list = getattr(slicer.modules, 'CurrentPostBranchAnalysisPointList', None)
        if current_list:
            update_post_branch_point_count_display(current_list, count_label)
    except Exception as e:
        logger.debug("Suppressed exception in update_post_branch_point_count_display_for_current_list", exc_info=True)

def on_post_branch_point_added(point_list, count_label):
    """
    Handle post branch point addition events
    """
    try:
        # Ensure this point list uses the current centerline reference
        centerline.ensure_point_placement_uses_current_centerline(point_list)
        
        # Update the display first
        update_post_branch_point_count_display(point_list, count_label)
        
        # Ensure point placement mode remains active for continued point placement
        ensure_point_placement_mode_active(point_list)
        
        # Get current point count for feedback
        point_count = point_list.GetNumberOfControlPoints()
        
        # Check if centerline exists using the current centerline reference
        centerline_exists = False
        centerline_model, centerline_curve = centerline.get_current_centerline_for_placement()
        
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
        logger.debug("Suppressed exception in on_post_branch_point_added", exc_info=True)

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
        current_centerline_model, current_centerline_curve = centerline.get_current_centerline_for_placement()
        
        point_list = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        
        point_list.SetName("B-1")
        
        # Store reference to the centerline that should be used for this point list
        # This ensures consistent positioning relative to the CPR centerline
        if current_centerline_model:
            try:
                point_list.ReferenceCenterlineModel = current_centerline_model
            except:
                logger.debug("Suppressed exception in start_new_branch_point_list_placement", exc_info=True)
        if current_centerline_curve:
            try:
                point_list.ReferenceCenterlineCurve = current_centerline_curve
            except:
                logger.debug("Suppressed exception in start_new_branch_point_list_placement", exc_info=True)
        
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
        logger.debug("Suppressed exception in setup_branch_point_count_observer", exc_info=True)

def on_branch_point_added(point_list, count_label):
    """
    Handle branch point addition events - update display and ensure placement mode stays active.
    (Exact copy of on_point_added with branch naming)
    """
    try:
        # Ensure this point list uses the current centerline reference
        centerline.ensure_point_placement_uses_current_centerline(point_list)
        
        # Update the display first
        update_branch_point_count_display_for_current_list(count_label)
        
        # Ensure point placement mode remains active for continued point placement
        ensure_point_placement_mode_active(point_list)
        
        # Get current point count for feedback
        point_count = point_list.GetNumberOfControlPoints()
        
        # Check if centerline exists using the current centerline reference
        centerline_exists = False
        centerline_model, centerline_curve = centerline.get_current_centerline_for_placement()
        
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
        logger.debug("Suppressed exception in on_branch_point_added", exc_info=True)

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
        logger.debug("Suppressed exception in update_branch_point_count_display_for_current_list", exc_info=True)

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
        logger.debug("Suppressed exception in update_branch_point_count_display", exc_info=True)

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
        logger.info("[DEBUG] === Stopping point placement mode ===")
        
        # Check current F-1 points before any cleanup
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for node in fiducial_nodes:
            if node.GetName() == "F-1":
                logger.info(f"[DEBUG] F-1 node before stop: {node.GetNumberOfControlPoints()} points")
                for i in range(node.GetNumberOfControlPoints()):
                    label = node.GetNthControlPointLabel(i)
                    logger.info(f"  Point {i}: {label}")
                break
        
        # SKIP cleanup entirely during stop - points should remain as placed
        logger.info("[DEBUG] Skipping cleanup during stop to preserve all placed points")
        
        # Keep cleanup disabled for now - will re-enable later if needed
        logger.info("[DEBUG] Keeping orphaned cleanup disabled after stopping point placement")
        
        # Check F-1 points after (skipped) cleanup
        for node in fiducial_nodes:
            if node.GetName() == "F-1":
                logger.info(f"[DEBUG] F-1 node after stop (no cleanup): {node.GetNumberOfControlPoints()} points")
                for i in range(node.GetNumberOfControlPoints()):
                    label = node.GetNthControlPointLabel(i)
                    logger.info(f"  Point {i}: {label}")
                break
        
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
                logger.debug("Suppressed exception in stop_point_placement_mode", exc_info=True)
        
        pass
        
    except Exception as e:
        logger.debug("Suppressed exception in stop_point_placement_mode", exc_info=True)

def setup_point_count_observer(point_list, count_label):
    """
    Set up observer to automatically update point count display and maintain point placement mode
    """
    try:
        if hasattr(point_list, 'PointCountObserver'):
            point_list.RemoveObserver(point_list.PointCountObserver)
        
        observer_id = point_list.AddObserver(point_list.PointModifiedEvent, 
                                           lambda caller, event: update_point_count_display(caller, count_label))
        point_list.PointCountObserver = observer_id
        
        observer_id2 = point_list.AddObserver(point_list.PointAddedEvent, 
                                            lambda caller, event: on_point_added(caller, count_label))
        point_list.PointAddObserver = observer_id2
        
        observer_id3 = point_list.AddObserver(point_list.PointRemovedEvent, 
                                            lambda caller, event: update_point_count_display(caller, count_label))
        point_list.PointRemoveObserver = observer_id3
        
    except Exception as e:
        logger.debug("Suppressed exception in setup_point_count_observer", exc_info=True)

def on_point_added(point_list, count_label):
    """
    Handle point addition events - update display and ensure placement mode stays active.
    Provides feedback for the enhanced workflow with multiple start/end slices.
    Ensures points are placed based on the most recently used centerline for CPR.
    """
    try:
        logger.info(f"[DEBUG] on_point_added called for node: '{point_list.GetName()}' ID: '{point_list.GetID()}'")
        logger.info(f"[DEBUG] Point count in this node: {point_list.GetNumberOfControlPoints()}")
        
        # Check if this is the expected F-1 node
        expected_f1 = getattr(slicer.modules, 'CurrentLesionAnalysisPointList', None)
        if expected_f1:
            logger.info(f"[DEBUG] Expected F-1 node: '{expected_f1.GetName()}' ID: '{expected_f1.GetID()}'")
            if point_list.GetID() != expected_f1.GetID():
                logger.info(f"[WARNING] Point added to different node than expected F-1!")
        
        # Ensure this point list uses the current centerline reference
        centerline.ensure_point_placement_uses_current_centerline(point_list)
        
        # Update the display first - use the specific point_list that was modified
        update_point_count_display(point_list, count_label)
        
        # Ensure point placement mode remains active for continued point placement
        ensure_point_placement_mode_active(point_list)
        
        # Debug: Verify what's in all F-1 nodes
        verify_f1_node_points()
        
        # Get current point count for feedback
        point_count = point_list.GetNumberOfControlPoints()
        
        # Check if centerline exists using the current centerline reference
        centerline_exists = False
        centerline_model, centerline_curve = centerline.get_current_centerline_for_placement()
        
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
        if point_count > 0 and centerline_exists:
            logger.info(f"[DEBUG] Creating circle for point {point_count - 1} (total points: {point_count})")
            success = draw_circle_for_single_point(point_count - 1)
            logger.info(f"[DEBUG] Circle creation success: {success}")
            
            # IMPORTANT: Re-ensure placement mode is active after drawing circle
            # The circle creation process might have interfered with the placement mode
            ensure_point_placement_mode_active(point_list)
        
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
        logger.debug("Suppressed exception in on_point_added", exc_info=True)

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
        logger.debug("Suppressed exception in update_point_count_display_for_current_list", exc_info=True)

def verify_f1_node_points():
    """
    Debug function to verify all points are in the F-1 node
    """
    try:
        logger.info("[DEBUG] === Verifying F-1 node points ===")
        
        # Find all F-1 nodes
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        f1_nodes = [node for node in fiducial_nodes if node.GetName() == "F-1"]
        
        logger.info(f"[DEBUG] Found {len(f1_nodes)} F-1 nodes")
        
        for i, node in enumerate(f1_nodes):
            logger.info(f"[DEBUG] F-1 node {i}: ID={node.GetID()}, Points={node.GetNumberOfControlPoints()}")
            for j in range(node.GetNumberOfControlPoints()):
                label = node.GetNthControlPointLabel(j)
                pos = [0, 0, 0]
                node.GetNthControlPointPosition(j, pos)
                logger.info(f"  Point {j}: label='{label}', pos=[{pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}]")
        
        # Check which node is currently active for placement
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            active_id = selectionNode.GetActivePlaceNodeID()
            logger.info(f"[DEBUG] Active place node ID: {active_id}")
            
        # Check stored reference
        expected_f1 = getattr(slicer.modules, 'CurrentLesionAnalysisPointList', None)
        if expected_f1:
            logger.info(f"[DEBUG] Stored CurrentLesionAnalysisPointList: ID={expected_f1.GetID()}, Points={expected_f1.GetNumberOfControlPoints()}")
        
        logger.info("[DEBUG] === End verification ===")
        
    except Exception as e:
        logger.info(f"[ERROR] Failed to verify F-1 points: {e}")

def apply_point_labels_to_list(point_list):
    """
    Apply proper labels to all points in the list - standalone helper function
    Updated to skip test-point and start directly with pre-lesion, post-lesion, then start/end slices
    """
    try:
        point_count = point_list.GetNumberOfControlPoints()
        
        for i in range(point_count):
            current_label = point_list.GetNthControlPointLabel(i)
            # Assign labels if empty or if they have default/generic labels
            if not current_label or current_label.startswith("F") or current_label.startswith("P-") or current_label.strip() == "":
                new_label = ""
                if i == 0:
                    new_label = "pre-lesion"
                    point_list.SetNthControlPointLabel(i, new_label)
                elif i == 1:
                    new_label = "post-lesion"
                    point_list.SetNthControlPointLabel(i, new_label)
                else:
                    # For points 2 and beyond, alternate between start and end slices
                    # Points 2, 4, 6, 8... are start slices (start-slice-1, start-slice-2, etc.)
                    # Points 3, 5, 7, 9... are end slices (end-slice-1, end-slice-2, etc.)
                    if (i - 2) % 2 == 0:  # Even offset from position 2 = start slice
                        start_slice_number = ((i - 2) // 2) + 1
                        new_label = f"start-slice-{start_slice_number}"
                        point_list.SetNthControlPointLabel(i, new_label)
                    else:  # Odd offset from position 2 = end slice
                        end_slice_number = ((i - 2) // 2) + 1
                        new_label = f"end-slice-{end_slice_number}"
                        point_list.SetNthControlPointLabel(i, new_label)
                
                logger.info(f"[DEBUG] Point {i}: '{current_label}' -> '{new_label}'")
        
    except Exception as e:
        logger.info(f"[ERROR] Failed to apply labels: {e}")
        pass

def update_point_count_display(point_list, count_label):
    """
    Update the point count display label and assign specific lesion analysis labels
    Supports multiple start and end slices with sequential numbering
    """
    try:
        point_count = point_list.GetNumberOfControlPoints()
        count_label.setText(f"Points placed: {point_count}")
        
        # Use the helper function to apply labels
        apply_point_labels_to_list(point_list)
        
    except Exception as e:
        logger.debug("Suppressed exception in update_point_count_display", exc_info=True)

def ensure_point_placement_mode_active(point_list):
    """
    Ensure that point placement mode remains active after each point is placed
    """
    try:
        # Check for multiple F-1 nodes - this might be the issue!
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        f1_nodes = [node for node in fiducial_nodes if node.GetName() == "F-1"]
        if len(f1_nodes) > 1:
            logger.info(f"[WARNING] Found {len(f1_nodes)} F-1 nodes! This might cause point placement issues.")
            for i, node in enumerate(f1_nodes):
                logger.info(f"  F-1 node {i}: ID={node.GetID()}, Points={node.GetNumberOfControlPoints()}")
        
        # Re-select the active point list in the selection node
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            current_active_id = selectionNode.GetActivePlaceNodeID()
            if current_active_id != point_list.GetID():
                logger.info(f"[DEBUG] Resetting active place node from '{current_active_id}' to '{point_list.GetID()}'")
                selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
                selectionNode.SetActivePlaceNodeID(point_list.GetID())

        # Ensure interaction mode is set to placement with continuous mode enabled
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            current_mode = interactionNode.GetCurrentInteractionMode()
            if current_mode != interactionNode.Place:
                logger.info(f"[DEBUG] Resetting interaction mode from {current_mode} to Place mode")
                interactionNode.SetCurrentInteractionMode(interactionNode.Place)
            
            # Enable continuous point placement mode (equivalent to "Place multiple control points" checkbox)
            persistence = interactionNode.GetPlaceModePersistence()
            if persistence != 1:
                logger.info(f"[DEBUG] Enabling place mode persistence (was {persistence})")
                interactionNode.SetPlaceModePersistence(1)
        
    except Exception as e:
        logger.info(f"[ERROR] Failed to ensure placement mode: {e}")
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
        logger.debug("Suppressed exception in cleanup_point_placement_ui", exc_info=True)

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
        centerline.clear_centerline_circles()
        
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
            current_centerline_model = centerline.find_recent_centerline_model()
            current_centerline_curve = centerline.find_recent_centerline_curve()
            
            # Store these for future reference
            if current_centerline_model:
                slicer.modules.WorkflowCenterlineModel = current_centerline_model
            if current_centerline_curve:
                slicer.modules.WorkflowCenterlineCurve = current_centerline_curve
        
        point_list = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        
        point_list.SetName("F-1")
        logger.info(f"[DEBUG] Created new F-1 node with ID: {point_list.GetID()}")
        
        # Store reference to the centerline that should be used for this point list
        # This ensures consistent positioning relative to the CPR centerline
        if current_centerline_model:
            try:
                point_list.ReferenceCenterlineModel = current_centerline_model
            except:
                logger.debug("Suppressed exception in start_new_point_list_placement", exc_info=True)
        if current_centerline_curve:
            try:
                point_list.ReferenceCenterlineCurve = current_centerline_curve
            except:
                logger.debug("Suppressed exception in start_new_point_list_placement", exc_info=True)
        
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
        
        # Disable orphaned cleanup during active point placement
        slicer.modules.DisableOrphanedCleanup = True
        logger.info("[DEBUG] Disabled orphaned cleanup for active point placement session")
        
        # Automatically apply the only transform to the point list if available
        apply_only_transform_to_point_list(point_list)
        
        slicer.modules.CurrentLesionAnalysisPointList = point_list
        logger.info(f"[DEBUG] Stored F-1 node as CurrentLesionAnalysisPointList")
        
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            selectionNode.SetActivePlaceNodeID(point_list.GetID())
            logger.info(f"[DEBUG] Set active place node ID to: {point_list.GetID()}")
        
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
            # Enable continuous point placement mode (equivalent to "Place multiple control points" checkbox)
            interactionNode.SetPlaceModePersistence(1)
            logger.info(f"[DEBUG] Set interaction mode to Place with persistence enabled")
        
        setup_point_count_observer(point_list, count_label)
        logger.info(f"[DEBUG] Set up observers for point list")
        
        update_point_count_display(point_list, count_label)
        
        logger.info(f"[DEBUG] Point placement setup complete for F-1 node: {point_list.GetID()}")
        pass
        pass
        pass
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not start point placement: {str(e)}")

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
            logger.debug("Suppressed exception in draw_circle_for_single_point", exc_info=True)
        
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
            logger.debug("Suppressed exception in draw_circle_for_single_point", exc_info=True)
        
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
        centerline_direction = centerline.calculate_centerline_direction(points, closest_centerline_idx)
        
        success = create_perpendicular_circle(circle_node, center_point, radius, centerline_direction)
        
        # Update the stored circle nodes list
        if not hasattr(slicer.modules, 'WorkflowCenterlineCircleNodes'):
            slicer.modules.WorkflowCenterlineCircleNodes = []
        
        if success:
            slicer.modules.WorkflowCenterlineCircleNodes.append(circle_node)
            
            try:
                # Hide only the specific control point, not the entire fiducial list
                f1_points.SetNthControlPointVisibility(point_index, False)
                # Keep the fiducial list itself visible for continued point placement
                display_node = f1_points.GetDisplayNode()
                if display_node:
                    display_node.SetPointLabelsVisibility(True)  # Keep labels visible
                    display_node.SetVisibility(True)  # Keep the fiducial list visible
                    # Only hide individual point glyphs if needed
                    display_node.SetGlyphScale(0.1)  # Make points very small instead of invisible

            except Exception as hide_error:
                logger.debug("Suppressed exception in draw_circle_for_single_point", exc_info=True)
        
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
        centerline_model, distance = centerline.find_nearest_centerline_to_point(pos)
        
        if not centerline_model:
            # Fallback: Try to find any centerline model
            try:
                centerline_model = slicer.util.getNode('Centerline model')
            except:
                logger.debug("Suppressed exception in draw_circle_for_branch_point", exc_info=True)
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
            logger.debug("Suppressed exception in draw_circle_for_branch_point", exc_info=True)
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
        direction = centerline.calculate_centerline_direction(points, closest_idx)
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
                logger.debug("Suppressed exception in draw_circle_for_branch_point", exc_info=True)
            
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
        centerline_model, distance = centerline.find_nearest_centerline_to_point(pos)
        
        if not centerline_model:
            # Fallback: Try to find any centerline model
            try:
                centerline_model = slicer.util.getNode('Centerline model')
            except:
                logger.debug("Suppressed exception in draw_circle_for_post_branch_point", exc_info=True)
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
            logger.debug("Suppressed exception in draw_circle_for_post_branch_point", exc_info=True)
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
        direction = centerline.calculate_centerline_direction(points, closest_idx)
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
                logger.debug("Suppressed exception in draw_circle_for_post_branch_point", exc_info=True)
            
            pass  # Created circle for {expected_label}

        # Update circle dropdown after creating a post-branch circle
        if success:
            update_circle_dropdown()

        return success
    except Exception as e:
        pass  # Error creating post branch circle: {str(e)}
        return False

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
