from ._common import *  # noqa: F401,F403  (shared imports + logger)
from . import centerline, core, markup, segmentation, volume  # sibling modules (cross-calls)

__all__ = [
    'initialize_workflow_ui',
    'force_collapse_left_panel_on_startup',
    'collapse_left_module_panel',
    'expand_left_module_panel',
    'set_volume_visible_in_slice_views',
    'show_red_green_views_only',
    'set_three_up_view',
    'set_3d_only_view',
    'set_3d_view_background_black',
    'create_continue_workflow_button',
    'create_floating_continue_button',
    'add_continue_button_to_crop_module',
    'collapse_crop_volume_gui',
    'cleanup_continue_ui',
    'cleanup_workflow_ui',
    'add_large_crop_apply_button',
    'collapse_parameters_tab',
    'toggle_window_level_tool',
    'show_saved_scene_locations',
    'show_pre_save_info',
    'open_save_dialog_with_all_selected',
    'cleanup_all_workflow_ui',
    'restore_original_layout',
    'setup_apply_button_monitoring',
    'check_for_apply_button_click',
    'stop_apply_button_monitoring',
    'hide_crop_volume_ui_elements',
    'restore_crop_ui',
    'show_keyboard_undo_help',
    'add_buttons_to_crop_module',
    'ensure_crop_button_disabled_if_completed',
    'disable_crop_apply_button',
    'remove_original_crop_apply_button',
    'restore_original_crop_apply_button',
    'show_restart_cropping_help',
    'restore_all_crop_ui_elements',
    'remove_custom_crop_buttons',
    'create_initial_custom_crop_interface',
    'create_custom_crop_interface',
    'setup_crop_display_layout',
    'cleanup_custom_crop_interface',
    'force_custom_crop_interface',
    'onSlicerAboutToQuit',
]

def initialize_workflow_ui():
    """Initialize the workflow UI state - collapse left panel on startup"""
    try:
        # Use QTimer to ensure this runs after the UI is fully loaded
        qt.QTimer.singleShot(1000, force_collapse_left_panel_on_startup)
    except Exception as e:
        logger.error(f"Warning: Could not initialize workflow UI: {e}")

def force_collapse_left_panel_on_startup():
    """Force collapse of left panel on startup - more aggressive approach"""
    try:
        main_window = slicer.util.mainWindow()
        if not main_window:
            return False
            
        success = False
        
        # Method 1: Try to find and hide the module panel dock widget
        try:
            dock_widgets = main_window.findChildren(qt.QDockWidget)
            for widget in dock_widgets:
                widget_name = widget.objectName()
                if widget_name and ('module' in widget_name.lower() or 'panel' in widget_name.lower()):
                    widget.hide()
                    success = True
        except Exception as e:
            logger.error(f"Warning: Could not hide dock widgets: {e}")
        
        # Method 2: Try specific known panel names
        try:
            known_panel_names = ['PanelDockWidget', 'ModulePanelDockWidget']
            for panel_name in known_panel_names:
                panels = main_window.findChildren(qt.QWidget, panel_name)
                for panel in panels:
                    panel.hide()
                    success = True
        except Exception as e:
            logger.error(f"Warning: Could not hide known panel widgets: {e}")
        
        # Method 3: Try to find all QWidget children and hide panel-related ones
        try:
            all_widgets = main_window.findChildren(qt.QWidget)
            for widget in all_widgets:
                widget_name = widget.objectName()
                if widget_name and ("PanelDockWidget" in widget_name or "ModulePanel" in widget_name):
                    widget.hide()
                    success = True
        except Exception as e:
            logger.error(f"Warning: Could not hide panel-related widgets: {e}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in force_collapse_left_panel_on_startup: {e}")
        return False

def collapse_left_module_panel():
    """
    Collapse the left module panel to maximize view space during workflow.
    """
    try:
        main_window = slicer.util.mainWindow()
        if not main_window:
            return False
        
        success = False
        
        # Method 1: Find and collapse/hide dock widgets
        try:
            dock_widgets = main_window.findChildren(qt.QDockWidget)
            for widget in dock_widgets:
                widget_name = widget.objectName()
                if widget_name and ('module' in widget_name.lower() or 'panel' in widget_name.lower()):
                    widget.hide()
                    success = True
        except Exception as e:
            logger.error(f"Warning: Could not hide dock widgets in collapse_left_module_panel: {e}")
        
        # Method 2: Try specific panel names
        try:
            panel_names = ['ModulePanelDockWidget', 'PanelDockWidget']
            for panel_name in panel_names:
                panels = main_window.findChildren(qt.QWidget, panel_name)
                for panel in panels:
                    panel.hide()
                    success = True
        except Exception as e:
            logger.error(f"Warning: Could not hide specific panels in collapse_left_module_panel: {e}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in collapse_left_module_panel: {e}")
        return False

def expand_left_module_panel():
    """
    Expand the left module panel when needed (e.g., for Extract Centerline step).
    """
    try:
        main_window = slicer.util.mainWindow()
        if not main_window:
            return False
        
        success = False
        
        # Method 1: Find and show dock widgets
        try:
            dock_widgets = main_window.findChildren(qt.QDockWidget)
            for widget in dock_widgets:
                widget_name = widget.objectName()
                if widget_name and ('module' in widget_name.lower() or 'panel' in widget_name.lower()):
                    widget.show()
                    success = True
        except Exception as e:
            logger.error(f"Warning: Could not show dock widgets in expand_left_module_panel: {e}")
        
        # Method 2: Try specific panel names
        try:
            panel_names = ['ModulePanelDockWidget', 'PanelDockWidget']
            for panel_name in panel_names:
                panels = main_window.findChildren(qt.QWidget, panel_name)
                for panel in panels:
                    panel.show()
                    success = True
        except Exception as e:
            logger.error(f"Warning: Could not show specific panels in expand_left_module_panel: {e}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in expand_left_module_panel: {e}")
        return False

def set_volume_visible_in_slice_views(volume_node):
    """
    Set the volume as visible and active in all slice views
    """
    try:
        # Get the application logic
        app_logic = slicer.app.applicationLogic()
        if app_logic:
            selection_node = app_logic.GetSelectionNode()
            if selection_node:
                # Set as active volume
                selection_node.SetActiveVolumeID(volume_node.GetID())
                selection_node.SetSecondaryVolumeID(volume_node.GetID())
                
                # Propagate the selection
                app_logic.PropagateVolumeSelection()
        
        # Also set in slice composite nodes directly
        layout_manager = slicer.app.layoutManager()
        if layout_manager:
            for slice_view_name in ['Red', 'Yellow', 'Green']:
                slice_logic = layout_manager.sliceWidget(slice_view_name).sliceLogic()
                if slice_logic:
                    composite_node = slice_logic.GetSliceCompositeNode()
                    if composite_node:
                        composite_node.SetBackgroundVolumeID(volume_node.GetID())
        
        # Reset field of view to show the volume properly
        slicer.util.resetSliceViews()
    
        
    except Exception as e:
        logger.debug("Suppressed exception in set_volume_visible_in_slice_views", exc_info=True)

