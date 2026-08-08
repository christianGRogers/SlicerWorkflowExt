from ._common import *  # noqa: F401,F403  (shared imports + logger)
from . import core, cpr, markup, segmentation, ui, volume  # sibling modules (cross-calls)

__all__ = [
    'hide_centerlines_from_views',
    'continue_to_centerline_from_left_panel',
    'open_centerline_module',
    'remove_duplicate_centerline_buttons',
    'add_large_centerline_apply_button',
    'cleanup_centerline_ui',
    'setup_centerline_module',
    'verify_extract_centerline_point_list_autoselection',
    'fix_extract_centerline_setup_issues',
    'prepare_surface_for_centerline',
    'apply_cpr_transform_to_centerlines',
    'setup_centerline_completion_monitor',
    'check_specific_centerline_completion',
    'check_centerline_completion',
    'get_current_centerline_for_placement',
    'ensure_point_placement_uses_current_centerline',
    'find_recent_centerline_model',
    'find_all_centerline_models',
    'find_recent_centerline_curve',
    'find_all_centerline_curves',
    'find_nearest_centerline_to_point',
    'populate_centerline_dropdown',
    'stop_centerline_monitoring',
    'validate_point_placement_centerline_reference',
    'show_centerline_completion_dialog',
    'on_retry_centerline',
    'on_add_more_centerlines',
    'on_verify_edit_centerline',
    'show_centerline_editing_dialog',
    'enable_centerline_editing',
    'on_extract_new_centerline_from_edit',
    'on_add_additional_centerline_from_edit',
    'on_reset_centerline_to_original',
    'backup_centerline_points',
    'save_edited_centerline_as_final',
    'cleanup_centerline_edit_dialog',
    'on_reset_centerline_to_original_in_edit',
    'on_close_centerline_editor',
    'disable_centerline_editing',
    'debug_centerline_editing',
    'store_existing_centerlines',
    'restart_cropping_preserving_centerlines',
    'restore_centerline_visibility',
    'setup_post_crop_centerline_restoration',
    'create_additional_centerline_setup',
    'count_existing_centerlines',
    'setup_centerline_for_additional_extraction',
    'clear_centerline_endpoints',
    'stop_all_centerline_monitoring',
    'cleanup_centerline_monitoring_button',
    'clear_existing_centerlines',
    'draw_circles_on_centerline',
    'calculate_centerline_direction',
    'clear_centerline_circles',
    'create_centerline_and_tube_mask',
    'clear_existing_tubes_and_centerlines',
    'hide_extract_centerline_ui_elements',
    'setup_minimal_extract_centerline_ui',
    'restore_extract_centerline_ui',
    'reset_extract_centerline_module',
    'cleanup_extract_centerline_custom_elements',
]

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
        logger.debug("Suppressed exception in hide_centerlines_from_views", exc_info=True)

def continue_to_centerline_from_left_panel():
    """
    Continue to centerline extraction from the left panel tools
    """
    try:
        # Clean up the left panel tools
        segmentation.cleanup_post_threshold_tools()
        
        # Continue with the normal workflow path
        slicer.util.infoDisplay("Proceeding to centerline extraction.\n\nNext: Extract Centerline module will open.")
        
        # Set up for centerline extraction
        qt.QTimer.singleShot(1000, lambda: segmentation.on_continue_from_scissors())
        
    except Exception as e:
        logger.debug("Suppressed exception in continue_to_centerline_from_left_panel", exc_info=True)

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
        
        # Expand the left module panel for ExtractCenterline step
        ui.expand_left_module_panel()
        
        slicer.util.selectModule("ExtractCenterline")
        pass
        slicer.app.processEvents()
        
        # Set up minimal UI with only inputs section
        setup_minimal_extract_centerline_ui()
        
        remove_duplicate_centerline_buttons()
        setup_centerline_module()
        
        # Allow module to fully initialize before forcing point placement
        slicer.app.processEvents()
        time.sleep(0.5)  # Give module time to complete initialization
        
        # Now force point placement tool selection after full initialization
        markup.force_point_placement_tool_selection()
        
        # Additional verification and fixes
        verification_results = verify_extract_centerline_point_list_autoselection()
        if not verification_results["success"]:
            fix_extract_centerline_setup_issues()
            markup.force_point_placement_tool_selection()  # Force again after fixes
            slicer.app.processEvents()
            time.sleep(0.2)
        
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
        logger.debug("Suppressed exception in remove_duplicate_centerline_buttons", exc_info=True)

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
                            # Stop any existing monitoring to prevent duplicates
                            stop_all_centerline_monitoring()
                            # Use apply button monitoring instead of centerline completion monitoring
                            # This provides more direct detection of when Apply is clicked
                            ui.setup_apply_button_monitoring()
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
        logger.debug("Suppressed exception in add_large_centerline_apply_button", exc_info=True)

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
        logger.debug("Suppressed exception in cleanup_centerline_ui", exc_info=True)

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
                                        logger.debug("Suppressed exception in setup_centerline_module", exc_info=True)

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
                        
                        # FORCE point placement mode activation
                        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
                        if interactionNode:
                            # Force interaction mode to Place
                            interactionNode.SetCurrentInteractionMode(interactionNode.Place)
                            interactionNode.SetPlaceModePersistence(1)  # Enable "place multiple control points"
                        
                        # Set this as the active node for point placement
                        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
                        if selectionNode:
                            selectionNode.SetActivePlaceNodeID(endpoint_point_list.GetID())
                        
                        # Force GUI updates to ensure the tool is visually selected
                        slicer.app.processEvents()
                        
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
                        logger.debug("Suppressed exception in setup_centerline_module", exc_info=True)
                    
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
                        logger.debug("Suppressed exception in setup_centerline_module", exc_info=True)
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
                        logger.debug("Suppressed exception in setup_centerline_module", exc_info=True)
                    
                    # Force GUI update and give time for widgets to initialize
                    slicer.app.processEvents()
                    time.sleep(0.2)
                    slicer.app.processEvents()
        add_large_centerline_apply_button()
        
        # Final verification and force point placement if needed
        slicer.app.processEvents()
        time.sleep(0.2)
        
        # Final point placement tool enforcement
        markup.force_point_placement_tool_selection()
        
        markup.prompt_for_endpoints()
        
    except Exception as e:
        logger.debug("Suppressed exception in setup_centerline_module", exc_info=True)

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
        
        # Force GUI updates to ensure changes take effect
        slicer.app.processEvents()
        
        # Also force point placement tool selection
        markup.force_point_placement_tool_selection()
                        
    except Exception as e:
        logger.debug("Suppressed exception in fix_extract_centerline_setup_issues", exc_info=True)

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
                logger.debug("Suppressed exception in apply_cpr_transform_to_centerlines", exc_info=True)
        
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
        logger.debug("Suppressed exception in setup_centerline_completion_monitor", exc_info=True)

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
        logger.debug("Suppressed exception in check_specific_centerline_completion", exc_info=True)

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
            
            # Backup the original centerline for potential reset functionality
            if new_centerline_curve and new_centerline_curve.GetNumberOfControlPoints() > 0:
                backup_centerline_points(new_centerline_curve)
            
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
        logger.debug("Suppressed exception in check_centerline_completion", exc_info=True)

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
                logger.debug("Suppressed exception in ensure_point_placement_uses_current_centerline", exc_info=True)
        
        if centerline_curve:
            try:
                point_list.ReferenceCenterlineCurve = centerline_curve
                pass  # Stored centerline curve reference
            except:
                logger.debug("Suppressed exception in ensure_point_placement_uses_current_centerline", exc_info=True)
        
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
        pass

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
        logger.debug("Suppressed exception in stop_centerline_monitoring", exc_info=True)

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

