import slicer
import qt
import vtk
import math
import numpy as np

"""
Slicer Guided Workflow for Vessel Centerline Extraction and CPR Visualization

This script provides a guided workflow for:
1. Threshold-based segmentation creation
2. Cropping with scissors tool in Segment Editor
3. Automated centerline extraction using the default Extract Centerline module
4. Automatic transition to Curved Planar Reformat (CPR) module

The workflow uses the standard Slicer GUI for endpoint placement rather than 
custom UI elements, providing a more integrated user experience.

Main workflow functions:
- create_threshold_segment(): Start the workflow
- prompt_for_endpoints(): Guide user to use default Extract Centerline GUI
- setup_centerline_completion_monitor(): Monitor for completion and auto-switch to CPR
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
        # Ultimate fallback
        return slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")

def create_threshold_segment():
    """
    Main workflow function to create a threshold segment with default values
    """
    # Find the appropriate volume - prefer cropped volumes and visible volumes
    volume_node = find_working_volume()
    
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    
    # Get threshold values from user via single dialog
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
        
        # Title
        title_label = qt.QLabel("Set Threshold Range")
        title_label.setStyleSheet("QLabel { font-weight: bold; font-size: 14px; margin: 10px; }")
        layout.addWidget(title_label)
        
        # Lower threshold
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
        
        # Upper threshold
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
        
        # Info label
        info_label = qt.QLabel("Range: -1024 to 3071 Hounsfield units")
        info_label.setStyleSheet("QLabel { color: #666; font-size: 11px; margin: 5px; }")
        layout.addWidget(info_label)
        
        # Buttons
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
        # Fallback to defaults
        return (290.0, 3071.0)

def create_segmentation_from_threshold(volume_node, threshold_value_low, threshold_value_high=None):
    """
    Apply threshold to existing Segment_1 instead of creating new segmentation
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
        print(f"Error applying threshold: {e}")

        try:
            print("Trying fallback method with Segment Editor...")

            segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
            slicer.mrmlScene.AddNode(segmentEditorNode)
            segmentEditorNode.SetAndObserveSegmentationNode(segmentation_node)
            segmentEditorNode.SetAndObserveSourceVolumeNode(volume_node)
            segmentEditorNode.SetSelectedSegmentID(segment_id)

            segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
            segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
            segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
            segmentEditorWidget.setActiveEffectByName("Threshold")
            effect = segmentEditorWidget.activeEffect()
            
            if effect:
                effect.setParameter("MinimumThreshold", str(threshold_value_low))
                effect.setParameter("MaximumThreshold", str(threshold_value_high))
                effect.self().onApply()
                print("Applied threshold using Segment Editor fallback method")
            slicer.mrmlScene.RemoveNode(segmentEditorNode)
            
        except Exception as e2:
            print(f"Fallback method also failed: {e2}")
            print("Segment_1 is ready - please apply threshold manually in Segment Editor")
    
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
            segment.SetColor(0.8, 0.2, 0.2)  # Red color
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
    simplify_segment_editor_gui()
    
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
        setup_cropping_monitor(segment_editor_widget)
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
            continue_button = qt.QPushButton("✓ FINISH CROPPING - CONTINUE")
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
        create_simple_continue_button()
        
    except Exception as e:
        print(f"Error adding continue button to segment editor: {e}")

def simplify_segment_editor_gui():
    """
    Simplify the Segment Editor GUI to show only Scissors tool and green button
    """
    try:
        segment_editor_widget = slicer.modules.segmenteditor.widgetRepresentation().self().editor
        
        # Get the main segment editor widget
        main_widget = slicer.modules.segmenteditor.widgetRepresentation()
        
        # Hide all top-level elements except the ones we need
        for child in main_widget.children():
            if hasattr(child, 'hide'):
                child_name = child.objectName() if hasattr(child, 'objectName') else ""
                child_class = child.__class__.__name__
                
                # Keep only essential elements and our green button
                if not any(keyword in child_name.lower() for keyword in ['editor', 'segment']) and \
                   child_class not in ['QScrollArea', 'QWidget'] and \
                   not (hasattr(child, 'text') and 'FINISH CROPPING' in str(child.text)):
                    child.hide()
        
        # Hide segment list/table
        try:
            segment_widgets = segment_editor_widget.findChildren(qt.QWidget)
            for widget in segment_widgets:
                widget_name = widget.objectName().lower() if hasattr(widget, 'objectName') else ""
                if any(keyword in widget_name for keyword in ['segment', 'table', 'list', 'tree']):
                    widget.hide()
        except Exception as e:
            print(f"Note: Could not hide segment list: {e}")
        
        # Hide all effect buttons except Scissors
        try:
            all_buttons = segment_editor_widget.findChildren(qt.QPushButton)
            for button in all_buttons:
                button_text = button.text.lower() if hasattr(button, 'text') else ""
                button_name = button.objectName().lower() if hasattr(button, 'objectName') else ""
                button_tooltip = button.toolTip.lower() if hasattr(button, 'toolTip') else ""
                
                # Hide all buttons except scissors and our green continue button
                if not ('scissors' in button_text or 'scissors' in button_name or 'scissors' in button_tooltip) and \
                   not 'FINISH CROPPING' in button.text:
                    button.hide()
                elif 'scissors' in button_text or 'scissors' in button_name or 'scissors' in button_tooltip:
                    button.show()  # Ensure scissors button is visible
        except Exception as e:
            print(f"Note: Could not hide effect buttons: {e}")
        
        # Hide parameter panels and options
        try:
            all_widgets = segment_editor_widget.findChildren(qt.QWidget)
            for widget in all_widgets:
                widget_name = widget.objectName().lower() if hasattr(widget, 'objectName') else ""
                widget_class = widget.__class__.__name__
                
                # Hide advanced options, parameters, and settings panels
                if any(keyword in widget_name for keyword in [
                    'parameter', 'option', 'setting', 'advanced', 'representation',
                    'statistics', 'properties', 'display', 'color', 'opacity',
                    'slice', 'fill', 'outline', 'smoothing', 'interpolation'
                ]) or widget_class in ['QGroupBox', 'QCollapsibleWidget']:
                    # Don't hide if it contains our green button
                    if not (hasattr(widget, 'findChildren') and 
                           any('FINISH CROPPING' in str(child.text) if hasattr(child, 'text') else False 
                               for child in widget.findChildren(qt.QPushButton))):
                        widget.hide()
        except Exception as e:
            print(f"Note: Could not hide parameter panels: {e}")
        
        # Hide menu bars and toolbars
        try:
            for child in main_widget.findChildren(qt.QMenuBar):
                child.hide()
            for child in main_widget.findChildren(qt.QToolBar):
                child.hide()
        except Exception as e:
            print(f"Note: Could not hide menu/toolbars: {e}")
        
        # Hide status bars and labels that aren't essential
        try:
            labels = segment_editor_widget.findChildren(qt.QLabel)
            for label in labels:
                label_text = label.text.lower() if hasattr(label, 'text') else ""
                if any(keyword in label_text for keyword in [
                    'status', 'info', 'tip', 'help', 'instruction', 'guidance'
                ]) and 'scissors' not in label_text:
                    label.hide()
        except Exception as e:
            print(f"Note: Could not hide status labels: {e}")
        
        print("Segment Editor GUI maximally simplified - showing only Scissors tool and green button")
        
    except Exception as e:
        print(f"Error simplifying segment editor GUI: {e}")

