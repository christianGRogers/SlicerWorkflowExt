"""
Slicer Workflow Test Functions

This file provides access to all test functions, console helpers, debug functions, 
and cleanup utilities for the workflow system.

Christian Rogers - So Lab - Lawson - UWO (2025)

Usage:
    To use these test functions, import this module in your console or script:
    
    >>> from DAI_Workflow.workflow.Moduals import workflow_test_functions as test
    >>> test.test_dicom_workflow()
    
    Or import specific functions:
    
    >>> from DAI_Workflow.workflow.Moduals.workflow_test_functions import test_centerline_monitoring
    >>> test_centerline_monitoring()

Available Test Functions:
    
    CENTERLINE WORKFLOW TESTS:
    - test_centerline_completion_dialog()
    - test_multiple_centerlines_workflow()
    - force_show_completion_dialog()
    - test_specific_centerline_monitoring()
    - test_duplicate_dialog_prevention()
    - debug_centerline_monitoring()
    - test_centerline_monitoring()
    - show_centerline_workflow_help()
    - test_add_centerlines()
    - show_centerline_info()
    - stop_monitoring()
    - stop_apply_monitoring()
    
    DICOM AND VOLUME WORKFLOW TESTS:
    - test_dicom_workflow()
    - test_volume_monitoring()
    - stop_volume_monitoring()
    - skip_to_volume_crop()
    - test_status_widget()
    - cleanup_status_widget()
    - show_dicom_workflow_help()
    
    SEGMENTATION AND SCISSORS WORKFLOW TESTS:
    - test_point_placement_auto_reselection()
    - test_mask_segmentation()
    - test_programmatic_scissors()
    - test_segment_editor_scissors_workflow()
    - test_scissors_toggle()
    - test_scissors_and_finish_buttons()
    - cleanup_all_workflow_scissors_ui()
    
    UI TESTING AND MODIFICATION:
    - test_hide_crop_ui()
    - test_minimal_crop_ui()
    - test_minimal_segment_editor_ui()
    - test_hide_extract_centerline_ui()
    - test_minimal_extract_centerline_ui()
    - test_crop_volume_collapse()
    - restore_crop_ui()
    - restore_extract_centerline_ui()
    - restore_segment_editor_ui()
    - remove_crop_apply_button_manually()
    
    DEBUG AND VERIFICATION:
    - debug_extract_centerline_widgets()
    - debug_point_list_transforms()
    - force_remove_all_transforms()
    - verify_extract_centerline_point_list_autoselection()
    - test_extract_centerline_verification()
    - test_extract_centerline_setup_with_verification()
    - fix_centerline_issues()
    
    MASK CREATION TESTS:
    - create_bone_mask()
    - create_soft_tissue_mask()
    - create_contrast_mask()
    - create_analysis_masks_manually()
"""

