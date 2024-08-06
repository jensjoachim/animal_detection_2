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

cam_ctrl = rpi_cam3_control.rpi_cam3_control(0,"test.jpg")
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(1,0)
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(2,0)
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(0,"test.jpg",(400,300))
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(1,0,(400,300))
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(2,0,(400,300))
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(1,0,(400,300),(800,600))



