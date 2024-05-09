from stitching import Stitcher
from stitching.images import Images
import pickle
import cv2

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
            with open('registration', 'wb') as file:
                pickle.dump(dict_pickle, file)
            # Done
            print("Camera registration stored!")

    def load_registration(self,print_en,load_settings_en=True):
        # Load camera data
        with open('registration', 'rb') as file:
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
