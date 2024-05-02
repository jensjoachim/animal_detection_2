from stitching import Stitcher
from stitching.images import Images
from stitching.cropper import Cropper
from stitching.seam_finder import SeamFinder
from stitching.exposure_error_compensator import ExposureErrorCompensator
from stitching.blender import Blender
from stitching.warper import Warper

from picamera2 import Picamera2
from libcamera import Transform
from libcamera import controls

import cv2
import time
import sys
import os
import inspect


import pickle

# Get root directory of project to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
sys.path.insert(0,parent_dir)

# Import local packages / modules
from modules import sampling_timers

#### Set settings for image input of stitcher

settings_input = {}
# Set option to use rpi camera of set of pictures
settings_input["cam_en"]        = True
#settings_input["cam_en"]       = False
#settings_input["cam_dim"]       = (576,324)    # registration_576,324     11.2
#settings_input["cam_dim"]       = (768,432)    # registration_76xx432      8.2
#settings_input["cam_dim"]       = (960,540)    # registration_960x540      7.5
#settings_input["cam_dim"]       = (1152,648)   # registration_1920x1080    6.5
#settings_input["cam_dim"]       = (1920,1080)  # registration_1920x1080    3.6
settings_input["cam_dim"]       = (2304,1296)  # registration_1920x1080    2.5
#settings_input["cam_dim"]       = (4608,2592)  # registration_1920x1080    0.6
settings_input["image_paths"]   = ['../o_0.png','../o_1.png','../o_2.png']
# Set to use image stitching or video stitcking, only calculating registration data once
settings_input["vid_stitch_en"] = True
# Change contrant and brightness if image before it's used for sticthing
settings_input["sw_con_bright_en"] = 0
# Lock finder region (only makes sense for video stitcking)
settings_input["finder_lock"] = False


#### Set settings for stitcher

#settings_stitcher = {"confidence_threshold": 0.4, "compensator": "no", "blender_type": "no", "finder": "no"}
settings_stitcher = {"confidence_threshold": 0.4}
#settings_stitcher = {"confidence_threshold": 0.3, "compensator": "no", "blender_type": "no", "finder": "no"}
#settings_stitcher = {"detector": "sift", "confidence_threshold": 0.2, "blender_type": "no", "finder": "no"} # Good
#settings_stitcher = {"detector": "sift", "confidence_threshold": 0.1, "compensator": "no", "blender_type": "no", "finder": "no","warper_type": "cylindrical"} # Good
#settings_stitcher = {"detector": "orb", "confidence_threshold": 0.7, "nfeatures": 500, "adjuster": "ray","warper_type": "cylindrical"} # Good
settings_stitcher = {"detector": "orb", "crop": False, "confidence_threshold": 0.7, "nfeatures": 500, "adjuster": "ray","warper_type": "cylindrical", "compensator": "no", "blender_type": "no", "finder": "no"} # Good
settings_stitcher = {"detector": "sift", "crop": False, "confidence_threshold": 0.7, "nfeatures": 1500, "adjuster": "ray","warper_type": "cylindrical", "blender_type": "no", "finder": "no"}

settings_stitcher = {"detector": "sift", "crop": False, "confidence_threshold": 0.7, "nfeatures": 1500, "adjuster": "ray","warper_type": "cylindrical", "compensator": "no", "blender_type": "no", "finder": "no"}
#settings_stitcher = {"detector": "orb", "crop": False, "confidence_threshold": 0.7, "nfeatures": 1500, "adjuster": "ray","warper_type": "cylindrical", "blender_type": "no", "finder": "no"}






