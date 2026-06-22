[//]: # (Image References)



[image1]: ./Figures/Step1.png "Choose the video you want to process from the interactive window"

[image2]: ./Figures/Step2-SelecetROI.png "Select the ROI"

[image3]: ./Figures/Step2-SelecetNextROI.png "Select the next ROI"

[image4]: ./Figures/Step2-SelectedROIALL.png "ALL ROIs are selected. Close this section using the esc key."

[image5]: ./Figures/Step3-SelectPoints.png "Select two end of a line along the measuring tape."

[image6]: ./Figures/Step3-ValuePoints.png "Enter the values of each point one by one in the terminal."

[image7]: ./Figures/Step4-RightVsWrongBlood.png "Wrong VS right frames to pick as the start moment of the blood dispense."

[image8]: ./Figures/Step5-EnterDetails.png "Enter Experiment details for each ROI."





# Step-by-step postprocessing the RFA videos and save the area change over time



A python code named `Circular_LateralFlow_readout.py` is developed to read the area of expanding blood drop on an analytical paper. The code mainly uses cv2 library, OpenCV (Open Source Computer Vision Library), for the image processing section. 



The code consist of four main parts:

1. Read the video, initialize the output folder/file, and extracting data such as frame rate, frame size, etc.
2. Select region of interests (ROIs) one by one on display frame (usually each record consists of 6 squares of papers arranges in 2 rows of 3 squares. The upper row is for Before exercise blood and the lower row is for After exercise blood tests.) And calibration for measuring tape by user clicking two points to define a line segment and inputting the real-world values (in cm) at start and end points.
3. Video processing parameters: segment the expanding blood circular area (red detection) in each frame.
4. Write out the area change over time for each ROI to a separate CSV. 



## Detailed tunning steps

* run `Circular_LateralFlow_readout.p`. It opens up and interactive window which allows you to select the movie file you want to process:
  ![Choose the video you want to process from the interactive window][image1]
* Select the first region of interest (ROI): The square that the first drop of blood is pipetted onto (usually the far left in the first row). **NOTE:** if the frames are 180 rotated you can either go to the code and change `cv2.ROTATE_90_CLOCKWISE` to `cv2.ROTATE_90_COUNTERCLOCKWISE` in both places throughout the code where `display_frame = cv2.rotate(display_frame, cv2.ROTATE_90_CLOCKWISE)` is called. Or, based on the signs in the frame (red arrows on the below image: the first row is usually the one with the "Before" tag representing the Before exercise blood. Also the pipetting starts from the square which is the closest to the measuring tape) choose the right ROI. As we are interested in the total area and the shape is circular, therefore the direction does not have any effect in the final results, only we have to be aware of the right places representing Before vs After data because it would affect the naming of the output files. 
![Select the ROI][image2] 

* Hit enter so another window opens up. In this window you can see that the previous selected ROI is shown in green and annotated as A1. You can proceed to select the second ROI:
![Select the next ROI][image3]

* Keep continues so you choose all the ROI. When you selected the last ROI and hit enter, the window shows all the 6 selected areas in green, annotated as A1 to A6. At this step you have to hit `esc` to escape the window and finish the ROI selection part of the code.
![ALL ROIs are selected. Close this section using the esc key.][image4]

* In the new opened window, you still can see all the selected ROIs shown in green. Here you need to select two points along the measuring tape (red arrows in the figure below). The length of this line helps in calculation of scaling factor later, to translate pixel to actual cm:

 ![Select two end of a line along the measuring tape.][image5]

* The code then asks you to put the value of each point (one by one) that can be read from the measuring tape: for example 18 and 27 for the example above. Hit enter when you put each of the values.

 ![Enter the values of each point one by one in the terminal.][image6]

* The code then starts processing the video, frame by frame and checks to see if it can find any red spots on each of the ROI. If it detects and red pixels it opens a window and asks the use if this is a true start of the blood expansion on the paper and not a floating pipete including blood (image image below). For the wrong capture of blood, hit **`N`** on the keyboard. Keep hitting `N` till the right omen of blood dispense shws. When the window shows the right time of blood dispense on the paper hit **`Y`** on the keyboard for the code to accept that frame as the starting frame for that RIO and move to the next ROIs. 

 ![Wrong VS right frames to pick as the start moment of the blood dispense.][image7]

* Pay attention to the terminal, the code tries to find the starting moment for all the 6 ROIs. When the starting frame is picked for all the 6 you need to wait for the code to finish the process for all the ROIs and all the frames. The progress can be seen as the updated measured area for the assay 1 to 6 in the terminal. 
* When the process is done, a message appears as: 

 ![Enter Experiment details for each ROI.][image8]

 Here, the code asks for some information to name the csv file appropriately for each ROI. Your need to enter:

 1. the concentration of the coagulant used (CaCl2 or protamine): for example _Control_, _450mM_, etc. for when CaCl2 is used only and _120ugml_ and _600ugml_ etc. when protamine is used. If in CBD, THC, etc is used in the experiment in addition to the coagulant, you need to add the concentration of that here too. For example: _800mMControlCBD_ means 800mM of CaCl2 is used plus control CBD (no CBD), or _800mMLowCBD_ means 800mM of CaCl2 is used plus the low concentration of CBD. Also, mostly the experiments are done by Rojan (Experimenter1), But in case that any other experimenter has conducted the tests we need to include their names here. For example: _800mMLowCBDDara_ means that 800mM of CaCl2 plus the low concentration of CBD is used and Dara has conducted the expariment. **NOTE** the wording and the conbination should follow as explain. Another code use this naming format later to do the data analysis. 

 2. use an "**_**" followed by whether it is a **REST** or **Exercise** blood sample. For example: *800mMControlCBD_REST* or *800mMControlCBD_Exercise*. **NOTE** follow the exact upercase/lowercase.

 3. use an "**_**" followed by the visit number. For example: *800mMControlCBD_REST_visit3"

* You have to complete the last step for all the 6 ROIs. The information you provide will be used in the name of the csv file for each ROI where the area change over time is saved into. 
* After saving the data into csv file, images of the segmented blood spot over time will be generated. You can disable it in the code if you do not want them to appear. Or use "Spyder" to run the code as the plots will be displayed in the Plots pane by default, which is easier to handle. These plots help to check if the segmentations are done correctly or not. 



# Removing visit number from csv file name and add them as a new column in the csv file. 

A python code named `add_visit_column_FromFileName.py` is developed to read the visit number from the csv file and add the value into a new column in the csv file. When you run the code, and interactive window opens up that let you choose all the folder you want the code to go inside and read the csv files inside then, remove the visit number from the names and add the visit number value into a new column inside each csv file. This step is necessary to make the csv files ready for further data analysis. 



# Prepare data for data analysis

After you are done processing all the experimental videos and preparing all the output csv files as explained above, we need to put all the values of area expansion over time with all the other information regarding experimenter, coagulant concentration, CBD concentration, etc. is a long format list, which can be used for statistical analysis in python or R. 

A paython code named `LateralFlow_DataAnalysis.py` is developed to do the exact thing. When you run the code, an interactive window opens and let you select all the folders which the csv files are saved in the. The code, then goes in each folder one-by-one, read the data from each one of the csv files inside each folder, and add the data to its long list. The output, would then be another csv file which contains all the data in a long format. You need to change the name of the csv file in this line: `long_df2.to_csv('.../Citrate_5min-1minIncubation_28May2026.csv', index=False)` unless you want to overwrite the previously generated csv file with the same name. 



