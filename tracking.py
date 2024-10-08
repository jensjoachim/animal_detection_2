# Import packages
import sys
import os
import cv2
import time
import numpy as np

# Import local packages / modules
from modules import sampling_timers
from modules import rpi_cam3_control
from modules import object_detection

model_dir = "object_detection_models/18_08_2022_efficientdet-lite1_e75_b32_s2000/"
obj_det = object_detection.object_detection(True,True,model_dir)
#obj_det = object_detection.object_detection(True,False,model_dir)

#cam_ctrl = rpi_cam3_control.rpi_cam3_control(0,"test.jpg")
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(1,0)
cam_ctrl = rpi_cam3_control.rpi_cam3_control(2,0)

# Tmp Loop
restart_imshow_window = True
running = True
# Setup timers
st = sampling_timers.sampling_timers()
st.add("all",       50)
st.add("read_image",50)
st.add("obj_detect",50)
st.add("draw_img"  ,50)
# Debug handlers
show_timers = True
cam_ctrl.img_add_en = False
img_add_path = "resources/deer_trans_bg_0.png"
if cam_ctrl.img_add_en == True:
    cam_ctrl.init_img_add(img_add_path,False)
    cam_ctrl.zoom_img_add("in")
    cam_ctrl.zoom_img_add("in")
while running:

    #
    # Read image
    #
    st.start("all")
    st.start("read_image")
    img = cam_ctrl.read_cam()
    st.stop("read_image")

    if True:
        #
        # Object detection
        #
        det_area = (100,699,0,599)
        st.start("obj_detect")
        detections = obj_det.run_detector(img[det_area[2]:det_area[3],det_area[0]:det_area[1]])
        st.stop("obj_detect")
        
        #
        # Draw detection area
        #
        st.start("draw_img")
        obj_det.draw_detection_area(0,img[det_area[2]:det_area[3],det_area[0]:det_area[1]])
        
        #
        # Add dectections boxes on image
        #
        obj_det.draw_boxes(img[det_area[2]:det_area[3],det_area[0]:det_area[1]],0,detections["detection_boxes"],detections["detection_classes"],detections["detection_scores"],max_boxes=10,min_score=0.5)
    
        #
        # Find strongest detection and add
        #
        (found_max,max_score,list_index,obj_index) = obj_det.find_strongest_detection([detections],0)
        obj_det.draw_strongest_detection([detections],max_score,list_index,obj_index,img[det_area[2]:det_area[3],det_area[0]:det_area[1]],'#0000ff',0)
        st.stop("draw_img")

        #
        # Set feedback
        #
        if found_max and cam_ctrl.scaler_crop_in_sync:
            thr_zoom_in = 0.35
            thr_zoom_out = 0.65
    
            # Get box details
            box = detections['detection_boxes'][obj_index]
            box_width = (box[3]-box[1],box[2]-box[0])
            box_center = ((box[1]+box_width[0]/2),(box[0]+box_width[1]/2))
            # DBG
            print(box_width)
            print(box_center)
            # Apply move
            # window/obj_are ration * object detect
            x_ratio = 1.0*(det_area[1]-det_area[0]+1)/cam_ctrl.dim_window[0]
            y_ratio = 1.0*(det_area[3]-det_area[2]+1)/cam_ctrl.dim_window[1]
            print("x_ratio: "+str(x_ratio))
            print("y_ratio: "+str(y_ratio))
            x_window_pixels = det_area[1]-det_area[0]+1
            y_window_pixels = det_area[3]-det_area[2]+1
            print("x_window_pixels: "+str(x_window_pixels))
            print("y_window_pixels: "+str(y_window_pixels))
            x_cam_pixels = x_window_pixels * cam_ctrl.cursor_zoom
            y_cam_pixels = y_window_pixels * cam_ctrl.cursor_zoom
            print("x_cam_pixels: "+str(x_cam_pixels))
            print("y_cam_pixels: "+str(y_cam_pixels))
            x_cam_pixels_add = round(x_cam_pixels * (box_center[0] - 0.5))
            y_cam_pixels_add = round(y_cam_pixels * (box_center[1] - 0.5))
            print("x_cam_pixels_add: "+str(x_cam_pixels_add))
            print("y_cam_pixels_add: "+str(y_cam_pixels_add))
            x_new = cam_ctrl.cursor_corner[0] + x_cam_pixels_add
            y_new = cam_ctrl.cursor_corner[1] + y_cam_pixels_add
            #x_new = cam_ctrl.cursor_corner[0] - x_cam_pixels_add
            #y_new = cam_ctrl.cursor_corner[1] - y_cam_pixels_add
            x = cam_ctrl.cursor_corner[0]
            y = cam_ctrl.cursor_corner[1]
            print("x: "+str(x))
            print("y: "+str(y))
            print("x_new: "+str(x_new))
            print("y_new: "+str(y_new))
            cam_ctrl.move_corner((x_new,y_new))
            
            # Check if zoom is needed
            if box_width[0] > thr_zoom_out or box_width[1] > thr_zoom_out:
                cam_ctrl.zoom_cursor_in_out("out")
            if box_width[0] < thr_zoom_in or box_width[1] < thr_zoom_in:
                cam_ctrl.zoom_cursor_in_out("in")
    
            print("Zoom: "+str(cam_ctrl.cursor_zoom))
            print("Cursor dim: "+str(cam_ctrl.cursor_dim))


    
    #
    # Show image
    #
    if restart_imshow_window == True:
        cv2.namedWindow('img', cv2.WINDOW_NORMAL)
        #cv2.setWindowProperty('img', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        restart_imshow_window = False
    cv2.imshow('img',img)
    
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

    
 


