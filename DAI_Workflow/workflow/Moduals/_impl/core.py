from ._common import *  # noqa: F401,F403  (shared imports + logger)
from . import centerline, cpr, dicom, markup, segmentation, ui, volume  # sibling modules (cross-calls)

__all__ = [
    'setup_module_observers',
    'import_transform_file',
    'open_data_module',
    'create_analysis_masks',
    '_get_plugin_and_loadable_for_files',
    '_load_via_standardized_temp_folder',
    '_extract_slice_number',
    '_load_with_series_hint',
    '_load_with_vtk_direct',
    '_adjust_plugin_confidence',
    'cleanup_orphaned_start_markers',
    'manually_enable_orphaned_cleanup',
    'manually_run_cleanup',
    'toggle_analysis_masks_visibility',
    'create_stenosis_ratio_measurement',
    'count_existing_stenosis_measurements',
    'configure_stenosis_line_node',
    'setup_single_stenosis_line_observer',
    'check_single_line_completion',
    'check_first_line_completion_carefully',
    'switch_to_second_stenosis_line',
    'setup_second_line_completion_observer',
    'check_second_line_completion_carefully',
    'stop_stenosis_measurement_tool',
    'disable_all_placement_tools',
    'save_scene_location_to_user_home',
    'clear_saved_scene_locations',
    'get_current_scene_location',
    'setup_scene_save_observer',
    'on_scene_saved',
    'track_scene_save_location',
    'remove_scene_save_observer',
    'enable_scene_save_tracking',
    'disable_scene_save_tracking',
    'setup_storage_nodes_for_consistent_saving',
    'custom_save_all_scene_data',
    'test_custom_save_functionality',
    'manual_export_with_ct_series',
    'check_ct_series_setup',
    'close_slicer_after_export',
    'export_project_and_continue',
    'switch_to_crosssectional_fullscreen',
    'switch_to_3d_fullscreen',
    'force_remove_all_transforms',
    'handle_keyboard_undo',
    'handle_keyboard_redo',
    'test_keyboard_undo_functionality',
    'force_enable_keyboard_undo',
    'set_source_path',
    'reset_all_workflow_modules',
    'cleanup_global_workflow_state',
    'test_full_workflow_reset',
    'deleteAllPatients',
    'setup_exit_handler',
]

# Call initialization when module is imported
try:
    ui.initialize_workflow_ui()
except Exception as e:
    logger.info(f"Warning: Could not call initialize_workflow_ui: {e}")

# Set up scene save observer after functions are defined
def setup_module_observers():
    """Set up observers after all functions are defined"""
    try:
        setup_scene_save_observer()
    except Exception as e:
        logger.info(f"Warning: Could not set up scene save observer: {e}")

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
            logger.debug("Suppressed exception in open_data_module", exc_info=True)
        
        
    except Exception as e:
        slicer.util.errorDisplay(f"Error opening Data module: {str(e)}")

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
        file_analysis = dicom._analyze_dicom_files(files)
        
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
                                logger.debug("Suppressed exception in cleanup_temp", exc_info=True)
                        
                        # Cleanup after a delay
                        qt.QTimer.singleShot(5000, cleanup_temp)
                        
                        return volume_node
        except Exception as e:
            logger.debug("Suppressed exception in _load_via_standardized_temp_folder", exc_info=True)
        
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
                                    logger.debug("Suppressed exception in cleanup_temp", exc_info=True)
                            
                            qt.QTimer.singleShot(5000, cleanup_temp)
                            
                            return volume_node
        except Exception as e:
            logger.debug("Suppressed exception in _load_via_standardized_temp_folder", exc_info=True)
        
        # Method 3: Try VTK DICOM reader with standardized files
        try:
            result = volume._load_volume_from_file_list(standardized_files)
            if result:
                
                # Clean up temp folder
                def cleanup_temp():
                    try:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                    except:
                        logger.debug("Suppressed exception in cleanup_temp", exc_info=True)
                
                qt.QTimer.singleShot(5000, cleanup_temp)
                
                return result
        except Exception as e:
            logger.debug("Suppressed exception in _load_via_standardized_temp_folder", exc_info=True)
        
        # Clean up temp folder if all methods failed
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            logger.debug("Suppressed exception in _load_via_standardized_temp_folder", exc_info=True)
            
        return None
        
    except Exception as e:
        pass
        import traceback
        traceback.print_exc()
        return None

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
                    ui.set_3d_view_background_black()
                    qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                    
                    return True
        except Exception as vtk_error:
            logger.debug("Suppressed exception in _load_with_vtk_direct", exc_info=True)
        
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
                        logger.debug("Suppressed exception in _load_with_vtk_direct", exc_info=True)
                
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
                        ui.set_3d_view_background_black()
                        qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                        
                        return True
                        
        except Exception as stack_error:
            logger.debug("Suppressed exception in _load_with_vtk_direct", exc_info=True)
        
        return False
        
    except Exception as e:
        pass
        return False

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