def show_centerline_completion_dialog(centerline_model=None, centerline_curve=None):
    """
    Show a dialog asking user to retry centerline extraction, add more centerlines, or continue to CPR
    """
    try:
        dialog = qt.QDialog(slicer.util.mainWindow())
        dialog.setWindowTitle("Centerline Extraction Complete")
        dialog.setModal(True)
        dialog.resize(500, 400)
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
            if centerline_curve:
                summary_text += f"\nAnalysis will use: {centerline_curve.GetName()}"
            summary_label = qt.QLabel(summary_text)
            summary_label.setStyleSheet("QLabel { color: #666; margin: 5px 10px; font-size: 11px; font-weight: bold; }")
            layout.addWidget(summary_label)
        
        layout.addSpacing(10)
        instruction_label = qt.QLabel("Choose your next action:")
        instruction_label.setStyleSheet("QLabel { color: #555; margin: 10px; font-size: 12px; font-weight: bold; }")
        layout.addWidget(instruction_label)
        
        # Create four rows of buttons
        first_row_layout = qt.QHBoxLayout()
        second_row_layout = qt.QHBoxLayout()
        third_row_layout = qt.QHBoxLayout()
        fourth_row_layout = qt.QHBoxLayout()
        
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
        
        # Add the new Verify and Edit Centerline button
        verify_edit_button = qt.QPushButton("Verify & Edit Centerline")
        verify_edit_button.setStyleSheet("""
            QPushButton { 
                background-color: #fd7e14; 
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
                background-color: #e8590c; 
            }
            QPushButton:pressed { 
                background-color: #dc5200; 
            }
        """)
        verify_edit_button.connect('clicked()', lambda: on_verify_edit_centerline(dialog, centerline_model, centerline_curve))
        second_row_layout.addWidget(verify_edit_button)
        
        restart_crop_button = qt.QPushButton("Restart Cropping")
        restart_crop_button.setStyleSheet("""
            QPushButton { 
                background-color: #6f42c1; 
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
                background-color: #5a32a3; 
            }
            QPushButton:pressed { 
                background-color: #4e2a8e; 
            }
        """)
        restart_crop_button.connect('clicked()', lambda: volume.on_restart_cropping(dialog, centerline_model, centerline_curve))
        third_row_layout.addWidget(restart_crop_button)
        
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
        continue_button.connect('clicked()', lambda: cpr.on_continue_to_cpr(dialog, centerline_model, centerline_curve))
        fourth_row_layout.addWidget(continue_button)
        
        layout.addLayout(first_row_layout)
        layout.addLayout(second_row_layout)
        layout.addLayout(third_row_layout)
        layout.addLayout(fourth_row_layout)
        layout.addStretch()
        dialog.exec_()
        
    except Exception as e:
        pass
        cpr.switch_to_cpr_module(centerline_model, centerline_curve)

def on_retry_centerline(dialog):
    """
    Called when user chooses to retry centerline extraction
    """
    try:
        # Stop ALL centerline monitoring systems to prevent double dialogs
        stop_all_centerline_monitoring()
        
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
        logger.debug("Suppressed exception in on_retry_centerline", exc_info=True)

def on_add_more_centerlines(dialog):
    """
    Called when user chooses to add more centerlines
    """
    try:
        # Stop ALL centerline monitoring systems to prevent double dialogs
        stop_all_centerline_monitoring()
        
        # Reset the dialog flag to allow future dialogs
        if hasattr(slicer.modules, 'CenterlineDialogShown'):
            slicer.modules.CenterlineDialogShown = False
        
        dialog.close()
        dialog.setParent(None)
        
        # Create a new centerline extraction setup for additional centerlines
        create_additional_centerline_setup()
    except Exception as e:
        logger.debug("Suppressed exception in on_add_more_centerlines", exc_info=True)

        