def show_red_green_views_only():
    """
    Switch Slicer layout to show only Red and Green slice views side-by-side.
    Also set the current working volume in both views and fit to slice.
    """
    try:
        lm = slicer.app.layoutManager()
        if not lm:
            return False

        # Define a custom two-slice layout (Red | Green)
        layout_xml = (
            '<layout type="horizontal">'
            '  <item>'
            '    <view class="vtkMRMLSliceNode" singletontag="Red">'
            '      <property name="orientation" action="default">Axial</property>'
            '      <property name="viewlabel" action="default">R</property>'
            '      <property name="layoutlabel" action="default">Red</property>'
            '    </view>'
            '  </item>'
            '  <item>'
            '    <view class="vtkMRMLSliceNode" singletontag="Green">'
            '      <property name="orientation" action="default">Sagittal</property>'
            '      <property name="viewlabel" action="default">G</property>'
            '      <property name="layoutlabel" action="default">Green</property>'
            '    </view>'
            '  </item>'
            '</layout>'
        )

        layout_node = lm.layoutLogic().GetLayoutNode()
        custom_layout_id = 55901  # Arbitrary, low collision risk
        # Register or replace the custom layout
        layout_node.AddLayoutDescription(custom_layout_id, layout_xml)
        layout_node.SetViewArrangement(custom_layout_id)

        # Assign background volume and fit to slice for both Red and Green
        vol = volume.find_working_volume()
        for name in ("Red", "Green"):
            w = lm.sliceWidget(name)
            if not w:
                continue
            comp = w.mrmlSliceCompositeNode()
            if vol and comp:
                comp.SetBackgroundVolumeID(vol.GetID())
            logic = w.sliceLogic()
            if logic:
                logic.FitSliceToAll()

        slicer.app.processEvents()
        return True
    except Exception:
        return False

def set_three_up_view():
    """
    Switch Slicer layout to show three slice views side by side: Red, Green, Yellow (Axial, Sagittal, Coronal).
    This is used before cropping to give a complete view of the volume without 3D view.
    """
    try:
        lm = slicer.app.layoutManager()
        if not lm:
            return False

        # Define a custom three-slice layout (Red | Green | Yellow) side by side
        layout_xml = (
            '<layout type="horizontal">'
            '  <item>'
            '    <view class="vtkMRMLSliceNode" singletontag="Red">'
            '      <property name="orientation" action="default">Axial</property>'
            '      <property name="viewlabel" action="default">R</property>'
            '      <property name="layoutlabel" action="default">Red</property>'
            '    </view>'
            '  </item>'
            '  <item>'
            '    <view class="vtkMRMLSliceNode" singletontag="Green">'
            '      <property name="orientation" action="default">Sagittal</property>'
            '      <property name="viewlabel" action="default">G</property>'
            '      <property name="layoutlabel" action="default">Green</property>'
            '    </view>'
            '  </item>'
            '  <item>'
            '    <view class="vtkMRMLSliceNode" singletontag="Yellow">'
            '      <property name="orientation" action="default">Coronal</property>'
            '      <property name="viewlabel" action="default">Y</property>'
            '      <property name="layoutlabel" action="default">Yellow</property>'
            '    </view>'
            '  </item>'
            '</layout>'
        )

        layout_node = lm.layoutLogic().GetLayoutNode()
        custom_layout_id = 55902  # Custom ID for three-slice layout
        # Register or replace the custom layout
        layout_node.AddLayoutDescription(custom_layout_id, layout_xml)
        layout_node.SetViewArrangement(custom_layout_id)
        
        # Assign background volume for all three views
        vol = volume.find_working_volume()
        for name in ("Red", "Green", "Yellow"):
            w = lm.sliceWidget(name)
            if not w:
                continue
            comp = w.mrmlSliceCompositeNode()
            if vol and comp:
                comp.SetBackgroundVolumeID(vol.GetID())
            logic = w.sliceLogic()
            if logic:
                logic.FitSliceToAll()

        # Give time for volumes to load into views before resetting
        slicer.app.processEvents()
        
        # Now call resetSliceViews after volumes are loaded for it to be effective
        slicer.util.resetSliceViews()

        # Final processing to ensure proper rendering
        slicer.app.processEvents()
        qt.QTimer.singleShot(100, lambda: slicer.app.processEvents())
        
        return True
    except Exception as e:
        pass
        return False

def set_3d_only_view():
    """
    Switch Slicer layout to show only the 3D view.
    This is used after cropping to focus on 3D visualization.
    """
    try:
        lm = slicer.app.layoutManager()
        if not lm:
            return False

        # Set to 3D-only layout (layout ID 4 in Slicer)
        layout_node = lm.layoutLogic().GetLayoutNode()
        layout_node.SetViewArrangement(4)  # 3D only view
        
        # Make sure 3D view shows the current working volume
        vol = volume.find_working_volume()
        if vol:
            # Ensure volume is visible in 3D
            vol.SetDisplayVisibility(True)
            
            # Get 3D view and reset camera
            threeDWidget = lm.threeDWidget(0)
            if threeDWidget:
                threeDView = threeDWidget.threeDView()
                if threeDView:
                    threeDView.resetFocalPoint()
                    threeDView.resetCamera()

        slicer.app.processEvents()
        return True
    except Exception as e:
        pass
        return False

def set_3d_view_background_black():
    """
    Set the 3D view background to black using the working approach from ChangeViewColors example
    """
    try:
        # Get the first 3D view node (typically "View1")
        viewNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLViewNode")
        if not viewNode:
            # If no view node exists, try to get by name
            viewNode = slicer.util.getNode("View1")
        
        if viewNode:
            # Create black color (same as your working example)
            black_color = qt.QColor(0, 0, 0)  # RGB values 0,0,0 for black
            
            # Convert to normalized values (0-1 range) as in your working example
            r = black_color.red() / 255.0    # 0.0
            g = black_color.green() / 255.0  # 0.0  
            b = black_color.blue() / 255.0   # 0.0
            
            # Set background colors using the working method
            viewNode.SetBackgroundColor(r, g, b)
            viewNode.SetBackgroundColor2(r, g, b)  # Also set gradient background
    except Exception as e:
        logger.debug("Suppressed exception in set_3d_view_background_black", exc_info=True)

def create_continue_workflow_button():
    """
    Create a continue button and add it to the Crop Volume module GUI
    """
    try:
        # Get the crop volume module widget
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if not crop_widget:
            create_floating_continue_button()
            return
        
        # Create continue button
        continue_button = qt.QPushButton("FINISH SEGMENTATION - CONTINUE")
        continue_button.setStyleSheet("""
            QPushButton { 
                background-color: #28a745; 
                color: white; 
                border: 2px solid #1e7e34; 
                padding: 18px; 
                font-weight: bold;
                border-radius: 8px;
                margin: 5px;
                font-size: 16px;
                min-height: 60px;
                min-width: 300px;
            }
            QPushButton:hover { 
                background-color: #218838; 
                border: 2px solid #155724;
                transform: scale(1.02);
            }
            QPushButton:pressed { 
                background-color: #1e7e34; 
                border: 2px solid #0f4c2c;
            }
        """)
        
        # Connect to continue function
        continue_button.connect('clicked()', lambda: segmentation.on_continue_from_scissors())
        
        # Add status label
        status_label = qt.QLabel("Segmentation tools active. Use scissors button to edit segments.")
        status_label.setWordWrap(True)
        status_label.setStyleSheet("color: #333; font-size: 14px; padding: 10px; font-weight: bold;")
        
        # Create container for continue workflow elements
        continue_container = qt.QWidget()
        continue_layout = qt.QVBoxLayout(continue_container)
        continue_layout.addWidget(status_label)
        continue_layout.addWidget(continue_button)
        
        # Try to add to the crop module GUI
        success = add_continue_button_to_crop_module(crop_widget, continue_container)
        
        if success:
            # Store references
            slicer.modules.WorkflowContinueButton = continue_button
            slicer.modules.WorkflowContinueWidget = continue_container
            pass
        else:
            # Fallback to floating widget
            pass
            create_floating_continue_button()
        
    except Exception as e:
        pass
        # Fallback to floating widget
        create_floating_continue_button()

