
import cv2
import numpy as np
import pickle
from numpy.linalg import inv
import math
from statistics import median

def map_forward(xy, r_kinv, scale):
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

# Load camera data
#with open('registration', 'rb') as file:
with open('../image_stitch/test_stitcher/registration', 'rb') as file:
    attr_data_dict_list_in = pickle.load(file)
    # Make tuple of CameraParams
    new_cam_param_tuple = ()
    for i in range(len(attr_data_dict_list_in)):
        new_cam_param = cv2.detail.CameraParams()
        for keys, value in attr_data_dict_list_in[i].items():
            setattr(new_cam_param,keys,value)
        new_cam_param_tuple = new_cam_param_tuple + (new_cam_param,)
    # Overwrite tupe in stitcher
    cameras = new_cam_param_tuple
    print("registration loaded")
    print(attr_data_dict_list_in)

# Calc scale
scale = 466.9297206162631
focals = [cam.focal for cam in cameras]
scale = median(focals)
print("scale: "+str(scale))

i = 0
for camera in cameras:
    i = i + 1

    # Gather constants
    K = camera.K().astype(np.float32)
    R = camera.R
    H = np.matmul(K, R, inv(K))
    R_Kinv = np.matmul(R, inv(K))
    K_Rinv = np.matmul(K, inv(R))

    coord_in = (1152,648)
    print("Coordinate in: "+str(coord_in))

    warper = cv2.PyRotationWarper("spherical",scale)
    coord_out = warper.warpPoint(coord_in, K, R)
    print("Coordinate out: "+str(coord_out))
    
    coord_out = map_forward(coord_in, R_Kinv, scale)
    print("Coordinate out: "+str(coord_out))

    coord_back = map_backward(coord_out, scale, K_Rinv)
    print("Coordinate back: "+str(coord_back))
    
   
