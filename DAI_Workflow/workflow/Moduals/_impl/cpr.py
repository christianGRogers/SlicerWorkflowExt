from ._common import *  # noqa: F401,F403  (shared imports + logger)
from . import centerline, core, markup, segmentation, ui, volume  # sibling modules (cross-calls)

__all__ = [
    'hide_cpr_slice_size_controls',
    'import_straightened_volume',
    'add_large_cpr_apply_button',
    'setup_cross_section_analysis_module',
    'configure_cross_section_module',
    'configure_browse_cross_sections',
    'switch_to_cpr_module',
    'auto_apply_cpr',
    'setup_cpr_completion_monitor',
    'check_cpr_completion',
    'stop_cpr_monitoring',
    'setup_cpr_module',
    'on_continue_to_cpr',
    'on_continue_to_cpr_from_edit',
    'reset_cpr_module',
    'cleanup_cpr_custom_elements',
]

def hide_cpr_slice_size_controls():
    """
    Hide the slice size controls (label and coordinates widget) from the CPR module UI.
    This removes the slice size text boxes when CPR is opened.
    """
    try:
        
        # Get the CPR module widget
        cpr_widget = slicer.modules.curvedplanarreformat.widgetRepresentation()
        if not cpr_widget:
            return False
        
        # Try to get the CPR module instance
        cpr_module = None
        if hasattr(cpr_widget, 'self'):
            try:
                cpr_module = cpr_widget.self()
            except Exception as e:
                logger.debug("Suppressed exception in hide_cpr_slice_size_controls", exc_info=True)
        
        if not cpr_module:
            cpr_module = cpr_widget
        
        # Look for the slice size controls in the UI
        controls_hidden = False
        
        # Method 1: Try to access via ui attribute (most common pattern)
        if hasattr(cpr_module, 'ui'):
            ui = cpr_module.ui
            
            
            if hasattr(ui, 'label_3'):
                ui.label_3.setVisible(False)
                controls_hidden = True
            
            
            if hasattr(ui, 'sliceSizeCoordinatesWidget'):
                ui.sliceSizeCoordinatesWidget.setVisible(False)
                controls_hidden = True
        
        # Method 2: Search for controls by object name if direct access didn't work
        if not controls_hidden:
            # Find all QLabel widgets and look for the one with "Slice size:" text
            labels = cpr_widget.findChildren(qt.QLabel)
            for label in labels:
                if hasattr(label, 'text') and label.text() == "Slice size:":
                    label.setVisible(False)
                    controls_hidden = True
                    break
            
            # Find the coordinates widget by class name
            coord_widgets = cpr_widget.findChildren("qMRMLCoordinatesWidget")
            for widget in coord_widgets:
                # Check if this is likely the slice size widget by checking nearby labels
                parent = widget.parent()
                if parent:
                    # Look for siblings that might be the slice size label
                    siblings = parent.findChildren(qt.QLabel)
                    for sibling in siblings:
                        if hasattr(sibling, 'text') and sibling.text() == "Slice size:":
                            widget.setVisible(False)
                            controls_hidden = True
                            break
                    if controls_hidden:
                        break
        
        # Method 3: Alternative approach - hide by object name
        if not controls_hidden:
            slice_label = cpr_widget.findChild(qt.QLabel, "label_3")
            if slice_label:
                slice_label.setVisible(False)
                controls_hidden = True
            
            coord_widget = cpr_widget.findChild("qMRMLCoordinatesWidget", "sliceSizeCoordinatesWidget")
            if coord_widget:
                coord_widget.setVisible(False)
                controls_hidden = True
        
        if controls_hidden:
            return True
        else:
            return False
            
    except Exception as e:
        return False

