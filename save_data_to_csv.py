import csv
import sys
import datetime
import tkinter as tk
from tkinter import filedialog
# hi :)
# ------ Functions used to save the file -------

def select_directory():
    """Opens a dialog to select a directory, asks for a filename, and returns the full path. Cleans up the Tk window."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    try: # Code that might return or have errors goes in 'try'
        folder_selected = filedialog.askdirectory()

        if folder_selected:  # User selected a folder
            print("Selected directory:", folder_selected)
            name_of_file = input("Name the file: ")
            path = folder_selected + "/" + name_of_file + ".csv"
            return path

        else:  # User canceled
            return None

    finally:
        root.destroy() # Cleans up Tkinter window; prevents resource leaks.

def compile_data(speed, samples, date, angle_data, hlfb_data):
    data_points = len(encoder_data)
    input_data = [
        ["Inputs",          "",        "",],
        ["Speed (Hz)",      "Samples",  "Date"],
        [speed,             samples,    date],
        ["",               "",        "",],
        ["Data Collected",  "",        ""],
        ["Sample",          "Angle",    "HLFB"]
    ]

    for i in range(0,data_points):
        new_row = [i+1, angle_data[i], hlfb_data[i]]
        input_data.append(new_row)

    return input_data


# -------- Start of Program ---------

# Dummy data to test the code
operating_speed = 30
num_of_samples = 8
current_date = datetime.datetime.now()
encoder_data = [10,11,12,13,14]
motor_data = [20,21,22,23,24]

print("\n---- Saving Data to CSV ----\n")

file_path = select_directory()  # Run select directory function and store the file path

# Only proceed if a file path was returned
if file_path:
    try:
        # 1. Compile the data first
        data = compile_data(operating_speed, num_of_samples, current_date, encoder_data, motor_data)

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
    sys.exit()