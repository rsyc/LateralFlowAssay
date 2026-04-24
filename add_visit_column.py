import pandas as pd
from tkinter import Tk, filedialog, simpledialog, messagebox
import os

def add_visit_number_to_csvs():
    # Create root window and make sure dialogs appear on top
    root = Tk()
    root.withdraw()                    # Hide the empty main window
    root.attributes('-topmost', True)  # Force dialogs to appear on top (helps a lot on Windows)

    # Step 1: Select files FIRST
    messagebox.showinfo(
        title="Select CSV Files",
        message="Please select all the CSV files you want to update.\n\n"
                "Hold Ctrl (Windows) or Cmd (Mac) to select multiple files."
    )

    file_paths = filedialog.askopenfilenames(
        title="Select CSV Files",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        parent=root
    )

    if not file_paths:
        messagebox.showinfo("Cancelled", "No files were selected.")
        root.destroy()
        return

    # Step 2: Ask for Visit Number AFTER files are selected
    visit_number = simpledialog.askstring(
        title="Enter Visit Number",
        prompt="Enter the Visit Number for all selected files:\n"
               "(Example: Visit1, V2, Baseline, Follow-up3)",
        parent=root
    )

    if not visit_number or visit_number.strip() == "":
        messagebox.showwarning("Cancelled", "No visit number entered. Operation cancelled.")
        root.destroy()
        return

    visit_number = visit_number.strip()

    # Step 3: Process the files
    success_count = 0
    errors = []

    for file_path in file_paths:
        try:
            df = pd.read_csv(file_path)
            df['visit#'] = visit_number
            df.to_csv(file_path, index=False)

            print(f" Updated: {os.path.basename(file_path)}")
            success_count += 1

        except Exception as e:
            error_msg = f"{os.path.basename(file_path)} → {str(e)}"
            print(f" Failed: {error_msg}")
            errors.append(error_msg)

    # Final message
    summary = f" Operation completed!\n\n"
    summary += f"Files selected : {len(file_paths)}\n"
    summary += f"Successfully updated : {success_count}\n"
    summary += f"Visit number added : '{visit_number}'"

    if errors:
        summary += f"\n\n⚠️  {len(errors)} file(s) failed."

    messagebox.showinfo("Done", summary)

    root.destroy()


if __name__ == "__main__":
    add_visit_number_to_csvs()