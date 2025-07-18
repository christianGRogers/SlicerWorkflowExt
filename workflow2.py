import slicer
import vtk
import numpy as np

def create_centerline_and_tube_mask():
    """
    Creates a centerline curve and tube mask from points 3-4 of the F-1 point list.
    """
    
    # Step 1: Get the F-1 point list
    f1_points = slicer.util.getNode('F-1')
    if not f1_points:
        print("Error: F-1 point list not found")
        return
    
    # Check if F-1 has at least 4 points
    if f1_points.GetNumberOfControlPoints() < 4:
        print(f"Error: F-1 has only {f1_points.GetNumberOfControlPoints()} points. Need at least 4.")
        return
    
    print(f"Found F-1 with {f1_points.GetNumberOfControlPoints()} points")
    
    # Step 2: Create a new point list with the 3rd and 4th points (indices 2 and 3)
    centerline_points = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
    centerline_points.SetName('CenterlinePoints')
    
    # Get the 3rd point (index 2)
    point3_pos = [0, 0, 0]
    f1_points.GetNthControlPointPosition(2, point3_pos)
    centerline_points.AddControlPoint(point3_pos)
    
    # Get the 4th point (index 3)
    point4_pos = [0, 0, 0]
    f1_points.GetNthControlPointPosition(3, point4_pos)
    centerline_points.AddControlPoint(point4_pos)
    
    print(f"Created centerline points: Point 3 at {point3_pos}, Point 4 at {point4_pos}")
    
    # Step 3: Create a centerline curve from the two points
    centerline_curve = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsCurveNode')
    centerline_curve.SetName('CenterlineCurve')
    
    # Add the two points to the curve
    centerline_curve.AddControlPoint(point3_pos)
    centerline_curve.AddControlPoint(point4_pos)
    
    # Set curve type to linear for a straight line between the points
    centerline_curve.SetCurveTypeToLinear()
    
    print("Created centerline curve")
    
    # Step 4: Create a tube mask from the centerline curve
       # First, we need to get the curve's points and create proper polydata
    curve_points = centerline_curve.GetCurvePointsWorld()
    
    if not curve_points or curve_points.GetNumberOfPoints() == 0:
        print("Error: Could not get curve points")
        return
    
    # Create polydata from the curve points
    curve_polydata = vtk.vtkPolyData()
    curve_polydata.SetPoints(curve_points)
    
    # Create lines connecting the points
    lines = vtk.vtkCellArray()
    for i in range(curve_points.GetNumberOfPoints() - 1):
        line = vtk.vtkLine()
        line.GetPointIds().SetId(0, i)
        line.GetPointIds().SetId(1, i + 1)
        lines.InsertNextCell(line)
    
    curve_polydata.SetLines(lines)
    
    # Create a tube filter
    tube_filter = vtk.vtkTubeFilter()
    tube_filter.SetInputData(curve_polydata)
    tube_filter.SetRadius(2.0)  # Set tube radius (adjust as needed)
    tube_filter.SetNumberOfSides(12)  # Number of sides for the tube
    tube_filter.CappingOn()  # Cap the ends of the tube
    tube_filter.Update()
    
    # Create a model node for the tube
    tube_model = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
    tube_model.SetName('TubeMask')
    tube_model.SetAndObservePolyData(tube_filter.GetOutput())
    
    # Create a display node for the tube model
    tube_display = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelDisplayNode')
    tube_display.SetColor(1.0, 0.0, 0.0)  # Red color
    tube_display.SetOpacity(0.5)  # Semi-transparent
    tube_model.SetAndObserveDisplayNodeID(tube_display.GetID())
    
    print("Created tube mask model")
    
    # Optional: Convert the tube model to a segmentation for masking operations
    stenosis_segmentation = create_segmentation_from_tube(tube_model)
    
    # Add the cropped volume to the 3D scene
    add_cropped_volume_to_3d_scene()
    
    # Display density statistics using Segment Statistics module
    if stenosis_segmentation:
        show_segment_statistics(stenosis_segmentation)
    
    print("Workflow completed successfully!")

def create_segmentation_from_tube(tube_model):
    """
    Convert the tube model to a segmentation for use as a mask.
    """
    try:
        # Create a new segmentation node
        segmentation_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
        segmentation_node.SetName('TubeMaskSegmentation')
        
        # Import the tube model as a segment
        slicer.modules.segmentations.logic().ImportModelToSegmentationNode(tube_model, segmentation_node)
        
        # Set the segment name
        segmentation = segmentation_node.GetSegmentation()
        segment_ids = vtk.vtkStringArray()
        segmentation.GetSegmentIDs(segment_ids)
        
        if segment_ids.GetNumberOfValues() > 0:
            segment_id = segment_ids.GetValue(0)
            segment = segmentation.GetSegment(segment_id)
            segment.SetName('TubeMask')
            segment.SetColor(1.0, 0.0, 0.0)  # Red color
        
        print("Created tube mask segmentation")
        return segmentation_node
        
    except Exception as e:
        print(f"Warning: Could not create segmentation from tube model: {str(e)}")
        return None