def create_simple_continue_button():
    """
    Create a simple continue button without complex dialogs
    """
    print("Scissors tool selected - ready for cropping")
    print("Use console command 'on_continue_from_scissors()' when done, or the workflow will auto-continue")

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

def setup_cropping_monitor(segment_editor_widget):
    """
    Set up simplified monitoring for cropping completion
    """
    print("Scissors tool selected - ready for cropping")
    print("When done cropping, run: open_centerline_module()")

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
        setup_centerline_module()
        
    except Exception as e:
        print(f"Error opening centerline module: {e}")
        slicer.util.errorDisplay(f"Could not open Extract Centerline module: {str(e)}")

def add_large_centerline_apply_button():
    """
    Add a large green Apply button directly to the Extract Centerline module GUI
    """
    try:
        # Use a timer to delay button creation until UI is fully loaded
        def create_large_button():
            try:
                centerline_widget = slicer.modules.extractcenterline.widgetRepresentation()
                if centerline_widget and hasattr(centerline_widget, 'self'):
                    centerline_module = centerline_widget.self()
                    
                    # Find the original Apply button first to connect to its action
                    original_apply_button = None
                    if hasattr(centerline_module.ui, 'applyButton'):
                        original_apply_button = centerline_module.ui.applyButton
                    elif hasattr(centerline_module.ui, 'ApplyButton'):
                        original_apply_button = centerline_module.ui.ApplyButton
                    
                    # If not found with direct attribute, search for it
                    if not original_apply_button:
                        all_buttons = centerline_widget.findChildren(qt.QPushButton)
                        for button in all_buttons:
                            button_text = button.text if hasattr(button, 'text') else ""
                            if 'apply' in button_text.lower():
                                original_apply_button = button
                                break
                    
                    if original_apply_button:
                        # Create a new large green button
                        large_apply_button = qt.QPushButton("✓ EXTRACT CENTERLINE")
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
                        
                        # Connect the new button to trigger the original Apply button's click
                        large_apply_button.connect('clicked()', lambda: original_apply_button.click())
                        
                        # Add the button directly to the Extract Centerline module's GUI
                        # Try to find the main UI container in the centerline module
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
                                print("✓ Added large green Apply button to Extract Centerline module GUI")
                            else:
                                # Create a layout if none exists
                                new_layout = qt.QVBoxLayout(main_ui_widget)
                                new_layout.insertWidget(0, large_apply_button)
                                print("✓ Created layout and added large green Apply button to Extract Centerline module")
                        else:
                            # Fallback: Try to find any suitable container widget
                            container_widgets = centerline_widget.findChildren(qt.QWidget)
                            for widget in container_widgets:
                                if hasattr(widget, 'layout') and widget.layout() and widget.layout().count() > 0:
                                    widget.layout().insertWidget(0, large_apply_button)
                                    print("✓ Added large green Apply button to Extract Centerline container widget")
                                    break
                            else:
                                print("✗ Could not find suitable container in Extract Centerline module")
                                return False
                        
                        # Store reference to the button for potential cleanup
                        slicer.modules.CenterlineLargeApplyButton = large_apply_button
                        return True
                    else:
                        print("✗ Could not find original Apply button in Extract Centerline module")
                        return False
                        
            except Exception as e:
                print(f"Error creating large Apply button in Extract Centerline: {e}")
                return False
        
        # Try creating the button immediately
        success = create_large_button()
        
        # If that didn't work, try again after delays
        if not success:
            qt.QTimer.singleShot(1000, create_large_button)
            qt.QTimer.singleShot(3000, create_large_button)
            print("Scheduling delayed large Apply button creation for Extract Centerline...")
            
    except Exception as e:
        print(f"Error adding large centerline Apply button: {e}")

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
                    
                    # Create new point list for endpoint selection
                    try:
                        endpoint_point_list = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
                        endpoint_point_list.SetName("CenterlineEndpoints")
                        
                        # Set endpoint selector to use new point list
                        endpoint_set = False
                        for endpoint_selector_attr in ['inputEndPointsSelector', 'endpointsSelector', 'inputFiducialSelector']:
                            if hasattr(centerline_module.ui, endpoint_selector_attr):
                                getattr(centerline_module.ui, endpoint_selector_attr).setCurrentNode(endpoint_point_list)
                                print(f"Created new endpoint point list using {endpoint_selector_attr}")
                                endpoint_set = True
                                break
                        
                        if not endpoint_set:
                            print("Warning: Could not find endpoint selector in centerline module")
                        
                        # Enable "create new" mode for endpoint selection
                        for create_new_attr in ['createNewEndpointsCheckBox', 'createNewPointListCheckBox']:
                            if hasattr(centerline_module.ui, create_new_attr):
                                getattr(centerline_module.ui, create_new_attr).setChecked(True)
                                print(f"Enabled create new point list using {create_new_attr}")
                                
                    except Exception as e:
                        print(f"Could not configure endpoint point list: {e}")
                    
                    # Create new model for centerline output
                    try:
                        centerline_model = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
                        centerline_model.SetName("CenterlineModel")
                        
                        # Set centerline model selector to use new model
                        model_set = False
                        for model_selector_attr in ['outputCenterlineModelSelector', 'centerlineModelSelector', 'outputModelSelector']:
                            if hasattr(centerline_module.ui, model_selector_attr):
                                getattr(centerline_module.ui, model_selector_attr).setCurrentNode(centerline_model)
                                print(f"Created new centerline model using {model_selector_attr}")
                                model_set = True
                                break
                        
                        if not model_set:
                            print("Warning: Could not find centerline model selector")
                        
                        # Enable "create new" mode for model selection
                        for create_new_model_attr in ['createNewModelCheckBox', 'createNewCenterlineModelCheckBox']:
                            if hasattr(centerline_module.ui, create_new_model_attr):
                                getattr(centerline_module.ui, create_new_model_attr).setChecked(True)
                                print(f"Enabled create new model using {create_new_model_attr}")
                                
                    except Exception as e:
                        print(f"Could not configure centerline model: {e}")
                    
                    # Configure additional output nodes
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
        # Check if button already exists to prevent duplicates
        if hasattr(slicer.modules, 'CropLargeApplyButton'):
            existing_button = slicer.modules.CropLargeApplyButton
            if existing_button and existing_button.parent():
                print("Large Apply button already exists in Crop Volume module")
                return
        
        print("=== STARTING CROP BUTTON CREATION ===")
        
        # Use a timer to delay button creation until UI is fully loaded
        def create_large_button():
            try:
                # Check if button already exists to prevent duplicates
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
                    # Try multiple ways to access the crop module
                    crop_module = None
                    
                    # Method 1: Try the 'self' attribute
                    if hasattr(crop_widget, 'self'):
                        try:
                            crop_module = crop_widget.self()
                            print(f"Method 1 - Got crop module via 'self': {crop_module is not None}")
                        except Exception as e:
                            print(f"Method 1 failed: {e}")
                    
                    # Method 2: Try direct access
                    if not crop_module:
                        try:
                            crop_module = crop_widget
                            print(f"Method 2 - Using crop_widget directly: {crop_module is not None}")
                        except Exception as e:
                            print(f"Method 2 failed: {e}")
                    
                    # Method 3: Try getting the widget representation directly
                    if not crop_module:
                        try:
                            crop_module = slicer.modules.cropvolume.createNewWidgetRepresentation()
                            print(f"Method 3 - Created new widget representation: {crop_module is not None}")
                        except Exception as e:
                            print(f"Method 3 failed: {e}")
                    
                    if crop_module:
                        print(f"Successfully got crop module: {type(crop_module)}")
                        
                        # Find the original Apply button first to connect to its action
                        original_apply_button = None
                        print("Searching for Apply button in Crop Volume module...")
                        
                        # Try various common attribute names for Apply button
                        apply_button_attrs = ['applyButton', 'ApplyButton', 'applyCropButton', 'cropApplyButton']
                        
                        # First try with ui attribute if it exists
                        if hasattr(crop_module, 'ui'):
                            print("Found 'ui' attribute, searching for Apply button...")
                            for attr_name in apply_button_attrs:
                                if hasattr(crop_module.ui, attr_name):
                                    original_apply_button = getattr(crop_module.ui, attr_name)
                                    print(f"Found Apply button using attribute: {attr_name}")
                                    break
                        else:
                            print("No 'ui' attribute found, trying direct attributes...")
                            # Try direct attributes on the module
                            for attr_name in apply_button_attrs:
                                if hasattr(crop_module, attr_name):
                                    original_apply_button = getattr(crop_module, attr_name)
                                    print(f"Found Apply button using direct attribute: {attr_name}")
                                    break
                        
                        # If not found with direct attribute, search for it by text
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
                        large_apply_button = qt.QPushButton("✓ APPLY CROP")
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
                        print("✓ Connected large button to original Apply button")
                        
                    else:
                        print("Warning: Original Apply button not found, creating standalone button")
                        # Create button anyway and try to trigger apply through the module
                        large_apply_button = qt.QPushButton("✓ APPLY CROP")
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
                        print("✓ Connected large button to crop apply logic")
                    
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
                    
                    # Add button to the main UI widget
                    if main_ui_widget and hasattr(main_ui_widget, 'layout'):
                        layout = main_ui_widget.layout()
                        if layout:
                            # Insert at the top of the module for maximum visibility
                            layout.insertWidget(0, large_apply_button)
                            print("✓ Added large green Apply button to Crop Volume module GUI")
                        else:
                            # Create a layout if none exists
                            new_layout = qt.QVBoxLayout(main_ui_widget)
                            new_layout.insertWidget(0, large_apply_button)
                            print("✓ Created layout and added large green Apply button to Crop Volume module")
                    else:
                        # Fallback: Try to find any suitable container widget
                        container_widgets = crop_widget.findChildren(qt.QWidget)
                        for widget in container_widgets:
                            if hasattr(widget, 'layout') and widget.layout() and widget.layout().count() > 0:
                                widget.layout().insertWidget(0, large_apply_button)
                                print("✓ Added large green Apply button to Crop Volume container widget")
                                break
                        else:
                            print("✗ Could not find suitable container in Crop Volume module")
                            return False
                    
                    # Store reference to the button for potential cleanup
                    slicer.modules.CropLargeApplyButton = large_apply_button
                    return True
                else:
                    print("✗ Could not access crop module after trying all methods")
                    print("Available crop_widget attributes:")
                    if crop_widget:
                        try:
                            attrs = [attr for attr in dir(crop_widget) if not attr.startswith('_')]
                            print(f"  {attrs[:10]}...")  # Show first 10 attributes
                        except:
                            print("  Could not list attributes")
                    return False
                        
            except Exception as e:
                print(f"Error creating large Apply button: {e}")
                return False
        
        # Try creating the button immediately
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
        # Check if button already exists to prevent duplicates
        if hasattr(slicer.modules, 'CPRLargeApplyButton'):
            existing_button = slicer.modules.CPRLargeApplyButton
            if existing_button and existing_button.parent():
                print("Large Apply button already exists in CPR module")
                return
        
        print("=== STARTING CPR BUTTON CREATION ===")
        
        # Use a timer to delay button creation until UI is fully loaded
        def create_large_button():
            try:
                # Check if button already exists to prevent duplicates
                if hasattr(slicer.modules, 'CPRLargeApplyButton'):
                    existing_button = slicer.modules.CPRLargeApplyButton
                    if existing_button and existing_button.parent():
                        print("Large Apply button already exists, skipping creation")
                        return True
                
                print("Attempting to create large Apply button for CPR...")
                cpr_widget = slicer.modules.curvedplanarreformat.widgetRepresentation()
                print(f"CPR widget found: {cpr_widget is not None}")
                print(f"CPR widget type: {type(cpr_widget)}")
                print(f"CPR widget has 'self' attribute: {hasattr(cpr_widget, 'self') if cpr_widget else 'N/A'}")
                
                if cpr_widget:
                    # Try multiple ways to access the cpr module
                    cpr_module = None
                    
                    # Method 1: Try the 'self' attribute
                    if hasattr(cpr_widget, 'self'):
                        try:
                            cpr_module = cpr_widget.self()
                            print(f"Method 1 - Got CPR module via 'self': {cpr_module is not None}")
                        except Exception as e:
                            print(f"Method 1 failed: {e}")
                    
                    # Method 2: Try direct access
                    if not cpr_module:
                        try:
                            cpr_module = cpr_widget
                            print(f"Method 2 - Using cpr_widget directly: {cpr_module is not None}")
                        except Exception as e:
                            print(f"Method 2 failed: {e}")
                    
                    # Method 3: Try getting the widget representation directly
                    if not cpr_module:
                        try:
                            cpr_module = slicer.modules.curvedplanarreformat.createNewWidgetRepresentation()
                            print(f"Method 3 - Created new widget representation: {cpr_module is not None}")
                        except Exception as e:
                            print(f"Method 3 failed: {e}")
                    
                    if cpr_module:
                        print(f"Successfully got CPR module: {type(cpr_module)}")
                        
                        # Find the original Apply button first to connect to its action
                        original_apply_button = None
                        print("Searching for Apply button in CPR module...")
                        
                        # Try various common attribute names for Apply button
                        apply_button_attrs = ['applyButton', 'ApplyButton', 'applyCPRButton', 'cprApplyButton']
                        
                        # First try with ui attribute if it exists
                        if hasattr(cpr_module, 'ui'):
                            print("Found 'ui' attribute, searching for Apply button...")
                            for attr_name in apply_button_attrs:
                                if hasattr(cpr_module.ui, attr_name):
                                    original_apply_button = getattr(cpr_module.ui, attr_name)
                                    print(f"Found Apply button using attribute: {attr_name}")
                                    break
                        else:
                            print("No 'ui' attribute found, trying direct attributes...")
                            # Try direct attributes on the module
                            for attr_name in apply_button_attrs:
                                if hasattr(cpr_module, attr_name):
                                    original_apply_button = getattr(cpr_module, attr_name)
                                    print(f"Found Apply button using direct attribute: {attr_name}")
                                    break
                        
                        # If not found with direct attribute, search for it by text
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
                            # Create a new large green button
                            large_apply_button = qt.QPushButton("✓ APPLY CPR")
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
                            print("✓ Connected large button to original Apply button")
                            
                        else:
                            print("Warning: Original Apply button not found, creating standalone button")
                            # Create button anyway and try to trigger apply through the module
                            large_apply_button = qt.QPushButton("✓ APPLY CPR")
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
                            
                            # Try to connect to CPR logic directly
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
                            print("✓ Connected large button to CPR apply logic")
                        
                        # Add the button to the GUI (common for both cases)
                        # Try to find the main UI container in the cpr module
                        main_ui_widget = None
                        
                        # Strategy 1: Look for the main widget container
                        if hasattr(cpr_module, 'ui') and hasattr(cpr_module.ui, 'widget'):
                            main_ui_widget = cpr_module.ui.widget
                        elif hasattr(cpr_module, 'widget'):
                            main_ui_widget = cpr_module.widget
                        elif hasattr(cpr_widget, 'widget'):
                            main_ui_widget = cpr_widget.widget
                        
                        # Strategy 2: Get the module widget representation directly
                        if not main_ui_widget:
                            main_ui_widget = cpr_widget
                        
                        # Add button to the main UI widget
                        if main_ui_widget and hasattr(main_ui_widget, 'layout'):
                            layout = main_ui_widget.layout()
                            if layout:
                                # Insert at the top of the module for maximum visibility
                                layout.insertWidget(0, large_apply_button)
                                print("✓ Added large green Apply button to CPR module GUI")
                            else:
                                # Create a layout if none exists
                                new_layout = qt.QVBoxLayout(main_ui_widget)
                                new_layout.insertWidget(0, large_apply_button)
                                print("✓ Created layout and added large green Apply button to CPR module")
                        else:
                            # Fallback: Try to find any suitable container widget
                            container_widgets = cpr_widget.findChildren(qt.QWidget)
                            for widget in container_widgets:
                                if hasattr(widget, 'layout') and widget.layout() and widget.layout().count() > 0:
                                    widget.layout().insertWidget(0, large_apply_button)
                                    print("✓ Added large green Apply button to CPR container widget")
                                    break
                            else:
                                print("✗ Could not find suitable container in CPR module")
                                return False
                        
                        # Store reference to the button for potential cleanup
                        slicer.modules.CPRLargeApplyButton = large_apply_button
                        return True
                    else:
                        print("✗ Could not access CPR module after trying all methods")
                        print("Available cpr_widget attributes:")
                        if cpr_widget:
                            try:
                                attrs = [attr for attr in dir(cpr_widget) if not attr.startswith('_')]
                                print(f"  {attrs[:10]}...")  # Show first 10 attributes
                            except:
                                print("  Could not list attributes")
                        return False
                        
            except Exception as e:
                print(f"Error creating large Apply button: {e}")
                return False
        
        # Try creating the button immediately
        success = create_large_button()
        
        # If that didn't work, try again after delays
        if not success:
            qt.QTimer.singleShot(1000, create_large_button)
            qt.QTimer.singleShot(3000, create_large_button)
            print("Scheduling delayed large Apply button creation...")
            
    except Exception as e:
        print(f"Error adding large CPR Apply button: {e}")