def import_straightened_volume():
    """
    Let the user select and import a straightened volume file
    Returns the imported volume node or None if cancelled/failed
    """
    try:
        # Create file dialog for volume import
        file_dialog = qt.QFileDialog(slicer.util.mainWindow())
        file_dialog.setWindowTitle("Select Straightened Volume File")
        file_dialog.setFileMode(qt.QFileDialog.ExistingFile)
        file_dialog.setAcceptMode(qt.QFileDialog.AcceptOpen)
        
        # Set file filters for common volume formats
        file_dialog.setNameFilters([
            "All Volume Files (*.nrrd *.nii *.nii.gz *.mhd *.vtk)",
            "NRRD Files (*.nrrd)",
            "NIfTI Files (*.nii *.nii.gz)",
            "MetaImage Files (*.mhd)",
            "VTK Files (*.vtk)",
            "All Files (*.*)"
        ])
        
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                volume_file = selected_files[0]
                
                try:
                    # Get existing volume nodes count to find the new one
                    existing_volumes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
                    
                    # Load the volume file
                    volume_node = slicer.util.loadVolume(volume_file)
                    
                    if volume_node:
                        # Set a recognizable name
                        volume_node.SetName("StraightenedVolume")
                        
                        # Make the volume visible in all slice views
                        ui.set_volume_visible_in_slice_views(volume_node)
                        
                        slicer.util.infoDisplay(f"Successfully imported straightened volume: {volume_node.GetName()}")
                        return volume_node
                    else:
                        slicer.util.errorDisplay("Failed to load the selected volume file.")
                        return None
                        
                except Exception as e:
                    slicer.util.errorDisplay(f"Error loading volume file: {str(e)}")
                    return None
            
        return None
        
    except Exception as e:
        slicer.util.errorDisplay(f"Error in volume file selection: {str(e)}")
        return None

