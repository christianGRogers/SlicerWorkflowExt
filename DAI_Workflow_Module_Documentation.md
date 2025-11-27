# DAI Workflow Module - Complete Feature Documentation

## Overview
The DAI Workflow module is a comprehensive 3D Slicer extension for vessel centerline extraction and Curved Planar Reformat (CPR) visualization. It provides a guided workflow for medical image analysis, specifically designed for vessel analysis with programmatic Segment Editor integration and enhanced user interface controls.

**Author:** Christian Rogers - So Lab - Lawson - UWO (2025)

---

## Module Architecture

The workflow module contains approximately **200+ functions** organized into the following major categories:

### 1. Core Workflow Management
### 2. UI Management and Layout Control
### 3. Data Import and Export
### 4. Volume Processing and Cropping
### 5. Segmentation and Thresholding
### 6. Centerline Extraction and Analysis
### 7. CPR (Curved Planar Reformat) Processing
### 8. Point Placement and Markup Tools
### 9. Measurement and Analysis Tools
### 10. DICOM Loading and Processing
### 11. Scene Management and Persistence

---

## Detailed Feature Categories

## 1. CORE WORKFLOW MANAGEMENT

### Initialization and Setup
- **`initialize_workflow_ui()`** - Initialize workflow UI state and collapse left panel on startup
- **`setup_module_observers()`** - Set up observers for scene events after functions are defined
- **`find_working_volume()`** - Find appropriate volume to work with, preferring cropped and visible volumes

### Main Workflow Entry Points
- **`start_with_dicom_data()`** - Start workflow by opening Add DICOM Data module
- **`start_with_volume_crop()`** - Start workflow using custom crop interface
- **`start_crop_workflow_directly()`** - Start crop workflow directly without dialogs
- **`start_markup_workflow()`** - Start workflow with crop first, then markup import
- **`start_workflow_with_segmentation_dialog()`** - Start workflow with segmentation import dialog
- **`create_threshold_segment()`** - Main function to create threshold segment with import options
- **`create_threshold_segment_with_markup_only()`** - Main workflow function with markup import only

### Workflow State Management
- **`cleanup_workflow_ui()`** - Clean up workflow UI elements
- **`cleanup_all_workflow_ui()`** - Complete cleanup of all workflow UI elements
- **`reset_all_workflow_modules()`** - Reset all workflow modules to default state
- **`cleanup_global_workflow_state()`** - Clean up global workflow state variables

---

## 2. UI MANAGEMENT AND LAYOUT CONTROL

### Panel and Layout Management
- **`collapse_left_module_panel()`** - Collapse left module panel to maximize view space
- **`expand_left_module_panel()`** - Expand left module panel when needed
- **`force_collapse_left_panel_on_startup()`** - Force collapse of left panel on startup

### View Layout Configuration
- **`show_red_green_views_only()`** - Switch to Red and Green slice views side-by-side
- **`set_three_up_view()`** - Switch to three slice views (Red, Green, Yellow)
- **`set_3d_only_view()`** - Switch layout to show only 3D view
- **`set_3d_view_background_black()`** - Set 3D view background to black
- **`switch_to_crosssectional_fullscreen()`** - Switch to cross-sectional fullscreen view
- **`switch_to_3d_fullscreen()`** - Switch to 3D fullscreen view
- **`restore_original_layout()`** - Restore original layout configuration

### Volume Display Management
- **`set_volume_visible_in_slice_views(volume_node)`** - Set volume as visible and active in all slice views
- **`set_cropped_volume_visible(cropped_volume)`** - Set cropped volume as visible and active
- **`get_volume_slice_thickness(volume_node)`** - Get slice thickness from volume's spacing information

### UI Element Control
- **`hide_centerlines_from_views()`** - Hide all centerline-related nodes from views
- **`hide_cpr_slice_size_controls()`** - Hide slice size controls from CPR module UI
- **`hide_threshold_segmentation_mask()`** - Hide threshold segmentation masks after CPR opens

---

## 3. DATA IMPORT AND EXPORT