def on_verify_edit_centerline(dialog, centerline_model=None, centerline_curve=None):
    """
    Called when user chooses to verify and edit the centerline points.
    Opens an editing interface to allow manual adjustment of centerline points.
    """
    try:
        # Stop ALL centerline monitoring systems to prevent double dialogs
        stop_all_centerline_monitoring()
        
        # Reset the dialog flag to allow future dialogs
        if hasattr(slicer.modules, 'CenterlineDialogShown'):
            slicer.modules.CenterlineDialogShown = False
        
        dialog.close()
        dialog.setParent(None)
        
        # Show the centerline editing dialog
        show_centerline_editing_dialog(centerline_model, centerline_curve)
        
    except Exception as e:
        pass
        # Fallback - go to CPR module if editing fails
        cpr.switch_to_cpr_module(centerline_model, centerline_curve)

def show_centerline_editing_dialog(centerline_model=None, centerline_curve=None):
    """
    Show a dialog for editing centerline points with options to extract new centerline or continue to CPR
    """
    try:
        # Find the most recent centerline curve if none provided
        if not centerline_curve:
            centerline_curve = find_recent_centerline_curve()
            
        # Also check for all available centerline curves as fallback
        if not centerline_curve:
            all_curves = find_all_centerline_curves()
            # Try to find any centerline curve in the scene as fallback
            if all_curves:
                centerline_curve = all_curves[-1]  # Use the last one
            else:
                qt.QMessageBox.warning(
                    slicer.util.mainWindow(),
                    "No Centerline Found",
                    "No centerline curve found to edit. Please extract a centerline first."
                )
                return
        
        # Create the editing panel as a docked side panel
        main_window = slicer.util.mainWindow()
        edit_dialog = qt.QDockWidget("Verify and Edit Centerline", main_window)
        edit_dialog.setFeatures(qt.QDockWidget.DockWidgetMovable | qt.QDockWidget.DockWidgetFloatable | qt.QDockWidget.DockWidgetClosable)
        edit_dialog.setAllowedAreas(qt.Qt.LeftDockWidgetArea | qt.Qt.RightDockWidgetArea)
        
        # Create the main widget for the dock
        dock_widget = qt.QWidget()
        edit_dialog.setWidget(dock_widget)
        
        layout = qt.QVBoxLayout(dock_widget)
        
        # Title and instructions
        title_label = qt.QLabel("Centerline Verification and Editing")
        title_label.setStyleSheet("QLabel { font-weight: bold; color: #dc3545; margin: 10px; font-size: 16px; }")
        title_label.setAlignment(qt.Qt.AlignCenter)
        layout.addWidget(title_label)
        
        instructions_text = (
            "Red slice view maximized for optimal centerline editing.\n\n"
            "Editing controls:\n"
            "• Drag control points to move them\n"
            "• Right-click curve → 'Add Point'\n"
            "• Right-click point → 'Delete Point'\n"
            "• Scroll to navigate through slices\n"
            "• Use left panel Markups controls\n\n"
            "Choose your next action:\n"
            "• Add Additional: Saves current edits, lets you add more centerlines\n"
            "• Replace with New: Discards current centerline, starts fresh\n"
            "• Continue to Analysis: Use current centerline for measurements"
        )
        
        instructions_label = qt.QLabel(instructions_text)
        instructions_label.setStyleSheet("QLabel { color: #333; margin: 10px; font-size: 12px; line-height: 18px; }")
        instructions_label.setWordWrap(True)
        layout.addWidget(instructions_label)
        
        # Info about the current centerline and scene status
        if centerline_curve:
            num_points = centerline_curve.GetNumberOfControlPoints()
            
            # Safely get curve length
            try:
                if hasattr(centerline_curve, 'GetCurveLengthWorld'):
                    curve_length = centerline_curve.GetCurveLengthWorld()
                else:
                    curve_length = centerline_curve.GetCurveLength()
            except:
                curve_length = 0.0
            
            # Count total centerlines in scene
            all_centerlines = find_all_centerline_curves()
            total_centerlines = len(all_centerlines)
            
            info_text = f"Current centerline: {centerline_curve.GetName()}\n"
            info_text += f"Control points: {num_points}\n"
            info_text += f"Curve length: {curve_length:.2f} mm\n"
            info_text += f"Total centerlines in scene: {total_centerlines}"
            
            info_label = qt.QLabel(info_text)
            info_label.setStyleSheet("QLabel { color: #666; margin: 5px; font-size: 10px; font-family: monospace; background-color: #f8f9fa; padding: 6px; border-radius: 4px; }")
            layout.addWidget(info_label)
        
        layout.addSpacing(15)
        
        # Action buttons
        button_layout1 = qt.QHBoxLayout()
        button_layout2 = qt.QHBoxLayout()
        
        # Add Additional Centerline button (saves current edits)
        add_additional_button = qt.QPushButton("Add Additional\nCenterline")
        add_additional_button.setStyleSheet("""
            QPushButton { 
                background-color: #17a2b8; 
                color: white; 
                border: none; 
                padding: 10px 8px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 3px;
                font-size: 12px;
                min-height: 50px;
            }
            QPushButton:hover { 
                background-color: #138496; 
            }
            QPushButton:pressed { 
                background-color: #117a8b; 
            }
        """)
        add_additional_button.connect('clicked()', lambda: on_add_additional_centerline_from_edit(edit_dialog, centerline_curve))
        button_layout1.addWidget(add_additional_button)
        
        # Extract new centerline button (replaces current)
        extract_new_button = qt.QPushButton("Replace with New\nCenterline")
        extract_new_button.setStyleSheet("""
            QPushButton { 
                background-color: #ffc107; 
                color: #212529; 
                border: none; 
                padding: 10px 8px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 3px;
                font-size: 12px;
                min-height: 50px;
            }
            QPushButton:hover { 
                background-color: #e0a800; 
            }
            QPushButton:pressed { 
                background-color: #d39e00; 
            }
        """)
        extract_new_button.connect('clicked()', lambda: on_extract_new_centerline_from_edit(edit_dialog, centerline_curve))
        button_layout1.addWidget(extract_new_button)
        
        # Continue to CPR button
        continue_cpr_button = qt.QPushButton("Continue to\nAnalysis")
        continue_cpr_button.setStyleSheet("""
            QPushButton { 
                background-color: #28a745; 
                color: white; 
                border: none; 
                padding: 10px 8px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 3px;
                font-size: 12px;
                min-height: 50px;
            }
            QPushButton:hover { 
                background-color: #218838; 
            }
            QPushButton:pressed { 
                background-color: #1e7e34; 
            }
        """)
        continue_cpr_button.connect('clicked()', lambda: cpr.on_continue_to_cpr_from_edit(edit_dialog, centerline_model, centerline_curve))
        button_layout2.addWidget(continue_cpr_button)
        
        # Reset centerline button
        reset_button = qt.QPushButton("Reset to Original")
        reset_button.setStyleSheet("""
            QPushButton { 
                background-color: #6c757d; 
                color: white; 
                border: none; 
                padding: 8px 8px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 3px;
                font-size: 11px;
                min-height: 35px;
            }
            QPushButton:hover { 
                background-color: #5a6268; 
            }
            QPushButton:pressed { 
                background-color: #545b62; 
            }
        """)
        reset_button.connect('clicked()', lambda: on_reset_centerline_to_original_in_edit(centerline_curve, info_label))
        button_layout2.addWidget(reset_button)
        
        layout.addLayout(button_layout1)
        layout.addLayout(button_layout2)
        
        # Add close button
        close_layout = qt.QHBoxLayout()
        close_button = qt.QPushButton("Close Editor")
        close_button.setStyleSheet("""
            QPushButton { 
                background-color: #dc3545; 
                color: white; 
                border: none; 
                padding: 8px 8px; 
                font-weight: bold;
                border-radius: 6px;
                margin: 3px;
                font-size: 11px;
                min-height: 35px;
            }
            QPushButton:hover { 
                background-color: #c82333; 
            }
            QPushButton:pressed { 
                background-color: #bd2130; 
            }
        """)
        close_button.connect('clicked()', lambda: on_close_centerline_editor(edit_dialog, centerline_curve))
        close_layout.addWidget(close_button)
        
        layout.addLayout(close_layout)
        layout.addStretch()
        
        # Note: Skip custom closeEvent handling to avoid Qt slot override issues
        # The close button and user actions will handle cleanup properly
        
        # Enable editing on the centerline curve
        enable_centerline_editing(centerline_curve)
        
        # Dock the panel to the right side and show it
        main_window.addDockWidget(qt.Qt.RightDockWidgetArea, edit_dialog)
        edit_dialog.show()
        
        # Make the dock widget compact
        edit_dialog.setMinimumWidth(300)
        edit_dialog.setMaximumWidth(400)
        
        # Store reference to dialog for cleanup
        slicer.modules.CenterlineEditDialog = edit_dialog
        
    except Exception as e:
        # Show error message and continue
        error_msg = f"Failed to open centerline editing interface.\n\nError: {str(e)}\n\nContinuing to analysis..."
        qt.QMessageBox.critical(
            slicer.util.mainWindow(),
            "Editing Error",
            error_msg
        )
        cpr.switch_to_cpr_module(centerline_model, centerline_curve)