class VideoStitcher(Stitcher):

    def initialize_stitcher(self,**kwargs):
        super().initialize_stitcher(**kwargs)
        self.cameras = None
        self.cameras_registered = False
        self.lock_seam_mask = False

    def stitch(self, images, feature_masks=[]):
        self.images = Images.of(
            images, self.medium_megapix, self.low_megapix, self.final_megapix
        )

        imgs = self.resize_medium_resolution()
        
        if not self.cameras_registered:
            print("Camera registration: Starting")
            features = self.find_features(imgs, feature_masks)
            print(features)
            matches = self.match_features(features)
            imgs, features, matches = self.subset(imgs, features, matches)
            cameras = self.estimate_camera_parameters(features, matches)
            cameras = self.refine_camera_parameters(features, matches, cameras)
            cameras = self.perform_wave_correction(cameras)
            self.estimate_scale(cameras)
            self.cameras = cameras
            self.cameras_registered = True
            print("Camera registration: OK")

        imgs = self.resize_low_resolution()
        imgs, masks, corners, sizes = self.warp_low_resolution(imgs, self.cameras)
        self.prepare_cropper(imgs, masks, corners, sizes)
        imgs, masks, corners, sizes = self.crop_low_resolution(
            imgs, masks, corners, sizes
        )
        self.estimate_exposure_errors(corners, imgs, masks)
        if self.lock_seam_mask == False:   # No lock
            seam_masks = self.find_seam_masks(imgs, corners, masks)
            self.seam_masks = seam_masks
        else:                     # Auto lock
            try:
                seam_masks = self.seam_masks
            except:
                seam_masks = self.find_seam_masks(imgs, corners, masks)
                self.seam_masks = seam_masks
                
        imgs = self.resize_final_resolution()
        imgs, masks, corners, sizes = self.warp_final_resolution(imgs, self.cameras)
        imgs, masks, corners, sizes = self.crop_final_resolution(
            imgs, masks, corners, sizes
        )
        self.set_masks(masks)
        imgs = self.compensate_exposure_errors(corners, imgs)
        seam_masks = self.resize_seam_masks(seam_masks)

        self.initialize_composition(corners, sizes)
        self.blend_images(imgs, seam_masks, corners)
        return self.create_final_panorama()

    def store_registration(self,print_en,settings_stitcher):
        if not self.cameras_registered:
            print("Camera registration not stored!")
        else:
            dict_pickle = {}
            # Gather camera data
            attr_data_dict_index = ["aspect","focal","ppx","ppy","R","t"]
            attr_data_dict_list = []
            for i in range(len(stitcher.cameras)):
                attr_data_dict = {}
                for attr in attr_data_dict_index:
                    attr_data_dict[attr] = getattr(stitcher.cameras[i], attr)
                attr_data_dict_list.append(attr_data_dict)
            dict_pickle["cameras"] = attr_data_dict_list
            # Print camera data
            if print_en:
                print("Camera data to be stored:")
                print(attr_data_dict_list)
            # Store "finder lock" setting
            dict_pickle["finder_lock"] = self.lock_seam_mask
            # Store stitcher setting
            dict_pickle["settings_stitcher"] = settings_stitcher
            # Store data
            with open('registration', 'wb') as file:
                pickle.dump(dict_pickle, file)
            # Done
            print("Camera registration stored!")

    def load_registration(self,print_en,load_settings_en=True):
        # Load camera data
        with open('registration', 'rb') as file:
            dict_pickle = pickle.load(file)
            attr_data_dict_list_in = dict_pickle["cameras"]
            lock_seam_mask = dict_pickle["finder_lock"]
            settings_stitcher = dict_pickle["settings_stitcher"]
        # Re-init stitcher
        if load_settings_en:
            self.initialize_stitcher(**settings_stitcher)
            self.lock_seam_mask = lock_seam_mask
        if print_en:
            print("Camera data loaded:")
            print(attr_data_dict_list_in)
        # Make tuple of CameraParams
        new_cam_param_tuple = ()
        for i in range(len(attr_data_dict_list_in)):
            new_cam_param = cv2.detail.CameraParams()
            for keys, value in attr_data_dict_list_in[i].items():
                setattr(new_cam_param,keys,value)
            new_cam_param_tuple = new_cam_param_tuple + (new_cam_param,)
        # Overwrite tupe in stitcher
        self.cameras = new_cam_param_tuple
        # Extra
        self.estimate_scale(self.cameras)
        # Set registration flag
        self.cameras_registered = True
        # Done
        print("Camera registration loaded")
        

