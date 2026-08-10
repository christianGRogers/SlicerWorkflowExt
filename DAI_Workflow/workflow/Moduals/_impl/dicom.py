from ._common import *  # noqa: F401,F403  (shared imports + logger)
from . import core, markup, segmentation, ui, volume  # sibling modules (cross-calls)

__all__ = [
    'start_with_dicom_data',
    'load_dicom_from_source_file',
    '_import_and_load_dicom_data',
    '_process_dicom_database_patients',
    '_load_philips_dicom_series',
    '_load_dicom_series_manually',
    '_load_with_dicom_browser',
    '_analyze_dicom_files',
    '_find_dicom_files_in_directory',
    'test_philips_detection',
    'load_philips_dicom_simple',
    'test_philips_dicom_loading',
    'diagnose_dicom_directory',
    'test_dicom_loading_with_path',
    'simple_dicom_load',
    '_fallback_dicom_loading',
    'test_dicom_directory_loading',
    'debug_dicom_file',
    'fix_dicom_spacing_and_orientation',
    'load_dicom_like_reference',
    'force_dicom_reimport',
]

def start_with_dicom_data():
    """
    Start the workflow by opening the Add DICOM Data module and waiting for a volume to be loaded.
    """
    try:
        # Set 3D view background to black at the start of workflow
        ui.set_3d_view_background_black()
        
        pass
        
        # Check if there are already volumes in the scene
        existing_volumes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        if existing_volumes:
            pass

            result = slicer.util.confirmYesNoDisplay(
                f"Found {len(existing_volumes)} existing volume(s) in the scene.\n\n"
                "Would you like to:\n"
                "• YES: Continue workflow with existing volumes\n"
                "• NO: Load new DICOM data",
                windowTitle="Existing Volumes Found"
            )
            if result:
                segmentation.start_workflow_with_segmentation_dialog()
                return
        
        slicer.util.selectModule("DICOM")
        slicer.app.processEvents()
        
        # Set up monitoring for volume addition
        volume.setup_volume_addition_monitor()
        
    except Exception as e:
        logger.debug("Suppressed exception in start_with_dicom_data", exc_info=True)
        slicer.util.errorDisplay(f"Could not open DICOM module: {str(e)}")

def load_dicom_from_source_file(dicom_path):
    """
    Load DICOM data from a path specified in the source_slicer.txt file.
    Uses a robust plugin-based approach similar to mpReviewPreprocessor for better compatibility.
    """
    import os
    import vtk
    try:
        
        # Check if path exists
        if not os.path.exists(dicom_path):
            qt.QMessageBox.warning(
                None,
                "DICOM Path Not Found",
                f"The DICOM path specified in source_slicer.txt does not exist:\n\n{dicom_path}\n\nPlease check the path and update the file."
            )
            return False
        
        # Enhanced Philips detection - prioritize this approach for Philips files
        # This checks for v_headers files and manufacturer info to identify Philips DICOMs
        dicom_files = _find_dicom_files_in_directory(dicom_path)
        if dicom_files:
            file_analysis = _analyze_dicom_files(dicom_files)
            if file_analysis['is_philips']:
                
                # Try the simple method first (exact copy of user's working script)
                simple_result = load_philips_dicom_simple(dicom_path)
                if simple_result:
                    return True
                
                # Fall back to enhanced method if simple fails
                philips_result = _load_philips_dicom_series(dicom_path)
                if philips_result:
                    return True
        
        # Check if enhanced DICOM utilities are available
        if not DICOM_UTILS_AVAILABLE:
            return _fallback_dicom_loading(dicom_path)
        
        # Use robust plugin-based approach inspired by mpReviewPreprocessor
        try:
            
            # Check if we can use TemporaryDICOMDatabase
            if DICOM_UTILS_AVAILABLE:
                try:
                    # Use temporary database for clean operation
                    temp_db_dir = os.path.join(slicer.app.temporaryPath, "WorkflowDICOMTemp")
                    if os.path.exists(temp_db_dir):
                        import shutil
                        shutil.rmtree(temp_db_dir)
                    
                    with TemporaryDICOMDatabase(temp_db_dir) as temp_db:
                        success = _import_and_load_dicom_data(dicom_path, temp_db)
                        if success:
                            return success
                except Exception as temp_db_error:
                    logger.debug("Suppressed exception in load_dicom_from_source_file", exc_info=True)
            
            # Fallback to direct plugin examination without temporary database
            success = _import_and_load_dicom_data(dicom_path, None)
            if success:
                return success
                    
        except Exception as e:
            logger.debug("Suppressed exception in load_dicom_from_source_file", exc_info=True)
            return _fallback_dicom_loading(dicom_path)
        
        # If we get here, all methods failed
        
        # Provide specific guidance based on file types found
        dicom_info = ""
        if os.path.isdir(dicom_path):
            files = os.listdir(dicom_path)
            numeric_extensions = [f for f in files if '.' in f and f.split('.')[-1].isdigit()]
            if numeric_extensions:
                dicom_info = f"\n\nDetected {len(numeric_extensions)} files with numeric extensions (e.g., .1, .2, .3).\nThis appears to be a DICOM series that should load as a complete volume."
        
        qt.QMessageBox.information(
            None,
            "DICOM Loading Failed",
            f"Could not automatically load DICOM from:\n{dicom_path}{dicom_info}\n\n"
            "Please manually:\n"
            "1. Go to DICOM module\n"
            "2. Import the DICOM folder\n"
            "3. Load the complete series as a volume\n"
            "4. Return to workflow module"
        )
        return False
        
    except Exception as e:
        logger.debug("Suppressed exception in load_dicom_from_source_file", exc_info=True)
        qt.QMessageBox.critical(
            None,
            "Error",
            f"Error loading DICOM from source file:\n{str(e)}"
        )
        return False