def set_tube_radius(radius):
    """
    Helper function to set a custom tube radius.
    """
    global tube_radius
    tube_radius = radius
    print(f"Tube radius set to {radius}")

def add_cropped_volume_to_3d_scene():
    """
    Add the cropped volume to the 3D scene for visualization.
    """
    try:
        # Find the cropped volume (look for volumes with "cropped" in the name)
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        cropped_volume = None
        
        for volume in volume_nodes:
            if 'cropped' in volume.GetName().lower():
                cropped_volume = volume
                break
        
        if not cropped_volume:
            print("Warning: Could not find cropped volume to add to 3D scene")
            return
        
        # Get the 3D view
        threeDWidget = slicer.app.layoutManager().threeDWidget(0)
        threeDView = threeDWidget.threeDView()
        
        # Get volume rendering logic
        volumeRenderingLogic = slicer.modules.volumerendering.logic()
        
        # Create volume rendering display node
        displayNode = volumeRenderingLogic.CreateDefaultVolumeRenderingNodes(cropped_volume)
        
        if displayNode:
            # Enable volume rendering
            displayNode.SetVisibility(True)
            
            # Set rendering method to GPU raycast for better visualization
            displayNode.SetRaycastTechnique(slicer.vtkMRMLVolumeRenderingDisplayNode.Composite)
            
            # Set appropriate preset (CT-Chest-Contrast-Enhanced or similar)
            try:
                # Apply a preset suitable for vascular imaging
                presetName = "CT-Chest-Contrast-Enhanced"
                volumeRenderingLogic.ApplyVolumeRenderingDisplayPreset(displayNode, presetName)
                print(f"Applied preset: {presetName}")
            except:
                # If preset fails, try other common presets
                try:
                    presetName = "CT-Cardiac"
                    volumeRenderingLogic.ApplyVolumeRenderingDisplayPreset(displayNode, presetName)
                    print(f"Applied preset: {presetName}")
                except:
                    print("Using default volume rendering settings")
            
            # Ensure proper color and opacity settings
            volumeProperty = displayNode.GetVolumePropertyNode().GetVolumeProperty()
            if volumeProperty:
                # Set scalar opacity unit distance for better quality
                volumeProperty.SetScalarOpacityUnitDistance(0.1)
                
                # Enable gradient opacity for better depth perception
                volumeProperty.SetGradientOpacity(0, 0.0)
                volumeProperty.SetGradientOpacity(1, 0.5)
                
                # Set interpolation to linear for smoother appearance
                volumeProperty.SetInterpolationTypeToLinear()
                
                # Enable shading for better 3D appearance
                volumeProperty.SetShade(True)
                volumeProperty.SetAmbient(0.3)
                volumeProperty.SetDiffuse(0.6)
                volumeProperty.SetSpecular(0.5)
                volumeProperty.SetSpecularPower(40)
            
            # Set quality settings for better visualization
            displayNode.SetExpectedFPS(10.0)  # Reasonable frame rate
            displayNode.SetGPUMemorySize(1024)  # Use more GPU memory for better quality
            
            print(f"Added cropped volume '{cropped_volume.GetName()}' to 3D scene with raycast rendering")
        else:
            print("Warning: Could not create volume rendering display node")
            
    except Exception as e:
        print(f"Error adding cropped volume to 3D scene: {str(e)}")

