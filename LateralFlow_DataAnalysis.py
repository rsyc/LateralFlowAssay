import os
import re
import pandas as pd
import sys
from PyQt5.QtWidgets import QApplication, QFileDialog
from pathlib import Path
import matplotlib.pyplot as plt
from itertools import cycle
from scipy.stats import linregress
import seaborn as sns # Optional: for nice default color palette
import numpy as np
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from sklearn.metrics import auc
from PyQt5.QtWidgets import QFileDialog, QListView, QTreeView, QAbstractItemView
from collections import defaultdict
#%matplotlib auto

def get_non_null_values(row):
    vals = [val for val in [row['source1_visit#'], 
                            row['source2_visit#'], 
                            row['source3_visit#']] 
            if pd.notna(val)]
    return set(vals)  # unique values

def custom_sort(item):
    key = item[0]
    
    # 1. Handle "Control_" priority
    if key.startswith("Control_"):
        return (0, 0)
    
    # 2. Extract number from keys like "50mM_"
    # Using \d+ matches the digits at the start of the string
    match = re.search(r'(\d+)', key)
    if match:
        return (1, int(match.group(1)))
    
    # 3. Fallback for any other unexpected keys
    return (2, key)
# ---- Define color and line-style cycles ----
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']  # default Matplotlib colors
line_styles = ['-', '--', '-.', ':']

color_cycle = cycle(colors)
linestyle_cycle = cycle(line_styles)

current_color = next(color_cycle)
current_linestyle = next(linestyle_cycle)

color_index = 0

def get_style():
    global current_color, current_linestyle, color_index

    # Use next color until exhausted
    if color_index < len(colors):
        style = dict(color=colors[color_index], linestyle=current_linestyle)
        color_index += 1
    else:
        # Reset color index and move to next linestyle
        color_index = 0
        current_linestyle = next(linestyle_cycle)
        style = dict(color=colors[color_index], linestyle=current_linestyle)
        color_index += 1

    return style

# ===================================================================
# NEW: Single dialog that lets you select MULTIPLE folders at once
# ===================================================================
def select_multiple_folders():
    dialog = QFileDialog()
    dialog.setWindowTitle("Select one or more folders (Ctrl+Click or Shift+Click to select multiple)")
    dialog.setFileMode(QFileDialog.Directory)
    dialog.setOption(QFileDialog.ShowDirsOnly, True)
    dialog.setOption(QFileDialog.DontUseNativeDialog, True)   # ← This is required for multi-select to work
    
    # Enable multi-selection in the views
    list_view = dialog.findChild(QListView, "listView")
    if list_view:
        list_view.setSelectionMode(QAbstractItemView.MultiSelection)
    
    tree_view = dialog.findChild(QTreeView)
    if tree_view:
        tree_view.setSelectionMode(QAbstractItemView.MultiSelection)
    
    if dialog.exec_() == QFileDialog.Accepted:
        return dialog.selectedFiles()   # Returns list of folder paths
    return []


