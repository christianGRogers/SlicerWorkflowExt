import slicer
import qt
import vtk
import math

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

def create_threshold_segment():
    """
    Main workflow function to create a threshold segment with user input
    """
    volume_node = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
    
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    
    threshold_value_low = prompt_for_threshold("lower threshold value", default_value=290)
    threshold_value_high = prompt_for_threshold("upper threshold value", default_value=3071)
    
    if threshold_value_low is None or threshold_value_high is None:
        print("User cancelled threshold input")
        return
    
    segmentation_node = create_segmentation_from_threshold(volume_node, threshold_value_low, threshold_value_high)
    
    if segmentation_node:
        show_segmentation_in_3d(segmentation_node)
        load_into_segment_editor(segmentation_node, volume_node)
        print(f"Successfully created threshold segment with range: {threshold_value_low} - {threshold_value_high}")

def prompt_for_threshold(label, default_value=0):
    """
    Show a popup dialog to get threshold value from user
    """
    dialog = qt.QInputDialog()
    dialog.setWindowTitle("Threshold Segmentation")
    dialog.setLabelText(f"Enter {label} (range: -1024 to 3071):")
    dialog.setInputMode(qt.QInputDialog.DoubleInput)
    dialog.setDoubleRange(-1024.0, 3071.0)
    dialog.setDoubleValue(default_value)
    dialog.setDoubleDecimals(2)
    
    if dialog.exec_():
        return dialog.doubleValue()
    else:
        return None

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
    slicer.util.infoDisplay("3D threshold segmentation created and displayed in 3D view!")

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
            continue_button = qt.QPushButton("DONE WITH SCISSORS - CONTINUE TO CENTERLINE")
            continue_button.setStyleSheet("""
                QPushButton { 
                    background-color: #28a745; 
                    color: white; 
                    border: none; 
                    padding: 15px; 
                    font-weight: bold;
                    border-radius: 8px;
                    margin: 10px;
                    font-size: 14px;
                    min-height: 50px;
                }
                QPushButton:hover { 
                    background-color: #218838; 
                }
                QPushButton:pressed { 
                    background-color: #1e7e34; 
                }
            """)
            continue_button.connect('clicked()', lambda: on_continue_from_scissors())
            if hasattr(segment_editor_main, 'layout'):
                layout = segment_editor_main.layout()
                if layout:
                    layout.addWidget(continue_button)
                    print("Added continue button to Segment Editor")
                    slicer.modules.SegmentEditorContinueButton = continue_button
                    return
        create_continue_dialog()
        
    except Exception as e:
        print(f"Error adding continue button to segment editor: {e}")
        pass

