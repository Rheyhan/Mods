# Minecraft Mod Manager

A desktop GUI that syncs a Minecraft installation with a Google Cloud Storage bucket. It can:

- Download and update mods in the `mods` folder
- Download and update TACZ zip files in the `tacz` folder
- Replace `options.txt` with server-optimized settings
- Show progress and detailed activity logs

## What the app does

The app connects to a configured GCS bucket and keeps your local files in sync:

- **Fresh Install**: Deletes local `mods` and `tacz` folders, recreates them, then downloads all files plus `options.txt`.
- **Update**: Syncs `mods` and `tacz` with the bucket (downloads missing files, deletes obsolete local files).
- **Get Options**: Replaces your local `options.txt` with the version from the bucket.

## Requirements

- Windows
- Python 3.10+ (if running from source)
- `google-cloud-storage` installed
- A valid Google Cloud service account JSON (see Setup)

## Setup (from source)

1. Ask rhey for credentials to access the GCS bucket and replace the `hidden_key`
2. Install dependencies:

	- `pip install google-cloud-storage`

3. Run the app:

	- `python app.py`

## Usage

1. Click **Select Minecraft Directory** and choose your `.minecraft` folder.
2. Choose an action:
	- **Fresh Install** for a clean full download.
	- **Update** to sync changes.
	- **Get Options** to replace `options.txt`.

## Notes

- The app validates the selected folder by checking for a `versions` directory.
- All actions run in the background so the UI stays responsive.
- Logs and progress are displayed in the right panel.