# Import all test functions from the main workflow module
# This approach avoids duplication and ensures all functions work correctly
try:
    # Try to import the main workflow module
    from . import workflow_moduals
    
    # Re-export all test functions from the main module
    # Centerline workflow tests
    test_centerline_completion_dialog = getattr(workflow_moduals, 'test_centerline_completion_dialog', None)
    test_multiple_centerlines_workflow = getattr(workflow_moduals, 'test_multiple_centerlines_workflow', None)
    force_show_completion_dialog = getattr(workflow_moduals, 'force_show_completion_dialog', None)
    test_specific_centerline_monitoring = getattr(workflow_moduals, 'test_specific_centerline_monitoring', None)
    test_duplicate_dialog_prevention = getattr(workflow_moduals, 'test_duplicate_dialog_prevention', None)
    debug_centerline_monitoring = getattr(workflow_moduals, 'debug_centerline_monitoring', None)
    test_centerline_monitoring = getattr(workflow_moduals, 'test_centerline_monitoring', None)
    show_centerline_workflow_help = getattr(workflow_moduals, 'show_centerline_workflow_help', None)
    test_add_centerlines = getattr(workflow_moduals, 'test_add_centerlines', None)
    show_centerline_info = getattr(workflow_moduals, 'show_centerline_info', None)
    stop_monitoring = getattr(workflow_moduals, 'stop_monitoring', None)
    stop_apply_monitoring = getattr(workflow_moduals, 'stop_apply_monitoring', None)
    
    # DICOM and volume workflow tests
    test_dicom_workflow = getattr(workflow_moduals, 'test_dicom_workflow', None)
    test_volume_monitoring = getattr(workflow_moduals, 'test_volume_monitoring', None)
    stop_volume_monitoring = getattr(workflow_moduals, 'stop_volume_monitoring', None)
    skip_to_volume_crop = getattr(workflow_moduals, 'skip_to_volume_crop', None)
    test_status_widget = getattr(workflow_moduals, 'test_status_widget', None)
    cleanup_status_widget = getattr(workflow_moduals, 'cleanup_status_widget', None)
    show_dicom_workflow_help = getattr(workflow_moduals, 'show_dicom_workflow_help', None)
    
    # Segmentation and scissors workflow tests
    test_point_placement_auto_reselection = getattr(workflow_moduals, 'test_point_placement_auto_reselection', None)
    test_mask_segmentation = getattr(workflow_moduals, 'test_mask_segmentation', None)
    test_programmatic_scissors = getattr(workflow_moduals, 'test_programmatic_scissors', None)
    test_segment_editor_scissors_workflow = getattr(workflow_moduals, 'test_segment_editor_scissors_workflow', None)
    test_scissors_toggle = getattr(workflow_moduals, 'test_scissors_toggle', None)
    test_scissors_and_finish_buttons = getattr(workflow_moduals, 'test_scissors_and_finish_buttons', None)
    cleanup_all_workflow_scissors_ui = getattr(workflow_moduals, 'cleanup_all_workflow_scissors_ui', None)
    
    # UI testing and modification
    test_hide_crop_ui = getattr(workflow_moduals, 'test_hide_crop_ui', None)
    test_minimal_crop_ui = getattr(workflow_moduals, 'test_minimal_crop_ui', None)
    test_minimal_segment_editor_ui = getattr(workflow_moduals, 'test_minimal_segment_editor_ui', None)
    test_hide_extract_centerline_ui = getattr(workflow_moduals, 'test_hide_extract_centerline_ui', None)
    test_minimal_extract_centerline_ui = getattr(workflow_moduals, 'test_minimal_extract_centerline_ui', None)
    test_crop_volume_collapse = getattr(workflow_moduals, 'test_crop_volume_collapse', None)
    restore_crop_ui = getattr(workflow_moduals, 'restore_crop_ui', None)
    restore_extract_centerline_ui = getattr(workflow_moduals, 'restore_extract_centerline_ui', None)
    restore_segment_editor_ui = getattr(workflow_moduals, 'restore_segment_editor_ui', None)
    remove_crop_apply_button_manually = getattr(workflow_moduals, 'remove_crop_apply_button_manually', None)
    
    # Debug and verification
    debug_extract_centerline_widgets = getattr(workflow_moduals, 'debug_extract_centerline_widgets', None)
    debug_point_list_transforms = getattr(workflow_moduals, 'debug_point_list_transforms', None)
    force_remove_all_transforms = getattr(workflow_moduals, 'force_remove_all_transforms', None)
    verify_extract_centerline_point_list_autoselection = getattr(workflow_moduals, 'verify_extract_centerline_point_list_autoselection', None)
    test_extract_centerline_verification = getattr(workflow_moduals, 'test_extract_centerline_verification', None)
    test_extract_centerline_setup_with_verification = getattr(workflow_moduals, 'test_extract_centerline_setup_with_verification', None)
    fix_centerline_issues = getattr(workflow_moduals, 'fix_centerline_issues', None)
    
    # Mask creation tests
    create_bone_mask = getattr(workflow_moduals, 'create_bone_mask', None)
    create_soft_tissue_mask = getattr(workflow_moduals, 'create_soft_tissue_mask', None)
    create_contrast_mask = getattr(workflow_moduals, 'create_contrast_mask', None)
    create_analysis_masks_manually = getattr(workflow_moduals, 'create_analysis_masks_manually', None)
    
    # Restart cropping workflow functions
    test_restart_cropping_with_preservation = getattr(workflow_moduals, 'test_restart_cropping_with_preservation', None)
    show_restart_cropping_help = getattr(workflow_moduals, 'show_restart_cropping_help', None)
    store_existing_centerlines = getattr(workflow_moduals, 'store_existing_centerlines', None)
    clear_workflow_for_cropping_restart = getattr(workflow_moduals, 'clear_workflow_for_cropping_restart', None)
    restart_cropping_preserving_centerlines = getattr(workflow_moduals, 'restart_cropping_preserving_centerlines', None)
    
    # Module reset functions
    reset_crop_module_to_default = getattr(workflow_moduals, 'reset_crop_module_to_default', None)
    reset_all_workflow_modules = getattr(workflow_moduals, 'reset_all_workflow_modules', None)
    cleanup_crop_module_custom_elements = getattr(workflow_moduals, 'cleanup_crop_module_custom_elements', None)
    restore_all_crop_ui_elements = getattr(workflow_moduals, 'restore_all_crop_ui_elements', None)
    remove_custom_crop_buttons = getattr(workflow_moduals, 'remove_custom_crop_buttons', None)
    test_crop_module_reset = getattr(workflow_moduals, 'test_crop_module_reset', None)
    test_full_workflow_reset = getattr(workflow_moduals, 'test_full_workflow_reset', None)
    restart_cropping_simple = getattr(workflow_moduals, 'restart_cropping_simple', None)
    manual_restart_cropping_help = getattr(workflow_moduals, 'manual_restart_cropping_help', None)
    
    print("Workflow test functions loaded successfully from workflow_moduals")

