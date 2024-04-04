from stitching import Stitcher
from stitching import AffineStitcher
from stitching.images import Images

import time

import copy

from picamera2 import Picamera2
from libcamera import Transform
from libcamera import controls

import cv2

import sys
import os

# Get root directory of project to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
sys.path.insert(0,parent_dir)

# Import local packages / modules
from modules import sampling_timers

#cam_en        = True
cam_en        = False
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

settings = {"detector": "sift", "crop": False, "confidence_threshold": 0.7, "nfeatures": 1500, "adjuster": "ray","warper_type": "cylindrical", "blender_type": "no", "finder": "no"}

settings_tmp = copy.deepcopy(settings)


class VideoStitcher(Stitcher):

    def initialize_stitcher(self, **kwargs):
        super().initialize_stitcher(**kwargs)
        self.cameras = None
        self.cameras_registered = False

    def stitch(self, images, feature_masks=[]):
        self.images = Images.of(
            images, self.medium_megapix, self.low_megapix, self.final_megapix
        )

        imgs = self.resize_medium_resolution()
        
        if not self.cameras_registered:
            features = self.find_features(imgs, feature_masks)
            matches = self.match_features(features)
            imgs, features, matches = self.subset(imgs, features, matches)
            cameras = self.estimate_camera_parameters(features, matches)
            cameras = self.refine_camera_parameters(features, matches, cameras)
            cameras = self.perform_wave_correction(cameras)
            self.estimate_scale(cameras)
            self.cameras = cameras
            self.cameras_registered = True

        imgs = self.resize_low_resolution()
        imgs, masks, corners, sizes = self.warp_low_resolution(imgs, self.cameras)
        self.prepare_cropper(imgs, masks, corners, sizes)
        imgs, masks, corners, sizes = self.crop_low_resolution(
            imgs, masks, corners, sizes
        )
        self.estimate_exposure_errors(corners, imgs, masks)
        seam_masks = self.find_seam_masks(imgs, corners, masks)

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
        picam1.set_controls({"AfMode": controls.AfModeEnum.Continuous, "AfSpeed": controls.AfSpeedEnum.Fast})
        picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous, "AfSpeed": controls.AfSpeedEnum.Fast})
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

# Init Camera
init_get_imgs(cam_en)

# Init stitcher
stitcher = init_stitcher(vid_stitch_en,**settings)

# Set sampling timers
st = sampling_timers.sampling_timers()
st.add("Run",4)

# Debug
#print("Print dir:")
#print(dir(stitcher))
#print("Print dict:")
print(stitcher.__dict__)
print("Print dict setting:")
print(stitcher.settings)
print("Print dict setting:")
#print(stitcher.settings["blender_type"])
#stitcher.settings["blender_type"] = "no"
#print(stitcher.settings["blender_type"])
print(stitcher.settings["blender_type"])

# First panorama will set registration
imgs = get_imgs(cam_en,image_paths)
panorama = stitcher.stitch(imgs)

# Show first image
cv2.imshow('final',panorama)
cv2.namedWindow('final', cv2.WINDOW_NORMAL)
cv2.setWindowProperty('final', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.waitKey(1)

# Run loop
while True:
    # Stitch images
    imgs = []
    imgs = get_imgs(cam_en,image_paths)
    st.start("Run")
    panorama = stitcher.stitch(imgs)
    st.stop("Run")
    # Show
    cv2.imshow('final',panorama)
    waitkey_in = cv2.waitKey(1) & 0xFF
    if waitkey_in == ord('q'):
        break
    if waitkey_in == ord('r'):
        #del stitcher
        stitcher = init_stitcher(vid_stitch_en,**settings)
        print(stitcher.__dict__)
        print("Print dict setting:")
        print(stitcher.settings)
        #imgs = []
        #imgs = get_imgs(cam_en,image_paths)
        panorama = stitcher.stitch(imgs)
        cv2.destroyAllWindows()
        cv2.imshow('final',panorama)
        cv2.namedWindow('final', cv2.WINDOW_NORMAL)
        cv2.setWindowProperty('final', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.waitKey(1)
    # Print time
    label_list = ["fps_curr","fps_mean"]
    st.print_pretty(False,label_list)
    #time.sleep(1)


#while cam_en == False:
#    cv2.imshow('final result',panorama)
#    waitkey_in = cv2.waitKey(10) & 0xFF
#    if waitkey_in == ord('q'):
#        break
#    time.sleep(1)
#
#if cam_en == True:
#    st.add("Run",4)
#
#
#            
#    while True:
#        
#        cv2.imshow('final',panorama)
#        waitkey_in = cv2.waitKey(10) & 0xFF
#        if waitkey_in == ord('q'):
#            break
#        if waitkey_in == ord('r'):
#            stitcher = init_stitcher(vid_stitch_en)
#            panorama = stitcher.stitch(imgs)
#         
#        imgs = []
#        imgs.append(picam1.capture_array())
#        imgs.append(picam2.capture_array())
#
#        # Option 1
#        alpha = 2.0 # Contrast control
#        beta = 10 # Brightness control
#        #alpha = 3.0 # Contrast control
#        #beta = -100 # Brightness control
#        imgs[0] = cv2.convertScaleAbs(imgs[0], alpha=alpha, beta=beta)
#        imgs[1] = cv2.convertScaleAbs(imgs[1], alpha=alpha, beta=beta)
#        
#        # Option 2
#        #contrast = 2 # Contrast control ( 0 to 127)
#        #brightness = 0 # Brightness control (0-100)
#        #imgs[0] = cv2.addWeighted(imgs[0], contrast, imgs[0], 0, brightness)
#        #imgs[1] = cv2.addWeighted(imgs[1], contrast, imgs[1], 0, brightness)
#        
#        st.start("Run")
#        panorama = stitcher.stitch(imgs)
#        st.stop("Run")
#        label_list = ["fps_curr","fps_mean"]
#        st.print_pretty(False,label_list)


# - Add SW contrast/brightness handlers
# - Disable/Enable SW contrast/brightness
# - Enable/disable crop
# - Add calibration handler
# - Store/Reload registration
# - Find a way to enable compensator/blender/composition
