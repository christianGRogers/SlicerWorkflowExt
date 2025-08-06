import slicer
import qt
import vtk
import math
import numpy as np

"""
Slicer Guided Workflow for Vessel Centerline Extraction and CPR Visualization

Christian Rogers - So Lab - Lawson - UWO (2025)

I apoligise in advance for the code you are about to read but there was a bit of a time crunch
"""

def find_working_volume():
    """
    Find the appropriate volume to work with, preferring cropped and visible volumes
    """
    try:
        # Strategy 0: Check if we have a stored reference to the cropped volume
        if hasattr(slicer.modules, 'WorkflowCroppedVolume'):
            cropped_volume = slicer.modules.WorkflowCroppedVolume
            if cropped_volume and not cropped_volume.IsA('vtkObject'):  # Check if node still exists
                print(f"Using stored cropped volume for segmentation: {cropped_volume.GetName()}")
                return cropped_volume
            else:
                print("Stored cropped volume reference no longer valid")
        
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        
        if not volume_nodes:
            return None
        
        # Strategy 1: Look for cropped volumes (these are most recent and relevant)
        for volume in volume_nodes:
            if 'crop' in volume.GetName().lower():
                print(f"Found cropped volume for segmentation: {volume.GetName()}")
                return volume
        
        # Strategy 2: Look for visible volumes (not hidden)
        visible_volumes = []
        for volume in volume_nodes:
            display_node = volume.GetDisplayNode()
            if display_node and display_node.GetVisibility():
                visible_volumes.append(volume)
        
        if len(visible_volumes) == 1:
            print(f"Found single visible volume for segmentation: {visible_volumes[0].GetName()}")
            return visible_volumes[0]
        elif len(visible_volumes) > 1:
            # If multiple visible volumes, prefer non-straightened ones for initial segmentation
            for volume in visible_volumes:
                if 'straight' not in volume.GetName().lower():
                    print(f"Found visible non-straightened volume for segmentation: {volume.GetName()}")
                    return volume
            # Fallback to first visible volume
            print(f"Using first visible volume for segmentation: {visible_volumes[0].GetName()}")
            return visible_volumes[0]
        
        # Strategy 3: Check the active volume in slice views
        try:
            selection_node = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
            if selection_node:
                active_volume_id = selection_node.GetActiveVolumeID()
                if active_volume_id:
                    active_volume = slicer.mrmlScene.GetNodeByID(active_volume_id)
                    if active_volume and active_volume.IsA("vtkMRMLScalarVolumeNode"):
                        print(f"Found active volume for segmentation: {active_volume.GetName()}")
                        return active_volume
        except Exception as e:
            print(f"Could not check active volume: {e}")
        
        # Strategy 4: Fallback to first volume, but warn user
        first_volume = volume_nodes[0]
        print(f"Warning: Using first available volume for segmentation: {first_volume.GetName()}")
        print("Available volumes:")
        for i, volume in enumerate(volume_nodes):
            visibility_status = "visible" if (volume.GetDisplayNode() and volume.GetDisplayNode().GetVisibility()) else "hidden"
            print(f"  {i+1}. {volume.GetName()} ({visibility_status})")
        
        return first_volume
        
    except Exception as e:
        print(f"Error finding working volume: {e}")
        return slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")

def create_threshold_segment():
    """
    Main workflow function to create a threshold segment with default values
    """
    volume_node = find_working_volume()
    
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    
    threshold_values = prompt_for_threshold_range()
    if threshold_values is None:
        print("Threshold input cancelled by user")
        return
    
    threshold_value_low, threshold_value_high = threshold_values
    print(f"Using thresholds: {threshold_value_low} - {threshold_value_high}")
    
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
        print(f"Error in threshold dialog: {e}")
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
        print("Created new segmentation with Segment_1")
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
        
        print(f"Using existing Segment_1 in segmentation: {segmentation_node.GetName()}")
    segmentation_node.SetAttribute("WorkflowCreatedSegmentID", segment_id)
    print(f"Using segment with ID: {segment_id}")

    print("Applying threshold directly to Segment_1...")
    
    segment = segmentation.GetSegment(segment_id)
    if not segment:
        print("Error: Could not find segment to apply threshold")
        return segmentation_node
    try:
        volume_array = slicer.util.arrayFromVolume(volume_node)
        if threshold_value_high is not None:
            binary_mask = (volume_array >= threshold_value_low) & (volume_array <= threshold_value_high)
        else:
            binary_mask = volume_array >= threshold_value_low
        
        print(f"Created binary mask with {binary_mask.sum()} voxels in threshold range")
        
        temp_labelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        temp_labelmap.SetName("TempThresholdLabelmap")
        slicer.util.updateVolumeFromArray(temp_labelmap, binary_mask.astype('uint8'))
        temp_labelmap.CopyOrientation(volume_node)
        segment.GetRepresentation(slicer.vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName()).Initialize()
        segmentationLogic = slicer.modules.segmentations.logic()
        if segmentationLogic.ImportLabelmapToSegmentationNode(temp_labelmap, segmentation_node):
            print(f"Successfully applied threshold {threshold_value_low} - {threshold_value_high} to Segment_1")
        else:
            print("Warning: Failed to import threshold labelmap to segment")
        slicer.mrmlScene.RemoveNode(temp_labelmap)
    except Exception as e:
        print(f"Error applying threshold to Segment_1: {e}")
    #TODO remove exesive error handeling 
    # except Exception as e:
    #     print(f"Error applying threshold: {e}")

    #     try:
    #         print("Trying fallback method with Segment Editor...")

    #         segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
    #         slicer.mrmlScene.AddNode(segmentEditorNode)
    #         segmentEditorNode.SetAndObserveSegmentationNode(segmentation_node)
    #         segmentEditorNode.SetAndObserveSourceVolumeNode(volume_node)
    #         segmentEditorNode.SetSelectedSegmentID(segment_id)

    #         segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
    #         segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
    #         segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
    #         segmentEditorWidget.setActiveEffectByName("Threshold")
    #         effect = segmentEditorWidget.activeEffect()
            
    #         if effect:
    #             effect.setParameter("MinimumThreshold", str(threshold_value_low))
    #             effect.setParameter("MaximumThreshold", str(threshold_value_high))
    #             effect.self().onApply()
    #             print("Applied threshold using Segment Editor fallback method")
    #         slicer.mrmlScene.RemoveNode(segmentEditorNode)
            
    #     except Exception as e2:
    #         print(f"Fallback method also failed: {e2}")
    #         print("Segment_1 is ready - please apply threshold manually in Segment Editor")
    
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
        segmentation = segmentation_node.GetSegmentation()
        segment_ids = vtk.vtkStringArray()
        segmentation.GetSegmentIDs(segment_ids)
        
        if segment_ids.GetNumberOfValues() > 0:
            segment_id = segment_ids.GetValue(0)
            segment = segmentation.GetSegment(segment_id)
            segment.SetColor(1.0, 0.0, 0.0) 
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
    print("3D threshold segmentation created and displayed in 3D view!")

def load_into_segment_editor(segmentation_node, volume_node):
    """
    Load the segmentation into the Segment Editor module and ensure proper selection
    """
    slicer.util.selectModule("SegmentEditor")
    remove_segment_from_all_segmentations("Segment_1")
    slicer.app.processEvents()
    segment_editor_widget = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    segment_editor_widget.setSegmentationNode(segmentation_node)
    segment_editor_widget.setSourceVolumeNode(volume_node)
    slicer.app.processEvents()
    segmentation = segmentation_node.GetSegmentation()
    workflow_segment_id = segmentation_node.GetAttribute("WorkflowCreatedSegmentID")
    
    if workflow_segment_id:
        segment = segmentation.GetSegment(workflow_segment_id)
        if segment:
            segment_editor_widget.setCurrentSegmentID(workflow_segment_id)
            print(f"Selected workflow segment (Segment_1): {workflow_segment_id}")
            
            display_node = segmentation_node.GetDisplayNode()
            if display_node:
                display_node.SetAllSegmentsVisibility(True)
                display_node.SetSegmentVisibility(workflow_segment_id, True)
                display_node.SetVisibility2DOutline(True)
                display_node.SetVisibility2DFill(True)
        else:
            print(f"Warning: Workflow segment {workflow_segment_id} not found, falling back to first segment")
            segment_ids = vtk.vtkStringArray()
            segmentation.GetSegmentIDs(segment_ids)
            if segment_ids.GetNumberOfValues() > 0:
                fallback_segment_id = segment_ids.GetValue(0)
                segment_editor_widget.setCurrentSegmentID(fallback_segment_id)
    else:
        print("Warning: No workflow segment ID found, selecting first available segment")
        segment_ids = vtk.vtkStringArray()
        segmentation.GetSegmentIDs(segment_ids)
        if segment_ids.GetNumberOfValues() > 0:
            fallback_segment_id = segment_ids.GetValue(0)
            segment_editor_widget.setCurrentSegmentID(fallback_segment_id)
        layout_manager = slicer.app.layoutManager()
        for sliceViewName in ['Red', 'Yellow', 'Green']:
            slice_widget = layout_manager.sliceWidget(sliceViewName)
            if slice_widget:
                slice_view = slice_widget.sliceView()
                slice_view.forceRender()
    slicer.app.processEvents()
    select_scissors_tool(segment_editor_widget)
    add_continue_button_to_segment_editor()
    
    
    print("Segmentation loaded and selected in Segment Editor module with mask visibility enabled")
    print("Scissors tool selected - ready for cropping")

def select_scissors_tool(segment_editor_widget):
    """
    Select the Scissors tool in the Segment Editor
    """
    scissors_effect = segment_editor_widget.effectByName("Scissors")
    if scissors_effect:
        segment_editor_widget.setActiveEffect(scissors_effect)
        print("Scissors tool selected")
    else:
        print("Warning: Scissors tool not found")

def add_continue_button_to_segment_editor():
    """
    Add a prominent continue button directly to the Segment Editor interface
    """
    try:
        segment_editor_widget = slicer.modules.segmenteditor.widgetRepresentation().self().editor
        
        if hasattr(segment_editor_widget, 'parent'):
            segment_editor_main = segment_editor_widget.parent()
            continue_button = qt.QPushButton("FINISH CROPPING - CONTINUE")
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
            continue_button.connect('clicked()', lambda: on_continue_from_scissors())
            if hasattr(segment_editor_main, 'layout'):
                layout = segment_editor_main.layout()
                if layout:
                    # Insert the button at the top for prominence
                    layout.insertWidget(0, continue_button)
                    print("Added prominent green finish cropping button to Segment Editor")
                    slicer.modules.SegmentEditorContinueButton = continue_button
                    return
        
    except Exception as e:
        print(f"Error adding continue button to segment editor: {e}")

def on_continue_from_scissors():
    """
    Called when user clicks the continue button after using scissors
    """
    print("User clicked continue from scissors tool - opening centerline extraction module...")
    cleanup_workflow_ui()
    open_centerline_module()

def cleanup_continue_ui():
    """
    Clean up continue button UI elements
    """
    try:
        if hasattr(slicer.modules, 'SegmentEditorContinueButton'):
            button = slicer.modules.SegmentEditorContinueButton
            if button.parent():
                button.parent().layout().removeWidget(button)
            button.setParent(None)
            del slicer.modules.SegmentEditorContinueButton
            print("Cleaned up continue button")
        if hasattr(slicer.modules, 'SegmentEditorContinueDialog'):
            dialog = slicer.modules.SegmentEditorContinueDialog
            dialog.close()
            dialog.setParent(None)
            del slicer.modules.SegmentEditorContinueDialog
            print("Cleaned up continue dialog")
            
    except Exception as e:
        print(f"Error cleaning up continue UI: {e}")

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
                print("Error: No volume nodes found in scene")
                return None
            
            # If volume_name is specified, search for it by name
            if volume_name:
                for volume in volume_nodes:
                    if volume.GetName() == volume_name:
                        volume_node = volume
                        print(f"Found volume by name: {volume_name}")
                        break
                    elif volume_name.lower() in volume.GetName().lower():
                        volume_node = volume
                        print(f"Found volume by partial name match: {volume.GetName()}")
                        break
                
                if volume_node is None:
                    print(f"Warning: Volume '{volume_name}' not found. Available volumes:")
                    for i, vol in enumerate(volume_nodes):
                        print(f"  {i+1}. {vol.GetName()}")
                    print("Falling back to automatic selection...")
            
            # Fallback: Try to find cropped volume first, otherwise use first available
            if volume_node is None:
                for volume in volume_nodes:
                    if 'cropped' in volume.GetName().lower():
                        volume_node = volume
                        break
                
                if volume_node is None:
                    volume_node = volume_nodes[0]
        
        print(f"Creating mask segmentation '{mask_name}' from volume '{volume_node.GetName()}'")
        
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
            print(f"Set segment color to RGB: {rgb_color}")
        
        # Apply threshold to create binary mask
        volume_array = slicer.util.arrayFromVolume(volume_node)
        if threshold_high is not None:
            binary_mask = (volume_array >= threshold_low) & (volume_array <= threshold_high)
            print(f"Applied threshold range: {threshold_low} - {threshold_high}")
        else:
            binary_mask = volume_array >= threshold_low
            print(f"Applied threshold: >= {threshold_low}")
        
        print(f"Binary mask contains {binary_mask.sum()} voxels")
        
        # Convert binary mask to labelmap and import to segmentation
        temp_labelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        temp_labelmap.SetName(f"TempLabelmap_{mask_name}")
        slicer.util.updateVolumeFromArray(temp_labelmap, binary_mask.astype('uint8'))
        temp_labelmap.CopyOrientation(volume_node)
        
        # Import labelmap to segmentation
        segmentationLogic = slicer.modules.segmentations.logic()
        if segmentationLogic.ImportLabelmapToSegmentationNode(temp_labelmap, segmentation_node):
            print(f"Successfully created mask segmentation '{mask_name}'")
            
            # Clean up temporary labelmap
            slicer.mrmlScene.RemoveNode(temp_labelmap)
            
            # Ensure segmentation is NOT visible in 3D scene
            display_node = segmentation_node.GetDisplayNode()
            if display_node:
                display_node.SetVisibility3D(False)  # Disable 3D visibility
                display_node.SetVisibility(True)     # Keep 2D slice visibility
                print("Segmentation visibility: 2D slice view only (not in 3D scene)")
            
            return segmentation_node
        else:
            print(f"Error: Failed to import labelmap to segmentation")
            slicer.mrmlScene.RemoveNode(temp_labelmap)
            slicer.mrmlScene.RemoveNode(segmentation_node)
            return None
            
    except Exception as e:
        print(f"Error creating mask segmentation: {e}")
        return None

