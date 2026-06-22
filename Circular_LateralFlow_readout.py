import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import re
import os
from PyQt5.QtWidgets import QApplication, QFileDialog
import sys
import csv

# from google.colab.patches import cv2_imshow  # Import for displaying images in Colab
# %matplotlib auto

# ========================== CONFIGURATION ==========================

# ────────────────────────────────────────────────
# VIDEO INPUT & FIRST FRAME FOR ROI SELECTION
# ────────────────────────────────────────────────
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

VIDEO_PATH, _ = QFileDialog.getOpenFileName(
    None,
    "Select a file",
    "",
    "All files (*.*)"
)
# VIDEO_PATH = "C:/Users/rojan\Documents/FSU/LateralFlowExperiments/3Feb2026/Circular_LFA\IMG_0419.MOV"         # file path
if VIDEO_PATH:
    print("Selected file:", VIDEO_PATH)
else:
    print("No file selected")    

# Create a Path object
p = Path(VIDEO_PATH)
# Get folder name and original filename parts
base_path = p.parent
# Access the components and slice the last parts, then join them
Date_name = Path(*p.parts[-2:-1])
# the last number:
last_number = re.search(r'(\d+)[^\d]*$', str(p)).group(1) if re.search(r'(\d+)[^\d]*$', str(p)) else None
#print(last_number) # Output: 0316


OUTPUT_FOLDER = Path("circular_blood_dispersion_results")
# Check if the directory exists
if not os.path.exists(OUTPUT_FOLDER):
    # If not, create the directory
    os.makedirs(OUTPUT_FOLDER)
    print(f"Directory '{OUTPUT_FOLDER}' created.")
else:
    print(f"Directory '{OUTPUT_FOLDER}' already exists.")
folder_name = Date_name
new_file_path = os.path.join(f"{OUTPUT_FOLDER}", f"{folder_name}_{last_number}")
os.makedirs(new_file_path, exist_ok=True)

# Detection thresholds (tune these after first run)
DIFF_THRESHOLD = 25          # pixel difference to consider "wet"
DROP_DETECTION_AREA = 800    # minimum changed pixels to detect a drop
MORPH_KERNEL_SIZE = 5

# HSV color ranges for final segmentation (very important – tune these!)
# Yellowish plasma (outer halo)
LOWER_YELLOW = np.array([15,  40,  80])
UPPER_YELLOW = np.array([45, 255, 255])

# Pinkish fingering region
LOWER_PINK   = np.array([135,  60,  80])
UPPER_PINK   = np.array([175, 255, 255])

# # Red blood cell rich center
# LOWER_RED1   = np.array([  0,  70,  70])
# UPPER_RED1   = np.array([ 12, 255, 255])
# LOWER_RED2   = np.array([165,  70,  70])
# UPPER_RED2   = np.array([180, 255, 255])

# Red detection (blood)
lower_red1 = np.array([0, 20, 20]) # np.array([0, 50, 20]) # np.array([0, 120, 70]) [hue, saturation, value]
upper_red1 = np.array([10, 255, 255]) # np.array([10, 255, 255]) # np.array([10, 255, 255])
lower_red2 = np.array([160, 20, 50]) # np.array([160,70,50]) # np.array([175,50,20]) # np.array([135,  60,  80]) # pinkish # np.array([170, 120, 70]) 
upper_red2 = np.array([180, 255, 255]) # np.array([180,255,255]) # np.array([175, 255, 255]) # pinkish # np.array([180, 255, 255])

# Scale (optional) – if you know the paper size in pixels
# Example: paper is 2.5 cm × 2.5 cm and your ROI exactly matches it
PIXELS_PER_CM = None   # set to e.g. 400 if your ROI width = 1000 px → 1000/2.5 = 400 px/cm

# Display settings for ROI selection
MAX_DISPLAY_WIDTH = 1920
MAX_DISPLAY_HEIGHT = 1080
ROTATE_IF_PORTRAIT = True  # Rotate 90 degrees if height > width

# =================================================================

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise IOError("Cannot open video")

fps = cap.get(cv2.CAP_PROP_FPS)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"Video: {frame_count} frames @ {fps:.2f} fps → ~{frame_count/fps/60:.1f} min")