def create_floating_continue_button():
    """
    Create a floating continue button as fallback
    """
    try:
        # Create continue button
        continue_button = qt.QPushButton("FINISH SEGMENTATION - CONTINUE")
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
        
        # Connect to continue function
        continue_button.connect('clicked()', lambda: segmentation.on_continue_from_scissors())
        
        # Create floating widget for continue button
        continue_widget = qt.QWidget()
        continue_widget.setWindowTitle("Workflow Progress")
        continue_widget.setWindowFlags(qt.Qt.WindowStaysOnTopHint | qt.Qt.Tool)
        
        # Set layout
        layout = qt.QVBoxLayout()
        
        # Add status label
        status_label = qt.QLabel("Segmentation tools active. Use scissors button to edit segments.")
        status_label.setWordWrap(True)
        status_label.setStyleSheet("color: #333; font-size: 14px; padding: 10px;")
        layout.addWidget(status_label)
        
        layout.addWidget(continue_button)
        continue_widget.setLayout(layout)
        continue_widget.resize(350, 150)
        
        # Position in bottom-right corner
        main_window = slicer.util.mainWindow()
        if main_window:
            main_geometry = main_window.geometry()
            continue_widget.move(main_geometry.right() - 370, main_geometry.bottom() - 200)
        
        continue_widget.show()
        
        # Store references
        slicer.modules.WorkflowContinueButton = continue_button
        slicer.modules.WorkflowContinueWidget = continue_widget
        
        pass
        
    except Exception as e:
        logger.debug("Suppressed exception in create_floating_continue_button", exc_info=True)

def add_continue_button_to_crop_module(crop_widget, continue_container):
    """
    DISABLED: Do not add any buttons to the Crop Volume module GUI.
    All functionality is handled by the custom crop interface.
    """
    # Return immediately - no buttons should be added to crop module
    return False

def collapse_crop_volume_gui():
    """
    Completely collapse/hide the Crop Volume module GUI when cropping is finished
    """
    try:
        pass
        
        # First try to hide all UI elements
        hide_crop_volume_ui_elements()
        
        # Additionally, try to collapse the entire module widget
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if crop_widget:
            # Try to find and collapse the main collapsible sections
            all_collapsible_buttons = crop_widget.findChildren("ctkCollapsibleButton")
            collapsed_count = 0
            
            for button in all_collapsible_buttons:
                try:
                    if hasattr(button, 'setCollapsed'):
                        button.setCollapsed(True)
                        collapsed_count += 1
                    elif hasattr(button, 'collapsed') and hasattr(button, 'setProperty'):
                        button.setProperty('collapsed', True)
                        collapsed_count += 1
                except Exception as e:
                    continue
            
            # Also try to minimize the main widget if possible
            try:
                if hasattr(crop_widget, 'setVisible'):
                    # Don't make completely invisible, but minimize visibility
                    crop_widget.setMaximumHeight(50)  # Minimize height
                    pass
            except Exception as e:
                logger.debug("Suppressed exception in collapse_crop_volume_gui", exc_info=True)
            
            pass
            
        # Force GUI update
        slicer.app.processEvents()
        
        pass
        
    except Exception as e:
        logger.debug("Suppressed exception in collapse_crop_volume_gui", exc_info=True)

def cleanup_continue_ui():
    """
    Clean up continue button UI elements
    """
    try:
        # Clean up old segment editor button if it exists
        if hasattr(slicer.modules, 'SegmentEditorContinueButton'):
            button = slicer.modules.SegmentEditorContinueButton
            if button.parent():
                button.parent().layout().removeWidget(button)
            button.setParent(None)
            del slicer.modules.SegmentEditorContinueButton
            pass
        
        # Clean up old dialog if it exists
        if hasattr(slicer.modules, 'SegmentEditorContinueDialog'):
            dialog = slicer.modules.SegmentEditorContinueDialog
            dialog.close()
            dialog.setParent(None)
            del slicer.modules.SegmentEditorContinueDialog
            pass
        
        # Clean up new workflow continue button
        if hasattr(slicer.modules, 'WorkflowContinueButton'):
            button = slicer.modules.WorkflowContinueButton
            button.setParent(None)
            del slicer.modules.WorkflowContinueButton
        
        # Clean up new workflow continue widget
        if hasattr(slicer.modules, 'WorkflowContinueWidget'):
            widget = slicer.modules.WorkflowContinueWidget
            widget.close()
            widget.setParent(None)
            del slicer.modules.WorkflowContinueWidget
            pass
            
        # Also clean up scissors tool UI
        segmentation.cleanup_scissors_tool_ui()
            
    except Exception as e:
        pass
        pass

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
            pass
        if hasattr(slicer.modules, 'WorkflowDialog'):
            dialog = slicer.modules.WorkflowDialog
            dialog.close()
            dialog.setParent(None)
            del slicer.modules.WorkflowDialog
            pass
        markup.cleanup_point_placement_ui()
        centerline.cleanup_centerline_ui()
            
    except Exception as e:
        logger.debug("Suppressed exception in cleanup_workflow_ui", exc_info=True)

def add_large_crop_apply_button():
    """
    DISABLED: Do not add any buttons to the Crop Volume module GUI.
    All cropping functionality is handled by the custom crop interface.
    """
    # Return immediately - no buttons should be added to crop module
    return True

def collapse_parameters_tab():
    """
    Remove the Parameters section in the Cross-Section Analysis module after Apply has been clicked
    """
    try:
        # Find the Cross-Section Analysis module widget
        module_manager = slicer.app.moduleManager()
        module = module_manager.module('CrossSectionAnalysis')
        if not module:
            return False
            
        module_widget = module.widgetRepresentation()
        if not module_widget:
            return False
        
        # Look for collapsible buttons or group boxes that might contain "Parameters"
        try:
            import ctk
            collapsible_buttons = module_widget.findChildren(ctk.ctkCollapsibleButton)
            for cb in collapsible_buttons:
                button_text = cb.text if hasattr(cb, 'text') else ""
                if "parameter" in button_text.lower():
                    # Fully hide/remove the parameters section instead of just collapsing
                    cb.setVisible(False)
                    cb.hide()
                    return True
        except Exception as ctk_error:
            logger.debug("Suppressed exception in collapse_parameters_tab", exc_info=True)
        
        # Also try QGroupBox as fallback
        group_boxes = module_widget.findChildren(qt.QGroupBox)
        for gb in group_boxes:
            box_title = gb.title if hasattr(gb, 'title') else ""
            if "parameter" in box_title.lower():
                # Completely hide the parameters section
                gb.setVisible(False)
                gb.hide()
                return True
        
        # Try finding any widget with "parameter" in the name or text
        all_widgets = module_widget.findChildren(qt.QWidget)
        for widget in all_widgets:
            # Check object name
            if hasattr(widget, 'objectName') and widget.objectName():
                if "parameter" in widget.objectName().lower():
                    # Fully hide the widget
                    widget.setVisible(False)
                    widget.hide()
                    return True
            
            # Check if it's a collapsible widget with parameter text
            if hasattr(widget, 'text') and widget.text:
                if "parameter" in widget.text().lower():
                    # Fully hide instead of just collapsing
                    widget.setVisible(False)
                    if hasattr(widget, 'hide'):
                        widget.hide()
                    return True
        
        return False
        
    except Exception as e:
        return False