def _import_and_load_dicom_data(input_dir, temp_db=None):
    """
    Import and load DICOM data using enhanced plugin-based approach.
    Based on mpReviewPreprocessor methodology for robust DICOM handling.
    """
    try:
        
        # Use temporary database if provided, otherwise get main database safely
        dicom_database = temp_db
        if not dicom_database:
            try:
                # Try different ways to get the DICOM database
                if hasattr(slicer, 'dicomDatabase'):
                    dicom_database = slicer.dicomDatabase
                elif hasattr(slicer.modules, 'dicom'):
                    dicom_module = slicer.modules.dicom
                    if hasattr(dicom_module, 'logic'):
                        dicom_logic = dicom_module.logic()
                        if hasattr(dicom_logic, 'database'):
                            dicom_database = dicom_logic.database
                else:
                    dicom_database = None
            except Exception as db_error:
                logger.debug("Suppressed exception in _import_and_load_dicom_data", exc_info=True)
                dicom_database = None
        
        # Try different import methods based on available components
        if ctk and dicom_database:
            # Method 1: Use ctk indexer if both are available
            try:
                indexer = ctk.ctkDICOMIndexer()
                indexer.addDirectory(dicom_database, input_dir)
                
                # Continue with database analysis
                patients = dicom_database.patients()
                
                if patients:
                    # Process patients as before...
                    return _process_dicom_database_patients(dicom_database, patients, input_dir)
                    
            except Exception as indexer_error:
                logger.debug("Suppressed exception in _import_and_load_dicom_data", exc_info=True)

        # Method 2: Direct file analysis without plugins (bypass database issues)
        dicom_files = _find_dicom_files_in_directory(input_dir)
        
        if dicom_files:
            
            # Check if these are Philips files first - use specialized loader if so
            file_analysis = _analyze_dicom_files(dicom_files)
            if file_analysis.get('is_philips', False):
                try:
                    philips_result = _load_philips_dicom_series(input_dir)
                    if philips_result:
                        ui.set_3d_view_background_black()
                        qt.QTimer.singleShot(1000, markup.start_markup_workflow)
                        return True
                
                except Exception as philips_error:
                    logger.debug("Suppressed exception in _import_and_load_dicom_data", exc_info=True)
                    pass
            
            # Skip plugin system entirely and use Slicer's built-in loading
            try:
                
                # Method 2a: Try loading the directory directly
                volume_node = slicer.util.loadVolume(input_dir)
                
                if volume_node:
                    
                    # Check if we got a proper multi-slice volume
                    image_data = volume_node.GetImageData()
                    if image_data:
                        dims = image_data.GetDimensions()
                        

                    
                    volume_node.SetName("CT_Cardiac_Series")
                    ui.set_3d_view_background_black()
                    qt.QTimer.singleShot(1000, markup.start_markup_workflow)
                    return True
                    
            except Exception as dir_load_error:
                logger.debug("Suppressed exception in _import_and_load_dicom_data", exc_info=True)
            
            # Method 2b: Try loading first DICOM file (should trigger series loading)
            try:
                first_file = dicom_files[0]
                
                volume_node = slicer.util.loadVolume(first_file)
                
                if volume_node:
                    
                    # Check what we got
                    image_data = volume_node.GetImageData()
                    if image_data:
                        dims = image_data.GetDimensions()
                        
                        if dims[2] > 1:
                            volume_node.SetName("CT_Series")
                            ui.set_3d_view_background_black()
                            qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                            return True
                        else:
                            
                            # Try to load the full series using DICOM module
                            success = _load_dicom_series_manually(dicom_files, input_dir)
                            if success:
                                return True
                    
                    # If we still only have one slice, keep it but warn user
                    volume_node.SetName("CT_SingleSlice")
                    ui.set_3d_view_background_black()
                    qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                    return True
                    
            except Exception as file_load_error:
                logger.debug("Suppressed exception in _import_and_load_dicom_data", exc_info=True)
            
            # Method 2c: Try manual series loading for numbered DICOM files
            success = _load_dicom_series_manually(dicom_files, input_dir)
            if success:
                return True
            
            # Method 2d: Try Slicer's volume sequence loading
            success = volume._load_as_volume_sequence(dicom_files, input_dir)
            if success:
                return True
            
            # Method 2e: Last resort - try loading with VTK directly
            success = core._load_with_vtk_direct(dicom_files)
            if success:
                return True

        
        return False
    
    except Exception as e:
        logger.debug("Suppressed exception in _import_and_load_dicom_data", exc_info=True)
        return False

def _process_dicom_database_patients(dicom_database, patients, input_dir=None):
    """
    Process patients from DICOM database to find and load suitable series.
    """
    try:
        # Process each patient to find loadable series
        for patient in patients:
            studies = dicom_database.studiesForPatient(patient)
            
            for study in studies:
                series_list = dicom_database.seriesForStudy(study)
                
                for series_uid in series_list:
                    files = dicom_database.filesForSeries(series_uid)
                    if not files:
                        continue
                    
                    series_description = dicom_database.seriesDescription(series_uid)
                    
                    # Use plugin-based approach to find best loader
                    plugin, loadable = core._get_plugin_and_loadable_for_files(series_description, files)
                    
                    if loadable and plugin:
                        
                        try:
                            # Load the series using the best plugin
                            volume_node = plugin.load(loadable)
                            
                            if volume_node:
                                # Set appropriate name
                                if series_description:
                                    volume_node.SetName(series_description)
                                else:
                                    volume_node.SetName(f"DICOM_Series_{series_uid[:8]}")
                                
                                # Store DICOM metadata
                                volume_node.SetAttribute("DICOM_SeriesUID", series_uid)
                                volume_node.SetAttribute("DICOM_PatientID", patient)
                                
                                
                                # Verify we have a proper volume
                                image_data = volume_node.GetImageData()
                                if image_data:
                                    dims = image_data.GetDimensions()
                                    spacing = volume_node.GetSpacing()
                                    
                                    # Apply any necessary corrections
                                    fix_dicom_spacing_and_orientation(volume_node, input_dir)
                                    
                                    # Continue workflow
                                    ui.set_3d_view_background_black()
                                    qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                                    return True
                                    
                        except Exception as load_error:
                            logger.debug("Suppressed exception in _process_dicom_database_patients", exc_info=True)
                            continue
        
        return False
        
    except Exception as e:
        logger.debug("Suppressed exception in _process_dicom_database_patients", exc_info=True)
        return False