def show_segment_statistics(stenosis_segmentation):
    """
    Open the Segment Statistics module to display density statistics for the stenosis mask.
    """
    try:
        if not stenosis_segmentation:
            print("Warning: No stenosis segmentation provided for statistics")
            return
        
        # Find the volume to analyze (specifically look for cropped volume)
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        analysis_volume = None
        
        # Search specifically for volumes with "cropped" in the name
        for volume in volume_nodes:
            if 'cropped' in volume.GetName().lower():
                analysis_volume = volume
                print(f"Found cropped volume for analysis: {volume.GetName()}")
                break
        
        if not analysis_volume:
            print("Warning: No volume with 'cropped' in name found for density analysis")
            print("Available volumes:")
            for volume in volume_nodes:
                print(f"  - {volume.GetName()}")
            return
        
        # Switch to Segment Statistics module
        slicer.util.selectModule('SegmentStatistics')
        
        # Get the Segment Statistics widget and auto-select the fields
        try:
            segmentStatisticsWidget = slicer.modules.segmentstatistics.widgetRepresentation().self()
            
            # Wait a moment for the widget to fully load
            slicer.app.processEvents()
            
            # Auto-select the segmentation (TubeMask)
            if hasattr(segmentStatisticsWidget, 'segmentationSelector'):
                segmentStatisticsWidget.segmentationSelector.setCurrentNode(stenosis_segmentation)
                print(f"✓ Set segmentation: {stenosis_segmentation.GetName()}")
            else:
                print("Warning: Could not find segmentationSelector")
            
            # Auto-select the cropped volume - try multiple approaches
            volume_set = False
            if hasattr(segmentStatisticsWidget, 'scalarVolumeSelector'):
                segmentStatisticsWidget.scalarVolumeSelector.setCurrentNode(analysis_volume)
                # Force update the selector
                slicer.app.processEvents()
                # Verify the selection took effect
                current_volume = segmentStatisticsWidget.scalarVolumeSelector.currentNode()
                if current_volume and current_volume.GetID() == analysis_volume.GetID():
                    print(f"✓ Set scalar volume: {analysis_volume.GetName()}")
                    volume_set = True
                else:
                    print(f"Warning: Volume selection may not have taken effect")
            
            # Try alternative method if first didn't work
            if not volume_set and hasattr(segmentStatisticsWidget, 'scalarVolumeSelector'):
                try:
                    # Try setting by node ID
                    segmentStatisticsWidget.scalarVolumeSelector.setCurrentNodeID(analysis_volume.GetID())
                    slicer.app.processEvents()
                    current_volume = segmentStatisticsWidget.scalarVolumeSelector.currentNode()
                    if current_volume and current_volume.GetID() == analysis_volume.GetID():
                        print(f"✓ Set scalar volume (method 2): {analysis_volume.GetName()}")
                        volume_set = True
                except:
                    pass
            
            if not volume_set:
                print(f"Warning: Could not automatically set scalar volume to {analysis_volume.GetName()}")
                print("Please manually select the cropped volume in the Scalar Volume dropdown")
            
            # Enable the statistics checkboxes
            if hasattr(segmentStatisticsWidget, 'labelmapStatisticsCheckBox'):
                segmentStatisticsWidget.labelmapStatisticsCheckBox.setChecked(True)
            if hasattr(segmentStatisticsWidget, 'scalarVolumeStatisticsCheckBox'):
                segmentStatisticsWidget.scalarVolumeStatisticsCheckBox.setChecked(True)
            
            print(f"Opened Segment Statistics module with auto-selected fields:")
            print(f"  Segmentation: {stenosis_segmentation.GetName()}")
            print(f"  Volume: {analysis_volume.GetName()}")
            print("  Statistics types: Labelmap and Scalar Volume enabled")
            print("  Click 'Apply' to compute statistics")
            
        except Exception as widget_error:
            print(f"Could not auto-select fields in Segment Statistics widget: {str(widget_error)}")
            print("Please manually select the segmentation and volume in the module")
            print(f"  Select segmentation: {stenosis_segmentation.GetName()}")
            print(f"  Select volume: {analysis_volume.GetName()} (look for 'cropped' in name)")
        
        print(f"Opened Segment Statistics module with auto-selected fields")
        
        # Show info to user
        if volume_set:
            volume_status = f"✓ Cropped Volume: {analysis_volume.GetName()}"
            ready_status = "Ready for analysis!"
            manual_instructions = ""
        else:
            volume_status = f"⚠ Please select: {analysis_volume.GetName()} (contains 'cropped')"
            ready_status = "Manual selection needed!"
            manual_instructions = ("If volume not selected automatically:\n"
                                 "• Click Scalar Volume dropdown\n"
                                 "• Select volume with \"cropped\" in name\n"
                                 "• Then click Apply\n\n")
        
        message = (f"Segment Statistics Module Ready!\n\n"
                  f"✓ Module opened\n"
                  f"✓ Segmentation: {stenosis_segmentation.GetName()}\n"
                  f"{volume_status}\n"
                  f"✓ Statistics types enabled\n\n"
                  f"{ready_status}\n\n"
                  f"{manual_instructions}"
                  f"Click 'Apply' in the Segment Statistics module to compute:\n"
                  f"• Volume measurements (cm³ and mm³)\n"
                  f"• Density statistics (HU)\n"
                  f"• Mean, standard deviation, min/max values\n\n"
                  f"Results will be displayed in the module's table.")
        
        slicer.util.infoDisplay(message)
        
    except Exception as e:
        print(f"Error opening Segment Statistics module: {str(e)}")
        
        # Fallback: just open the module without auto-selection
        try:
            slicer.util.selectModule('SegmentStatistics')
            print("Opened Segment Statistics module - please configure manually")
            print(f"  Select segmentation: {stenosis_segmentation.GetName()}")
            print(f"  Select volume: {analysis_volume.GetName()}")
            
        except Exception as fallback_error:
            print(f"Could not open Segment Statistics module: {str(fallback_error)}")
            print("Please open the Segment Statistics module manually")

def main():
    """
    Main function to run the workflow.
    """
    print("Starting centerline and tube mask creation workflow...")
    create_centerline_and_tube_mask()

# Run the script
if __name__ == "__main__":
    main()