def style_crop_apply_button():
    """
    Style the Apply button in the Crop Volume module to be large and green
    """
    try:
        # Use a timer to delay styling until UI is fully loaded
        def apply_styling():
            try:
                crop_widget = slicer.modules.cropvolume.widgetRepresentation()
                if crop_widget:
                    # Multiple strategies to find the Apply button
                    apply_button = None
                    
                    # Strategy 1: Direct UI access
                    if hasattr(crop_widget, 'self') and hasattr(crop_widget.self(), 'ui'):
                        crop_module = crop_widget.self()
                        if hasattr(crop_module.ui, 'applyButton'):
                            apply_button = crop_module.ui.applyButton
                            print("Found Apply button via direct UI access")
                        elif hasattr(crop_module.ui, 'ApplyButton'):
                            apply_button = crop_module.ui.ApplyButton
                            print("Found Apply button via capitalized UI access")
                    
                    # Strategy 2: Search all buttons in crop widget
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
                    
                    # Strategy 3: Search in entire main window for crop-related apply buttons
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
                        # Apply the green styling
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
                        
                        # Also try setting some properties directly
                        apply_button.setMinimumHeight(70)
                        apply_button.setMinimumWidth(200)
                        
                        print("✓ Successfully styled Apply button in Crop Volume module - large and green")
                        return True
                    else:
                        print("✗ Could not find Apply button in Crop Volume module")
                        return False
                        
            except Exception as e:
                print(f"Error in apply_styling: {e}")
                return False
        
        # Try styling immediately
        success = apply_styling()
        
        # If that didn't work, try again after a short delay
        if not success:
            timer = qt.QTimer()
            timer.singleShot(1000, apply_styling)  # Try again after 1 second
            print("Scheduling delayed Apply button styling...")
            
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
    
    # Create a new ROI that fits the entire volume
    roi_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode", "CropROI")
    
    # Get volume bounds and set ROI to fit entire volume
    bounds = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    volume_node.GetBounds(bounds)
    
    # Calculate center and size of the volume
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
    
    # Set ROI center and size to encompass entire volume
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
    
    # Make sure ROI is visible
    display_node = roi_node.GetDisplayNode()
    if display_node:
        display_node.SetVisibility(True)
        display_node.SetHandlesInteractive(True)
        display_node.SetColor(1.0, 1.0, 0.0)  # Yellow color for visibility
        display_node.SetSelectedColor(1.0, 0.5, 0.0)  # Orange when selected
    
    print("ROI created - adjust handles and click Apply to crop")
    
    # Ensure UI is fully loaded before adding button
    slicer.app.processEvents()
    
    # Try adding the button immediately
    add_large_crop_apply_button()
    
    # Also try adding the button after a delay to ensure UI is fully loaded (only one retry)
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
            
            # Store references to both volumes for potential future use
            slicer.modules.WorkflowOriginalVolume = original_volume_node
            slicer.modules.WorkflowCroppedVolume = node
            
            # Set the cropped volume as the active volume and make it visible in all slice views
            set_cropped_volume_visible(node)
            
            # Auto-delete the ROI node after cropping
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
        # Ensure the cropped volume has a display node
        if not cropped_volume.GetDisplayNode():
            cropped_volume.CreateDefaultDisplayNodes()
        
        # Set the cropped volume as the active volume in the selection node
        selection_node = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selection_node:
            selection_node.SetActiveVolumeID(cropped_volume.GetID())
            selection_node.SetSecondaryVolumeID(None)
        
        # Get layout manager and set the volume in all slice views
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
        
        # Force refresh of all slice views
        for slice_view_name in slice_view_names:
            slice_widget = layout_manager.sliceWidget(slice_view_name)
            if slice_widget:
                slice_view = slice_widget.sliceView()
                slice_view.forceRender()
        
        # Process events to ensure GUI is updated
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
        print("Centerline extraction configured - place start and end points, then click Apply")
        setup_centerline_completion_monitor()
        
    except Exception as e:
        print(f"Error prompting for endpoints: {e}")
        print("Please add start and end points using the Extract Centerline module, then click Apply")

