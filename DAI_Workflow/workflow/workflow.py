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

        if not hasattr(self.ui, 'startWorkflowButton'):
            startButton = qt.QPushButton("Start Workflow")
            startButton.clicked.connect(self.onStartWorkflow)
            self.layout.addWidget(startButton)
        else:
            self.ui.startWorkflowButton.clicked.connect(self.onStartWorkflow)

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

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
            # If hiding status bar fails, log it but don't break the workflow
            print(f"Warning: Could not hide status bar: {str(e)}")

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
            # If showing status bar fails, log it but don't break the workflow
            print(f"Warning: Could not show status bar: {str(e)}")

    def setDarkBackground(self) -> None:
        """Set the 3D view background to dark/black."""
        try:
            # Call the function from workflow_moduals to set dark background
            import Moduals.workflow_moduals as workflow_mod
            workflow_mod.set_3d_view_background_black()
        except Exception as e:
            # If setting dark background fails, log it but don't break the workflow
            print(f"Warning: Could not set dark background: {str(e)}")

    def enter(self) -> None:
        """Called each time the user opens this module."""
        # Make sure parameter node exists and observed
        self.initializeParameterNode()
        
        # Hide the status bar by default when entering the workflow module
        self.hideStatusBar()
        
        # Set 3D view background to dark by default when entering the workflow module
        self.setDarkBackground()

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
    """Simple test for the Hello World module."""

    def setUp(self):
        """Do whatever is needed to reset the state."""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run tests."""
        self.setUp()
        self.test_workflow1()

    def test_workflow1(self):
        """Test the Hello World functionality."""
        self.delayDisplay("Starting the test")

        # Test the module logic
        logic = workflowLogic()
        logic.startWorkflow()

        self.delayDisplay("Test passed")