def create_continue_dialog():
    """
    Create a floating dialog with a continue button as fallback
    """
    try:
        dialog = qt.QDialog(slicer.util.mainWindow())
        dialog.setWindowTitle("Scissors Tool - Continue")
        dialog.setModal(False)
        dialog.resize(400, 120)
        dialog.setWindowFlags(qt.Qt.Tool | qt.Qt.WindowStaysOnTopHint)

        layout = qt.QVBoxLayout(dialog)

        instruction_label = qt.QLabel("Use the Scissors tool to crop your vessel, then:")
        instruction_label.setStyleSheet("QLabel { color: #333; margin: 10px; font-size: 12px; }")
        instruction_label.setWordWrap(True)
        layout.addWidget(instruction_label)

        continue_button = qt.QPushButton("DONE WITH SCISSORS - CONTINUE TO CENTERLINE")
        continue_button.setStyleSheet("""
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
        
        continue_button.connect('clicked()', lambda: on_continue_from_scissors_with_dialog(dialog))
        layout.addWidget(continue_button)

        dialog.show()

        slicer.modules.SegmentEditorContinueDialog = dialog
        
        print("Created continue dialog for scissors tool")
        
    except Exception as e:
        print(f"Error creating continue dialog: {e}")

def on_continue_from_scissors():
    """
    Called when user clicks the continue button after using scissors
    """
    print("User clicked continue from scissors tool - opening centerline extraction module...")

    cleanup_continue_ui()

    cleanup_workflow_ui()

    open_centerline_module()

def on_continue_from_scissors_with_dialog(dialog):
    """
    Called when user clicks continue button in the dialog version
    """
    print("User clicked continue from scissors tool - opening centerline extraction module...")

    try:
        dialog.close()
        dialog.setParent(None)
        if hasattr(slicer.modules, 'SegmentEditorContinueDialog'):
            del slicer.modules.SegmentEditorContinueDialog
    except Exception as e:
        print(f"Error cleaning up continue dialog: {e}")

    cleanup_continue_ui()
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
    Set up monitoring to detect when user finishes cropping and open centerline module
    """
    create_finish_cropping_button(segment_editor_widget)

def create_finish_cropping_button(segment_editor_widget):
    """
    Create a button that users can click when they finish cropping
    """
    try:
        main_window = slicer.util.mainWindow()
        
        dock_widget = qt.QDockWidget("Workflow Control", main_window)
        dock_widget.setAllowedAreas(qt.Qt.LeftDockWidgetArea | qt.Qt.RightDockWidgetArea)
        dock_widget.setFeatures(qt.QDockWidget.DockWidgetMovable | qt.QDockWidget.DockWidgetFloatable)

        widget_content = qt.QWidget()
        dock_widget.setWidget(widget_content)

        layout = qt.QVBoxLayout(widget_content)

        label = qt.QLabel("Threshold Workflow")
        label.setStyleSheet("QLabel { font-weight: bold; color: #0078d4; margin: 5px; font-size: 14px; }")
        layout.addWidget(label)

        instruction_label = qt.QLabel("Use the Scissors tool to crop your segmentation,\nthen click the button below to continue.")
        instruction_label.setStyleSheet("QLabel { color: #333; margin: 5px; }")
        instruction_label.setWordWrap(True)
        layout.addWidget(instruction_label)

        finish_button = qt.QPushButton("Finish Cropping & Open Centerline Module")
        finish_button.setStyleSheet("""
            QPushButton { 
                background-color: #0078d4; 
                color: white; 
                border: none; 
                padding: 10px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 5px;
                font-size: 12px;
            }
            QPushButton:hover { 
                background-color: #106ebe; 
            }
            QPushButton:pressed { 
                background-color: #005a9e; 
            }
        """)
        finish_button.connect('clicked()', lambda: on_finish_cropping_with_cleanup(dock_widget))
        layout.addWidget(finish_button)

        layout.addStretch()
        main_window.addDockWidget(qt.Qt.RightDockWidgetArea, dock_widget)
        dock_widget.show()
        slicer.modules.WorkflowDockWidget = dock_widget
        
        print("Finish cropping button created in dock widget")
        
    except Exception as e:
        print(f"Error creating finish cropping button: {e}")
        create_simple_workflow_dialog()

def create_simple_workflow_dialog():
    """
    Fallback: Create a simple dialog for workflow control
    """
    try:
        dialog = qt.QDialog(slicer.util.mainWindow())
        dialog.setWindowTitle("Workflow Control")
        dialog.setModal(False) 
        dialog.resize(300, 150)
        
        layout = qt.QVBoxLayout(dialog)
        
        label = qt.QLabel("Use Scissors tool to crop, then:")
        layout.addWidget(label)
        
        button = qt.QPushButton("Finish Cropping & Open Centerline Module")
        button.connect('clicked()', lambda: on_finish_cropping_with_dialog_cleanup(dialog))
        layout.addWidget(button)
        
        dialog.show()

        slicer.modules.WorkflowDialog = dialog
        
        print("Created fallback workflow dialog")
        
    except Exception as e:
        print(f"Error creating workflow dialog: {e}")
        print("Instructions: After cropping with scissors tool, run 'open_centerline_module()' to continue")

def on_finish_cropping_with_cleanup(dock_widget):
    """
    Called when user clicks finish cropping button in dock widget
    """
    print("User finished cropping - opening centerline extraction module...")

    try:
        dock_widget.close()
        dock_widget.setParent(None)
        if hasattr(slicer.modules, 'WorkflowDockWidget'):
            del slicer.modules.WorkflowDockWidget
        print("Workflow dock widget cleaned up")
    except Exception as e:
        print(f"Error cleaning up dock widget: {e}")

    open_centerline_module()

def on_finish_cropping_with_dialog_cleanup(dialog):
    """
    Called when user clicks finish cropping button in dialog
    """
    print("User finished cropping - opening centerline extraction module...")
    
    try:
        dialog.close()
        dialog.setParent(None)
        if hasattr(slicer.modules, 'WorkflowDialog'):
            del slicer.modules.WorkflowDialog
        print("Workflow dialog cleaned up")
    except Exception as e:
        print(f"Error cleaning up dialog: {e}")
    open_centerline_module()

def on_finish_cropping(segment_editor_widget):
    """
    Called when user clicks the finish cropping button (legacy function)
    """
    print("User finished cropping - opening centerline extraction module...")
    cleanup_workflow_ui()
    open_centerline_module()

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
    
    slicer.util.infoDisplay(
        "ROI automatically created to fit the entire volume!\n\n" +
        "The yellow ROI box shows the current crop boundaries.\n" +
        "Adjust the ROI handles to select your region of interest,\n" +
        "then click 'Apply' to crop. The workflow will continue automatically."
    )
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
            
            # Remove the original volume
            slicer.mrmlScene.RemoveNode(original_volume_node)
            
            # Auto-delete the ROI node after cropping
            roi_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsROINode')
            for roi_node in roi_nodes:
                if 'crop' in roi_node.GetName().lower():
                    slicer.mrmlScene.RemoveNode(roi_node)
                    print(f"Automatically deleted ROI: {roi_node.GetName()}")
            
            slicer.util.infoDisplay(f"Cropped volume '{node.GetName()}' detected. ROI automatically deleted. Continuing workflow.")
            create_threshold_segment()
            return



def prompt_for_endpoints():
    """
    Prompt user to add start and end points for centerline extraction using default GUI
    """
    try:
        slicer.util.infoDisplay(
            "Centerline extraction configured!\n\n"
            "✓ New endpoint point list automatically created\n"
            "✓ New centerline model automatically selected\n\n"
            "Next step: Add endpoints for centerline extraction:\n"
            "1. In the Extract Centerline module, find the 'Endpoints' section\n"
            "2. The 'CenterlineEndpoints' point list is already selected\n"
            "3. Click the placement button (looks like a fiducial marker) to start placing points\n"
            "4. Place fiducial points on your vessel:\n"
            "   - Click once to place the START point\n"
            "   - Click again to place the END point\n"
            "5. Press ESC to exit placement mode\n"
            "6. Click 'Apply' to run the centerline extraction\n\n"
            "The workflow will automatically continue once extraction is complete."
        )
        setup_centerline_completion_monitor()
        
    except Exception as e:
        print(f"Error prompting for endpoints: {e}")
        slicer.util.infoDisplay(
            "Centerline extraction configured!\n\n"
            "Please add start and end points using the Extract Centerline module:\n"
            "1. Find the 'Endpoints' section\n"
            "2. Use the fiducial placement tools to add endpoints\n"
            "3. Click 'Apply' to run extraction"
        )

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
        
        slicer.util.infoDisplay(
            "Centerline extraction complete!\n\n"
            "✓ Switched to Curved Planar Reformat module\n"
            "✓ Centerline automatically selected\n"
            "✓ Output volume and transform automatically created\n"
            "✓ CPR automatically applied\n"
            "✓ Straightened volume now visible in all views\n\n"
            "A new point list has been created for lesion analysis.\n"
            "Place points in order: 1 (pre-lesion) → 2 (post-lesion) → 3 (start-slice) → 4 (end-slice)\n\n"
            "You can now view the straightened volume and perform lesion analysis."
        )
        
    except Exception as e:
        print(f"Error switching to CPR module: {e}")
        slicer.util.errorDisplay(f"Could not open Curved Planar Reformat module: {str(e)}")

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
            
            # Configure output nodes and settings
            try:
                # Create new output volume for straightened result
                output_volume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
                output_volume.SetName("Straightened Volume")
                output_volume.CreateDefaultDisplayNodes()
                
                # Create new transform node
                transform_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTransformNode")
                transform_node.SetName("Straightening transform")
                
                # Store references for later use
                slicer.modules.WorkflowStraightenedVolume = output_volume
                slicer.modules.WorkflowStraighteningTransform = transform_node
                
                # Process events to ensure nodes are properly added to scene
                slicer.app.processEvents()
                
                # Set output volume selector with retry mechanism
                output_volume_set = False
                for output_selector_name in ['outputVolumeSelector', 'straightenedVolumeSelector', 'outputSelector']:
                    if hasattr(cpr_module.ui, output_selector_name):
                        selector = getattr(cpr_module.ui, output_selector_name)
                        
                        # Enable "create new" mode first if available
                        create_new_checkbox = None
                        for create_new_attr in ['createNewVolumeCheckBox', 'createNewOutputCheckBox']:
                            if hasattr(cpr_module.ui, create_new_attr):
                                create_new_checkbox = getattr(cpr_module.ui, create_new_attr)
                                create_new_checkbox.setChecked(False)  # Disable create new to use existing
                                break
                        
                        # Force refresh the selector's node list
                        if hasattr(selector, 'updateMRMLFromWidget'):
                            selector.updateMRMLFromWidget()
                        
                        # Set the node
                        selector.setCurrentNode(output_volume)
                        
                        # Force update again
                        slicer.app.processEvents()
                        
                        # Verify the selection took effect
                        if selector.currentNode() == output_volume:
                            print(f"Successfully set output volume using {output_selector_name}: {output_volume.GetName()}")
                            output_volume_set = True
                            break
                        else:
                            print(f"Failed to set output volume using {output_selector_name}")
                
                if not output_volume_set:
                    print("Warning: Could not find or set output volume selector")
                
                # Set transform selector with retry mechanism
                transform_set = False
                for transform_selector_name in ['outputTransformSelector', 'transformSelector', 'outputTransformNodeSelector']:
                    if hasattr(cpr_module.ui, transform_selector_name):
                        selector = getattr(cpr_module.ui, transform_selector_name)
                        
                        # Enable "create new" mode first if available
                        create_new_checkbox = None
                        for create_new_attr in ['createNewTransformCheckBox', 'createNewTransformNodeCheckBox']:
                            if hasattr(cpr_module.ui, create_new_attr):
                                create_new_checkbox = getattr(cpr_module.ui, create_new_attr)
                                create_new_checkbox.setChecked(False)  # Disable create new to use existing
                                break
                        
                        # Force refresh the selector's node list
                        if hasattr(selector, 'updateMRMLFromWidget'):
                            selector.updateMRMLFromWidget()
                        
                        # Set the node
                        selector.setCurrentNode(transform_node)
                        
                        # Force update again
                        slicer.app.processEvents()
                        
                        # Verify the selection took effect
                        if selector.currentNode() == transform_node:
                            print(f"Successfully set transform using {transform_selector_name}: {transform_node.GetName()}")
                            transform_set = True
                            break
                        else:
                            print(f"Failed to set transform using {transform_selector_name}")
                
                if not transform_set:
                    print("Warning: Could not find or set transform selector")
                
                # Set resolution and thickness parameters
                if hasattr(cpr_module.ui, 'resolutionSpinBox'):
                    cpr_module.ui.resolutionSpinBox.setValue(1.0)
                    print("Set resolution to 2.0")
                
                if hasattr(cpr_module.ui, 'thicknessSpinBox'):
                    cpr_module.ui.thicknessSpinBox.setValue(1.0)
                    print("Set thickness to 5.0")
                
                # Final UI update
                slicer.app.processEvents()
                
                print("CPR module configured with output nodes")
                    
            except Exception as e:
                print(f"Could not configure CPR output options: {e}")

            slicer.app.processEvents()

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
            "Click 'Start Placing Points' to add lesion analysis points in order:\n"
            "1: pre-lesion → 2: post-lesion → 3: start-slice → 4: end-slice"
        )
        instruction_label.setStyleSheet("QLabel { color: #333; margin: 5px; }")
        instruction_label.setWordWrap(True)
        layout.addWidget(instruction_label)
        
        count_label = qt.QLabel("Points placed: 0")
        count_label.setStyleSheet("QLabel { color: #666; margin: 5px; font-weight: bold; }")
        layout.addWidget(count_label)
        
        start_button = qt.QPushButton("Start Placing Points (New Point List)")
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
        
        clear_button = qt.QPushButton("Clear All Points")
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
        
        export_button = qt.QPushButton("Export Points & Continue")
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
        slicer.util.infoDisplay("Lesion analysis point placement started!\n\nPlace points in order:\n1: pre-lesion → 2: post-lesion → 3: start-slice → 4: end-slice\n\nClick 'Stop Placing Points' when finished.")
        
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
            slicer.util.infoDisplay("No points to clear.")
            return
        
        result = slicer.util.confirmYesNoDisplay(f"Are you sure you want to clear all {point_count} measurement points?")
        if result:
            point_list.RemoveAllControlPoints()
            update_point_count_display(point_list, count_label)
            print("All measurement points cleared")
            slicer.util.infoDisplay("All measurement points have been cleared.")
        
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
    Show detailed instructions for lesion analysis point placement
    """
    try:
        instructions = (
            "Lesion Analysis Point Placement\n\n"
            "Instructions for placing lesion analysis points:\n\n"
            "1. Click 'Start Placing Points' in the control panel\n"
            "2. Place points in the following order:\n\n"
            "   1: pre-lesion - Click upstream of the lesion\n"
            "   2: post-lesion - Click downstream of the lesion\n"
            "   3: start-slice - Click at the beginning of analysis region\n"
            "   4: end-slice - Click at the end of analysis region\n\n"
            "3. Use the curved reformat view to navigate along the vessel\n"
            "4. Click 'Stop Placing Points' when finished\n"
            "5. Export your points to save the lesion analysis measurements\n\n"
            "Tips:\n"
            "• Points will be automatically labeled for lesion analysis\n"
            "• Place points accurately for precise measurements\n"
            "• You can clear and restart if needed\n"
            "• Additional points beyond point 4 will be labeled as 'additional'"
        )
        dialog = qt.QMessageBox()
        dialog.setIcon(qt.QMessageBox.Information)
        dialog.setWindowTitle("Lesion Analysis Point Placement")
        dialog.setText(instructions)
        dialog.setStandardButtons(qt.QMessageBox.Ok)
        dialog.exec_()
        
    except Exception as e:
        print(f"Error showing point placement instructions: {e}")
        slicer.util.infoDisplay("Lesion analysis point placement controls are ready. Use the control panel to start placing points.")

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
            print(f"Automatically applied 'Straightening transform' to point list '{point_list.GetName()}'")
            
            # Show confirmation to user
            slicer.util.infoDisplay(
                f"Transform Applied!\n\n"
                f"Automatically applied 'Straightening transform' to the new F-1 point list.\n\n"
                "Points will now be placed in the straightened coordinate system."
            )
            return True
        else:
            # Straightening transform not found
            transform_names = [node.GetName() for node in transform_nodes]
            print(f"'Straightening transform' not found. Available transforms: {', '.join(transform_names)}")
            
            slicer.util.infoDisplay(
                f"Straightening Transform Not Found!\n\n"
                f"Looking for 'Straightening transform' but found:\n"
                f"{', '.join(transform_names)}\n\n"
                "Point list will use default coordinate system. You can manually apply a transform if needed."
            )
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
        
        slicer.util.infoDisplay(
            f"New F-1 point list created!\n\n"
            "Point placement started!\n\n"
            "Place points in order:\n"
            "1: pre-lesion → 2: post-lesion → 3: start-slice → 4: end-slice\n\n"
            "Click anywhere in the slice views to place points.\n"
            "Use 'Clear All Points' to reset if needed."
        )
        
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
            slicer.util.infoDisplay("No F-1 point list found to clear.")
            return
        
        node_count = len(lesion_analysis_nodes)
        total_points = sum(node.GetNumberOfControlPoints() for node in lesion_analysis_nodes)
        
        result = slicer.util.confirmYesNoDisplay(
            f"Are you sure you want to clear the F-1 point list?\n\n"
            f"This will remove {node_count} point list(s) containing {total_points} total points."
        )
        
        if result:
            for node in lesion_analysis_nodes:
                slicer.mrmlScene.RemoveNode(node)
                print(f"Removed point list: {node.GetName()}")
            

            if hasattr(slicer.modules, 'CurrentLesionAnalysisPointList'):
                del slicer.modules.CurrentLesionAnalysisPointList

            interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
            if interactionNode:
                interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
            
            count_label.setText("Points placed: 0")
            
            print(f"Cleared {node_count} F-1 point(s)")
            slicer.util.infoDisplay(f"Successfully cleared {node_count} F-1 point list(s) with {total_points} total points.")
        
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
            result = slicer.util.confirmYesNoDisplay(
                "No F-1 point list found to export.\n\n"
                "Do you still want to save the project and continue to workflow2?"
            )
            if not result:
                return
        else:
            total_points = sum(node.GetNumberOfControlPoints() for node in lesion_analysis_nodes)
            result = slicer.util.confirmYesNoDisplay(
                f"Ready to export project with {len(lesion_analysis_nodes)} F-1 point list(s) "
                f"containing {total_points} total lesion analysis points.\n\n"
                "This will save the Slicer project and continue to workflow2.py for centerline analysis.\n\n"
                "Continue with export and workflow2?"
            )
            if not result:
                return

        # Remove transforms from point lists before saving
        if lesion_analysis_nodes:
            print("=== REMOVING TRANSFORMS FROM F-1 POINT LISTS BEFORE EXPORT ===")
            
            # First check current status
            debug_point_list_transforms()
            
            # Remove transforms
            transforms_removed = remove_transforms_from_point_lists()
            
            # If standard removal didn't work, force it
            if not transforms_removed:
                print("Standard removal didn't find transforms, forcing removal...")
                force_remove_all_transforms()
            
            # Verify removal was successful
            print("=== VERIFYING TRANSFORM REMOVAL ===")
            debug_point_list_transforms()
            
            slicer.util.infoDisplay(
                "Transforms Removed!\n\n"
                "All transforms have been removed from F-1 point lists before export.\n"
                "Points are now in their final coordinate system for analysis.\n\n"
                "Check the console for detailed verification."
            )

        success = slicer.app.ioManager().openSaveDataDialog()
        
        if success:
            print("Project saved successfully using standard Slicer save")

            slicer.util.infoDisplay(
                "Project successfully saved!\n\n"
                "Now starting centerline and tube mask creation workflow..."
            )

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
            
            success = create_closed_curve_circle(circle_node, center_point, radius)
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