def setup_centerline_completion_monitor():
    """
    Set up monitoring to detect when centerline extraction completes
    """
    try:
        if not hasattr(slicer.modules, 'CenterlineMonitorTimer'):
            timer = qt.QTimer()
            timer.timeout.connect(check_centerline_completion)
            timer.start(2000)
            slicer.modules.CenterlineMonitorTimer = timer
            slicer.modules.CenterlineCheckCount = 0
            print("Started monitoring for centerline completion")
        
    except Exception as e:
        print(f"Error setting up centerline completion monitor: {e}")

def check_centerline_completion():
    """
    Check if centerline extraction has completed and switch to CPR module
    """
    try:
        if hasattr(slicer.modules, 'CenterlineCheckCount'):
            slicer.modules.CenterlineCheckCount += 1
            if slicer.modules.CenterlineCheckCount > 60:
                stop_centerline_monitoring()
                print("Centerline monitoring timed out")
                return
        centerline_model = find_recent_centerline_model()
        centerline_curve = find_recent_centerline_curve()
        
        if centerline_model or centerline_curve:
            print("Centerline extraction completed!")
            stop_centerline_monitoring()
            show_centerline_completion_dialog(centerline_model, centerline_curve)
        
    except Exception as e:
        print(f"Error checking centerline completion: {e}")