def enable_centerline_editing(centerline_curve):
    """
    Enable interactive editing of the centerline curve points
    """
    try:
        if not centerline_curve:
            return
        
        # Store current layout for restoration later
        layout_manager = slicer.app.layoutManager()
        if layout_manager:
            current_layout = layout_manager.layout
            slicer.modules.CenterlineEditingOriginalLayout = current_layout
        
        # Switch to cross-sectional view layout for better editing
        core.switch_to_crosssectional_fullscreen()
        
        # Make the curve visible and editable with all control points visible
        display_node = centerline_curve.GetDisplayNode()
        if display_node:
            display_node.SetVisibility(True)
            display_node.SetPropertiesLabelVisibility(True)
            display_node.SetPointLabelsVisibility(True)
            display_node.SetTextScale(3.0)  # Larger text for better visibility
            display_node.SetGlyphScale(3.0)  # Larger control points for easier interaction
            display_node.SetSelectedColor(1.0, 0.0, 0.0)  # Red for selected points
            display_node.SetActiveColor(0.0, 1.0, 0.0)  # Green for active points
            display_node.SetColor(0.0, 0.8, 1.0)  # Cyan for normal points
            display_node.SetOpacity(1.0)  # Full opacity
            display_node.SetLineThickness(0.3)  # Thicker line for better visibility
            
            # Set glyph type to sphere for better visibility
            try:
                display_node.SetGlyphType(slicer.vtkMRMLMarkupsDisplayNode.Sphere3D)
            except:
                pass  # Continue if glyph type setting fails
            
        # Ensure all control points are visible
        for i in range(centerline_curve.GetNumberOfControlPoints()):
            centerline_curve.SetNthControlPointVisibility(i, True)
            
        # Enable interaction and place mode
        centerline_curve.SetLocked(False)
        
        # Set the curve as the active markups node for editing
        selection_node = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selection_node:
            selection_node.SetReferenceActivePlaceNodeID(centerline_curve.GetID())
        
        # Switch to markups module to show editing controls
        try:
            slicer.util.selectModule("Markups")
        except Exception as module_error:
            pass  # Continue even if module switch fails
        
        # Center the view on the centerline
        if centerline_curve.GetNumberOfControlPoints() > 0:
            try:
                # Get the center point of the curve
                bounds = [0, 0, 0, 0, 0, 0]
                centerline_curve.GetBounds(bounds)
                center = [(bounds[0] + bounds[1]) / 2, 
                         (bounds[2] + bounds[3]) / 2, 
                         (bounds[4] + bounds[5]) / 2]
                
                # Center all views on the centerline
                for viewNode in slicer.util.getNodesByClass('vtkMRMLAbstractViewNode'):
                    if viewNode.IsA('vtkMRMLSliceNode'):
                        try:
                            viewNode.JumpSliceByOffsetting(center[0], center[1], center[2])
                        except:
                            pass  # Continue if view centering fails
            except:
                pass  # Continue if bounds calculation fails
        
        # Show information message
        slicer.util.infoDisplay(
            "Centerline editing mode enabled!\n\n"
            "✓ View switched to maximized Red slice for optimal editing\n"
            "✓ All control points are now large, visible, and editable\n"
            "✓ The editing panel is docked on the right side\n\n"
            "Edit the centerline by:\n"
            "• Clicking and dragging control points to move them\n"
            "• Right-clicking on the curve to add new points\n"
            "• Right-clicking on points to delete them\n"
            "• Using the Markups module controls in the left panel\n"
            "• Scrolling through slices to verify positioning\n\n"
            "When finished editing, use the buttons in the side panel.\n"
            "The view will automatically switch to 3D fullscreen when you continue."
        )
        
    except Exception as e:
        raise  # Re-raise the exception so it gets caught by the calling function