def main():
    selected_files = []  # List to store tuples of (folder_path, file_name)
    # Create QApplication once
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    # while True:
    #     # Step 1: Choose a folder
    #     # folder_path = input("Enter the path to the folder (or 'done' to finish selection, 'q' to quit): ").strip()
        
    #     folder_path = QFileDialog.getExistingDirectory(
    #         None,
    #         "Select a folder",
    #         ""   # starting directory ("" = default)
    #     )
        
    #     if folder_path:
    #         print("Selected folder:", folder_path)
    #     else:
    #         print("No folder selected")

    #     # if folder_path.lower() == 'q':
    #     #     print("Exiting the program.")
    #     #     return
    #     # elif folder_path.lower() == 'done':
    #     #     print("Selection complete.")
    #     #     break
        
    #     if not os.path.isdir(folder_path):
    #         print("Invalid folder path. Please try again.")
    #         continue
        
    #     # Step 2: List CSV files in the folder
    #     #csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    #     csv_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.csv')]
    #     csv_files.sort(key=natural_sort_key)
    #     if not csv_files:
    #         print("No CSV files found in the folder. Please choose another folder.")
    #         continue
        
    #     print("\nAvailable CSV files in " + folder_path + ":")
    #     for idx, file in enumerate(csv_files, 1):
    #         print(f"{idx}. {file}")
        
    #     # Step 3: Allow selecting multiple files (comma-separated numbers)
    #     choices_input = input("Enter the numbers of the CSV files to select (comma-separated, e.g., 1,3,5), or 'all' for all, or '0' to skip: ").strip()
    #     if choices_input == '0':
    #         continue
        
    #     if choices_input.lower() == 'all':
    #         selected = csv_files
    #     else:
    #         try:
    #             choices = [int(c.strip()) for c in choices_input.split(',') if c.strip()]
    #             selected = [csv_files[i-1] for i in choices if 1 <= i <= len(csv_files)]
    #         except (ValueError, IndexError):
    #             print("Invalid input. Please enter valid numbers.")
    #             continue
        
    #     # Add selected files to the list
    #     for file in selected:
    #         selected_files.append((folder_path, file))
    #         print(f"Added '{file}' from '{folder_path}' to selection.")
        
    #     print(f"\nCurrent selection: {len(selected_files)} files.")
        
    #     # After adding files (or even if none were added this round)
    #     more = input("\nAdd files from another folder? (y/n): ").strip().lower()
    #     if more in ('n', 'no', '0', ''):
    #         print("\nFinished selecting. Reading files...")
    #         break
    
    # if not selected_files:
    #     print("No files selected. Exiting.")
    #     return
    
    
    print("Opening folder selection dialog...")
    selected_folder_paths = select_multiple_folders()
    
    if not selected_folder_paths:
        print("No folders selected. Exiting.")
        return
    
    print(f"\n You selected {len(selected_folder_paths)} folder(s):")
    for folder in selected_folder_paths:
        print(f"   • {folder}")
    
    # ===================================================================
    # For every selected folder → automatically read ALL CSV files inside it
    # ===================================================================
    for folder_path in selected_folder_paths:
        if not os.path.isdir(folder_path):
            print(f"  Skipping invalid folder: {folder_path}")
            continue
        
        # Read only CSV files in this folder (one layer deep - no subfolders)
        csv_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.csv')]
        csv_files.sort(key=natural_sort_key)
        
        if not csv_files:
            print(f"   No CSV files found in: {folder_path}")
            continue
        
        print(f"\n Processing folder: {folder_path}")
        print(f"   Found {len(csv_files)} CSV file(s):")
        
        for file in csv_files:
            selected_files.append((folder_path, file))
            print(f"      → Added '{file}'")
    
    print(f"\n Total files selected for analysis: {len(selected_files)}\n")
    
    # Final safety check
    if not selected_files:
        print("No CSV files were found in the selected folders. Exiting.")
        return
    
    
    # Step 4: Read all selected files
    dataframes = {}
    key_counts = {}
    for folder, file in selected_files:
        file_path = os.path.join(folder, file)
        try:
            df = pd.read_csv(file_path)
            p = Path(file)
            # Remove the extension (.csv)
            name_without_ext = os.path.splitext(p)[0]
            parts = name_without_ext.rsplit('_', 2) 
            base_key = "_".join(parts[-2:])  #f"{os.path.basename(folder)}_{file}"  # Unique key: folder_name_file.csv
            # ---- Make key unique if repeated ----
            if base_key not in key_counts:
                key_counts[base_key] = 0
                key = f"{base_key}"
            else:
                key_counts[base_key] += 1
                key = f"{base_key}_{key_counts[base_key]}"
            # key_counts[base_key] += 1
            # if key_counts[base_key] == 1:
            #     key = base_key
            # else:
            #     key = f"{base_key}_{key_counts[base_key]}"
            dataframes[key] = df
            print(f"Successfully read '{file}' from '{folder}'.")
        except Exception as e:
            print(f"Error reading '{file}' from '{folder}': {e}")
    
    # Step 5: Perform analysis on all dataframes (placeholder - customize as needed)
    for key, df in dataframes.items():
        print(f"\nAnalysis for {key}:")
        print("DataFrame head:")
        print(df.head())
        print("\nDataFrame description:")
        print(df.describe())
    
    return dataframes

def natural_sort_key(name):
    # Split on numbers → sort numbers as int, text as str
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', name)]