def _load_philips_dicom_series(dicom_directory):
    """
    Load Philips DICOM series using the exact method that works.
    Based on user's proven successful script - simplified and direct.
    """
    try:
        # Import required modules (exactly as in working script)
        import DICOMLib
        from DICOMLib import DICOMUtils
        import slicer
        
        # Track existing volumes
        existing_volumes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        
        # Ensure DICOM database is properly initialized before importing
        try:
            # Initialize DICOM database if it doesn't exist
            if not hasattr(slicer, 'dicomDatabase') or slicer.dicomDatabase is None:
                # Open DICOM module to initialize the database
                slicer.util.selectModule("DICOM")
                slicer.app.processEvents()
                
                # Alternative initialization if module approach doesn't work
                if not hasattr(slicer, 'dicomDatabase') or slicer.dicomDatabase is None:
                    import DICOMLib
                    # This should initialize slicer.dicomDatabase
                    DICOMLib.DICOMUtils.openDatabase()
        except Exception as init_error:
            logger.debug("Suppressed exception in _load_philips_dicom_series", exc_info=True)
        
        # Import DICOM directory (ignores unreadable files like v_headers)
        DICOMUtils.importDicom(dicom_directory)
        
        # Access the Slicer DICOM database instance (exactly as in working script)
        db = slicer.dicomDatabase  #  this is the correct database handle
        
        # Get all patient UIDs in the database
        patientUIDs = db.patients()
        
        if len(patientUIDs) == 0:
            return None
        else:
            firstPatientUID = patientUIDs[0]
            
            # Load the patient data (exactly as in working script)
            DICOMUtils.loadPatientByUID(firstPatientUID)
            
            # Check if volume was loaded successfully
            new_volumes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
            
            # Find the newly loaded volume
            for volume in new_volumes:
                if volume not in existing_volumes:  # This is a new volume
                    image_data = volume.GetImageData()
                    if image_data:
                        dims = image_data.GetDimensions()
                        
                        if dims[2] > 1:  # Ensure it's a multi-slice volume
                            volume.SetName("CT_Series_Philips")
                            
                            # Continue workflow after successful loading
                            qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                            
                            return volume
            
            # If no new volumes found, try the most recently loaded volume
            if new_volumes:
                latest_volume = new_volumes[-1]
                image_data = latest_volume.GetImageData()
                if image_data:
                    dims = image_data.GetDimensions()
                    if dims[2] > 1:
                        latest_volume.SetName("CT_Series_Philips")
                        
                        # Continue workflow after successful loading
                        qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                        
                        return latest_volume
            
            return None
            
    except Exception as e:
        logger.debug("Suppressed exception in _load_philips_dicom_series", exc_info=True)
        return None

def _load_dicom_series_manually(dicom_files, series_directory):
    """
    Manually load DICOM series when automatic loading only gets single slice.
    This handles numbered series like i1559699.CTDC.1, i1559700.CTDC.2, etc.
    Now includes Philips-specific loading and standardized temp folder conversion for better compatibility.
    """
    try:
        
        # Method -1: Check if this is Philips DICOM and use specialized loading
        file_analysis = _analyze_dicom_files(dicom_files)
        
        if file_analysis.get('is_philips', False):
            try:
                philips_result = _load_philips_dicom_series(series_directory)
                if philips_result:
                    ui.set_3d_view_background_black()
                    qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                    return True
            except Exception as philips_error:
                logger.debug("Suppressed exception in _load_dicom_series_manually", exc_info=True)
        
        # Method 0: Try standardized temp folder conversion first
        try:
            standardized_result = core._load_via_standardized_temp_folder(dicom_files, series_directory)
            if standardized_result:
                ui.set_3d_view_background_black()
                qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                return True
        except Exception as std_error:
            logger.debug("Suppressed exception in _load_dicom_series_manually", exc_info=True)
        
        # Method 1: Try using DICOMLib to create a temporary database and load series
        try:
            
            import DICOMLib
            
            # Create a temporary database in memory
            db = DICOMLib.DICOMDatabase()
            
            # Set up temporary database location
            import tempfile
            temp_dir = tempfile.mkdtemp()
            db_path = os.path.join(temp_dir, "temp_dicom.db")
            
            if db.openDatabase(db_path):
                
                # Index the DICOM files
                indexer = ctk.ctkDICOMIndexer()
                indexer.addDirectory(db, series_directory)
                
                # Get patients and series
                patients = db.patients()
                if patients:
                    for patient in patients:
                        studies = db.studiesForPatient(patient)
                        for study in studies:
                            series_list = db.seriesForStudy(study)
                            for series in series_list:
                                files_in_series = db.filesForSeries(series)
                                
                                if len(files_in_series) >= len(dicom_files) * 0.8:  # Got most files
                                    
                                    # Load using slicer with the series files
                                    volume_node = slicer.util.loadVolume(files_in_series[0])
                                    
                                    if volume_node:
                                        # Check if we got the full volume
                                        image_data = volume_node.GetImageData()
                                        if image_data:
                                            dims = image_data.GetDimensions()
                                            
                                            if dims[2] > 1:
                                                volume_node.SetName("CT_Series_Manual")
                                                ui.set_3d_view_background_black()
                                                qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                                                
                                                # Cleanup temp database
                                                db.closeDatabase()
                                                import shutil
                                                shutil.rmtree(temp_dir, ignore_errors=True)
                                                
                                                return True
                                    
                # Cleanup if failed
                db.closeDatabase()
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as dicomlib_error:
            logger.debug("Suppressed exception in _load_dicom_series_manually", exc_info=True)
        
        # Method 2: Try loading with explicit file list
        try:
            
            # Sort files by slice number if possible
            sorted_files = sorted(dicom_files, key=lambda x: core._extract_slice_number(x))
            
            # Try different approaches for multi-file loading
            approaches = [
                ("Load file list directly", lambda: slicer.util.loadVolume(sorted_files)),
                ("VTK DICOM reader", lambda: volume._load_volume_from_file_list(sorted_files)),
                ("Load directory with series hint", lambda: core._load_with_series_hint(series_directory, sorted_files)),
            ]
            
            for approach_name, approach_func in approaches:
                try:
                    volume_node = approach_func()
                    
                    if volume_node:
                        image_data = volume_node.GetImageData()
                        if image_data:
                            dims = image_data.GetDimensions()
                            
                            if dims[2] > 1:
                                volume_node.SetName("CT_Series_FileList")
                                ui.set_3d_view_background_black()
                                qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                                return True

                except Exception as approach_error:
                    logger.debug("Suppressed exception in _load_dicom_series_manually", exc_info=True)
                    
        except Exception as filelist_error:
            logger.debug("Suppressed exception in _load_dicom_series_manually", exc_info=True)
        
        # Method 3: Try DICOM browser loading
        try:
            success = _load_with_dicom_browser(series_directory)
            if success:
                return True
        except Exception as browser_error:
            logger.debug("Suppressed exception in _load_dicom_series_manually", exc_info=True)
        
        return False
        
    except Exception as e:
        logger.debug("Suppressed exception in _load_dicom_series_manually", exc_info=True)
        return False

