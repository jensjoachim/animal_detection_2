

import numpy as np
from numpy.linalg import inv
import math

from picamera2 import Picamera2
from libcamera import Transform
from libcamera import controls

import os
import cv2
import time
import sys

# Get root directory of project to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0,parent_dir)

# Import local packages / modules
from modules import sampling_timers
from modules import video_stitcher

def map_forward(xy, r_kinv, scale):
    x, y = xy
    x_ = r_kinv[0][0] * x + r_kinv[0][1] * y + r_kinv[0][2]
    y_ = r_kinv[1][0] * x + r_kinv[1][1] * y + r_kinv[1][2]
    z_ = r_kinv[2][0] * x + r_kinv[2][1] * y + r_kinv[2][2]
    u = scale * math.atan2(x_, z_)
    v = scale * y_ / math.sqrt(x_ * x_ + z_ * z_)
    return (u,v)

def map_forward_old(xy, r_kinv, scale):
    x, y = xy
    x_ = r_kinv[0][0] * x + r_kinv[0][1] * y + r_kinv[0][2]
    y_ = r_kinv[1][0] * x + r_kinv[1][1] * y + r_kinv[1][2]
    z_ = r_kinv[2][0] * x + r_kinv[2][1] * y + r_kinv[2][2]
    u = scale * math.atan2(x_, z_)
    w = y_ / math.sqrt(x_ * x_ + y_ * y_ + z_ * z_)
    v = scale * (math.pi - math.acos(w if not math.isnan(w) else 0))
    return (u,v)

def map_backward(uv, scale, k_rinv):
    u, v = uv
    u /= scale
    v /= scale
    x_ = math.sin(u)
    y_ = v
    z_ = math.cos(u)
    x = k_rinv[0][0] * x_ + k_rinv[0][1] * y_ + k_rinv[0][2] * z_
    y = k_rinv[1][0] * x_ + k_rinv[1][1] * y_ + k_rinv[1][2] * z_
    z = k_rinv[2][0] * x_ + k_rinv[2][1] * y_ + k_rinv[2][2] * z_
    if z > 0:
        x /= z
        y /= z
    else:
        x = -1
        y = -1
    return (x,y)

def map_backward_old(uv, scale, k_rinv):
    u, v = uv
    u /= scale
    v /= scale
    sinv = math.sin(math.pi - v)
    x_ = sinv * math.sin(u)
    y_ = math.cos(math.pi - v)
    z_ = sinv * math.cos(u)
    x = k_rinv[0][0] * x_ + k_rinv[0][1] * y_ + k_rinv[0][2] * z_
    y = k_rinv[1][0] * x_ + k_rinv[1][1] * y_ + k_rinv[1][2] * z_
    z = k_rinv[2][0] * x_ + k_rinv[2][1] * y_ + k_rinv[2][2] * z_
    if z > 0:
        x /= z
        y /= z
    else:
        x = y = -1
    return (x,y)

def point_plot(img,xy,w=5,c=(0,0,255)):
    x,y = xy
    for i in range(w):
        for j in range(w):
            img[int(y+i),int(x+j)] = c

def point_round(xy):
    return (round(xy[0]),round(xy[1]))

def point_check_in_frame(xy,size):
    if xy[0] > 0 and xy[0] < size[0]:
        if xy[1] > 0 and xy[1] < size[1]:
            return True
    return False

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
        return video_stitcher.video_stitcher(**settings_stitcher)
    else:
        return Stitcher(**settings_stitcher)

settings_input = {}
# Set option to use rpi camera of set of pictures
settings_input["cam_en"]        = True
settings_input["cam_dim"]       = (1152,648)   # registration_1920x1080    6.5
settings_input["vid_stitch_en"] = True
    
# Init Camera
init_get_imgs(**settings_input)

# Init stitcher
settings_stitcher = {}
stitcher = init_stitcher(settings_input["vid_stitch_en"],**settings_stitcher)
stitcher.load_registration(False)

# Get first panoram, to calculate offset for point warping
imgs = get_imgs(**settings_input)
panorama = stitcher.stitch(imgs)
stitcher.warp_point_init()
pano_size = (panorama.shape[1],panorama.shape[0])
imgs_size = []
for img in imgs:
    imgs_size.append((img.shape[1],img.shape[0]))
print("pano_size: "+str(pano_size))
print("imgs_size: "+str(imgs_size))

#exit(0)