def cleanup_orphaned_start_markers():
    """
    Remove any start-slice markers that don't have corresponding end-slice markers
    Only run this during stop operations, not during active point placement
    
    IMPORTANT: This function should only remove truly orphaned start markers,
    not valid end-slice markers that complete a pair.
    """
    try:
        # Global disable flag check
        if hasattr(slicer.modules, 'DisableOrphanedCleanup') and slicer.modules.DisableOrphanedCleanup:
            logger.info("[DEBUG] Cleanup disabled by global flag")
            return False
            
        # Check if point placement is currently active - don't cleanup during active placement
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if interactionNode and interactionNode.GetCurrentInteractionMode() == interactionNode.Place:
            logger.info("[DEBUG] Skipping orphaned marker cleanup - point placement is active")
            return False
            
        f1_points = None
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for node in fiducial_nodes:
            if node.GetName() == "F-1":
                f1_points = node
                break
        
        if not f1_points:
            logger.info("[DEBUG] No F-1 node found for cleanup")
            return False
        
        total_points = f1_points.GetNumberOfControlPoints()
        logger.info(f"[DEBUG] Cleanup analyzing F-1 node with {total_points} points")
        
        if total_points <= 2:  # Need at least pre-lesion, post-lesion
            logger.info("[DEBUG] Not enough points for cleanup (need > 2)")
            return False
        
        # Print all current labels for debugging
        for i in range(total_points):
            label = f1_points.GetNthControlPointLabel(i)
            logger.info(f"[DEBUG]   Point {i}: '{label}'")
        
        # Count slice points (everything after the first 2 points: pre-lesion, post-lesion)
        slice_points = total_points - 2
        logger.info(f"[DEBUG] Found {slice_points} slice points")
        
        # Only remove if we have an odd number of slice points AND the last point is actually a start-slice
        if slice_points % 2 == 1:
            last_point_index = total_points - 1
            last_label = f1_points.GetNthControlPointLabel(last_point_index)
            logger.info(f"[DEBUG] Odd number of slice points ({slice_points}), checking last point: '{last_label}'")
            
            # Only remove if it's actually a start-slice marker (not an end-slice)
            if last_label and "start-slice" in last_label and "end-slice" not in last_label:
                logger.info(f"[DEBUG] Removing truly orphaned start marker: {last_label}")
                f1_points.RemoveNthControlPoint(last_point_index)
                return True
            else:
                # The last point is an end-slice or something else - don't remove it
                logger.info(f"[DEBUG] Last point '{last_label}' is not an orphaned start marker - keeping it")
                return False
        else:
            logger.info(f"[DEBUG] Even number of slice points ({slice_points}) - no cleanup needed")
            return False
        
    except Exception as e:
        logger.info(f"[ERROR] Failed in cleanup_orphaned_start_markers: {e}")
        return False

def manually_enable_orphaned_cleanup():
    """
    Manually re-enable orphaned cleanup (for use after point placement is complete)
    """
    try:
        slicer.modules.DisableOrphanedCleanup = False
        logger.info("[DEBUG] Manually re-enabled orphaned cleanup")
    except Exception as e:
        logger.info(f"[DEBUG] Error re-enabling cleanup: {e}")

