from stitching import Stitcher
from stitching import AffineStitcher
from stitching.images import Images

import time

from picamera2 import Picamera2
from libcamera import Transform
from libcamera import controls

import cv2

cam_en        = True
cam_dim       = (1920,1080)
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
    picam1.start()
    picam2.start()
    time.sleep(1)
    imgs.append(picam1.capture_array())
    imgs.append(picam2.capture_array())

# Set settings

#settings = {"detector": "sift", "confidence_threshold": 0.2}
settings = {"confidence_threshold": 0.4, "compensator": "no", "blender_type": "no", "finder": "no"}
#settings = {"confidence_threshold": 0.4}

# Normal stitcher class or vidoe stitch
if vid_stitch_en == True:
    stitcher = VideoStitcher(**settings)
else:
    stitcher = Stitcher(**settings)
    
print(str(time.time()))
panorama = stitcher.stitch(imgs)
print(str(time.time()))
panorama = stitcher.stitch(imgs)
print(str(time.time()))

while cam_en == False:
    cv2.imshow('final result',panorama) 
    if (cv2.waitKey(10) & 0xFF) == ord('q'):
        break
    time.sleep(1)

while cam_en == True:
    cv2.imshow('final result',panorama) 
    if (cv2.waitKey(10) & 0xFF) == ord('q'):
        break
    imgs = []
    imgs.append(picam1.capture_array())
    imgs.append(picam2.capture_array())
    panorama = stitcher.stitch(imgs)
