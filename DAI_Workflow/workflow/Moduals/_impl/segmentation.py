from ._common import *  # noqa: F401,F403  (shared imports + logger)
from . import centerline, core, markup, ui, volume  # sibling modules (cross-calls)

__all__ = [
    'ask_user_for_segmentation_import',
    'import_segmentation_file',
    'start_imported_segmentation_workflow',
    'create_threshold_segment_with_markup_only',
    'add_post_threshold_tools_to_left_panel',
    'cleanup_post_threshold_tools',
    'create_threshold_segment',
    'create_segmentation_from_threshold',
    'show_segmentation_in_3d',
    'load_into_segment_editor',
    'select_scissors_tool',
    'on_continue_from_scissors',
    'remove_segment_from_all_segmentations',
    'start_workflow_with_segmentation_dialog',
    'hide_threshold_segmentation_mask',
    'create_segmentation_from_tube',
    'show_segment_statistics',
    'start_with_segment_editor_scissors',
    'create_scissors_tool_button',
    'create_floating_scissors_widget',
    'toggle_scissors_tool_programmatic',
    'cleanup_scissors_tool_ui',
    'reset_segment_editor_module',
    'cleanup_segment_editor_custom_elements',
    'add_scissors_tools_to_initial_interface',
    'update_crop_interface_for_segmentation_phase',
    'toggle_scissors_tool',
]

# Removed ask_user_for_markup_import() function - skipping markup import popup

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
                        volume_node = volume.find_working_volume()
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
        ui.set_3d_view_background_black()
        
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

def create_threshold_segment_with_markup_only():
    """
    Main workflow function with markup import only (no segmentation import)
    """
    volume_node = volume.find_working_volume()
    
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    
    # Initialize workflow flags
    slicer.modules.WorkflowUsingMarkup = False
    slicer.modules.WorkflowUsingImportedSegmentation = False
    
    # Skip markup import popup - continue with normal workflow without markup
    
    # Continue with threshold workflow
    # Use default threshold values instead of prompting user
    threshold_value_low, threshold_value_high = 290.0, 3071.0
    
    segmentation_node = create_segmentation_from_threshold(volume_node, threshold_value_low, threshold_value_high)
    
    if segmentation_node:
        show_segmentation_in_3d(segmentation_node)
        load_into_segment_editor(segmentation_node, volume_node)
        
        # Only add post-threshold tools if markup was actually imported
        if hasattr(slicer.modules, 'WorkflowUsingMarkup') and slicer.modules.WorkflowUsingMarkup:
            add_post_threshold_tools_to_left_panel(segmentation_node, volume_node)
        else:
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
        ui.expand_left_module_panel()
        
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
        
        fiducial_button.connect('clicked()', lambda: markup.create_additional_fiducial_list())
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
        
        curve_button.connect('clicked()', lambda: markup.create_additional_curve_markup())
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
        
        continue_button.connect('clicked()', lambda: centerline.continue_to_centerline_from_left_panel())
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
        logger.debug("Suppressed exception in add_post_threshold_tools_to_left_panel", exc_info=True)

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
        logger.debug("Suppressed exception in cleanup_post_threshold_tools", exc_info=True)

def create_threshold_segment():
    """
    Main workflow function to create a threshold segment with default values or import existing segmentation
    """
    volume_node = volume.find_working_volume()
    
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
    
    # Skip markup import popup - continue with normal workflow without markup
    want_markup = False
    slicer.modules.WorkflowUsingMarkup = False
    
    # If neither segmentation nor markup is imported, continue with normal threshold workflow
    # But if user cancelled both and we were called from crop workflow, go to crop workflow
    if (not want_segmentation and not want_markup) and calling_from_crop:
        # Reset the flag and continue with crop workflow
        slicer.modules.WorkflowDialogShown = False
        volume.start_crop_workflow_directly()
        return
    
    # Continue with normal threshold workflow
    # Use default threshold values instead of prompting user
    threshold_value_low, threshold_value_high = 290.0, 3071.0
    
    segmentation_node = create_segmentation_from_threshold(volume_node, threshold_value_low, threshold_value_high)
    
    if segmentation_node:
        show_segmentation_in_3d(segmentation_node)
        load_into_segment_editor(segmentation_node, volume_node)