# Calc coordinates on each image and panorama
#coord_in = (300,550)
#coord_in = (550,300)
#coord_in = (600,320)
#coord_in = (-600,-320)
#coord_in = (0.5,0.5)
#coord_in = (1,1)
#coord_in = (0,0)
coord_in = (150,90)
scale = stitcher.warper.scale
print("scale: "+str(scale))
i = 0
for camera in stitcher.cameras:
    i = i + 1

    # Gather constants
    K = camera.K().astype(np.float32)
    R = camera.R
    R_Kinv = np.matmul(R, inv(K))
    K_Rinv = np.matmul(K, inv(R))

    print("Coordinate in: "+str(coord_in))

    #warper = cv2.PyRotationWarper("spherical",scale)
    #coord_out = warper.warpPoint(coord_in, K, R)
    #print("Coordinate out: "+str(coord_out))
    
    warper = cv2.PyRotationWarper("cylindrical",scale)
    coord_out = warper.warpPoint(coord_in, K, R)
    print("Coordinate out: "+str(coord_out))
    
    coord_out = map_forward(coord_in, R_Kinv, scale)
    print("Coordinate out: "+str(coord_out))

    coord_back = map_backward(coord_out, scale, K_Rinv)
    print("Coordinate back: "+str(coord_back))

#exit(0)

#https://github.com/opencv/opencv/blob/41f08988b4c9756bd528bb6cd0cca0ce104b4edb/modules/stitching/include/opencv2/stitching/detail/warpers_inl.hpp#L222

# On first loop start stitching and open image windows
init_stitch_success = True
restart_imshow_window = True
point_in = (500,300)
#point_in = (1000,300)

# Run loop
while True:
    # Make panorama
    imgs = []
    imgs = get_imgs(**settings_input)
    panorama = stitcher.stitch(imgs)
    #print("panorama, WxH: "+str(panorama.shape[1])+"x"+str(panorama.shape[0]))
    #print("imgs[0] , WxH: "+str(imgs[0].shape[1])+"x"+str(imgs[0].shape[0]))

    # Plot points
    for i in range(len(stitcher.cameras)):
        #print("point_in: "+str(point_in))
        point_plot(imgs[i],point_in)
        point_new = stitcher.warp_point_forward(point_in,i)
        #print("point_new: "+str(point_new))
        point_plot(panorama,point_new)
        point_back = stitcher.warp_point_backward(point_new,(i+1)%2)
        if point_check_in_frame(point_back,imgs_size[(i+1)%2]):
            #print("point_back: "+str(point_back))
            point_plot(imgs[(i+1)%2],point_back,5,(0,255,0))

    # Add edge on images on panorama
    i = 0
    while i < len(imgs):
        dot_size = 1
        if i == 0:
            x_edge = imgs_size[i][0]-dot_size
        else:
            x_edge = 0
        y = 0
        while y < imgs_size[i][1]-dot_size:
            xy = (x_edge,y)
            point_plot(imgs[i],xy,dot_size)
            xy_pano = stitcher.warp_point_forward(xy,i)
            point_plot(panorama,xy_pano,dot_size)
            xy_back = stitcher.warp_point_backward(xy_pano,(i+1)%2)
            if point_check_in_frame(xy_back,imgs_size[(i+1)%2]):
                #print("xy_back: "+str(xy_back))
                point_plot(imgs[(i+1)%2],xy_back,1,(0,255,0))
            y = y + 1
        i = i + 1

    #exit(0)
    
    # Show images
    if restart_imshow_window == True:
        for i in range(len(imgs)):
            cv2.namedWindow("img_"+str(i), cv2.WINDOW_NORMAL)
            cv2.setWindowProperty("img_"+str(i), cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    for i in range(len(imgs)):
        cv2.imshow("img_"+str(i),imgs[i])     
    # Show first panorama
    if restart_imshow_window == True:
        cv2.namedWindow('final', cv2.WINDOW_NORMAL)
        cv2.setWindowProperty('final', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow('final',panorama)
    # Print all dimmensions of images and panorama
    if restart_imshow_window == True:
        for i in range(len(imgs)):
            print("img_"+str(i)+", WxH: "+str(imgs[i].shape[1])+"x"+str(imgs[i].shape[0]))
        print("panorama, WxH: "+str(panorama.shape[1])+"x"+str(panorama.shape[0]))
    restart_imshow_window = False
    # Handle keybaord input
    waitkey_in = cv2.waitKey(1) & 0xFF
    if waitkey_in == ord('q'): # Exit
        sys.exit()
    if waitkey_in == ord('w'): # Up
        x,y = point_in
        point_in = (x,y-100)
    if waitkey_in == ord('s'): # Down
        x,y = point_in
        point_in = (x,y+100)
    if waitkey_in == ord('a'): # Left
        x,y = point_in
        point_in = (x-100,y)
    if waitkey_in == ord('d'): # Right
        x,y = point_in
        point_in = (x+100,y)
