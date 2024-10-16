# Import packages
import sys
import os
import cv2
import numpy as np

# Get root directory of project to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.insert(0,parent_dir)

# Import local packages / modules
from modules import sampling_timers
from modules import rpi_cam3_control
from modules import object_detection

obj_det = object_detection.object_detection(True,True)
#obj_det = object_detection.object_detection(True,False)

#cam_ctrl = rpi_cam3_control.rpi_cam3_control(0,"test.jpg")
cam_ctrl = rpi_cam3_control.rpi_cam3_control(1,0)
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(2,0)

# Tmp Loop
restart_imshow_window = True
running = True
# Setup timers
st = sampling_timers.sampling_timers()
st.add("all",       50)
st.add("read_image",50)
st.add("object_detect",50)
# Debug handlers
show_timers = True
cam_ctrl.img_add_en = False
img_add_path = "../../resources/deer_trans_bg_0.png"
if cam_ctrl.img_add_en == True:
    cam_ctrl.init_img_add(img_add_path)
while running:

    #
    # Read image
    #
    st.start("all")
    st.start("read_image")
    img = cam_ctrl.read_cam()
    st.stop("read_image")

    #
    # Object detection
    #
    st.start("object_detect")
    detections = obj_det.run_detector(img)
    st.stop("object_detect")

    #
    # Add dectections boxes on image
    #
    obj_det.draw_boxes(img,0,detections["detection_boxes"],detections["detection_classes"],detections["detection_scores"],max_boxes=10,min_score=0.1)

    #
    # Show image
    #
    if restart_imshow_window == True:
        cv2.namedWindow('img', cv2.WINDOW_NORMAL)
        #cv2.setWindowProperty('img', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        restart_imshow_window = False
    #cv2.imshow('img',img)
    cv2.imshow('img_w_boxes',img)
    
    # Show timers
    if show_timers == True:
        #st.print_all()
        st.print_pretty()
    # Handle user input
    waitkey_in = cv2.waitKey(1) & 0xFF
    if waitkey_in == ord('q'): # Exit
        sys.exit()
    elif waitkey_in == ord('w'): # Up
        if cam_ctrl.img_add_en == True:
            cam_ctrl.move_img_add("up")
        else:
            cam_ctrl.move_corner_direction("up")
    elif waitkey_in == ord('s'): # Down
        if cam_ctrl.img_add_en == True:
            cam_ctrl.move_img_add("down")
        else:
            cam_ctrl.move_corner_direction("down")
    elif waitkey_in == ord('a'): # Left
        if cam_ctrl.img_add_en == True:
            cam_ctrl.move_img_add("left")
        else:
            cam_ctrl.move_corner_direction("left")
    elif waitkey_in == ord('d'): # Right
        if cam_ctrl.img_add_en == True:
            cam_ctrl.move_img_add("right")
        else:
            cam_ctrl.move_corner_direction("right")
    elif waitkey_in == ord('z'): # In
        if cam_ctrl.img_add_en == True:
            cam_ctrl.zoom_img_add("in")
        else:
            cam_ctrl.zoom_cursor_in_out("in")
    elif waitkey_in == ord('x'): # Out
        if cam_ctrl.img_add_en == True:
            cam_ctrl.zoom_img_add("out")
        else:
            cam_ctrl.zoom_cursor_in_out("out")
    #elif waitkey_in == ord('1'): # DBG Info #1
    #    scaler_crop = cam_ctrl.get_scaler_crop()
    #    print("scaler_crop: "+str(scaler_crop))
    #elif waitkey_in == ord('2'): # DBG Info #2
    #    lens_position = cam_ctrl.get_lens_position()
    #    print("lens_position: "+str(lens_position))
    elif waitkey_in == ord('1'): # DBG Info #1
        scaler_crop = cam_ctrl.get_scaler_crop()
        print("scaler_crop: "+str(scaler_crop))
    elif waitkey_in == ord('2'): # DBG Info #2
        lens_position = cam_ctrl.get_lens_position()
        print("lens_position: "+str(lens_position))
    elif waitkey_in == ord('3'): # DBG Info #3
        if show_timers == True:
            show_timers = False
        else:
            show_timers = True
    elif waitkey_in == ord('4'): # DBG Info #4
        if cam_ctrl.img_add_init == True:
            if cam_ctrl.img_add_en == True:
                cam_ctrl.img_add_en = False
            else:
                cam_ctrl.img_add_en = True
    elif waitkey_in == ord('5'): # DBG Info #5
        if cam_ctrl.img_add_init == False:
            cam_ctrl.init_img_add(img_add_path)
        else:
            if cam_ctrl.img_transparent_feature == True:
                cam_ctrl.init_img_add(img_add_path,False)
            else:
                cam_ctrl.init_img_add(img_add_path,True)

    
 