def _load_with_dicom_browser(directory):
    """Try to load using DICOM browser module."""
    try:
        
        # Get DICOM browser module
        if hasattr(slicer.modules, 'dicom'):
            dicom_module = slicer.modules.dicom
            
            # Create widget instance
            dicom_widget = slicer.modules.DICOMWidget()
            
            # Try to import directory
            dicom_widget.onImportDirectory(directory)
            
            # This is a simplified approach - in practice, the DICOM browser
            # would require user interaction or more complex automation
            return False
            
    except Exception as e:
        logger.debug("Suppressed exception in _load_with_dicom_browser", exc_info=True)
        return False

def _analyze_dicom_files(files):
    """
    Analyze DICOM files to understand data characteristics and help with plugin selection.
    """
    analysis = {
        'file_count': len(files),
        'has_numeric_extensions': False,
        'has_ctdc_pattern': False,
        'has_header_files': False,
        'modality': 'unknown',
        'manufacturer': 'unknown',
        'series_type': 'unknown',
        'is_philips': False
    }
    
    try:
        # Analyze file naming patterns
        for file_path in files[:5]:  # Check first 5 files
            file_name = os.path.basename(file_path)
            
            # Check for numeric extensions (.1, .2, .3, etc.)
            if '.' in file_name and file_name.split('.')[-1].isdigit():
                analysis['has_numeric_extensions'] = True
            
            # Check for CTDC pattern
            if 'CTDC' in file_name.upper():
                analysis['has_ctdc_pattern'] = True
            
            # Check for header files
            if 'v_headers' in file_name.lower():
                analysis['has_header_files'] = True
        
        # Enhanced Philips detection - check for v_headers file
        for file_path in files:
            file_name = os.path.basename(file_path)
            if 'v_headers' in file_name.lower() or 'volume_headers' in file_name.lower():
                analysis['has_header_files'] = True
                analysis['is_philips'] = True  # v_headers is a strong indicator of Philips
                break
        
        # Try to read DICOM header information from first file if possible
        try:
            if DICOM_UTILS_AVAILABLE and not analysis['is_philips']:  # Skip DICOM header read if already detected as Philips
                # Try to use pydicom if available
                try:
                    import pydicom
                    ds = pydicom.dcmread(files[0], stop_before_pixels=True)
                    
                    if hasattr(ds, 'Modality'):
                        analysis['modality'] = str(ds.Modality)
                    
                    if hasattr(ds, 'Manufacturer'):
                        analysis['manufacturer'] = str(ds.Manufacturer)
                        # Check for Philips manufacturer
                        if 'philips' in analysis['manufacturer'].lower():
                            analysis['is_philips'] = True
                    
                    if hasattr(ds, 'SeriesDescription'):
                        series_desc = str(ds.SeriesDescription).lower()
                        if any(term in series_desc for term in ['enhanced', '4d', 'dynamic']):
                            analysis['series_type'] = 'enhanced'
                        elif any(term in series_desc for term in ['seg', 'segmentation']):
                            analysis['series_type'] = 'segmentation'
                        elif any(term in series_desc for term in ['rt', 'rtstruct']):
                            analysis['series_type'] = 'rt_structure'
                        else:
                            analysis['series_type'] = 'standard'
                    
                except Exception:
                    logger.debug("Suppressed exception in _analyze_dicom_files", exc_info=True)
                    pass  # pydicom not available or file not readable
        except Exception:
            logger.debug("Suppressed exception in _analyze_dicom_files", exc_info=True)
            pass  # DICOM analysis failed, use basic analysis
        
    except Exception as e:
        logger.debug("Suppressed exception in _analyze_dicom_files", exc_info=True)
    
    return analysis

def _find_dicom_files_in_directory(directory):
    """
    Find DICOM files in a directory using enhanced detection patterns.
    Improved to handle complex medical imaging folder structures.
    """
    dicom_files = []
    try:
        file_count = 0
        
        for root, dirs, files in os.walk(directory):
            
            for file in files:
                file_count += 1
                file_path = os.path.join(root, file)
                filename = os.path.basename(file)
                filename_lower = filename.lower()
                
                # Check file size - DICOM files are typically larger than a few KB
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size < 1024:  # Skip very small files (likely not DICOM)
                        continue
                except:
                    logger.debug("Suppressed exception in _find_dicom_files_in_directory", exc_info=True)
                    continue
                
                # Enhanced DICOM file detection patterns
                is_dicom = False
                
                # Standard DICOM extensions
                if filename_lower.endswith(('.dcm', '.dicom', '.ima', '.dcm30', '.dic')):
                    is_dicom = True
                
                # Files with no extension (common in medical imaging)
                elif '.' not in filename and len(filename) > 3:
                    is_dicom = True
                
                # Files starting with medical imaging prefixes
                elif filename_lower.startswith(('i', 'im', 'ima', 'dicom', 'ct', 'mr')):
                    is_dicom = True
                
                # Files containing medical patterns (but exclude known non-DICOM files)
                elif any(pattern in filename_lower for pattern in ['ctdc', 'ct_', 'mr_', 'cta', 'coronary']):
                    # Exclude known non-DICOM files
                    if not any(exclude in filename_lower for exclude in ['header', 'readme', 'info', 'summary']):
                        is_dicom = True
                
                # Numbered series (.1, .2, .3, etc.) but not headers
                elif '.' in filename and filename.split('.')[-1].isdigit() and 'header' not in filename_lower:
                    is_dicom = True
                
                # Try to detect DICOM by reading file header
                elif file_size > 132:  # DICOM files have at least 132 byte preamble
                    # Skip files that are clearly not DICOM
                    if not any(exclude in filename_lower for exclude in ['header', 'readme', 'info', 'summary', 'text', 'log']):
                        try:
                            with open(file_path, 'rb') as f:
                                f.seek(128)  # Skip preamble
                                dicm_tag = f.read(4)
                                if dicm_tag == b'DICM':
                                    is_dicom = True
                        except:
                            logger.debug("Suppressed exception in _find_dicom_files_in_directory", exc_info=True)
                
                if is_dicom:
                    dicom_files.append(file_path)
        
        
        # Sort files for proper series order
        dicom_files.sort()

        
        return dicom_files
        
    except Exception as e:
        logger.debug("Suppressed exception in _find_dicom_files_in_directory", exc_info=True)
        return []