def create_analysis_masks(straightened_volumes):
    try:
        if not straightened_volumes:
            print("Warning: No straightened volumes provided for analysis masks")
            return
        
        straightened_volume = straightened_volumes[0]
        print(f"Creating analysis masks on straightened volume: {straightened_volume.GetName()}")
        
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
            print(f"Adding {mask_name} mask with threshold range {threshold_low}-{threshold_high} HU...")
            
            binary_mask = (volume_array >= threshold_low) & (volume_array <= threshold_high)
            voxel_count = binary_mask.sum()
            print(f"{mask_name} mask contains {voxel_count} voxels")
            
            temp_labelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
            temp_labelmap.SetName(f"TempLabelmap_{mask_name}")
            slicer.util.updateVolumeFromArray(temp_labelmap, binary_mask.astype('uint8'))
            temp_labelmap.CopyOrientation(straightened_volume)
            
            segmentationLogic = slicer.modules.segmentations.logic()
            if segmentationLogic.ImportLabelmapToSegmentationNode(temp_labelmap, segmentation_node):
                print(f"Successfully added {mask_name} to st-analysis segment")
            else:
                print(f"Failed to add {mask_name} to st-analysis segment")
            
            slicer.mrmlScene.RemoveNode(temp_labelmap)
        
        print(f"\nAnalysis masks created successfully!")
        print(f"Single segment: st-analysis in segmentation: {segmentation_node.GetName()}")
        print("Combined mask includes LAP, NCP, and STENOSIS thresholds")
        print("Mask is visible in 2D slice views but not in 3D scene.")
        
        slicer.modules.WorkflowAnalysisSegmentation = segmentation_node
        slicer.modules.WorkflowAnalysisSegments = [segment_id]
        
        return segmentation_node
            
    except Exception as e:
        print(f"Error creating analysis masks: {e}")
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
            print("Workflow dock widget cleaned up")
        if hasattr(slicer.modules, 'WorkflowDialog'):
            dialog = slicer.modules.WorkflowDialog
            dialog.close()
            dialog.setParent(None)
            del slicer.modules.WorkflowDialog
            print("Workflow dialog cleaned up")
        cleanup_point_placement_ui()
        cleanup_centerline_ui()
            
    except Exception as e:
        print(f"Error cleaning up workflow UI: {e}")

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
        print("Switched to Extract Centerline module")
        slicer.app.processEvents()
        
        remove_duplicate_centerline_buttons()
        setup_centerline_module()
        
    except Exception as e:
        print(f"Error opening centerline module: {e}")
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
                print(f"Found {len(duplicate_buttons)} duplicate centerline buttons, removing {len(duplicate_buttons) - 1}")
                for i, button in enumerate(duplicate_buttons):
                    if i > 0:
                        if button.parent() and hasattr(button.parent(), 'layout'):
                            button.parent().layout().removeWidget(button)
                        button.setParent(None)
                        button.deleteLater()
                        print(f"Removed duplicate centerline button #{i+1}")
            elif len(duplicate_buttons) == 1:
                print("Found 1 centerline button (no duplicates)")
            else:
                print("No large centerline buttons found")
                
    except Exception as e:
        print(f"Error removing duplicate centerline buttons: {e}")

def add_large_centerline_apply_button():
    """
    Add a large green Apply button directly to the Extract Centerline module GUI
    """
    try:
        if hasattr(slicer.modules, 'CenterlineLargeApplyButton'):
            existing_button = slicer.modules.CenterlineLargeApplyButton
            if existing_button and existing_button.parent():
                print("Large Apply button already exists in Extract Centerline module")
                return
        remove_duplicate_centerline_buttons()
        
        def create_large_button():
            try:
                if hasattr(slicer.modules, 'CenterlineLargeApplyButton'):
                    existing_button = slicer.modules.CenterlineLargeApplyButton
                    if existing_button and existing_button.parent():
                        print("Large Apply button already exists, skipping creation")
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
                            print("Apply button clicked - starting centerline extraction and monitoring...")
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
                print(f"Error creating large Apply button in Extract Centerline: {e}")
                return False
        success = create_large_button()
        
        if not success and not hasattr(slicer.modules, 'CenterlineLargeApplyButton'):
            def delayed_create():
                if not hasattr(slicer.modules, 'CenterlineLargeApplyButton'):
                    create_large_button()
            qt.QTimer.singleShot(1000, delayed_create)
            qt.QTimer.singleShot(3000, delayed_create)
            
    except Exception as e:
        print(f"Error adding large centerline Apply button: {e}")

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
            print("Cleaned up centerline large apply button")
            
    except Exception as e:
        print(f"Error cleaning up centerline UI: {e}")

def clean_centerline_buttons():
    """
    Utility function to manually clean up duplicate centerline buttons (can be called from console)
    """
    print("Manually cleaning up duplicate centerline buttons...")
    remove_duplicate_centerline_buttons()
    print("Cleanup complete. You can now add a new button if needed.")

def stop_centerline_monitoring_manually():
    """
    Utility function to manually stop centerline monitoring (can be called from console)
    """
    print("Manually stopping centerline monitoring...")
    stop_centerline_monitoring()
    print("Centerline monitoring stopped. You can now click the Apply button to start fresh monitoring.")

def check_monitoring_status():
    """
    Utility function to check if centerline monitoring is currently active
    """
    if hasattr(slicer.modules, 'CenterlineMonitorTimer'):
        timer = slicer.modules.CenterlineMonitorTimer
        if timer and timer.isActive():
            check_count = getattr(slicer.modules, 'CenterlineCheckCount', 0)
            start_time = getattr(slicer.modules, 'CenterlineMonitoringStartTime', 0)
            print(f"Centerline monitoring is ACTIVE - Check count: {check_count}, Started at: {start_time}")
            print("Monitoring will automatically detect when centerline extraction completes")
        else:
            print("Centerline monitoring timer exists but is NOT active")
    else:
        print("Centerline monitoring is NOT active")
        print("Monitoring will start automatically when you click the Extract Centerline button")

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
                    print(f"Setting up centerline extraction for: {workflow_segmentation.GetName()}")
                    workflow_segmentation.CreateClosedSurfaceRepresentation()
                    segmentation_set = False
                    for selector_name in ['inputSegmentationSelector', 'inputSurfaceSelector', 'segmentationSelector']:
                        if hasattr(centerline_module, 'ui') and hasattr(centerline_module.ui, selector_name):
                            getattr(centerline_module.ui, selector_name).setCurrentNode(workflow_segmentation)
                            print(f"Set input segmentation using {selector_name}")
                            segmentation_set = True
                            break
                    
                    if not segmentation_set:
                        print("Warning: Could not find segmentation selector in centerline module")
                    slicer.app.processEvents()
                    workflow_segment_id = workflow_segmentation.GetAttribute("WorkflowCreatedSegmentID")
                    if workflow_segment_id:
                        segmentation = workflow_segmentation.GetSegmentation()
                        segment = segmentation.GetSegment(workflow_segment_id)
                        if segment:
                            print(f"Found workflow segment: {segment.GetName()} (ID: {workflow_segment_id})")
                            segment.SetTag("Segmentation.Status", "completed")
                            segment_set = False
                            for selector_name in ['inputSegmentSelector', 'segmentSelector', 'inputSurfaceSegmentSelector']:
                                if hasattr(centerline_module.ui, selector_name):
                                    try:
                                        getattr(centerline_module.ui, selector_name).setCurrentSegmentID(workflow_segment_id)
                                        print(f"Selected segment using {selector_name}: {segment.GetName()}")
                                        segment_set = True
                                        break
                                    except Exception as e:
                                        print(f"Could not set segment using {selector_name}: {e}")
                            
                            if not segment_set:
                                print("Warning: Could not find segment selector, but segmentation is set")
                        else:
                            print(f"Warning: Could not find segment with ID {workflow_segment_id}")
                    else:
                        print("Warning: No workflow segment ID stored")
                        segmentation = workflow_segmentation.GetSegmentation()
                        segment_ids = vtk.vtkStringArray()
                        segmentation.GetSegmentIDs(segment_ids)
                        if segment_ids.GetNumberOfValues() > 0:
                            first_segment_id = segment_ids.GetValue(0)
                            first_segment = segmentation.GetSegment(first_segment_id)
                            if first_segment:
                                print(f"Using first available segment: {first_segment.GetName()}")
                                first_segment.SetTag("Segmentation.Status", "completed")
                    
                    try:
                        endpoint_point_list = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
                        endpoint_point_list.SetName("CenterlineEndpoints")
                        
                        endpoint_set = False
                        for endpoint_selector_attr in ['inputEndPointsSelector', 'endpointsSelector', 'inputFiducialSelector']:
                            if hasattr(centerline_module.ui, endpoint_selector_attr):
                                getattr(centerline_module.ui, endpoint_selector_attr).setCurrentNode(endpoint_point_list)
                                print(f"Created new endpoint point list using {endpoint_selector_attr}")
                                endpoint_set = True
                                break
                        
                        if not endpoint_set:
                            print("Warning: Could not find endpoint selector in centerline module")
                        
                        for create_new_attr in ['createNewEndpointsCheckBox', 'createNewPointListCheckBox']:
                            if hasattr(centerline_module.ui, create_new_attr):
                                getattr(centerline_module.ui, create_new_attr).setChecked(True)
                                print(f"Enabled create new point list using {create_new_attr}")
                                
                    except Exception as e:
                        print(f"Could not configure endpoint point list: {e}")
                    
                    try:
                        centerline_model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
                        centerline_model.SetName("CenterlineModel")
                        
                        model_set = False
                        for model_selector_attr in ['outputCenterlineModelSelector', 'centerlineModelSelector', 'outputModelSelector']:
                            if hasattr(centerline_module.ui, model_selector_attr):
                                getattr(centerline_module.ui, model_selector_attr).setCurrentNode(centerline_model)
                                print(f"Created new centerline model using {model_selector_attr}")
                                model_set = True
                                break
                        
                        if not model_set:
                            print("Warning: Could not find centerline model selector")
                        
                        for create_new_model_attr in ['createNewModelCheckBox', 'createNewCenterlineModelCheckBox']:
                            if hasattr(centerline_module.ui, create_new_model_attr):
                                getattr(centerline_module.ui, create_new_model_attr).setChecked(True)
                                print(f"Enabled create new model using {create_new_model_attr}")
                                
                    except Exception as e:
                        print(f"Could not configure centerline model: {e}")
                    try:
                        if hasattr(centerline_module.ui, 'outputTreeModelSelector'):
                            tree_model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
                            tree_model.SetName("CenterlineTree")
                            centerline_module.ui.outputTreeModelSelector.setCurrentNode(tree_model)
                            print("Created new model node for centerline tree")

                        if hasattr(centerline_module.ui, 'outputTreeCurveSelector'):
                            tree_curve = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode")
                            tree_curve.SetName("CenterlineCurve")
                            centerline_module.ui.outputTreeCurveSelector.setCurrentNode(tree_curve)
                            print("Created new curve node for centerline tree")
                        
                        for tree_model_attr in ['treeModelSelector']:
                            if hasattr(centerline_module.ui, tree_model_attr):
                                tree_model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
                                tree_model.SetName("CenterlineTree")
                                getattr(centerline_module.ui, tree_model_attr).setCurrentNode(tree_model)
                                print(f"Created new model node using {tree_model_attr}")
                        
                        for tree_curve_attr in ['outputCenterlineCurveSelector', 'centerlineCurveSelector', 'treeCurveSelector']:
                            if hasattr(centerline_module.ui, tree_curve_attr):
                                tree_curve = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode")
                                tree_curve.SetName("CenterlineCurve")
                                getattr(centerline_module.ui, tree_curve_attr).setCurrentNode(tree_curve)
                                print(f"Created new curve node using {tree_curve_attr}")
                                
                    except Exception as e:
                        print(f"Could not configure tree outputs (this is normal if UI elements have different names): {e}")
                    slicer.app.processEvents()
                    
        print("Extract Centerline module setup complete")
        add_large_centerline_apply_button()
        
        prompt_for_endpoints()
        
    except Exception as e:
        print(f"Error setting up centerline module: {e}")

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
                    print(f"Creating closed surface representation for segment: {segment.GetName()}")
                    segmentation_node.CreateClosedSurfaceRepresentation()
                
                print(f"Prepared segment for centerline extraction: {segment.GetName()}")
        segmentation_node.Modified()
        
        print("Surface preparation for centerline extraction complete")
        return True
        
    except Exception as e:
        print(f"Error preparing surface for centerline: {e}")
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
                    print(f"Marking for removal: {segment_name} (ID: {segment_id})")
        for segment_id in segments_to_remove:
            segmentation.RemoveSegment(segment_id)
            print(f"Removed default segment: {segment_id}")
        
        if segments_to_remove:
            print(f"Cleaned up {len(segments_to_remove)} default segment(s)")
        else:
            print("No default segments to remove")
            
    except Exception as e:
        print(f"Error removing default segments: {e}")

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
                    print(f"Removed segment '{segment_name}' from {seg_node.GetName()}")
                    removed_count += 1
                    break 
        
        if removed_count == 0:
            print(f"No segments named '{segment_name}' found in any segmentation")
        else:
            print(f"Removed {removed_count} segment(s) named '{segment_name}'")
            
    except Exception as e:
        print(f"Error removing segments: {e}")