# Init get image function
def init_get_imgs(**settings):
    if settings["cam_en"] == True:
        global picam1
        global picam2
        picam1 = Picamera2(1)
        time.sleep(0.5)
        picam2 = Picamera2(0)
        time.sleep(0.5)
        picam1.configure(picam1.create_preview_configuration(raw={"size":(4608,2592)},main={"format": 'RGB888', "size": settings["cam_dim"]},transform=Transform(hflip=True,vflip=True)))
        picam2.configure(picam2.create_preview_configuration(raw={"size":(4608,2592)},main={"format": 'RGB888', "size": settings["cam_dim"]},transform=Transform(hflip=True,vflip=True)))
        picam1.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 0.0})
        picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 0.0})
        #picam1.set_controls({"AfMode": controls.AfModeEnum.Continuous, "AfSpeed": controls.AfSpeedEnum.Fast})
        #picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous, "AfSpeed": controls.AfSpeedEnum.Fast})
        picam1.start()
        picam2.start()
        time.sleep(2)
        picam1.capture_array()
        picam2.capture_array()

        metadata = picam1.capture_metadata()
        print(metadata)

        if False:
            for i in range(10):
                picam1.capture_array()
                picam2.capture_array()
                picam1.capture_metadata()
                picam2.capture_metadata()
                time.sleep(0.1)

            metadata = picam1.capture_metadata()
            print(metadata)
            img = picam2.capture_array()
            print(img.shape)
                
            #(buffer, ), metadata = picam1.capture_buffers(["main"])
            #img = picam2.helpers.make_array(buffer, picam1.camera_configuration()["main"])
            #print(metadata)
            #print(img.shape)

            #picam1.stop()
            #print(picam1.sensor_modes)
            
            exit(0)

def get_imgs(**settings):
    imgs = []
    if settings["cam_en"] == False:
        image_paths = settings["image_paths"]
        for i in range(len(image_paths)):
            img_in = cv2.imread(image_paths[i])
            imgs.append(img_in)
    else:
        global picam1
        global picam2
        imgs.append(picam1.capture_array())
        imgs.append(picam2.capture_array())
    return imgs

# Normal stitcher class or vidoe stitch
def init_stitcher(vid_stitch_en,**settings_stitcher):
    if vid_stitch_en == True:
        return VideoStitcher(**settings_stitcher)
    else:
        return Stitcher(**settings_stitcher)



def sw_contrast_brightness(imgs_in,**settings):
    # Disabled
    if settings["sw_con_bright_en"] == 0:
        return imgs_in
    # Two contranst brightness functions
    imgs_out = []
    for img in imgs_in:
        if settings["sw_con_bright_en"] == 1:
            # Option 1
            #alpha = 2.0 # Contrast control
            #beta = 10 # Brightness control
            alpha = 3.0 # Contrast control
            beta = -100 # Brightness control
            imgs_out.append(cv2.convertScaleAbs(img, alpha=alpha, beta=beta))
        elif settings["sw_con_bright_en"] == 2:
            # Option 2
            #contrast = 2 # Contrast control ( 0 to 127)
            #brightness = 0 # Brightness control (0-100)
            contrast = 2 # Contrast control ( 0 to 127)
            brightness = 0 # Brightness control (0-100)
            brightness = 100
            imgs_out.append(cv2.addWeighted(img, contrast, img, 0, brightness))
        else:
            print("inspect.stack()[0][3]: Wrong option: "+str(settings["sw_con_bright_en"]))
            sys.exit(1)
    return imgs_out       

# Init Camera
init_get_imgs(**settings_input)

# Init stitcher
stitcher = init_stitcher(settings_input["vid_stitch_en"],**settings_stitcher)
#stitcher.load_registration(False)

# Set sampling timers
st = sampling_timers.sampling_timers()
st.add("main",4)
st.add("stitch",4)

## Debug
#print("Print dir:")
#print(dir(stitcher))
#print("Print dict:")
#print(stitcher.__dict__)
#sys.exit(1)

# On first loop start stitching and open image windows
init_stitch_success = True
restart_imshow_window = True

