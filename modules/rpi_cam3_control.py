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

        # Don't add image in front if not initated
        self.img_add_init = False

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
        if self.img_add_en == False:
            if self.image_proc_mode == 0:
                return self.debug_image.copy()
            else:
                return self.picam.capture_array()
        else:
            if self.image_proc_mode == 0:
                return self.get_img_add(self.debug_image.copy())
            else:
                return self.get_img_add(self.picam.capture_array())

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

    def init_img_add(self,img_add_path,img_transparent_feature=True):
        if self.image_proc_mode == 0 or self.image_proc_mode == 1:
            self.img_add_init = True
            self.img_add_en = True
            self.img_transparent_feature = img_transparent_feature
            if img_transparent_feature == True:
                self.img_add_original = cv2.imread(img_add_path, cv2.IMREAD_UNCHANGED)
            else:
                self.img_add_original = cv2.imread(img_add_path)
            self.img_add = self.img_add_original
            self.img_pos = (self.dim_window[0]/2,self.dim_window[1]/2)
            self.img_pos_step = 0.25*max(self.img_add_original.shape[1],self.img_add_original.shape[0])
            self.img_zoom = 1.0
            self.img_zoom_step = 0.25
            self.img_outside_border = False
            self.update_get_img()
            self.dbg_img_add()

    def update_get_img(self):
        # Start to zoom image
        #img_zoom = 
        # Update image location
        self.img_location = (round(self.img_pos[0]-self.img_add_original.shape[1]/2),
                             round(self.img_pos[0]-self.img_add_original.shape[1]/2)+self.img_add_original.shape[1],
                             round(self.img_pos[1]-self.img_add_original.shape[0]/2),
                             round(self.img_pos[1]-self.img_add_original.shape[0]/2)+self.img_add_original.shape[0])
        self.dbg_img_add()
        # Check if all of image is not outside image
        x1,x2,y1,y2 = self.img_location
        self.img_outside_border = False
        if x2 < 0:
            print("add_img outside border: x2")
            self.img_outside_border = True
        if x1 > (self.dim_window[0]-1):
            print("add_img outside border: x1")
            self.img_outside_border = True
        if y2 < 0:
            print("add_img outside border: y2")
            self.img_outside_border = True
        if y1 > (self.dim_window[1]-1):
            print("add_img outside border: y1")
            self.img_outside_border = True
        # Check if image needs to be trimmed
        trim_x1 = 0
        trim_x2 = 0
        trim_y1 = 0
        trim_y2 = 0
        trim = False
        if x1 < 0:
            print("add_img needs to be trimmed: x2")
            trim_x1 = x1*(-1)
            trim = True
        if x2 > (self.dim_window[0]-1):
            print("add_img needs to be trimmed: x1")
            trim_x2 = x2 - (self.dim_window[0]-1)
            trim = True
        if y1 < 0:
            print("add_img needs to be trimmed: y2")
            trim_y1 = y1*(-1)
            trim = True
        if y2 > (self.dim_window[1]-1):
            print("add_img needs to be trimmed: y1")
            trim_y2 = y2 - (self.dim_window[1]-1)
            trim = True
        if trim == True:
            print("trim_x1: "+str(trim_x1))
            print("trim_x2: "+str(trim_x2))
            print("trim_y1: "+str(trim_y1))
            print("trim_y2: "+str(trim_y2))
        # Update position
        x1 = x1+trim_x1
        x2 = x2-trim_x2
        y1 = y1+trim_y1
        y2 = y2-trim_y2
        self.img_location = (x1,x2,y1,y2)
        # Trim image
        self.img_add = self.img_add_original[trim_y1:self.img_add_original.shape[0]-trim_y2,
                                             trim_x1:self.img_add_original.shape[1]-trim_x2]

        self.dbg_img_add()
        
    def dbg_img_add(self):
        print("img_pos:       "+str(self.img_pos))
        print("img_pos_step:  "+str(self.img_pos_step))
        print("img_zoom:      "+str(self.img_zoom))
        print("img_zoom_step: "+str(self.img_zoom_step))
        print("img_location:  "+str(self.img_location))

        #print("X: "+str(self.img_location[1]-self.img_location[0]))
        #print("Y: "+str(self.img_location[3]-self.img_location[2]))
        #print("shape: "+str(self.img_add.shape))
            

    def get_img_add(self,img):
        self.update_get_img()
        if self.img_outside_border == False:
            if self.img_transparent_feature:
                # Split the channels of both images
                b1, g1, r1, a1 = cv2.split(self.img_add)
                #b2, g2, r2 = cv2.split(img[0:self.img_add.shape[0],0:self.img_add.shape[1]])
                #b3, g3, r3 = cv2.split(img[self.img_location[2]:self.img_location[3],self.img_location[0]:self.img_location[1]])
                #print(b1.shape)
                #print(b2.shape)
                #print(b3.shape)
                #print(img.shape)
                #print(self.img_add.shape)
                b2, g2, r2 = cv2.split(img[self.img_location[2]:self.img_location[3],self.img_location[0]:self.img_location[1]])
                # Apply the custom functionelement-wise using vectorize
                def custom_operation(x, y, a):
                    return y if a==0 else x
                vectorized_operation = np.vectorize(custom_operation)
                b = vectorized_operation(b1, b2, a1)
                g = vectorized_operation(g1, g2, a1)
                r = vectorized_operation(r1, r2, a1)
                # Merge the blended channels back into a single image
                blended_image = cv2.merge([b, g, r])
                # Add to img
                #img[0:self.img_add.shape[0],0:self.img_add.shape[1]] = blended_image
                img[self.img_location[2]:self.img_location[3],self.img_location[0]:self.img_location[1]] = blended_image
            else:
                # Add to img
                #img[0:self.img_add.shape[0],0:self.img_add.shape[1]] = self.img_add
                img[self.img_location[2]:self.img_location[3],self.img_location[0]:self.img_location[1]] = self.img_add
        return img
    
    def move_img_add(self,direction):
        x, y = self.img_pos
        # Update position
        if direction == "up":
            y = y - round(self.img_pos_step*self.img_zoom)
        elif direction == "down":
            y = y + round(self.img_pos_step*self.img_zoom)
        elif direction == "left":
            x = x - round(self.img_pos_step*self.img_zoom)
        elif direction == "right":
            x = x + round(self.img_pos_step*self.img_zoom)
        # Update
        self.img_pos = (x,y)
        self.update_get_img()
        

    def zoom_img_add(self,inout):
        self.dbg_img_add()
