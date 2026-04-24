# Import necessary libraries
import cv2
import numpy as np
import csv
from pathlib import Path
import re
import os
from PyQt5.QtWidgets import QApplication, QFileDialog
import sys



# Define rotation function
def rotate_frame(frame, direction='anticlockwise'):
    if direction == 'clockwise':
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    elif direction == 'anticlockwise':
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif direction == 'flip':
        return cv2.rotate(frame, cv2.ROTATE_180)
    else:
        raise ValueError("Direction must be 'clockwise', 'anticlockwise', or 'flip'")

# ────────────────────────────────────────────────
# VIDEO INPUT & FIRST FRAME FOR ROI SELECTION
# ────────────────────────────────────────────────
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

video_path, _ = QFileDialog.getOpenFileName(
    None,
    "Select a file",
    "",
    "All files (*.*)"
)

if video_path:
    print("Selected file:", video_path)
else:
    print("No file selected")    
# video_path = "C:/Users/rojan/Documents/FSU/LateralFlowExperiments/8Jan2026/IMG_0316.MOV"  
#"C:/Users/rojan/Documents/FSU/LateralFlowExperiments/15Jan2026/IMG_2318.MOV" 
#"C:/Users/rojan/Documents/FSU/LateralFlowExperiments/8Jan2026/IMG_0321.MOV"  # ← change this

# Create a Path object
p = Path(video_path)
# Get folder name and original filename parts
base_path = p.parent
# Access the components and slice the last parts, then join them
Date_name = Path(*p.parts[-2:-1])
# the last number:
last_number = re.search(r'(\d+)[^\d]*$', str(p)).group(1) if re.search(r'(\d+)[^\d]*$', str(p)) else None
#print(last_number) # Output: 0316

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("Error opening video file")
    exit()

# Read first frame for ROI selection
target_frame_number = 0
cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_number - 1)
ret, first_frame = cap.read()
if not ret:
    print("Error reading first frame")
    exit()

# Rotate once — this orientation will be used for all processing
rotated_frame = rotate_frame(first_frame, 'anticlockwise') #rotate_frame(first_frame, 'clockwise')  # ← change to 'anticlockwise' or 'flip' if needed

# Reset capture to beginning for later processing
cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

# ────────────────────────────────────────────────
# INTERACTIVE ROI SELECTION — ALL IN ONE PHASE
# ────────────────────────────────────────────────

print("=== ROI SELECTION PHASE ===")
print("Use mouse to drag rectangle for assays. For tape calibration, click two points.")
print("Press SPACE or ENTER to confirm rectangles, ESC to cancel.\n")

rois = []                    # list of assay ROIs: [(x,y,w,h), ...]

# 1. Select assay ROIs (viewing windows where blood moves)
num_assays = 2  # ← CHANGE THIS to match your experiment

