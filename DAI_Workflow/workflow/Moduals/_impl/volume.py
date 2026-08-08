from ._common import *  # noqa: F401,F403  (shared imports + logger)
from . import centerline, core, markup, segmentation, ui  # sibling modules (cross-calls)

__all__ = [
    'find_working_volume',
    'get_volume_slice_thickness',
    'on_finish_cropping',
    '_load_volume_from_file_list',
    '_load_as_volume_sequence',
    'setup_volume_addition_monitor',
    'create_volume_waiting_status_widget',
    'update_volume_waiting_status',
    'cleanup_volume_waiting_status_widget',
    'cancel_volume_waiting',
    'check_for_volume_addition',
    'stop_volume_addition_monitoring',
    'start_crop_workflow_directly',
    'start_with_volume_crop',
    'setup_crop_completion_monitor',
    'check_crop_completion',
    'set_cropped_volume_visible',
    'on_restart_cropping',
    'reset_crop_module_safely',
    'restart_cropping_workflow_safely',
    'clear_workflow_for_cropping_restart',
    'add_cropped_volume_to_3d_scene',
    'fix_volume_spacing_manually',
    'reset_volume_to_identity_matrix',
    'analyze_volume_properties',
    'test_restart_cropping_with_preservation',
    'reset_crop_module_to_default',
    'cleanup_crop_module_custom_elements',
    'restart_cropping_simple',
    'manual_restart_cropping_help',
    'test_crop_module_reset',
    'cropVolumeWithNamedROI',
    'execute_initial_custom_crop',
    'execute_custom_crop',
    'continue_workflow_after_custom_crop',
    'ensure_crop_roi_exists',
    'finish_custom_crop_workflow',
    'use_custom_crop_instead_of_module',
]

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
            logger.error(f"Warning: Could not get active volume from selection node: {e}")
        
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

def on_finish_cropping():
    """
    Called when user clicks the finish cropping button after using scissors tool
    """
    try:
        pass
        
        # First collapse/hide the crop volume GUI completely
        ui.collapse_crop_volume_gui()
        
        # Clean up scissors tool UI
        segmentation.cleanup_scissors_tool_ui()
        
        # Continue to the next step in the workflow
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
        
        pass
        
    except Exception as e:
        logger.debug("Suppressed exception in on_finish_cropping", exc_info=True)

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
            logger.debug("Suppressed exception in _load_volume_from_file_list", exc_info=True)
        
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
            logger.debug("Suppressed exception in _load_volume_from_file_list", exc_info=True)
        except Exception as sitk_error:
            logger.debug("Suppressed exception in _load_volume_from_file_list", exc_info=True)
        
        # Method 3: Try VTK ImageReader2 with file pattern
        try:
            
            # Find a pattern in the files
            first_file = os.path.basename(file_list[0])
            if 'CTDC' in first_file:
                # For files like i1559699.CTDC.1, create pattern like i%d.CTDC.%d
                base_pattern = first_file.split('.')[0]
                pattern_file = os.path.join(os.path.dirname(file_list[0]), f"{base_pattern[:8]}*.CTDC.*")
        
        except Exception as pattern_error:
            logger.debug("Suppressed exception in _load_volume_from_file_list", exc_info=True)
        
        return None
        
    except Exception as e:
        return None

def _load_as_volume_sequence(dicom_files, directory):
    """Try to load DICOM files as a volume sequence."""
    try:
        
        # Sort files by slice number
        sorted_files = sorted(dicom_files, key=lambda x: core._extract_slice_number(x))
        
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
                    ui.set_3d_view_background_black()
                    qt.QTimer.singleShot(1000, start_with_volume_crop)
                    return True
                elif dims[2] > 1:
                    base_volume.SetName("CT_PartialSeries")
                    ui.set_3d_view_background_black()
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
                                ui.set_3d_view_background_black()
                                qt.QTimer.singleShot(1000, start_with_volume_crop)
                                return True
                            else:
                                # Clean up single slice
                                slicer.mrmlScene.RemoveNode(temp_volume)
                except Exception as chunk_error:
                    logger.debug("Suppressed exception in _load_as_volume_sequence", exc_info=True)
                    
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
        logger.debug("Suppressed exception in setup_volume_addition_monitor", exc_info=True)

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
        logger.debug("Suppressed exception in create_volume_waiting_status_widget", exc_info=True)

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
        logger.debug("Suppressed exception in update_volume_waiting_status", exc_info=True)

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
        logger.debug("Suppressed exception in cleanup_volume_waiting_status_widget", exc_info=True)

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
        logger.debug("Suppressed exception in cancel_volume_waiting", exc_info=True)

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
            ui.set_3d_view_background_black()

            stop_volume_addition_monitoring()
            if volume_nodes:
                latest_volume = volume_nodes[-1]
            
            qt.QTimer.singleShot(2000, cleanup_volume_waiting_status_widget)
            # Start crop workflow directly when volume is detected
            qt.QTimer.singleShot(500, start_with_volume_crop)
            
    except Exception as e:
        logger.debug("Suppressed exception in check_for_volume_addition", exc_info=True)

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
        logger.debug("Suppressed exception in stop_volume_addition_monitoring", exc_info=True)