def find_recent_centerline_model():
    """
    Find the most recently created centerline model
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
        if centerline_models:
            centerline_models.sort(key=lambda x: x.GetMTime(), reverse=True)
            return centerline_models[0]
        
        return None
        
    except Exception as e:
        print(f"Error finding centerline model: {e}")
        return None

def find_recent_centerline_curve():
    """
    Find the most recently created centerline curve
    """
    try:
        curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsCurveNode')
        centerline_curves = []
        for curve in curve_nodes:
            curve_name = curve.GetName().lower()
            if any(keyword in curve_name for keyword in ['centerline', 'curve', 'vessel']):
                if curve.GetNumberOfControlPoints() > 0:
                    centerline_curves.append(curve)
        if centerline_curves:
            centerline_curves.sort(key=lambda x: x.GetMTime(), reverse=True)
            return centerline_curves[0]
        
        return None
        
    except Exception as e:
        print(f"Error finding centerline curve: {e}")
        return None

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
        
        # Add large green Apply button with a small delay to ensure UI is loaded
        qt.QTimer.singleShot(1000, add_large_cpr_apply_button)
        
        # Auto-apply CPR after everything is set up (with additional delay)
        qt.QTimer.singleShot(3000, auto_apply_cpr)
        
        print("CPR module ready - point placement controls available")
        print("CPR will be automatically applied in 3 seconds...")
        
    except Exception as e:
        print(f"Error switching to CPR module: {e}")
        slicer.util.errorDisplay(f"Could not open Curved Planar Reformat module: {str(e)}")

def auto_apply_cpr():
    """
    Automatically apply the CPR processing while keeping the module open for re-application
    """
    try:
        print("Auto-applying CPR...")
        
        # Get the CPR module widget
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
        
        # Try to find and click the Apply button
        apply_button = None
        
        # Strategy 1: Look for the original Apply button in the UI
        if hasattr(cpr_module, 'ui') and hasattr(cpr_module.ui, 'applyButton'):
            apply_button = cpr_module.ui.applyButton
            print("Found original Apply button")
        
        # Strategy 2: Look for our custom large Apply button
        if not apply_button and hasattr(slicer.modules, 'CPRLargeApplyButton'):
            apply_button = slicer.modules.CPRLargeApplyButton
            print("Found custom large Apply button")
        
        # Strategy 3: Search for any Apply button in the CPR widget
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
            
            # Set up monitoring for CPR completion
            setup_cpr_completion_monitor()
            
            print("✓ CPR processing started automatically!")
            print("Module remains open for manual re-application if needed.")
            
        else:
            if not apply_button:
                print("⚠ Could not find Apply button for auto-apply")
            else:
                print("⚠ Apply button found but not enabled - please check CPR configuration")
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
            if slicer.modules.CPRCheckCount > 30:  # Stop after 60 seconds
                stop_cpr_monitoring()
                print("CPR monitoring timed out")
                return
        
        # Check if new volumes have been created (indicating CPR completion)
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
            print("✓ CPR processing completed successfully!")
            if straightened_volumes:
                print(f"  - Created straightened volume(s): {[v.GetName() for v in straightened_volumes]}")
            if projected_volumes:
                print(f"  - Created projected volume(s): {[v.GetName() for v in projected_volumes]}")
            
            stop_cpr_monitoring()
            
            # Show completion message
            print("CPR workflow complete! You can:")
            print("1. View the results in the slice views")
            print("2. Adjust parameters and re-apply if needed")
            print("3. Continue with point placement for lesion analysis")
        
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
            centerline_model = find_recent_centerline_model()
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
                if hasattr(cpr_module.ui, 'resolutionSpinBox'):
                    cpr_module.ui.resolutionSpinBox.setValue(1.0)
                    print("Set resolution to 2.0")
                
                if hasattr(cpr_module.ui, 'thicknessSpinBox'):
                    cpr_module.ui.thicknessSpinBox.setValue(1.0)
                    print("Set thickness to 5.0")
                
                # Final UI update
                slicer.app.processEvents()
                
                # Report setup status
                print("CPR module setup complete with automatic selector configuration:")
                if output_volume_set:
                    print("✓ Output straightened volume selector set")
                else:
                    print("⚠ Output straightened volume selector not found - users should select manually")
                    
                if projected_volume_set:
                    print("✓ Output projected volume selector set")
                else:
                    print("⚠ Output projected volume selector not found - users should select manually")
                    
                if transform_set:
                    print("✓ Output transform selector set")
                else:
                    print("⚠ Output transform selector not found - users should select manually")
                
                if not input_volume:
                    print("Warning: No input volume detected - users should select one manually")
                if not centerline_model:
                    print("Warning: No centerline model detected - users should select one manually")
                
                print("CPR module configured - ready to apply!")
                    
            except Exception as e:
                print(f"Could not configure CPR output options: {e}")

            slicer.app.processEvents()
            
            # Add large green Apply button to CPR module
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
        
        print("Point placement controls created")

        show_point_placement_instructions()
        
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
    Start interactive point placement mode
    """
    try:
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selectionNode:
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
            selectionNode.SetActivePlaceNodeID(point_list.GetID())

        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode:
            interactionNode.SetCurrentInteractionMode(interactionNode.Place)

        start_button.setEnabled(False)
        stop_button.setEnabled(True)
        update_point_count_display(point_list, count_label)
        
        print("Point placement mode started")
        print("Point placement started - place points: 1:pre-lesion, 2:post-lesion, 3:start-slice, 4:end-slice")
        
    except Exception as e:
        print(f"Error starting point placement: {e}")
        slicer.util.errorDisplay(f"Could not start point placement: {str(e)}")

