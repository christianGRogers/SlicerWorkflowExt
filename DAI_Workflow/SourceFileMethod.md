# Source File Method for Automatic DICOM Loading

## Overview

This method uses a simple text file in your user directory to automatically load DICOM data when the workflow module starts. This is much simpler and safer than command-line arguments.

## Setup Instructions

### 1. Create the Source File

Create a file named `source_slicer.txt` in your user directory:
```
C:\Users\chris\source_slicer.txt
```

### 2. Add Your DICOM Path

Edit the file to contain only the path to your DICOM folder (one line, no quotes needed):
```
G:\My Drive\Lawson\FOURDIX\FOURDIX\RATIB1\Cardiac 1CTA_CORONARY_ARTERIES_lowHR_TESTBOLUS (Adult)\CorCTALow  0.6  B10f 65%
```

### 3. Start Slicer Normally

Just start Slicer normally - no command-line arguments needed:
- Double-click Slicer icon
- Or use: `"C:\Users\chris\AppData\Local\slicer.org\Slicer 5.8.1\Slicer.exe"`

## How It Works

1. **Slicer starts** → Your workflow module opens automatically (as configured)
2. **Workflow checks** for `C:\Users\chris\source_slicer.txt`
3. **If file exists**: Reads the DICOM path and tries to load it automatically
4. **If successful**: Skips manual file selection, goes straight to workflow
5. **If failed**: Shows helpful error message with manual instructions

## Multiple Loading Methods

The system tries several methods to load your DICOM data:

1. **Direct folder loading** using `slicer.util.loadVolume()`
2. **File search** - finds `.dcm` files in the directory and loads them
3. **User guidance** - if all fail, shows clear instructions for manual loading

## Sample File Provided

I've created a sample `source_slicer.txt` file in the extension directory with your test path. Copy this to your user directory:

**From**: `C:\Users\chris\Documents\repos\SlicerWorkflowExt\DAI_Workflow\source_slicer.txt`
**To**: `C:\Users\chris\source_slicer.txt`

## Advantages of This Method

✅ **Simple**: Just edit a text file, no command-line complexity
✅ **Safe**: No infinite loops or recursive launching
✅ **Flexible**: Easy to change DICOM path anytime
✅ **Persistent**: Path stays until you change it
✅ **No arguments**: Start Slicer normally with any method
✅ **Error handling**: Clear feedback if path doesn't work

## Changing DICOM Data

To load different DICOM data:
1. Edit `C:\Users\chris\source_slicer.txt`
2. Replace the path with your new DICOM folder path
3. Restart Slicer

## Disabling Auto-Loading

To disable automatic loading:
1. Delete `C:\Users\chris\source_slicer.txt`
2. Or rename it to something else (e.g., `source_slicer_disabled.txt`)

## Troubleshooting

- **File not found**: Make sure the file is exactly `C:\Users\chris\source_slicer.txt`
- **Path not working**: Check that the DICOM folder path exists and contains DICOM files
- **Permission issues**: Make sure Slicer can read the DICOM folder
- **Multiple attempts**: The system only tries once per Slicer session to prevent loops