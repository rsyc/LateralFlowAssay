import os
import re
import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QListView, QTreeView, QAbstractItemView
)


# ===================================================================
# NEW: Single dialog that lets you select MULTIPLE folders at once
# ===================================================================
def select_multiple_folders():
    dialog = QFileDialog()
    dialog.setWindowTitle("Select one or more folders (Ctrl+Click or Shift+Click to select multiple)")
    dialog.setFileMode(QFileDialog.Directory)
    dialog.setOption(QFileDialog.ShowDirsOnly, True)
    dialog.setOption(QFileDialog.DontUseNativeDialog, True)  # Required for multi-select to work

    # Enable multi-selection in the views
    list_view = dialog.findChild(QListView, "listView")
    if list_view:
        list_view.setSelectionMode(QAbstractItemView.MultiSelection)

    tree_view = dialog.findChild(QTreeView)
    if tree_view:
        tree_view.setSelectionMode(QAbstractItemView.MultiSelection)

    if dialog.exec_() == QFileDialog.Accepted:
        return dialog.selectedFiles()  # Returns list of folder paths
    return []


def natural_sort_key(name):
    """Natural sort: numbers are sorted numerically, not lexicographically."""
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', name)]


# ====================== MAIN PROCESSING ======================
def process_selected_files(selected_files):
    """
    selected_files: list of tuples (folder_path, filename)
    """
    if not selected_files:
        print("No CSV files were found in the selected folders. Exiting.")
        return

    total_processed = 0
    total_skipped = 0

    print(f"\nStarting to process {len(selected_files)} CSV file(s)...\n")

    for folder_path, filename in selected_files:
        full_path = os.path.join(folder_path, filename)

        # Extract visit# from the last part after final "_"
        name_without_ext, ext = os.path.splitext(filename)
        parts = name_without_ext.split('_')

        if len(parts) < 2:
            print(f"Skipping {filename} – no '_' separator found.")
            total_skipped += 1
            continue

        visit_part = parts[-1]                    # e.g. "visit1", "visit2", etc.
        new_name_without_ext = '_'.join(parts[:-1])
        new_filename = new_name_without_ext + ext
        new_full_path = os.path.join(folder_path, new_filename)

        # Safety check: don't overwrite existing file
        if os.path.exists(new_full_path):
            print(f" Skipping {filename} – target file '{new_filename}' already exists.")
            total_skipped += 1
            continue

        try:
            # Read CSV
            df = pd.read_csv(full_path)

            # Add new column "visit#" and fill all rows with the extracted value
            df['visit#'] = visit_part

            # Save with the new (cleaned) filename
            df.to_csv(new_full_path, index=False)

            # Remove the original file
            os.remove(full_path)

            print(f" Processed: {filename} → {new_filename}  |  visit# = {visit_part}")
            total_processed += 1

        except Exception as e:
            print(f" Error processing {filename}: {e}")
            total_skipped += 1

    print("\n Finished processing all files!")
    print(f"   • Successfully updated : {total_processed}")
    print(f"   • Skipped             : {total_skipped}")
    print("\n   Every processed CSV now has a 'visit#' column.")
    print("   Original filenames have been cleaned (last '_visitX' part removed).")


# ====================== MAIN SCRIPT ======================
def main():
    # Create QApplication if it doesn't exist yet
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    print("Opening multi-folder selection dialog...")
    selected_folder_paths = select_multiple_folders()

    if not selected_folder_paths:
        print("No folders selected. Exiting.")
        return

    print(f"\nYou selected {len(selected_folder_paths)} folder(s):")
    for folder in selected_folder_paths:
        print(f" • {folder}")

    # Collect all CSV files from the selected folders (one layer only)
    selected_files = []   # list of (folder_path, filename)

    for folder_path in selected_folder_paths:
        if not os.path.isdir(folder_path):
            print(f"Skipping invalid folder: {folder_path}")
            continue

        # Only top-level CSV files (no recursion into subfolders)
        csv_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.csv')]
        csv_files.sort(key=natural_sort_key)

        if not csv_files:
            print(f"No CSV files found in: {folder_path}")
            continue

        print(f"\nProcessing folder: {os.path.basename(folder_path)}")
        print(f"Found {len(csv_files)} CSV file(s):")

        for file in csv_files:
            selected_files.append((folder_path, file))
            print(f" → Added '{file}'")

    print(f"\nTotal files selected for processing: {len(selected_files)}\n")

    # Now do the actual work
    process_selected_files(selected_files)


if __name__ == "__main__":
    main()