# Removed prompt_for_threshold_range() function - using hardcoded values instead

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
        logger.debug("Suppressed exception in create_segmentation_from_threshold", exc_info=True)
    ui.set_3d_view_background_black()
    
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

def on_continue_from_scissors():
    """
    Called when user clicks the continue button after using scissors
    """
    pass
    ui.cleanup_workflow_ui()
    
    # Set 3D view background to black
    ui.set_3d_view_background_black()
    
    # Check if we're in markup workflow mode
    if hasattr(slicer.modules, 'WorkflowUsingMarkup') and slicer.modules.WorkflowUsingMarkup:
        # Open the Data module to show imported markup and created curve models
        core.open_data_module()
    else:
        # Normal workflow - proceed to centerline extraction
        centerline.open_centerline_module()

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
        logger.debug("Suppressed exception in remove_segment_from_all_segmentations", exc_info=True)

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
        volume.start_with_volume_crop()

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
        logger.debug("Suppressed exception in hide_threshold_segmentation_mask", exc_info=True)

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
                    logger.debug("Suppressed exception in show_segment_statistics", exc_info=True)
            
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
        
        # Create segment editor widget with proper keyboard shortcut support
        segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
        
        # Enable undo functionality in the segment editor widget
        segmentEditorWidget.setUndoEnabled(True)
        
        # Make sure the widget can receive focus and keyboard events
        segmentEditorWidget.setFocusPolicy(qt.Qt.StrongFocus)
        
        # Make the segment editor widget visible but small to ensure it can receive events
        # This is a workaround to ensure keyboard shortcuts work
        segmentEditorWidget.resize(1, 1)  # Make it tiny
        segmentEditorWidget.show()
        segmentEditorWidget.hide()  # Hide it but keep it in the widget hierarchy
        
        # Install keyboard shortcuts for Ctrl+Z functionality
        try:
            # Method 1: Install shortcuts on the main window
            main_window = slicer.util.mainWindow()
            if main_window:
                # Create a shortcut for Ctrl+Z that calls the segment editor's undo
                undo_shortcut = qt.QShortcut(qt.QKeySequence("Ctrl+Z"), main_window)
                undo_shortcut.connect('activated()', lambda: core.handle_keyboard_undo(segmentEditorWidget))
                
                # Create a shortcut for Ctrl+Y (redo) as well
                redo_shortcut = qt.QShortcut(qt.QKeySequence("Ctrl+Y"), main_window)
                redo_shortcut.connect('activated()', lambda: core.handle_keyboard_redo(segmentEditorWidget))
                
                # Store shortcut references so they don't get garbage collected
                slicer.modules.WorkflowUndoShortcut = undo_shortcut
                slicer.modules.WorkflowRedoShortcut = redo_shortcut
                
                logger.info("Installed global Ctrl+Z and Ctrl+Y shortcuts")
            
            # Method 2: Also try to install shortcuts directly on the segment editor widget
            if segmentEditorWidget:
                widget_undo_shortcut = qt.QShortcut(qt.QKeySequence("Ctrl+Z"), segmentEditorWidget)
                widget_undo_shortcut.connect('activated()', lambda: core.handle_keyboard_undo(segmentEditorWidget))
                
                widget_redo_shortcut = qt.QShortcut(qt.QKeySequence("Ctrl+Y"), segmentEditorWidget)
                widget_redo_shortcut.connect('activated()', lambda: core.handle_keyboard_redo(segmentEditorWidget))
                
                # Store these as well
                slicer.modules.WorkflowWidgetUndoShortcut = widget_undo_shortcut
                slicer.modules.WorkflowWidgetRedoShortcut = widget_redo_shortcut
                
                logger.info("Installed widget-specific Ctrl+Z and Ctrl+Y shortcuts")
                
        except Exception as shortcut_error:
            logger.info(f"Warning: Could not install keyboard shortcuts: {shortcut_error}")
        
        # Configure segment editor for better undo support
        try:
            # Enable maximum undo levels for the segmentation
            segmentation = segmentation_node.GetSegmentation()
            if segmentation and hasattr(segmentation, 'SetMaximumNumberOfUndoStates'):
                segmentation.SetMaximumNumberOfUndoStates(20)  # Allow plenty of undo levels
            
            # Enable scene undo as backup
            slicer.mrmlScene.SetUndoOn()
            slicer.mrmlScene.SetMaximumNumberOfUndoLevels(20)
            
            logger.info("Configured undo system with 20 levels for both segmentation and scene")
        except Exception as undo_config_error:
            logger.info(f"Warning: Could not configure undo system: {undo_config_error}")
        
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
                finish_button.connect('clicked()', lambda: volume.on_finish_cropping())
                
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
                
                success = ui.add_buttons_to_crop_module(crop_widget, scissors_button, finish_button)
                
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
        finish_button.connect('clicked()', lambda: volume.on_finish_cropping())
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
        logger.debug("Suppressed exception in create_floating_scissors_widget", exc_info=True)

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
        
        # Clean up keyboard shortcuts
        if hasattr(slicer.modules, 'WorkflowUndoShortcut'):
            try:
                shortcut = slicer.modules.WorkflowUndoShortcut
                shortcut.setParent(None)
                del slicer.modules.WorkflowUndoShortcut
                logger.info("Cleaned up Ctrl+Z shortcut")
            except Exception:
                logger.debug("Suppressed exception in cleanup_scissors_tool_ui", exc_info=True)
        
        if hasattr(slicer.modules, 'WorkflowRedoShortcut'):
            try:
                shortcut = slicer.modules.WorkflowRedoShortcut
                shortcut.setParent(None)
                del slicer.modules.WorkflowRedoShortcut
                logger.info("Cleaned up Ctrl+Y shortcut")
            except Exception:
                logger.debug("Suppressed exception in cleanup_scissors_tool_ui", exc_info=True)
        
        # Clean up widget-specific shortcuts
        if hasattr(slicer.modules, 'WorkflowWidgetUndoShortcut'):
            try:
                shortcut = slicer.modules.WorkflowWidgetUndoShortcut
                shortcut.setParent(None)
                del slicer.modules.WorkflowWidgetUndoShortcut
                logger.info("Cleaned up widget Ctrl+Z shortcut")
            except Exception:
                logger.debug("Suppressed exception in cleanup_scissors_tool_ui", exc_info=True)
        
        if hasattr(slicer.modules, 'WorkflowWidgetRedoShortcut'):
            try:
                shortcut = slicer.modules.WorkflowWidgetRedoShortcut
                shortcut.setParent(None)
                del slicer.modules.WorkflowWidgetRedoShortcut
                logger.info("Cleaned up widget Ctrl+Y shortcut")
            except Exception:
                logger.debug("Suppressed exception in cleanup_scissors_tool_ui", exc_info=True)
        
        for attr in ['WorkflowSegmentationNode', 'WorkflowScissorsActive']:
            if hasattr(slicer.modules, attr):
                delattr(slicer.modules, attr)
        
        ui.restore_original_crop_apply_button()
        
    except Exception as e:
        logger.debug("Suppressed exception in cleanup_scissors_tool_ui", exc_info=True)

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
        logger.debug("Suppressed exception in cleanup_segment_editor_custom_elements", exc_info=True)

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
        continue_button.connect('clicked()', lambda: volume.finish_custom_crop_workflow())
        layout.addWidget(continue_button)
        
        # Re-add stretch to push everything to the top
        layout.addStretch()
        
        # Store references
        slicer.modules.CustomScissorsButton = scissors_button
        slicer.modules.CustomContinueButton = continue_button
        
        # Resize the widget to accommodate new buttons
        crop_widget.setFixedHeight(400)
        
    except Exception as e:
        logger.debug("Suppressed exception in add_scissors_tools_to_initial_interface", exc_info=True)

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
        logger.info(f"Error in update_crop_interface_for_segmentation_phase: {e}")

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
        logger.info(f"Error in toggle_scissors_tool: {e}")