def toggle_window_level_tool(activated, toggle_button):
    """
    Toggle the window level tool on/off in all slice views
    
    Args:
        activated (bool): True to activate window level tool, False to deactivate
        toggle_button: The button that called this function to update its text
    """
    try:
        # Get the interaction node
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if not interactionNode:
            return
        
        if activated:
            # Activate window level tool (adjust window/level)
            interactionNode.SetCurrentInteractionMode(interactionNode.AdjustWindowLevel)
            toggle_button.setText("Window Level (ON)")
            toggle_button.setChecked(True)
        else:
            # Deactivate window level tool (return to view transform)
            interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
            toggle_button.setText("Window Level")
            toggle_button.setChecked(False)
        
        # Force update of slice views
        slicer.app.processEvents()
        
    except Exception as e:
        slicer.util.errorDisplay(f"Could not toggle window level tool: {str(e)}")
        # Reset button state on error
        toggle_button.setText("Window Level")
        toggle_button.setChecked(False)

def show_saved_scene_locations():
    """
    Display all saved scene locations from the user's home directory.
    Console function to view the history of saved scenes.
    """
    try:
        import os
        
        # Get user home directory
        home_dir = os.path.expanduser("~")
        location_file = os.path.join(home_dir, "slicer_scene_locations.txt")
        
        if not os.path.exists(location_file):
            logger.warning("No saved scene locations found.")
            logger.info(f"Location file would be: {location_file}")
            return
        
        logger.info(f"Saved scene locations from: {location_file}")
        logger.info("=" * 60)
        
        with open(location_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        if not lines:
            logger.info("No scene locations recorded yet.")
        else:
            for i, line in enumerate(lines, 1):
                logger.info(f"{i:2d}. {line.strip()}")
                
        logger.info("=" * 60)
        logger.info(f"Total scenes recorded: {len(lines)}")
        
    except Exception as e:
        logger.error(f"Could not read scene locations: {str(e)}")

def show_pre_save_info():
    """
    Show information about what will be saved before opening the save dialog.
    """
    try:
        # Count all the saveable nodes in the scene
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        segmentation_nodes = slicer.util.getNodesByClass('vtkMRMLSegmentationNode')
        markup_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsNode')
        model_nodes = slicer.util.getNodesByClass('vtkMRMLModelNode')
        transform_nodes = slicer.util.getNodesByClass('vtkMRMLTransformNode')
        
        # Build the info message
        info_parts = []
        
        if volume_nodes:
            info_parts.append(f"• {len(volume_nodes)} Volume(s)")
            working_volume = volume.find_working_volume()
            for vol in volume_nodes:
                if vol == working_volume:
                    info_parts.append(f"  - {vol.GetName()} → will be saved as CT_Series.nrrd")
                else:
                    info_parts.append(f"  - {vol.GetName()}")
        
        if segmentation_nodes:
            info_parts.append(f"• {len(segmentation_nodes)} Segmentation(s)")
            for seg in segmentation_nodes:
                info_parts.append(f"  - {seg.GetName()}")
        
        if markup_nodes:
            info_parts.append(f"• {len(markup_nodes)} Markup(s)")
            for markup in markup_nodes:
                info_parts.append(f"  - {markup.GetName()}")
        
        if model_nodes:
            info_parts.append(f"• {len(model_nodes)} Model(s)")
            for model in model_nodes:
                info_parts.append(f"  - {model.GetName()}")
        
        if transform_nodes:
            info_parts.append(f"• {len(transform_nodes)} Transform(s)")
            for transform in transform_nodes:
                info_parts.append(f"  - {transform.GetName()}")
        
        if info_parts:
            info_message = "The save dialog will open with ALL scene data selected for saving:\n\n" + "\n".join(info_parts)
            info_message += "\n\nAll files will be saved to the same directory for easy organization."
            logger.info("=== SAVE INFORMATION ===")
            logger.info(info_message)
            logger.info("========================")
        
    except Exception as e:
        logger.error(f"Could not show pre-save info: {str(e)}")

def open_save_dialog_with_all_selected():
    """
    Open the save dialog and attempt to automatically select all items.
    """
    try:
        # Method 1: Try using the IO manager with modification
        io_manager = slicer.app.ioManager()
        
        # Create a QTimer to select all items after the dialog opens
        def select_all_after_delay():
            try:
                # Find the save dialog window
                for widget in qt.QApplication.allWidgets():
                    if hasattr(widget, 'selectAll') and widget.windowTitle() and 'save' in widget.windowTitle().lower():
                        logger.info("Found save dialog, attempting to select all items...")
                        widget.selectAll()
                        break
                    # Also try to find qSlicerSaveDataDialog specifically
                    elif widget.__class__.__name__ == 'qSlicerSaveDataDialog':
                        logger.info("Found qSlicerSaveDataDialog, attempting to select all items...")
                        if hasattr(widget, 'selectAll'):
                            widget.selectAll()
                        break
            except Exception as select_error:
                logger.error(f"Could not auto-select all items in save dialog: {str(select_error)}")
        
        # Schedule the selection after a short delay to allow dialog to fully open
        timer = qt.QTimer()
        timer.timeout.connect(select_all_after_delay)
        timer.setSingleShot(True)
        timer.start(500)  # 500ms delay
        
        # Open the standard save dialog
        success = io_manager.openSaveDataDialog()
        
        # Clean up the timer
        timer.timeout.disconnect()
        return success
        
    except Exception as e:
        logger.error(f"Error opening save dialog with auto-select: {str(e)}")
        # Fallback to standard dialog
        try:
            return slicer.app.ioManager().openSaveDataDialog()
        except:
            return False

def cleanup_all_workflow_ui():
    """
    Clean up all workflow UI elements before continuing to workflow2
    """
    try:
        markup.cleanup_point_placement_ui()
        cleanup_workflow_ui()
        cleanup_continue_ui()
        centerline.cleanup_centerline_monitoring_button()
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
        
        pass
        
    except Exception as e:
        logger.debug("Suppressed exception in cleanup_all_workflow_ui", exc_info=True)

def restore_original_layout():
    """
    Restore the original layout that was active before centerline editing
    """
    try:
        if hasattr(slicer.modules, 'CenterlineEditingOriginalLayout'):
            layout_manager = slicer.app.layoutManager()
            if layout_manager:
                original_layout = slicer.modules.CenterlineEditingOriginalLayout
                layout_manager.setLayout(original_layout)
            
            # Clean up the stored layout
            delattr(slicer.modules, 'CenterlineEditingOriginalLayout')
            
    except Exception as e:
        logger.debug("Suppressed exception in restore_original_layout", exc_info=True)

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
        
        # Clear the dialog shown flag for new extraction cycle
        if hasattr(slicer.modules, 'CenterlineDialogShown'):
            del slicer.modules.CenterlineDialogShown
            pass
        
        # Get baseline counts before user starts
        current_models = centerline.find_all_centerline_models()
        current_curves = centerline.find_all_centerline_curves()
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
        
        
    except Exception as e:
        logger.debug("Suppressed exception in setup_apply_button_monitoring", exc_info=True)

def check_for_apply_button_click():
    """
    Check if Apply button has been clicked by monitoring for new centerline activity
    """
    try:
        # Increment check count and add timeout
        if hasattr(slicer.modules, 'ApplyMonitorCheckCount'):
            slicer.modules.ApplyMonitorCheckCount += 1
            
        # Get current centerlines
        current_models = centerline.find_all_centerline_models()
        current_curves = centerline.find_all_centerline_curves()
        
        # Check for truly new centerlines (not just count changes)
        existing_model_ids = getattr(slicer.modules, 'ExistingModelIDs', [])
        existing_curve_ids = getattr(slicer.modules, 'ExistingCurveIDs', [])
        
        new_models = [model for model in current_models if model.GetID() not in existing_model_ids]
        new_curves = [curve for curve in current_curves if curve.GetID() not in existing_curve_ids]
        
        # If we have truly new centerlines, Apply was clicked and processing started/completed
        if new_models or new_curves:
            # Check if dialog has already been shown for this extraction cycle
            if hasattr(slicer.modules, 'CenterlineDialogShown') and slicer.modules.CenterlineDialogShown:
                pass
                return  # Exit early to prevent duplicate dialogs
            
            # Stop Apply button monitoring
            stop_apply_button_monitoring()
            
            # Check if any of the new centerlines have sufficient data
            best_model = None
            best_curve = None
            
            # Find the best new model (one with most points)
            for model in new_models:
                polydata = model.GetPolyData()
                if polydata and polydata.GetNumberOfPoints() > 10:  # Require at least 10 points
                    if not best_model or polydata.GetNumberOfPoints() > best_model.GetPolyData().GetNumberOfPoints():
                        best_model = model
            
            # Find the best new curve (one with most control points)
            for curve in new_curves:
                if curve.GetNumberOfControlPoints() > 5:  # Require at least 5 control points
                    if not best_curve or curve.GetNumberOfControlPoints() > best_curve.GetNumberOfControlPoints():
                        best_curve = curve
            
            # If we have sufficient data, show dialog immediately
            if best_model or best_curve:
                # Stop ALL monitoring to prevent duplicate dialogs
                centerline.stop_all_centerline_monitoring()
                
                # Mark that we're showing a dialog for this extraction cycle BEFORE showing dialog
                slicer.modules.CenterlineDialogShown = True
                
                centerline.show_centerline_completion_dialog(best_model, best_curve)
                return
            else:
                # No sufficient data yet, but don't set up additional monitoring
                # Let the timer continue to check for data completion
                return
        
        # Alternative detection: Look for recently modified nodes (processing activity)
        for model in current_models:
            if model.GetID() in existing_model_ids:
                # Check if this existing model was recently modified (processing activity)
                import time
                current_time = time.time() * 1000  # Convert to milliseconds
                time_since_modified = current_time - model.GetMTime()
                if time_since_modified < 5000:  # Modified within last 5 seconds
                    pass
                    # Just continue with existing monitoring, don't start new ones
                    return
        
    except Exception as e:
        logger.debug("Suppressed exception in check_for_apply_button_click", exc_info=True)

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
            
        pass
        
    except Exception as e:
        logger.debug("Suppressed exception in stop_apply_button_monitoring", exc_info=True)

def hide_crop_volume_ui_elements():
    """
    Hide ALL UI elements in the Crop Volume module - remove everything from the interface
    """
    try:
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if not crop_widget:
            return False
        
        elements_hidden = 0

        try:
            collapsible_buttons = crop_widget.findChildren("ctkCollapsibleButton")
            for button in collapsible_buttons:
                button.setVisible(False)
                elements_hidden += 1
        except Exception:
            logger.debug("Suppressed exception in hide_crop_volume_ui_elements", exc_info=True)
        try:
            push_buttons = crop_widget.findChildren(qt.QPushButton)
            for button in push_buttons:
                button.setVisible(False)
                elements_hidden += 1
        except Exception:
            logger.debug("Suppressed exception in hide_crop_volume_ui_elements", exc_info=True)
        try:
            labels = crop_widget.findChildren(qt.QLabel)
            for label in labels:
                label.setVisible(False)
                elements_hidden += 1
        except Exception:
            logger.debug("Suppressed exception in hide_crop_volume_ui_elements", exc_info=True)

        try:
            input_widgets = crop_widget.findChildren(qt.QLineEdit)
            input_widgets.extend(crop_widget.findChildren(qt.QSpinBox))
            input_widgets.extend(crop_widget.findChildren(qt.QDoubleSpinBox))
            input_widgets.extend(crop_widget.findChildren(qt.QComboBox))
            input_widgets.extend(crop_widget.findChildren(qt.QCheckBox))
            for widget in input_widgets:
                widget.setVisible(False)
                elements_hidden += 1
        except Exception:
            logger.debug("Suppressed exception in hide_crop_volume_ui_elements", exc_info=True)

        try:
            layouts = crop_widget.findChildren(qt.QHBoxLayout)
            layouts.extend(crop_widget.findChildren(qt.QVBoxLayout))
            layouts.extend(crop_widget.findChildren(qt.QGridLayout))
            for layout in layouts:
                parent_widget = layout.parent()
                if parent_widget and parent_widget != crop_widget:
                    parent_widget.setVisible(False)
                    elements_hidden += 1
        except Exception:
            logger.debug("Suppressed exception in hide_crop_volume_ui_elements", exc_info=True)

        try:
            all_children = crop_widget.findChildren(qt.QWidget)
            for child in all_children:
                if child.isVisible() and child != crop_widget:
                    child.setVisible(False)
                    elements_hidden += 1
        except Exception:
            logger.debug("Suppressed exception in hide_crop_volume_ui_elements", exc_info=True)
        
        return True
        
    except Exception as e:
        pass
        return False

def restore_crop_ui():
    """Console helper to restore all hidden Crop Volume UI elements"""
    try:
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if not crop_widget:
            pass
            return False
        
        # Find all widgets and make them visible
        all_widgets = crop_widget.findChildren(qt.QWidget)
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

def show_keyboard_undo_help():
    """
    Show help information for using keyboard undo functionality
    """
    try:
        logger.info("\n" + "="*60)
        logger.info("           KEYBOARD UNDO FUNCTIONALITY HELP")
        logger.info("="*60)
        logger.info("The workflow now supports Ctrl+Z for undo functionality!")
        logger.info()
        logger.info("HOW TO USE:")
        logger.info("1. Use the scissors tool to make segmentation changes")
        logger.info("2. Press Ctrl+Z to undo the last change")
        logger.info("3. Press Ctrl+Y to redo (if available)")
        logger.info()
        logger.info("TROUBLESHOOTING:")
        logger.info("If Ctrl+Z doesn't work, try these steps:")
        logger.info("• Call force_enable_keyboard_undo() to re-enable shortcuts")
        logger.info("• Make sure you click in a slice view first to give it focus")
        logger.info("• Ensure you've made at least one change before trying to undo")
        logger.info("• Try pressing Ctrl+Z while mouse is over a slice view")
        logger.info()
        logger.info("TESTING FUNCTIONS:")
        logger.info("• test_keyboard_undo_functionality() - Run diagnostics")
        logger.info("• force_enable_keyboard_undo() - Re-enable if not working")
        logger.info("• handle_keyboard_undo() - Manually trigger undo")
        logger.info()
        logger.warning("The system uses multiple fallback methods:")
        logger.info("1. Segment editor built-in undo (preferred)")
        logger.warning("2. Scene-based undo system (fallback)")
        logger.info("3. Both global and widget-specific shortcuts")
        logger.info("="*60 + "\n")
        
    except Exception as e:
        logger.error(f"Error showing help: {e}")

def add_buttons_to_crop_module(crop_widget, scissors_button, finish_button):
    """
    Add scissors and finish buttons to the Crop Volume module GUI
    """
    try:
        # First, remove/hide the original large green "APPLY CROP" button
        remove_original_crop_apply_button(crop_widget)
        
        # Try to get the crop module
        crop_module = None
        if hasattr(crop_widget, 'self'):
            try:
                crop_module = crop_widget.self()
            except Exception:
                logger.debug("Suppressed exception in add_buttons_to_crop_module", exc_info=True)
        
        if not crop_module:
            crop_module = crop_widget
        
        # Find the main UI container in the crop module
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
        
        # Create a container widget for our buttons
        button_container = qt.QWidget()
        button_layout = qt.QHBoxLayout(button_container)
        button_layout.addWidget(scissors_button)
        button_layout.addWidget(finish_button)
        
        # Add some instructions
        instructions = qt.QLabel("Workflow: Use scissors to edit segmentation, then finish cropping")
        instructions.setStyleSheet("color: #666; font-size: 12px; padding: 5px; font-weight: bold;")
        instructions.setWordWrap(True)
        
        # Create final container with instructions and buttons
        final_container = qt.QWidget()
        final_layout = qt.QVBoxLayout(final_container)
        final_layout.addWidget(instructions)
        final_layout.addWidget(button_container)
        
        # Try to add to the GUI layout
        if main_ui_widget and hasattr(main_ui_widget, 'layout'):
            layout = main_ui_widget.layout()
            if layout:
                # Insert at the top of the module
                layout.insertWidget(0, final_container)
                pass
                return True
            else:
                # Try to create a new layout
                new_layout = qt.QVBoxLayout(main_ui_widget)
                new_layout.insertWidget(0, final_container)
                pass
                return True
        else:
            # Fallback: try to find a suitable container widget
            container_widgets = crop_widget.findChildren(qt.QWidget)
            for widget in container_widgets:
                if hasattr(widget, 'layout') and widget.layout() and widget.layout().count() > 0:
                    widget.layout().insertWidget(0, final_container)
                    pass
                    return True
        
        pass
        return False
        
    except Exception as e:
        pass
        return False

def ensure_crop_button_disabled_if_completed():
    """
    Ensure crop apply button remains disabled if crop has been completed
    """
    try:
        if hasattr(slicer.modules, 'WorkflowCropCompleted') and slicer.modules.WorkflowCropCompleted:
            crop_widget = slicer.modules.cropvolume.widgetRepresentation()
            if crop_widget:
                disable_crop_apply_button(crop_widget)
    except Exception as e:
        logger.debug("Suppressed exception in ensure_crop_button_disabled_if_completed", exc_info=True)

def disable_crop_apply_button(crop_widget):
    """
    Disable and grey out the crop apply button once it has been used
    """
    try:
        disabled_count = 0
        
        # Method 1: Disable the stored reference button
        if hasattr(slicer.modules, 'CropLargeApplyButton'):
            button = slicer.modules.CropLargeApplyButton
            if button and button.parent():
                # Disable the button
                button.setEnabled(False)
                
                # Change text to indicate completion
                button.setText("CROP APPLIED ✓")
                
                # Set grey styling
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #808080;
                        color: #FFFFFF;
                        border: 2px solid #606060;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;
                        padding: 10px 20px;
                        min-height: 40px;
                        min-width: 150px;
                    }
                """)
                
                disabled_count += 1
        
        # Method 2: Search for and disable any "APPLY CROP" buttons in the crop widget
        if crop_widget:
            all_buttons = crop_widget.findChildren(qt.QPushButton)
            for button in all_buttons:
                try:
                    button_text = button.text if hasattr(button, 'text') else ""
                    if button_text and ("APPLY CROP" in button_text or "Apply" in button_text):
                        # Disable the button
                        button.setEnabled(False)
                        
                        # Change text to indicate completion
                        if "APPLY CROP" in button_text:
                            button.setText("CROP APPLIED ✓")
                        else:
                            button.setText("APPLIED ✓")
                        
                        # Set grey styling
                        button.setStyleSheet("""
                            QPushButton {
                                background-color: #808080;
                                color: #FFFFFF;
                                border: 2px solid #606060;
                                border-radius: 8px;
                                font-size: 14px;
                                font-weight: bold;
                                padding: 8px 16px;
                                min-height: 30px;
                            }
                        """)
                        
                        disabled_count += 1
                except Exception as e:
                    continue
        
        return disabled_count > 0
        
    except Exception as e:
        return False

def remove_original_crop_apply_button(crop_widget):
    """
    Remove or hide the original large green "APPLY CROP" button from the Crop Volume module
    """
    try:
        removed_count = 0
        
        # Method 1: Remove the stored reference button
        if hasattr(slicer.modules, 'CropLargeApplyButton'):
            button = slicer.modules.CropLargeApplyButton
            if button and button.parent():
                # Remove from parent layout
                parent = button.parent()
                if hasattr(parent, 'layout') and parent.layout():
                    parent.layout().removeWidget(button)
                elif hasattr(parent, 'removeWidget'):
                    parent.removeWidget(button)
                
                # Hide and delete the button
                button.hide()
                button.setParent(None)
                
                # Remove the reference
                del slicer.modules.CropLargeApplyButton
                removed_count += 1
                pass
        
        # Method 2: Search for and remove any "APPLY CROP" buttons in the crop widget
        if crop_widget:
            all_buttons = crop_widget.findChildren(qt.QPushButton)
            for button in all_buttons:
                try:
                    button_text = button.text if hasattr(button, 'text') else ""
                    if button_text and "APPLY CROP" in button_text:
                        # Remove from parent layout
                        parent = button.parent()
                        if parent and hasattr(parent, 'layout') and parent.layout():
                            parent.layout().removeWidget(button)
                        elif parent and hasattr(parent, 'removeWidget'):
                            parent.removeWidget(button)
                        
                        # Hide and delete the button
                        button.hide()
                        button.setParent(None)
                        removed_count += 1
                        pass
                except Exception as e:
                    logger.debug("Suppressed exception in remove_original_crop_apply_button", exc_info=True)
        
        # Method 3: Also look for and hide any other large green buttons that might be apply buttons
        if crop_widget:
            all_buttons = crop_widget.findChildren(qt.QPushButton)
            for button in all_buttons:
                try:
                    button_text = button.text if hasattr(button, 'text') else ""
                    button_style = button.styleSheet() if hasattr(button, 'styleSheet') else ""
                    
                    # Check if it's a large green button (likely an apply button)
                    if (button_text and 
                        ("apply" in button_text.lower() or "crop" in button_text.lower()) and 
                        ("#28a745" in button_style or "background-color: #28a745" in button_style)):
                        
                        # Hide the button instead of removing it completely (safer)
                        button.hide()
                        removed_count += 1
                        pass
                except Exception as e:
                    logger.debug("Suppressed exception in remove_original_crop_apply_button", exc_info=True)
        
        if removed_count > 0:
            pass
        else:
            pass
        
        return removed_count > 0
        
    except Exception as e:
        pass
        return False

def restore_original_crop_apply_button():
    """
    Restore the original large green "APPLY CROP" button to the Crop Volume module
    """
    try:
        # Check if crop has been completed and ensure button stays disabled
        if hasattr(slicer.modules, 'WorkflowCropCompleted') and slicer.modules.WorkflowCropCompleted:
            ensure_crop_button_disabled_if_completed()
            return
            
        # Check if we're still in the Crop Volume module
        current_module = slicer.util.selectedModule()
        if current_module != "CropVolume":
            return
        if hasattr(slicer.modules, 'CropLargeApplyButton'):
            button = slicer.modules.CropLargeApplyButton
            if button and button.parent():
                # Only restore if not already disabled from completion
                if button.isEnabled() or not button.text().endswith("✓"):
                    button.show()
                return
    except Exception as e:
        logger.debug("Suppressed exception in restore_original_crop_apply_button", exc_info=True)

def show_restart_cropping_help():
    """
    Show help information about the restart cropping functionality.
    Usage: show_restart_cropping_help()
    """
    help_text = """