def add_large_crop_apply_button():
    """
    Add a large green Apply button directly to the Crop Volume module GUI
    """
    try:
        if hasattr(slicer.modules, 'CropLargeApplyButton'):
            existing_button = slicer.modules.CropLargeApplyButton
            if existing_button and existing_button.parent():
                print("Large Apply button already exists in Crop Volume module")
                return
        
        def create_large_button():
            try:
                if hasattr(slicer.modules, 'CropLargeApplyButton'):
                    existing_button = slicer.modules.CropLargeApplyButton
                    if existing_button and existing_button.parent():
                        print("Large Apply button already exists, skipping creation")
                        return True
                
                print("Attempting to create large Apply button for Crop Volume...")
                crop_widget = slicer.modules.cropvolume.widgetRepresentation()
                print(f"Crop widget found: {crop_widget is not None}")
                print(f"Crop widget type: {type(crop_widget)}")
                print(f"Crop widget has 'self' attribute: {hasattr(crop_widget, 'self') if crop_widget else 'N/A'}")
                
                if crop_widget:
                    crop_module = None
                    
                    if hasattr(crop_widget, 'self'):
                        try:
                            crop_module = crop_widget.self()
                            print(f"Method 1 - Got crop module via 'self': {crop_module is not None}")
                        except Exception as e:
                            print(f"Method 1 failed: {e}")
                    
                    if not crop_module:
                        try:
                            crop_module = crop_widget
                            print(f"Method 2 - Using crop_widget directly: {crop_module is not None}")
                        except Exception as e:
                            print(f"Method 2 failed: {e}")

                    if not crop_module:
                        try:
                            crop_module = slicer.modules.cropvolume.createNewWidgetRepresentation()
                            print(f"Method 3 - Created new widget representation: {crop_module is not None}")
                        except Exception as e:
                            print(f"Method 3 failed: {e}")
                    
                    if crop_module:
                        print(f"Successfully got crop module: {type(crop_module)}")
                        
                        original_apply_button = None
                        print("Searching for Apply button in Crop Volume module...")
                        
                        apply_button_attrs = ['applyButton', 'ApplyButton', 'applyCropButton', 'cropApplyButton']
                        
                        if hasattr(crop_module, 'ui'):
                            print("Found 'ui' attribute, searching for Apply button...")
                            for attr_name in apply_button_attrs:
                                if hasattr(crop_module.ui, attr_name):
                                    original_apply_button = getattr(crop_module.ui, attr_name)
                                    print(f"Found Apply button using attribute: {attr_name}")
                                    break
                        else:
                            print("No 'ui' attribute found, trying direct attributes...")
                            for attr_name in apply_button_attrs:
                                if hasattr(crop_module, attr_name):
                                    original_apply_button = getattr(crop_module, attr_name)
                                    print(f"Found Apply button using direct attribute: {attr_name}")
                                    break

                        if not original_apply_button:
                            print("Direct attribute search failed, searching by button text...")
                            all_buttons = crop_widget.findChildren(qt.QPushButton)
                            print(f"Found {len(all_buttons)} buttons in crop widget")
                            for i, button in enumerate(all_buttons):
                                button_text = button.text if hasattr(button, 'text') else ""
                                print(f"Button {i}: '{button_text}'")
                                if button_text and 'apply' in button_text.lower():
                                    original_apply_button = button
                                    print(f"Found Apply button by text: '{button_text}'")
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
                        print("Warning: Original Apply button not found, creating standalone button")
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
                                    print("Applied crop using onApplyButton method")
                                elif hasattr(crop_module, 'apply'):
                                    crop_module.apply()
                                    print("Applied crop using apply method")
                                else:
                                    print("Could not find crop apply method - please use original Apply button")
                            except Exception as e:
                                print(f"Error applying crop: {e}")
                        
                        large_apply_button.connect('clicked()', trigger_crop_apply)
                        print("Connected large button to crop apply logic")
                    
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
                            print("Created layout and added large green Apply button to Crop Volume module")
                    else:
                        container_widgets = crop_widget.findChildren(qt.QWidget)
                        for widget in container_widgets:
                            if hasattr(widget, 'layout') and widget.layout() and widget.layout().count() > 0:
                                widget.layout().insertWidget(0, large_apply_button)
                                print("Added large green Apply button to Crop Volume container widget")
                                break
                        else:
                            print("Could not find suitable container in Crop Volume module")
                            return False
                    
                    slicer.modules.CropLargeApplyButton = large_apply_button
                    return True
                else:
                    if crop_widget:
                        try:
                            attrs = [attr for attr in dir(crop_widget) if not attr.startswith('_')]
                            print(f"  {attrs[:10]}...")  # Show first 10 attributes
                        except:
                            print("  Could not list attributes")
                    return False
                        
            except Exception as e:
                return False
        
        success = create_large_button()
        
        # If that didn't work, try again after delays
        if not success:
            qt.QTimer.singleShot(1000, create_large_button)
            qt.QTimer.singleShot(3000, create_large_button)
            print("Scheduling delayed large Apply button creation...")
            
    except Exception as e:
        print(f"Error adding large crop Apply button: {e}")

def add_large_cpr_apply_button():
    """
    Add a large green Apply button directly to the Curved Planar Reformat module GUI
    """
    try:
        if hasattr(slicer.modules, 'CPRLargeApplyButton'):
            existing_button = slicer.modules.CPRLargeApplyButton
            if existing_button and existing_button.parent():
                print("Large Apply button already exists in CPR module")
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
                            print(f"Method 1 failed: {e}")
                    
                    if not cpr_module:
                        try:
                            cpr_module = cpr_widget
                            print(f"Method 2 - Using cpr_widget directly: {cpr_module is not None}")
                        except Exception as e:
                            print(f"Method 2 failed: {e}")

                    if not cpr_module:
                        try:
                            cpr_module = slicer.modules.curvedplanarreformat.createNewWidgetRepresentation()
                            print(f"Method 3 - Created new widget representation: {cpr_module is not None}")
                        except Exception as e:
                            print(f"Method 3 failed: {e}")
                    
                    if cpr_module:
                        print(f"Successfully got CPR module: {type(cpr_module)}")
                        
                        original_apply_button = None
                        print("Searching for Apply button in CPR module...")
                        
                        apply_button_attrs = ['applyButton', 'ApplyButton', 'applyCPRButton', 'cprApplyButton']

                        if hasattr(cpr_module, 'ui'):
                            for attr_name in apply_button_attrs:
                                if hasattr(cpr_module.ui, attr_name):
                                    original_apply_button = getattr(cpr_module.ui, attr_name)
                                    print(f"Found Apply button using attribute: {attr_name}")
                                    break
                        else:

                            for attr_name in apply_button_attrs:
                                if hasattr(cpr_module, attr_name):
                                    original_apply_button = getattr(cpr_module, attr_name)
                                    print(f"Found Apply button using direct attribute: {attr_name}")
                                    break
                        
                        if not original_apply_button:
                            print("Direct attribute search failed, searching by button text...")
                            all_buttons = cpr_widget.findChildren(qt.QPushButton)
                            print(f"Found {len(all_buttons)} buttons in CPR widget")
                            for i, button in enumerate(all_buttons):
                                button_text = button.text if hasattr(button, 'text') else ""
                                print(f"Button {i}: '{button_text}'")
                                if button_text and 'apply' in button_text.lower():
                                    original_apply_button = button
                                    print(f"Found Apply button by text: '{button_text}'")
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
                            
                            large_apply_button.connect('clicked()', lambda: original_apply_button.click())
                            
                        else:
                            print("Warning: Original Apply button not found, creating standalone button")
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
                                    if hasattr(cpr_module, 'onApplyButton'):
                                        cpr_module.onApplyButton()
                                        print("Applied CPR using onApplyButton method")
                                    elif hasattr(cpr_module, 'apply'):
                                        cpr_module.apply()
                                        print("Applied CPR using apply method")
                                    else:
                                        print("Could not find CPR apply method - please use original Apply button")
                                except Exception as e:
                                    print(f"Error applying CPR: {e}")
                            
                            large_apply_button.connect('clicked()', trigger_cpr_apply)
                        
                        main_ui_widget = None
                        
                        if hasattr(cpr_module, 'ui') and hasattr(cpr_module.ui, 'widget'):
                            main_ui_widget = cpr_module.ui.widget
                        elif hasattr(cpr_module, 'widget'):
                            main_ui_widget = cpr_module.widget
                        elif hasattr(cpr_widget, 'widget'):
                            main_ui_widget = cpr_widget.widget
                        
                        if not main_ui_widget:
                            main_ui_widget = cpr_widget

                        if main_ui_widget and hasattr(main_ui_widget, 'layout'):
                            layout = main_ui_widget.layout()
                            if layout:
                                layout.insertWidget(0, large_apply_button)
                            else:
                                new_layout = qt.QVBoxLayout(main_ui_widget)
                                new_layout.insertWidget(0, large_apply_button)
                        else:
                            container_widgets = cpr_widget.findChildren(qt.QWidget)
                            for widget in container_widgets:
                                if hasattr(widget, 'layout') and widget.layout() and widget.layout().count() > 0:
                                    widget.layout().insertWidget(0, large_apply_button)
                                    break
                            else:
                                return False
                        
                        slicer.modules.CPRLargeApplyButton = large_apply_button
                        return True
                    else:
                        if cpr_widget:
                            try:
                                attrs = [attr for attr in dir(cpr_widget) if not attr.startswith('_')]
                                print(f"  {attrs[:10]}...")
                            except:
                                print("  Could not list attributes")
                        return False
                        
            except Exception as e:
                print(f"Error creating large Apply button: {e}")
                return False
        
        success = create_large_button()
        
        if not success:
            qt.QTimer.singleShot(1000, create_large_button)
            qt.QTimer.singleShot(3000, create_large_button)
            
    except Exception as e:
        print(f"Error adding large CPR Apply button: {e}")

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
                            print("Found Apply button via direct UI access")
                        elif hasattr(crop_module.ui, 'ApplyButton'):
                            apply_button = crop_module.ui.ApplyButton
                            print("Found Apply button via capitalized UI access")
                    
                    if not apply_button:
                        all_buttons = crop_widget.findChildren(qt.QPushButton)
                        print(f"Searching through {len(all_buttons)} buttons in crop module")
                        for button in all_buttons:
                            button_text = button.text if hasattr(button, 'text') else ""
                            button_name = button.objectName() if hasattr(button, 'objectName') else ""
                            print(f"  Button: '{button_text}' (name: '{button_name}')")
                            if 'apply' in button_text.lower() or 'apply' in button_name.lower():
                                apply_button = button
                                print(f"Found Apply button via search: '{button_text}'")
                                break
                    
                    if not apply_button:
                        main_window = slicer.util.mainWindow()
                        all_buttons = main_window.findChildren(qt.QPushButton)
                        for button in all_buttons:
                            button_text = button.text if hasattr(button, 'text') else ""
                            parent_name = button.parent().objectName() if button.parent() and hasattr(button.parent(), 'objectName') else ""
                            if 'apply' in button_text.lower() and ('crop' in parent_name.lower() or 'volume' in parent_name.lower()):
                                apply_button = button
                                print(f"Found Apply button via global search: '{button_text}' in parent '{parent_name}'")
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
                print(f"Error in apply_styling: {e}")
                return False
        
        success = apply_styling()
        
        if not success:
            timer = qt.QTimer()
            timer.singleShot(1000, apply_styling)  # Try again after 1 second
            
    except Exception as e:
        print(f"Error styling crop Apply button: {e}")

def start_with_volume_crop():
    """
    Start the workflow by opening the Volume Crop module and creating an ROI that fits the entire volume.
    """
    volume_node = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    slicer.util.selectModule("CropVolume")
    slicer.app.processEvents()
    
    # Hide all UI elements except the green Apply button
    hide_crop_volume_ui_elements()
    
    # Schedule additional UI hiding attempts in case the first one doesn't catch everything
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
    
    print(f"Created ROI covering entire volume: center={center}, size={size}")
    
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
    
    print("ROI created - adjust handles and click Apply to crop")
    
    slicer.app.processEvents()
    
    add_large_crop_apply_button()
    
    qt.QTimer.singleShot(2000, add_large_crop_apply_button)
    
    print("Large green Apply button creation scheduled for Crop Volume module")
    
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
    if slicer.modules.CropCheckCount > 60:
        slicer.modules.CropMonitorTimer.stop()
        slicer.modules.CropMonitorTimer.timeout.disconnect()
        del slicer.modules.CropMonitorTimer
        del slicer.modules.CropCheckCount
        slicer.util.errorDisplay("Cropping timed out. Please try again.")
        return
    volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
    for node in volume_nodes:
        if node is not original_volume_node and 'crop' in node.GetName().lower():
            slicer.modules.CropMonitorTimer.stop()
            slicer.modules.CropMonitorTimer.timeout.disconnect()
            del slicer.modules.CropMonitorTimer
            del slicer.modules.CropCheckCount
            
            # HIDE the original volume
            original_volume_node.SetDisplayVisibility(False)
            
            # Also hide it from slice views
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
            
            print(f"Hidden original volume: {original_volume_node.GetName()}")
            
            slicer.modules.WorkflowOriginalVolume = original_volume_node
            slicer.modules.WorkflowCroppedVolume = node
            
            set_cropped_volume_visible(node)
            
            roi_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsROINode')
            for roi_node in roi_nodes:
                if 'crop' in roi_node.GetName().lower():
                    slicer.mrmlScene.RemoveNode(roi_node)
                    print(f"Automatically deleted ROI: {roi_node.GetName()}")
            
            print(f"Cropped volume '{node.GetName()}' detected. Continuing workflow.")
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
        
        print(f"Cropped volume '{cropped_volume.GetName()}' set as active and visible in all slice views")
        return True
        
    except Exception as e:
        print(f"Error setting cropped volume visible: {e}")
        return False


def prompt_for_endpoints():
    """
    Simplified prompt for centerline extraction
    """
    try:
        print("Centerline extraction configured - place start and end points, then click the Extract Centerline button")
        print("Monitoring will start automatically when you click the Apply button")
        
    except Exception as e:
        print(f"Error prompting for endpoints: {e}")
        print("Please add start and end points using the Extract Centerline module, then click Apply")

def setup_centerline_completion_monitor():
    """
    Set up monitoring to detect when centerline extraction completes
    """
    try:
        stop_centerline_monitoring()

        timer = qt.QTimer()
        timer.timeout.connect(check_centerline_completion)
        timer.start(2000)
        slicer.modules.CenterlineMonitorTimer = timer
        slicer.modules.CenterlineCheckCount = 0
        slicer.modules.CenterlineMonitoringStartTime = slicer.app.applicationUptime()
        print("Started monitoring for centerline completion (triggered by Apply button)")
        
    except Exception as e:
        print(f"Error setting up centerline completion monitor: {e}")

def check_centerline_completion():
    """
    Check if centerline extraction has completed and switch to CPR module
    """
    try:
        if hasattr(slicer.modules, 'CenterlineCheckCount'):
            slicer.modules.CenterlineCheckCount += 1
            # if slicer.modules.CenterlineCheckCount > 60:
            #     stop_centerline_monitoring()
            #     print("Centerline monitoring timed out")
            #     return
            #depricate timeout
        
        monitoring_start_time = getattr(slicer.modules, 'CenterlineMonitoringStartTime', 0)
        
        centerline_model = find_recent_centerline_model(created_after=monitoring_start_time)
        centerline_curve = find_recent_centerline_curve(created_after=monitoring_start_time)
        
        model_has_data = False
        curve_has_data = False
        
        if centerline_model:
            polydata = centerline_model.GetPolyData()
            if polydata and polydata.GetNumberOfPoints() > 10:  # Require at least 10 points for a meaningful centerline
                model_has_data = True
                print(f"Found centerline model with {polydata.GetNumberOfPoints()} points")
        
        if centerline_curve:
            if centerline_curve.GetNumberOfControlPoints() > 5:  # Require at least 5 control points
                curve_has_data = True
                print(f"Found centerline curve with {centerline_curve.GetNumberOfControlPoints()} control points")
        
        if model_has_data or curve_has_data:
            print("Centerline extraction completed with sufficient data!")
            stop_centerline_monitoring()
            show_centerline_completion_dialog(centerline_model, centerline_curve)
        
    except Exception as e:
        print(f"Error checking centerline completion: {e}")

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
                        print(f"Found potential centerline model: {model.GetName()} with {polydata.GetNumberOfPoints()} points")
        
        if centerline_models:
            centerline_models.sort(key=lambda x: x.GetMTime(), reverse=True)
            return centerline_models[0]
        
        return None
        
    except Exception as e:
        print(f"Error finding centerline model: {e}")
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
        print(f"Error finding all centerline models: {e}")
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
                        print(f"Found potential centerline curve: {curve.GetName()} with {curve.GetNumberOfControlPoints()} control points")
        
        if centerline_curves:
            centerline_curves.sort(key=lambda x: x.GetMTime(), reverse=True)
            return centerline_curves[0]
        
        return None
        
    except Exception as e:
        print(f"Error finding centerline curve: {e}")
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
        print(f"Error finding all centerline curves: {e}")
        return []

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
            
        print("Stopped centerline monitoring")
        
    except Exception as e:
        print(f"Error stopping centerline monitoring: {e}")

