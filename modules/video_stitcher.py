from stitching import Stitcher
from stitching.images import Images
from stitching.warper import Warper
import pickle
import cv2
import os
import numpy as np
from numpy.linalg import inv
import math

class video_stitcher(Stitcher):
 
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
            for i in range(len(self.cameras)):
                attr_data_dict = {}
                for attr in attr_data_dict_index:
                    attr_data_dict[attr] = getattr(self.cameras[i], attr)
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
            with open(self.search_backward_for_directory("registrations")+"/registration", 'wb') as file:
                pickle.dump(dict_pickle, file)
            # Done
            print("Camera registration stored!")

    def load_registration(self,print_en,load_settings_en=True):
        # Load camera data
        with open(self.search_backward_for_directory("registrations")+"/registration", 'rb') as file:
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

    def search_backward_for_directory(self,target_directory,start_directory=None):
        if start_directory is None:
            start_directory = os.getcwd()  # Start from the current working directory
        current_directory = start_directory
        while True:
            if os.path.isdir(os.path.join(current_directory, target_directory)):
                return os.path.join(current_directory, target_directory)
            # Move up one level
            current_directory = os.path.dirname(current_directory)
            # If reached the root directory, break the loop
            if current_directory == os.path.dirname(current_directory):
                break
        return None

    def calc_point_for_zero_center(self,corners):
        print("corners:      "+str(corners))
        if self.cropper.do_crop:
            min_corner_x = min([corner[0] for corner in corners])
            min_corner_y = min([corner[1] for corner in corners])
            lir_aspect = self.images.get_ratio(
            Images.Resolution.LOW, Images.Resolution.FINAL
            )
            scaled_overlaps = [r.times(lir_aspect) for r in self.cropper.overlapping_rectangles]
            cropped_corners = [r.corner for r in scaled_overlaps]
            new_corners = []
            for i in range(len(corners)):
                new_corners.append((corners[i][0]+cropped_corners[i][0],corners[i][1]+cropped_corners[i][1]))
            min_corner_x = min([corner[0] for corner in new_corners])
            min_corner_y = min([corner[1] for corner in new_corners])
        else:
            min_corner_x = min([corner[0] for corner in corners])
            min_corner_y = min([corner[1] for corner in corners])
        print("min_corner_x: "+str(min_corner_x))
        print("min_corner_y: "+str(min_corner_y))
        return (min_corner_x,min_corner_y)

    def warp_point_init(self):
        sizes = self.images.get_scaled_img_sizes(Images.Resolution.FINAL)
        camera_aspect = self.images.get_ratio(Images.Resolution.MEDIUM, Images.Resolution.FINAL)
        corners = []
        n = 0
        for camera in self.cameras:
            warper = cv2.PyRotationWarper(self.warper.warper_type, self.warper.scale * camera_aspect)
            K = Warper.get_K(camera, camera_aspect)
            roi = warper.warpRoi(sizes[n], K, camera.R)
            print("roi: "+str(roi))
            corners.append((roi[0],roi[1]))
            n = n + 1
        min_corner = self.calc_point_for_zero_center(corners)
        self.wp_min_corner = min_corner            
        print("warp_point_new stop")
        
    def warp_point_forward(self,xy,n):
        camera_aspect = self.images.get_ratio(Images.Resolution.MEDIUM, Images.Resolution.FINAL)
        min_corner = self.wp_min_corner
        camera = self.cameras[n]
        K = Warper.get_K(camera, camera_aspect)  
        point = self.map_forward(xy, K, camera.R, self.warper.scale * camera_aspect)
        point_new = (point[0]-min_corner[0],point[1]-min_corner[1])
        return point_new

    def warp_point_backward(self,xy,n):
        camera_aspect = self.images.get_ratio(Images.Resolution.MEDIUM, Images.Resolution.FINAL)
        min_corner = self.wp_min_corner
        camera = self.cameras[n]
        K = Warper.get_K(camera, camera_aspect)
        point = (xy[0]+min_corner[0],xy[1]+min_corner[1])
        point_new = self.map_backward(point, K, camera.R, self.warper.scale * camera_aspect)
        return point_new
    
    def map_forward(self,xy,K,R,scale):
        r_kinv = np.matmul(R,inv(K))
        x, y = xy
        x_ = r_kinv[0][0] * x + r_kinv[0][1] * y + r_kinv[0][2]
        y_ = r_kinv[1][0] * x + r_kinv[1][1] * y + r_kinv[1][2]
        z_ = r_kinv[2][0] * x + r_kinv[2][1] * y + r_kinv[2][2]
        u = scale * math.atan2(x_, z_)
        v = scale * y_ / math.sqrt(x_ * x_ + z_ * z_)
        return (u,v)

    def map_backward(self,uv,K,R,scale):
        k_rinv = np.matmul(K,inv(R))
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
