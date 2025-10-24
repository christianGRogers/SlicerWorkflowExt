import logging
import os
import Moduals.workflow_moduals as workflow_mod

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

try:
    import qt
except ImportError:
    # For environments where qt is not available
    pass


#
# workflow
#


class workflow(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("Workflow")
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Scripted Modules")]
        self.parent.dependencies = []
        self.parent.contributors = ["Christian Rogers (Lawson Research Institute and Western University (So Lab))"]
        self.parent.helpText = _("""
This is a workflow module for automated vessel processing.
""")
        self.parent.acknowledgementText = _("""
This file was originally developed by Christian Rogers (Lawson Research Institute and Western University (So Lab)).
""")


#
# workflowWidget
#


class workflowWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        uiWidget = slicer.util.loadUI(self.resourcePath('UI/workflow.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        self.logic = workflowLogic()
        self.initializeParameterNode()

        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        self.setupDataProbeAutoHide()
        self.hideLogo()
        self.hideHelpAndAcknowledgments()
        self.collapseLeftPanelForWorkflow()

        if not hasattr(self.ui, 'startWorkflowButton'):
            startButton = qt.QPushButton("Start Workflow")
            startButton.clicked.connect(self.onStartWorkflow)
            self.layout.addWidget(startButton)
        else:
            self.ui.startWorkflowButton.clicked.connect(self.onStartWorkflow)

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()
        
        # Clean up the data probe hide timer
        if hasattr(self, 'dataProbeHideTimer'):
            self.dataProbeHideTimer.stop()
            self.dataProbeHideTimer = None

    def setupDataProbeAutoHide(self) -> None:
        """Set up automatic hiding of data probe when modules are switched."""
        try:
            # Hide data probe immediately
            slicer.util.setDataProbeVisible(False)
            
            # Try to connect to module manager's active module changed signal
            try:
                moduleManager = slicer.app.moduleManager()
                if moduleManager and hasattr(moduleManager, 'activeModuleChanged'):
                    moduleManager.activeModuleChanged.connect(self.hideDataProbe)
            except:
                pass

            if hasattr(qt, 'QTimer'):
                self.dataProbeHideTimer = qt.QTimer()
                self.dataProbeHideTimer.timeout.connect(self.hideDataProbe)
                self.dataProbeHideTimer.timeout.connect(self.hideHelpAndAcknowledgments)
                self.dataProbeHideTimer.start(2000)  # Check every 2 seconds
            
        except Exception as e:
            pass

    def hideDataProbe(self) -> None:
        """Hide the data probe."""
        try:
            slicer.util.setDataProbeVisible(False)
        except Exception as e:
            pass
    def hideLogo(self) -> None:
        """Hide the Slicer logo."""
        try:
            logoLabel = slicer.util.findChild(slicer.util.mainWindow(), "LogoLabel")
            if logoLabel:
                logoLabel.visible = False
        except Exception as e:
           pass

    def hideHelpAndAcknowledgments(self) -> None:
        """Hide the Help and Acknowledgments section from all modules."""
        try:
            # Find the main window and look for help-related elements
            mainWindow = slicer.util.mainWindow()
            if mainWindow:
                # Look for common help section identifiers
                helpElements = [
                    "HelpCollapsibleButton",
                    "HelpButton",
                    "AcknowledgmentCollapsibleButton", 
                    "AcknowledgmentButton",
                    "ModuleHelpSection",
                    "ModuleAcknowledgmentSection"
                ]
                
                for elementName in helpElements:
                    element = slicer.util.findChild(mainWindow, elementName)
                    if element:
                        element.visible = False
                
                # Also look for elements by text content
                try:
                    # Find all collapsible buttons and hide those with help/acknowledgment text
                    from qt import QCollapsibleButton
                    collapsibleButtons = mainWindow.findChildren(QCollapsibleButton)
                    for button in collapsibleButtons:
                        buttonText = button.text.lower() if hasattr(button, 'text') else ""
                        if any(keyword in buttonText for keyword in ['help', 'acknowledgment', 'acknowledgement']):
                            button.visible = False
                except:
                    pass
                    
        except Exception as e:
            pass

    def hideStatusBar(self) -> None:
        """Hide the status bar at the bottom of the screen."""
        try:
            # Access the main window and hide its status bar
            mainWindow = slicer.util.mainWindow()
            if mainWindow:
                statusBar = mainWindow.statusBar()
                if statusBar:
                    statusBar.hide()
        except Exception as e:
            pass

    def showStatusBar(self) -> None:
        """Show the status bar at the bottom of the screen."""
        try:
            # Access the main window and show its status bar
            mainWindow = slicer.util.mainWindow()
            if mainWindow:
                statusBar = mainWindow.statusBar()
                if statusBar:
                    statusBar.show()
        except Exception as e:
            pass

    def setDarkBackground(self) -> None:
        """Set the 3D view background to dark/black."""
        try:
            import Moduals.workflow_moduals as workflow_mod
            workflow_mod.set_3d_view_background_black()
        except Exception as e:
            pass

    def enter(self) -> None:
        """Called each time the user opens this module."""

        self.initializeParameterNode()
        self.hideStatusBar()
        self.hideLogo()
        self.hideHelpAndAcknowledgments()
        self.setDarkBackground()
        self.checkForSourceSlicerFile()

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def collapseLeftPanelForWorkflow(self) -> None:
        """Collapse the left module panel when the DAI workflow is opened."""
        try:
            # Use the panel collapse function from workflow_moduals
            workflow_mod.force_collapse_left_panel_on_startup()
        except Exception as e:
            print(f"Could not collapse left panel: {e}")

    def checkForSourceSlicerFile(self) -> None:
        """Check for source_slicer.txt file in user directory and auto-load DICOM if found."""
        import os
        try:
            # Prevent multiple attempts in the same session
            if hasattr(slicer.modules, 'SourceSlicerFileProcessed'):
                return
            
            # Get user directory (e.g., C:\Users\chris)
            user_home = os.path.expanduser("~")
            source_file_path = os.path.join(user_home, "source_slicer.txt")
            
            print(f"Checking for source file: {source_file_path}")
            
            if os.path.exists(source_file_path):
                # Mark as processed to prevent multiple attempts
                slicer.modules.SourceSlicerFileProcessed = True
                
                try:
                    with open(source_file_path, 'r', encoding='utf-8') as f:
                        dicom_path = f.read().strip()
                    
                    if dicom_path and os.path.exists(dicom_path):
                        print(f"Found DICOM path in source file: {dicom_path}")
                        # Load DICOM automatically using workflow_moduals
                        import Moduals.workflow_moduals as workflow_mod
                        workflow_mod.load_dicom_from_source_file(dicom_path)
                    else:
                        print(f"Invalid or non-existent DICOM path in source file: {dicom_path}")
                        
                except Exception as e:
                    print(f"Error reading source_slicer.txt: {e}")
            else:
                # Mark as processed even if file doesn't exist to prevent repeated checks
                slicer.modules.SourceSlicerFileProcessed = True
                print("No source_slicer.txt file found in user directory")
                
        except Exception as e:
            print(f"Error checking for source_slicer.txt: {e}")

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        self.setParameterNode(self.logic.getParameterNode())

    def setParameterNode(self, inputParameterNode) -> None:
        """Set and observe parameter node."""
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)

    def onStartWorkflow(self) -> None:
        """Called when the start workflow button is clicked."""
        if self.logic:
            self.logic.startWorkflow()


#
# workflowLogic
#


class workflowLogic(ScriptedLoadableModuleLogic):
    """Simple logic class for Hello World functionality."""

    def __init__(self) -> None:
        """Called when the logic class is instantiated."""
        ScriptedLoadableModuleLogic.__init__(self)

    def getParameterNode(self):
        """Return the first parameter node for this module, creating one if none exists."""
        return slicer.mrmlScene.GetSingletonNode("workflow", "vtkMRMLScriptedModuleNode")

    def startWorkflow(self) -> None:
        #main entry point
        try:
            workflow_mod.start_with_dicom_data()
        except Exception as e:
            slicer.util.errorDisplay(f"Error in workflow: {str(e)}")
            


class workflowTest(ScriptedLoadableModuleTest):
    """Simple test for main module logic."""

    def setUp(self):
        """Do whatever is needed to reset the state."""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run tests."""
        self.setUp()
        self.test_workflow1()

    def test_workflow1(self):
        """Test the main module logic."""
        self.delayDisplay("Starting the test")

        
        logic = workflowLogic()
        logic.startWorkflow()

        self.delayDisplay("Test passed")