# Run loop
while True:
    st.start("main")
    # Get images
    imgs = []
    imgs = get_imgs(**settings_input)
    imgs = sw_contrast_brightness(imgs,**settings_input)
    # Try to stitch images
    if init_stitch_success == True:
        try:
            st.start("stitch")
            panorama = stitcher.stitch(imgs)
            st.stop("stitch")
        except:
            init_stitch_success = False
            print("Stitching failed!")
    # Show panorama image or input images in cases init stitch fails
    if init_stitch_success == False:
        # If stitching failed open images
        if restart_imshow_window == True:
            for i in range(len(imgs)):
                cv2.namedWindow("img_"+str(i), cv2.WINDOW_NORMAL)
                cv2.setWindowProperty("img_"+str(i), cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        for i in range(len(imgs)):
            cv2.imshow("img_"+str(i),imgs[i])
    else:        
        # Show first panorama
        if restart_imshow_window == True:
            cv2.namedWindow('final', cv2.WINDOW_NORMAL)
            cv2.setWindowProperty('final', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow('final',panorama)
    restart_imshow_window = False
    # Handle keybaord input
    waitkey_in = cv2.waitKey(1) & 0xFF
    if waitkey_in == ord('q'): # Exit
        sys.exit()
    if waitkey_in == ord('r'): # Recalc stitch registration
        stitcher = init_stitcher(settings_input["vid_stitch_en"],**settings_stitcher)
        cv2.destroyAllWindows()
        init_stitch_success = True
        restart_imshow_window = True
    if waitkey_in == ord('s'): # Store camera registration
        stitcher.store_registration(False,settings_stitcher)
    if waitkey_in == ord('x'): # Load camera registration
        stitcher = init_stitcher(settings_input["vid_stitch_en"],**settings_stitcher)
        stitcher.load_registration(False)
        cv2.destroyAllWindows()
        init_stitch_success = True
        restart_imshow_window = True
    if waitkey_in == ord('c'): # Crop on/off
        settings_input["finder_lock"] = False
        stitcher.lock_seam_mask = False
        if settings_stitcher["crop"] == False:
            stitcher.cropper = Cropper(True)
            settings_stitcher["crop"] = stitcher.DEFAULT_SETTINGS["crop"]
        else:
            stitcher.cropper = Cropper(False)
            settings_stitcher["crop"] = True
        # Restart window
        cv2.destroyAllWindows()
        restart_imshow_window = True
    if waitkey_in == ord('f'): # Finder ON/OFF
        if settings_stitcher["finder"] == "no":
            stitcher.seam_finder = SeamFinder(stitcher.DEFAULT_SETTINGS["finder"])
            settings_stitcher["finder"] = stitcher.DEFAULT_SETTINGS["finder"]
        else:
            stitcher.seam_finder = SeamFinder("no")
            settings_stitcher["finder"] = "no"
    if waitkey_in == ord('g'): # Finder Lock
        if settings_input["cam_en"] == True:
            if settings_input["finder_lock"] == True:
                settings_input["finder_lock"] = False
                stitcher.lock_seam_mask = False
            else:
                settings_input["finder_lock"] = True
                stitcher.lock_seam_mask = True
    if waitkey_in == ord('t'): # Compesator ON/OFF
        if settings_stitcher["compensator"] == "no":
            stitcher.compensator = ExposureErrorCompensator(stitcher.DEFAULT_SETTINGS["compensator"])
            settings_stitcher["compensator"] = stitcher.DEFAULT_SETTINGS["compensator"]
        else:
            stitcher.compensator = ExposureErrorCompensator("no")
            settings_stitcher["compensator"] = "no"
    if waitkey_in == ord('b'): # Blender ON/OFF
        if settings_stitcher["blender_type"] == "no":
            stitcher.blender = Blender(stitcher.DEFAULT_SETTINGS["blender_type"],stitcher.DEFAULT_SETTINGS["blend_strength"])
            settings_stitcher["blender_type"] = stitcher.DEFAULT_SETTINGS["blender_type"]
        else:
            stitcher.blender = Blender("no")
            settings_stitcher["blender_type"] = "no"
    if waitkey_in == ord('m'): # Change constrast mode
        settings_input["sw_con_bright_en"] = (settings_input["sw_con_bright_en"] + 1) % 3
    if waitkey_in == ord('i'): # Print Info: FPS   
        label_list = ["fps_curr","fps_mean"]
        st.print_pretty(False,label_list)
    if waitkey_in == ord('l'):
        stitcher.jjp_test()
        