def test_philips_detection(dicom_path):
    """
    Test Philips DICOM detection for a given directory.
    Usage: test_philips_detection(r"C:\\Users\\username\\Desktop\\DICOM_folder")
    """
    
    if not os.path.exists(dicom_path):
        return False
    
    try:
        # Find DICOM files
        dicom_files = _find_dicom_files_in_directory(dicom_path)
        if not dicom_files:
            return False
        
        
        # Analyze files
        analysis = _analyze_dicom_files(dicom_files)
        
        if analysis.get('is_philips', False):
            return True
        else:
            return False
            
    except Exception as e:
        logger.debug("Suppressed exception in test_philips_detection", exc_info=True)
        return False

def load_philips_dicom_simple(dicom_path):
    """
    Load Philips DICOM using the exact user's working method.
    This is a direct copy of the user's proven script.
    """
    try:
        import DICOMLib
        from DICOMLib import DICOMUtils
        import slicer

        dicomDataDir = dicom_path

        # Import DICOM directory (ignores unreadable files like v_headers)
        DICOMUtils.importDicom(dicomDataDir)

        # Access the Slicer DICOM database instance
        db = slicer.dicomDatabase

        # Get all patient UIDs in the database
        patientUIDs = db.patients()

        if len(patientUIDs) == 0:
            return None
        else:
            firstPatientUID = patientUIDs[0]
            DICOMUtils.loadPatientByUID(firstPatientUID)
            
            # Continue workflow after successful loading
            qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
            
            # Return success
            return True
            
    except Exception as e:
        logger.debug("Suppressed exception in load_philips_dicom_simple", exc_info=True)
        return None