def manually_run_cleanup():
    """
    Manually run cleanup after re-enabling (for export or workflow completion)
    """
    try:
        manually_enable_orphaned_cleanup()
        result = cleanup_orphaned_start_markers()
        logger.info(f"[DEBUG] Manual cleanup result: {result}")
        return result
    except Exception as e:
        logger.info(f"[DEBUG] Error in manual cleanup: {e}")
        return False

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
        logger.debug("Suppressed exception in configure_stenosis_line_node", exc_info=True)

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
        logger.debug("Suppressed exception in setup_single_stenosis_line_observer", exc_info=True)

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
        logger.debug("Suppressed exception in check_single_line_completion", exc_info=True)

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
        logger.debug("Suppressed exception in check_first_line_completion_carefully", exc_info=True)

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
        logger.debug("Suppressed exception in switch_to_second_stenosis_line", exc_info=True)

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
        logger.debug("Suppressed exception in setup_second_line_completion_observer", exc_info=True)

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
        logger.debug("Suppressed exception in check_second_line_completion_carefully", exc_info=True)

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
        logger.debug("Suppressed exception in stop_stenosis_measurement_tool", exc_info=True)

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
        logger.debug("Suppressed exception in disable_all_placement_tools", exc_info=True)

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
            
        logger.info(f"Scene location saved to: {location_file}")
        
    except Exception as e:
        logger.info(f"Could not save scene location to user home: {str(e)}")

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
            logger.info(f"Cleared scene location history: {location_file}")
        else:
            logger.info("No scene location history file found to clear.")
            
    except Exception as e:
        logger.info(f"Could not clear scene location history: {str(e)}")

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
            logger.info(f"Current scene location: {scene_path}")
            return scene_path
        else:
            logger.info("Current scene has not been saved yet (no file location).")
            return None
            
    except Exception as e:
        logger.info(f"Could not get current scene location: {str(e)}")
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
        
        logger.info("Scene save observer has been set up - all scene saves will now be tracked.")
        
    except Exception as e:
        logger.info(f"Could not set up scene save observer: {str(e)}")

def on_scene_saved(caller, event):
    """
    Called whenever the scene is saved. Automatically logs the save location.
    """
    try:
        # Small delay to ensure the URL is updated
        qt.QTimer.singleShot(100, lambda: track_scene_save_location())
        
    except Exception as e:
        logger.info(f"Error in scene save callback: {str(e)}")

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
                logger.info("Scene save detected but no valid file path found")
        else:
            logger.info("Scene save detected but no URL available")
            
    except Exception as e:
        logger.info(f"Could not track scene save location: {str(e)}")

def remove_scene_save_observer():
    """
    Remove the scene save observer.
    Console function to stop automatic scene save tracking.
    """
    try:
        if hasattr(slicer.modules, 'SceneSaveObserverTag') and slicer.modules.SceneSaveObserverTag:
            slicer.mrmlScene.RemoveObserver(slicer.modules.SceneSaveObserverTag)
            slicer.modules.SceneSaveObserverTag = None
            logger.info("Scene save observer has been removed.")
        else:
            logger.info("No scene save observer was active.")
            
    except Exception as e:
        logger.info(f"Could not remove scene save observer: {str(e)}")

def enable_scene_save_tracking():
    """
    Manually enable scene save tracking.
    Console function to activate automatic scene save location tracking.
    """
    try:
        setup_scene_save_observer()
        logger.info("Scene save tracking is now enabled.")
        logger.info("All scene saves will be automatically logged to:")
        import os
        home_dir = os.path.expanduser("~")
        location_file = os.path.join(home_dir, "slicer_scene_locations.txt")
        logger.info(f"  {location_file}")
    except Exception as e:
        logger.info(f"Could not enable scene save tracking: {str(e)}")

def disable_scene_save_tracking():
    """
    Manually disable scene save tracking.
    Console function to deactivate automatic scene save location tracking.
    """
    try:
        remove_scene_save_observer()
        logger.info("Scene save tracking is now disabled.")
    except Exception as e:
        logger.info(f"Could not disable scene save tracking: {str(e)}")