def on_extract_new_centerline_from_edit(dock_widget, original_curve):
    """
    Called when user wants to extract a new centerline after editing
    """
    try:
        # Close and cleanup the dock widget
        cleanup_centerline_edit_dialog()
        
        # Exit editing mode and return to appropriate view
        disable_centerline_editing(original_curve)
        
        # Clear existing centerlines
        clear_existing_centerlines()
        
        # Return to centerline extraction module
        open_centerline_module()
        
        # Return to centerline extraction
        slicer.util.infoDisplay(
            "Returning to centerline extraction.\n\n"
            "You can now adjust your endpoints or segmentation if needed,\n"
            "then click 'Apply' again to extract a new centerline.\n\n"
            "The edited centerline has been removed."
        )
        
        # Set up monitoring for new centerline completion
        setup_centerline_completion_monitor()
        
    except Exception as e:
        logger.debug("Suppressed exception in on_extract_new_centerline_from_edit", exc_info=True)

def on_add_additional_centerline_from_edit(dock_widget, original_curve):
    """
    Called when user wants to add additional centerlines while preserving the edited one
    """
    try:
        # Save the current edited centerline with a specific name
        save_edited_centerline_as_final(original_curve)
        
        # Close and cleanup the dock widget
        cleanup_centerline_edit_dialog()
        
        # Exit editing mode and return to appropriate view
        disable_centerline_editing(original_curve)
        
        # Return to centerline extraction module (don't clear existing centerlines)
        open_centerline_module()
        
        # Inform user about the preserved centerline
        slicer.util.infoDisplay(
            "Edited centerline saved and preserved!\n\n"
            "Your edited centerline has been saved and will remain in the scene.\n"
            "You can now add additional centerlines if needed.\n\n"
            "To add more centerlines:\n"
            "• Place new endpoints on the volume\n"
            "• Click 'Apply' to extract additional centerlines\n"
            "• When finished, all centerlines will be available for analysis\n\n"
            "The most recent centerline will be used by default for analysis."
        )
        
        # Set up monitoring for new centerline completion
        setup_centerline_completion_monitor()
        
    except Exception as e:
        logger.debug("Suppressed exception in on_add_additional_centerline_from_edit", exc_info=True)

def on_reset_centerline_to_original(centerline_curve):
    """
    Called when user wants to reset the centerline to its original state
    """
    try:
        if not centerline_curve:
            return
        
        # Check if we have a backup of the original centerline
        curve_id = centerline_curve.GetID()
        backup_key = f"OriginalCenterlineBackup_{curve_id}"
        
        if hasattr(slicer.modules, backup_key):
            original_points = getattr(slicer.modules, backup_key)
            
            # Clear current points
            centerline_curve.RemoveAllControlPoints()
            
            # Restore original points
            for point in original_points:
                centerline_curve.AddControlPoint(point)
                
            slicer.util.infoDisplay("Centerline reset to original state.")
        else:
            qt.QMessageBox.information(
                slicer.util.mainWindow(),
                "Reset Not Available",
                "Original centerline backup not found. Cannot reset to original state."
            )
    
    except Exception as e:
        logger.debug("Suppressed exception in on_reset_centerline_to_original", exc_info=True)

def backup_centerline_points(centerline_curve):
    """
    Create a backup of the centerline control points for potential reset functionality
    """
    try:
        if not centerline_curve or centerline_curve.GetNumberOfControlPoints() == 0:
            return
        
        # Create a list to store the original points
        original_points = []
        
        # Store each control point
        for i in range(centerline_curve.GetNumberOfControlPoints()):
            point = [0, 0, 0]
            centerline_curve.GetNthControlPointPosition(i, point)
            original_points.append(point[:])  # Make a copy of the point
        
        # Store the backup using the curve ID to make it specific to this centerline
        curve_id = centerline_curve.GetID()
        backup_key = f"OriginalCenterlineBackup_{curve_id}"
        setattr(slicer.modules, backup_key, original_points)
        
        pass  # Backup created successfully
        
    except Exception as e:
        logger.debug("Suppressed exception in backup_centerline_points", exc_info=True)