=== Restart Cropping with Centerline Preservation ===

This feature allows you to return to the volume cropping step while keeping 
your existing centerlines intact. This is useful when you need to:

• Adjust the crop region after seeing centerline results
• Re-crop the volume with different boundaries
• Fix cropping issues without losing centerline work

USAGE METHODS:

1. FROM CENTERLINE COMPLETION DIALOG:
   - Click the "🔄 Restart Cropping" button
   - Your centerlines will be automatically preserved

2. FROM CONSOLE:
   - test_restart_cropping_with_preservation()
   - This provides the same functionality as the dialog button

3. MANUAL STEPS (if needed):
   - store_existing_centerlines()
   - clear_workflow_for_cropping_restart()
   - restart_cropping_preserving_centerlines()

WHAT HAPPENS:
✅ Existing centerlines are preserved and remain visible
✅ Original volume is restored for re-cropping
✅ Crop ROI and segmentation data are cleared
✅ Workflow returns to cropping step
✅ You can adjust crop region and continue normally

WHAT'S PRESERVED:
• All centerline models and curves
• Centerline visibility settings
• Original volume data

WHAT'S CLEARED:
• Cropped volumes
• ROI nodes
• Segmentation nodes
• Endpoint markups

After restarting, simply crop your volume again and the workflow will continue
with both your existing centerlines and new cropped volume.
"""

def restore_all_crop_ui_elements():
    """
    Restore all UI elements in the Crop Volume module to their original visible state.
    This is more comprehensive than the existing restore_crop_ui function.
    """
    try:
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if not crop_widget:
            return False
        
        # Make all widgets visible
        all_widgets = crop_widget.findChildren(qt.QWidget)
        restored_count = 0
        
        for widget in all_widgets:
            if hasattr(widget, 'setVisible'):
                widget.setVisible(True)
                restored_count += 1
                
            # Reset any custom styling
            if hasattr(widget, 'setStyleSheet'):
                widget.setStyleSheet("")
        
        # Restore collapsible buttons to their default state
        collapsible_buttons = crop_widget.findChildren("ctkCollapsibleButton")
        for button in collapsible_buttons:
            button.setVisible(True)
            # Reset to collapsed state (default for most modules)
            if hasattr(button, 'setCollapsed'):
                button.setCollapsed(False)
        
        # Remove any custom layouts or buttons that were added
        remove_custom_crop_buttons()
        
        return True
        
    except Exception as e:
        return False

def remove_custom_crop_buttons():
    """
    Remove custom buttons that were added to the Crop Volume module during workflow.
    """
    try:
        crop_widget = slicer.modules.cropvolume.widgetRepresentation()
        if not crop_widget:
            return False
        
        buttons_removed = 0
        
        # Find and remove custom buttons by object name or text
        custom_button_names = [
            "WorkflowCropApplyButton",
            "WorkflowContinueButton",
            "ContinueWorkflowButton",
            "FinishCroppingButton",
            "ScissorsToolButton"
        ]
        
        for button_name in custom_button_names:
            custom_buttons = crop_widget.findChildren(qt.QPushButton, button_name)
            for button in custom_buttons:
                button.setParent(None)
                button.deleteLater()
                buttons_removed += 1
        
        # Also remove buttons by text content
        all_buttons = crop_widget.findChildren(qt.QPushButton)
        for button in all_buttons:
            button_text = button.text
            if any(keyword in button_text for keyword in [
                "Continue Workflow", 
                "Finish Cropping", 
                "Scissors Tool",
                "Large Apply"  # Our custom large green apply button
            ]):
                button.setParent(None)
                button.deleteLater()
                buttons_removed += 1
        
        # Remove custom layouts
        custom_layouts = crop_widget.findChildren(qt.QHBoxLayout, "WorkflowButtonLayout")
        for layout in custom_layouts:
            # Remove all widgets in the layout first
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
                    item.widget().deleteLater()
            # Remove the layout itself
            layout.setParent(None)
            layout.deleteLater()
            buttons_removed += 1
        
        
        return True
        
    except Exception as e:
        return False

def create_initial_custom_crop_interface():
    """
    Create the initial custom crop interface for the first crop operation.
    Uses dark color scheme and hides scissors tools until after cropping.
    """
    try:
        # Clean up any existing custom crop interface
        if hasattr(slicer.modules, 'CustomCropWidget'):
            existing_widget = slicer.modules.CustomCropWidget
            if existing_widget:
                existing_widget.close()
                existing_widget.deleteLater()
        
        # First, ensure ROI exists and is visible
        roi_node = volume.ensure_crop_roi_exists()

        
        # Switch to the same three-up view used in the workflow
        setup_crop_display_layout()
        
        # Create the custom crop widget as a fixed left-side module with dark theme
        crop_widget = qt.QWidget()
        crop_widget.setWindowTitle("Crop Tools")
        
        # Set up as a dockable widget on the left side with dark theme
        crop_widget.setWindowFlags(qt.Qt.Widget)
        crop_widget.setFixedWidth(280)
        crop_widget.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 2px solid #555555;
                border-radius: 8px;
                color: #ffffff;
            }
        """)
        
        # Position on the left side of the screen
        main_window = slicer.util.mainWindow()
        if main_window:
            screen_geometry = qt.QApplication.desktop().availableGeometry()
            crop_widget.setGeometry(10, 100, 280, 300)
            crop_widget.setWindowFlags(qt.Qt.WindowStaysOnTopHint | qt.Qt.FramelessWindowHint)
        
        # Set up layout
        layout = qt.QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Header with title and close button - dark theme
        header_layout = qt.QHBoxLayout()
        
        # Title
        title_label = qt.QLabel("Crop Tools")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)
        
        # Close button - dark theme
        close_button = qt.QPushButton("×")
        close_button.setStyleSheet("""
            QPushButton { 
                background-color: #e74c3c; 
                color: white; 
                border: none; 
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
            }
            QPushButton:hover { 
                background-color: #c0392b; 
            }
        """)
        close_button.connect('clicked()', lambda: cleanup_custom_crop_interface())
        header_layout.addWidget(close_button)
        
        # Add header to main layout
        header_widget = qt.QWidget()
        header_widget.setLayout(header_layout)
        header_widget.setStyleSheet("padding: 10px; background-color: #3a3a3a; border-radius: 6px; margin-bottom: 10px;")
        layout.addWidget(header_widget)

        # Crop button - dark theme
        crop_button = qt.QPushButton("CROP VOLUME")
        crop_button.setStyleSheet("""
            QPushButton { 
                background-color: #3498db; 
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
                background-color: #2980b9; 
            }
            QPushButton:pressed { 
                background-color: #21618c; 
            }
        """)
        
        # Connect crop button
        crop_button.connect('clicked()', lambda: volume.execute_initial_custom_crop())
        layout.addWidget(crop_button)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Set layout and show
        crop_widget.setLayout(layout)
        
        # Show the fixed left-side module
        crop_widget.show()
        crop_widget.raise_()
        crop_widget.activateWindow()
        
        # Store references
        slicer.modules.CustomCropWidget = crop_widget
        slicer.modules.CustomCropButton = crop_button
        
        # Check if crop has already been completed and disable button if so
        if hasattr(slicer.modules, 'WorkflowCroppedVolume') and slicer.modules.WorkflowCroppedVolume:
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
        
        return crop_widget
        
    except Exception as e:
        pass
        return None