def switch_to_cpr_module(centerline_model=None, centerline_curve=None):
    """
    Switch to Curved Planar Reformat module and configure it with the centerline
    """
    try:
        slicer.util.selectModule("CurvedPlanarReformat")
        print("Switched to Curved Planar Reformat module")
        slicer.app.processEvents()
        setup_cpr_module()
        create_point_list_and_prompt()
        
        qt.QTimer.singleShot(1000, add_large_cpr_apply_button)
        
        qt.QTimer.singleShot(3000, auto_apply_cpr)
        
        
    except Exception as e:
        print(f"Error switching to CPR module: {e}")
        slicer.util.errorDisplay(f"Could not open Curved Planar Reformat module: {str(e)}")

def auto_apply_cpr():
    """
    Automatically apply the CPR processing while keeping the module open for re-application
    """
    try:
        print("Auto-applying CPR...")
        
        cpr_widget = slicer.modules.curvedplanarreformat.widgetRepresentation()
        if not cpr_widget:
            print("Error: CPR module widget not found for auto-apply")
            return
        
        cpr_module = None
        if hasattr(cpr_widget, 'self'):
            cpr_module = cpr_widget.self()
        
        if not cpr_module:
            print("Error: Could not access CPR module for auto-apply")
            return
        
        apply_button = None
        
        if hasattr(cpr_module, 'ui') and hasattr(cpr_module.ui, 'applyButton'):
            apply_button = cpr_module.ui.applyButton
            print("Found original Apply button")
        
        if not apply_button and hasattr(slicer.modules, 'CPRLargeApplyButton'):
            apply_button = slicer.modules.CPRLargeApplyButton
            print("Found custom large Apply button")
        
        if not apply_button:
            all_buttons = cpr_widget.findChildren(qt.QPushButton)
            for button in all_buttons:
                if button.text.lower() == 'apply' and button.isEnabled():
                    apply_button = button
                    print("Found Apply button by searching widget")
                    break
        
        if apply_button and apply_button.isEnabled():
            print("Clicking Apply button to start CPR processing...")
            apply_button.click()
            
            setup_cpr_completion_monitor()
            
            
        else:
            if not apply_button:
                print("Could not find Apply button for auto-apply")
            else:
                print("Apply button found but not enabled - please check CPR configuration")
            print("You can manually click Apply when ready.")
            
    except Exception as e:
        print(f"Error in auto-apply CPR: {e}")
        print("You can manually click Apply to run CPR processing.")

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
            print("Started monitoring CPR completion...")
        
    except Exception as e:
        print(f"Error setting up CPR completion monitor: {e}")

def check_cpr_completion():
    """
    Check if CPR processing has completed
    """
    try:
        if hasattr(slicer.modules, 'CPRCheckCount'):
            slicer.modules.CPRCheckCount += 1
            # if slicer.modules.CPRCheckCount > 30:  # Stop after 60 seconds
            #     stop_cpr_monitoring()
            #     print("CPR monitoring timed out")
            #     return
        

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
            print("CPR processing completed successfully!")
            if straightened_volumes:
                print(f"  - Created straightened volume(s): {[v.GetName() for v in straightened_volumes]}")
            if projected_volumes:
                print(f"  - Created projected volume(s): {[v.GetName() for v in projected_volumes]}")
            
            # Create analysis masks on the straightened volume
            create_analysis_masks(straightened_volumes)
            
            stop_cpr_monitoring()
            
        
    except Exception as e:
        print(f"Error checking CPR completion: {e}")

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
            
        print("Stopped CPR monitoring")
        
    except Exception as e:
        print(f"Error stopping CPR monitoring: {e}")

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
                print(f"Found input volume for CPR: {input_volume.GetName()}")
                
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
                            print(f"Successfully set input volume using {input_selector_name}: {input_volume.GetName()}")
                            input_volume_set = True
                            break
                        else:
                            print(f"Failed to set input volume using {input_selector_name}")
                
                if not input_volume_set:
                    print("Warning: Could not find or set input volume selector")
                    print("Available UI attributes:", [attr for attr in dir(cpr_module.ui) if 'volume' in attr.lower() or 'input' in attr.lower()])
            else:
                print("Warning: Could not find appropriate input volume for CPR")
            
            # Configure centerline input - find the most recent centerline
            centerline_model = find_recent_centerline_model()  # Use default created_after=0 to find any existing model
            if centerline_model:
                print(f"Found centerline model for CPR: {centerline_model.GetName()}")
                
                # Set centerline selector
                centerline_set = False
                for centerline_selector_name in ['inputCenterlineSelector', 'centerlineSelector', 'curveSelector']:
                    if hasattr(cpr_module.ui, centerline_selector_name):
                        selector = getattr(cpr_module.ui, centerline_selector_name)
                        
                        # Force refresh the selector's node list
                        if hasattr(selector, 'updateMRMLFromWidget'):
                            selector.updateMRMLFromWidget()
                        
                        # Set the node
                        selector.setCurrentNode(centerline_model)
                        
                        # Force update again
                        slicer.app.processEvents()
                        
                        # Verify the selection took effect
                        if selector.currentNode() == centerline_model:
                            print(f"Successfully set centerline using {centerline_selector_name}: {centerline_model.GetName()}")
                            centerline_set = True
                            break
                        else:
                            print(f"Failed to set centerline using {centerline_selector_name}")
                
                if not centerline_set:
                    print("Warning: Could not find or set centerline selector")
                    print("Available UI attributes:", [attr for attr in dir(cpr_module.ui) if 'centerline' in attr.lower() or 'curve' in attr.lower()])
            else:
                print("Warning: Could not find centerline model for CPR")
            
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
                
                print(f"Created output volume: {output_volume.GetName()}")
                print(f"Created projected volume: {projected_volume.GetName()}")
                print(f"Created transform node: {transform_node.GetName()}")
                
                # Set the output selectors to the created nodes
                output_volume_set = False
                projected_volume_set = False
                transform_set = False
                
                # Set output straightened volume selector
                if hasattr(cpr_module.ui, 'outputStraightenedVolumeSelector'):
                    cpr_module.ui.outputStraightenedVolumeSelector.setCurrentNode(output_volume)
                    output_volume_set = True
                    print("Set output straightened volume selector")
                
                # Set output projected volume selector
                if hasattr(cpr_module.ui, 'outputProjectedVolumeSelector'):
                    cpr_module.ui.outputProjectedVolumeSelector.setCurrentNode(projected_volume)
                    projected_volume_set = True
                    print("Set output projected volume selector")
                
                # Set output transform selector
                if hasattr(cpr_module.ui, 'outputTransformToStraightenedVolumeSelector'):
                    cpr_module.ui.outputTransformToStraightenedVolumeSelector.setCurrentNode(transform_node)
                    transform_set = True
                    print("Set output transform selector")
                
                # Set resolution and thickness parameters
                if hasattr(cpr_module.ui, 'curveResolutionSliderWidget'):
                    cpr_module.ui.curveResolutionSliderWidget.setValue(0.6)
                    print("Set curve resolution to 0.6 mm")
                
                if hasattr(cpr_module.ui, 'sliceResolutionSliderWidget'):
                    cpr_module.ui.sliceResolutionSliderWidget.setValue(0.6)
                    print("Set slice resolution to 0.6 mm")
                
                # Legacy fallback for older parameter names
                if hasattr(cpr_module.ui, 'resolutionSpinBox'):
                    cpr_module.ui.resolutionSpinBox.setValue(0.6)
                    print("Set resolution to 0.6 mm")
                
                if hasattr(cpr_module.ui, 'thicknessSpinBox'):
                    cpr_module.ui.thicknessSpinBox.setValue(1.0)
                    print("Set thickness to 1.0 mm")
                
                # Final UI update
                slicer.app.processEvents()
                
                # Report setup status
                print("CPR module setup complete with automatic selector configuration:")
                if output_volume_set:
                    print("Output straightened volume selector set")
                else:
                    print("Output straightened volume selector not found - users should select manually")
                    
                if projected_volume_set:
                    print("Output projected volume selector set")
                else:
                    print("Output projected volume selector not found - users should select manually")
                    
                if transform_set:
                    print("Output transform selector set")
                else:
                    print("Output transform selector not found - users should select manually")
                
                if not input_volume:
                    print("Warning: No input volume detected - users should select one manually")
                if not centerline_model:
                    print("Warning: No centerline model detected - users should select one manually")
                
                print("CPR module configured - ready to apply!")
                    
            except Exception as e:
                print(f"Could not configure CPR output options: {e}")

            slicer.app.processEvents()
            
            add_large_cpr_apply_button()

        else:
            print("Warning: Could not access CPR module widget")
            
    except Exception as e:
        print(f"Error setting up CPR module: {e}")
            


def create_point_list_and_prompt():
    """
    Create the point placement control interface (without creating an initial point list)
    """
    try:
        create_point_placement_controls()
        

        
        return True
        
    except Exception as e:
        print(f"Error creating point placement controls: {e}")
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
            "Place points: 1:pre-lesion → 2:post-lesion → 3:start-slice → 4:end-slice"
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
        start_button.connect('clicked()', lambda: start_new_point_list_placement(count_label))
        layout.addWidget(start_button)
        
        clear_button = qt.QPushButton("Clear Points")
        clear_button.setStyleSheet("""
            QPushButton { 
                background-color: #ffc107; 
                color: #212529; 
                border: none; 
                padding: 12px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 13px;
            }
            QPushButton:hover { 
                background-color: #e0a800; 
            }
            QPushButton:pressed { 
                background-color: #d39e00; 
            }
        """)
        clear_button.connect('clicked()', lambda: clear_all_points_from_scene(count_label))
        layout.addWidget(clear_button)
        
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
        
        layout.addStretch()
        
        main_window.addDockWidget(qt.Qt.RightDockWidgetArea, dock_widget)
        dock_widget.show()
        
        slicer.modules.PointPlacementDockWidget = dock_widget
        slicer.modules.PointCountLabel = count_label
        
        print("Point placement controls created")
        
    except Exception as e:
        print(f"Error creating point placement controls: {e}")

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
        
        print("Point placement mode started with continuous placement enabled")
        print("Point placement started - place points: 1:pre-lesion, 2:post-lesion, 3:start-slice, 4:end-slice")
        
    except Exception as e:
        print(f"Error starting point placement: {e}")
        slicer.util.errorDisplay(f"Could not start point placement: {str(e)}")


def clear_all_points(point_list, count_label):
    """
    Clear all points from the point list
    """
    try:
        point_count = point_list.GetNumberOfControlPoints()
        if point_count == 0:
            print("No points to clear.")
            return
        
        result = slicer.util.confirmYesNoDisplay(f"Clear all {point_count} points?")
        if result:
            point_list.RemoveAllControlPoints()
            update_point_count_display(point_list, count_label)
            print("All points cleared")
        
    except Exception as e:
        print(f"Error clearing points: {e}")
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
        print(f"Error setting up point count observer: {e}")

def on_point_added(point_list, count_label):
    """
    Handle point addition events - update display and ensure placement mode stays active
    """
    try:
        # Update the display first
        update_point_count_display_for_current_list(count_label)
        
        # Ensure point placement mode remains active for continued point placement
        ensure_point_placement_mode_active(point_list)
        
        # Get current point count for feedback
        point_count = point_list.GetNumberOfControlPoints()
        
        # Provide feedback about what point was just placed
        point_names = ["pre-lesion", "post-lesion", "start-slice", "end-slice"]
        if point_count <= len(point_names):
            point_name = point_names[point_count - 1]
            print(f"Point {point_count} placed: {point_name} point")
            print(f"Point placement tool automatically re-selected for next point")
        else:
            print(f"Additional point {point_count} placed")
            print(f"Point placement tool automatically re-selected")
            
        # Provide next step guidance
        if point_count < 4:
            next_point = point_names[point_count] if point_count < len(point_names) else f"point {point_count + 1}"
            print(f"Ready to place {next_point}")
        elif point_count == 4:
            print("All 4 required points placed! Circles will be created automatically.")
        
    except Exception as e:
        print(f"Error handling point addition: {e}")

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
            
            # Check if we have all 4 points (pre-lesion, post-lesion, start-slice, end-slice) to create circles
            if current_point_list.GetNumberOfControlPoints() == 4:
                print("F-1 has all 4 points - creating circles at pre-lesion and post-lesion locations")
                draw_circles_on_centerline()
                
        else:
            fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
            total_points = 0
            
            for node in fiducial_nodes:
                node_name = node.GetName()
                if node_name == "F-1":
                    total_points += node.GetNumberOfControlPoints()
            
            count_label.setText(f"Total points: {total_points}")
        
    except Exception as e:
        print(f"Error updating point count display: {e}")

def update_point_count_display(point_list, count_label):
    """
    Update the point count display label and assign specific lesion analysis labels
    """
    try:
        point_count = point_list.GetNumberOfControlPoints()
        count_label.setText(f"Points placed: {point_count}")
        
        point_labels = [
            "pre-lesion",
            "post-lesion", 
            "start-slice",
            "end-slice"
        ]
        
        for i in range(point_count):
            current_label = point_list.GetNthControlPointLabel(i)
            if not current_label or current_label.startswith("F") or current_label.startswith("P-"): 
                if i < len(point_labels):
                    point_list.SetNthControlPointLabel(i, point_labels[i])
                else:
                    point_list.SetNthControlPointLabel(i, f"additional-{i+1-4}")
        
    except Exception as e:
        print(f"Error updating point count display: {e}")

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
                print("Point placement mode automatically re-enabled")
            
            # Enable continuous point placement mode (equivalent to "Place multiple control points" checkbox)
            interactionNode.SetPlaceModePersistence(1)
        
    except Exception as e:
        print(f"Error ensuring point placement mode active: {e}")

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
            print("Point placement dock widget cleaned up")
        
        if hasattr(slicer.modules, 'PointCountLabel'):
            del slicer.modules.PointCountLabel
            
    except Exception as e:
        print(f"Error cleaning up point placement UI: {e}")

def apply_only_transform_to_point_list(point_list):
    """
    Automatically find and apply the "Straightening transform" to the point list
    """
    try:
        # Get all transform nodes in the scene
        transform_nodes = slicer.util.getNodesByClass('vtkMRMLTransformNode')
        
        if len(transform_nodes) == 0:
            print("No transforms found in the scene - point list will use default coordinate system")
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
            print(f"Applied 'Straightening transform' to point list '{point_list.GetName()}'")
            return True
        else:
            # Straightening transform not found
            transform_names = [node.GetName() for node in transform_nodes]
            print(f"'Straightening transform' not found. Available transforms: {', '.join(transform_names)}")
            return False
            
    except Exception as e:
        print(f"Error applying transform to point list: {e}")
        return False

