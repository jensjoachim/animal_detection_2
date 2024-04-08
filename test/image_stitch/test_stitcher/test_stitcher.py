from stitching import Stitcher
from stitching.images import Images
from stitching.cropper import Cropper
from stitching.seam_finder import SeamFinder
from stitching.exposure_error_compensator import ExposureErrorCompensator
from stitching.blender import Blender

from picamera2 import Picamera2
from libcamera import Transform
from libcamera import controls

import cv2
import time
import sys
import os
import inspect

# Get root directory of project to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
sys.path.insert(0,parent_dir)

# Import local packages / modules
from modules import sampling_timers

#### Set settings for image input of stitcher

settings_input = {}
# Set option to use rpi camera of set of pictures
#settings_input["cam_en"]        = True
settings_input["cam_en"]       = False
#settings_input["cam_dim"]       = (800,600)
settings_input["cam_dim"]       = (1920, 1080)
#settings_input["cam_dim"]       = (4608,2592)
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

    def initialize_stitcher(self, **kwargs):
        super().initialize_stitcher(**kwargs)
        self.cameras = None
        self.cameras_registered = False

    def stitch(self, images, lock_seam_mask=False, feature_masks=[]):
        self.images = Images.of(
            images, self.medium_megapix, self.low_megapix, self.final_megapix
        )

        imgs = self.resize_medium_resolution()
        
        if not self.cameras_registered:
            print("Camera registration: Starting")
            features = self.find_features(imgs, feature_masks)
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
        if lock_seam_mask == False:
            seam_masks = self.find_seam_masks(imgs, corners, masks)
            self.seam_masks = seam_masks
        else:
            seam_masks = self.seam_masks

        imgs = self.resize_final_resolution()
        imgs, masks, corners, sizes = self.warp_final_resolution(imgs, self.cameras)
        imgs, masks, corners, sizes = self.crop_final_resolution(
            imgs, masks, corners, sizes
        )
        self.set_masks(masks)
        imgs = self.compensate_exposure_errors(corners, imgs)
        #if lock_seam_mask == False:
        #    seam_masks = self.resize_seam_masks(seam_masks)
        #    self.seam_masks_resize = seam_masks
        #else:
        #    seam_masks = self.seam_masks_resize
        seam_masks = self.resize_seam_masks(seam_masks)

        self.initialize_composition(corners, sizes)
        self.blend_images(imgs, seam_masks, corners)
        return self.create_final_panorama()

# Init get image function
def init_get_imgs(**settings):
    if settings["cam_en"] == True:
        global picam1
        global picam2
        picam1 = Picamera2(1)
        time.sleep(0.5)
        picam2 = Picamera2(0)
        time.sleep(0.5)
        picam1.configure(picam1.create_preview_configuration(main={"format": 'RGB888', "size": cam_dim},transform=Transform(hflip=True,vflip=True)))
        picam2.configure(picam2.create_preview_configuration(main={"format": 'RGB888', "size": cam_dim},transform=Transform(hflip=True,vflip=True)))
        picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 0.0})
        picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 0.0})
        #picam1.set_controls({"AfMode": controls.AfModeEnum.Continuous, "AfSpeed": controls.AfSpeedEnum.Fast})
        #picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous, "AfSpeed": controls.AfSpeedEnum.Fast})
        picam1.start()
        picam2.start()
        time.sleep(2)
        picam1.capture_array()
        picam2.capture_array()

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
            imgs_out.append(cv2.addWeighted(img, contrast, img, 0, brightness))
        else:
            print("inspect.stack()[0][3]: Wrong option: "+str(settings["sw_con_bright_en"]))
            sys.exit(1)
    return imgs_out       

# Init Camera
init_get_imgs(**settings_input)

# Init stitcher
stitcher = init_stitcher(settings_input["vid_stitch_en"],**settings_stitcher)

# Set sampling timers
st = sampling_timers.sampling_timers()
st.add("main",4)
st.add("stitch",4)

# Debug
#print("Print dir:")
#print(dir(stitcher))
#print("Print dict:")
#print(stitcher.__dict__)
#print("Print dict setting:")
#print(stitcher.settings_stitcher)
#print("Print dict setting:")
#print(stitcher.settings_stitcher["blender_type"])
#stitcher.settings_stitcher["blender_type"] = "no"
#print(stitcher.settings_stitcher["blender_type"])
#print(stitcher.settings_stitcher["blender_type"])


# First panorama will set registration
imgs = get_imgs(**settings_input)
imgs = sw_contrast_brightness(imgs,**settings_input)
stitch_success = True
try:
    panorama = stitcher.stitch(imgs)
except:
    stitch_success = False
    print("Stitching failed!")

# If stitching failed opne images
if stitch_success == False:
    for i in range(len(imgs)):
        cv2.namedWindow("img_"+str(i), cv2.WINDOW_NORMAL)
        cv2.setWindowProperty("img_"+str(i), cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    while True:
        for i in range(len(imgs)):
            cv2.imshow("img_"+str(i),imgs[i])
            waitkey_in = cv2.waitKey(1) & 0xFF
            if waitkey_in == ord('q'): # Exit
                sys.exit()
    
# Show first image
cv2.namedWindow('final', cv2.WINDOW_NORMAL)
cv2.setWindowProperty('final', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.imshow('final',panorama)
cv2.waitKey(1)

# Run loop
while True:
    st.start("main")
    # Stitch images
    imgs = []
    imgs = get_imgs(**settings_input)
    imgs = sw_contrast_brightness(imgs,**settings_input)
    st.start("stitch")
    panorama = stitcher.stitch(imgs,settings_input["finder_lock"])
    st.stop("stitch")
    # Show
    cv2.imshow('final',panorama)
    # Handle keybaord input
    waitkey_in = cv2.waitKey(1) & 0xFF
    if waitkey_in == ord('q'): # Exit
        sys.exit()
    if waitkey_in == ord('r'): # Recalc stitch registration
        stitcher = init_stitcher(settings_input["vid_stitch_en"],**settings_stitcher)
        panorama = stitcher.stitch(imgs)
        cv2.destroyAllWindows()
        cv2.namedWindow('final', cv2.WINDOW_NORMAL)
        cv2.setWindowProperty('final', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow('final',panorama)
        cv2.waitKey(1)
    if waitkey_in == ord('c'): # Crop on/off
        if settings_stitcher["crop"] == False:
            stitcher.cropper = Cropper(True)
            settings_stitcher["crop"] = stitcher.DEFAULT_SETTINGS["crop"]
        else:
            stitcher.cropper = Cropper(False)
            settings_stitcher["crop"] = True
        # Restart window
        cv2.destroyAllWindows()
        cv2.namedWindow('final', cv2.WINDOW_NORMAL)
        cv2.setWindowProperty('final', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow('final',panorama)
        cv2.waitKey(1)
    if waitkey_in == ord('f'): # Finder ON/OFF
        if settings_stitcher["finder"] == "no":
            stitcher.seam_finder = SeamFinder(stitcher.DEFAULT_SETTINGS["finder"])
            settings_stitcher["finder"] = stitcher.DEFAULT_SETTINGS["finder"]
        else:
            stitcher.seam_finder = SeamFinder("no")
            settings_stitcher["finder"] = "no"
    if waitkey_in == ord('g'): # Finder Lock
        if settings_input["cam_en"] == True:
            if settings_input["finder_lock == False"]:
                settings_input["finder_lock"] = True
            else:
                settings_input["finder_lock"] = False
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



# - Add definition for setting imshow -> Also add the debug window if stithing fails
# - Add SW contrast/brightness handlers
# - Add calibration handler
# - Store/Reload registration