def create_custom_crop_interface():
    """
    Create a clean custom interface for cropping when the crop module GUI becomes distorted.
    This creates a fixed left-side module with crop button and scissors controls.
    Automatically creates and shows the ROI for cropping.
    """
    try:
        # Clean up any existing custom crop interface
        if hasattr(slicer.modules, 'CustomCropWidget'):
            existing_widget = slicer.modules.CustomCropWidget
            if existing_widget:
                existing_widget.close()
                existing_widget.deleteLater()
        
        # First, ensure ROI exists and is visible
        roi_node = volume.ensure_crop_roi_exists()
        
        # Switch to the same three-up view used in the original workflow
        setup_crop_display_layout()
        
        # Create the custom crop widget as a fixed left-side module
        crop_widget = qt.QWidget()
        crop_widget.setWindowTitle("Crop Tools")
        
        # Set up as a dockable widget on the left side
        crop_widget.setWindowFlags(qt.Qt.Widget)
        crop_widget.setFixedWidth(280)
        crop_widget.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 2px solid #555555;
                border-radius: 8px;
                color: #ffffff;
            }
        """)
        
        # Position on the left side of the screen
        main_window = slicer.util.mainWindow()
        if main_window:
            screen_geometry = qt.QApplication.desktop().availableGeometry()
            crop_widget.setGeometry(10, 100, 280, 400)
            crop_widget.setWindowFlags(qt.Qt.WindowStaysOnTopHint | qt.Qt.FramelessWindowHint)
        
        # Set up layout
        layout = qt.QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Header with title and close button
        header_layout = qt.QHBoxLayout()
        
        # Title
        title_label = qt.QLabel("Crop Tools")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)
        
        # Close button
        close_button = qt.QPushButton("×")
        close_button.setStyleSheet("""
            QPushButton { 
                background-color: #e74c3c; 
                color: white; 
                border: none; 
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
            }
            QPushButton:hover { 
                background-color: #c0392b; 
            }
        """)
        close_button.connect('clicked()', lambda: cleanup_custom_crop_interface())
        header_layout.addWidget(close_button)
        
        # Add header to main layout
        header_widget = qt.QWidget()
        header_widget.setLayout(header_layout)
        header_widget.setStyleSheet("padding: 10px; background-color: #ecf0f1; border-radius: 6px; margin-bottom: 10px;")
        layout.addWidget(header_widget)
        

        
        # Crop button
        crop_button = qt.QPushButton("CROP VOLUME")
        crop_button.setStyleSheet("""
            QPushButton { 
                background-color: #3498db; 
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
                background-color: #2980b9; 
            }
            QPushButton:pressed { 
                background-color: #21618c; 
            }
        """)
        
        # Connect crop button
        crop_button.connect('clicked()', lambda: volume.execute_custom_crop())
        layout.addWidget(crop_button)
        
        # Add spacing
        layout.addSpacing(10)
        
        # Scissors toggle button
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
        scissors_button.connect('toggled(bool)', lambda checked: segmentation.toggle_scissors_tool_programmatic(checked))
        layout.addWidget(scissors_button)
        
        # Store button reference for external access
        slicer.modules.CustomScissorsButton = scissors_button
        
        # Add spacing
        layout.addSpacing(15)
        
        # Continue workflow button
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
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Set layout and show
        crop_widget.setLayout(layout)
        
        # Show the fixed left-side module
        crop_widget.show()
        crop_widget.raise_()
        crop_widget.activateWindow()
        
        # Store references
        slicer.modules.CustomCropWidget = crop_widget
        slicer.modules.CustomCropButton = crop_button
        slicer.modules.CustomScissorsButton = scissors_button
        slicer.modules.CustomContinueButton = continue_button
        
        # Check if crop has already been completed and disable button if so
        if hasattr(slicer.modules, 'WorkflowCroppedVolume') and slicer.modules.WorkflowCroppedVolume:
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
        
        
        return crop_widget
        
    except Exception as e:
        pass
        return None

def setup_crop_display_layout():
    """
    Set up the display layout for cropping - uses the same three-up view as the original workflow.
    This ensures consistent behavior between first and subsequent croppings.
    """
    try:
        success = set_three_up_view()
        if success:
            vol = volume.find_working_volume()
            if vol:
                set_volume_visible_in_slice_views(vol)
            
        else:
            lm = slicer.app.layoutManager()
            if lm:
                layout_node = lm.layoutLogic().GetLayoutNode()
                layout_node.SetViewArrangement(slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalView)
        return success
        
    except Exception as e:
        logger.error(f"Error in setup_crop_display_layout: {e}")
        return False

def cleanup_custom_crop_interface():
    """
    Clean up the custom crop interface widgets
    """
    try:

        if hasattr(slicer.modules, 'CustomCropWidget'):
            widget = slicer.modules.CustomCropWidget
            if widget:
                widget.close()
                widget.deleteLater()
            delattr(slicer.modules, 'CustomCropWidget')

        for attr_name in ['CustomCropButton', 'CustomScissorsButton', 'CustomContinueButton']:
            if hasattr(slicer.modules, attr_name):
                delattr(slicer.modules, attr_name)
    except Exception as e:
        logger.error(f"Error in cleanup_custom_crop_interface: {e}")

def force_custom_crop_interface():
    """
    Convenience function to directly force the custom crop interface.
    Can be called from console or when crop module GUI is definitely broken.
    
    Usage from Slicer console:
    exec(open(r'c:\\path\\to\\workflow_moduals.py').read())
    force_custom_crop_interface()
    """
    try:
        success = volume.use_custom_crop_instead_of_module()
        return success
        
    except Exception as e:
        logger.error(f"Error in force_custom_crop_interface: {e}")
        return False

def onSlicerAboutToQuit():
    """Called when Slicer is about to quit - runs before database closes"""
    logger.info("Slicer is about to quit - running cleanup...")
    try:
        core.deleteAllPatients()
        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
