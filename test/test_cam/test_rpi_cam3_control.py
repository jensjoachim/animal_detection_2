# Import packages
import sys
import os
import cv2

# Get root directory of project to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.insert(0,parent_dir)

# Import local packages / modules
from modules import sampling_timers

from modules import rpi_cam3_control

#cam_ctrl = rpi_cam3_control.rpi_cam3_control(0,"test.jpg")
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(1,0)
cam_ctrl = rpi_cam3_control.rpi_cam3_control(2,0)
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(0,"test.jpg",(400,300))
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(1,0,(400,300))
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(2,0,(400,300))
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(1,0,(400,300),(800,600))



# Tmp Loop
restart_imshow_window = True
running = True
# Setup timers
st = sampling_timers.sampling_timers()
st.add("all",       30)
st.add("read_image",30)
show_timers = False
# Debug handlers
#test_insert_deer = True
test_insert_deer = False
while running:
    
    # Read image
    st.start("all")
    st.start("read_image")
    img = cam_ctrl.read_cam()
    # Add a deer to image
    if cam_ctrl.image_proc_mode == 0 or cam_ctrl.image_proc_mode == 1:
        if test_insert_deer == True:
            cam_ctrl.test_insert_deer_on_pos(img)
            # Apply offset, zoom, and scale
    if cam_ctrl.image_proc_mode == 0 or cam_ctrl.image_proc_mode == 1:
        c1_x, c1_y, c2_x, c2_y = cam_ctrl.get_cursor_crop(cam_ctrl.cursor_corner,cam_ctrl.cursor_dim)
        img_window = cv2.resize(img[c1_y:c2_y,c1_x:c2_x],cam_ctrl.dim_window,interpolation=cam_ctrl.interpolation)
    else:
        img_window = img
    st.stop("read_image")
    # Object detection
    #
    # Add FPS
    #
    #
    # Show image
    if restart_imshow_window == True:
        cv2.namedWindow('img', cv2.WINDOW_NORMAL)
        #cv2.setWindowProperty('img', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        restart_imshow_window = False
    cv2.imshow('img',img_window)
    # Show timers
    if show_timers == True:
        st.print_all()
    # Handle user input
    waitkey_in = cv2.waitKey(1) & 0xFF
    if waitkey_in == ord('q'): # Exit
        sys.exit()
    elif waitkey_in == ord('w'): # Up
        cam_ctrl.move_corner_direction("up")
    elif waitkey_in == ord('s'): # Down
        cam_ctrl.move_corner_direction("down")
    elif waitkey_in == ord('a'): # Left
        cam_ctrl.move_corner_direction("left")
    elif waitkey_in == ord('d'): # Right
        cam_ctrl.move_corner_direction("right")
    elif waitkey_in == ord('z'): # In
        cam_ctrl.zoom_cursor_in_out("in")
    elif waitkey_in == ord('x'): # Out
        cam_ctrl.zoom_cursor_in_out("out")
    elif waitkey_in == ord('1'): # DBG Info #1
        scaler_crop = cam_ctrl.get_scaler_crop()
        print("scaler_crop: "+str(scaler_crop))
    elif waitkey_in == ord('2'): # DBG Info #2
        lens_position = cam_ctrl.get_lens_position()
        print("lens_position: "+str(lens_position))
    elif waitkey_in == ord('3'): # DBG Info #3
        brightness = cam_ctrl.get_brightness()
        print("brightness: "+str(brightness))
    elif waitkey_in == ord('4'): # DBG Info #4
        if show_timers == True:
            show_timers = False
        else:
            show_timers = True
    elif waitkey_in == ord('i'): # Test - Insert deer
        if test_insert_deer == True:
            test_insert_deer = False
        else:
            test_insert_deer = True

    
 