### Markup Import Features
- **`ask_user_for_markup_import()`** - Ask user if they want to import markup workflow files
- **`import_markup_file()`** - Let user select source folder containing markup files
- **`process_markup_folder_and_create_tubes(folder_path)`** - Process folder with markup files and create tube masks
- **`load_first_point_from_markup(markup_file_path)`** - Load first point from markup file
- **`create_curve_models_from_markup(markup_node)`** - Create curve models from markup points

### Segmentation Import
- **`ask_user_for_segmentation_import()`** - Ask user if they want to import existing segmentation
- **`import_segmentation_file()`** - Let user select and import segmentation file
- **`start_imported_segmentation_workflow(segmentation_node, volume_node)`** - Start alternate workflow with imported segmentation

### Transform and Volume Import
- **`import_transform_file()`** - Let user select and import transform file
- **`import_straightened_volume()`** - Let user select and import straightened volume file

### Tube Creation from Markup
- **`create_tube_from_two_points(start_point, end_point, tube_name, color)`** - Create tube model from two points
- **`create_tube_from_curve_with_color(curve_markup, tube_name, color)`** - Create tube model from curve markup with color

### Scene Persistence
- **`save_scene_location_to_user_home(scene_path)`** - Save scene location to user home directory
- **`show_saved_scene_locations()`** - Display saved scene locations
- **`clear_saved_scene_locations()`** - Clear saved scene location history
- **`get_current_scene_location()`** - Get current scene file location
- **`custom_save_all_scene_data()`** - Custom save all scene data with proper selection
- **`export_project_and_continue()`** - Export project and continue workflow

---

## 4. VOLUME PROCESSING AND CROPPING

### Custom Crop Interface
- **`create_initial_custom_crop_interface()`** - Create initial custom crop interface instead of module
- **`create_custom_crop_interface()`** - Create comprehensive custom crop interface
- **`execute_initial_custom_crop()`** - Execute initial custom crop operation
- **`execute_custom_crop()`** - Execute custom crop operation
- **`finish_custom_crop_workflow()`** - Finish custom crop workflow
- **`cleanup_custom_crop_interface()`** - Clean up custom crop interface elements

### Crop Monitoring and Completion
- **`setup_crop_completion_monitor(original_volume_node)`** - Monitor for cropped volume creation
- **`check_crop_completion(original_volume_node)`** - Check if new cropped volume exists
- **`on_finish_cropping()`** - Called when user finishes cropping
- **`continue_workflow_after_custom_crop()`** - Continue workflow after custom crop completion

### Crop UI Management
- **`add_large_crop_apply_button()`** - Add large green Apply button to Crop Volume module (disabled)
- **`collapse_crop_volume_gui()`** - Completely collapse/hide Crop Volume module GUI
- **`hide_crop_volume_ui_elements()`** - Hide crop volume UI elements
- **`restore_crop_ui()`** - Restore crop UI elements
- **`cleanup_crop_module_custom_elements()`** - Clean up crop module custom elements

### Crop Workflow Control
- **`cropVolumeWithNamedROI(roiName="CropROI", outputName="CroppedVolume")`** - Crop volume with named ROI
- **`ensure_crop_roi_exists()`** - Ensure crop ROI exists for workflow
- **`setup_crop_display_layout()`** - Set up display layout for cropping
- **`restart_cropping_workflow_safely()`** - Restart cropping workflow safely

---

## 5. SEGMENTATION AND THRESHOLDING

### Threshold Creation
- **`prompt_for_threshold_range()`** - Show dialog to get threshold values from user
- **`create_segmentation_from_threshold(volume_node, threshold_value_low, threshold_value_high)`** - Apply threshold to create segmentation
- **`show_segmentation_in_3d(segmentation_node)`** - Display segmentation as 3D volume rendering

### Segment Editor Integration
- **`load_into_segment_editor(segmentation_node, volume_node)`** - Load segmentation using programmatic API
- **`select_scissors_tool(segment_editor_widget)`** - Select Scissors tool programmatically
- **`start_with_segment_editor_scissors()`** - Start with segment editor scissors tool