def setup_storage_nodes_for_consistent_saving():
    """
    Setup storage nodes to ensure consistent file naming and directory structure.
    This ensures that the main volume and all other files are saved properly.
    """
    try:
        # Find the working volume and ensure it has proper storage node
        working_volume = volume.find_working_volume()
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
                logger.info(f"Set volume '{current_name}' filename to: CT_Series.nrrd")
        
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
        
        logger.info(f"Prepared {nodes_prepared} nodes for saving")
        return True
        
    except Exception as e:
        logger.info(f"Error setting up storage nodes: {str(e)}")
        import traceback
        traceback.print_exc()
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
        ui.show_pre_save_info()
        
        # Use the standard save dialog, but it should now have proper storage nodes
        # Try to automatically select all items when the dialog opens
        success = ui.open_save_dialog_with_all_selected()
        
        if success:
            # After successful save, verify that CT_Series was saved properly
            scene_path = slicer.mrmlScene.GetURL()
            if scene_path:
                if scene_path.startswith("file://"):
                    scene_path = scene_path[7:]  # Remove "file://" prefix
                    
                scene_dir = os.path.dirname(scene_path)
                logger.info(f"Scene saved to directory: {scene_dir}")
                
                # List all files saved in the directory
                try:
                    files_in_dir = os.listdir(scene_dir)
                    scene_files = [f for f in files_in_dir if not f.startswith('.')]
                    logger.info(f"Files saved in scene directory: {scene_files}")
                    
                    # Check if CT_Series.nrrd exists
                    ct_series_files = [f for f in scene_files if f.startswith("CT_Series") and f.endswith('.nrrd')]
                    if ct_series_files:
                        logger.info(f"✓ CT_Series volume saved as: {ct_series_files[0]}")
                    else:
                        # Try to find any .nrrd file that might be the CT volume
                        nrrd_files = [f for f in scene_files if f.endswith('.nrrd')]
                        if nrrd_files:
                            logger.info(f"Found .nrrd files: {nrrd_files}")
                            # If there's exactly one .nrrd file, it's likely the CT volume
                            if len(nrrd_files) == 1:
                                old_path = os.path.join(scene_dir, nrrd_files[0])
                                new_path = os.path.join(scene_dir, "CT_Series.nrrd")
                                try:
                                    os.rename(old_path, new_path)
                                    logger.info(f"Renamed {nrrd_files[0]} to CT_Series.nrrd")
                                except Exception as rename_error:
                                    logger.info(f"Could not rename {nrrd_files[0]} to CT_Series.nrrd: {str(rename_error)}")
                        else:
                            logger.info("Warning: No .nrrd files found in save directory")
                            
                except Exception as dir_error:
                    logger.info(f"Could not list directory contents: {str(dir_error)}")
            
            return True
        else:
            return False
            
    except Exception as e:
        logger.info(f"Error in custom save function: {str(e)}")
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
        logger.info("Testing custom save functionality...")
        
        # Show what's in the scene
        ui.show_pre_save_info()
        
        # Test storage node setup
        setup_result = setup_storage_nodes_for_consistent_saving()
        logger.info(f"Storage nodes setup result: {setup_result}")
        
        # Test finding working volume
        working_vol = volume.find_working_volume()
        if working_vol:
            logger.info(f"Working volume found: {working_vol.GetName()}")
        else:
            logger.info("No working volume found")
        
        logger.info("Custom save functionality test completed.")
        return True
        
    except Exception as e:
        logger.info(f"Error testing custom save functionality: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def manual_export_with_ct_series():
    """
    Manual export function that can be called from console to test the new export functionality.
    Usage: manual_export_with_ct_series()
    """
    try:
        logger.info("Starting manual export with CT_Series handling...")
        result = custom_save_all_scene_data()
        return result
    except Exception as e:
        logger.info(f"Error in manual export: {str(e)}")
        return False

def check_ct_series_setup():
    """
    Console function to check if CT_Series volume is properly set up for saving.
    Usage: check_ct_series_setup()
    """
    try:
        logger.info("=== CT_Series Setup Check ===")
        
        # Find working volume
        working_vol = volume.find_working_volume()
        if not working_vol:
            return False
        
        logger.info(f"Working volume: {working_vol.GetName()}")
        
        # Note: Volume name is preserved, but will be saved as CT_Series.nrrd
        logger.info(f"✓ Volume '{working_vol.GetName()}' will be saved as CT_Series.nrrd")
        
        # Check storage node
        storage_node = working_vol.GetStorageNode()
        if storage_node:
            filename = storage_node.GetFileName()
            logger.info(f"✓ Storage node exists with filename: {filename}")
            
            if filename and os.path.basename(filename).startswith("CT_Series"):
                logger.info("✓ Storage filename is properly set for CT_Series")
            else:
                logger.info("⚠ Storage filename should be set to CT_Series.nrrd")
        else:
            logger.info("⚠ No storage node found - will be created during save")
        
        # Count all saveable nodes
        all_volumes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        all_segs = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
        all_markups = slicer.util.getNodesByClass('vtkMRMLMarkupsNode')
        all_models = slicer.util.getNodesByClass('vtkMRMLModelNode')
        
        total_nodes = len(all_volumes) + len(all_segs) + len(all_markups) + len(all_models)
        logger.info(f"Total saveable nodes in scene: {total_nodes}")
        logger.info(f"  - Volumes: {len(all_volumes)}")
        logger.info(f"  - Segmentations: {len(all_segs)}")
        logger.info(f"  - Markups: {len(all_markups)}")
        logger.info(f"  - Models: {len(all_models)}")
        
        logger.info("==============================")
        return True
        
    except Exception as e:
        logger.info(f"Error checking CT_Series setup: {str(e)}")
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
        logger.info("[DEBUG] === Starting export_project_and_continue ===")
        
        # Check current F-1 points before any cleanup
        fiducial_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsFiducialNode')
        for node in fiducial_nodes:
            if node.GetName() == "F-1":
                logger.info(f"[DEBUG] F-1 node before cleanup: {node.GetNumberOfControlPoints()} points")
                for i in range(node.GetNumberOfControlPoints()):
                    label = node.GetNthControlPointLabel(i)
                    logger.info(f"  Point {i}: {label}")
                break
        
        # Clean up any orphaned start markers before export
        cleanup_result = cleanup_orphaned_start_markers()
        logger.info(f"[DEBUG] Cleanup orphaned markers result: {cleanup_result}")
        
        # Check F-1 points after cleanup
        for node in fiducial_nodes:
            if node.GetName() == "F-1":
                logger.info(f"[DEBUG] F-1 node after cleanup: {node.GetNumberOfControlPoints()} points")
                for i in range(node.GetNumberOfControlPoints()):
                    label = node.GetNthControlPointLabel(i)
                    logger.info(f"  Point {i}: {label}")
                break
        
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
            
            transforms_removed = markup.remove_transforms_from_point_lists()
            
            if not transforms_removed:
                pass
                force_remove_all_transforms()
            
            pass
            verification_passed = markup.verify_pre_post_lesion_points_transform_free()
            
            if not verification_passed:
                pass
                force_remove_all_transforms()
                verification_passed = markup.verify_pre_post_lesion_points_transform_free()
                
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
                    logger.info("Warning: Could not determine scene save location")
            except Exception as e:
                logger.info(f"Error saving scene location: {str(e)}")
            
            # Deselect placement tools and return to normal interaction mode
            pass
            disable_all_placement_tools()

            # Reapply transforms after saving
            if lesion_analysis_nodes:
                pass
                markup.reapply_transforms_to_point_lists()
                markup.reapply_transforms_to_circles()

            pass
            ui.cleanup_all_workflow_ui()

            # Run workflow2 functionality directly
            try:
                pass
                centerline.create_centerline_and_tube_mask()
                
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
            qt.QTimer.singleShot(3000, ui.restore_original_layout)
                    
    except Exception as e:
        pass  # Continue even if layout switch fails

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

def handle_keyboard_undo(segmentEditorWidget=None):
    """
    Handle Ctrl+Z keyboard shortcut for undo in segment editor
    """
    try:
        # Get the segment editor widget if not provided
        if not segmentEditorWidget and hasattr(slicer.modules, 'WorkflowSegmentEditorWidget'):
            segmentEditorWidget = slicer.modules.WorkflowSegmentEditorWidget
        
        if segmentEditorWidget:
            # First try the segment editor's built-in undo
            if hasattr(segmentEditorWidget, 'undo'):
                segmentEditorWidget.undo()
                logger.info("Executed keyboard undo via segment editor")
                return True
            elif hasattr(segmentEditorWidget, 'undoEnabled') and segmentEditorWidget.undoEnabled:
                # Alternative method to trigger undo
                segmentEditorWidget.undoEnabled = True
                if hasattr(segmentEditorWidget, 'undo'):
                    segmentEditorWidget.undo()
                    logger.info("Executed keyboard undo via alternative method")
                    return True
        
        # Fallback to scene undo system
        logger.info("Falling back to scene undo system for keyboard shortcut")
        if slicer.mrmlScene.GetUndoFlag() and slicer.mrmlScene.GetNumberOfUndoLevels() > 0:
            slicer.mrmlScene.Undo()
            slicer.app.processEvents()  # Refresh views
            return True
        else:
            logger.info("No undo levels available")
            return False
        
    except Exception as e:
        logger.info(f"Error in keyboard undo handler: {e}")
        return False

def handle_keyboard_redo(segmentEditorWidget=None):
    """
    Handle Ctrl+Y keyboard shortcut for redo in segment editor
    """
    try:
        # Get the segment editor widget if not provided
        if not segmentEditorWidget and hasattr(slicer.modules, 'WorkflowSegmentEditorWidget'):
            segmentEditorWidget = slicer.modules.WorkflowSegmentEditorWidget
        
        if segmentEditorWidget:
            # Try the segment editor's built-in redo
            if hasattr(segmentEditorWidget, 'redo'):
                segmentEditorWidget.redo()
                logger.info("Executed keyboard redo via segment editor")
                return True
        
        # If no segment editor redo available, inform user
        if hasattr(slicer, 'util') and hasattr(slicer.util, 'infoDisplay'):
            slicer.util.infoDisplay("Redo functionality not available in workflow mode.", autoCloseMsec=2000)
        
        return False
        
    except Exception as e:
        logger.info(f"Error in keyboard redo handler: {e}")
        return False

def test_keyboard_undo_functionality():
    """
    Test function to verify that Ctrl+Z keyboard shortcut is working properly
    """
    try:
        logger.info("=== Testing Keyboard Undo Functionality ===")
        
        # Check if shortcuts are installed
        if hasattr(slicer.modules, 'WorkflowUndoShortcut'):
            shortcut = slicer.modules.WorkflowUndoShortcut
            logger.info(f"✓ Ctrl+Z shortcut found: {shortcut}")
            logger.info(f"  Key sequence: {shortcut.key().toString()}")
        else:
            logger.info("✗ No Ctrl+Z shortcut found")
        
        if hasattr(slicer.modules, 'WorkflowRedoShortcut'):
            shortcut = slicer.modules.WorkflowRedoShortcut
            logger.info(f"✓ Ctrl+Y shortcut found: {shortcut}")
            logger.info(f"  Key sequence: {shortcut.key().toString()}")
        else:
            logger.info("✗ No Ctrl+Y shortcut found")
        
        # Check widget shortcuts
        if hasattr(slicer.modules, 'WorkflowWidgetUndoShortcut'):
            shortcut = slicer.modules.WorkflowWidgetUndoShortcut
            logger.info(f"✓ Widget Ctrl+Z shortcut found: {shortcut}")
        else:
            logger.info("✗ No widget Ctrl+Z shortcut found")
        
        if hasattr(slicer.modules, 'WorkflowWidgetRedoShortcut'):
            shortcut = slicer.modules.WorkflowWidgetRedoShortcut
            logger.info(f"✓ Widget Ctrl+Y shortcut found: {shortcut}")
        else:
            logger.info("✗ No widget Ctrl+Y shortcut found")
        
        # Check segment editor widget
        if hasattr(slicer.modules, 'WorkflowSegmentEditorWidget'):
            widget = slicer.modules.WorkflowSegmentEditorWidget
            logger.info(f"✓ Segment editor widget found: {type(widget)}")
            
            if hasattr(widget, 'undoEnabled'):
                logger.info(f"  Undo enabled: {widget.undoEnabled}")
            
            if hasattr(widget, 'undo'):
                logger.info("  ✓ Undo method available")
            else:
                logger.info("  ✗ Undo method not available")
                
            if hasattr(widget, 'redo'):
                logger.info("  ✓ Redo method available")
            else:
                logger.info("  ✗ Redo method not available")
        else:
            logger.info("✗ No segment editor widget found")
        
        # Check segmentation undo settings
        if hasattr(slicer.modules, 'WorkflowSegmentationNode'):
            segmentation_node = slicer.modules.WorkflowSegmentationNode
            if segmentation_node:
                segmentation = segmentation_node.GetSegmentation()
                if segmentation and hasattr(segmentation, 'GetMaximumNumberOfUndoStates'):
                    undo_states = segmentation.GetMaximumNumberOfUndoStates()
                    logger.info(f"✓ Segmentation undo states: {undo_states}")
                else:
                    logger.info("✗ Cannot check segmentation undo states")
        
        # Test manual keyboard undo function
        logger.info("\n--- Testing Manual Keyboard Undo ---")
        result = handle_keyboard_undo()
        logger.info(f"Manual undo test result: {result}")
        
        logger.info("\n=== Keyboard Undo Test Complete ===")
        logger.info("If Ctrl+Z still doesn't work, try:")
        logger.info("1. Make sure you're clicking in a slice view first to give it focus")
        logger.info("2. Try pressing Ctrl+Z while the mouse is over a slice view")
        logger.info("3. Check that the segment editor widget has focus")
        
    except Exception as e:
        logger.info(f"Error during keyboard undo test: {e}")
        import traceback
        traceback.print_exc()

def force_enable_keyboard_undo():
    """
    Force enable Ctrl+Z keyboard undo functionality for the workflow
    Call this function if Ctrl+Z is not working
    """
    try:
        logger.info("Force enabling keyboard undo functionality...")
        
        # Get the segment editor widget
        segmentEditorWidget = None
        if hasattr(slicer.modules, 'WorkflowSegmentEditorWidget'):
            segmentEditorWidget = slicer.modules.WorkflowSegmentEditorWidget
        
        if not segmentEditorWidget:
            logger.info("✗ No segment editor widget found. Please start the scissors tool first.")
            return False
        
        # Clear existing shortcuts
        for shortcut_attr in ['WorkflowUndoShortcut', 'WorkflowRedoShortcut', 'WorkflowWidgetUndoShortcut', 'WorkflowWidgetRedoShortcut']:
            if hasattr(slicer.modules, shortcut_attr):
                try:
                    shortcut = getattr(slicer.modules, shortcut_attr)
                    shortcut.setParent(None)
                    delattr(slicer.modules, shortcut_attr)
                except Exception:
                    logger.debug("Suppressed exception in force_enable_keyboard_undo", exc_info=True)
        
        # Re-install shortcuts with fresh references
        main_window = slicer.util.mainWindow()
        if main_window:
            # Global shortcuts
            undo_shortcut = qt.QShortcut(qt.QKeySequence("Ctrl+Z"), main_window)
            undo_shortcut.connect('activated()', lambda: handle_keyboard_undo(segmentEditorWidget))
            slicer.modules.WorkflowUndoShortcut = undo_shortcut
            
            redo_shortcut = qt.QShortcut(qt.QKeySequence("Ctrl+Y"), main_window)
            redo_shortcut.connect('activated()', lambda: handle_keyboard_redo(segmentEditorWidget))
            slicer.modules.WorkflowRedoShortcut = redo_shortcut
            
            logger.info("✓ Installed global keyboard shortcuts")
        
        # Widget shortcuts
        if segmentEditorWidget:
            widget_undo_shortcut = qt.QShortcut(qt.QKeySequence("Ctrl+Z"), segmentEditorWidget)
            widget_undo_shortcut.connect('activated()', lambda: handle_keyboard_undo(segmentEditorWidget))
            slicer.modules.WorkflowWidgetUndoShortcut = widget_undo_shortcut
            
            widget_redo_shortcut = qt.QShortcut(qt.QKeySequence("Ctrl+Y"), segmentEditorWidget)
            widget_redo_shortcut.connect('activated()', lambda: handle_keyboard_redo(segmentEditorWidget))
            slicer.modules.WorkflowWidgetRedoShortcut = widget_redo_shortcut
            
            logger.info("✓ Installed widget-specific keyboard shortcuts")
        
        # Try to activate the segment editor widget to give it focus
        if segmentEditorWidget:
            segmentEditorWidget.setFocus()
            segmentEditorWidget.activateWindow()
        
        logger.info("✓ Keyboard undo functionality has been re-enabled")
        logger.info("Try pressing Ctrl+Z now. If it still doesn't work, make sure:")
        logger.info("  1. You have made some changes to the segmentation first")
        logger.info("  2. The mouse cursor is over a slice view when you press Ctrl+Z")
        logger.info("  3. You are using the scissors tool from this workflow")
        
        return True
        
    except Exception as e:
        logger.info(f"Error enabling keyboard undo: {e}")
        return False

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
        logger.debug("Suppressed exception in set_source_path", exc_info=True)

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
        results['crop_volume'] = volume.reset_crop_module_to_default()
        
        # Reset Extract Centerline module
        results['extract_centerline'] = centerline.reset_extract_centerline_module()
        
        # Reset Segment Editor module (if it was used)
        results['segment_editor'] = segmentation.reset_segment_editor_module()
        
        # Reset CPR module
        results['cpr'] = cpr.reset_cpr_module()
        
        # Clean up any global workflow state
        cleanup_global_workflow_state()
        
        successful_resets = sum(results.values())
        total_modules = len(results)
        



            
        return results
        
    except Exception as e:
        return {'error': str(e)}

def cleanup_global_workflow_state():
    """Clean up global workflow state and monitoring timers."""
    try:
        # Stop all monitoring timers
        centerline.stop_all_centerline_monitoring()
        cpr.stop_cpr_monitoring()
        volume.stop_volume_addition_monitoring()
        
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
        logger.debug("Suppressed exception in cleanup_global_workflow_state", exc_info=True)

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

# Initialize scene save observer when module is fully loaded
try:
    setup_module_observers()
except Exception as e:
    logger.info(f"Scene save observer setup failed. You will have to manualy close the program after saving. Error: {e}")


def deleteAllPatients():
    """Delete all patients from the DICOM database"""
    dicomDatabase = slicer.dicomDatabase
    
    if not dicomDatabase.isOpen:
        logger.info("DICOM database is not open")
        return
    
    # Get all patient IDs
    patients = dicomDatabase.patients()
    
    if len(patients) == 0:
        logger.info("No patients found in database")
        return
    
    logger.info(f"Found {len(patients)} patients. Deleting all...")
    
    # Delete each patient
    for patientID in patients:
        patientName = dicomDatabase.nameForPatient(patientID)
        dicomDatabase.removePatient(patientID)
        logger.info(f"Deleted Patient ID: {patientID}, Name: {patientName}")
    
    logger.info("All patients deleted successfully")

def setup_exit_handler():
    """Set up cleanup using aboutToQuit signal"""
    try:
        slicer.app.connect("aboutToQuit()", ui.onSlicerAboutToQuit)
        logger.info("Exit handler registered successfully")
        logger.info("Patient data will be deleted when Slicer exits")
        return True
    except Exception as e:
        logger.info(f"Could not register exit handler: {e}")
        return False

setup_exit_handler()