# === 1. Read first frame ===
ret, first_frame = cap.read()
if not ret:
    raise IOError("Cannot read first frame")

# Prepare display frame: rotate if needed, then resize if too large
display_frame = first_frame.copy()
h, w = display_frame.shape[:2]
scale = 1.0
rotation_applied = False

if ROTATE_IF_PORTRAIT and h > w:
    display_frame = cv2.rotate(display_frame, cv2.ROTATE_90_CLOCKWISE)  #cv2.ROTATE_90_CLOCKWISE or cv2.ROTATE_180 or cv2.ROTATE_90_COUNTERCLOCKWISE
    h, w = display_frame.shape[:2]
    rotation_applied = True

if w > MAX_DISPLAY_WIDTH or h > MAX_DISPLAY_HEIGHT:
    scale = min(MAX_DISPLAY_WIDTH / w, MAX_DISPLAY_HEIGHT / h)
    display_frame = cv2.resize(display_frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    h, w = display_frame.shape[:2]

# === 2. Select ROIs one by one on display frame ===
print("Instructions:")
print("- Draw a rectangle around one drop location.")
print("- Press SPACE or ENTER to confirm it.")
print("- The window will reopen for the next ROI.")
print("- When done with all ROIs, press ESC (or c) without drawing a rectangle.")
print("If the image is still too large, you can resize the window manually.")

window_name = "Select ROIs (one per drop, ESC to finish)"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.resizeWindow(window_name, w, h)  # Set initial window size to image size



rois_display = []
num_assays = 0
while True:
    num_assays +=1
    print(f"→ Step 1.{num_assays+1}: Select ROI for ASSAY {num_assays+1}")
    
    # Draw previously selected ROIs for reference (previous assays)
    for j, prev_roi in enumerate(rois_display):
        x, y, w, h = prev_roi
        cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)   # green for assays
        cv2.putText(display_frame, f"A{j+1}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    roi = cv2.selectROI(f"Select Assay {num_assays+1}", display_frame, fromCenter=False, showCrosshair=True)  
    if roi == (0, 0, 0, 0):
        break
    if roi[2] > 0 and roi[3] > 0:
        rois_display.append(roi)
        print(f"Assay {num_assays+1} ROI: {roi}\n")
    else:
        print(f"Assay {num_assays+1} selection cancelled. Exiting.")
        cap.release()
        exit()

cv2.destroyAllWindows()

if not rois_display:
    raise ValueError("No ROIs selected")

print(f"Selected {len(rois_display)} ROIs")


# 2. Now, interactive calibration for measuring tape: user clicks two points to define a line segment
#    and inputs the real-world values (in cm) at start and end points
print("→ Step 2: Calibrate scale using measuring tape")
print("Click LEFT MOUSE BUTTON on the START point of the tape segment, then on the END point.")
print("Press 'q' to quit or restart if needed. Window will close after two clicks.\n")

# Global variables for mouse clicks
calibration_points = []
drawing_frame = display_frame.copy()

# Draw existing assay ROIs on the drawing frame for context
for i, roi in enumerate(rois_display):
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

blood_detection_threshold = 500           # red pixels needed to detect start
measurement_interval_seconds = 10.0        # measure every X seconds after blood appears
measurement_interval_frames = int(measurement_interval_seconds * fps)

start_frames = [None] * len(rois_display)
measurements = [[] for _ in range(len(rois_display))]

frame_num = 0

print("Starting video processing...\n")

while cap.isOpened():
    ret, frame = cap.read()
    
    if not ret:
        break
    if rotation_applied:
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)  #cv2.ROTATE_90_CLOCKWISE or cv2.ROTATE_180 or cv2.ROTATE_90_COUNTERCLOCKWISE
    # cv2.imshow('Frame', frame)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    frame_num += 1 # Increment at the start for clarity
    for i, roi in enumerate(rois_display):
        x, y, w, h = roi
        assay_roi = frame[y:y+h, x:x+w]

        # VALIDATION GATE: Check if the ROI is actually readable
        # Calculate mean brightness; if it's too dark (blank), skip the math
        mean_brightness = np.mean(assay_roi)
       
        
        hsv = cv2.cvtColor(assay_roi, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        # red_mask = mask1 + mask2
        # has_red = np.any(red_mask > 0, axis=1)
        # max_x = np.max(np.where(has_red))
        # Use bitwise AND to extract the red color from the original image
        result = cv2.bitwise_and(assay_roi, assay_roi, mask=red_mask)
        

        if start_frames[i] is None:
            red_pixels = cv2.countNonZero(red_mask)
            if red_pixels > blood_detection_threshold:                
                # cv2.imshow("ROI Image", frame)
                # cv2.waitKey(0)
                # cv2.destroyAllWindows()
                
                # Sanity check: display the ROI and ask for confirmation
                # Show the assay ROI with potential blood detection
                # display_roi = assay_roi.copy()
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
                cv2.destroyWindow(f"Potential Start for Assay {i+1} at Frame {frame_num}")
                # cv2.destroyWindow(f"Potential Start for Assay {i+1} at Frame {frame_num}")
                # start_frames[i] = frame_num
                # t = frame_num / fps
                # print(f"Assay {i+1}: Blood appeared  at frame {frame_num} (~{t:.1f} s)")
                
        # MEASUREMENT PHASE (Every 10 frames after start)
        elif (frame_num - start_frames[i]) % measurement_interval_frames == 0:  #(frame_num - start_frames[i]>0)
            time_s = (frame_num - start_frames[i]) / fps
            # Count pixels
            # findContours is more robust than just counting non-zero pixels 
            # as it allows you to filter out small noise/dust.
            # Display the original image, mask, and result
            # plt.figure()
            # plt.imshow(assay_roi)       # Display original image
            # plt.figure()
            # plt.imshow(mask1)   # Display red mask 1
            # plt.figure()
            # plt.imshow(mask2)   # Display red mask 2
            # plt.figure()
            # plt.imshow(red_mask)      # Display the result where red is detected
            plt.figure()
            plt.imshow(result)      # Display the result where red is detected
            contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE) #cv2.CHAIN_APPROX_SIMPLE)
            largest_contour = sorted(contours, key=cv2.contourArea, reverse=True)[0]

            total_area_pixels = 0
            for cnt in contours:
                if cv2.contourArea(cnt) > 5: # Filter out tiny noise
                    total_area_pixels += cv2.contourArea(cnt)
        
            # Convert to cm^2
            area_cm2 = total_area_pixels * (scale_factor ** 2)
            measurements[i].append((time_s, area_cm2))
            print(f"Assay {i+1} | {frame_num} | {time_s:6.1f} s | {area_cm2:5.2f} cm2")
            
            # Display results on frame
            cv2.drawContours(assay_roi, largest_contour, -1, (0, 255, 0), 1)
            # cv2.imshow('largest_contour', assay_roi)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()
            cv2.putText(assay_roi, f"Area: {area_cm2:.2f} cm2", (20, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 1)
            cv2.imshow('largest_contour', assay_roi)  #cv2.imshow('Tracking', assay_roi)
            cv2.destroyWindow('largest_contour')
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break
            
             

cap.release()
cv2.destroyAllWindows()

#----------------------------------------
#          Write out to CSV
#----------------------------------------

for i in range(len(rois_display)):
    concentration = input("Enter the concentration of CaCl2/heparin and CBD used for all the assays (e.g Control, or 450mM, or 800mMControlCBD, or 800mMLowCBDDara, etc.)"
                              " in this experiment followed by _ and whether it is REST or Exercise blood"
                              "followed by _ and which visit it is (eg. visit3, visit4, ...").strip()
    visit_num = concentration.split("_")[-1]
    filename = f"assay_{i+1}_{folder_name}_{last_number}_{concentration}.csv"
        
    # Combine the folder path and file name using os.path.join
    file_path = os.path.join(new_file_path, filename)
    # Combine using os.path.join with f-string
    
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        #writer.writerow([Col_names[i], Col_names[i]])
        writer.writerow(['time_s', 'area_cm2'])
        writer.writerows(measurements[i])
    print(f"Saved: {filename}")

print("\nProcessing finished.")
