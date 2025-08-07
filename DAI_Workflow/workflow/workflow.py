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
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Examples")]
        self.parent.dependencies = []
        self.parent.contributors = ["Your Name (Your Organization)"]
        self.parent.helpText = _("""
This is a workflow module for automated processing.
""")
        self.parent.acknowledgementText = _("""
This file was originally developed by Your Name.
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

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/workflow.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Create logic class
        self.logic = workflowLogic()

        # Make sure parameter node exists and observed
        self.initializeParameterNode()

        # Connections
        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Add a button to start the workflow (if not in UI file)
        if not hasattr(self.ui, 'startWorkflowButton'):
            startButton = qt.QPushButton("Start Workflow")
            startButton.clicked.connect(self.onStartWorkflow)
            self.layout.addWidget(startButton)
        else:
            self.ui.startWorkflowButton.clicked.connect(self.onStartWorkflow)

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

    def enter(self) -> None:
        """Called each time the user opens this module."""
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

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
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.
        self.setParameterNode(self.logic.getParameterNode())

    def setParameterNode(self, inputParameterNode) -> None:
        """Set and observe parameter node."""
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
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
            print(f"Error: {e}")


#
# workflowTest
#


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