### Scissors Tool Management
- **`create_scissors_tool_button()`** - Create scissors tool toggle button
- **`toggle_scissors_tool(activated)`** - Toggle scissors tool programmatically
- **`toggle_scissors_tool_programmatic(activated)`** - Toggle scissors tool with programmatic controls
- **`cleanup_scissors_tool_ui()`** - Clean up scissors tool UI elements

### Post-Threshold Tools
- **`add_post_threshold_tools_to_left_panel(segmentation_node, volume_node)`** - Add scissors tools to left panel
- **`cleanup_post_threshold_tools()`** - Clean up post-threshold tools widget
- **`continue_to_centerline_from_left_panel()`** - Continue to centerline extraction from left panel

### Workflow Continuation
- **`markup_workflow_after_crop()`** - Handle markup import workflow after crop
- **`continue_workflow_without_markup()`** - Continue workflow with threshold segmentation only

---

## 6. CENTERLINE EXTRACTION AND ANALYSIS

### Centerline Module Setup
- **`open_centerline_module()`** - Open Extract Centerline module
- **`setup_centerline_module()`** - Set up Extract Centerline module with current segmentation
- **`prepare_surface_for_centerline(segmentation_node)`** - Prepare segmentation surface for centerline extraction

### Centerline UI Management
- **`add_large_centerline_apply_button()`** - Add large green Apply button to Extract Centerline module
- **`cleanup_centerline_ui()`** - Clean up centerline UI elements
- **`remove_duplicate_centerline_buttons()`** - Remove duplicate centerline buttons (deprecated)
- **`hide_extract_centerline_ui_elements()`** - Hide extract centerline UI elements
- **`restore_extract_centerline_ui()`** - Restore extract centerline UI elements

### Point Placement Tools
- **`force_point_placement_tool_selection()`** - Force point placement tool selection
- **`verify_extract_centerline_point_list_autoselection()`** - Verify point list autoselection
- **`fix_extract_centerline_setup_issues()`** - Fix common Extract Centerline setup issues

### Centerline Detection and Management
- **`find_recent_centerline_model(created_after)`** - Find most recently created centerline model
- **`find_all_centerline_models()`** - Find all centerline models in scene
- **`find_recent_centerline_curve(created_after)`** - Find most recently created centerline curve
- **`find_all_centerline_curves()`** - Find all centerline curves in scene
- **`find_nearest_centerline_to_point(point_position)`** - Find centerline closest to given point

### Centerline Monitoring
- **`setup_centerline_completion_monitor()`** - Set up monitoring to detect centerline completion
- **`check_centerline_completion()`** - Check if centerline extraction has completed
- **`check_specific_centerline_completion()`** - Check if specific target centerlines have data
- **`stop_centerline_monitoring()`** - Stop centerline completion monitoring

### Centerline Workflow Management
- **`get_current_centerline_for_placement()`** - Get centerline for point placement
- **`ensure_point_placement_uses_current_centerline(point_list)`** - Ensure point list uses current centerline
- **`populate_centerline_dropdown()`** - Populate centerline dropdown with available centerlines

### Multiple Centerline Support
- **`count_existing_centerlines()`** - Count existing centerlines in scene
- **`create_additional_centerline_setup()`** - Create setup for additional centerline extraction
- **`setup_centerline_for_additional_extraction(centerline_module, new_model, new_curve)`** - Setup for additional extractions
- **`clear_existing_centerlines()`** - Clear existing centerlines from scene

### Centerline Editing
- **`show_centerline_editing_dialog(centerline_model, centerline_curve)`** - Show centerline editing dialog
- **`enable_centerline_editing(centerline_curve)`** - Enable centerline editing mode
- **`disable_centerline_editing(centerline_curve)`** - Disable centerline editing mode
- **`backup_centerline_points(centerline_curve)`** - Backup centerline points before editing
- **`save_edited_centerline_as_final(centerline_curve)`** - Save edited centerline as final version