def save_edited_centerline_as_final(centerline_curve):
    """
    Save the current edited centerline with a descriptive name to preserve it
    """
    try:
        if not centerline_curve or centerline_curve.GetNumberOfControlPoints() == 0:
            return
        
        # Get current timestamp for unique naming
        import datetime
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        
        # Rename the centerline to indicate it's been edited and finalized
        original_name = centerline_curve.GetName()
        if "edited" not in original_name.lower():
            new_name = f"{original_name}_Edited_{timestamp}"
        else:
            new_name = f"{original_name}_{timestamp}"
        
        centerline_curve.SetName(new_name)
        
        # Ensure the curve is visible and properly styled for preservation
        display_node = centerline_curve.GetDisplayNode()
        if display_node:
            display_node.SetVisibility(True)
            display_node.SetColor(0.0, 0.8, 0.2)  # Green color to indicate finalized
            display_node.SetOpacity(0.8)
            display_node.SetLineThickness(0.3)
            
        # Lock the curve to prevent accidental modifications
        centerline_curve.SetLocked(True)
        
        # Hide control points since it's finalized
        for i in range(centerline_curve.GetNumberOfControlPoints()):
            centerline_curve.SetNthControlPointVisibility(i, False)
            
        # Store this as a preserved centerline for future reference
        if not hasattr(slicer.modules, 'PreservedCenterlines'):
            slicer.modules.PreservedCenterlines = []
        slicer.modules.PreservedCenterlines.append(centerline_curve)
        
        pass  # Centerline saved successfully
        
    except Exception as e:
        logger.debug("Suppressed exception in save_edited_centerline_as_final", exc_info=True)

def cleanup_centerline_edit_dialog():
    """
    Clean up the centerline edit dialog reference and remove dock widget
    """
    try:
        if hasattr(slicer.modules, 'CenterlineEditDialog'):
            dock_widget = slicer.modules.CenterlineEditDialog
            if dock_widget:
                main_window = slicer.util.mainWindow()
                if main_window:
                    main_window.removeDockWidget(dock_widget)
                dock_widget.setParent(None)
            delattr(slicer.modules, 'CenterlineEditDialog')
    except Exception as e:
        logger.debug("Suppressed exception in cleanup_centerline_edit_dialog", exc_info=True)

def on_reset_centerline_to_original_in_edit(centerline_curve, info_label):
    """
    Called when user wants to reset the centerline to its original state during editing.
    Updates the dialog with new information after reset.
    """
    try:
        if not centerline_curve:
            return
        
        # Check if we have a backup of the original centerline
        curve_id = centerline_curve.GetID()
        backup_key = f"OriginalCenterlineBackup_{curve_id}"
        
        if hasattr(slicer.modules, backup_key):
            original_points = getattr(slicer.modules, backup_key)
            
            # Clear current points
            centerline_curve.RemoveAllControlPoints()
            
            # Restore original points
            for point in original_points:
                centerline_curve.AddControlPoint(point)
            
            # Update the info label with new stats
            num_points = centerline_curve.GetNumberOfControlPoints()
            
            # Safely get curve length
            try:
                if hasattr(centerline_curve, 'GetCurveLengthWorld'):
                    curve_length = centerline_curve.GetCurveLengthWorld()
                else:
                    curve_length = centerline_curve.GetCurveLength()
            except:
                curve_length = 0.0
            
            # Count total centerlines in scene
            all_centerlines = find_all_centerline_curves()
            total_centerlines = len(all_centerlines)
            
            info_text = f"Current centerline: {centerline_curve.GetName()}\n"
            info_text += f"Control points: {num_points}\n"
            info_text += f"Curve length: {curve_length:.2f} mm\n"
            info_text += f"Total centerlines in scene: {total_centerlines}"
            info_label.setText(info_text)
                
            slicer.util.infoDisplay("Centerline reset to original state.", windowTitle="Reset Complete")
        else:
            qt.QMessageBox.information(
                slicer.util.mainWindow(),
                "Reset Not Available",
                "Original centerline backup not found. Cannot reset to original state."
            )
    
    except Exception as e:
        logger.debug("Suppressed exception in on_reset_centerline_to_original_in_edit", exc_info=True)

def on_close_centerline_editor(dock_widget, centerline_curve):
    """
    Called when user clicks the close editor button
    """
    try:
        # Exit editing mode and return to 3D fullscreen
        disable_centerline_editing(centerline_curve)
        
        # Close and cleanup dock widget
        cleanup_centerline_edit_dialog()
        
        slicer.util.infoDisplay("Centerline editor closed. Returned to 3D view. You can now continue with your workflow.")
        
    except Exception as e:
        logger.debug("Suppressed exception in on_close_centerline_editor", exc_info=True)

def disable_centerline_editing(centerline_curve):
    """
    Disable editing mode for the centerline curve and switch to 3D fullscreen view
    """
    try:
        if centerline_curve:
            # Lock the curve and hide editing controls
            centerline_curve.SetLocked(True)
            display_node = centerline_curve.GetDisplayNode()
            if display_node:
                display_node.SetPropertiesLabelVisibility(False)
                display_node.SetPointLabelsVisibility(False)
                
            # Hide all control points
            for i in range(centerline_curve.GetNumberOfControlPoints()):
                centerline_curve.SetNthControlPointVisibility(i, False)
        
        # Clear active markups selection to exit editing mode
        selection_node = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        if selection_node:
            selection_node.SetReferenceActivePlaceNodeID(None)
            
        # Switch to 3D fullscreen view
        core.switch_to_3d_fullscreen()
        
    except Exception as e:
        logger.debug("Suppressed exception in disable_centerline_editing", exc_info=True)

