from stitching import Stitcher
from stitching import AffineStitcher
from stitching.images import Images

import time

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

cam_en        = False
#cam_dim       = (800,600)
cam_dim       = (1920, 1080)
#cam_dim       = (4608,2592)
#cam_dim       = (1600, 800)
vid_stitch_en = True
image_paths   = ['../o_0.png','../o_1.png','../o_2.png']

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

imgs = []
if cam_en == False:
    for i in range(len(image_paths)): 
        imgs.append(cv2.imread(image_paths[i]))

if cam_en == True:
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
    time.sleep(1)
    time.sleep(1)
    picam1.capture_array()
    picam2.capture_array()
    time.sleep(1)
    imgs.append(picam1.capture_array())
    imgs.append(picam2.capture_array())

# Set settings

#settings = {"detector": "sift", "confidence_threshold": 0.2}
#settings = {"confidence_threshold": 0.4, "compensator": "no", "blender_type": "no", "finder": "no"}
settings = {"confidence_threshold": 0.4}
#settings = {"confidence_threshold": 0.3}
#settings = {"confidence_threshold": 0.3, "compensator": "no", "blender_type": "no", "finder": "no"}
#settings = {"detector": "sift", "confidence_threshold": 0.2, "blender_type": "no", "finder": "no"} # Good
#settings = {"detector": "sift", "confidence_threshold": 0.1, "compensator": "no", "blender_type": "no", "finder": "no","warper_type": "cylindrical"} # Good

#settings = {"detector": "orb", "crop": False, "confidence_threshold": 0.7, "blender_type": "no", "finder": "no", "nfeatures": 1000, "adjuster": "ray"}
#settings = {"detector": "orb", "crop": False, "confidence_threshold": 0.7, "blender_type": "no", "finder": "no", "nfeatures": 1000, "adjuster": "ray","warper_type": "cylindrical"}
#settings = {"detector": "orb", "crop": False, "confidence_threshold": 0.7, "blender_type": "no", "finder": "no", "nfeatures": 500, "adjuster": "ray","warper_type": "cylindrical"}
#settings = {"detector": "sift", "crop": False, "confidence_threshold": 0.7, "blender_type": "no", "finder": "no", "nfeatures": 1000, "adjuster": "ray","warper_type": "plane"}
#settings = {"detector": "orb", "crop": False, "confidence_threshold": 0.7, "finder": "no", "nfeatures": 500, "adjuster": "ray","warper_type": "cylindrical"}
#settings = {"detector": "orb", "crop": False, "confidence_threshold": 0.7, "nfeatures": 500, "adjuster": "ray","warper_type": "cylindrical","compensator": "no", "blender_type": "no", "finder": "no"}settings = {"detector": "orb", "crop": "False", "confidence_threshold": 0.7, "nfeatures": 500, "adjuster": "ray","warper_type": "cylindrical","compensator": "no", "blender_type": "no"}

#settings = {"detector": "orb", "crop": False, "confidence_threshold": 0.7, "nfeatures": 500, "adjuster": "ray","warper_type": "cylindrical", "compensator": "no", "blender_type": "no", "finder": "no"}
#settings = {"detector": "orb", "crop": False, "confidence_threshold": 0.7, "nfeatures": 500, "adjuster": "ray","warper_type": "cylindrical", "blender_type": "no"}
#settings = {"detector": "orb", "crop": False, "confidence_threshold": 0.7, "nfeatures": 500, "adjuster": "ray","warper_type": "cylindrical"}
#settings = {"detector": "orb", "confidence_threshold": 0.7, "nfeatures": 500, "adjuster": "ray","warper_type": "cylindrical"} # Good


settings = {"detector": "orb", "crop": False, "confidence_threshold": 0.7, "nfeatures": 2500, "adjuster": "ray","warper_type": "cylindrical", "compensator": "no", "blender_type": "no", "finder": "no"}

#--adjuster {ray,reproj,affine,no}




# Normal stitcher class or vidoe stitch
if vid_stitch_en == True:
    stitcher = VideoStitcher(**settings)
else:
    stitcher = Stitcher(**settings)

#settings = {"crop": False,"confidence_threshold": 0.5,"blender_type": "no", "finder": "no",}   
#stitcher = AffineStitcher(**settings)

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

# Set sampling timers
st = sampling_timers.sampling_timers()
st.add("Init",1)
    
print(str(time.time()))
st.start("Init")
panorama = stitcher.stitch(imgs)
st.stop("Init")
print(str(time.time()))
panorama = stitcher.stitch(imgs)
print(str(time.time()))

label_list = ["time_curr"]
st.print_pretty(True,label_list)

while cam_en == False:
    cv2.imshow('final result',panorama)
    waitkey_in = cv2.waitKey(10) & 0xFF
    restitch = False
    if waitkey_in == ord('q'):
        break
    if waitkey_in == ord('w'):
        stitcher.settings["blender_type"] = "no"
        print(stitcher.settings["blender_type"])
        restitch = True
    if waitkey_in == ord('s'):
        stitcher.settings["blender_type"] = "multiband"
        print(stitcher.settings["blender_type"])
        restitch = True
    if restitch == True:
        panorama = stitcher.stitch(imgs)
    time.sleep(1)

if cam_en == True:
    st.remove("Init")
    st.add("Run",4)

    cv2.namedWindow("final", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("final", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            
    while True:
        
        cv2.imshow('final',panorama)
        waitkey_in = cv2.waitKey(10) & 0xFF
        if waitkey_in == ord('q'):
            break
        if waitkey_in == ord('r'):
            stitcher = VideoStitcher(**settings)
            panorama = stitcher.stitch(imgs)
         
        imgs = []
        imgs.append(picam1.capture_array())
        imgs.append(picam2.capture_array())
        st.start("Run")
        panorama = stitcher.stitch(imgs)
        st.stop("Run")
        label_list = ["fps_curr","fps_mean"]
        st.print_pretty(False,label_list)