### Centerline Completion Dialogs
- **`show_centerline_completion_dialog(centerline_model, centerline_curve)`** - Show completion dialog after centerline extraction
- **`on_retry_centerline(dialog)`** - Handle retry centerline extraction
- **`on_continue_to_cpr(dialog, centerline_model, centerline_curve)`** - Continue to CPR from dialog
- **`on_add_more_centerlines(dialog)`** - Add more centerlines from dialog
- **`on_verify_edit_centerline(dialog, centerline_model, centerline_curve)`** - Verify/edit centerline from dialog

---

## 7. CPR (CURVED PLANAR REFORMAT) PROCESSING

### CPR Module Setup
- **`switch_to_cpr_module(centerline_model, centerline_curve)`** - Switch to CPR module and configure
- **`setup_cpr_module()`** - Set up CPR module with generated centerline
- **`add_large_cpr_apply_button()`** - Add large green Apply button to CPR module

### CPR Processing
- **`auto_apply_cpr()`** - Automatically apply CPR processing
- **`apply_cpr_transform_to_centerlines()`** - Apply CPR transform to centerline nodes

### CPR Monitoring
- **`setup_cpr_completion_monitor()`** - Monitor for CPR completion
- **`check_cpr_completion()`** - Check if CPR processing has completed
- **`stop_cpr_monitoring()`** - Stop CPR completion monitoring

### Cross-Section Analysis
- **`setup_cross_section_analysis_module()`** - Configure Cross-Section Analysis module after CPR
- **`configure_cross_section_module()`** - Helper function to configure Cross-Section Analysis
- **`collapse_parameters_tab()`** - Remove Parameters section after Apply
- **`configure_browse_cross_sections()`** - Configure browse cross sections settings

---

## 8. POINT PLACEMENT AND MARKUP TOOLS

### Point Placement Controls
- **`create_point_list_and_prompt()`** - Create point placement control interface
- **`create_point_placement_controls()`** - Create control widget for point placement
- **`toggle_point_placement_mode()`** - Toggle between starting/stopping point placement
- **`start_new_point_list_placement(count_label)`** - Create new point list and start placement
- **`stop_point_placement_mode()`** - Stop point placement mode

### Branch Point Management
- **`toggle_branch_point_placement_mode()`** - Toggle branch point placement mode
- **`start_new_branch_point_list_placement(count_label)`** - Create new branch point list
- **`stop_branch_point_placement_mode()`** - Stop branch point placement mode
- **`on_branch_point_added(point_list, count_label)`** - Handle branch point addition events

### Post-Branch Point Management
- **`toggle_post_branch_point_placement_mode()`** - Toggle post-branch point placement
- **`start_new_post_branch_point_list_placement(count_label)`** - Create new post-branch point list
- **`stop_post_branch_point_placement_mode()`** - Stop post-branch point placement
- **`on_post_branch_point_added(point_list, count_label)`** - Handle post-branch point addition

### Point Count Management
- **`setup_point_count_observer(point_list, count_label)`** - Set up observer for point count updates
- **`on_point_added(point_list, count_label)`** - Handle point addition events
- **`update_point_count_display(point_list, count_label)`** - Update point count display
- **`update_point_count_display_for_current_list(count_label)`** - Update count for current active list

### Circle Drawing and Management
- **`draw_circles_on_centerline()`** - Draw circles on centerline at marked points
- **`draw_circle_for_single_point(point_index)`** - Draw circle for single point
- **`draw_circle_for_single_branch_point(point_index)`** - Draw circle for single branch point
- **`draw_circle_for_single_post_branch_point(point_index)`** - Draw circle for single post-branch point
- **`create_closed_curve_circle(circle_node, center_point, radius)`** - Create closed curve circle
- **`create_perpendicular_circle(circle_node, center_point, radius, direction_vector)`** - Create perpendicular circle

### Circle Editing and Control
- **`update_circle_dropdown()`** - Update circle dropdown with available circles
- **`on_circle_selection_changed(selected_text)`** - Handle circle selection change
- **`calculate_circle_radius(circle_node)`** - Calculate geometric radius of circle
- **`on_radius_slider_changed(slider_value)`** - Handle radius slider value change
- **`apply_radius_to_circle(circle_node, radius_value)`** - Apply specified radius to circle

