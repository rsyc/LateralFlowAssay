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
#%matplotlib auto


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

def main():
    selected_files = []  # List to store tuples of (folder_path, file_name)
    
    while True:
        # Step 1: Choose a folder
        # folder_path = input("Enter the path to the folder (or 'done' to finish selection, 'q' to quit): ").strip()
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
        
        folder_path = QFileDialog.getExistingDirectory(
            None,
            "Select a folder",
            ""   # starting directory ("" = default)
        )
        
        if folder_path:
            print("Selected folder:", folder_path)
        else:
            print("No folder selected")

        # if folder_path.lower() == 'q':
        #     print("Exiting the program.")
        #     return
        # elif folder_path.lower() == 'done':
        #     print("Selection complete.")
        #     break
        
        if not os.path.isdir(folder_path):
            print("Invalid folder path. Please try again.")
            continue
        
        # Step 2: List CSV files in the folder
        #csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
        csv_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.csv')]
        csv_files.sort(key=natural_sort_key)
        if not csv_files:
            print("No CSV files found in the folder. Please choose another folder.")
            continue
        
        print("\nAvailable CSV files in " + folder_path + ":")
        for idx, file in enumerate(csv_files, 1):
            print(f"{idx}. {file}")
        
        # Step 3: Allow selecting multiple files (comma-separated numbers)
        choices_input = input("Enter the numbers of the CSV files to select (comma-separated, e.g., 1,3,5), or 'all' for all, or '0' to skip: ").strip()
        if choices_input == '0':
            continue
        
        if choices_input.lower() == 'all':
            selected = csv_files
        else:
            try:
                choices = [int(c.strip()) for c in choices_input.split(',') if c.strip()]
                selected = [csv_files[i-1] for i in choices if 1 <= i <= len(csv_files)]
            except (ValueError, IndexError):
                print("Invalid input. Please enter valid numbers.")
                continue
        
        # Add selected files to the list
        for file in selected:
            selected_files.append((folder_path, file))
            print(f"Added '{file}' from '{folder_path}' to selection.")
        
        print(f"\nCurrent selection: {len(selected_files)} files.")
        
        # After adding files (or even if none were added this round)
        more = input("\nAdd files from another folder? (y/n): ").strip().lower()
        if more in ('n', 'no', '0', ''):
            print("\nFinished selecting. Reading files...")
            break
    
    if not selected_files:
        print("No files selected. Exiting.")
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
        All_data[name] = df[mask]
   
    
   
    new_dict = {}
    grouped_keys = {}
    
    # Group keys by the first two parts (e.g., "Part1_Part2")
    for key in All_data.keys():
        # Splitting by underscore and taking first two elements
        parts = key.split('_')
        if len(parts) >= 2:
            prefix = parts[0]  #  f"{parts[0]}_{parts[1]}" # -> taking first two elements
        else:
            prefix = parts[0]
        
        if prefix not in grouped_keys:
            grouped_keys[prefix] = []
        grouped_keys[prefix].append(key) 
   
    # Process groups for averaging or direct copying
    for prefix, keys in grouped_keys.items():
        if len(keys) > 1:
            # Group has multiple files: Calculate Mean
            combined_group = []
            
            for k in keys:
                df = All_data[k].copy()
                # Ensure the first column is time and rounded
                time_col = df.columns[0]
                df[time_col] = df[time_col].astype(int) #.round()
                combined_group.append(df)
            
            # Merge all DataFrames in this group on the time column
            merged_df = None
            for i, df in enumerate(combined_group):
                # Copy and rename every column except "time" to avoid conflicts
                df_renamed = df.copy()
                rename_dict = {col: f"source{i+1}_{col}" 
                               for col in df.columns if col != "time_s"}
                df_renamed.rename(columns=rename_dict, inplace=True)
                
                if merged_df is None:
                    merged_df = df_renamed
                else:
                    merged_df = pd.merge(merged_df, df_renamed, on="time_s", how="outer")

            # Fill missing values with 0 (as you requested)
            merged_df.fillna(0, inplace=True)

            # Sort by time and reset index for a clean result
            merged_df = merged_df.sort_values(by="time_s").reset_index(drop=True)

            # === AVERAGE OVER NON-ZERO VALUES (vectorized) ===
            value_columns = [col for col in merged_df.columns if col != "time_s"]

            # Sum of non-zero values
            non_zero_mask = merged_df[value_columns] != 0
            sum_non_zero = (merged_df[value_columns] * non_zero_mask).sum(axis=1)

            # Count of non-zero values
            count_non_zero = non_zero_mask.sum(axis=1)

            # Average = sum / count (if count == 0 we return 0)
            merged_df["mean_length"] = sum_non_zero / count_non_zero.replace(0, 1) 
            merged_df["std_length"] = (merged_df[value_columns] * non_zero_mask).std(axis=1)
            # merged_df = combined_group[0]
            # time_col = merged_df.columns[0]
            # for i in range(1, len(combined_group)):
            #     merged_df = pd.merge(merged_df, combined_group[i], on=time_col, how='outer')
            
            # # Sort by time and reset the index to keep it clean
            # merged_df = merged_df.sort_values(by='time_s').reset_index(drop=True)
            # # Calculate mean across all 'length' columns (excluding the time column)
            # # We select all columns except the first one (time) to calculate the mean
            # time_col_name = merged_df.columns[0]
            # data_cols = merged_df.columns[1:]
            
            # avg_df = pd.DataFrame()
            # avg_df[time_col_name] = merged_df[time_col_name]
            # avg_df['mean_length'] = merged_df[data_cols].mean(axis=1)
            
            new_dict[f"{prefix}_averaged"] = merged_df # avg_df
        else:
            # Only one file: Add it to the new dictionary as is
            new_dict[keys[0]] = All_data[keys[0]]
   
    
    
    #---------PLOT------------
    # Create a figure and a single axes object
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Define the maximum row number to plot (e.g., 50)
    max_rows = 30
    
    # Loop through the dictionary and plot on the same axes
    for name, df in sorted(new_dict.items(), key=custom_sort): # Sort the items and convert back to a dictionary
        # Use the 'ax' parameter to plot on the same axes.
        # The 'label' parameter uses the dictionary key for the legend.
        style = get_style()
        df = df.iloc[:max_rows]
        if 'mean_length' in df.columns:
            df.plot(x='time_s', y='mean_length', yerr='std_length', ax=ax, label=name, **style)
        else:
            df.plot(x='time_s', y='length_cm', ax=ax, label=name, **style)
     
    # Customize and display the plot
    ax.tick_params(axis='both', which='major', labelsize=20)
    ax.set_title('CalCl2 Concentrations', fontsize=20)
    # ax.set_title('Heparin Concentrations')
    ax.set_xlabel('Time (s)', fontsize=20)
    # ax.set_ylabel('Travelled length (cm)')
    ax.set_ylabel('Area expansion (cm$^2$)', fontsize=20)
    ax.legend(title='',fontsize=14)
    plt.grid(True)
    plt.show()
    
    
    
    
    
   #------------------Rojan-------------------------------
    # Create a figure and a single axes object
    fig, ax = plt.subplots(figsize=(10, 6))
    exclude_str = 'Domenica'

    # Filter: Keep keys that DO NOT contain 'Domenica' so it just plots my results
    filtered_dict = {k: v for k, v in new_dict.items() if exclude_str not in k}
    
    # Loop through the dictionary and plot on the same axes
    for name, df in sorted(filtered_dict.items(), key=custom_sort): # Sort the items and convert back to a dictionary
        # Use the 'ax' parameter to plot on the same axes.
        # The 'label' parameter uses the dictionary key for the legend.
        style = get_style()
        df = df.iloc[:max_rows]
        if 'mean_length' in df.columns:
            df.plot(x='time_s', y='mean_length', yerr='std_length',  ax=ax, label=name, **style)
            # df.plot(x='time_s', y='mean_length', ax=ax, label=name, **style)
        else:
            df.plot(x='time_s', y='length_cm', ax=ax, label=name, **style)
     
    # Customize and display the plot
    ax.tick_params(axis='both', which='major', labelsize=20)
    ax.set_title('CalCl2 Concentrations', fontsize=20)
    # ax.set_title('Heparin Concentrations')
    ax.set_xlabel('Time (s)', fontsize=20)
    # ax.set_ylabel('Travelled length (cm)')
    ax.set_ylabel('Area expansion (cm$^2$)', fontsize=20)
    ax.legend(title='',fontsize=14)
    plt.grid(True)
    plt.show()
    

    
    #------------------------Domenica------------------------
    # Find common keys
    shared_keys = set(new_dict.keys()) & set(filtered_dict.keys())
    
    # Create the new dictionary with unshared dataframes to plot only Domenica's results
    unshared_dataframes = { k: v for k, v in new_dict.items() if k not in shared_keys }
    fig, ax = plt.subplots(figsize=(10, 6))
    # Loop through the dictionary and plot on the same axes
    for name, df in sorted(unshared_dataframes.items(), key=custom_sort): # Sort the items and convert back to a dictionary
        # Use the 'ax' parameter to plot on the same axes.
        # The 'label' parameter uses the dictionary key for the legend.
        style = get_style()
        df = df.iloc[:max_rows]
        if 'mean_length' in df.columns:
            df.plot(x='time_s', y='mean_length', yerr='std_length', ax=ax, label=name, **style)
        else:
            df.plot(x='time_s', y='length_cm', ax=ax, label=name, **style)
     
    # Customize and display the plot
    ax.tick_params(axis='both', which='major', labelsize=20)
    ax.set_title('CalCl2 Concentrations', fontsize=20)
    # ax.set_title('Heparin Concentrations')
    ax.set_xlabel('Time (s)', fontsize=20)
    # ax.set_ylabel('Travelled length (cm)')
    ax.set_ylabel('Area expansion (cm$^2$)', fontsize=20)
    ax.legend(title='',fontsize=14)
    plt.grid(True)
    plt.show()
    
    
    
    
    
    
    
    #---------PLOT------------
    # Define the maximum row number to plot (e.g., 50)
    max_rows = 30
    # Loop through the dictionary and plot on the same axes
    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Define a color palette (optional, but helpful)
    colors = sns.color_palette('husl', n_colors=len(new_dict))
    color_map = dict(zip(new_dict.keys(), colors))
    for name, df in new_dict.items():
        # Prepare data for plotting
        df = df.iloc[:max_rows]
        x_values = df['time_s']
        # Calculate y-squared
        if 'mean_length' in df.columns: #df.columns[1]!='mean_length':
           y_squared = df['mean_length'] ** 2             
        else:
           y_squared = df['length_cm'] ** 2 
        
        # Plot scatter points
        ax.scatter(x_values, y_squared, label=f'{name} Data', color=color_map[name], alpha=0.6, edgecolors='k')
        
        # Perform linear regression on the (x, y^2) data
        # linregress returns slope, intercept, r_value, p_value, std_err
        slope, intercept, r_value, p_value, std_err = linregress(x_values, y_squared)
        
        # Plot the regression line
        # Create x-sequence for the line
        x_seq = np.linspace(x_values.min(), x_values.max(), 100)
        ax.plot(x_seq, slope * x_seq + intercept, color=color_map[name], linestyle='--', lw=2, label=f'{name} Regression (R²={r_value**2:.2f})')
        # Increase font size for both x and y axis tick labels
        ax.tick_params(axis='both', which='major', labelsize=20)
        
    # Add titles and labels
    #ax.set_title(f'Scatter Plot for {name} with Regression Line')
    ax.set_xlabel('Time (s)', fontsize=20)
    ax.set_ylabel('Travel Distance$^2$ (cm$^2$)', fontsize=20)
    ax.legend(title='Drug concentration (mM)', fontsize=12)
            
    # Optional: Annotate with R-squared value
    ax.annotate(f'$R^2$: {r_value**2:.2f}', xy=(0.05, 0.9), xycoords='axes fraction')
            
    # Display the plot
    plt.show()




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
        
        # Melt them into long format
        melted = df.melt(
            id_vars=['time_s'],
            value_vars=area_cols,
            var_name='replicate',
            value_name='area'
        )
        
        # Drop any NaN measurements (some cases may have only 3-4 replicates)
        melted = melted.dropna(subset=['area'])
        
        # Add case identifier
        melted['case'] = case_name
        
        # Keep only the columns we need
        long_rows.append(melted[['time_s', 'case', 'area']])
    
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
    
    # ================================================================
    # STEP 2: ONE-WAY ANOVA AT EVERY TIME POINT (with Bonferroni correction)
    # ================================================================
    unique_times = sorted(long_df[time_column_to_use].unique())
    unique_cases = long_df['case'].unique()
    
    p_values_raw = {}
    group_counts = {}
    
    for t in unique_times:
        group_values = []
        for case in unique_cases:
            vals = long_df[
                (long_df[time_column_to_use] == t) & 
                (long_df['case'] == case)
            ]['area'].values
            
            if len(vals) >= 2:          # need at least 2 replicates for variance
                group_values.append(vals)
                group_counts[t] = group_counts.get(t, 0) + 1
        
        if len(group_values) >= 2:
            f_stat, p_val = stats.f_oneway(*group_values)
            p_values_raw[t] = p_val
        else:
            p_values_raw[t] = np.nan
    
    # Bonferroni correction
    n_tests = sum(1 for p in p_values_raw.values() if not np.isnan(p))
    corrected_p = {
        t: p * n_tests if not np.isnan(p) else np.nan 
        for t, p in p_values_raw.items()
    }
    
    # print("\n=== ANOVA RESULTS (differences between cases at each time) ===")
    # print(f"{'Time':>10} | {'Raw p-value':>12} | {'Corrected p':>12} | Significant?")
    # for t in unique_times:
    #     p_raw = p_values_raw[t]
    #     p_corr = corrected_p[t]
    #     sig = "YES" if (not np.isnan(p_corr) and p_corr < 0.05) else "no"
    #     print(f"{t:10.2f} | {p_raw:12.4f} | {p_corr:12.4f} | {sig:>10}")
    
    # ================================================================
    # OPTIONAL: Post-hoc Tukey HSD at a specific significant time
    # ================================================================
    # Change example_time to any time where corrected p < 0.05
    example_time = unique_times[24] if unique_times else None
    if example_time is not None and not np.isnan(corrected_p.get(example_time, np.nan)):
        data_at_t = long_df[long_df[time_column_to_use] == example_time]
        tukey = pairwise_tukeyhsd(
            endog=data_at_t['area'],
            groups=data_at_t['case'],
            alpha=0.05
        )
        print(f"\nTukey HSD post-hoc at time ≈ {example_time}")
        print(tukey)
        
        
        
        
    # 2. AUC
    # ================================================================
    # STEP 1: Find the shortest maximum time across all cases
    # ================================================================
    data_to_analyse = new_dict # unshared_dataframes   #= filtered_dict
    max_times = [df['time_s'].max() for df in data_to_analyse.values()]
    common_end_time = 250 #min(max_times)
    common_start_time = 35
    
    print(f"Truncating all cases to {common_end_time} seconds for fair comparison.")
    
    all_auc_data = []
    
    for case_name, df in data_to_analyse.items():
        # Only keep data up to the common end time
        df_clipped = df[df['time_s'].between(common_start_time,common_end_time)].copy()
        
        area_cols = [c for c in df_clipped.columns if c.endswith('_area_cm2')]
        
        for col in area_cols:
            clean_df = df_clipped[['time_s', col]].dropna()
            if not clean_df.empty:
                # Calculate AUC for the clipped window
                case_auc = auc(clean_df['time_s'], clean_df[col])
                all_auc_data.append({'Case': case_name, 'AUC': case_auc})
    
    stats_df = pd.DataFrame(all_auc_data)
    
    # ================================================================
    # STEP 2: Run One-Way ANOVA
    # ================================================================
    groups = [group['AUC'].values for name, group in stats_df.groupby('Case')]
    f_stat, p_val = stats.f_oneway(*groups)
    
    print(f"ANOVA Result: F={f_stat:.3f}, p-value={p_val:.4f}")
    
    # ================================================================
    # STEP 3: Run Tukey HSD if significant
    # ================================================================
    if p_val < 0.05:
        tukey = pairwise_tukeyhsd(endog=stats_df['AUC'], groups=stats_df['Case'], alpha=0.05)
        print(tukey)        
    # Convert Results to a Pandas DataFrame
    tukey_data = pd.DataFrame(data=tukey._results_table.data[1:], 
                              columns=tukey._results_table.data[0])
    
    #  Write Results to Excel
    output_file = 'Citrate_CaCl2_Tukey_Results.xlsx'
    tukey_data.to_excel(output_file, index=False, sheet_name='Tukey_HSD')
    
    print(f"Tukey results successfully written to {output_file}")
    
    
    
    
    
    # 3. NLME (NonLinear Mixed-Effect Model)
    