def start_new_point_list_placement(count_label):
    """
    Create a new point list and start placement mode with continuous placement enabled
    """
    try:
        point_list = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
        
        point_list.SetName("F-1")
        
        display_node = point_list.GetDisplayNode()
        if display_node:
            display_node.SetGlyphScale(3.0)  # Make points larger
            display_node.SetSelectedColor(1.0, 1.0, 0.0)  # Yellow when selected
            display_node.SetColor(1.0, 0.0, 0.0)  # Red when not selected
            display_node.SetTextScale(2.0)  # Larger text labels
            display_node.SetVisibility(True)
            display_node.SetPointLabelsVisibility(True)
        
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
        
        print(f"Created new point list: {point_list.GetName()}")
        print("Point placement mode started with continuous placement enabled")
        print("F-1 point list created - place points: 1:pre-lesion, 2:post-lesion, 3:start-slice, 4:end-slice")
        
    except Exception as e:
        print(f"Error starting new point list placement: {e}")
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
            print("No F-1 point list found to clear.")
            return
        
        node_count = len(lesion_analysis_nodes)
        total_points = sum(node.GetNumberOfControlPoints() for node in lesion_analysis_nodes)
        
        for node in lesion_analysis_nodes:
            slicer.mrmlScene.RemoveNode(node)
            print(f"Removed point list: {node.GetName()}")
        
        if hasattr(slicer.modules, 'CurrentLesionAnalysisPointList'):
            del slicer.modules.CurrentLesionAnalysisPointList

        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
        
        count_label.setText("Points placed: 0")
        print(f"Cleared {node_count} F-1 point(s) with {total_points} total points")
        
    except Exception as e:
        print(f"Error clearing points from scene: {e}")
        slicer.util.errorDisplay(f"Could not clear points: {str(e)}")

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
        
        print(f"Created stenosis line measurement: {line_node.GetName()}")
        print("Line measurement tool activated - place line measurement")
        
        return line_node
        
    except Exception as e:
        print(f"Error creating stenosis line measurements: {e}")
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
        print(f"Error counting stenosis measurements: {e}")
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
        
        print(f"Configured stenosis line node: {line_node.GetName()}")
        
    except Exception as e:
        print(f"Error configuring stenosis line node: {e}")

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
        
        print("Set up single stenosis line observer (waiting for 2 points)")
        
    except Exception as e:
        print(f"Error setting up single stenosis line observer: {e}")

def check_single_line_completion(line_node):
    """
    Check if the stenosis line has exactly 2 points and distance > 0mm before stopping tool
    """
    try:
        current_points = line_node.GetNumberOfControlPoints()
        print(f"Stenosis line now has {current_points} point(s)")
        
        # Only stop when we have exactly 2 points AND a measurable distance > 0mm
        if current_points == 2:
            # Get the measurement value and check if it's > 0mm
            measurement = line_node.GetMeasurement("length")
            if measurement:
                length_value = measurement.GetValue()
                print(f"Stenosis line distance: {length_value:.2f} mm")
                
                if length_value > 0.0:  # Only stop if distance is greater than 0mm
                    # Remove the observer to avoid multiple triggers
                    if hasattr(line_node, 'StenosisObserver'):
                        line_node.RemoveObserver(line_node.StenosisObserver)
                        delattr(line_node, 'StenosisObserver')
                    
                    print(f"Stenosis line complete: {length_value:.2f} mm")
                    
                    # Stop the measurement tool
                    stop_stenosis_measurement_tool()
                else:
                    print("Line has 2 points but distance is 0mm - waiting for proper line placement")
                    print("Make sure you click two distinct points to create a measurable distance")
            else:
                print("Line has 2 points but measurement not ready - waiting...")
        elif current_points == 1:
            print("First point placed - click second point to complete the line")
        
    except Exception as e:
        print(f"Error checking single line completion: {e}")



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
        
        print("Set up stenosis line sequence observer (waiting for 2 points)")
        
    except Exception as e:
        print(f"Error setting up stenosis line sequence observer: {e}")

def check_first_line_completion_carefully(first_line_node, second_line_node):
    """
    Check if the first stenosis line has exactly 2 points and a distance > 0mm before switching
    """
    try:
        current_points = first_line_node.GetNumberOfControlPoints()
        print(f"First line now has {current_points} point(s)")
        
        if current_points == 2:
            measurement = first_line_node.GetMeasurement("length")
            if measurement:
                length_value = measurement.GetValue()
                print(f"First line distance: {length_value:.2f} mm")
                
                if length_value > 0.0:
                    if hasattr(first_line_node, 'StenosisSequenceObserver'):
                        first_line_node.RemoveObserver(first_line_node.StenosisSequenceObserver)
                        delattr(first_line_node, 'StenosisSequenceObserver')
                    
                    print(f"First stenosis line complete: {length_value:.2f} mm")
                    print(f"DEBUG: About to trigger switch to second line: {second_line_node.GetName()}")

                    slicer.modules.StenosisSecondLineNode = second_line_node

                    try:
                        switch_to_second_stenosis_line(second_line_node)
                    except Exception as e:
                        print(f"Direct switch failed: {e}, trying with timer...")
                        qt.QTimer.singleShot(100, lambda: switch_to_second_stenosis_line(slicer.modules.StenosisSecondLineNode))
                else:
                    print("First line has 2 points but distance is 0mm - waiting for proper line placement")
                    print("Make sure you click two distinct points to create a measurable distance")
            else:
                print("First line has 2 points but measurement not ready - waiting...")
        elif current_points == 1:
            print("First point placed for first line - click second point to complete the line")
        
    except Exception as e:
        print(f"Error checking first line completion: {e}")

def switch_to_second_stenosis_line(second_line_node):
    """
    Automatically switch to the second line measurement
    """
    try:
        print(f"DEBUG: Attempting to switch to second line node: {second_line_node.GetName()}")
        print(f"DEBUG: Second line node ID: {second_line_node.GetID()}")
        print(f"DEBUG: Second line node valid: {second_line_node is not None}")
        
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            print("DEBUG: Setting active place node class and ID")
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsLineNode")
            selectionNode.SetActivePlaceNodeID(second_line_node.GetID())
            print(f"DEBUG: Active place node ID set to: {selectionNode.GetActivePlaceNodeID()}")
        else:
            print("ERROR: Selection node not found!")
        
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            print("DEBUG: Setting interaction mode to Place")
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
            interactionNode.SetPlaceModePersistence(1)
            print(f"DEBUG: Current interaction mode: {interactionNode.GetCurrentInteractionMode()}")
            print(f"DEBUG: Place mode persistence: {interactionNode.GetPlaceModePersistence()}")
        else:
            print("ERROR: Interaction node not found!")
        
        print(f"Automatically switched to second line: {second_line_node.GetName()}")
        print("Place second line measurement (green)")
        
        setup_second_line_completion_observer(second_line_node)
        
    except Exception as e:
        print(f"Error switching to second stenosis line: {e}")

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
        print(f"Error setting up second line completion observer: {e}")

def check_second_line_completion_carefully(second_line_node):
    """
    Check if second line has exactly 2 points and distance > 0mm before completing
    """
    try:
        current_points = second_line_node.GetNumberOfControlPoints()
        print(f"Second line now has {current_points} point(s)")
        if current_points == 2:
            measurement = second_line_node.GetMeasurement("length")
            if measurement:
                length_value = measurement.GetValue()
                print(f"Second line distance: {length_value:.2f} mm")
                
                if length_value > 0.0:  # Only complete if distance is greater than 0mm
                    # Remove the observer to avoid multiple triggers
                    if hasattr(second_line_node, 'StenosisSequenceObserver'):
                        second_line_node.RemoveObserver(second_line_node.StenosisSequenceObserver)
                        delattr(second_line_node, 'StenosisSequenceObserver')
                    
                    print(f"Second stenosis line complete: {length_value:.2f} mm")
                    print("Both stenosis lines completed successfully")
                    
                    # Stop the measurement tool automatically instead of showing dialog
                    stop_stenosis_measurement_tool()
                    print("Stenosis measurement pair completed - tool automatically stopped")
                else:
                    print("Second line has 2 points but distance is 0mm - waiting for proper line placement")
                    print("Make sure you click two distinct points to create a measurable distance")
            else:
                print("Second line has 2 points but measurement not ready - waiting...")
        elif current_points == 1:
            print("First point placed for second line - click second point to complete the line")
        
    except Exception as e:
        print(f"Error checking second line completion: {e}")



def on_continue_stenosis_measurements(dialog):
    """
    Continue with another stenosis measurement pair
    """
    try:
        dialog.close()
        dialog.setParent(None)
        
        print("User chose to continue stenosis measurements")
        print("Creating next stenosis measurement pair...")
        
        # Create another pair of stenosis measurements
        create_stenosis_ratio_measurement()
        
    except Exception as e:
        print(f"Error continuing stenosis measurements: {e}")

def on_stop_stenosis_measurements(dialog):
    """
    Stop stenosis measurements and close the measurement tool
    """
    try:
        dialog.close()
        dialog.setParent(None)
        
        print("User chose to stop stenosis measurements")
        stop_stenosis_measurement_tool()
        show_stenosis_measurements_summary()
        
    except Exception as e:
        print(f"Error stopping stenosis measurements: {e}")

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
        print(f"Error stopping stenosis measurement tool: {e}")

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
            print("=" * 50)
            print("STENOSIS MEASUREMENTS SUMMARY")
            print("=" * 50)
            for name, length in stenosis_lines:
                print(f"{name}: {length:.2f} mm")
            print("=" * 50)
            print(f"Total stenosis measurements: {len(stenosis_lines)}")
            
            # Show summary dialog
            summary_text = "Stenosis Measurements Complete!\n\n"
            summary_text += f"Created {len(stenosis_lines)} stenosis measurements:\n\n"
            for name, length in stenosis_lines:
                summary_text += f"• {name}: {length:.2f} mm\n"
            summary_text += f"\nAll measurements are available in the scene for analysis."
            
            slicer.util.infoDisplay(summary_text)
        else:
            print("No completed stenosis measurements found")
        
    except Exception as e:
        print(f"Error showing stenosis measurements summary: {e}")

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
            print("Set interaction mode to ViewTransform (normal mode)")
        
        # Clear any active placement node
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetActivePlaceNodeID(None)
            selectionNode.SetReferenceActivePlaceNodeClassName("")
            print("Cleared active placement node")
        
        # Process events to ensure UI is updated
        slicer.app.processEvents()
        
        print("All placement tools disabled - returned to normal interaction mode")
        
    except Exception as e:
        print(f"Error disabling placement tools: {e}")

def export_project_and_continue():
    """
    Save the Slicer project using normal save functionality and continue to workflow2.py
    """
    try:
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        lesion_analysis_nodes = []
        
        for node in fiducial_nodes:
            node_name = node.GetName()
            if node_name == "F-1":
                lesion_analysis_nodes.append(node)
        
        if not lesion_analysis_nodes:
            print("No F-1 point list found - saving project anyway")
        else:
            total_points = sum(node.GetNumberOfControlPoints() for node in lesion_analysis_nodes)
            print(f"Exporting project with {len(lesion_analysis_nodes)} F-1 point list(s) containing {total_points} points")

        # Remove transforms from point lists before saving
        if lesion_analysis_nodes:
            print("Preparing F-1 point lists for export...")
            debug_point_list_transforms()
            transforms_removed = remove_transforms_from_point_lists()
            
            if not transforms_removed:
                print("Forcing transform removal...")
                force_remove_all_transforms()
            
            print("Verifying pre and post lesion points are transform-free...")
            verification_passed = verify_pre_post_lesion_points_transform_free()
            
            if not verification_passed:
                print("ERROR: Pre and post lesion points still have transforms - attempting additional cleanup...")
                force_remove_all_transforms()
                verification_passed = verify_pre_post_lesion_points_transform_free()
                
            if verification_passed:
                print("Pre and post lesion points confirmed transform-free - ready for saving")
            else:
                print("Warning: Could not fully verify pre and post lesion points are transform-free")
            
            print("Transform removal verification complete")

        success = slicer.app.ioManager().openSaveDataDialog()
        
        if success:
            print("Project saved successfully")
            
            # Deselect placement tools and return to normal interaction mode
            print("Deselecting point placement tools...")
            disable_all_placement_tools()

            # Reapply transforms after saving
            if lesion_analysis_nodes:
                print("Reapplying transforms after save...")
                reapply_transforms_to_point_lists()
                reapply_transforms_to_circles()

            print("Project saved - starting centerline and tube mask creation workflow...")
            cleanup_all_workflow_ui()

            # Run workflow2 functionality directly
            try:
                print("Starting centerline and tube mask creation workflow...")
                create_centerline_and_tube_mask()
                
            except Exception as e:
                print(f"Error running workflow2 functionality: {e}")
                slicer.util.errorDisplay(f"Could not run workflow2 functionality: {str(e)}\n\nPlease check the console for details.")
            
        else:
            print("Save dialog was cancelled or failed")
            # Still deselect tools even if save was cancelled
            print("Deselecting point placement tools...")
            disable_all_placement_tools()
        
    except Exception as e:
        print(f"Error exporting project: {e}")
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
        
        print("All workflow UI elements cleaned up")
        
    except Exception as e:
        print(f"Error during UI cleanup: {e}")


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
        print(f"Error showing centerline completion dialog: {e}")
        switch_to_cpr_module(centerline_model, centerline_curve)

def on_retry_centerline(dialog):
    """
    Called when user chooses to retry centerline extraction
    """
    try:
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
        
        print("User chose to retry centerline extraction")
        
    except Exception as e:
        print(f"Error during centerline retry: {e}")

def on_continue_to_cpr(dialog, centerline_model=None, centerline_curve=None):
    """
    Called when user chooses to continue to CPR analysis
    """
    try:
        dialog.close()
        dialog.setParent(None)
        switch_to_cpr_module(centerline_model, centerline_curve)
        
        draw_circles_on_centerline()
        
        print("User chose to continue to CPR analysis")
        
    except Exception as e:
        print(f"Error continuing to CPR: {e}")

def on_add_more_centerlines(dialog):
    """
    Called when user chooses to add more centerlines
    """
    try:
        dialog.close()
        dialog.setParent(None)
        
        # Create a new centerline extraction setup for additional centerlines
        create_additional_centerline_setup()
        
        print("User chose to add more centerlines")
        
    except Exception as e:
        print(f"Error adding more centerlines: {e}")