### Circle Cleanup
- **`clear_centerline_circles()`** - Clear all centerline-related circles
- **`clear_branch_circles()`** - Clear branch circles
- **`clear_circles_selective(circle_types)`** - Clear circles selectively by type

### Additional Markup Tools
- **`create_additional_fiducial_list()`** - Create new fiducial list for additional markup
- **`create_additional_curve_markup()`** - Create new curve markup for additional curves
- **`cleanup_orphaned_start_markers()`** - Remove start-slice markers without end-slice markers

---

## 9. MEASUREMENT AND ANALYSIS TOOLS

### Stenosis Measurement
- **`create_stenosis_ratio_measurement()`** - Create stenosis ratio measurement tool
- **`count_existing_stenosis_measurements()`** - Count existing stenosis measurements in scene
- **`configure_stenosis_line_node(line_node)`** - Configure stenosis line node properties
- **`stop_stenosis_measurement_tool()`** - Stop stenosis measurement tool

### Stenosis Line Management
- **`setup_single_stenosis_line_observer(line_node)`** - Set up observer for single stenosis line
- **`check_single_line_completion(line_node)`** - Check single line completion
- **`check_first_line_completion_carefully(first_line_node, second_line_node)`** - Check first line completion
- **`switch_to_second_stenosis_line(second_line_node)`** - Switch to second stenosis line
- **`setup_second_line_completion_observer(second_line_node)`** - Set up second line observer
- **`check_second_line_completion_carefully(second_line_node)`** - Check second line completion

### Analysis Mask Management
- **`create_analysis_masks(straightened_volumes)`** - Create analysis masks from straightened volumes
- **`toggle_analysis_masks_visibility(toggle_button)`** - Toggle visibility of analysis masks

### Measurement Tools
- **`toggle_window_level_tool(activated, toggle_button)`** - Toggle window/level tool
- **`disable_all_placement_tools()`** - Disable all placement tools

### Transform Management
- **`remove_transforms_from_point_lists()`** - Remove transforms from point lists
- **`verify_pre_post_lesion_points_transform_free()`** - Verify points are transform-free
- **`reapply_transforms_to_point_lists()`** - Reapply transforms to point lists
- **`reapply_transforms_to_circles()`** - Reapply transforms to circles
- **`force_remove_all_transforms()`** - Force remove all transforms from scene

---

## 10. DICOM LOADING AND PROCESSING

### Main DICOM Loading Functions
- **`load_dicom_from_source_file(dicom_path)`** - Load DICOM data from path in source file
- **`simple_dicom_load(dicom_path)`** - Simplified DICOM loading bypassing complex operations
- **`load_philips_dicom_simple(dicom_path)`** - Load Philips DICOM using user's working method

### Enhanced DICOM Processing
- **`_import_and_load_dicom_data(input_dir, temp_db)`** - Import and load DICOM with enhanced plugin approach
- **`_process_dicom_database_patients(dicom_database, patients, input_dir)`** - Process patients from DICOM database
- **`_get_plugin_and_loadable_for_files(series_description, files)`** - Find best DICOM plugin for files
- **`_load_via_standardized_temp_folder(dicom_files, series_directory)`** - Load via standardized temp folder

### Specialized DICOM Handlers
- **`_load_philips_dicom_series(dicom_directory)`** - Load Philips DICOM series specifically
- **`_load_dicom_series_manually(dicom_files, series_directory)`** - Manual DICOM series loading
- **`_load_volume_from_file_list(file_list)`** - Load volume from explicit file list
- **`_load_with_series_hint(directory, file_list)`** - Load DICOM with series loading hints

### DICOM Analysis and Utilities
- **`_analyze_dicom_files(files)`** - Analyze DICOM files to understand characteristics
- **`_adjust_plugin_confidence(plugin_name, original_confidence, file_analysis, series_description)`** - Adjust plugin confidence
- **`_find_dicom_files_in_directory(directory)`** - Find DICOM files using enhanced detection
- **`_extract_slice_number(file_path)`** - Extract slice number from DICOM filename

