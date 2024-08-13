import numpy as np
import cv2
import sys
import time

from picamera2 import Picamera2
from libcamera import Transform
from libcamera import controls

class rpi_cam3_control:

    def __init__(self,image_proc_mode,cam_sel,dim_window=-1,dim_cam=-1):

        ################################### 
        # Class Description
        ################################### 
        # Manipulation of image with follwing function: zoom/scale and crop
        # With camera mode "1" this manupulation is done on RPI CAM 3, to
        # save CPU on RPI.

        ################################### 
        # TODO's:
        ###################################
        # - Read camera in a thread and also to processing of commands there.
        #
        #
        
        # Camera image processing mode
        # 0: Debug mode uses a picture on drive, combined with mode "1"
        # 1: Image processing on RPI
        # 2: Image processing on image processor of camera
        self.image_proc_mode = image_proc_mode

        # RPI camera selection
        # 0: or 1: to select RPI camera #1 or #2
        # When Camera image proc mode "0", then set a path to picture
        # Set dimmension of debug window and camera dimmension
        # dim_cam only has meaning in mode "1"
        self.init_cam(cam_sel,dim_window,dim_cam)

        # Image interpolattion when resizing
        self.interpolation = cv2.INTER_NEAREST
        #self.interpolation = cv2.INTER_LINEAR

    def init_cam(self,cam_sel,dim_window,dim_cam):

        # Store in object
        self.cam_sel = cam_sel

        # Set dimmension
        if dim_window == -1:
            # Default
            self.dim_window = (800,600)
        else:
            self.dim_window = dim_window
        # Only use unique camera dim when mode "1"
        if self.image_proc_mode == 1:
            if dim_cam == -1:
                # Set max dimmension of RPI cam 3
                self.dim_cam = (4608,2592)
            else:
                self.dim_cam = dim_cam
        # Use max dimmension when mode 2
        if self.image_proc_mode == 2:
            self.dim_cam = (4608,2592)
            
        # Set source of image
        if self.image_proc_mode == 0:
            # Load picture from drive
            self.debug_image = np.array(cv2.imread(self.cam_sel))
            self.dim_cam = (self.debug_image.shape[1],self.debug_image.shape[0])
        elif self.image_proc_mode == 1:
            # Start Camera
            # (800,600)
            # (1920,1080)
            # (4608,2592)
            self.picam = Picamera2(self.cam_sel)
            self.picam.configure(self.picam.create_preview_configuration(main={"format": 'RGB888', "size": self.dim_cam},transform=Transform(hflip=True,vflip=True)))
            self.picam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 0.0})
            self.picam.start()
        else:
            self.picam = Picamera2(self.cam_sel)
            self.picam.configure(self.picam.create_preview_configuration(raw={"size":(4608,2592)},main={"format": 'RGB888', "size": self.dim_window},transform=Transform(hflip=True,vflip=True)))
            
            self.picam.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 0.0})
            self.picam.start()

        # Print settings
        print("rpi_cam3_control Settings:")
        print("image_proc_mode: "+str(self.image_proc_mode))
        print("cam_sel        : "+str(self.cam_sel))
        print("dim_window     : "+str(self.dim_window))
        print("dim_cam        : "+str(self.dim_cam))

        # Calculate on window dimension
        ratio_window = self.dim_window[0]/self.dim_window[1]
        ratio_cam = self.dim_cam[0]/self.dim_cam[1]
        print("ratio_window: "+str(ratio_window))
        print("ratio_cam   : "+str(ratio_cam))
        # Biggest frame window in cam dimension fitted to either X or Y size
        if ratio_window > ratio_cam:
            self.dim_window_in_cam_max = (self.dim_cam[0],int(round(1/ratio_window*self.dim_cam[1])))
        else:
            self.dim_window_in_cam_max = (int(round(1/ratio_window*self.dim_cam[0])),self.dim_cam[1])
        print("dim_window_in_cam_max: "+str(self.dim_window_in_cam_max))
        # Set min/max zoom
        self.zoom_max = self.dim_window_in_cam_max[0] / self.dim_window[0]
        #self.zoom_min = 0.5
        #self.zoom_step_size = 0.5
        self.zoom_min = 0.25
        self.zoom_step_size = 0.25
        # Calc nearest even zoom
        self.zoom_max_even = round(self.zoom_max / self.zoom_step_size)*self.zoom_step_size - self.zoom_step_size
        self.cursor_zoom = self.zoom_max
        # Set corner cursor and cursor size
        self.cursor_corner = (int(round((self.dim_cam[0]-self.dim_window_in_cam_max[0])/2)),int(round((self.dim_cam[1]-self.dim_window_in_cam_max[1])/2)))
        self.cursor_dim = self.dim_window_in_cam_max
        cursor_crop = self.get_cursor_crop(self.cursor_corner,self.cursor_dim)
        print("cursor_zoom  : "+str(self.cursor_zoom))
        print("cursor_corner: "+str(self.cursor_corner))
        print("cursor_dim   : "+str(self.cursor_dim))
        print("cursor_crop  : "+str(cursor_crop))
        # Set cursor move step
        self.move_step_size = 0.25

    def read_cam(self):
        if self.image_proc_mode == 0:
            return self.debug_image.copy()
        else:
            return self.picam.capture_array()

    def get_cursor_crop(self,corner,dim):
        return (corner[0],corner[1],corner[0]+dim[0]-1,corner[1]+dim[1]-1)

    def move_corner_direction(self,direction):
        # Calc pixel step size
        if self.cursor_dim[0] > self.cursor_dim[1]:
            move_step_pixel = round(self.cursor_dim[1] * self.move_step_size)
        else:
            move_step_pixel = round(self.cursor_dim[0] * self.move_step_size)
        print("move_step_pixel: "+str(move_step_pixel))
        # Add to corner
        x, y = self.cursor_corner
        if direction == "up":
            y = y - move_step_pixel
        elif direction == "down":
            y = y + move_step_pixel
        elif direction == "left":
            x = x - move_step_pixel
        elif direction == "right":
            x = x + move_step_pixel
        # Move corner
        self.move_corner((x,y))

    def move_corner(self,cursor_corner):
        # Check if within camera dimmension
        c1_x, c1_y, c2_x, c2_y = self.get_cursor_crop(cursor_corner,self.cursor_dim)
        c1_x_new = c1_x
        c1_y_new = c1_y
        c2_x_new = c2_x
        c2_y_new = c2_y
        if c1_x < 0:
            c1_x_new = 0
            c2_x_new = c2_x - c1_x
        if c2_x > self.dim_cam[0]-1:
            c1_x_new = c1_x - (c2_x-(self.dim_cam[0]-1))
            c2_x_new = self.dim_cam[0]-1
        if c1_y < 0:
            c1_y_new = 0
            c2_y_new = c2_y - c1_y
        if c2_y > self.dim_cam[1]-1:
            c1_y_new = c1_y - (c2_y-(self.dim_cam[1]-1))
            c2_y_new = self.dim_cam[1]-1
        cursor_crop = (c1_x_new,c1_y_new,c2_x_new,c2_y_new)
        self.cursor_corner = (c1_x_new,c1_y_new)
        # Apply to camera processor
        if self.image_proc_mode == 2:
            self.set_scaler_crop(self.cursor_corner,self.cursor_dim)
        # Print Debug
        print("cursor_zoom  : "+str(self.cursor_zoom))
        print("cursor_corner: "+str(self.cursor_corner))
        print("cursor_dim   : "+str(self.cursor_dim))
        print("cursor_crop  : "+str(cursor_crop))

    def zoom_cursor_in_out(self,inout):
        if inout == "in":
            zoom = self.cursor_zoom - self.zoom_step_size
            # if last zoom was max set even zoom
            if self.cursor_zoom == self.zoom_max:
                zoom = self.zoom_max_even
        elif inout == "out":
            zoom = self.cursor_zoom + self.zoom_step_size
        self.zoom_cursor_change(zoom)
        
    def zoom_cursor_change(self,zoom):
        # Check if within min/max
        if zoom < self.zoom_min:
            zoom = self.zoom_min
        if zoom > self.zoom_max:
            zoom = self.zoom_max
        self.cursor_zoom = zoom
        # Apply zoom dim
        x, y = self.dim_window
        cursor_dim_new = (round(x*zoom),round(y*zoom))
        #print("cursor_dim_old   : "+str(self.cursor_dim))
        #print("cursor_dim_new   : "+str(cursor_dim_new))
        # Apply zoom corner
        x = round(self.cursor_corner[0]+(self.cursor_dim[0] - cursor_dim_new[0])/2)
        y = round(self.cursor_corner[1]+(self.cursor_dim[1] - cursor_dim_new[1])/2)
        cursor_corner_new = (x,y)
        #print("cursor_corner_old: "+str(self.cursor_corner))
        #print("cursor_corner_new: "+str(cursor_corner_new))
        # Update values
        self.cursor_dim = cursor_dim_new
        self.cursor_corner = cursor_corner_new
        # Check if within camera dimmension
        c1_x, c1_y, c2_x, c2_y = self.get_cursor_crop(self.cursor_corner,self.cursor_dim)
        c1_x_new = c1_x
        c1_y_new = c1_y
        c2_x_new = c2_x
        c2_y_new = c2_y
        if c1_x < 0:
            c1_x_new = 0
            c2_x_new = c2_x - c1_x
        if c2_x > self.dim_cam[0]-1:
            c1_x_new = c1_x - (c2_x-(self.dim_cam[0]-1))
            c2_x_new = self.dim_cam[0]-1
        if c1_y < 0:
            c1_y_new = 0
            c2_y_new = c2_y - c1_y
        if c2_y > self.dim_cam[1]-1:
            c1_y_new = c1_y - (c2_y-(self.dim_cam[1]-1))
            c2_y_new = self.dim_cam[1]-1
        cursor_crop = (c1_x_new,c1_y_new,c2_x_new,c2_y_new)
        self.cursor_corner = (c1_x_new,c1_y_new)
        # Apply to camera processor
        if self.image_proc_mode == 2:
            self.set_scaler_crop(self.cursor_corner,self.cursor_dim)
        # Print Debug
        print("cursor_zoom  : "+str(self.cursor_zoom))
        print("cursor_corner: "+str(self.cursor_corner))
        print("cursor_dim   : "+str(self.cursor_dim))
        print("cursor_crop  : "+str(cursor_crop))

    def set_scaler_crop(self,cursor_corner,cursor_dim):
        self.picam.set_controls({"ScalerCrop": cursor_corner+cursor_dim})

    def get_scaler_crop(self):
        return self.picam.capture_metadata()['ScalerCrop']

    def get_lens_position(self):
        return self.picam.capture_metadata()['LensPosition']

    def get_brightness(self):
        return self.picam.capture_metadata()['Brightness']

    def test_insert_deer_on_pos(self,img):
        print("Not implemented")