############################################################################## depricated
# def stop_point_placement(point_list, start_button, stop_button, count_label):
#     """
#     Stop interactive point placement mode
#     """
#     try:
#         # Disable placement mode
#         interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
#         if interactionNode:
#             interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
        
#         # Update button states
#         start_button.setEnabled(True)
#         stop_button.setEnabled(False)
        
#         update_point_count_display(point_list, count_label)
        
#         point_count = point_list.GetNumberOfControlPoints()
#         print(f"Point placement mode stopped. Total points: {point_count}")
        
#         if point_count > 0:
#             slicer.util.infoDisplay(f"Lesion analysis point placement stopped!\n\nYou have placed {point_count} analysis points.\n\nYou can now export the points or continue with your lesion analysis.")
#         else:
#             slicer.util.infoDisplay("Point placement stopped!\n\nNo points were placed. You can start placing lesion analysis points again if needed.")
        
#     except Exception as e:
#         print(f"Error stopping point placement: {e}")

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


################################################depricate 
# def export_points_to_file(point_list):
#     """
#     Export measurement points to a file
#     """
#     try:
#         point_count = point_list.GetNumberOfControlPoints()
#         if point_count == 0:
#             slicer.util.infoDisplay("No points to export.")
#             return
        
#         # Get save file path from user
#         file_dialog = qt.QFileDialog()
#         file_dialog.setFileMode(qt.QFileDialog.AnyFile)
#         file_dialog.setAcceptMode(qt.QFileDialog.AcceptSave)
#         file_dialog.setNameFilter("JSON Files (*.json);;CSV Files (*.csv);;All Files (*)")
#         file_dialog.setDefaultSuffix("json")
        
#         if file_dialog.exec_():
#             file_paths = file_dialog.selectedFiles()
#             if file_paths:
#                 file_path = file_paths[0]
                
#                 # Export based on file extension
#                 if file_path.lower().endswith('.csv'):
#                     export_points_to_csv(point_list, file_path)
#                 else:
#                     export_points_to_json(point_list, file_path)
                
#                 slicer.util.infoDisplay(f"Successfully exported {point_count} points to:\n{file_path}")
#                 print(f"Exported {point_count} measurement points to: {file_path}")
        
#     except Exception as e:
#         print(f"Error exporting points: {e}")
#         slicer.util.errorDisplay(f"Could not export points: {str(e)}")

# def export_points_to_json(point_list, file_path):
#     """
#     Export points to JSON format
#     """
#     import json
    