### DICOM Testing and Debugging
- **`test_philips_detection(dicom_path)`** - Test Philips DICOM detection
- **`test_philips_dicom_loading(dicom_path)`** - Test complete Philips DICOM loading workflow
- **`diagnose_dicom_directory(dicom_path)`** - Diagnose what's in DICOM directory
- **`test_dicom_loading_with_path(dicom_path)`** - Test enhanced DICOM loading with specific path
- **`test_dicom_directory_loading(directory_path)`** - Test DICOM directory loading

### DICOM Fallback Methods
- **`_fallback_dicom_loading(dicom_path)`** - Fallback DICOM loading when enhanced methods unavailable
- **`_load_with_dicom_browser(directory)`** - Load using DICOM browser module
- **`_load_as_volume_sequence(dicom_files, directory)`** - Load DICOM files as volume sequence
- **`_load_with_vtk_direct(dicom_files)`** - Direct VTK DICOM loading with error handling

### DICOM Configuration and Fixes
- **`fix_dicom_spacing_and_orientation(volume_node, dicom_directory)`** - Fix DICOM spacing and orientation
- **`fix_volume_spacing_manually(spacing_x, spacing_y, spacing_z)`** - Fix volume spacing manually
- **`reset_volume_to_identity_matrix()`** - Reset volume to identity matrix
- **`analyze_volume_properties()`** - Analyze volume properties for debugging

---

## 11. SCENE MANAGEMENT AND PERSISTENCE

### Scene Save Management
- **`setup_scene_save_observer()`** - Set up observer for scene save events
- **`on_scene_saved(caller, event)`** - Handle scene saved events
- **`track_scene_save_location()`** - Track scene save location for persistence
- **`remove_scene_save_observer()`** - Remove scene save observer

### Scene Save Tracking
- **`enable_scene_save_tracking()`** - Enable scene save location tracking
- **`disable_scene_save_tracking()`** - Disable scene save location tracking
- **`setup_storage_nodes_for_consistent_saving()`** - Set up storage nodes for consistent saving

### Save Dialog Management
- **`show_pre_save_info()`** - Show information before saving scene
- **`open_save_dialog_with_all_selected()`** - Open save dialog with all items selected
- **`test_custom_save_functionality()`** - Test custom save functionality

### Export and Close Functions
- **`manual_export_with_ct_series()`** - Manual export with CT series setup
- **`check_ct_series_setup()`** - Check CT series setup for export
- **`close_slicer_after_export()`** - Close Slicer application after export

### Volume Addition Monitoring
- **`setup_volume_addition_monitor()`** - Monitor for volume addition to scene
- **`create_volume_waiting_status_widget()`** - Create status widget for volume waiting
- **`update_volume_waiting_status(message)`** - Update volume waiting status message
- **`cleanup_volume_waiting_status_widget()`** - Clean up volume waiting widget
- **`check_for_volume_addition()`** - Check if new volume has been added
- **`stop_volume_addition_monitoring()`** - Stop monitoring for volume addition

---

## 12. WORKFLOW2 FUNCTIONS - CENTERLINE AND TUBE MASK CREATION

### Tube and Centerline Creation
- **`create_centerline_and_tube_mask()`** - Create centerline and tube mask workflow
- **`clear_existing_tubes_and_centerlines()`** - Clear existing tubes and centerlines
- **`create_tube_from_curve(centerline_curve, pair_number)`** - Create tube from centerline curve
- **`create_segmentation_from_tube(tube_model, pair_number)`** - Create segmentation from tube model

### 3D Scene Management
- **`add_cropped_volume_to_3d_scene()`** - Add cropped volume to 3D scene
- **`show_segment_statistics(stenosis_segmentation)`** - Show segment statistics for analysis

---

## 13. UTILITY AND HELPER FUNCTIONS