if __name__ == "__main__":
    All_data = main()
    # Iterate and remove rows with 0
    for name, df in All_data.items():
        # Create a boolean mask: True for non-zero values across any column in the row
        # The .all(axis=1) ensures that the entire row is kept only if all elements are non-zero.
        mask = (df != 0).all(axis=1)
        
        # Apply the mask and update the dictionary with the cleaned DataFrame
        All_data[name] = df[mask].copy()
   
    
   
    new_dict = {}
    # grouped_keys = {}
    grouped = defaultdict(list)
    
    # Group keys by the first two parts (e.g., "Part1_Part2")
    for key, df in All_data.items():
        # Splitting by underscore and taking first two elements
        parts = key.split('_')
        prefix = '_'.join(parts[:2]) if len(parts) >= 2 else parts[0]
        
        # if prefix not in grouped_keys:
        #     grouped_keys[prefix] = []
        # grouped_keys[prefix].append(key) 
        # Get visit# from the dataframe (should be the same for all rows in one df)
        if 'visit#' in df.columns:
            visit_values = df['visit#'].dropna().unique()
            visit = visit_values[0] if len(visit_values) > 0 else "unknown"
        else:
            visit = "unknown"
        
        group_key = f"{prefix}_{visit}"
        grouped[group_key].append((key, df))
   
    # Process each group for averaging or direct copying
    
    # for prefix, keys in grouped_keys.items():
    #     if len(keys) > 1:
    #         # Group has multiple files: Calculate Mean
    #         combined_group = []
            
    #         for k in keys:
    #             df = All_data[k].copy()
    #             # Ensure the first column is time and rounded
    #             time_col = df.columns[0]
    #             df[time_col] = df[time_col].astype(int) #.round()
    #             combined_group.append(df)
            
    #         # Merge all DataFrames in this group on the time column
    #         merged_df = None
    #         for i, df in enumerate(combined_group):
    #             # Copy and rename every column except "time" to avoid conflicts
    #             df_renamed = df.copy()
    #             rename_dict = {col: f"source{i+1}_{col}" 
    #                            for col in df.columns if col != "time_s"}
    #             df_renamed.rename(columns=rename_dict, inplace=True)
                
    #             if merged_df is None:
    #                 merged_df = df_renamed
    #             else:
    #                 merged_df = pd.merge(merged_df, df_renamed, on="time_s", how="outer")
            
                        
    #         # Fill missing values with 0 (as you requested)
    #         merged_df.fillna(0, inplace=True)

    #         # Sort by time and reset index for a clean result
    #         merged_df = merged_df.sort_values(by="time_s").reset_index(drop=True)

    #         # === AVERAGE OVER NON-ZERO VALUES (vectorized) ===
    #         value_columns = [col for col in merged_df.columns if col != "time_s"]

    #         # Sum of non-zero values
    #         non_zero_mask = merged_df[value_columns] != 0
    #         sum_non_zero = (merged_df[value_columns] * non_zero_mask).sum(axis=1)

    #         # Count of non-zero values
    #         count_non_zero = non_zero_mask.sum(axis=1)

    #         # Average = sum / count (if count == 0 we return 0)
    #         merged_df["mean_length"] = sum_non_zero / count_non_zero.replace(0, 1) 
    #         merged_df["std_length"] = (merged_df[value_columns] * non_zero_mask).std(axis=1)
    #         # merged_df = combined_group[0]
    #         # time_col = merged_df.columns[0]
    #         # for i in range(1, len(combined_group)):
    #         #     merged_df = pd.merge(merged_df, combined_group[i], on=time_col, how='outer')
            
    #         # # Sort by time and reset the index to keep it clean
    #         # merged_df = merged_df.sort_values(by='time_s').reset_index(drop=True)
    #         # # Calculate mean across all 'length' columns (excluding the time column)
    #         # # We select all columns except the first one (time) to calculate the mean
    #         # time_col_name = merged_df.columns[0]
    #         # data_cols = merged_df.columns[1:]
            
    #         # avg_df = pd.DataFrame()
    #         # avg_df[time_col_name] = merged_df[time_col_name]
    #         # avg_df['mean_length'] = merged_df[data_cols].mean(axis=1)
            
    #         new_dict[f"{prefix}_averaged"] = merged_df # avg_df
    #     else:
    #         # Only one file: Add it to the new dictionary as is
    #         new_dict[keys[0]] = All_data[keys[0]]
   
    for group_key, items in grouped.items():
        if len(items) == 1:
            # Single file → keep as is (already has clean 'visit#')
            original_key, df = items[0]
            df = df.copy()
            
            # Find any column that contains 'visit#'
            visit_cols = [c for c in df.columns if 'visit#' in str(c)]
            
            if visit_cols:
                # Take the first one (should be the only one)
                visit_col = visit_cols[0]
                if visit_col != 'visit#':
                    df['visit_number'] = df[visit_col]
                    # Drop all other visit-related columns
                    df = df.drop(columns=visit_cols)
                # else: already has clean 'visit#' → do nothing
            else:
                # No visit column at all (very rare now)
                df['visit_number'] = 'unknown'
            
            new_dict[original_key] = df
            print(f"Single file → kept with visit#: {original_key} ({group_key})")
            continue

        # Multiple files with same prefix + same visit# → merge and average
        print(f"Averaging {len(items)} files for group: {group_key}")

        combined_group = []
        for i, (orig_key, df) in enumerate(items):
            df = df.copy()
            
            # Ensure time column is integer
            time_col = df.columns[0]          # assuming first column is time_s
            if time_col != "time_s":
                print(f"Warning: Expected time_s but found {time_col} in {orig_key}")
            
            df[time_col] = df[time_col].astype(int)
            
            # Rename columns to avoid conflicts (except time and visit#)
            rename_dict = {}
            for col in df.columns:
                if col not in ["time_s"] and 'visit#' not in str(col):
                    rename_dict[col] = f"source{i+1}_{col}"
            
            df_renamed = df.rename(columns=rename_dict)
            combined_group.append(df_renamed)

        # Merge all on time_s (outer join)
        merged_df = None
        for df_renamed in combined_group:
            if merged_df is None:
                merged_df = df_renamed
            else:
                merged_df = pd.merge(merged_df, df_renamed, on="time_s", how="outer")

        # Fill missing values with 0
        merged_df.fillna(0, inplace=True)

        # === CRITICAL FIX: Consolidate all visit# columns into ONE clean 'visit#' ===
        visit_cols = [col for col in merged_df.columns if 'visit#' in str(col)]
        if visit_cols:
            # All visit# values should be identical (because we grouped by visit)
            # Take the first non-null value across the columns
            merged_df['visit_number'] = merged_df[visit_cols].bfill(axis=1).iloc[:, 0]
            # Drop the suffixed columns (visit#_x, visit#_y, ...)
            merged_df = merged_df.drop(columns=visit_cols)

        # Sort by time
        merged_df = merged_df.sort_values(by="time_s").reset_index(drop=True)

        # === Vectorized non-zero mean and std ===
        # value_columns = [col for col in merged_df.columns 
        #                 if col not in ["time_s", "visit#"] 
        #                 and not col.startswith('source') or '_' in col]  # rough filter

        # Better: all columns that came from sources (they start with source1_, source2_, etc.)
        source_value_cols = [col for col in merged_df.columns 
                            if col.startswith('source') and '_area_cm2' in col]

        non_zero_mask = merged_df[source_value_cols] != 0
        
        sum_non_zero = (merged_df[source_value_cols] * non_zero_mask).sum(axis=1)
        count_non_zero = non_zero_mask.sum(axis=1)

        merged_df["mean_length"] = sum_non_zero / count_non_zero.replace(0, 1)
        merged_df["std_length"] = (merged_df[source_value_cols] * non_zero_mask).std(axis=1)

        # Optional: drop the sourceX_ columns if you don't need them anymore
        # merged_df = merged_df.drop(columns=source_value_cols)

        new_dict[group_key] = merged_df

    print(f"\n Processing complete. Created {len(new_dict)} final DataFrames.")
    
    
    
    #================================PLOT SECTION==============================================
    
   #  #---------PLOT------------
   #  # Create a figure and a single axes object
   #  fig, ax = plt.subplots(figsize=(10, 6))
    
   #  # Define the maximum row number to plot (e.g., 50)
   #  max_rows = 30
    
   #  # Loop through the dictionary and plot on the same axes
   #  for name, df in sorted(new_dict.items(), key=custom_sort): # Sort the items and convert back to a dictionary
   #      # Use the 'ax' parameter to plot on the same axes.
   #      # The 'label' parameter uses the dictionary key for the legend.
   #      style = get_style()
   #      df = df.iloc[:max_rows]
   #      if 'mean_length' in df.columns:
   #          # df.plot(x='time_s', y='mean_length', yerr='std_length', ax=ax, label=name, **style)
   #          df.plot(x='time_s', y='mean_length', ax=ax, label=name, **style)
   #      else:
   #          df.plot(x='time_s', y='length_cm', ax=ax, label=name, **style)
     
   #  # Customize and display the plot
   #  ax.tick_params(axis='both', which='major', labelsize=20)
   #  # ax.set_title('CalCl2 Concentrations', fontsize=20)
   #  ax.set_title('Drug Concentrations')
   #  ax.set_xlabel('Time (s)', fontsize=20)
   #  # ax.set_ylabel('Travelled length (cm)')
   #  ax.set_ylabel('Area expansion (cm$^2$)', fontsize=20)
   #  ax.legend(title='',fontsize=14)
   #  plt.grid(True)
   #  plt.show()
    
    
    
    
    
   # #------------------Rojan-------------------------------
   #  # Create a figure and a single axes object
   #  fig, ax = plt.subplots(figsize=(10, 6))
   #  exclude_str = 'Domenica'

   #  # Filter: Keep keys that DO NOT contain 'Domenica' so it just plots my results
   #  filtered_dict = {k: v for k, v in new_dict.items() if exclude_str not in k}
    
   #  # Loop through the dictionary and plot on the same axes
   #  for name, df in sorted(filtered_dict.items(), key=custom_sort): # Sort the items and convert back to a dictionary
   #      # Use the 'ax' parameter to plot on the same axes.
   #      # The 'label' parameter uses the dictionary key for the legend.
   #      style = get_style()
   #      df = df.iloc[:max_rows]
   #      if 'mean_length' in df.columns:
   #          # df.plot(x='time_s', y='mean_length', yerr='std_length',  ax=ax, label=name, **style)
   #          df.plot(x='time_s', y='mean_length', ax=ax, label=name, **style)
   #      else:
   #          df.plot(x='time_s', y='length_cm', ax=ax, label=name, **style)
     
   #  # Customize and display the plot
   #  ax.tick_params(axis='both', which='major', labelsize=20)
   #  # ax.set_title('CalCl2 Concentrations', fontsize=20)
   #  ax.set_title('Drug Concentrations')
   #  ax.set_xlabel('Time (s)', fontsize=20)
   #  # ax.set_ylabel('Travelled length (cm)')
   #  ax.set_ylabel('Area expansion (cm$^2$)', fontsize=20)
   #  ax.legend(title='',fontsize=14)
   #  plt.grid(True)
   #  plt.show()
    

    
   #  #------------------------Domenica------------------------
   #  # Find common keys
   #  shared_keys = set(new_dict.keys()) & set(filtered_dict.keys())
    
   #  # Create the new dictionary with unshared dataframes to plot only Domenica's results
   #  unshared_dataframes = { k: v for k, v in new_dict.items() if k not in shared_keys }
   #  fig, ax = plt.subplots(figsize=(10, 6))
   #  # Loop through the dictionary and plot on the same axes
   #  for name, df in sorted(unshared_dataframes.items(), key=custom_sort): # Sort the items and convert back to a dictionary
   #      # Use the 'ax' parameter to plot on the same axes.
   #      # The 'label' parameter uses the dictionary key for the legend.
   #      style = get_style()
   #      df = df.iloc[:max_rows]
   #      if 'mean_length' in df.columns:
   #          # df.plot(x='time_s', y='mean_length', yerr='std_length', ax=ax, label=name, **style)
   #          df.plot(x='time_s', y='mean_length', ax=ax, label=name, **style)
   #      else:
   #          df.plot(x='time_s', y='length_cm', ax=ax, label=name, **style)
     
   #  # Customize and display the plot
   #  ax.tick_params(axis='both', which='major', labelsize=20)
   #  # ax.set_title('CalCl2 Concentrations', fontsize=20)
   #  ax.set_title('Drug Concentrations')
   #  ax.set_xlabel('Time (s)', fontsize=20)
   #  # ax.set_ylabel('Travelled length (cm)')
   #  ax.set_ylabel('Area expansion (cm$^2$)', fontsize=20)
   #  ax.legend(title='',fontsize=14)
   #  plt.grid(True)
   #  plt.show()
    
    
    
    
    
    
    
   #  #---------PLOT------------
   #  # Define the maximum row number to plot (e.g., 50)
   #  max_rows = 30
   #  # Loop through the dictionary and plot on the same axes
   #  # Create the plot
   #  fig, ax = plt.subplots(figsize=(10, 7))
    
   #  # Define a color palette (optional, but helpful)
   #  colors = sns.color_palette('husl', n_colors=len(new_dict))
   #  color_map = dict(zip(new_dict.keys(), colors))
   #  for name, df in new_dict.items():
   #      # Prepare data for plotting
   #      df = df.iloc[:max_rows]
   #      x_values = df['time_s']
   #      # Calculate y-squared
   #      if 'mean_length' in df.columns: #df.columns[1]!='mean_length':
   #         y_squared = df['mean_length'] ** 2             
   #      else:
   #         y_squared = df['length_cm'] ** 2 
        
   #      # Plot scatter points
   #      ax.scatter(x_values, y_squared, label=f'{name} Data', color=color_map[name], alpha=0.6, edgecolors='k')
        
   #      # Perform linear regression on the (x, y^2) data
   #      # linregress returns slope, intercept, r_value, p_value, std_err
   #      slope, intercept, r_value, p_value, std_err = linregress(x_values, y_squared)
        
   #      # Plot the regression line
   #      # Create x-sequence for the line
   #      x_seq = np.linspace(x_values.min(), x_values.max(), 100)
   #      ax.plot(x_seq, slope * x_seq + intercept, color=color_map[name], linestyle='--', lw=2, label=f'{name} Regression (R²={r_value**2:.2f})')
   #      # Increase font size for both x and y axis tick labels
   #      ax.tick_params(axis='both', which='major', labelsize=20)
        
   #  # Add titles and labels
   #  #ax.set_title(f'Scatter Plot for {name} with Regression Line')
   #  ax.set_xlabel('Time (s)', fontsize=20)
   #  ax.set_ylabel('Travel Distance$^2$ (cm$^2$)', fontsize=20)
   #  ax.legend(title='Drug concentration (mM)', fontsize=12)
            
   #  # Optional: Annotate with R-squared value
   #  ax.annotate(f'$R^2$: {r_value**2:.2f}', xy=(0.05, 0.9), xycoords='axes fraction')
            
   #  # Display the plot
   #  plt.show()




    # ------------------------Statistical Analysis--------------------------
    # 1. One-Way ANOVA
    # ================================================================
    # STEP 1: RESHAPE YOUR DICTIONARY INTO LONG FORMAT (RAW REPLICATES)
    # ================================================================
    
    case_data = new_dict #filtered_dict  
    
    long_rows = []
    
    for case_name, df in case_data.items():
        # Find all replicate columns (area_1, area_2, ..., area_6)
        area_cols = [col for col in df.columns if col.endswith('_area_cm2')]
        # if not area_cols:
        #     print(f"Warning: No area columns found in {case_name}")
        # continue
        
        # Melt them into long format
        melted = df.melt(
            id_vars=['time_s', 'visit_number'],
            value_vars=area_cols,
            var_name='replicate',
            value_name='area'
        )
        
        # Drop any NaN measurements (some cases may have only 3-4 replicates)
        melted = melted.dropna(subset=['area'])
        
        # Add case identifier
        melted['case'] = case_name
        
        # Keep only the columns we need
        long_rows.append(melted[['time_s', 'visit_number', 'case', 'area', 'replicate']])
        
    
    # Combine everything
    long_df = pd.concat(long_rows, ignore_index=True)
    
    # Rename for convenience
    long_df = long_df.rename(columns={'time_s': 'time'})
    
    print(f"Reshaped data: {len(long_df)} raw measurements across {long_df['case'].nunique()} cases")
    print(long_df.head())
    
    # ================================================================
    # OPTIONAL: Round time if values are only slightly different
    # (highly recommended if times are close but not identical)
    # ================================================================
    # Choose the rounding precision that makes sense for your experiment
    # e.g. round(1) = nearest 0.1 s, round(0) = nearest second
    long_df['time_rounded'] = long_df['time'].round(1)   # ← change the number if needed
    time_column_to_use = 'time' #'time_rounded'          # or 'time' if you want exact match
    
    # # ================================================================
    # # STEP 2: ONE-WAY ANOVA AT EVERY TIME POINT (with Bonferroni correction)
    # # ================================================================
    # unique_times = sorted(long_df[time_column_to_use].unique())
    # unique_cases = long_df['case'].unique()
    
    # p_values_raw = {}
    # group_counts = {}
    
    # for t in unique_times:
    #     group_values = []
    #     for case in unique_cases:
    #         vals = long_df[
    #             (long_df[time_column_to_use] == t) & 
    #             (long_df['case'] == case)
    #         ]['area'].values
            
    #         if len(vals) >= 2:          # need at least 2 replicates for variance
    #             group_values.append(vals)
    #             group_counts[t] = group_counts.get(t, 0) + 1
        
    #     if len(group_values) >= 2:
    #         f_stat, p_val = stats.f_oneway(*group_values)
    #         p_values_raw[t] = p_val
    #     else:
    #         p_values_raw[t] = np.nan
    
    # # Bonferroni correction
    # n_tests = sum(1 for p in p_values_raw.values() if not np.isnan(p))
    # corrected_p = {
    #     t: p * n_tests if not np.isnan(p) else np.nan 
    #     for t, p in p_values_raw.items()
    # }
    
    # # print("\n=== ANOVA RESULTS (differences between cases at each time) ===")
    # # print(f"{'Time':>10} | {'Raw p-value':>12} | {'Corrected p':>12} | Significant?")
    # # for t in unique_times:
    # #     p_raw = p_values_raw[t]
    # #     p_corr = corrected_p[t]
    # #     sig = "YES" if (not np.isnan(p_corr) and p_corr < 0.05) else "no"
    # #     print(f"{t:10.2f} | {p_raw:12.4f} | {p_corr:12.4f} | {sig:>10}")
    
    # # ================================================================
    # # OPTIONAL: Post-hoc Tukey HSD at a specific significant time
    # # ================================================================
    # # Change example_time to any time where corrected p < 0.05
    # example_time = unique_times[24] if unique_times else None
    # if example_time is not None and not np.isnan(corrected_p.get(example_time, np.nan)):
    #     data_at_t = long_df[long_df[time_column_to_use] == example_time]
    #     tukey = pairwise_tukeyhsd(
    #         endog=data_at_t['area'],
    #         groups=data_at_t['case'],
    #         alpha=0.05
    #     )
    #     print(f"\nTukey HSD post-hoc at time ≈ {example_time}")
    #     print(tukey)
        
        
        
        
    # # 2. AUC
    # # ================================================================
    # # STEP 1: Find the shortest maximum time across all cases
    # # ================================================================
    # data_to_analyse = new_dict # unshared_dataframes   #= filtered_dict
    # max_times = [df['time_s'].max() for df in data_to_analyse.values()]
    # common_end_time = 250 #min(max_times)
    # common_start_time = 35
    
    # print(f"Truncating all cases to {common_end_time} seconds for fair comparison.")
    
    # all_auc_data = []
    
    # for case_name, df in data_to_analyse.items():
    #     # Only keep data up to the common end time
    #     df_clipped = df[df['time_s'].between(common_start_time,common_end_time)].copy()
        
    #     area_cols = [c for c in df_clipped.columns if c.endswith('_area_cm2')]
        
    #     for col in area_cols:
    #         clean_df = df_clipped[['time_s', col]].dropna()
    #         if not clean_df.empty:
    #             # Calculate AUC for the clipped window
    #             case_auc = auc(clean_df['time_s'], clean_df[col])
    #             all_auc_data.append({'Case': case_name, 'AUC': case_auc})
    
    # stats_df = pd.DataFrame(all_auc_data)
    
    # # ================================================================
    # # STEP 2: Run One-Way ANOVA
    # # ================================================================
    # groups = [group['AUC'].values for name, group in stats_df.groupby('Case')]
    # f_stat, p_val = stats.f_oneway(*groups)
    
    # print(f"ANOVA Result: F={f_stat:.3f}, p-value={p_val:.4f}")
    
    # # ================================================================
    # # STEP 3: Run Tukey HSD if significant
    # # ================================================================
    # if p_val < 0.05:
    #     tukey = pairwise_tukeyhsd(endog=stats_df['AUC'], groups=stats_df['Case'], alpha=0.05)
    #     print(tukey)        
    # # Convert Results to a Pandas DataFrame
    # tukey_data = pd.DataFrame(data=tukey._results_table.data[1:], 
    #                           columns=tukey._results_table.data[0])
    
    # #  Write Results to Excel
    # output_file = 'Heparin_Protamin_Tukey_Results.xlsx' # 'Citrate_CaCl2_Tukey_Results.xlsx'
    # tukey_data.to_excel(output_file, index=False, sheet_name='Tukey_HSD')
    
    # print(f"Tukey results successfully written to {output_file}")
    
    
    
    
    
    # Write out the data into csv to be used in R code for further analysis and NLME
    long_df2=long_df.copy()
    long_df2 = long_df2.drop(columns=['time_rounded'])
    long_df2['replicate'] = long_df2['replicate'].str.replace('_area_cm2', '', regex=True)
    long_df2['case'] = long_df2['case'].str.replace('_averaged', '', regex=True)
    
    # Create a new 'Experimenter' column based on partial text match in column case
    long_df2['Experimenter'] = 'Exp1'
    long_df2.loc[long_df2['case'].str.contains('Domenica'),'Experimenter'] = 'Exp2'
    long_df2.loc[long_df2['case'].str.contains('Dara'),'Experimenter'] = 'Exp3'
    # Removing the name of Experimenters from the "case" column to make iit solely include the drug dosage value.
    long_df2['case'] = long_df2['case'].str.replace('Domenica', '', regex=True)
    long_df2['case'] = long_df2['case'].str.replace('Dara', '', regex=True)
    
    
    # separate CaCl2/protamine dose from CBD leve and have them in two separate dolumns:
    # if all(long_df2['case'].str.contains('mM')):
    #     long_df2[['case', 'CBD']] = long_df2['case'].str.split('mM', n=1, expand=True) #.str.rpartition('mM', expand=True, n=1)
    #     long_df2['case'] = long_df2['case'].astype(str) + 'mM'
    # elif all(long_df2['case'].str.contains('ugml')):
    #     long_df2[['case', 'CBD']] = long_df2['case'].str.split('mM', n=1, expand=True) #.str.rpartition('ugml', expand=True)
    #     long_df2['case'] = long_df2['case'].astype(str) + 'mM'
    
    # Extract CBD level (if present) or set "NoCBD"
    # This robustly detects CBD-related text anywhere in the remaining case string
    cbd_pattern = r'(VeryHighCBD|HighCBD|MediumCBD|LowCBD|ControlCBD)'   # add more patterns if you use different names
    
    long_df2['CBD'] = long_df2['case'].str.extract(cbd_pattern, expand=False)
    
    # If no CBD found → "NoCBD"
    long_df2['CBD'] = long_df2['CBD'].fillna('NoCBD')
    
    # Remove the CBD part from the 'case' column
    long_df2['case'] = long_df2['case'].str.replace(cbd_pattern, '', regex=True)
    
    
    
    # Create a new 'ExStatuse' column based on partial text match in column "case"
    long_df2['ExStatuse'] = 'REST'
    # if 'CBD' in long_df2.columns: 
    #     long_df2.loc[long_df2['CBD'].str.contains('Exercise'),'ExStatuse'] = 'Exercise'
    #     long_df2.loc[long_df2['CBD'].str.contains('Exrcise'),'ExStatuse'] = 'Exercise'
    #     # Removing the name of Experimenters from the "case" column to make iit solely include the drug dosage value.
    #     long_df2['CBD'] = long_df2['CBD'].str.replace('_Exercise', '', regex=True)
    #     long_df2['CBD'] = long_df2['CBD'].str.replace('_Exrcise', '', regex=True)
    #     long_df2['CBD'] = long_df2['CBD'].str.replace('_REST', '', regex=True)
    # else:             
    #     long_df2.loc[long_df2['case'].str.contains('Exercise'),'ExStatuse'] = 'Exercise'
    #     long_df2.loc[long_df2['case'].str.contains('Exrcise'),'ExStatuse'] = 'Exercise'
    #     # Removing the name of Experimenters from the "case" column to make iit solely include the drug dosage value.
    #     long_df2['case'] = long_df2['case'].str.replace('_Exercise', '', regex=True)
    #     long_df2['case'] = long_df2['case'].str.replace('_Exrcise', '', regex=True)
    #     long_df2['case'] = long_df2['case'].str.replace('_REST', '', regex=True)
    long_df2.loc[long_df2['case'].str.contains('Exercise'),'ExStatuse'] = 'Exercise'
    long_df2.loc[long_df2['case'].str.contains('Exrcise'),'ExStatuse'] = 'Exercise'
    # Removing the name of Experimenters from the "case" column to make iit solely include the drug dosage value.
    long_df2['case'] = long_df2['case'].str.replace('_Exercise', '', regex=True)
    long_df2['case'] = long_df2['case'].str.replace('_Exrcise', '', regex=True)
    long_df2['case'] = long_df2['case'].str.replace('_REST', '', regex=True)
    
    long_df2['case'] = long_df2['case'].str.replace(r'_visit(\d+)$', '', regex=True) # captures the number after _visit
    # Write the DataFrame to a CSV file 
    # long_df2.to_csv('circular_blood_dispersion_results/Citrate_CaCl2_CBD.csv', index=False)
    # long_df2.to_csv('circular_blood_dispersion_results/Only_Heparin_Protamin.csv', index=False)
    long_df2.to_csv('C:/Users/rojan/Documents/FSU/codes/PythonCodes/LatteralFlowAssay/circular_blood_dispersion_results/LateralFlow_DataAnalysis_Results/Citrate_5min-1minIncubation_28May2026.csv', index=False)