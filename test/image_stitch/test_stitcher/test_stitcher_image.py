from stitching import Stitcher
from stitching import AffineStitcher
from stitching.images import Images

import time

from picamera2 import Picamera2
from libcamera import Transform
from libcamera import controls

import cv2
    
#settings = {"detector": "sift", "confidence_threshold": 0.2}
settings = {"confidence_threshold": 0.4}
stitcher = Stitcher(**settings)

image_paths=['../o_0.png','../o_1.png','../o_2.png']
imgs = [] 
for i in range(len(image_paths)): 
    imgs.append(cv2.imread(image_paths[i])) 
panorama = stitcher.stitch(imgs)           

cv2.imshow('final result',panorama) 
cv2.waitKey(0)