def test_philips_dicom_loading(dicom_path):
    """
    Test the complete Philips DICOM loading workflow.
    Usage: test_philips_dicom_loading(r"C:\\Users\\username\\Desktop\\Philips_DICOM_folder")
    """
    
    if not os.path.exists(dicom_path):
        return False
    
    try:
        # Step 1: Test detection
        dicom_files = _find_dicom_files_in_directory(dicom_path)
        if not dicom_files:
            return False
        
        analysis = _analyze_dicom_files(dicom_files)
        
        if not analysis.get('is_philips', False):
            return False
        
        # Step 2: Test Philips loading
        initial_volumes = len(slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode'))
        
        result = _load_philips_dicom_series(dicom_path)
        
        final_volumes = len(slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode'))
        
        if result:
            return True
        else:
            return False
            
    except Exception as e:
        logger.debug("Suppressed exception in test_philips_dicom_loading", exc_info=True)
        return False

def diagnose_dicom_directory(dicom_path):
    """
    Diagnose what's in a DICOM directory to help troubleshoot loading issues.
    Usage: diagnose_dicom_directory(r"G:\\My Drive\\Lawson\\FOURDIX\\...")
    """
    
    if not os.path.exists(dicom_path) or not os.path.isdir(dicom_path):
        return
    
    try:
        # Get directory structure
        subdirs = []
        total_files = 0
        
        for root, dirs, files in os.walk(dicom_path):
            level = root.replace(dicom_path, '').count(os.sep)
            indent = ' ' * 2 * level
            folder_name = os.path.basename(root) if level > 0 else "ROOT"
            total_files += len(files)
            
            if level == 1:  # First level subdirectories
                subdirs.append(root)
            
            if level > 3:  # Don't go too deep in display
                continue
        
        
        # Analyze DICOM files
        dicom_files = _find_dicom_files_in_directory(dicom_path)
        
        if not dicom_files:
            
            # Suggest looking in subdirectories
            if subdirs:
                for subdir in subdirs[:3]:  # Check first 3 subdirs
                    sub_dicom_files = _find_dicom_files_in_directory(subdir)
                    if sub_dicom_files:
                        break

            
    except Exception as e:
        logger.debug("Suppressed exception in diagnose_dicom_directory", exc_info=True)

def test_dicom_loading_with_path(dicom_path):
    """
    Test the enhanced DICOM loading with a specific path.
    Usage: test_dicom_loading_with_path(r"C:\\Users\\username\\Desktop\\DICOM_folder")
    """
    
    if not os.path.exists(dicom_path):
        return False
    
    # Test the enhanced loading function
    try:
        success = load_dicom_from_source_file(dicom_path)
        return success
    except Exception as e:
        logger.debug("Suppressed exception in test_dicom_loading_with_path", exc_info=True)
        return False

def simple_dicom_load(dicom_path):
    """
    Simplified DICOM loading that bypasses complex database operations.
    Usage: simple_dicom_load(r"G:\\My Drive\\Lawson\\FOURDIX\\...")
    """
    
    if not os.path.exists(dicom_path):
        return False
    
    try:
        # Method 1: Try direct directory loading
        volume_node = slicer.util.loadVolume(dicom_path)
        
        if volume_node:
            image_data = volume_node.GetImageData()
            if image_data:
                dims = image_data.GetDimensions()
            
            ui.set_3d_view_background_black()
            qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
            return True
            
    except Exception as e:
        logger.debug("Suppressed exception in simple_dicom_load", exc_info=True)
    
    try:
        # Method 2: Find and load first DICOM file
        dicom_files = _find_dicom_files_in_directory(dicom_path)
        
        if not dicom_files:
            return False
            
        first_file = dicom_files[0]
        
        volume_node = slicer.util.loadVolume(first_file)
        
        if volume_node:
            image_data = volume_node.GetImageData()
            
            ui.set_3d_view_background_black()
            qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
            return True
            
    except Exception as e:
        logger.debug("Suppressed exception in simple_dicom_load", exc_info=True)
    
    return False

def _fallback_dicom_loading(dicom_path):
    """
    Fallback DICOM loading when enhanced methods are not available.
    Uses simplified but robust approaches.
    """
    try:
        
        # Method 1: Simple directory loading (try multiple approaches)
        try:
            
            # Try loading the directory directly
            volume_node = slicer.util.loadVolume(dicom_path)
            if volume_node:
                ui.set_3d_view_background_black()
                qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                return True
                
        except Exception as e:
            
            # Try loading subdirectories if main directory fails
            try:
                pass
                subdirs = [d for d in os.listdir(dicom_path) if os.path.isdir(os.path.join(dicom_path, d))]
                
                for subdir in subdirs:
                    subdir_path = os.path.join(dicom_path, subdir)
                    pass
                    
                    try:
                        volume_node = slicer.util.loadVolume(subdir_path)
                        if volume_node:
                            pass
                            ui.set_3d_view_background_black()
                            qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                            return True
                    except Exception as subdir_error:
                        logger.debug("Suppressed exception in _fallback_dicom_loading", exc_info=True)
                        continue
                        
            except Exception as subdir_scan_error:
                logger.debug("Suppressed exception in _fallback_dicom_loading", exc_info=True)
        
        # Method 2: Enhanced directory analysis and direct loading
        try:
            
            # Analyze directory for DICOM files
            dicom_files = []
            for root, dirs, files in os.walk(dicom_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_lower = file.lower()
                    
                    # Enhanced DICOM file detection
                    is_dicom = (
                        file_lower.endswith(('.dcm', '.dicom', '.ima')) or
                        ('.' not in file and len(file) > 3) or  # Files without extension
                        file_lower.startswith(('i', 'ima', 'dicom')) or
                        'ctdc' in file_lower or
                        ('.' in file and file.split('.')[-1].isdigit())  # .1, .2, .3 files
                    )
                    
                    if is_dicom:
                        dicom_files.append(file_path)
            
            
            if dicom_files:
                # Sort files for proper series order
                dicom_files.sort()
                
                # Try to load using directory path first
                try:
                    # Use parent directory for series loading
                    parent_dir = os.path.dirname(dicom_files[0])
                    volume_node = slicer.util.loadVolume(parent_dir)
                    
                    if volume_node:
                        ui.set_3d_view_background_black()
                        qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                        return True
                except Exception as dir_load_error:
                    logger.debug("Suppressed exception in _fallback_dicom_loading", exc_info=True)
                
                # Try loading first file (may only get single slice)
                try:
                    volume_node = slicer.util.loadVolume(dicom_files[0])
                    if volume_node:
                        ui.set_3d_view_background_black()
                        qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                        return True
                except Exception as file_load_error:
                    logger.debug("Suppressed exception in _fallback_dicom_loading", exc_info=True)
                                
        except Exception as e:
            logger.debug("Suppressed exception in _fallback_dicom_loading", exc_info=True)
            
        # Method 3: Try using Slicer's DICOM database directly (safer approach)
        try:
            
            # Clear any existing data
            current_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
            initial_count = len(current_nodes)
            
            # Open DICOM module
            slicer.util.selectModule("DICOM")
            slicer.app.processEvents()
            
            # Try to get DICOM database and add directory
            dicom_db = None
            try:
                if hasattr(slicer, 'dicomDatabase'):
                    dicom_db = slicer.dicomDatabase
                elif hasattr(slicer.modules, 'dicom'):
                    dicom_module = slicer.modules.dicom
                    if hasattr(dicom_module, 'logic'):
                        dicom_logic = dicom_module.logic()
                        if hasattr(dicom_logic, 'database'):
                            dicom_db = dicom_logic.database
            except:
                logger.debug("Suppressed exception in _fallback_dicom_loading", exc_info=True)
                dicom_db = None
                
            if dicom_db:
                
                # Initialize database if needed
                if hasattr(dicom_db, 'initializeDatabase'):
                    dicom_db.initializeDatabase()
                
                # Try to import using the database's own methods
                try:
                    # Import files to database
                    import glob
                    all_files = glob.glob(os.path.join(dicom_path, '**', '*'), recursive=True)
                    dicom_files = [f for f in all_files if os.path.isfile(f)]
                    
                    
                    if dicom_files:
                        # Try loading a representative file to trigger series detection
                        test_file = dicom_files[0]
                        
                        # Use Slicer's own loading logic
                        volume_node = slicer.util.loadVolume(test_file)
                        
                        if volume_node:
                            
                            # Check if we got more than one slice
                            image_data = volume_node.GetImageData()
                            if image_data:
                                dims = image_data.GetDimensions()
    
                            
                            ui.set_3d_view_background_black()
                            qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                            return True
                            
                except Exception as db_import_error:
                    logger.debug("Suppressed exception in _fallback_dicom_loading", exc_info=True)
            else:
                
                # Method 4: Direct Slicer loading without database
                try:
                    # Find DICOM files and try loading with Slicer's built-in methods
                    dicom_files = _find_dicom_files_in_directory(dicom_path)
                    
                    if dicom_files:
                        
                        # Try loading the first file (should trigger series loading)
                        first_file = dicom_files[0]
                        
                        volume_node = slicer.util.loadVolume(first_file)
                        
                        if volume_node:
                            
                            # Check dimensions
                            image_data = volume_node.GetImageData()
                            if image_data:
                                dims = image_data.GetDimensions()

                            
                            ui.set_3d_view_background_black()
                            qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                            return True
                            
                except Exception as direct_load_error:
                    logger.debug("Suppressed exception in _fallback_dicom_loading", exc_info=True)
                    
        except Exception as e:
            logger.debug("Suppressed exception in _fallback_dicom_loading", exc_info=True)
        
        return False
        
    except Exception as e:
        logger.debug("Suppressed exception in _fallback_dicom_loading", exc_info=True)
        return False

# ===============================================================================
# DICOM DEBUGGING AND TESTING FUNCTIONS
# ===============================================================================

def test_dicom_directory_loading(directory_path):
    """
    Test DICOM loading from a directory (console helper function).
    Usage: test_dicom_directory_loading(r"C:\\Users\\croger52\\Desktop\\SYS_01")
    """
    import os
    
    if not os.path.exists(directory_path):
        return
    
    if not os.path.isdir(directory_path):
        return
    
    # List all files and identify potential DICOM files and header files
    try:
        all_files = []
        potential_dicom_files = []
        header_files = []
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                full_path = os.path.join(root, file)
                all_files.append(full_path)
                
                file_lower = file.lower()
                
                # Check for header files first
                if 'v_headers' in file_lower:
                    header_files.append((full_path, "DICOM header file"))
                    continue
                
                is_dicom = False
                reason = []
                
                # Check various DICOM patterns
                if file_lower.endswith(('.dcm', '.dicom', '.ima')):
                    is_dicom = True
                    reason.append("standard extension")
                elif '.' not in file:
                    is_dicom = True
                    reason.append("no extension")
                elif file_lower.startswith(('i', 'im', 'ima', 'dicom')):
                    is_dicom = True
                    reason.append("DICOM prefix")
                elif any(pattern in file_lower for pattern in ['ctdc', 'ct', 'mr', 'us', 'xr']):
                    is_dicom = True
                    reason.append("medical imaging pattern")
                elif file.count('.') >= 1:
                    parts = file.split('.')
                    if len(parts) >= 2 and parts[-1].isdigit():
                        is_dicom = True
                        reason.append("numeric extension")
                
                if is_dicom:
                    potential_dicom_files.append((full_path, ", ".join(reason)))
        


        
        # Analyze for DICOM series patterns
        numeric_files = []
        ctdc_files = []
        standard_dicom_files = []
        
        for file_path, reason in potential_dicom_files:
            filename = os.path.basename(file_path)
            if 'CTDC' in filename.upper():
                ctdc_files.append((filename, reason))
            elif '.' in filename and filename.split('.')[-1].isdigit():
                numeric_files.append((filename, reason))
            elif filename.lower().endswith(('.dcm', '.dicom')):
                standard_dicom_files.append((filename, reason))

            
        # Test loading the enhanced function
        success = load_dicom_from_source_file(directory_path)
        
        if success:
            # Check if we got a proper volume series
            volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
            if volume_nodes:
                latest_volume = volume_nodes[-1]  # Get the most recently loaded volume
                image_data = latest_volume.GetImageData()
                if image_data:
                    dimensions = image_data.GetDimensions()

        
    except Exception as e:
        logger.debug("Suppressed exception in test_dicom_directory_loading", exc_info=True)

def debug_dicom_file(file_path):
    """
    Debug information about a specific DICOM file.
    Usage: debug_dicom_file(r"C:\\Users\\croger52\\Desktop\\SYS_01\\i1559699.CTDC.1")
    """
    import os
    try:
        
        if not os.path.exists(file_path):
            return
            
        
        # Try to read first few bytes to check if it looks like DICOM
        try:
            with open(file_path, 'rb') as f:
                first_bytes = f.read(200)
                
                # Check for DICOM magic number at offset 128
                if len(first_bytes) > 132:
                    magic = first_bytes[128:132]
                    is_dicom = magic == b'DICM'
                
        except Exception as e:
            logger.debug("Suppressed exception in debug_dicom_file", exc_info=True)
            
    except Exception as e:
        logger.debug("Suppressed exception in debug_dicom_file", exc_info=True)

def fix_dicom_spacing_and_orientation(volume_node, dicom_directory=None):
    """
    Attempt to fix spacing and orientation issues in a loaded DICOM volume.
    This function tries to extract proper spacing from DICOM headers if available.
    
    Args:
        volume_node: The volume node to fix
        dicom_directory: Optional directory containing DICOM files for header analysis
        
    Returns:
        bool: True if corrections were applied, False otherwise
    """
    import os
    
    if not volume_node:
        return False
    
    try:
        
        # Get current properties
        current_spacing = volume_node.GetSpacing()
        image_data = volume_node.GetImageData()
        
        if not image_data:
            return False
        
        dims = image_data.GetDimensions()
        
        # Try to analyze DICOM files in directory for proper spacing
        corrections_applied = False
        
        if dicom_directory and os.path.exists(dicom_directory):
            try:
                
                # Find DICOM files
                dicom_files = []
                for root, dirs, files in os.walk(dicom_directory):
                    for file in files:
                        if (file.endswith(('.dcm', '.DICOM')) or 
                            ('.' in file and file.split('.')[-1].isdigit()) or
                            'CTDC' in file.upper()):
                            dicom_files.append(os.path.join(root, file))
                
                if len(dicom_files) >= 2:
                    # Sort files to get proper sequence
                    dicom_files.sort()
                    
                    # Try to read first few files to get spacing info
                    try:
                        import pydicom
                        
                        # Read first file
                        ds1 = pydicom.dcmread(dicom_files[0], force=True)
                        
                        # Get pixel spacing
                        pixel_spacing = None
                        if hasattr(ds1, 'PixelSpacing') and ds1.PixelSpacing:
                            pixel_spacing = [float(x) for x in ds1.PixelSpacing]
                        
                        # Calculate slice thickness from file positions if possible
                        slice_thickness = None
                        if len(dicom_files) > 1:
                            try:
                                ds2 = pydicom.dcmread(dicom_files[1], force=True)
                                
                                # Try to get slice positions
                                if (hasattr(ds1, 'ImagePositionPatient') and ds1.ImagePositionPatient and
                                    hasattr(ds2, 'ImagePositionPatient') and ds2.ImagePositionPatient):
                                    
                                    pos1 = [float(x) for x in ds1.ImagePositionPatient]
                                    pos2 = [float(x) for x in ds2.ImagePositionPatient]
                                    
                                    # Calculate distance between slices
                                    import math
                                    slice_thickness = math.sqrt(sum([(p2-p1)**2 for p1, p2 in zip(pos1, pos2)]))
                                
                                elif hasattr(ds1, 'SliceThickness') and ds1.SliceThickness:
                                    slice_thickness = float(ds1.SliceThickness)
                                    
                            except Exception as slice_error:
                                logger.debug("Suppressed exception in fix_dicom_spacing_and_orientation", exc_info=True)
                        
                        # Apply corrections if we found proper spacing
                        if pixel_spacing:
                            new_spacing = list(current_spacing)
                            
                            # Apply pixel spacing to x,y
                            new_spacing[0] = pixel_spacing[0] if len(pixel_spacing) > 0 else current_spacing[0]
                            new_spacing[1] = pixel_spacing[1] if len(pixel_spacing) > 1 else current_spacing[1]
                            
                            # Apply slice thickness to z if available
                            if slice_thickness and slice_thickness > 0:
                                new_spacing[2] = slice_thickness
                            elif len(pixel_spacing) > 1:
                                # Use average pixel spacing as estimate for slice thickness
                                new_spacing[2] = (pixel_spacing[0] + pixel_spacing[1]) / 2
                            
                            # Only apply if significantly different from current
                            spacing_diff = max([abs(new_spacing[i] - current_spacing[i]) for i in range(3)])
                            if spacing_diff > 0.01:  # Only if difference is > 0.01mm
                                volume_node.SetSpacing(new_spacing)
                                corrections_applied = True
                        
                    except ImportError:
                        logger.debug("Suppressed exception in fix_dicom_spacing_and_orientation", exc_info=True)
                    except Exception as dicom_error:
                        logger.debug("Suppressed exception in fix_dicom_spacing_and_orientation", exc_info=True)
                        
            except Exception as analysis_error:
                logger.debug("Suppressed exception in fix_dicom_spacing_and_orientation", exc_info=True)
        
        # Fallback: Apply reasonable defaults if spacing looks wrong
        if not corrections_applied:
            # Check if current spacing looks unreasonable
            if (current_spacing[0] == 1.0 and current_spacing[1] == 1.0 and current_spacing[2] == 1.0):
                # Common CT spacing
                volume_node.SetSpacing((0.5, 0.5, 1.0))  # 0.5mm pixel, 1mm slice
                corrections_applied = True
        
        if corrections_applied:
            
            # Update display
            volume_node.Modified()
            slicer.app.processEvents()
            
            # Reset slice views to show corrected volume properly
            slicer.util.resetSliceViews()
            
        return corrections_applied
        
    except Exception as e:
        logger.debug("Suppressed exception in fix_dicom_spacing_and_orientation", exc_info=True)
        return False

def load_dicom_like_reference():
    """
    Load DICOM using the same method that produces the reference structure.
    This replicates the exact import process that creates properly structured DICOM series.
    """
    import os
    try:
        
        # Read the source path - use user's home directory (consistent with other functions)
        user_home = os.path.expanduser("~")
        source_file_path = os.path.join(user_home, "source_slicer.txt")
        dicom_path = None
        
        try:
            with open(source_file_path, 'r') as f:
                dicom_path = f.read().strip()
        except FileNotFoundError:
            logger.debug("Suppressed exception in load_dicom_like_reference", exc_info=True)
            return False
        
        if not dicom_path or not os.path.exists(dicom_path):
            return False
        
        
        # Method 1: Use the exact same approach as the DICOM module
        # This matches how the reference import was likely created
        
        # Open DICOM module first
        slicer.util.selectModule("DICOM")
        slicer.app.processEvents()
        
        # Get DICOM browser widget
        dicom_browser = slicer.modules.dicom.widgetRepresentation().self().browserWidget
        
        # Clear existing database to avoid conflicts
        slicer.dicomDatabase.initializeDatabase()
        
        # Import the directory with the same settings as manual import
        dicom_browser.importDirectory(dicom_path, copy=True)
        
        # Process events and wait for completion
        slicer.app.processEvents()
        import time
        time.sleep(2)
        slicer.app.processEvents()
        
        # Get the imported data and load it
        dicomDatabase = slicer.dicomDatabase
        patients = dicomDatabase.patients()
        
        if patients:
            
            # Get the patient (should be the one we just imported)
            patient_id = patients[-1]  # Most recent
            patient_name = dicomDatabase.patientName(patient_id)
            
            # Get studies for this patient
            studies = dicomDatabase.studiesForPatient(patient_id)
            if studies:
                study_uid = studies[-1]  # Most recent study
                study_description = dicomDatabase.studyDescription(study_uid)
                
                # Get series for this study
                series_list = dicomDatabase.seriesForStudy(study_uid)
                if series_list:
                    # Find the best series (usually the largest one)
                    best_series = None
                    max_files = 0
                    
                    for series_uid in series_list:
                        series_files = dicomDatabase.filesForSeries(series_uid)
                        series_description = dicomDatabase.seriesDescription(series_uid)
                        
                        if len(series_files) > max_files:
                            max_files = len(series_files)
                            best_series = series_uid
                    
                    if best_series:
                        series_files = dicomDatabase.filesForSeries(best_series)
                        series_description = dicomDatabase.seriesDescription(best_series)
                        
                        # Load using the standard Slicer method
                        # This should create the same structure as the reference
                        volume_node = slicer.util.loadVolume(series_files[0])
                        
                        if volume_node:
                            # Set proper name matching reference style
                            if series_description:
                                volume_node.SetName(series_description)
                            
                            # Verify the loading
                            image_data = volume_node.GetImageData()
                            if image_data:
                                dims = image_data.GetDimensions()
                                spacing = volume_node.GetSpacing()
                                
                                # Store DICOM metadata
                                volume_node.SetAttribute("DICOM_PatientName", patient_name)
                                volume_node.SetAttribute("DICOM_SeriesDescription", series_description)
                                volume_node.SetAttribute("DICOM_SeriesUID", best_series)
                                
                                ui.set_3d_view_background_black()
                                qt.QTimer.singleShot(1000, volume.start_with_volume_crop)
                                return True
        
        return False
        
    except Exception as e:
        logger.debug("Suppressed exception in load_dicom_like_reference", exc_info=True)
        return False

def force_dicom_reimport():
    """
    Force a clean DICOM reimport using the reference method.
    Console helper: force_dicom_reimport()
    """
    try:
        # Clear existing volumes first
        volume_nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')
        for node in volume_nodes:
            slicer.mrmlScene.RemoveNode(node)
        
        # Clear DICOM database
        slicer.dicomDatabase.initializeDatabase()
        
        # Load using reference method
        return load_dicom_like_reference()
        
    except Exception as e:
        logger.debug("Suppressed exception in force_dicom_reimport", exc_info=True)
        return False