def create_additional_centerline_setup():
    """
    Create new centerline model and curve nodes and set up Extract Centerline module for additional centerlines
    """
    try:
        # Ensure we're in the Extract Centerline module
        slicer.util.selectModule("ExtractCenterline")
        slicer.app.processEvents()
        
        centerline_widget = slicer.modules.extractcenterline.widgetRepresentation()
        if not centerline_widget:
            print("Error: Could not access Extract Centerline module")
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
        
        print(f"Created new centerline model: {new_centerline_model.GetName()}")
        print(f"Created new centerline curve: {new_centerline_curve.GetName()}")
        
        # Configure the Extract Centerline module with the new nodes
        setup_centerline_for_additional_extraction(centerline_module, new_centerline_model, new_centerline_curve)
        
        # Clear any existing endpoint markups and prepare for new placement
        clear_centerline_endpoints()
        
        # Set up automatic monitoring that waits for Apply button click
        setup_apply_button_monitoring()
        
        return new_centerline_model, new_centerline_curve
        
    except Exception as e:
        print(f"Error creating additional centerline setup: {e}")
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
        print(f"Error counting existing centerlines: {e}")
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
            print(f"Using existing segmentation: {workflow_segmentation.GetName()}")
            
            # Set input segmentation
            segmentation_set = False
            for selector_name in ['inputSegmentationSelector', 'inputSurfaceSelector', 'segmentationSelector']:
                if hasattr(centerline_module, 'ui') and hasattr(centerline_module.ui, selector_name):
                    getattr(centerline_module.ui, selector_name).setCurrentNode(workflow_segmentation)
                    print(f"Set input segmentation using {selector_name}")
                    segmentation_set = True
                    break
            
            if not segmentation_set:
                print("Warning: Could not find segmentation selector in centerline module")
                
        # Set output nodes for the new centerline
        try:
            # Set output centerline model
            if hasattr(centerline_module.ui, 'outputCenterlineModelSelector'):
                centerline_module.ui.outputCenterlineModelSelector.setCurrentNode(new_model)
                print(f"Set output centerline model: {new_model.GetName()}")
            elif hasattr(centerline_module.ui, 'centerlineModelSelector'):
                centerline_module.ui.centerlineModelSelector.setCurrentNode(new_model)
                print(f"Set centerline model: {new_model.GetName()}")
                
            # Set output centerline curve
            if hasattr(centerline_module.ui, 'outputCenterlineCurveSelector'):
                centerline_module.ui.outputCenterlineCurveSelector.setCurrentNode(new_curve)
                print(f"Set output centerline curve: {new_curve.GetName()}")
            elif hasattr(centerline_module.ui, 'centerlineCurveSelector'):
                centerline_module.ui.centerlineCurveSelector.setCurrentNode(new_curve)
                print(f"Set centerline curve: {new_curve.GetName()}")
                
        except Exception as e:
            print(f"Error setting output selectors: {e}")
        
        slicer.app.processEvents()
        
        # Add the large Apply button again
        add_large_centerline_apply_button()
        
        print("Extract Centerline module configured for additional centerline extraction")
        
    except Exception as e:
        print(f"Error setting up centerline for additional extraction: {e}")

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
                print(f"Cleared endpoints from: {node.GetName()}")
        
        if endpoints_cleared == 0:
            print("No endpoint nodes found to clear")
        else:
            print(f"Cleared endpoints from {endpoints_cleared} node(s)")
            
    except Exception as e:
        print(f"Error clearing centerline endpoints: {e}")

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
        
        print("Apply button monitoring started - waiting for user to click Apply")
        print(f"Baseline: {len(current_models)} models, {len(current_curves)} curves")
        
    except Exception as e:
        print(f"Error setting up Apply button monitoring: {e}")

def check_for_apply_button_click():
    """
    Check if Apply button has been clicked by monitoring for new centerline activity
    """
    try:
        # Increment check count and add timeout
        if hasattr(slicer.modules, 'ApplyMonitorCheckCount'):
            slicer.modules.ApplyMonitorCheckCount += 1
            
            # if slicer.modules.ApplyMonitorCheckCount > 300:  # 10 minutes (300 * 2 seconds)
            #     print("Apply button monitoring timed out after 10 minutes")
            #     stop_apply_button_monitoring()
            #     return
        
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
            print(f"New centerlines detected! Found {len(new_models)} new models, {len(new_curves)} new curves")
            for model in new_models:
                print(f"  New model: {model.GetName()}")
            for curve in new_curves:
                print(f"  New curve: {curve.GetName()}")
            
            # Stop Apply button monitoring
            stop_apply_button_monitoring()
            
            # Start centerline completion monitoring immediately
            setup_centerline_completion_monitor()
            return
        
        # Alternative detection: Look for recently modified nodes (processing activity)
        for model in current_models:
            if model.GetID() in existing_model_ids:
                # Check if this existing model was recently modified (processing activity)
                import time
                current_time = time.time() * 1000  # Convert to milliseconds
                time_since_modified = current_time - model.GetMTime()
                if time_since_modified < 5000:  # Modified within last 5 seconds
                    print(f"Recent processing activity detected on {model.GetName()}")
                    stop_apply_button_monitoring()
                    setup_centerline_completion_monitor()
                    return
        
    except Exception as e:
        print(f"Error checking for Apply button click: {e}")

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
            
        print("Apply button monitoring stopped")
        
    except Exception as e:
        print(f"Error stopping Apply button monitoring: {e}")

def start_centerline_monitoring_for_additional():
    """
    Manual function to start centerline monitoring for additional centerlines
    """
    try:
        setup_centerline_completion_monitor()
        print("Centerline completion monitoring started manually")
        print("The workflow will now automatically detect when centerline extraction completes")
        
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
        print(f"Error starting centerline monitoring: {e}")

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
                print("Centerline monitoring button cleaned up")
        
    except Exception as e:
        print(f"Error cleaning up centerline monitoring button: {e}")

def test_multiple_centerlines_functionality():
    """
    Test function to verify the multiple centerlines functionality works correctly
    """
    try:
        print("=== Testing Multiple Centerlines Functionality ===")
        
        # Test finding all centerlines
        all_models = find_all_centerline_models()
        all_curves = find_all_centerline_curves()
        
        print(f"Found {len(all_models)} centerline models")
        print(f"Found {len(all_curves)} centerline curves")
        
        # Test counting existing centerlines
        count = count_existing_centerlines()
        print(f"Existing centerline count: {count}")
        
        # Test getting summary
        summary = get_centerline_summary()
        print("Centerline summary:")
        print(summary)
        
        print("=== Multiple Centerlines Functionality Test Complete ===")
        
    except Exception as e:
        print(f"Error testing multiple centerlines functionality: {e}")

# Console helpers for testing
def test_add_centerlines():
    """Console helper to test adding centerlines"""
    create_additional_centerline_setup()

def show_centerline_info():
    """Console helper to show centerline information"""
    summary = get_centerline_summary()
    print(summary)

def stop_monitoring():
    """Console helper to stop centerline monitoring"""
    stop_centerline_monitoring()

def stop_apply_monitoring():
    """Console helper to stop Apply button monitoring"""
    stop_apply_button_monitoring()

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
            print(f"Removed centerline model: {model.GetName()}")
            removed_count += 1
        
        for curve in centerline_curves:
            slicer.mrmlScene.RemoveNode(curve)
            print(f"Removed centerline curve: {curve.GetName()}")
            removed_count += 1
        
        if removed_count > 0:
            print(f"Cleared {removed_count} existing centerline result(s)")
        else:
            print("No existing centerline results to clear")
            
    except Exception as e:
        print(f"Error clearing existing centerlines: {e}")

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
        print(f"Error getting centerline summary: {e}")
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
                    print(f"Processing F-1 point list with {point_count} points - ensuring pre and post lesion points are transform-free")
                    
                    # Check points 1 and 2 (pre-lesion and post-lesion)
                    for point_index in [0, 1]:  # 0 = pre-lesion, 1 = post-lesion
                        point_name = "pre-lesion" if point_index == 0 else "post-lesion"
                        
                        # Note: Individual points within a fiducial list cannot have separate transforms
                        # The transform applies to the entire point list, but we verify the points exist
                        if point_index < point_count:
                            point_pos = [0.0, 0.0, 0.0]
                            node.GetNthControlPointPosition(point_index, point_pos)
                            print(f"  - {point_name} point position: [{point_pos[0]:.2f}, {point_pos[1]:.2f}, {point_pos[2]:.2f}]")
                            pre_post_lesion_processed += 1
                        else:
                            print(f"  - Warning: {point_name} point not found (index {point_index})")
                
                # Remove transform from the entire point list
                if node.GetTransformNodeID():
                    transform_name = ""
                    transform_node = node.GetTransformNode()
                    if transform_node:
                        transform_name = transform_node.GetName()
                    
                    print(f"Removing transform '{transform_name}' from F-1 point list (affects all points including pre and post lesion)")
                    node.SetAndObserveTransformNodeID(None)
                    node.Modified()
                    removed_count += 1
                    print(f"✓ Transform removed from F-1 point list - pre and post lesion points are now in original coordinate space")
                else:
                    print("F-1 point list has no transform - pre and post lesion points already in original coordinate space")
        
        if removed_count > 0:
            slicer.app.processEvents()
            print(f"Successfully removed transforms from {removed_count} F-1 point list(s)")
            print(f"Processed {pre_post_lesion_processed} pre and post lesion points")
            print("All pre and post lesion points are now transform-free for saving")
            return True
        else:
            if pre_post_lesion_processed > 0:
                print(f"Verified {pre_post_lesion_processed} pre and post lesion points - no transforms to remove")
                return True
            else:
                print("No F-1 point lists or pre/post lesion points found")
                return False
            
    except Exception as e:
        print(f"Error removing transforms from point lists: {e}")
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
                    print(f"ERROR: F-1 point list still has transform '{transform_name}' applied!")
                    verification_passed = False
                    continue
                
                # Verify pre and post lesion points exist and report their positions
                point_count = node.GetNumberOfControlPoints()
                if point_count >= 2:
                    for point_index in [0, 1]:  # 0 = pre-lesion, 1 = post-lesion
                        point_name = "pre-lesion" if point_index == 0 else "post-lesion"
                        point_pos = [0.0, 0.0, 0.0]
                        node.GetNthControlPointPosition(point_index, point_pos)
                        print(f"{point_name} point at [{point_pos[0]:.2f}, {point_pos[1]:.2f}, {point_pos[2]:.2f}] - transform-free")
                        points_checked += 1
                else:
                    print(f"Warning: F-1 point list has only {point_count} points (expected at least 2 for pre/post lesion)")
                    verification_passed = False
        
        if points_checked == 0:
            print("Warning: No pre or post lesion points found for verification")
            return False
        
        if verification_passed:
            print(f"Verification passed: {points_checked} pre and post lesion points are transform-free")
            return True
        else:
            print(f"Verification failed: Issues found with pre and post lesion point transforms")
            return False
            
    except Exception as e:
        print(f"Error verifying pre and post lesion points: {e}")
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
            print("Warning: No 'Straightening transform' found to reapply")
            return False
        
        for node in fiducial_nodes:
            node_name = node.GetName()
            if node_name == "F-1":
                node.SetAndObserveTransformNodeID(straightening_transform.GetID())
                node.Modified()
                applied_count += 1
                print(f"Reapplied 'Straightening transform' to point list '{node.GetName()}'")
        
        if applied_count > 0:
            slicer.app.processEvents()
            print(f"Reapplied transforms to {applied_count} F-1 point list(s)")
            print("GUI updated to reflect transform reapplication")
            return True
        else:
            print("No F-1 point lists found to reapply transforms to")
            return False
            
    except Exception as e:
        print(f"Error reapplying transforms to point lists: {e}")
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
            print("Warning: No 'Straightening transform' found to reapply to circles")
            return False
        
        # Reapply to closed curve circles
        closed_curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsClosedCurveNode')
        for node in closed_curve_nodes:
            if 'circle' in node.GetName().lower():
                node.SetAndObserveTransformNodeID(straightening_transform.GetID())
                node.Modified()
                circles_reapplied += 1
                print(f"Reapplied transform to circle '{node.GetName()}'")
        
        # Reapply to regular curve circles
        curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsCurveNode')
        for node in curve_nodes:
            if 'circle' in node.GetName().lower():
                node.SetAndObserveTransformNodeID(straightening_transform.GetID())
                node.Modified()
                circles_reapplied += 1
                print(f"Reapplied transform to circle '{node.GetName()}'")
        
        if circles_reapplied > 0:
            slicer.app.processEvents()
            print(f"Reapplied transforms to {circles_reapplied} circle(s)")
            return True
        else:
            print("No circles found to reapply transforms to")
            return False
            
    except Exception as e:
        print(f"Error reapplying transforms to circles: {e}")
        return False

def debug_point_list_transforms():
    """
    Debug function to check transform status of all F-1 point lists
    """
    try:
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        f1_nodes = []
        
        for node in fiducial_nodes:
            if node.GetName() == "F-1":
                f1_nodes.append(node)
        
        if not f1_nodes:
            print("No F-1 point lists found in scene")
            return
        
        print(f"Found {len(f1_nodes)} F-1 point list(s):")
        for i, node in enumerate(f1_nodes):
            transform_id = node.GetTransformNodeID()
            if transform_id:
                transform_node = node.GetTransformNode()
                transform_name = transform_node.GetName() if transform_node else "Unknown"
                print(f"  F-1 #{i+1}: HAS TRANSFORM '{transform_name}' (ID: {transform_id})")
            else:
                print(f"  F-1 #{i+1}: NO TRANSFORM (None)")
                
    except Exception as e:
        print(f"Error in debug function: {e}")

def force_remove_all_transforms():
    """
    Force remove all transforms from F-1 point lists and update GUI
    """
    try:
        print("=== FORCE REMOVING ALL TRANSFORMS FROM F-1 POINT LISTS ===")
        
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        processed_count = 0
        
        for node in fiducial_nodes:
            if node.GetName() == "F-1":
                old_transform_id = node.GetTransformNodeID()
                
                node.SetAndObserveTransformNodeID(None)
                node.Modified()
                
                processed_count += 1
                
                if old_transform_id:
                    print(f"Removed transform from F-1 point list (was: {old_transform_id})")
                else:
                    print(f"Ensured F-1 point list has no transform (was already None)")
        
        slicer.app.processEvents()
        
        print(f"Processed {processed_count} F-1 point list(s)")
        print("=== CHECKING FINAL STATUS ===")
        debug_point_list_transforms()
        
        return processed_count > 0
        
    except Exception as e:
        print(f"Error in force remove function: {e}")
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
                        print(f"Set straightened volume visible in {slice_view_name} slice view")
            
            for slice_view_name in slice_view_names:
                slice_widget = layout_manager.sliceWidget(slice_view_name)
                if slice_widget:
                    slice_view = slice_widget.sliceView()
                    if slice_view:
                        slice_view.fitToWindow()
            
            selection_node = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
            if selection_node:
                selection_node.SetActiveVolumeID(straightened_volume.GetID())
            
            print(f"Straightened volume '{straightened_volume.GetName()}' set as visible and active")
            
        else:
            print("Warning: Could not find straightened volume to set as visible")
            
    except Exception as e:
        print(f"Error setting straightened volume visible: {e}")

