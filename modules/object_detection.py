
#import time

#import tensorflow as tf

#import importlib.util

import os
import cv2
import numpy as np

class object_detection:

    def __init__(self,tflite_en=True,edge_tpu_en=True,model_dir=-1):

        # Assume that Linux is on RaspberryPi
        #if os.name == 'posix':

        # Set model type and directory
        self.TFLITE_EN  = tflite_en
        self.EDGE_TPU_EN = edge_tpu_en
        if model_dir == -1:
            self.MODEL_DIR  = '../../object_detection_models/18_08_2022_efficientdet-lite1_e75_b32_s2000/'
        else:
            self.MODEL_DIR = model_dir

        # Load correct model
        if self.TFLITE_EN:
            # Import TensorFlow libraries
            # If tflite_runtime is installed, import interpreter from tflite_runtime, else import from regular tensorflow
            # If using Coral Edge TPU, import the load_delegate library
            import importlib.util
            pkg = importlib.util.find_spec('tflite_runtime')
            if pkg:
                from tflite_runtime.interpreter import Interpreter
                if self.EDGE_TPU_EN:
                    from tflite_runtime.interpreter import load_delegate
            else:
                from tensorflow.lite.python.interpreter import Interpreter
                if self.EDGE_TPU_EN:
                    from tensorflow.lite.python.interpreter import load_delegate
            # Load Model
            #if TFLITE_PC:
            if os.name != 'posix':
                if self.EDGE_TPU_EN:
                    # Edge TPU TFLITE
                    print('No support for Edge TPU on PC...')
                    exit()
                else:
                    # float16 TFLITE
                    self.interpreter = Interpreter(model_path=os.path.join(self.MODEL_DIR,'model_float16.tflite'))
                    print('Loading TFLITE Float16...')
            else:
                if self.EDGE_TPU_EN:
                    # Edge TPU TFLITE
                    self.interpreter = Interpreter(model_path=os.path.join(self.MODEL_DIR,'edge_tpu_2','model_default_edgetpu.tflite'),
                                          experimental_delegates=[load_delegate('libedgetpu.so.1.0')])
                    print('Loading TFLITE for Edge TPU...')
                else:
                    # Default TFLITE
                    self.interpreter = Interpreter(model_path=os.path.join(self.MODEL_DIR,'model_default.tflite'))
                    print('Loading TFLITE Default...')
            # Allocate    
            self.interpreter.allocate_tensors()
            # Get model details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            height = self.input_details[0]['shape'][1]
            width = self.input_details[0]['shape'][2]
            print('H: '+str(height)+' W: '+str(width))
            self.tflite_model_height = height
            self.tflite_model_width  = width
            self.floating_model = (self.input_details[0]['dtype'] == np.float32)
            self.input_mean = 127.5
            self.input_std = 127.5
            # Check output layer name to determine if this model was created with TF2 or TF1,
            # because outputs are ordered differently for TF2 and TF1 models
            outname = self.output_details[0]['name']
            if ('StatefulPartitionedCall' in outname): # This is a TF2 model
                self.boxes_idx, self.classes_idx, self.scores_idx = 1, 3, 0
            else: # This is a TF1 model
                self.boxes_idx, self.classes_idx, self.scores_idx = 0, 1, 2
        else:
            # Print Tensorflow version
            print('Tensorflow version: '+tf.__version__)
            # Init Model
            self.detect_fn = tf.saved_model.load(self.MODEL_DIR+'saved_model/')    


    def run_detector(self,img):
        if self.TFLITE_EN:
        
            # Run detector
            frame_rgb = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB)
            frame_resized = cv2.resize(frame_rgb, (self.tflite_model_width, self.tflite_model_height))
            input_data = np.expand_dims(frame_resized, axis=0)

            # Normalize pixel values if using a floating model (i.e. if model is non-quantized)
            if self.floating_model:
                input_data = (np.float32(input_data) - self.input_mean) / self.input_std

            # Perform the actual detection by running the model with the image as input
            self.interpreter.set_tensor(self.input_details[0]['index'],input_data)
            self.interpreter.invoke()

            # Retrieve detection results
            boxes = self.interpreter.get_tensor(self.output_details[self.boxes_idx]['index'])[0] # Bounding box coordinates of detected objects
            classes = self.interpreter.get_tensor(self.output_details[self.classes_idx]['index'])[0] # Class index of detected objects
            scores = self.interpreter.get_tensor(self.output_details[self.scores_idx]['index'])[0] # Confidence of detected objects
        
            # Add one to classes to match MODEL
            for i in range(len(classes)):
                classes[i] = classes[i] + 1
        
            # Convert to NP
            boxes = np.array(boxes)
            classes = np.array(classes).astype(np.int64)
            scores = np.array(scores)

        else:

            # Run detector
            image_np = np.array(img.copy())
            input_tensor = tf.convert_to_tensor(image_np)
            input_tensor = input_tensor[tf.newaxis, ...]
            detections = detect_fn(input_tensor)
    
            # Normalize boxes
            boxes   = []
            for box in tf.get_static_value(detections[0][0]):
                boxes.append([box[0]/image_np.shape[0],
                              box[1]/image_np.shape[1],
                              box[2]/image_np.shape[0],
                              box[3]/image_np.shape[1]])  
            boxes = np.array(boxes)
            # Convert Classes to integers
            classes = tf.get_static_value(detections[2][0]).astype(np.int64)
            # Scores
            scores  = tf.get_static_value(detections[1][0])
        
        # Load in dict
        detections = {}
        detections['detection_boxes'] = boxes
        detections['detection_scores'] = scores
        detections['detection_classes'] = classes

        return detections
