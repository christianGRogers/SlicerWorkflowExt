cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(DAI_Workflow)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/DAI_Workflow")
set(EXTENSION_CONTRIBUTORS "Christian Rogers (Lawson Research Institute and Western University (So Lab))")
set(EXTENSION_DESCRIPTION "This is a workflow module for automated vessel processing.")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/DAI_Workflow.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/DAI_Workflow/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(workflow)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
