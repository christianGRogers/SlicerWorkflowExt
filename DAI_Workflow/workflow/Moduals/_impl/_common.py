# Standard library imports
import logging
import math
import os
import time

# Third-party imports
import numpy as np
import vtk

# Slicer imports
import slicer
import qt

# Module logger. Routes through Slicer's Python logging so that failures are
# recorded in the application log (Help > Report a bug / the log files) instead
# of being silently swallowed. Suppressed/expected exceptions are logged at
# DEBUG so they stay quiet in normal use but can be surfaced by lowering the
# log level (logging.getLogger("DAI_Workflow").setLevel(logging.DEBUG)).
logger = logging.getLogger("DAI_Workflow")

# Import DICOM utilities with error handling
try:
    import DICOMLib
    from DICOMLib.DICOMUtils import TemporaryDICOMDatabase
    DICOM_UTILS_AVAILABLE = True
except ImportError as e:
    logger.warning("DICOMLib not available: %s", e)
    DICOM_UTILS_AVAILABLE = False

try:
    import ctk
except ImportError as e:
    logger.warning("ctk not available: %s", e)
    ctk = None

"""
Slicer Guided Workflow for Vessel Centerline Extraction and CPR Visualization

Christian Rogers - So Lab - Lawson - UWO (2025)

"""

# Initialize workflow by collapsing left panel on module load

# Names below are defined for star-import consumers even when the optional
# dependency is missing, so submodules can import them unconditionally.
if not DICOM_UTILS_AVAILABLE:
    DICOMLib = None
    TemporaryDICOMDatabase = None