def add_large_cpr_apply_button():
    """
    Add a large green Apply button directly to the Curved Planar Reformat module GUI
    """
    centerline.hide_centerlines_from_views()
    hide_cpr_slice_size_controls()
    ui.show_red_green_views_only()

    try:
        if hasattr(slicer.modules, 'CPRLargeApplyButton'):
            existing_button = slicer.modules.CPRLargeApplyButton
            if existing_button and existing_button.parent():
                pass
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
                            logger.debug("Suppressed exception in create_large_button", exc_info=True)
                    
                    if not cpr_module:
                        try:
                            cpr_module = cpr_widget
                            pass
                        except Exception as e:
                            logger.debug("Suppressed exception in create_large_button", exc_info=True)

                    if not cpr_module:
                        try:
                            cpr_module = slicer.modules.curvedplanarreformat.createNewWidgetRepresentation()
                            pass
                        except Exception as e:
                            logger.debug("Suppressed exception in create_large_button", exc_info=True)
                    
                    if cpr_module:
                        pass
                        
                        original_apply_button = None
                        pass
                        
                        apply_button_attrs = ['applyButton', 'ApplyButton', 'applyCPRButton', 'cprApplyButton']

                        if hasattr(cpr_module, 'ui'):
                            for attr_name in apply_button_attrs:
                                if hasattr(cpr_module.ui, attr_name):
                                    original_apply_button = getattr(cpr_module.ui, attr_name)
                                    pass
                                    break
                        else:

                            for attr_name in apply_button_attrs:
                                if hasattr(cpr_module, attr_name):
                                    original_apply_button = getattr(cpr_module, attr_name)
                                    pass
                                    break
                        
                        if not original_apply_button:
                            pass
                            all_buttons = cpr_widget.findChildren(qt.QPushButton)
                            pass
                            for i, button in enumerate(all_buttons):
                                button_text = button.text if hasattr(button, 'text') else ""
                                pass
                                if button_text and 'apply' in button_text.lower():
                                    original_apply_button = button
                                    pass
                                    break
                        
                        if original_apply_button:
                            large_apply_button = qt.QPushButton("Apply Curved Planar Reformat")
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
                            
                            def apply_cpr_and_transform():
                                """
                                Apply CPR only - transform application moved to Cross-Section Analysis button
                                """
                                try:
                                    
                                    # Apply the original CPR
                                    original_apply_button.click()
                                    
                                    # Give time for CPR processing
                                    slicer.app.processEvents()
                                    import time
                                    time.sleep(1.0)

                                    slicer.app.processEvents()
                                    
                                except Exception as e:
                                    logger.debug("Suppressed exception in apply_cpr_and_transform", exc_info=True)
                            
                            large_apply_button.connect('clicked()', apply_cpr_and_transform)
                            
                            # Create Cross-Section Analysis button
                            cross_section_button = qt.QPushButton("OPEN CROSS-SECTION ANALYSIS")
                            cross_section_button.setStyleSheet("""
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
                                    min-width: 300px;
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
                            
                            def open_cross_section_analysis():
                                try:
                                    # Apply transform to centerline nodes before opening Cross-Section Analysis
                                    transform_result = centerline.apply_cpr_transform_to_centerlines()
                                    
                                    # Switch to Cross-Section Analysis module
                                    slicer.util.selectModule("CrossSectionAnalysis")
                                    
                                    # Configure the Cross-Section Analysis module
                                    setup_cross_section_analysis_module()
                                    
                                    pass
                                except Exception as e:
                                    # Try alternative module names if the first doesn't work
                                    try:
                                        slicer.util.selectModule("Cross-sectionanalysis")
                                        setup_cross_section_analysis_module()
                                        pass
                                    except Exception as e2:
                                        try:
                                            slicer.util.selectModule("CrossSection")
                                            setup_cross_section_analysis_module()
                                            pass
                                        except Exception as e3:
                                            logger.debug("Suppressed exception in open_cross_section_analysis", exc_info=True)

                            cross_section_button.connect('clicked()', open_cross_section_analysis)
                            
                        else:
                            pass
                            large_apply_button = qt.QPushButton("Apply Curved Planar Reformat")
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
                                    # Apply CPR using fallback method
                                    if hasattr(cpr_module, 'onApplyButton'):
                                        cpr_module.onApplyButton()
                                        pass
                                    elif hasattr(cpr_module, 'apply'):
                                        cpr_module.apply()
                                        pass
                                    else:
                                        pass
                                    
                                    # Give time for CPR processing
                                    slicer.app.processEvents()
                                    import time
                                    time.sleep(1.0)
                                    
                                    pass
                                    
                                except Exception as e:
                                    logger.debug("Suppressed exception in trigger_cpr_apply", exc_info=True)
                            
                            large_apply_button.connect('clicked()', trigger_cpr_apply)
                            
                            # Create Cross-Section Analysis button
                            cross_section_button = qt.QPushButton("OPEN CROSS-SECTION ANALYSIS")
                            cross_section_button.setStyleSheet("""
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
                                    min-width: 300px;
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
                            
                            def open_cross_section_analysis():
                                try:
                                    # Apply transform to centerline nodes before opening Cross-Section Analysis
                                    transform_result = centerline.apply_cpr_transform_to_centerlines()                                    
                                    # Switch to Cross-Section Analysis module
                                    slicer.util.selectModule("CrossSectionAnalysis")
                                    
                                    # Configure the Cross-Section Analysis module
                                    setup_cross_section_analysis_module()
                                    
                                    pass
                                except Exception as e:
                                    try:
                                        slicer.util.selectModule("Cross-sectionanalysis")
                                        setup_cross_section_analysis_module()
                                        pass
                                    except Exception as e2:
                                        
                                        try:
                                            slicer.util.selectModule("CrossSection")
                                            setup_cross_section_analysis_module()
                                            pass
                                        except Exception as e3:
                                            logger.debug("Suppressed exception in open_cross_section_analysis", exc_info=True)

                            cross_section_button.connect('clicked()', open_cross_section_analysis)
                        
                        main_ui_widget = None
                        
                        if hasattr(cpr_module, 'ui') and hasattr(cpr_module.ui, 'widget'):
                            main_ui_widget = cpr_module.ui.widget
                        elif hasattr(cpr_module, 'widget'):
                            main_ui_widget = cpr_module.widget
                        elif hasattr(cpr_widget, 'widget'):
                            main_ui_widget = cpr_widget.widget
                        
                        if not main_ui_widget:
                            main_ui_widget = cpr_widget

                        # Create a container widget for both buttons
                        button_container = qt.QWidget()
                        button_layout = qt.QVBoxLayout(button_container)
                        button_layout.addWidget(large_apply_button)
                        button_layout.addWidget(cross_section_button)

                        if main_ui_widget and hasattr(main_ui_widget, 'layout'):
                            layout = main_ui_widget.layout()
                            if layout:
                                layout.insertWidget(0, button_container)
                            else:
                                new_layout = qt.QVBoxLayout(main_ui_widget)
                                new_layout.insertWidget(0, button_container)
                        else:
                            container_widgets = cpr_widget.findChildren(qt.QWidget)
                            for widget in container_widgets:
                                if hasattr(widget, 'layout') and widget.layout() and widget.layout().count() > 0:
                                    widget.layout().insertWidget(0, button_container)
                                    break
                            else:
                                return False
                        
                        slicer.modules.CPRLargeApplyButton = large_apply_button
                        slicer.modules.CPRCrossSectionButton = cross_section_button
                        return True
                    else:
                        if cpr_widget:
                            try:
                                attrs = [attr for attr in dir(cpr_widget) if not attr.startswith('_')]
                                pass
                            except:
                                logger.debug("Suppressed exception in create_large_button", exc_info=True)
                        return False
                        
            except Exception as e:
                pass
                return False
        
        success = create_large_button()
        
        if not success:
            qt.QTimer.singleShot(1000, create_large_button)
            qt.QTimer.singleShot(3000, create_large_button)
            
    except Exception as e:
        logger.debug("Suppressed exception in add_large_cpr_apply_button", exc_info=True)

def setup_cross_section_analysis_module():
    """
    Automatically configure the Cross-Section Analysis module after it opens.
    This function:
    1. Selects the centerline curve (everything else default)
    2. Clicks Apply
    3. Configures browse cross sections: Axial: Red, Long: Green, Point Index: half of total
    """
    try:
        
        # Give the module a moment to fully load
        qt.QTimer.singleShot(500, lambda: configure_cross_section_module())
        
    except Exception as e:
        return False

def configure_cross_section_module():
    """Helper function to configure the Cross-Section Analysis module"""
    try:
        
        # Find the Cross-Section Analysis module widget
        module_widget = None
        try:
            # Try to get the module widget directly
            module_manager = slicer.app.moduleManager()
            module = module_manager.module('CrossSectionAnalysis')
            if module:
                module_widget = module.widgetRepresentation()
        except:
            return False
        
        if not module_widget:
            return False
        
        try:
            # Look for parameter set selector (might be a combo box with parameter set options)
            combo_boxes = module_widget.findChildren(qt.QComboBox)
            parameter_set_selector = None
            
            for i, combo in enumerate(combo_boxes):
                # Look for combo box that might contain parameter sets
                for j in range(combo.count()):
                    item_text = combo.itemText(j)
                    if item_text and ('parameter' in item_text.lower() or 'default' in item_text.lower() or 'standard' in item_text.lower()):
                        parameter_set_selector = combo
                        break
                if parameter_set_selector:
                    break
            
            # If we found a parameter set selector, set it to a reasonable default
            if parameter_set_selector:
                # Try to find and select a default or standard parameter set
                for j in range(parameter_set_selector.count()):
                    item_text = parameter_set_selector.itemText(j)
                    if item_text and ('default' in item_text.lower() or 'standard' in item_text.lower() or j == 0):
                        parameter_set_selector.setCurrentIndex(j)
                        break
                
                # Give UI time to update after parameter set selection
                slicer.app.processEvents()
                time.sleep(0.2)
                
        except Exception as e:
            logger.debug("Suppressed exception in configure_cross_section_module", exc_info=True)

        try:
            # Look for the input curve selector (first qMRMLNodeComboBox)
            curve_selectors = module_widget.findChildren(slicer.qMRMLNodeComboBox)
            if curve_selectors:
                
                # Find centerline curve node first
                centerline_curve = None
                try:
                    centerline_curve = slicer.util.getNode("CenterlineCurve (0)")
                except:
                    # Try to find any curve node with "Centerline" in the name
                    curve_nodes = slicer.util.getNodesByClass('vtkMRMLMarkupsCurveNode')
                    for curve_node in curve_nodes:
                        if "Centerline" in curve_node.GetName():
                            centerline_curve = curve_node
                            break
                
                if not centerline_curve:
                    return False
                
                # Try to find the correct input selector by looking for one that accepts curves
                input_curve_selector = None
                for i, selector in enumerate(curve_selectors):
                    try:
                        # Check if this selector accepts the type of node we have
                        if hasattr(selector, 'nodeTypes'):
                            node_types = selector.nodeTypes  # Fixed: removed () - it's a property not method
                            if node_types and any('Curve' in node_type or 'Markup' in node_type for node_type in node_types):
                                input_curve_selector = selector
                                break
                        else:
                            # If we can't check types, try the first one
                            if i == 0:
                                input_curve_selector = selector
                    except Exception as e:
                        continue
                
                if not input_curve_selector:
                    # Fallback to first selector
                    input_curve_selector = curve_selectors[0]
                
                # Set the centerline curve
                try:
                    input_curve_selector.setCurrentNode(centerline_curve)
                    
                    # Give the UI more time to update and enable the Apply button
                    slicer.app.processEvents()
                    qt.QApplication.instance().processEvents()
                    
                    # Additional wait to ensure module processes the selection
                    import time
                    time.sleep(0.5)
                    slicer.app.processEvents()
                    
                except Exception as e:
                    
                    return False
                    
        
        except Exception as e:
            return False
        
        # Step 2: Click Apply button

        try:
            # Give the module a moment to update after setting the curve
            slicer.app.processEvents()
            qt.QApplication.instance().processEvents()
            
            # Look for Apply button with more flexible search
            apply_buttons = module_widget.findChildren(qt.QPushButton)
            apply_button = None
            

            
            for i, button in enumerate(apply_buttons):
                button_text = button.text if hasattr(button, 'text') else ""
                
                if button_text and 'apply' in button_text.lower():
                    apply_button = button

                    break
            
            if not apply_button:
                for i, button in enumerate(apply_buttons):
                    button_text = button.text if hasattr(button, 'text') else ""
                    if (button_text and 
                        (button_text.lower() in ['apply', 'run', 'execute', 'start', 'compute'] or
                         'apply' in button_text.lower() or
                         'run' in button_text.lower())):
                        apply_button = button
                        break
            
            if apply_button:
                if apply_button.enabled:
                    apply_button.click()
                    slicer.app.processEvents()
                    qt.QApplication.instance().processEvents()
                    try:
                        # Try to get the module logic to check if Apply succeeded
                        module_manager = slicer.app.moduleManager()
                        module = module_manager.module('CrossSectionAnalysis')
                        if module and hasattr(module, 'logic'):
                            module_logic = module.logic()
                    except Exception as logic_error:
                        logger.debug("Suppressed exception in configure_cross_section_module", exc_info=True)
                    
                    # Wait for processing to complete
                    qt.QTimer.singleShot(2000, lambda: configure_browse_cross_sections())
                    
                    # Collapse the Parameters tab after Apply has been clicked
                    qt.QTimer.singleShot(1000, lambda: ui.collapse_parameters_tab())
                    return True             
        except Exception as e:
            return False
            
    except Exception as e:
        return False

def configure_browse_cross_sections():
    """Configure the browse cross sections settings"""
    try:
        module_manager = slicer.app.moduleManager()
        module = module_manager.module('CrossSectionAnalysis')
        if not module:
            return False
            
        module_widget = module.widgetRepresentation()
        if not module_widget:
            return False
        
        # Look for the browse cross sections area (likely a collapsible button or group box)
        browse_widgets = []
        
        # Try to find collapsible buttons or group boxes
        # Import ctk module for collapsible button access
        try:
            import ctk
            collapsible_buttons = module_widget.findChildren(ctk.ctkCollapsibleButton)
            for cb in collapsible_buttons:
                if "browse" in cb.text.lower() or "cross" in cb.text.lower():
                    browse_widgets.append(cb)
        except Exception as e:
            logger.debug("Suppressed exception in configure_browse_cross_sections", exc_info=True)

        group_boxes = module_widget.findChildren(qt.QGroupBox)
        for gb in group_boxes:
            if "browse" in gb.title.lower() or "cross" in gb.title.lower():
                browse_widgets.append(gb)

        # Configure the settings
        for widget in browse_widgets:
            try:
                # Look for the axial and longitudinal slice view selectors
                # Based on XML: axialSliceViewSelector and longitudinalSliceViewSelector
                axial_selector = widget.findChild(slicer.qMRMLNodeComboBox, "axialSliceViewSelector")
                longitudinal_selector = widget.findChild(slicer.qMRMLNodeComboBox, "longitudinalSliceViewSelector")
                
                try:
                    if axial_selector:
                        # Set Axial to Red using direct node selection (similar to provided script)
                        red_slice_node = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeRed')
                        if red_slice_node:
                            axial_selector.setCurrentNode(red_slice_node)
                except Exception as axial_error:
                    logger.debug("Suppressed exception in configure_browse_cross_sections", exc_info=True)
                try:
                    if longitudinal_selector:
                        # Set Longitudinal to Green using direct node selection (similar to provided script)
                        green_slice_node = slicer.mrmlScene.GetNodeByID('vtkMRMLSliceNodeGreen')
                        if green_slice_node:
                            longitudinal_selector.setCurrentNode(green_slice_node)
                except Exception as longitudinal_error:
                    logger.debug("Suppressed exception in configure_browse_cross_sections", exc_info=True)
                
                # Find slider for Point Index (moveToPointSliderWidget in XML)
                try:
                    # Import ctk module first
                    import ctk
                    point_slider = widget.findChild(ctk.ctkSliderWidget, "moveToPointSliderWidget")
                    if point_slider:
                        if hasattr(point_slider, 'maximum') and point_slider.maximum > 0:
                            # Set point index to 230, but ensure it's within the slider's range
                            target_value = min(230, point_slider.maximum)
                            point_slider.setValue(target_value)
                except Exception as slider_error:
                    logger.debug("Suppressed exception in configure_browse_cross_sections", exc_info=True)
            except Exception as e:
                continue
        return True
    except Exception as e:
        return False

def switch_to_cpr_module(centerline_model=None, centerline_curve=None):
    """
    Switch to Curved Planar Reformat module and configure it with the centerline.
    Stores centerline references to ensure subsequent point placement uses the correct centerline.
    """
    try:
        # Store references to centerline nodes for later transform application and point placement
        if centerline_model:
            slicer.modules.WorkflowCenterlineModel = centerline_model
            pass  # Stored centerline model reference for CPR and point placement
        if centerline_curve:
            slicer.modules.WorkflowCenterlineCurve = centerline_curve
            pass  # Stored centerline curve reference for CPR and point placement
        
        # If no specific centerlines provided, try to find and store the most recent ones
        if not centerline_model and not centerline_curve:
            recent_model = centerline.find_recent_centerline_model()
            recent_curve = centerline.find_recent_centerline_curve()
            
            if recent_model:
                slicer.modules.WorkflowCenterlineModel = recent_model
                centerline_model = recent_model
                pass  # Found and stored recent centerline model
            
            if recent_curve:
                slicer.modules.WorkflowCenterlineCurve = recent_curve
                centerline_curve = recent_curve
                pass  # Found and stored recent centerline curve
        
        slicer.util.selectModule("CurvedPlanarReformat")
        pass
        slicer.app.processEvents()
        
        # Hide slice size controls from CPR module UI
        hide_cpr_slice_size_controls()

    # Switch to Red|Green slice-only layout
        ui.show_red_green_views_only()
        
        # Hide threshold segmentation mask after opening CPR module
        segmentation.hide_threshold_segmentation_mask()
        
        setup_cpr_module()
        markup.create_point_list_and_prompt()
        
        qt.QTimer.singleShot(1000, add_large_cpr_apply_button)
        
        qt.QTimer.singleShot(3000, auto_apply_cpr)
        
        
    except Exception as e:
        pass
        slicer.util.errorDisplay(f"Could not open Curved Planar Reformat module: {str(e)}")

def auto_apply_cpr():
    """
    Automatically apply the CPR processing while keeping the module open for re-application
    """
    try:
        pass
        
        cpr_widget = slicer.modules.curvedplanarreformat.widgetRepresentation()
        if not cpr_widget:
            pass
            return
        
        cpr_module = None
        if hasattr(cpr_widget, 'self'):
            cpr_module = cpr_widget.self()
        
        if not cpr_module:
            pass
            return
        
        apply_button = None
        
        if hasattr(cpr_module, 'ui') and hasattr(cpr_module.ui, 'applyButton'):
            apply_button = cpr_module.ui.applyButton
            pass
        
        if not apply_button and hasattr(slicer.modules, 'CPRLargeApplyButton'):
            apply_button = slicer.modules.CPRLargeApplyButton
            pass
        
        if not apply_button:
            all_buttons = cpr_widget.findChildren(qt.QPushButton)
            for button in all_buttons:
                if button.text.lower() == 'apply' and button.isEnabled():
                    apply_button = button
                    pass
                    break
        
        if apply_button and apply_button.isEnabled():
            pass
            apply_button.click()
            
            setup_cpr_completion_monitor()
            
            
        else:
            if not apply_button:
                pass
            else:
                pass
            pass
            
    except Exception as e:
        pass
        pass

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
            pass
        
    except Exception as e:
        logger.debug("Suppressed exception in setup_cpr_completion_monitor", exc_info=True)

def check_cpr_completion():
    """
    Check if CPR processing has completed
    """
    try:
        if hasattr(slicer.modules, 'CPRCheckCount'):
            slicer.modules.CPRCheckCount += 1
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
            pass
            if straightened_volumes:
                pass
            if projected_volumes:
                pass
            
            # Create analysis masks on the straightened volume
            core.create_analysis_masks(straightened_volumes)
            
            stop_cpr_monitoring()
            
        
    except Exception as e:
        logger.debug("Suppressed exception in check_cpr_completion", exc_info=True)

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
            
        pass
        
    except Exception as e:
        logger.debug("Suppressed exception in stop_cpr_monitoring", exc_info=True)

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
            input_volume = volume.find_working_volume()
            if input_volume:
                pass
                
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
                            pass
                            input_volume_set = True
                            break
                        else:
                            pass
                
                if not input_volume_set:
                    pass
                    pass
            else:
                pass
            
            # Configure centerline input - find the most recent centerline
            centerline_model = centerline.find_recent_centerline_model()  # Use default created_after=0 to find any existing model
            if centerline_model:
                pass
                
                # Store this as the current centerline for point placement
                slicer.modules.WorkflowCenterlineModel = centerline_model
                
                # Set centerline selector
                centerline_set = False
                for centerline_selector_name in ['inputCenterlineSelector', 'centerlineSelector', 'curveSelector']:
                    if hasattr(cpr_module.ui, centerline_selector_name):
                        selector = getattr(cpr_module.ui, centerline_selector_name)
                        
                        # Force refresh the selector's node list
                        if hasattr(selector, 'updateMRMLFromWidget'):
                            selector.updateMRMLFromWidget()

                        selector.setCurrentNode(centerline_model)
                        slicer.app.processEvents()
            
            # Also check for centerline curves and store reference
            centerline_curve = centerline.find_recent_centerline_curve()
            if centerline_curve:
                slicer.modules.WorkflowCenterlineCurve = centerline_curve

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
                
                # Set the output selectors to the created nodes
                output_volume_set = False
                projected_volume_set = False
                transform_set = False
                
                # Set output straightened volume selector
                if hasattr(cpr_module.ui, 'outputStraightenedVolumeSelector'):
                    cpr_module.ui.outputStraightenedVolumeSelector.setCurrentNode(output_volume)
                    output_volume_set = True
                    pass
                
                # Set output projected volume selector
                if hasattr(cpr_module.ui, 'outputProjectedVolumeSelector'):
                    cpr_module.ui.outputProjectedVolumeSelector.setCurrentNode(projected_volume)
                    projected_volume_set = True
                    pass
                
                # Set output transform selector
                if hasattr(cpr_module.ui, 'outputTransformToStraightenedVolumeSelector'):
                    cpr_module.ui.outputTransformToStraightenedVolumeSelector.setCurrentNode(transform_node)
                    transform_set = True
                    pass
                
                # Set resolution and thickness parameters
                if hasattr(cpr_module.ui, 'curveResolutionSliderWidget'):
                    cpr_module.ui.curveResolutionSliderWidget.setValue(1.0)
                    pass
                
                # Get the slice thickness from the input volume instead of using hardcoded value
                volume_slice_thickness = volume.get_volume_slice_thickness(input_volume)
                
                if hasattr(cpr_module.ui, 'sliceResolutionSliderWidget'):
                    cpr_module.ui.sliceResolutionSliderWidget.setValue(volume_slice_thickness)
                    pass
                
                # Legacy fallback for older parameter names
                if hasattr(cpr_module.ui, 'resolutionSpinBox'):
                    cpr_module.ui.resolutionSpinBox.setValue(volume_slice_thickness)
                    pass
                
                if hasattr(cpr_module.ui, 'thicknessSpinBox'):
                    cpr_module.ui.thicknessSpinBox.setValue(1.0)
                    pass
                
                # Final UI update
                slicer.app.processEvents()
                
                # Report setup status
                pass
                if output_volume_set:
                    pass
                else:
                    pass
                    
                if projected_volume_set:
                    pass
                else:
                    pass
                    
                if transform_set:
                    pass
                else:
                    pass
                
                if not input_volume:
                    pass
                if not centerline_model:
                    pass
                
                pass
                    
            except Exception as e:
                logger.debug("Suppressed exception in setup_cpr_module", exc_info=True)

            slicer.app.processEvents()
            
            add_large_cpr_apply_button()

        else:
            pass
            
    except Exception as e:
        logger.debug("Suppressed exception in setup_cpr_module", exc_info=True)

        


def on_continue_to_cpr(dialog, centerline_model=None, centerline_curve=None):
    """
    Called when user chooses to continue to CPR analysis
    """
    try:
        if hasattr(slicer.modules, 'CenterlineDialogShown'):
            slicer.modules.CenterlineDialogShown = False
        
        dialog.close()
        dialog.setParent(None)
        switch_to_cpr_module(centerline_model, centerline_curve)
        
        centerline.draw_circles_on_centerline()
    except Exception as e:
        logger.debug("Suppressed exception in on_continue_to_cpr", exc_info=True)

def on_continue_to_cpr_from_edit(dock_widget, centerline_model, centerline_curve):
    """
    Called when user wants to continue to CPR analysis with the edited centerline
    """
    try:
        # Close and cleanup the dock widget
        centerline.cleanup_centerline_edit_dialog()
        
        # Disable editing mode and switch to 3D fullscreen
        centerline.disable_centerline_editing(centerline_curve)
        
        # Continue to CPR with the edited centerline
        switch_to_cpr_module(centerline_model, centerline_curve)
        
        # Show circles on the centerline for analysis
        centerline.draw_circles_on_centerline()
        
    except Exception as e:
        logger.debug("Suppressed exception in on_continue_to_cpr_from_edit", exc_info=True)

def reset_cpr_module():
    """Reset the Curved Planar Reformat module to default state."""
    try:
        # Clean up CPR monitoring and custom elements
        stop_cpr_monitoring()
        
        # Switch modules to trigger reload
        current_module = slicer.util.moduleSelector().selectedModule
        slicer.util.selectModule("Welcome")
        slicer.app.processEvents()
        
        # Clean up CPR specific elements
        cleanup_cpr_custom_elements()
        
        # Switch back to original module
        if current_module and current_module != "CurvedPlanarReformat":
            slicer.util.selectModule(current_module)
            slicer.app.processEvents()
        return True
        
    except Exception as e:
        return False

def cleanup_cpr_custom_elements():
    """Clean up custom elements from CPR module."""
    try:
        cpr_attributes = [
            'CPRMonitorTimer',
            'CPRCheckCount',
            'LastUsedCenterlineModel',
            'LastUsedCenterlineCurve'
        ]
        
        for attr in cpr_attributes:
            if hasattr(slicer.modules, attr):
                delattr(slicer.modules, attr)
                
    except Exception as e:
        logger.debug("Suppressed exception in cleanup_cpr_custom_elements", exc_info=True)
