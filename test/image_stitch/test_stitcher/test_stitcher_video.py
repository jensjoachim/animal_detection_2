from stitching import Stitcher
from stitching import AffineStitcher
from stitching.images import Images

import time

from picamera2 import Picamera2
from libcamera import Transform
from libcamera import controls

import cv2

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

image_paths=['../o_0.png','../o_1.png','../o_2.png']
imgs = [] 
for i in range(len(image_paths)): 
    imgs.append(cv2.imread(image_paths[i])) 
    
#settings = {"detector": "sift", "confidence_threshold": 0.2}

settings = {"confidence_threshold": 0.4, "compensator": "no", "blender_type": "no", "finder": "no"}
#settings = {"confidence_threshold": 0.4}
videostitcher = VideoStitcher(**settings)
print(str(time.time()))
panorama = videostitcher.stitch(imgs)
print(str(time.time()))
panorama = videostitcher.stitch(imgs)
print(str(time.time()))

cv2.imshow('final result',panorama) 
cv2.waitKey(0)