for i in range(num_assays):
    print(f"→ Step 1.{i+1}: Select ROI for ASSAY {i+1}")
    display_frame = rotated_frame.copy()
    
    # Draw previously selected ROIs for reference (previous assays)
    for j, prev_roi in enumerate(rois):
        x, y, w, h = prev_roi
        cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)   # green for assays
        cv2.putText(display_frame, f"A{j+1}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    roi = cv2.selectROI(f"Select Assay {i+1}", display_frame, fromCenter=False, showCrosshair=True)
    if i != num_assays-1:
        cv2.destroyWindow(f"Select Assay {i+1}")
    
    if roi[2] > 0 and roi[3] > 0:
        rois.append(roi)
        print(f"Assay {i+1} ROI: {roi}\n")
    else:
        print(f"Assay {i+1} selection cancelled. Exiting.")
        cap.release()
        exit()

# 2. Now, interactive calibration for measuring tape: user clicks two points to define a line segment
#    and inputs the real-world values (in cm) at start and end points
print("→ Step 2: Calibrate scale using measuring tape")
print("Click LEFT MOUSE BUTTON on the START point of the tape segment, then on the END point.")
print("Press 'q' to quit or restart if needed. Window will close after two clicks.\n")

# Global variables for mouse clicks
calibration_points = []
drawing_frame = rotated_frame.copy()

# Draw existing assay ROIs on the drawing frame for context
for i, roi in enumerate(rois):
    x, y, w, h = roi
    cv2.rectangle(drawing_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.putText(drawing_frame, f"A{i+1}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

# Mouse callback function to capture two points
def mouse_callback(event, x, y, flags, param):
    global calibration_points, drawing_frame
    if event == cv2.EVENT_LBUTTONDOWN:
        calibration_points.append((x, y))
        # Draw a small circle at the clicked point
        cv2.circle(drawing_frame, (x, y), 5, (0, 0, 255), -1)  # Red circle
        cv2.imshow("Calibrate Tape Scale", drawing_frame)
        
        if len(calibration_points) == 2:
            # Draw the line between the two points
            cv2.line(drawing_frame, calibration_points[0], calibration_points[1], (255, 0, 0), 2)  # Blue line
            cv2.imshow("Calibrate Tape Scale", drawing_frame)

# Create window and set mouse callback
cv2.namedWindow("Calibrate Tape Scale")
cv2.setMouseCallback("Calibrate Tape Scale", mouse_callback)
cv2.imshow("Calibrate Tape Scale", drawing_frame)

# Wait until two points are clicked or 'q' is pressed
while len(calibration_points) < 2:
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        print("Calibration cancelled. Exiting.")
        cap.release()
        cv2.destroyAllWindows()
        exit()

# After two clicks, keep the window open briefly to review, then close on any key
print("Line drawn. Press any key to continue to value input.")
cv2.waitKey(0)
cv2.destroyAllWindows()

# Now, prompt for real-world values
try:
    start_value = float(input("Enter the value (in cm) at the START point: "))
    end_value = float(input("Enter the value (in cm) at the END point: "))
except ValueError:
    print("Invalid input. Using default scale_factor = 0.01 cm/pixel.")
    scale_factor = 0.01
else:
    # Calculate pixel distance (Euclidean, handles tilted lines)
    pt1 = np.array(calibration_points[0])
    pt2 = np.array(calibration_points[1])
    dist_pixels = np.linalg.norm(pt2 - pt1)
    
    dist_cm = abs(end_value - start_value)
    
    if dist_pixels > 0:
        scale_factor = dist_cm / dist_pixels
        print(f"Calculated scale_factor: {scale_factor:.4f} cm/pixel\n")
    else:
        print("Points are the same. Using default scale_factor = 0.01 cm/pixel.")
        scale_factor = 0.01

print("All selections and calibration complete.\n")
# ────────────────────────────────────────────────
# VIDEO PROCESSING PARAMETERS
# ────────────────────────────────────────────────

fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

blood_detection_threshold = 20           # red pixels needed to detect start
measurement_interval_seconds = 10.0        # measure every X seconds after blood appears
measurement_interval_frames = int(measurement_interval_seconds * fps)

# Threshold to detect black/empty frames (mean pixel intensity)
black_frame_threshold = 5.0  # Adjust if needed; if mean < this, consider black

start_frames = [None] * len(rois)
measurements = [[] for _ in range(len(rois))]

frame_num = 0

print("Starting video processing...\n")

while cap.isOpened():
    ret, frame = cap.read()
    
    if not ret:
        break

    frame = rotate_frame(frame, 'anticlockwise') #rotate_frame(frame, 'clockwise')  # same rotation as before
    frame_num += 1 # Increment at the start for clarity
    for i, roi in enumerate(rois):
        x, y, w, h = roi
        assay_roi = frame[y:y+h, x:x+w]

        # VALIDATION GATE: Check if the ROI is actually readable
        # Calculate mean brightness; if it's too dark (blank), skip the math
        mean_brightness = np.mean(assay_roi)
        is_blank = mean_brightness < black_frame_threshold
        
        
        hsv = cv2.cvtColor(assay_roi, cv2.COLOR_BGR2HSV)
        # # Display
        # cv2.imshow("ROI Image", hsv)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        # Red detection (blood)
        lower_red1 = np.array([0, 100, 100]) #np.array([150, 100, 100]) #np.array([0, 120, 70]) # np.array([0, 100, 100])
        upper_red1 = np.array([10, 100, 100]) #np.array([160, 255, 255])
        lower_red2 = np.array([160, 100, 100]) #np.array([170, 120, 70]) # np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        # # Display
        # cv2.imshow("ROI Image red mask 1", mask1)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        # # Display
        # cv2.imshow("ROI Image red mask 2", mask2)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        
        red_mask = cv2.bitwise_or(mask1, mask2)
        # # Display
        # cv2.imshow("ROI Image red mask all", red_mask)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        if start_frames[i] is None:
            red_pixels = cv2.countNonZero(red_mask)
            if red_pixels > blood_detection_threshold and not is_blank:                
                # cv2.imshow("ROI Image", frame)
                # cv2.waitKey(0)
                # cv2.destroyAllWindows()
                
                # Sanity check: display the ROI and ask for confirmation
                # Show the assay ROI with potential blood detection
                display_roi = assay_roi.copy()
                # Optional: overlay the red mask in semi-transparent red for visualization
                # display_roi[red_mask > 0] = (0, 0, 255)  # Highlight red pixels.
                # Actually, to show original, maybe show side by side: original ROI | masked
                # But for simplicity, show original ROI
                cv2.imshow(f"Potential Start for Assay {i+1} at Frame {frame_num}", assay_roi)
                
                print(f"Assay {i+1}: Potential blood detected at frame {frame_num} (time: {frame_num / fps:.2f}s)")
                print("Is this the true start of blood penetration (not pipette)? Press 'y' for yes, 'n' for no.")
                
                while True:  # Loop until valid input
                    key = cv2.waitKey(0) & 0xFF
                    if key == ord('y'):
                        start_frames[i] = frame_num
                        print(f"Assay {i+1}: Confirmed start at frame {frame_num} (time: {frame_num / fps:.2f}s)")
                        break
                    elif key == ord('n'):
                        print(f"Assay {i+1}: False positive rejected, continuing...")
                        break
                    else:
                        print("Invalid key. Press 'y' or 'n'.")
                
                # cv2.destroyWindow(f"Potential Start for Assay {i+1} at Frame {frame_num}")
                # start_frames[i] = frame_num
                # t = frame_num / fps
                # print(f"Assay {i+1}: Blood appeared  at frame {frame_num} (~{t:.1f} s)")
                
        # MEASUREMENT PHASE (Every 10 frames after start)
        elif (frame_num - start_frames[i]) % measurement_interval_frames == 0:  #(frame_num - start_frames[i]>0)
            time_s = (frame_num - start_frames[i]) / fps
            # Simple length measurement: farthest column with red pixels
            # has_red = np.any(red_mask > 0, axis=1)
            # max_x = np.max(np.where(has_red)) if np.any(has_red) else 0
            # min_x = np.min(np.where(has_red)) if np.any(has_red) else 0
            # length_cm = abs(max_x - min_x)* scale_factor
            
                       
            
            if is_blank:
                # OPTION A: Carry forward the last measurement if available
                if len(measurements[i]) > 0:
                    last_val = measurements[i][-1][1]
                    measurements[i].append((time_s, last_val))
                    print(f"Assay {i+1}: Frame blank at {time_s}s, carrying forward {last_val}cm")
                else:
                    measurements[i].append((time_s, 0.0))
            else:
                # Normal measurement logic
                has_red = np.any(red_mask > 0, axis=1)
                if np.any(has_red):
                    max_x = np.max(np.where(has_red))
                    min_x = np.min(np.where(has_red))
                    length_cm = abs(max_x - min_x) * scale_factor
                else:
                    length_cm = 0.0
                
                measurements[i].append((time_s, length_cm))
                print(f"Assay {i+1} | {frame_num} | {time_s:6.1f} s | {length_cm:5.2f} cm")
            
            
            
            # if length_cm==0.0:
            #    # cv2.imshow(f"Potential Start for Assay {i+1} at Frame {frame_num}", assay_roi)
            #    # # Wait for a key press
            #    # # 0 means the window will wait indefinitely until a key is pressed
            #    # cv2.waitKey(0)
            #    print("The frame is empty, no strip and/or blood in the frame.")
            #    #length_cm = measurements[i][-1][1]
            #    zero_frame_flag = True
            #    continue
            
            # measurements[i].append((time_s, length_cm))

            # print(f"Assay {i+1} | {frame_num} | {time_s:6.1f} s | {length_cm:5.2f} cm")


    # frame_num += 1

cap.release()
cv2.destroyAllWindows()

# ────────────────────────────────────────────────
# SAVE RESULTS
# ────────────────────────────────────────────────
Col_names=['Control_REST','50mM_REST','150mM_REST','250mM_REST','350mM_REST','450mM_REST',
           'Control_Exercise','50mM_Exercise','150mM_Exercise','250mM_Exercise','350mM_Exercise','450mM_Exercise']

# Define the folder name
folder_name = Date_name
new_file_path = os.path.join(f"{folder_name}_{last_number}")
#print(new_file_path) # Output: /data/reports/reports_Q1_sales.csv

# Create the directory
# os.makedirs creates directories recursively and doesn't raise an error if the directory already exists
os.makedirs(new_file_path, exist_ok=True)


for i in range(len(rois)):
    if num_assays != 12:
        concentration = input("Enter the concentration of CaCl2/heparin used for all the assays"
                              "in this experiment followed by _ and whether it is REST or Exercise blood").strip()
    if num_assays == 12:
        filename = f"assay_{i+1}_{folder_name}_{last_number}_{Col_names[i]}.csv" #f"assay_{i+1}_15Jan_2318_450mM.csv"
    else:
        # concentration = input("Enter the concentration of CaCl2 used for all the assays"
        #                       "in this experiment followed by _ and whether it is REST or Exercise blood").strip()
        filename = f"assay_{i+1}_{folder_name}_{last_number}_{concentration}.csv"
        
    # Combine the folder path and file name using os.path.join
    file_path = os.path.join(new_file_path, filename)
    # Combine using os.path.join with f-string
    
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        #writer.writerow([Col_names[i], Col_names[i]])
        writer.writerow(['time_s', 'length_cm'])
        writer.writerows(measurements[i])
    print(f"Saved: {filename}")

print("\nProcessing finished.")