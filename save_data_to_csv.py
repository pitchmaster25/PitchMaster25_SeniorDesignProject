import csv
import sys
import datetime
# Use PySide6 file dialog instead of tkinter for consistency with the GUI
from PySide6.QtWidgets import QApplication, QFileDialog
# hi :)
# ------ Functions used to save the file -------

def select_directory():
    """Opens a dialog to select a directory, asks for a filename, and returns the full path. Cleans up the Tk window."""
    # QFileDialog needs a running QApplication. If one exists, reuse it;
    # otherwise create a temporary one for this dialog.
    app = QApplication.instance()
    created_app = False
    if app is None:
        app = QApplication([])
        created_app = True

    folder_selected = QFileDialog.getExistingDirectory(None, "Select Directory")

    if created_app:
        # Clean up the temporary app
        app.quit()

    if folder_selected:
        print("Selected directory:", folder_selected)
        name_of_file = input("Name the file: ")
        path = folder_selected + "/" + name_of_file + ".csv"
        return path
    return None

def compile_data(speed, samples, date, angle_data, hlfb_data, encoder_data=None):
    data_points = len(hlfb_data)
    input_data = [
        ["Inputs",          "",        "",],
        ["Speed (Hz)",      "Samples",  "Date"],
        [speed,             samples,    date],
        ["",               "",        "",],
        ["Data Collected",  "",        ""],
        ["Sample",          "Angle",    "HLFB"]
    ]

    if encoder_data:
        for i in range(0,data_points):
            new_row = [i+1, encoder_data[i], hlfb_data[i]]
            input_data.append(new_row)
    else:
        for i in range(0,data_points):
            new_row = [i+1, "Null", hlfb_data[i]]
            input_data.append(new_row)
    

    # If encoder data supplied, append it as an additional section
    if encoder_data:
        input_data.append(["", "", ""])  # spacer row
        input_data.append(["Encoder Data", "", ""])
        input_data.append(["Sample Index", "Encoder Value", ""])
        for idx, val in enumerate(encoder_data):
            input_data.append([idx + 1, val, ""])

    return input_data


# -------- Start of Program ---------
def save(operating_speed, angle_data, hlfb_data, encoder_data=None, file_path=None):
    """
    Save data to CSV. Signature matches callers in `main.py` and GUI:
        save(operating_speed, angle_data, hlfb_data, encoder_data)
    """
    num_of_samples = len(hlfb_data) if hlfb_data else 0
    current_date = datetime.datetime.now()

    print("\n---- Saving Data to CSV ----\n")

    # If a file_path is provided (e.g. from GUI), use it directly; otherwise prompt
    if file_path is None:
        file_path = select_directory()  # Run select directory function and store the file path

    # Only proceed if a file path was returned
    if file_path:
        try:
            # 1. Compile the data first
            data = compile_data(operating_speed, num_of_samples, current_date, angle_data, hlfb_data, encoder_data)

            # 2. Open the file to write
            with open(file_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(data)

            print(f"\nCSV file created successfully!")

        # --- Add specific error handling ---
        except PermissionError:
            print(f"\nError: You do not have permission to write to this file. Close the file if you currently have it open.")
            print(f"File path: {file_path}")
        except Exception as e:
            # This catches any other errors (e.g., from compile_data)
            print(f"\nAn unexpected error occurred: {e}")

    else: # If no directory was selected, end the program gracefully.
        print("No directory selected. Ending Program.")
