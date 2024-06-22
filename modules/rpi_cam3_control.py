import numpy as np
import cv2
import sys

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


        # Tmp Loop
        restart_imshow_window = True
        running = True
        while running:
            # Check mode is implmented
            if self.image_proc_mode != 0:
                print("Mode Not implemented!")
                running = False
            # Read image
            if self.image_proc_mode == 0:
                img = self.read_cam()
            # Apply offset, zoom, and scale
            c1_x, c1_y, c2_x, c2_y = self.get_cursor_crop(self.cursor_corner,self.cursor_dim)
            img_window = cv2.resize(img[c1_y:c2_y,c1_x:c2_x],self.dim_window,interpolation=self.interpolation)
            # Show image
            if restart_imshow_window == True:
                cv2.namedWindow('img', cv2.WINDOW_NORMAL)
                #cv2.setWindowProperty('img', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                restart_imshow_window = False
            cv2.imshow('img',img_window)
            # Handle user input
            waitkey_in = cv2.waitKey(1) & 0xFF
            if waitkey_in == ord('q'): # Exit
                sys.exit()
            elif waitkey_in == ord('w'): # Up
                self.move_corner_direction("up")
            elif waitkey_in == ord('s'): # Down
                self.move_corner_direction("down")
            elif waitkey_in == ord('a'): # Left
                self.move_corner_direction("left")
            elif waitkey_in == ord('d'): # Right
                self.move_corner_direction("right")

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
                self.dim_cam = dim_ca
    
        # Set source of image
        if self.image_proc_mode == 0:
            # Load picture from drive
            self.debug_image = np.array(cv2.imread(cam_sel))
            self.dim_cam = (self.debug_image.shape[1],self.debug_image.shape[0])
        else:
            # Start Camera
            # (800,600)
            # (1920,1080)
            # (4608,2592)
            self.picam = Picamera2()
            self.picam.configure(picam.create_preview_configuration(main={"format": 'RGB888', "size": self.dim_cam},transform=Transform(hflip=True,vflip=True)))
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
        self.max_zoom = self.dim_window_in_cam_max[0] / self.dim_window[0]
        self.min_zoom = 0.5
        print("max_zoom: "+str(self.max_zoom))
        print("min_zoom: "+str(self.min_zoom))
        # Set corner cursor and cursor size
        self.cursor_corner = (int(round((self.dim_cam[0]-self.dim_window_in_cam_max[0])/2)),int(round((self.dim_cam[1]-self.dim_window_in_cam_max[1])/2)))
        self.cursor_dim = self.dim_window_in_cam_max
        #self.cursor_crop = self.get_cursor_crop(self.cursor_corner,self.cursor_dim)
        cursor_crop = self.get_cursor_crop(self.cursor_corner,self.cursor_dim)
        print("cursor_corner: "+str(self.cursor_corner))
        print("cursor_dim   : "+str(self.cursor_dim))
        print("cursor_crop  : "+str(cursor_crop))
        # Set cursor move step
        self.move_step_size = 0.25

    def read_cam(self):
        if self.image_proc_mode == 0:
            return self.debug_image
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
        # Print Debug
        print("cursor_corner: "+str(self.cursor_corner))
        print("cursor_dim   : "+str(self.cursor_dim))
        print("cursor_crop  : "+str(cursor_crop))

    def zoom_cursor(self,inout):
        print("Not implemented!")