#     points_data = {
#         "name": point_list.GetName(),
#         "description": "Lesion analysis points exported from 3D Slicer workflow",
#         "analysis_type": "lesion_analysis",
#         "point_definitions": {
#             "P1": "Pre-lesion reference point",
#             "P2": "Post-lesion reference point", 
#             "P3": "Start-slice analysis boundary",
#             "P4": "End-slice analysis boundary"
#         },
#         "points": []
#     }
    
#     for i in range(point_list.GetNumberOfControlPoints()):
#         point = [0.0, 0.0, 0.0]
#         point_list.GetNthControlPointPosition(i, point)
#         label = point_list.GetNthControlPointLabel(i)
        
#         points_data["points"].append({
#             "index": i,
#             "label": label,
#             "position": {
#                 "x": point[0],
#                 "y": point[1], 
#                 "z": point[2]
#             }
#         })
    
#     with open(file_path, 'w') as f:
#         json.dump(points_data, f, indent=2)

# def export_points_to_csv(point_list, file_path):
#     """
#     Export points to CSV format
#     """
#     import csv
    
#     with open(file_path, 'w', newline='') as csvfile:
#         writer = csv.writer(csvfile)
#         writer.writerow(['Index', 'Label', 'X', 'Y', 'Z'])
        
#         for i in range(point_list.GetNumberOfControlPoints()):
#             point = [0.0, 0.0, 0.0]
#             point_list.GetNthControlPointPosition(i, point)
#             label = point_list.GetNthControlPointLabel(i)
#             writer.writerow([i, label, point[0], point[1], point[2]])

def setup_point_count_observer(point_list, count_label):
    """
    Set up observer to automatically update point count display
    """
    try:
        if hasattr(point_list, 'PointCountObserver'):
            point_list.RemoveObserver(point_list.PointCountObserver)
        
        observer_id = point_list.AddObserver(point_list.PointModifiedEvent, 
                                           lambda caller, event: update_point_count_display_for_current_list(count_label))
        point_list.PointCountObserver = observer_id
        
        observer_id2 = point_list.AddObserver(point_list.PointAddedEvent, 
                                            lambda caller, event: update_point_count_display_for_current_list(count_label))
        point_list.PointAddObserver = observer_id2
        
        observer_id3 = point_list.AddObserver(point_list.PointRemovedEvent, 
                                            lambda caller, event: update_point_count_display_for_current_list(count_label))
        point_list.PointRemoveObserver = observer_id3
        
    except Exception as e:
        print(f"Error setting up point count observer: {e}")

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

def show_point_placement_instructions():
    """
    Show simplified instructions for lesion analysis point placement
    """
    print("Point placement controls ready")
    print("Use control panel to start placing points: 1:pre-lesion, 2:post-lesion, 3:start-slice, 4:end-slice")

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
    Create a new point list and start placement mode
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
        
        setup_point_count_observer(point_list, count_label)
        
        update_point_count_display(point_list, count_label)
        
        print(f"Created new point list: {point_list.GetName()}")
        print("Point placement mode started")
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
            
            print("Transform removal verification complete")

        success = slicer.app.ioManager().openSaveDataDialog()
        
        if success:
            print("Project saved successfully")

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
    Show a dialog asking user to retry centerline extraction or continue to CPR
    """
    try:
        dialog = qt.QDialog(slicer.util.mainWindow())
        dialog.setWindowTitle("Centerline Extraction Complete")
        dialog.setModal(True)
        dialog.resize(450, 250)
        dialog.setWindowFlags(qt.Qt.Dialog | qt.Qt.WindowTitleHint | qt.Qt.WindowCloseButtonHint)
        layout = qt.QVBoxLayout(dialog)
        title_label = qt.QLabel("Centerline Extraction Completed Successfully!")
        title_label.setStyleSheet("QLabel { font-weight: bold; color: #28a745; margin: 10px; font-size: 16px; }")
        title_label.setAlignment(qt.Qt.AlignCenter)
        layout.addWidget(title_label)
        status_text = "Centerline extraction has completed. You can:"
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
        layout.addSpacing(10)
        instruction_label = qt.QLabel("Choose your next action:")
        instruction_label.setStyleSheet("QLabel { color: #555; margin: 10px; font-size: 12px; font-weight: bold; }")
        layout.addWidget(instruction_label)
        button_layout = qt.QHBoxLayout()
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
        button_layout.addWidget(retry_button)
        
        continue_button = qt.QPushButton("✓ Continue to Analysis")
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
                min-width: 180px;
            }
            QPushButton:hover { 
                background-color: #218838; 
            }
            QPushButton:pressed { 
                background-color: #1e7e34; 
            }
        """)
        continue_button.connect('clicked()', lambda: on_continue_to_cpr(dialog, centerline_model, centerline_curve))
        button_layout.addWidget(continue_button)
        
        layout.addLayout(button_layout)
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


def remove_transforms_from_point_lists():
    """
    Remove all transforms from F-1 point lists before saving
    """
    try:
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        removed_count = 0
        
        for node in fiducial_nodes:
            node_name = node.GetName()
            if node_name == "F-1":
                if node.GetTransformNodeID():
                    transform_name = ""
                    transform_node = node.GetTransformNode()
                    if transform_node:
                        transform_name = transform_node.GetName()
                    
                    node.SetAndObserveTransformNodeID(None)
                    node.Modified()
                    removed_count += 1
                    print(f"Removed transform '{transform_name}' from point list '{node.GetName()}'")
        
        if removed_count > 0:
            slicer.app.processEvents()
            print(f"Removed transforms from {removed_count} F-1 point list(s)")
            print("GUI updated to reflect transform removal")
            return True
        else:
            print("No transforms found on F-1 point lists")
            return False
            
    except Exception as e:
        print(f"Error removing transforms from point lists: {e}")
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
                    display_node.SetSelectedColor(0.0, 0.8, 0.0)
                else:
                    display_node.SetColor(1.0, 0.0, 0.0)
                    display_node.SetSelectedColor(0.8, 0.0, 0.0)
                
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
        print(f"✓ Lesion circles created: {circles_created} circles")
        print(f"✓ Green circle: pre-lesion point")
        print(f"✓ Red circle: post-lesion point")
        print(f"✓ Circles sized according to vessel radius")
        print(f"✓ F-1 point list re-selected for continued placement")
        
        return True
        
    except Exception as e:
        print(f"Error drawing circles on centerline: {e}")
        return False