def start_crop_workflow_directly():
    """
    Start the crop workflow directly without showing segmentation dialog again
    """
    # Collapse the left module panel at workflow start to maximize view space
    ui.collapse_left_module_panel()
    
    # Set 3D view background to black at the start of workflow
    ui.set_3d_view_background_black()
    
    # Set three-up view (Red, Green, Yellow) before cropping
    ui.set_three_up_view()
    
    volume_node = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    
    # Use custom crop interface instead of standard module
    ui.create_initial_custom_crop_interface()

def start_with_volume_crop():
    """
    Start the workflow using the custom crop interface instead of the standard crop module.
    """
    # Collapse the left module panel at workflow start to maximize view space
    ui.collapse_left_module_panel()
    
    # Set 3D view background to black at the start of workflow
    ui.set_3d_view_background_black()
    
    # Set three-up view (Red, Green, Yellow) before cropping
    ui.set_three_up_view()
    
    volume_node = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    
    # Use custom crop interface instead of standard module
    ui.create_initial_custom_crop_interface()
    
    volume_node = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
    if not volume_node:
        slicer.util.errorDisplay("No volume loaded. Please load a volume first.")
        return
    
    # Use custom crop interface instead of standard module
    ui.create_initial_custom_crop_interface()
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
    
    ui.add_large_crop_apply_button()
    
    qt.QTimer.singleShot(2000, ui.add_large_crop_apply_button)
    
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
                    ui.disable_crop_apply_button(crop_widget)
                    # Set flag to prevent button restoration
                    slicer.modules.WorkflowCropCompleted = True
            except Exception as e:
                logger.debug("Suppressed exception in check_crop_completion", exc_info=True)
            
            # Switch to 3D-only view after cropping is complete
            qt.QTimer.singleShot(500, ui.set_3d_only_view)
            
            pass
            segmentation.create_threshold_segment()
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

def on_restart_cropping(dialog, centerline_model=None, centerline_curve=None):
    """
    Called when user chooses to restart cropping while preserving existing centerlines.
    Uses staged approach with timers to prevent freezing.
    """
    try:
        # Stop ALL centerline monitoring systems to prevent double dialogs
        centerline.stop_all_centerline_monitoring()
        
        # Reset the dialog flag to allow future dialogs
        if hasattr(slicer.modules, 'CenterlineDialogShown'):
            slicer.modules.CenterlineDialogShown = False
        
        dialog.close()
        dialog.setParent(None)
        
        # Hide the custom crop interface during recropping
        ui.cleanup_custom_crop_interface()
        
        # Show progress message
        
        # Stage 1: Store centerlines immediately
        centerline.store_existing_centerlines()
        
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
        logger.debug("Suppressed exception in reset_crop_module_safely", exc_info=True)

def restart_cropping_workflow_safely():
    """
    Safely restart the cropping workflow with proper timing and error handling.
    Shows the custom crop interface and waits for user to perform recropping.
    """
    try:
        slicer.app.processEvents()
        
        # Collapse the left module panel for recropping to maximize view space
        ui.collapse_left_module_panel()
        
        # Restore centerline visibility first
        centerline.restore_centerline_visibility()
        slicer.app.processEvents()
        
        # Show the crop module for recropping instead of custom interface
        try:
            # Open the crop module so user can see it in the left panel
            slicer.util.selectModule("CropVolume")
            slicer.app.processEvents()
            
            # Hide ALL UI elements from the crop module
            ui.hide_crop_volume_ui_elements()
            qt.QTimer.singleShot(500, ui.hide_crop_volume_ui_elements)
            qt.QTimer.singleShot(1500, ui.hide_crop_volume_ui_elements)
            
            # Create initial custom crop interface (without scissors tools) to match first crop
            success = ui.create_initial_custom_crop_interface()

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
            logger.debug("Suppressed exception in restart_cropping_workflow_safely", exc_info=True)

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
                logger.debug("Suppressed exception in clear_workflow_for_cropping_restart", exc_info=True)
        
        # Safely clear existing ROI nodes
        roi_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsROINode')
        for roi in roi_nodes:
            try:
                slicer.mrmlScene.RemoveNode(roi)
                slicer.app.processEvents()
            except Exception as e:
                logger.debug("Suppressed exception in clear_workflow_for_cropping_restart", exc_info=True)
        
        # Safely clear segmentation nodes (user will need to re-segment after cropping)
        segmentation_nodes = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
        for seg in segmentation_nodes:
            try:
                slicer.mrmlScene.RemoveNode(seg)
                slicer.app.processEvents()
            except Exception as e:
                logger.debug("Suppressed exception in clear_workflow_for_cropping_restart", exc_info=True)
        
        # Safely clear endpoint markups but preserve centerlines
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for fid in fiducial_nodes:
            try:
                # Only remove if it's not a preserved centerline-related node
                if 'endpoint' in fid.GetName().lower() or 'F-' in fid.GetName():
                    slicer.mrmlScene.RemoveNode(fid)
                    slicer.app.processEvents()
            except Exception as e:
                logger.debug("Suppressed exception in clear_workflow_for_cropping_restart", exc_info=True)
        
        # Store reference to original volume for workflow
        if original_volume:
            slicer.modules.WorkflowOriginalVolume = original_volume
        
        
    except Exception as e:
        logger.debug("Suppressed exception in clear_workflow_for_cropping_restart", exc_info=True)

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
                    logger.debug("Suppressed exception in add_cropped_volume_to_3d_scene", exc_info=True)
            
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
        logger.debug("Suppressed exception in add_cropped_volume_to_3d_scene", exc_info=True)

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