### UI Point Placement Utilities
- **`validate_point_placement_centerline_reference()`** - Validate point placement centerline reference
- **`ensure_point_placement_mode_active(point_list)`** - Ensure point placement mode stays active
- **`cleanup_point_placement_ui()`** - Clean up point placement UI elements
- **`apply_only_transform_to_point_list(point_list)`** - Apply transform to specific point list

### Module Reset Functions
- **`reset_crop_module_to_default()`** - Reset crop module to default state
- **`reset_extract_centerline_module()`** - Reset extract centerline module
- **`reset_segment_editor_module()`** - Reset segment editor module
- **`reset_cpr_module()`** - Reset CPR module to default state

### Testing and Debugging
- **`debug_centerline_editing()`** - Debug centerline editing functionality
- **`test_restart_cropping_with_preservation()`** - Test restart cropping with preservation
- **`test_crop_module_reset()`** - Test crop module reset functionality
- **`test_full_workflow_reset()`** - Test full workflow reset

### Continue Button Management
- **`create_continue_workflow_button()`** - Create continue button for workflow
- **`create_floating_continue_button()`** - Create floating continue button as fallback
- **`on_continue_from_scissors()`** - Handle continue from scissors tool
- **`cleanup_continue_ui()`** - Clean up continue button UI elements

### Segmentation Utilities
- **`remove_segment_from_all_segmentations(segment_name)`** - Remove segment by name from all segmentations
- **`open_data_module()`** - Open Data module to display imported data

---

## Key Workflow Paths

### Path 1: Standard Workflow
1. **Volume Loading** → DICOM import or volume selection
2. **Volume Cropping** → Custom crop interface with ROI selection
3. **Segmentation** → Threshold-based or imported segmentation
4. **Centerline Extraction** → Extract Centerline module with point placement
5. **CPR Processing** → Curved Planar Reformat for vessel straightening
6. **Analysis** → Point placement, circle drawing, measurements

### Path 2: Markup Import Workflow
1. **Markup Import** → Import existing markup files and transforms
2. **Tube Creation** → Automatic tube mask creation from markup
3. **Volume Processing** → Continue with cropping and analysis
4. **Enhanced Analysis** → Pre-defined analysis masks and measurements

### Path 3: Segmentation Import Workflow
1. **Segmentation Import** → Import existing segmentation file
2. **Skip Threshold** → Bypass threshold creation step
3. **Direct Centerline** → Go directly to centerline extraction
4. **Standard Analysis** → Continue with CPR and measurements

---

## Technical Features

### Programmatic Integration
- **No GUI Dependencies** - All Segment Editor operations are programmatic
- **Custom UI Elements** - Floating controls and custom interfaces
- **Scene Persistence** - Automatic save location tracking
- **Error Handling** - Comprehensive try/catch blocks throughout

### Enhanced DICOM Support
- **Multi-vendor Support** - Philips, Siemens, GE compatibility
- **Robust Loading** - Multiple fallback methods for DICOM loading
- **File Analysis** - Automatic DICOM file type detection
- **Plugin Selection** - Intelligent DICOM plugin confidence adjustment

### Advanced Analysis Tools
- **Multiple Point Types** - Main points, branch points, post-branch points
- **Circle Drawing** - Automatic perpendicular circle creation
- **Transform Management** - Coordinate system handling
- **Measurement Tools** - Stenosis ratio measurements with dual-line setup

---

## Module Dependencies

### Required Slicer Modules
- **Segment Editor** - For segmentation operations
- **Extract Centerline** - For vessel centerline extraction
- **Curved Planar Reformat** - For vessel straightening
- **Cross-Section Analysis** - For cross-sectional measurements
- **Crop Volume** - For volume cropping operations

### Optional Dependencies
- **DICOMLib** - For enhanced DICOM loading (fallback available)
- **ctk** - For advanced UI controls (fallback available)

### Python Libraries
- **Standard Library** - math, os, time
- **Third-party** - numpy, vtk
- **Slicer** - slicer, qt modules

---

This documentation represents the complete feature set of the DAI Workflow module as of November 2025, containing approximately 200+ functions organized into a comprehensive guided workflow for vessel analysis in 3D Slicer.