def create_individual_circle_markups():
    """
    Alternative approach: Create individual circle markup nodes for each centerline point
    """
    try:
        centerline_model = slicer.util.getNode('Centerline model')
        if not centerline_model:
            print("Warning: Could not find 'Centerline model' node")
            return False
        
        points = slicer.util.arrayFromModelPoints(centerline_model)
        radii = slicer.util.arrayFromModelPointData(centerline_model, 'Radius')
        
        if points is None or len(points) == 0:
            print("Warning: No points found in centerline model")
            return False
            
        if radii is None or len(radii) == 0:
            print("Warning: No radius data found in centerline model")
            return False
        
        circles_folder = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLFolderDisplayNode")
        circles_folder.SetName("Centerline Circles")
        
        circles_created = 0
        circle_nodes = []

        step_size = max(1, len(points) // 20)  
        
        for i in range(0, len(points), step_size):
            point = points[i]
            radius = radii[i] if i < len(radii) else 1.0;
            
            # Create individual circle markup
            circle_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsCurveNode")
            circle_node.SetName(f"Circle_{i:03d}")
            
            display_node = circle_node.GetDisplayNode()
            if display_node:
                display_node.SetColor(0.0, 1.0, 0.0)  # Green
                display_node.SetSelectedColor(0.0, 0.8, 0.0)
                display_node.SetLineWidth(2.0)
                display_node.SetVisibility(True)
                display_node.SetPointLabelsVisibility(False)
            
            success = create_axial_circle_points(circle_node, point, radius)
            if success:
                circles_created += 1
                circle_nodes.append(circle_node)
        
        print(f"Created {circles_created} individual circle markups")
        
        slicer.modules.WorkflowCenterlineCircleNodes = circle_nodes
        
        slicer.util.infoDisplay(
            f"Individual Centerline Circles Created!\n\n"
            f"✓ {circles_created} individual circles created\n"
            f"✓ Circles sized according to vessel radius\n"
            f"✓ Visible in all slice views\n\n"
            "Each green circle shows vessel cross-section at centerline points."
        )
        
        return True
        
    except Exception as e:
        print(f"Error creating individual circle markups: {e}")
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

def debug_scene_nodes():
    """
    Debug function to list all nodes in the scene
    """
    try:
        print("=== ALL NODES IN SCENE ===")
        model_nodes = slicer.util.getNodesByClass('vtkMRMLModelNode')
        print(f"Model nodes ({len(model_nodes)}):")
        for i, node in enumerate(model_nodes):
            print(f"  {i+1}. {node.GetName()} (ID: {node.GetID()})")
        
        markup_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsNode')
        print(f"\nMarkup nodes ({len(markup_nodes)}):")
        for i, node in enumerate(markup_nodes):
            print(f"  {i+1}. {node.GetName()} (ID: {node.GetID()}) - Type: {node.GetClassName()}")

        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        print(f"\nVolume nodes ({len(volume_nodes)}):")
        for i, node in enumerate(volume_nodes):
            print(f"  {i+1}. {node.GetName()} (ID: {node.GetID()})")
        seg_nodes = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
        print(f"\nSegmentation nodes ({len(seg_nodes)}):")
        for i, node in enumerate(seg_nodes):
            print(f"  {i+1}. {node.GetName()} (ID: {node.GetID()})")
        
        print("=== END NODE LIST ===")
        
    except Exception as e:
        print(f"Error listing scene nodes: {e}")

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
                print(f"✓ Set segmentation: {stenosis_segmentation.GetName()}")
            else:
                print("Warning: Could not find segmentationSelector")
            
            volume_set = False
            if hasattr(segmentStatisticsWidget, 'scalarVolumeSelector'):
                segmentStatisticsWidget.scalarVolumeSelector.setCurrentNode(analysis_volume)
                slicer.app.processEvents()
                current_volume = segmentStatisticsWidget.scalarVolumeSelector.currentNode()
                if current_volume and current_volume.GetID() == analysis_volume.GetID():
                    print(f"✓ Set scalar volume: {analysis_volume.GetName()}")
                    volume_set = True
                else:
                    print(f"Warning: Volume selection may not have taken effect")
            

            if not volume_set and hasattr(segmentStatisticsWidget, 'scalarVolumeSelector'):
                try:

                    segmentStatisticsWidget.scalarVolumeSelector.setCurrentNodeID(analysis_volume.GetID())
                    slicer.app.processEvents()
                    current_volume = segmentStatisticsWidget.scalarVolumeSelector.currentNode()
                    if current_volume and current_volume.GetID() == analysis_volume.GetID():
                        print(f"✓ Set scalar volume (method 2): {analysis_volume.GetName()}")
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
            
            print(f"Opened Segment Statistics module with auto-selected fields:")
            print(f"  Segmentation: {stenosis_segmentation.GetName()}")
            print(f"  Volume: {analysis_volume.GetName()}")
            print("  Statistics types: Labelmap and Scalar Volume enabled")
            print("  Click 'Apply' to compute statistics")
            
        except Exception as widget_error:
            print(f"Could not auto-select fields in Segment Statistics widget: {str(widget_error)}")
            print("Please manually select the segmentation and volume in the module")
            print(f"  Select segmentation: {stenosis_segmentation.GetName()}")
            print(f"  Select volume: {analysis_volume.GetName()} (look for 'cropped' in name)")
        
        print(f"Opened Segment Statistics module with auto-selected fields")
        
        if volume_set:
            volume_status = f"Cropped Volume: {analysis_volume.GetName()}"
            ready_status = "Ready for analysis!"
            manual_instructions = ""
        else:
            volume_status = f"Please select: {analysis_volume.GetName()} (contains 'cropped')"
            ready_status = "Manual selection needed!"
            manual_instructions = ("If volume not selected automatically:\n"
                                 "• Click Scalar Volume dropdown\n"
                                 "• Select volume with \"cropped\" in name\n"
                                 "• Then click Apply\n\n")
        
        message = (f"Segment Statistics Module Ready!\n\n"
                  f"Module opened\n"
                  f"Segmentation: {stenosis_segmentation.GetName()}\n"
                  f"{volume_status}\n"
                  f"Statistics types enabled\n\n"
                  f"{ready_status}\n\n"
                  f"{manual_instructions}"
                  f"Click 'Apply' in the Segment Statistics module to compute:\n"
                  f"Volume measurements (cm³ and mm³)\n"
                  f"Density statistics (HU)\n"
                  f"Mean, standard deviation, min/max values\n\n"
                  f"Results will be displayed in the module's table.")
        
        slicer.util.infoDisplay(message)
        
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
# END WORKFLOW2 FUNCTIONS
# ===============================================================================

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
