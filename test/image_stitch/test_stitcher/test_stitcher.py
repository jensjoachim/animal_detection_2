from stitching import Stitcher
from stitching.images import Images
from stitching.cropper import Cropper
from stitching.seam_finder import SeamFinder
from stitching.exposure_error_compensator import ExposureErrorCompensator
from stitching.blender import Blender

import time

import copy

from picamera2 import Picamera2
from libcamera import Transform
from libcamera import controls

import cv2

import sys
import os

import inspect



# Get root directory of project to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
sys.path.insert(0,parent_dir)

# Import local packages / modules
from modules import sampling_timers

cam_en        = True
#cam_en        = False
#cam_dim       = (800,600)
cam_dim       = (1920, 1080)
#cam_dim       = (4608,2592)
image_paths   = ['../o_0.png','../o_1.png','../o_2.png']
vid_stitch_en = True

# Set settings

#settings = {"confidence_threshold": 0.4, "compensator": "no", "blender_type": "no", "finder": "no"}
settings = {"confidence_threshold": 0.4}
#settings = {"confidence_threshold": 0.3, "compensator": "no", "blender_type": "no", "finder": "no"}
#settings = {"detector": "sift", "confidence_threshold": 0.2, "blender_type": "no", "finder": "no"} # Good
#settings = {"detector": "sift", "confidence_threshold": 0.1, "compensator": "no", "blender_type": "no", "finder": "no","warper_type": "cylindrical"} # Good
#settings = {"detector": "orb", "confidence_threshold": 0.7, "nfeatures": 500, "adjuster": "ray","warper_type": "cylindrical"} # Good
settings = {"detector": "orb", "crop": False, "confidence_threshold": 0.7, "nfeatures": 500, "adjuster": "ray","warper_type": "cylindrical", "compensator": "no", "blender_type": "no", "finder": "no"} # Good
settings = {"detector": "sift", "crop": False, "confidence_threshold": 0.7, "nfeatures": 1500, "adjuster": "ray","warper_type": "cylindrical", "blender_type": "no", "finder": "no"}

settings = {"detector": "sift", "crop": False, "confidence_threshold": 0.7, "nfeatures": 1500, "adjuster": "ray","warper_type": "cylindrical", "compensator": "no", "blender_type": "no", "finder": "no"}
#settings = {"detector": "orb", "crop": False, "confidence_threshold": 0.7, "nfeatures": 1500, "adjuster": "ray","warper_type": "cylindrical", "blender_type": "no", "finder": "no"}





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
def init_get_imgs(cam_en):
    if cam_en == True:
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

def get_imgs(cam_en,image_paths):
    imgs = []
    if cam_en == False:
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
def init_stitcher(vid_stitch_en,**settings):
    if vid_stitch_en == True:
        return VideoStitcher(**settings)
    else:
        return Stitcher(**settings)



def sw_contrast_brightness(opt,imgs_in):
    # Disabled
    if opt == 0:
        return imgs_in
    # Two contranst brightness functions
    imgs_out = []
    for img in imgs_in:
        if opt == 1:
            # Option 1
            #alpha = 2.0 # Contrast control
            #beta = 10 # Brightness control
            alpha = 3.0 # Contrast control
            beta = -100 # Brightness control
            imgs_out.append(cv2.convertScaleAbs(img, alpha=alpha, beta=beta))
        elif opt == 2:
            # Option 2
            #contrast = 2 # Contrast control ( 0 to 127)
            #brightness = 0 # Brightness control (0-100)
            contrast = 2 # Contrast control ( 0 to 127)
            brightness = 0 # Brightness control (0-100)
            imgs_out.append(cv2.addWeighted(img, contrast, img, 0, brightness))
        else:
            print("inspect.stack()[0][3]: Wrong option: "+str(opt))
            sys.exit(1)
    return imgs_out       

# Init Camera
init_get_imgs(cam_en)

# Init stitcher
stitcher = init_stitcher(vid_stitch_en,**settings)

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
#print(stitcher.settings)
#print("Print dict setting:")
#print(stitcher.settings["blender_type"])
#stitcher.settings["blender_type"] = "no"
#print(stitcher.settings["blender_type"])
#print(stitcher.settings["blender_type"])


sw_con_bright_en = 1
finder_lock = False



# First panorama will set registration
imgs = get_imgs(cam_en,image_paths)
imgs = sw_contrast_brightness(sw_con_bright_en,imgs)
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
    imgs = get_imgs(cam_en,image_paths)
    imgs = sw_contrast_brightness(sw_con_bright_en,imgs)
    st.start("stitch")
    panorama = stitcher.stitch(imgs,finder_lock)
    st.stop("stitch")
    # Show
    cv2.imshow('final',panorama)
    # Handle keybaord input
    waitkey_in = cv2.waitKey(1) & 0xFF
    if waitkey_in == ord('q'): # Exit
        sys.exit()
    if waitkey_in == ord('r'): # Recalc stitch registration
        stitcher = init_stitcher(vid_stitch_en,**settings)
        panorama = stitcher.stitch(imgs)
        cv2.destroyAllWindows()
        cv2.namedWindow('final', cv2.WINDOW_NORMAL)
        cv2.setWindowProperty('final', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow('final',panorama)
        cv2.waitKey(1)
    if waitkey_in == ord('c'): # Crop on/off
        if stitcher.cropper.do_crop == True:
            stitcher.cropper = Cropper(False)
        else:
            stitcher.cropper = Cropper(True)
        cv2.destroyAllWindows()
        cv2.namedWindow('final', cv2.WINDOW_NORMAL)
        cv2.setWindowProperty('final', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow('final',panorama)
        cv2.waitKey(1)
    if waitkey_in == ord('f'): # Finder ON
        stitcher.seam_finder = SeamFinder()
    if waitkey_in == ord('g'): # Finder OFF
        stitcher.seam_finder = SeamFinder("no")
    if waitkey_in == ord('h'): # Finder Lock
        if cam_en == True:
            if finder_lock == False:
                finder_lock = True
            else:
                finder_lock = False
    if waitkey_in == ord('t'): # Compesator ON
        stitcher.compensator = ExposureErrorCompensator()
    if waitkey_in == ord('y'): # Compensator OFF
        stitcher.compensator = ExposureErrorCompensator("no")
    if waitkey_in == ord('b'): # Blender ON
        stitcher.blender = Blender("multiband",1)
    if waitkey_in == ord('n'): # Blender OFF
        stitcher.blender = Blender("no")
    if waitkey_in == ord('m'): # Change constrast mode
        sw_con_bright_en = (sw_con_bright_en + 1) % 3
    # Print time
    label_list = ["fps_curr","fps_mean"]
    #st.print_pretty(False,label_list)



# - Add global configuration file
# - Add definition for setting imshow
# - Add SW contrast/brightness handlers
# - Disable/Enable SW contrast/brightness
# - Enable/disable crop -> Also update args!
# - Add calibration handler
# - Store/Reload registration
# - Find a way to enable compensator/blender/composition  -> Also update args!
# - Can finder region be locked?