def test_restart_cropping_with_preservation():
    """
    Test function to restart cropping while preserving existing centerlines.
    Usage: test_restart_cropping_with_preservation()
    
    This function provides the same functionality as the "Restart Cropping" button
    in the centerline completion dialog, but can be called from the console.
    """
    try:
        # Check if we have any centerlines to preserve
        centerline_models = centerline.find_all_centerline_models()
        centerline_curves = centerline.find_all_centerline_curves()
        
        if not centerline_models and not centerline_curves:
            start_with_volume_crop()
            return
        
        
        # Store existing centerlines
        centerline.store_existing_centerlines()
        
        # Clear workflow data but preserve centerlines
        clear_workflow_for_cropping_restart()
        
        # Restart cropping workflow
        centerline.restart_cropping_preserving_centerlines()
        
        
        return True
        
    except Exception as e:
        pass
        pass
        start_with_volume_crop()
        return False

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
        ui.hide_crop_volume_ui_elements()
        qt.QTimer.singleShot(500, ui.hide_crop_volume_ui_elements)
        qt.QTimer.singleShot(1500, ui.hide_crop_volume_ui_elements)
        
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
        ui.restore_all_crop_ui_elements()
        
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

def restart_cropping_simple():
    """
    Simple restart cropping function that's less likely to cause freezing.
    This is a fallback when the full restart with preservation fails.
    
    Usage:
        restart_cropping_simple()  # Simple restart without preservation
    """
    try:
        
        # Stop all monitoring to prevent conflicts
        centerline.stop_all_centerline_monitoring()
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
            ui.set_3d_only_view()
            
            # Set dark background
            ui.set_3d_view_background_black()
            
            
            # Add scissors tools and continue button to the interface after cropping
            segmentation.add_scissors_tools_to_initial_interface()
            
            # Continue with the normal workflow - threshold segmentation
            qt.QTimer.singleShot(500, lambda: continue_workflow_after_custom_crop())
            
    except Exception as e:
        logger.debug("Suppressed exception in execute_initial_custom_crop", exc_info=True)

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
            ui.set_3d_only_view()
            
            # Set dark background
            ui.set_3d_view_background_black()

            # Continue with the normal workflow - threshold segmentation immediately
            qt.QTimer.singleShot(500, lambda: continue_workflow_after_custom_crop())
        
            
    except Exception as e:
        logger.error(f"Error in execute_custom_crop: {e}")

def continue_workflow_after_custom_crop():
    """
    Continue the normal workflow after custom cropping is completed.
    This ensures the same behavior as the original workflow.
    """
    try:

        volume_node = find_working_volume()
        if not volume_node:
            return

        # Skip markup import popup - continue with normal threshold workflow
        markup.continue_workflow_without_markup()
            
    except Exception as e:
        logger.error(f"Error in continue_workflow_after_custom_crop: {e}")

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
        logger.error(f"Error in ensure_crop_roi_exists: {e}")
        return None

def finish_custom_crop_workflow():
    """
    Finish the custom crop workflow and continue to next steps.
    This is called by the "FINISH SEGMENTATION - CONTINUE" button.
    """
    try:
        ui.cleanup_custom_crop_interface()
        segmentation.on_continue_from_scissors()
        
    except Exception as e:
        logger.error(f"Error in finish_custom_crop_workflow: {e}")

def use_custom_crop_instead_of_module():
    """
    Utility function to switch from the problematic crop module GUI to the custom crop interface.
    Call this when the crop module GUI becomes distorted during recropping.
    """
    try:

        try:
            ui.collapse_crop_volume_gui()
        except Exception as e:
            logger.error(f"Warning: Could not collapse crop volume GUI: {e}")
        custom_interface = ui.create_custom_crop_interface()
        if custom_interface:
            return True
        return False
            
    except Exception as e:
        logger.error(f"Error in use_custom_crop_instead_of_module: {e}")
        return False