except ImportError as e:
    print(f"Warning: Could not import workflow_moduals: {e}")
    print("Test functions will not be available.")
    
    # Define placeholder functions that show an error message
    def _unavailable_function(name):
        def placeholder(*args, **kwargs):
            print(f"Error: Function '{name}' is not available. workflow_moduals could not be imported.")
            return False
        return placeholder
    
    # Create placeholder functions for all test functions
    test_centerline_completion_dialog = _unavailable_function('test_centerline_completion_dialog')
    test_multiple_centerlines_workflow = _unavailable_function('test_multiple_centerlines_workflow')
    force_show_completion_dialog = _unavailable_function('force_show_completion_dialog')
    test_specific_centerline_monitoring = _unavailable_function('test_specific_centerline_monitoring')
    test_duplicate_dialog_prevention = _unavailable_function('test_duplicate_dialog_prevention')
    debug_centerline_monitoring = _unavailable_function('debug_centerline_monitoring')
    test_centerline_monitoring = _unavailable_function('test_centerline_monitoring')
    show_centerline_workflow_help = _unavailable_function('show_centerline_workflow_help')
    test_add_centerlines = _unavailable_function('test_add_centerlines')
    show_centerline_info = _unavailable_function('show_centerline_info')
    stop_monitoring = _unavailable_function('stop_monitoring')
    stop_apply_monitoring = _unavailable_function('stop_apply_monitoring')
    test_dicom_workflow = _unavailable_function('test_dicom_workflow')
    test_volume_monitoring = _unavailable_function('test_volume_monitoring')
    stop_volume_monitoring = _unavailable_function('stop_volume_monitoring')
    skip_to_volume_crop = _unavailable_function('skip_to_volume_crop')
    test_status_widget = _unavailable_function('test_status_widget')
    cleanup_status_widget = _unavailable_function('cleanup_status_widget')
    show_dicom_workflow_help = _unavailable_function('show_dicom_workflow_help')
    test_point_placement_auto_reselection = _unavailable_function('test_point_placement_auto_reselection')
    test_mask_segmentation = _unavailable_function('test_mask_segmentation')
    test_programmatic_scissors = _unavailable_function('test_programmatic_scissors')
    test_segment_editor_scissors_workflow = _unavailable_function('test_segment_editor_scissors_workflow')
    test_scissors_toggle = _unavailable_function('test_scissors_toggle')
    test_scissors_and_finish_buttons = _unavailable_function('test_scissors_and_finish_buttons')
    cleanup_all_workflow_scissors_ui = _unavailable_function('cleanup_all_workflow_scissors_ui')
    test_hide_crop_ui = _unavailable_function('test_hide_crop_ui')
    test_minimal_crop_ui = _unavailable_function('test_minimal_crop_ui')
    test_minimal_segment_editor_ui = _unavailable_function('test_minimal_segment_editor_ui')
    test_hide_extract_centerline_ui = _unavailable_function('test_hide_extract_centerline_ui')
    test_minimal_extract_centerline_ui = _unavailable_function('test_minimal_extract_centerline_ui')
    test_crop_volume_collapse = _unavailable_function('test_crop_volume_collapse')
    restore_crop_ui = _unavailable_function('restore_crop_ui')
    restore_extract_centerline_ui = _unavailable_function('restore_extract_centerline_ui')
    restore_segment_editor_ui = _unavailable_function('restore_segment_editor_ui')
    remove_crop_apply_button_manually = _unavailable_function('remove_crop_apply_button_manually')
    debug_extract_centerline_widgets = _unavailable_function('debug_extract_centerline_widgets')
    debug_point_list_transforms = _unavailable_function('debug_point_list_transforms')
    force_remove_all_transforms = _unavailable_function('force_remove_all_transforms')
    verify_extract_centerline_point_list_autoselection = _unavailable_function('verify_extract_centerline_point_list_autoselection')
    test_extract_centerline_verification = _unavailable_function('test_extract_centerline_verification')
    test_extract_centerline_setup_with_verification = _unavailable_function('test_extract_centerline_setup_with_verification')
    fix_centerline_issues = _unavailable_function('fix_centerline_issues')
    create_bone_mask = _unavailable_function('create_bone_mask')
    create_soft_tissue_mask = _unavailable_function('create_soft_tissue_mask')
    create_contrast_mask = _unavailable_function('create_contrast_mask')
    create_analysis_masks_manually = _unavailable_function('create_analysis_masks_manually')
    test_restart_cropping_with_preservation = _unavailable_function('test_restart_cropping_with_preservation')
    show_restart_cropping_help = _unavailable_function('show_restart_cropping_help')
    store_existing_centerlines = _unavailable_function('store_existing_centerlines')
    clear_workflow_for_cropping_restart = _unavailable_function('clear_workflow_for_cropping_restart')
    restart_cropping_preserving_centerlines = _unavailable_function('restart_cropping_preserving_centerlines')
    reset_crop_module_to_default = _unavailable_function('reset_crop_module_to_default')
    reset_all_workflow_modules = _unavailable_function('reset_all_workflow_modules')
    cleanup_crop_module_custom_elements = _unavailable_function('cleanup_crop_module_custom_elements')
    restore_all_crop_ui_elements = _unavailable_function('restore_all_crop_ui_elements')
    remove_custom_crop_buttons = _unavailable_function('remove_custom_crop_buttons')
    test_crop_module_reset = _unavailable_function('test_crop_module_reset')
    test_full_workflow_reset = _unavailable_function('test_full_workflow_reset')
    restart_cropping_simple = _unavailable_function('restart_cropping_simple')
    manual_restart_cropping_help = _unavailable_function('manual_restart_cropping_help')