def draw_circles_on_centerline():
    """
    Draw circles only at pre-lesion and post-lesion points (F-1 points 1 and 2)
    """
    try:
        f1_points = None
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for node in fiducial_nodes:
            if node.GetName() == "F-1":
                f1_points = node
                break
        
        if not f1_points:
            print("No F-1 point list found - circles will be created when points are placed")
            return False
        
        if f1_points.GetNumberOfControlPoints() < 2:
            print("Need at least 2 F-1 points (pre-lesion and post-lesion) to create circles")
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
                    print(f"Found centerline model: '{model.GetName()}'")
                    break
        
        if not centerline_model:
            for model in all_models:
                if 'tree' in model.GetName().lower():
                    centerline_model = model
                    print(f"Found tree model (assuming centerline): '{model.GetName()}'")
                    break
        
        if not centerline_model:
            print("Warning: Could not find centerline model - cannot create circles")
            return False
        
        points = slicer.util.arrayFromModelPoints(centerline_model)
        radii = slicer.util.arrayFromModelPointData(centerline_model, 'Radius')
        
        if points is None or len(points) == 0:
            print("Warning: No points found in centerline model")
            return False
            
        if radii is None or len(radii) == 0:
            print("Warning: No radius data found in centerline model")
            return False
        
        clear_centerline_circles()
        
        circles_created = 0
        circle_nodes = []
        
        lesion_points = []
        for i in range(min(2, f1_points.GetNumberOfControlPoints())):
            point = [0.0, 0.0, 0.0]
            f1_points.GetNthControlPointPosition(i, point)
            lesion_points.append(point)
        
        for i, lesion_point in enumerate(lesion_points):
            min_distance = float('inf')
            closest_centerline_idx = 0
            
            for j, centerline_point in enumerate(points):
                distance = ((lesion_point[0] - centerline_point[0])**2 + 
                           (lesion_point[1] - centerline_point[1])**2 + 
                           (lesion_point[2] - centerline_point[2])**2)**0.5
                
                if distance < min_distance:
                    min_distance = distance
                    closest_centerline_idx = j
            
            center_point = points[closest_centerline_idx]
            radius = radii[closest_centerline_idx] if closest_centerline_idx < len(radii) else 1.0;
            
            circle_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsClosedCurveNode")
            point_name = "pre-lesion" if i == 0 else "post-lesion"
            circle_node.SetName(f"Circle_{point_name}")
            

            display_node = circle_node.GetDisplayNode()
            if display_node:
                if i == 0:
                    display_node.SetColor(0.0, 1.0, 0.0)
                    display_node.SetSelectedColor(0.0, 1.0, 0.0)  # Bright green
                else:
                    display_node.SetColor(1.0, 0.0, 0.0)
                    display_node.SetSelectedColor(1.0, 0.0, 0.0)  # Bright red
                
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
                print(f"Created {point_name} circle at centerline point {closest_centerline_idx}")
        
        slicer.modules.WorkflowCenterlineCircleNodes = circle_nodes
        
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode and f1_points:
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            selectionNode.SetActivePlaceNodeID(f1_points.GetID())
        
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
        
        return True
        
    except Exception as e:
        print(f"Error drawing circles on centerline: {e}")
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
        print(f"Created closed curve circle with {num_points} points, radius {radius:.2f} at Z={center_point[2]:.2f}")
        return True
        
    except Exception as e:
        print(f"Error creating closed curve circle: {e}")
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
        
        print(f"Calculated centerline direction at point {point_index}: {direction}")
        return direction
        
    except Exception as e:
        print(f"Error calculating centerline direction: {e}")
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
        
        print(f"Created perpendicular circle with {num_points} points, radius {radius:.2f}")
        print(f"  Direction vector: {direction}")
        print(f"  Perpendicular vectors: {perp1}, {perp2}")
        return True
        
    except Exception as e:
        print(f"Error creating perpendicular circle: {e}")
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
        print(f"Error creating axial circle points: {e}")
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
            print(f"Cleared {removed_count} centerline circle markup(s)")
        else:
            print("No centerline circles found to clear")
            
        return removed_count > 0
        
    except Exception as e:
        print(f"Error clearing centerline circles: {e}")
        return False

def apply_transform_to_circle(circle_node):
    """
    Apply the same transform as the F-1 point list to the circle node
    """
    try:
        transform_nodes = slicer.util.getNodesByClass('vtkMRMLTransformNode')
        
        if len(transform_nodes) == 0:
            print("No transforms found in the scene - circle will use default coordinate system")
            return False
        straightening_transform = None
        for transform_node in transform_nodes:
            if transform_node.GetName() == "Straightening transform":
                straightening_transform = transform_node
                break
        
        if straightening_transform:
            circle_node.SetAndObserveTransformNodeID(straightening_transform.GetID())
            print(f"Applied 'Straightening transform' to circle '{circle_node.GetName()}'")
            return True
        else:
            transform_names = [node.GetName() for node in transform_nodes]
            print(f"'Straightening transform' not found for circle. Available transforms: {', '.join(transform_names)}")
            return False
            
    except Exception as e:
        print(f"Error applying transform to circle: {e}")
        return False

def apply_transform_to_node(node, node_description="node"):
    """
    Apply the straightening transform to any node
    """
    try:
        transform_nodes = slicer.util.getNodesByClass('vtkMRMLTransformNode')
        
        if len(transform_nodes) == 0:
            print(f"No transforms found in the scene - {node_description} will use default coordinate system")
            return False
        
        straightening_transform = None
        for transform_node in transform_nodes:
            if transform_node.GetName() == "Straightening transform":
                straightening_transform = transform_node
                break
        
        if straightening_transform:
            node.SetAndObserveTransformNodeID(straightening_transform.GetID())
            print(f"Applied 'Straightening transform' to {node_description} '{node.GetName()}'")
            return True
        else:
            transform_names = [node.GetName() for node in transform_nodes]
            print(f"'Straightening transform' not found for {node_description}. Available transforms: {', '.join(transform_names)}")
            return False
            
    except Exception as e:
        print(f"Error applying transform to {node_description}: {e}")
        return False

# ===============================================================================
# WORKFLOW2 FUNCTIONS - Centerline and Tube Mask Creation
# ===============================================================================

def create_centerline_and_tube_mask():
    """
    Creates a centerline curve and tube mask from points 3-4 of the F-1 point list.
    """
    
    f1_points = slicer.util.getNode('F-1')
    if not f1_points:
        print("Error: F-1 point list not found")
        return

    if f1_points.GetNumberOfControlPoints() < 4:
        print(f"Error: F-1 has only {f1_points.GetNumberOfControlPoints()} points. Need at least 4.")
        return
    
    print(f"Found F-1 with {f1_points.GetNumberOfControlPoints()} points")
    
    centerline_points = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
    centerline_points.SetName('CenterlinePoints')
    
    point3_pos = [0, 0, 0]
    f1_points.GetNthControlPointPosition(2, point3_pos)
    centerline_points.AddControlPoint(point3_pos)
    
    point4_pos = [0, 0, 0]
    f1_points.GetNthControlPointPosition(3, point4_pos)
    centerline_points.AddControlPoint(point4_pos)
    
    print(f"Created centerline points: Point 3 at {point3_pos}, Point 4 at {point4_pos}")
    
    centerline_curve = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsCurveNode')
    centerline_curve.SetName('CenterlineCurve')

    centerline_curve.AddControlPoint(point3_pos)
    centerline_curve.AddControlPoint(point4_pos)
    
    centerline_curve.SetCurveTypeToLinear()
    
    # NOTE: Transform is NOT applied to centerline curve - it should remain in original coordinate system
    # for accurate tube mask creation and analysis
    
    print("Created centerline curve")
    

    curve_points = centerline_curve.GetCurvePointsWorld()
    
    if not curve_points or curve_points.GetNumberOfPoints() == 0:
        print("Error: Could not get curve points")
        return
    
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
    tube_model.SetName('TubeMask')
    tube_model.SetAndObservePolyData(tube_filter.GetOutput())
    
    # NOTE: Transform is NOT applied to tube model - it should remain in original coordinate system
    # for accurate segmentation and density analysis
    
    tube_display = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelDisplayNode')
    tube_display.SetColor(1.0, 0.0, 0.0)
    tube_display.SetOpacity(0.5)
    tube_model.SetAndObserveDisplayNodeID(tube_display.GetID())
    
    print("Created tube mask model")
    
    stenosis_segmentation = create_segmentation_from_tube(tube_model)
    
    add_cropped_volume_to_3d_scene()
    
    if stenosis_segmentation:
        show_segment_statistics(stenosis_segmentation)
    
    print("Workflow completed successfully!")

def create_segmentation_from_tube(tube_model):
    """
    Convert the tube model to a segmentation for use as a mask.
    """
    try:
        segmentation_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
        segmentation_node.SetName('TubeMaskSegmentation')
        
        slicer.modules.segmentations.logic().ImportModelToSegmentationNode(tube_model, segmentation_node)
        
        segmentation = segmentation_node.GetSegmentation()
        segment_ids = vtk.vtkStringArray()
        segmentation.GetSegmentIDs(segment_ids)
        
        if segment_ids.GetNumberOfValues() > 0:
            segment_id = segment_ids.GetValue(0)
            segment = segmentation.GetSegment(segment_id)
            segment.SetName('TubeMask')
            segment.SetColor(1.0, 0.0, 0.0)  
        
        print("Created tube mask segmentation")
        return segmentation_node
        
    except Exception as e:
        print(f"Warning: Could not create segmentation from tube model: {str(e)}")
        return None

def set_tube_radius(radius):
    """
    Helper function to set a custom tube radius.
    """
    global tube_radius
    tube_radius = radius
    print(f"Tube radius set to {radius}")

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
            print("Warning: Could not find cropped volume to add to 3D scene")
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
                print(f"Applied preset: {presetName}")
            except:
                try:
                    presetName = "CT-Cardiac"
                    volumeRenderingLogic.ApplyVolumeRenderingDisplayPreset(displayNode, presetName)
                    print(f"Applied preset: {presetName}")
                except:
                    print("Using default volume rendering settings")
            
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
            
            print(f"Added cropped volume '{cropped_volume.GetName()}' to 3D scene with raycast rendering")
        else:
            print("Warning: Could not create volume rendering display node")
            
    except Exception as e:
        print(f"Error adding cropped volume to 3D scene: {str(e)}")

def show_segment_statistics(stenosis_segmentation):
    """
    Open the Segment Statistics module to display density statistics for the stenosis mask.
    """
    try:
        if not stenosis_segmentation:
            print("Warning: No stenosis segmentation provided for statistics")
            return
        
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        analysis_volume = None
        
        for volume in volume_nodes:
            if 'cropped' in volume.GetName().lower():
                analysis_volume = volume
                print(f"Found cropped volume for analysis: {volume.GetName()}")
                break
        
        if not analysis_volume:
            print("Warning: No volume with 'cropped' in name found for density analysis")
            print("Available volumes:")
            for volume in volume_nodes:
                print(f"  - {volume.GetName()}")
            return
        
        slicer.util.selectModule('SegmentStatistics')
        
        try:
            segmentStatisticsWidget = slicer.modules.segmentstatistics.widgetRepresentation().self()
            
            slicer.app.processEvents()
            
            if hasattr(segmentStatisticsWidget, 'segmentationSelector'):
                segmentStatisticsWidget.segmentationSelector.setCurrentNode(stenosis_segmentation)
                print(f"Set segmentation: {stenosis_segmentation.GetName()}")
            else:
                print("Warning: Could not find segmentationSelector")
            
            volume_set = False
            if hasattr(segmentStatisticsWidget, 'scalarVolumeSelector'):
                segmentStatisticsWidget.scalarVolumeSelector.setCurrentNode(analysis_volume)
                slicer.app.processEvents()
                current_volume = segmentStatisticsWidget.scalarVolumeSelector.currentNode()
                if current_volume and current_volume.GetID() == analysis_volume.GetID():
                    print(f"Set scalar volume: {analysis_volume.GetName()}")
                    volume_set = True
                else:
                    print(f"Warning: Volume selection may not have taken effect")
            

            if not volume_set and hasattr(segmentStatisticsWidget, 'scalarVolumeSelector'):
                try:

                    segmentStatisticsWidget.scalarVolumeSelector.setCurrentNodeID(analysis_volume.GetID())
                    slicer.app.processEvents()
                    current_volume = segmentStatisticsWidget.scalarVolumeSelector.currentNode()
                    if current_volume and current_volume.GetID() == analysis_volume.GetID():
                        print(f"Set scalar volume (method 2): {analysis_volume.GetName()}")
                        volume_set = True
                except:
                    pass
            
            if not volume_set:
                print(f"Warning: Could not automatically set scalar volume to {analysis_volume.GetName()}")
                print("Please manually select the cropped volume in the Scalar Volume dropdown")
            
            if hasattr(segmentStatisticsWidget, 'labelmapStatisticsCheckBox'):
                segmentStatisticsWidget.labelmapStatisticsCheckBox.setChecked(True)
            if hasattr(segmentStatisticsWidget, 'scalarVolumeStatisticsCheckBox'):
                segmentStatisticsWidget.scalarVolumeStatisticsCheckBox.setChecked(True)
        except AttributeError as ae:
            print(f"Error accessing Segment Statistics widget: {str(ae)}")
            print("Please open the Segment Statistics module manually and configure it")
               
    except Exception as e:
        print(f"Error opening Segment Statistics module: {str(e)}")
        
        try:
            slicer.util.selectModule('SegmentStatistics')
            print("Opened Segment Statistics module - please configure manually")
            print(f"  Select segmentation: {stenosis_segmentation.GetName()}")
            print(f"  Select volume: {analysis_volume.GetName()}")
            
        except Exception as fallback_error:
            print(f"Could not open Segment Statistics module: {str(fallback_error)}")
            print("Please open the Segment Statistics module manually")

# ===============================================================================
# CONSOLE HELPER FUNCTIONS
# ===============================================================================

def test_point_placement_auto_reselection():
    """
    Test function to verify automatic point placement tool re-selection is working
    """
    try:
        print("=== Testing Automatic Point Placement Tool Re-selection ===")
        
        # Check if there's a current point list
        current_point_list = None
        if hasattr(slicer.modules, 'CurrentLesionAnalysisPointList'):
            current_point_list = slicer.modules.CurrentLesionAnalysisPointList
            
        if current_point_list:
            print(f"Current active point list: {current_point_list.GetName()}")
            print(f"Current point count: {current_point_list.GetNumberOfControlPoints()}")
            
            # Test the re-selection function
            ensure_point_placement_mode_active(current_point_list)
            
            # Check interaction mode
            interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
            if interactionNode:
                current_mode = interactionNode.GetCurrentInteractionMode()
                if current_mode == interactionNode.Place:
                    print("Point placement mode is active")
                else:
                    print("Point placement mode is NOT active")
            
            print("Automatic re-selection test completed")
            print("Place a point to verify the tool stays selected after placement")
        else:
            print("No active point list found")
            print("Start point placement first using the workflow controls")
            
    except Exception as e:
        print(f"Error testing point placement auto-reselection: {e}")

# ===============================================================================
# END WORKFLOW2 FUNCTIONS
# ===============================================================================

# ===============================================================================
# CONSOLE HELPER FUNCTIONS FOR MASK SEGMENTATION
# ===============================================================================

def test_mask_segmentation(volume_name=None):
    """
    Test function to demonstrate creating a mask segmentation.
    Creates a red calcification mask using default threshold values.
    
    Args:
        volume_name (str, optional): Name of the volume to use for the test
    """
    try:
        # Example: Create a calcification mask (high density threshold)
        mask_node = create_mask_segmentation(
            mask_name="CalcificationMask",
            threshold_low=130,        # Typical calcification threshold
            threshold_high=3000,      # Upper bound to exclude artifacts
            rgb_color=(1.0, 0.0, 0.0), # Red color
            volume_name=volume_name   # Use specified volume name
        )
        
        if mask_node:
            print(f"Successfully created test mask: {mask_node.GetName()}")
            return mask_node
        else:
            print("Failed to create test mask")
            return None
            
    except Exception as e:
        print(f"Error in test mask segmentation: {e}")
        return None

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
            print(f"Error: Could not find volume '{volume_name}' or any straightened volume")
            return None
        
        # Create masks using the create_analysis_masks function
        segmentation_node = create_analysis_masks([target_volume])
        
        # Return the created segmentation node
        return segmentation_node
            
    except Exception as e:
        print(f"Error creating analysis masks manually: {e}")
        return None