def debug_centerline_editing():
    """
    Debug function to test centerline editing - run this in Slicer console
    """
    try:
        logger.info("DEBUG: Starting centerline editing debug...")
        
        # Check for centerlines
        all_curves = find_all_centerline_curves()
        logger.info(f"DEBUG: Found {len(all_curves)} centerline curves")
        
        for i, curve in enumerate(all_curves):
            if curve:
                logger.info(f"  Curve {i}: {curve.GetName()}, Points: {curve.GetNumberOfControlPoints()}")
            else:
                logger.info(f"  Curve {i}: None")
        
        if not all_curves:
            logger.info("DEBUG: No centerline curves found in scene")
            return False
        
        # Try to open editing dialog with the first curve
        curve = all_curves[0]
        logger.info(f"DEBUG: Attempting to open editing dialog with curve: {curve.GetName()}")
        
        show_centerline_editing_dialog(None, curve)
        return True
        
    except Exception as e:
        logger.info(f"DEBUG: Error in debug_centerline_editing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# Removed show_restart_completion_message function - no longer needed


def store_existing_centerlines():
    """
    Store references to existing centerlines to preserve them during workflow restart
    """
    try:
        # Find all existing centerline models and curves
        centerline_models = find_all_centerline_models()
        centerline_curves = find_all_centerline_curves()
        
        # Store them in the slicer modules for persistence
        slicer.modules.PreservedCenterlineModels = [model.GetID() for model in centerline_models]
        slicer.modules.PreservedCenterlineCurves = [curve.GetID() for curve in centerline_curves]
        
        # Also store their current visibility states
        model_visibility = {}
        curve_visibility = {}
        
        for model in centerline_models:
            display_node = model.GetDisplayNode()
            if display_node:
                model_visibility[model.GetID()] = display_node.GetVisibility()
        
        for curve in centerline_curves:
            display_node = curve.GetDisplayNode()
            if display_node:
                curve_visibility[curve.GetID()] = display_node.GetVisibility()
        
        slicer.modules.PreservedModelVisibility = model_visibility
        slicer.modules.PreservedCurveVisibility = curve_visibility
        
        
    except Exception as e:
        logger.debug("Suppressed exception in store_existing_centerlines", exc_info=True)

        # Don't let this stop the restart process - continue anyway


def restart_cropping_preserving_centerlines():
    """
    Restart the cropping workflow while maintaining existing centerlines
    """
    try:
        # Ensure centerlines remain visible
        restore_centerline_visibility()
        
        # Reset the Crop Volume module to default state first
        volume.reset_crop_module_to_default()
        
        # Start the volume cropping workflow
        volume.start_with_volume_crop()
        
        # Set up monitoring to restore centerlines after cropping completion
        setup_post_crop_centerline_restoration()
        
        
    except Exception as e:
        logger.debug("Suppressed exception in restart_cropping_preserving_centerlines", exc_info=True)

def restore_centerline_visibility():
    """
    Restore visibility of preserved centerlines
    """
    try:
        if hasattr(slicer.modules, 'PreservedCenterlineModels'):
            model_ids = slicer.modules.PreservedCenterlineModels
            model_visibility = getattr(slicer.modules, 'PreservedModelVisibility', {})
            
            for model_id in model_ids:
                model = slicer.mrmlScene.GetNodeByID(model_id)
                if model:
                    display_node = model.GetDisplayNode()
                    if display_node:
                        # Restore original visibility or make visible by default
                        visibility = model_visibility.get(model_id, True)
                        display_node.SetVisibility(visibility)
        
        if hasattr(slicer.modules, 'PreservedCenterlineCurves'):
            curve_ids = slicer.modules.PreservedCenterlineCurves
            curve_visibility = getattr(slicer.modules, 'PreservedCurveVisibility', {})
            
            for curve_id in curve_ids:
                curve = slicer.mrmlScene.GetNodeByID(curve_id)
                if curve:
                    display_node = curve.GetDisplayNode()
                    if display_node:
                        # Restore original visibility or make visible by default
                        visibility = curve_visibility.get(curve_id, True)
                        display_node.SetVisibility(visibility)
        
        
    except Exception as e:
        logger.debug("Suppressed exception in restore_centerline_visibility", exc_info=True)

def setup_post_crop_centerline_restoration():
    """
    Set up monitoring to ensure centerlines remain functional after cropping
    """
    try:
        # This will be called after crop completion to ensure centerlines work with new cropped volume
        # For now, we'll rely on the existing crop completion monitoring
        pass
        
    except Exception as e:
        logger.debug("Suppressed exception in setup_post_crop_centerline_restoration", exc_info=True)

def create_additional_centerline_setup():
    """
    Create new centerline model and curve nodes and set up Extract Centerline module for additional centerlines
    """
    try:
        # Expand the left module panel for additional centerline extraction
        ui.expand_left_module_panel()
        
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
        ui.setup_apply_button_monitoring()
        
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
                
            # Set segment selector for the workflow segment
            workflow_segment_id = workflow_segmentation.GetAttribute("WorkflowCreatedSegmentID")
            if workflow_segment_id:
                segmentation = workflow_segmentation.GetSegmentation()
                segment = segmentation.GetSegment(workflow_segment_id)
                if segment:
                    segment_set = False
                    for selector_name in ['inputSegmentSelector', 'segmentSelector', 'inputSurfaceSegmentSelector']:
                        if hasattr(centerline_module.ui, selector_name):
                            try:
                                getattr(centerline_module.ui, selector_name).setCurrentSegmentID(workflow_segment_id)
                                segment_set = True
                                break
                            except Exception as e:
                                logger.debug("Suppressed exception in setup_centerline_for_additional_extraction", exc_info=True)
                
        # Create and set up new endpoint fiducial list for point placement
        try:
            # Get the count of existing centerlines for unique naming
            existing_count = count_existing_centerlines()
            endpoint_point_list = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
            endpoint_point_list.SetName(f"CenterlineEndpoints_{existing_count + 1}")
            
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
            logger.debug("Suppressed exception in setup_centerline_for_additional_extraction", exc_info=True)
                
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
            logger.debug("Suppressed exception in setup_centerline_for_additional_extraction", exc_info=True)
        
        # Force GUI update and give time for widgets to initialize
        slicer.app.processEvents()
        time.sleep(0.2)
        slicer.app.processEvents()
        
        # Verify that point placement is properly set up
        verification_results = verify_extract_centerline_point_list_autoselection()
        if not verification_results["success"]:
            pass
            fix_extract_centerline_setup_issues()
            # Re-verify after fixes
            time.sleep(0.2)
            slicer.app.processEvents()
            verification_results = verify_extract_centerline_point_list_autoselection()
        
        # Force point placement tool selection one final time
        markup.force_point_placement_tool_selection()
        
        # Add the large Apply button again
        add_large_centerline_apply_button()
        
    except Exception as e:
        logger.debug("Suppressed exception in setup_centerline_for_additional_extraction", exc_info=True)

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
        logger.debug("Suppressed exception in clear_centerline_endpoints", exc_info=True)

def stop_all_centerline_monitoring():
    """
    Stop all centerline monitoring systems to prevent double dialogs
    """
    try:
        # Stop the main centerline completion monitoring
        stop_centerline_monitoring()
        
        # Stop the apply button monitoring
        ui.stop_apply_button_monitoring()
        
        pass
        
    except Exception as e:
        logger.debug("Suppressed exception in stop_all_centerline_monitoring", exc_info=True)

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
        logger.debug("Suppressed exception in cleanup_centerline_monitoring_button", exc_info=True)

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
        logger.debug("Suppressed exception in clear_existing_centerlines", exc_info=True)

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
        core.cleanup_orphaned_start_markers()
        
        centerline_model = None
        try:
            centerline_model = slicer.util.getNode('Centerline model')
        except:
            logger.debug("Suppressed exception in draw_circles_on_centerline", exc_info=True)
        
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
            
            markup.apply_transform_to_circle(circle_node)
            
            # Calculate centerline direction for perpendicular circles
            centerline_direction = calculate_centerline_direction(points, closest_centerline_idx)
            
            success = markup.create_perpendicular_circle(circle_node, center_point, radius, centerline_direction)
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
        markup.update_circle_dropdown()
        
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
            node_name = node.GetName().lower()
            if ('circle' in node_name and 'centerline' in node_name) or \
               ('axialcircle' in node_name) or \
               (node.GetName().startswith('Circle_')):  # Clear all workflow circles
                slicer.mrmlScene.RemoveNode(node)
                removed_count += 1
        
        if removed_count > 0:
            pass
            # Update circle dropdown after clearing circles
            markup.update_circle_dropdown()
        else:
            pass
            
        return removed_count > 0
        
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
        tube_model = markup.create_tube_from_curve(centerline_curve, pair_index + 1)
        
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
            stenosis_segmentation = segmentation.create_segmentation_from_tube(tube_model, pair_index + 1)
            if stenosis_segmentation:
                created_segmentations.append(stenosis_segmentation)
        
        pass
    
    # Add cropped volume to 3D scene
    volume.add_cropped_volume_to_3d_scene()
    
    # Show statistics for all segmentations
    for segmentation in created_segmentations:
        segmentation.show_segment_statistics(segmentation)
    
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
        logger.debug("Suppressed exception in clear_existing_tubes_and_centerlines", exc_info=True)

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
                logger.debug("Suppressed exception in hide_extract_centerline_ui_elements", exc_info=True)
        
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
                        logger.debug("Suppressed exception in hide_extract_centerline_ui_elements", exc_info=True)
                
                if not collapsed_successfully:
                    pass
                    
        except Exception as e:
            logger.debug("Suppressed exception in hide_extract_centerline_ui_elements", exc_info=True)
        
        # Double-check advanced section is completely hidden
        try:
            advanced_buttons = extract_centerline_widget.findChildren("ctkCollapsibleButton", "advancedCollapsibleButton")
            for button in advanced_buttons:
                button.setVisible(False)
                button.hide()  # Also explicitly call hide()
                elements_hidden += 1
                pass
        except Exception as e:
            logger.debug("Suppressed exception in hide_extract_centerline_ui_elements", exc_info=True)
        
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
            logger.debug("Suppressed exception in hide_extract_centerline_ui_elements", exc_info=True)
        
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
            logger.debug("Suppressed exception in hide_extract_centerline_ui_elements", exc_info=True)
        
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
            logger.debug("Suppressed exception in hide_extract_centerline_ui_elements", exc_info=True)
        
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
            logger.debug("Suppressed exception in hide_extract_centerline_ui_elements", exc_info=True)
        
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
            logger.debug("Suppressed exception in hide_extract_centerline_ui_elements", exc_info=True)
        
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
                        logger.debug("Suppressed exception in hide_extract_centerline_ui_elements", exc_info=True)
                
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
                        logger.debug("Suppressed exception in hide_extract_centerline_ui_elements", exc_info=True)
            
            # Note: Apply button widgets are intentionally left visible and functional
                    
        except Exception as e:
            logger.debug("Suppressed exception in hide_extract_centerline_ui_elements", exc_info=True)
        
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
        # Expand the left module panel for ExtractCenterline setup
        ui.expand_left_module_panel()
        
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

def reset_extract_centerline_module():
    """Reset the Extract Centerline module to default state."""
    try:
        # Switch modules to trigger reload
        slicer.util.selectModule("Welcome")
        slicer.app.processEvents()
        
        # Clean up Extract Centerline specific elements
        cleanup_extract_centerline_custom_elements()
        
        slicer.util.selectModule("ExtractCenterline")
        slicer.app.processEvents()
        
        # Restore UI elements
        restore_extract_centerline_ui()
        
        return True
        
    except Exception as e:
        return False

def cleanup_extract_centerline_custom_elements():
    """Clean up custom elements from Extract Centerline module."""
    try:
        centerline_attributes = [
            'CenterlineMonitorTimer',
            'CenterlineDialogShown', 
            'BaselineCenterlineModelCount',
            'BaselineCenterlineCurveCount',
            'CenterlineCheckCount',
            'TargetCenterlineModels',
            'TargetCenterlineCurves',
            'CenterlineMonitoringStartTime'
        ]
        
        for attr in centerline_attributes:
            if hasattr(slicer.modules, attr):
                delattr(slicer.modules, attr)
        
        # Stop any active monitoring
        stop_all_centerline_monitoring()
        
    except Exception as e:
        logger.debug("Suppressed exception in cleanup_extract_centerline_custom_elements", exc_info=True)