def list_available_functions():
    """List all available test functions with their descriptions."""
    help_text = """
=== WORKFLOW TEST FUNCTIONS ===

CENTERLINE WORKFLOW TESTS:
• test_centerline_completion_dialog() - Test the centerline completion dialog manually
• test_multiple_centerlines_workflow() - Test the multiple centerlines workflow
• force_show_completion_dialog() - Force show dialog with latest centerlines
• test_specific_centerline_monitoring() - Test the specific centerline monitoring system
• test_duplicate_dialog_prevention() - Test that duplicate dialogs are prevented
• debug_centerline_monitoring() - Debug centerline monitoring state
• test_centerline_monitoring() - Test the centerline monitoring system
• show_centerline_workflow_help() - Show help for centerline workflow
• test_add_centerlines() - Test adding centerlines
• show_centerline_info() - Show centerline information
• stop_monitoring() - Stop centerline monitoring
• stop_apply_monitoring() - Stop Apply button monitoring

DICOM AND VOLUME WORKFLOW TESTS:
• test_dicom_workflow() - Test the DICOM workflow start
• test_volume_monitoring() - Test volume addition monitoring
• stop_volume_monitoring() - Stop volume monitoring manually
• skip_to_volume_crop() - Skip DICOM loading and go directly to volume crop
• test_status_widget() - Test the volume waiting status widget
• cleanup_status_widget() - Clean up the status widget
• show_dicom_workflow_help() - Show help for the DICOM workflow

SEGMENTATION AND SCISSORS WORKFLOW TESTS:
• test_point_placement_auto_reselection() - Test automatic point placement tool re-selection
• test_mask_segmentation() - Test creating a mask segmentation
• test_programmatic_scissors() - Test the new programmatic scissors workflow
• test_segment_editor_scissors_workflow() - Test the complete Segment Editor scissors workflow
• test_scissors_toggle() - Test scissors tool toggle
• test_scissors_and_finish_buttons() - Test the scissors tool and finish cropping buttons
• cleanup_all_workflow_scissors_ui() - Clean up all scissors workflow UI

UI TESTING AND MODIFICATION:
• test_hide_crop_ui() - Test hiding Crop Volume UI elements
• test_minimal_crop_ui() - Test setting up minimal Crop Volume UI
• test_minimal_segment_editor_ui() - Test setting up minimal Segment Editor UI
• test_hide_extract_centerline_ui() - Test hiding Extract Centerline UI elements
• test_minimal_extract_centerline_ui() - Test setting up minimal Extract Centerline UI
• test_crop_volume_collapse() - Test the crop volume GUI collapse functionality
• restore_crop_ui() - Restore all hidden Crop Volume UI elements
• restore_extract_centerline_ui() - Restore all hidden Extract Centerline UI elements
• restore_segment_editor_ui() - Restore all hidden Segment Editor UI elements
• remove_crop_apply_button_manually() - Manually remove the original crop apply button

DEBUG AND VERIFICATION:
• debug_extract_centerline_widgets() - Debug function to list all widgets in Extract Centerline module
• debug_point_list_transforms() - Debug function to check transform status of all F-1 point lists
• force_remove_all_transforms() - Force remove all transforms from F-1 point lists
• verify_extract_centerline_point_list_autoselection() - Verify Extract Centerline point list auto-selection
• test_extract_centerline_verification() - Test the Extract Centerline verification
• test_extract_centerline_setup_with_verification() - Test the full setup with verification
• fix_centerline_issues() - Fix Extract Centerline issues

MASK CREATION TESTS:
• create_bone_mask() - Create a bone density mask
• create_soft_tissue_mask() - Create a soft tissue density mask
• create_contrast_mask() - Create a contrast-enhanced tissue mask
• create_analysis_masks_manually() - Manually create analysis masks

RESTART CROPPING WORKFLOW:
• test_restart_cropping_with_preservation() - Restart cropping while preserving existing centerlines
• show_restart_cropping_help() - Display help for restart cropping functionality
• store_existing_centerlines() - Store centerlines before workflow restart
• clear_workflow_for_cropping_restart() - Clear workflow data while preserving centerlines
• restart_cropping_preserving_centerlines() - Restart cropping workflow with preservation

MODULE RESET FUNCTIONS:
• reset_crop_module_to_default() - Reset Crop Volume module to original default state
• reset_all_workflow_modules() - Reset all workflow modules to default states
• cleanup_crop_module_custom_elements() - Remove custom elements from Crop module
• restore_all_crop_ui_elements() - Restore all UI elements to visible state
• remove_custom_crop_buttons() - Remove custom buttons added during workflow
• test_crop_module_reset() - Test function to quickly reset Crop module
• test_full_workflow_reset() - Test function to reset all workflow modules
• restart_cropping_simple() - Simple restart cropping without preservation (safer)
• manual_restart_cropping_help() - Show manual restart steps if auto-restart fails

USAGE EXAMPLES:
>>> import workflow_test_functions as test
>>> test.test_dicom_workflow()
>>> test.debug_centerline_monitoring()
>>> test.list_available_functions()  # Show this help
"""
    print(help_text)
    return True