def hide_crop_volume_ui_elements():
    """
    Hide all UI elements in the Crop Volume module except the green Apply button
    """
    try:
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if not crop_widget:
            print("Error: Could not get Crop Volume widget")
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
                    print(f"Hidden: {button_name}")
            except Exception as e:
                print(f"Could not hide {button_name}: {e}")
        
        # Hide error message elements 
        for element_name in error_elements_to_hide:
            try:
                elements = crop_widget.findChildren(qt.QWidget, element_name)
                for element in elements:
                    element.setVisible(False)
                    elements_hidden += 1
                    print(f"Hidden: {element_name}")
            except Exception as e:
                print(f"Could not hide {element_name}: {e}")
        
        # Also hide by finding ctkCollapsibleButton widgets directly
        try:
            collapsible_buttons = crop_widget.findChildren("ctkCollapsibleButton")
            for button in collapsible_buttons:
                button.setVisible(False)
                elements_hidden += 1
                print(f"Hidden collapsible button: {button.text if hasattr(button, 'text') else 'unnamed'}")
        except Exception as e:
            print(f"Could not hide collapsible buttons directly: {e}")
        
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
                        print("Hidden error message layout")
        except Exception as e:
            print(f"Could not hide error message layout: {e}")
        
        print(f"Successfully hidden {elements_hidden} UI elements in Crop Volume module")
        print("Only the green Apply button should now be visible")
        return True
        
    except Exception as e:
        print(f"Error hiding Crop Volume UI elements: {e}")
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
            print("Crop Volume module configured with minimal UI")
            return True
        else:
            print("Warning: Could not fully hide all UI elements")
            return False
            
    except Exception as e:
        print(f"Error setting up minimal Crop Volume UI: {e}")
        return False

# Console helper functions for testing UI modifications
def test_hide_crop_ui():
    """Console helper to test hiding Crop Volume UI elements"""
    return hide_crop_volume_ui_elements()

def test_minimal_crop_ui():
    """Console helper to test setting up minimal Crop Volume UI"""
    return setup_minimal_crop_volume_ui()

def test_hide_segment_editor_ui():
    """Console helper to test hiding Segment Editor UI elements"""
    return hide_segment_editor_ui_elements()

def test_minimal_segment_editor_ui():
    """Console helper to test setting up minimal Segment Editor UI"""
    return setup_minimal_segment_editor_ui()

def test_segment_editor_scissors_workflow():
    """Console helper to test the complete Segment Editor scissors workflow"""
    return start_with_segment_editor_scissors()

def restore_crop_ui():
    """Console helper to restore all hidden Crop Volume UI elements"""
    try:
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if not crop_widget:
            print("Error: Could not get Crop Volume widget")
            return False
        
        # Find all widgets and make them visible
        all_widgets = crop_widget.findChildren(qt.QWidget)
        restored_count = 0
        
        for widget in all_widgets:
            if hasattr(widget, 'setVisible'):
                widget.setVisible(True)
                restored_count += 1
        
        print(f"Restored visibility for {restored_count} widgets in Crop Volume module")
        return True
        
    except Exception as e:
        print(f"Error restoring Crop Volume UI: {e}")
        return False

def hide_segment_editor_ui_elements():
    """
    Hide all UI elements in the Segment Editor module except the scissors tool icon
    """
    try:
        segment_editor_widget = slicer.modules.segmenteditor.widgetRepresentation()
        if not segment_editor_widget:
            print("Error: Could not get Segment Editor widget")
            return False
        
        # Get the segment editor widget
        segment_editor = segment_editor_widget.self()
        if not segment_editor:
            print("Error: Could not get Segment Editor module")
            return False
        
        elements_hidden = 0
        
        # Hide the parameter set section
        try:
            if hasattr(segment_editor, 'parameterSetCollapsibleButton'):
                segment_editor.parameterSetCollapsibleButton.setVisible(False)
                elements_hidden += 1
                print("Hidden parameter set section")
        except Exception as e:
            print(f"Could not hide parameter set section: {e}")
        
        # Hide the segmentation section
        try:
            if hasattr(segment_editor, 'segmentationCollapsibleButton'):
                segment_editor.segmentationCollapsibleButton.setVisible(False)
                elements_hidden += 1
                print("Hidden segmentation section")
        except Exception as e:
            print(f"Could not hide segmentation section: {e}")
        
        # Hide the source volume section
        try:
            if hasattr(segment_editor, 'sourceVolumeCollapsibleButton'):
                segment_editor.sourceVolumeCollapsibleButton.setVisible(False)
                elements_hidden += 1
                print("Hidden source volume section")
        except Exception as e:
            print(f"Could not hide source volume section: {e}")
        
        # Hide segments table but keep add/remove segment buttons for scissors tool
        try:
            if hasattr(segment_editor, 'segmentsTableResizableFrame'):
                # Hide the segments table frame
                segment_editor.segmentsTableResizableFrame.setVisible(False)
                elements_hidden += 1
                print("Hidden segments table")
        except Exception as e:
            print(f"Could not hide segments table: {e}")
        
        # Hide all effect buttons except scissors - this is the most important part
        try:
            # First, try to find the effects toolbar or button group
            effects_hidden = 0
            scissors_found = False
            
            # Look for effect buttons by finding the effects widget
            if hasattr(segment_editor, 'effectsGroupBox') or hasattr(segment_editor, 'effectsWidget'):
                effects_widget = getattr(segment_editor, 'effectsGroupBox', None) or getattr(segment_editor, 'effectsWidget', None)
                if effects_widget:
                    effect_buttons = effects_widget.findChildren(qt.QPushButton)
                    for button in effect_buttons:
                        button_text = button.text if hasattr(button, 'text') else ""
                        button_name = button.objectName() if hasattr(button, 'objectName') else ""
                        button_tooltip = button.toolTip if hasattr(button, 'toolTip') else ""
                        
                        # Keep scissors tool button visible
                        if ('scissors' in button_text.lower() or 
                            'scissors' in button_name.lower() or 
                            'scissors' in button_tooltip.lower() or
                            'cut' in button_text.lower() or
                            'clip' in button_text.lower()):
                            print(f"Keeping scissors-related button visible: {button_text}")
                            scissors_found = True
                            # Make sure the scissors button is prominent
                            button.setStyleSheet("""
                                QPushButton {
                                    background-color: #ff6b6b;
                                    color: white;
                                    border: 2px solid #ff5252;
                                    padding: 12px 20px;
                                    font-weight: bold;
                                    border-radius: 8px;
                                    font-size: 16px;
                                    min-width: 150px;
                                    min-height: 50px;
                                }
                                QPushButton:hover {
                                    background-color: #ff5252;
                                    border: 2px solid #d32f2f;
                                    transform: scale(1.05);
                                }
                                QPushButton:pressed {
                                    background-color: #d32f2f;
                                }
                            """)
                            continue
                        
                        # Hide other effect buttons
                        button.setVisible(False)
                        effects_hidden += 1
                        print(f"Hidden effect button: {button_text}")
            
            # Also search globally in the widget for any remaining effect buttons
            all_buttons = segment_editor_widget.findChildren(qt.QPushButton)
            for button in all_buttons:
                button_text = button.text if hasattr(button, 'text') else ""
                button_name = button.objectName() if hasattr(button, 'objectName') else ""
                
                # Skip if already processed or is scissors
                if ('scissors' in button_text.lower() or 
                    'scissors' in button_name.lower() or
                    'cut' in button_text.lower() or
                    'clip' in button_text.lower()):
                    if not scissors_found:
                        print(f"Found scissors button in global search: {button_text}")
                        scissors_found = True
                        # Style the scissors button
                        button.setStyleSheet("""
                            QPushButton {
                                background-color: #ff6b6b;
                                color: white;
                                border: 2px solid #ff5252;
                                padding: 12px 20px;
                                font-weight: bold;
                                border-radius: 8px;
                                font-size: 16px;
                                min-width: 150px;
                                min-height: 50px;
                            }
                            QPushButton:hover {
                                background-color: #ff5252;
                                border: 2px solid #d32f2f;
                            }
                            QPushButton:pressed {
                                background-color: #d32f2f;
                            }
                        """)
                    continue
                
                # Hide known effect buttons
                if (button_text and any(effect in button_text.lower() for effect in 
                    ['paint', 'draw', 'erase', 'level', 'grow', 'fill', 'threshold', 'island', 
                     'smooth', 'margin', 'hollow', 'wrap', 'logical', 'mask', 'split'])):
                    if button.isVisible():
                        button.setVisible(False)
                        effects_hidden += 1
                        print(f"Hidden remaining effect button: {button_text}")
            
            elements_hidden += effects_hidden
            if scissors_found:
                print(f"Hidden {effects_hidden} effect buttons, keeping scissors visible and styled")
            else:
                print(f"Hidden {effects_hidden} effect buttons, but scissors tool not found")
                print("You may need to manually look for the scissors tool")
                    
        except Exception as e:
            print(f"Could not hide effect buttons: {e}")
        
        # Hide options sections
        try:
            if hasattr(segment_editor, 'effectOptionsCollapsibleButton'):
                segment_editor.effectOptionsCollapsibleButton.setVisible(False)
                elements_hidden += 1
                print("Hidden effect options section")
        except Exception as e:
            print(f"Could not hide effect options: {e}")
        
        # Hide masking settings
        try:
            if hasattr(segment_editor, 'maskingCollapsibleButton'):
                segment_editor.maskingCollapsibleButton.setVisible(False)
                elements_hidden += 1
                print("Hidden masking settings")
        except Exception as e:
            print(f"Could not hide masking settings: {e}")
        
        # Try to find and hide collapsible buttons by searching for them
        try:
            collapsible_buttons = segment_editor_widget.findChildren("ctkCollapsibleButton")
            for button in collapsible_buttons:
                button_text = button.text if hasattr(button, 'text') else ""
                # Keep only essential sections, hide others
                if any(keyword in button_text.lower() for keyword in 
                       ['parameter', 'segmentation', 'source', 'masking', 'options', 'display']):
                    button.setVisible(False)
                    elements_hidden += 1
                    print(f"Hidden collapsible button: {button_text}")
        except Exception as e:
            print(f"Could not hide collapsible buttons: {e}")
        
        print(f"Successfully hidden {elements_hidden} UI elements in Segment Editor module")
        print("Only the scissors tool should now be prominently visible")
        return True
        
    except Exception as e:
        print(f"Error hiding Segment Editor UI elements: {e}")
        return False

def start_with_segment_editor_scissors():
    """
    Start segmentation workflow by opening the Segment Editor module with only the scissors tool visible.
    This function should be called when the workflow needs to switch to segmentation.
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
            slicer.util.errorDisplay("No volume found. Please load a volume first.")
            return False
        
        # Switch to Segment Editor module
        slicer.util.selectModule("SegmentEditor")
        slicer.app.processEvents()
        
        # Hide all UI elements except scissors tool
        hide_segment_editor_ui_elements()
        
        # Schedule additional UI hiding attempts in case the first one doesn't catch everything
        qt.QTimer.singleShot(1000, hide_segment_editor_ui_elements)
        qt.QTimer.singleShot(3000, hide_segment_editor_ui_elements)
        
        # Set up the segmentation
        segment_editor_widget = slicer.modules.segmenteditor.widgetRepresentation()
        segment_editor = segment_editor_widget.self()
        
        # Create new segmentation if needed
        segmentation_node = segment_editor.parameterSetNode.GetSegmentationNode()
        if segmentation_node is None or segmentation_node.GetSegmentation().GetNumberOfSegments() > 0:
            segmentation_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
            segment_editor.parameterSetNode.SetAndObserveSegmentationNode(segmentation_node)
        
        # Name segmentation node based on the volume
        segmentation_node.SetName(volume_node.GetName() + "_Segmentation")
        
        # Set source volume
        segment_editor.parameterSetNode.SetAndObserveSourceVolumeNode(volume_node)
        
        # Try to automatically select the scissors tool
        try:
            if hasattr(segment_editor, 'effectByName'):
                # Try different names for the scissors tool
                scissors_names = ['Scissors', 'Cut', 'Scissor', 'Clip']
                for name in scissors_names:
                    scissors_effect = segment_editor.effectByName(name)
                    if scissors_effect:
                        segment_editor.setActiveEffect(scissors_effect)
                        print(f"Automatically selected {name} tool")
                        break
                else:
                    print("Scissors tool not found with standard names")
        except Exception as e:
            print(f"Could not auto-select scissors tool: {e}")
        
        print("Segment Editor module configured with scissors tool only")
        print(f"Ready to segment volume: {volume_node.GetName()}")
        
        return True
        
    except Exception as e:
        print(f"Error setting up Segment Editor with scissors: {e}")
        return False

def setup_minimal_segment_editor_ui():
    """
    Set up the Segment Editor module with minimal UI (only the scissors tool)
    """
    try:
        # First ensure we're in the Segment Editor module
        slicer.util.selectModule("SegmentEditor")
        slicer.app.processEvents()
        
        # Hide all UI elements except the scissors tool
        hide_success = hide_segment_editor_ui_elements()
        
        # Automatically select the scissors tool if available
        try:
            segment_editor_widget = slicer.modules.segmenteditor.widgetRepresentation()
            segment_editor = segment_editor_widget.self()
            
            # Try to activate the scissors effect
            if hasattr(segment_editor, 'effectByName'):
                scissors_effect = segment_editor.effectByName('Scissors')
                if scissors_effect:
                    segment_editor.setActiveEffect(scissors_effect)
                    print("Automatically selected scissors tool")
                else:
                    print("Scissors tool not found, trying alternative names")
                    # Try alternative names
                    for effect_name in ['Cut', 'Scissor', 'Clip']:
                        effect = segment_editor.effectByName(effect_name)
                        if effect:
                            segment_editor.setActiveEffect(effect)
                            print(f"Selected {effect_name} tool")
                            break
        except Exception as e:
            print(f"Could not auto-select scissors tool: {e}")
        
        if hide_success:
            print("Segment Editor module configured with minimal UI")
            return True
        else:
            print("Warning: Could not fully hide all UI elements")
            return False
            
    except Exception as e:
        print(f"Error setting up minimal Segment Editor UI: {e}")
        return False

def restore_segment_editor_ui():
    """Console helper to restore all hidden Segment Editor UI elements"""
    try:
        segment_editor_widget = slicer.modules.segmenteditor.widgetRepresentation()
        if not segment_editor_widget:
            print("Error: Could not get Segment Editor widget")
            return False
        
        # Find all widgets and make them visible
        all_widgets = segment_editor_widget.findChildren(qt.QWidget)
        restored_count = 0
        
        for widget in all_widgets:
            if hasattr(widget, 'setVisible'):
                widget.setVisible(True)
                restored_count += 1
        
        print(f"Restored visibility for {restored_count} widgets in Segment Editor module")
        return True
        
    except Exception as e:
        print(f"Error restoring Segment Editor UI: {e}")
        return False

def main():
    """
    Main entry point for the workflow
    """
    try:
        start_with_volume_crop()
    except Exception as e:
        slicer.util.errorDisplay(f"Error in workflow: {str(e)}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()