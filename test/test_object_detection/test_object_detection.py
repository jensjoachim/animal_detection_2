# Import packages
import sys
import os
import cv2
import numpy as np

#from PIL import Image
#from PIL import ImageColor
#from PIL import ImageDraw
#from PIL import ImageFont
#from PIL import ImageOps

import tensorflow as tf

import importlib.util

# Load Model
global MODEL_AUTO_EN
MODEL_AUTO_EN = True
global MODEL_DIR
global TFLITE_EN
global TFLITE_PC
global interpreter
global detect_fn
global tflite_model_height
global tflite_model_width
global floating_model
global input_details
global output_details
global boxes_idx
global classes_idx
global scores_idx

def load_model():
    
    # Model Selection
    # Automatic model selection regarding if testing on PC or RaspberryPi+EdgeTPU
    global MODEL_AUTO_EN
    global MODEL_DIR
    global TFLITE_EN
    global TFLITE_PC
    if MODEL_AUTO_EN:
        # Assume that Linux is on RaspberryPi
        if os.name == 'posix':
            TFLITE_EN   = True
            TFLITE_PC   = False
            EDGE_TPU_EN = True
            #MODEL_DIR   = '../../18_08_2022_efficientdet-lite1_e75_b32_s2000/'
            #MODEL_DIR   = '../../../Downloads/18_08_2022_efficientdet-lite1_e75_b32_s2000/'
            MODEL_DIR   = '../../object_detection_models/18_08_2022_efficientdet-lite1_e75_b32_s2000/'
        else:
            TFLITE_EN   = True
            TFLITE_PC   = True
            EDGE_TPU_EN = False
            #MODEL_DIR   = '../../../../tflite_custom_models/good/18_08_2022_efficientdet-lite1_e75_b32_s2000/'
            MODEL_DIR   = '../../object_detection_models/18_08_2022_efficientdet-lite1_e75_b32_s2000/'
    else:
        TFLITE_EN   = True
        TFLITE_PC   = True
        EDGE_TPU_EN = False
        #MODEL_DIR   = '../../../../tflite_custom_models/good/18_08_2022_efficientdet-lite1_e75_b32_s2000/'
        MODEL_DIR   = '../../object_detection_models/18_08_2022_efficientdet-lite1_e75_b32_s2000/'

    #EDGE_TPU_EN = False
    TFLITE_EN   = False
        
    # TFLITE
    global interpreter
    global detect_fn
    global tflite_model_height
    global tflite_model_width
    global floating_model
    global input_details
    global output_details
    global boxes_idx
    global classes_idx
    global scores_idx
    if TFLITE_EN:
        # Import TensorFlow libraries
        # If tflite_runtime is installed, import interpreter from tflite_runtime, else import from regular tensorflow
        # If using Coral Edge TPU, import the load_delegate library
        pkg = importlib.util.find_spec('tflite_runtime')
        if pkg:
            from tflite_runtime.interpreter import Interpreter
            if EDGE_TPU_EN:
                from tflite_runtime.interpreter import load_delegate
        else:
            from tensorflow.lite.python.interpreter import Interpreter
            if EDGE_TPU_EN:
                from tensorflow.lite.python.interpreter import load_delegate
                # Load Model
        if TFLITE_PC: 
            if EDGE_TPU_EN:
                # Edge TPU TFLITE
                print('No support for Edge TPU on PC...')
                exit()
            else:
                # float16 TFLITE
                interpreter = Interpreter(model_path=os.path.join(MODEL_DIR,'model_float16.tflite'))
                print('Loading TFLITE Float16...')
        else:
            if EDGE_TPU_EN:
                # Edge TPU TFLITE
                interpreter = Interpreter(model_path=os.path.join(MODEL_DIR,'edge_tpu_2','model_default_edgetpu.tflite'),
                                          experimental_delegates=[load_delegate('libedgetpu.so.1.0')])
                print('Loading TFLITE for Edge TPU...')
            else:
                # Default TFLITE
                interpreter = Interpreter(model_path=os.path.join(MODEL_DIR,'model_default.tflite'))
                print('Loading TFLITE Default...')
                # Allocate    
        interpreter.allocate_tensors()
        # Get model details
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        height = input_details[0]['shape'][1]
        width = input_details[0]['shape'][2]
        print('H: '+str(height)+' W: '+str(width))
        tflite_model_height = height
        tflite_model_width  = width

        floating_model = (input_details[0]['dtype'] == np.float32)

        input_mean = 127.5
        input_std = 127.5

        # Check output layer name to determine if this model was created with TF2 or TF1,
        # because outputs are ordered differently for TF2 and TF1 models
        outname = output_details[0]['name']

        if ('StatefulPartitionedCall' in outname): # This is a TF2 model
            boxes_idx, classes_idx, scores_idx = 1, 3, 0
        else: # This is a TF1 model
            boxes_idx, classes_idx, scores_idx = 0, 1, 2
    else:
        # Print Tensorflow version
        print('Tensorflow version: '+tf.__version__)
        # Init Model
        detect_fn = tf.saved_model.load(MODEL_DIR+'saved_model/')

load_model()

# Load Labels
category_index = {}
labels_file = open(MODEL_DIR+'labels.txt', 'r')
lines_labels_file = labels_file.readlines()
i = 1
for line in lines_labels_file:
    category_index[i] = {'id': i, 'name': line.split('\n')[0]}
    print("\'id\': "+str(i)+", \'name\': "+line.split('\n')[0])
    i = i + 1
# Define a list of colors for visualization
np.random.seed(1931)
COLORS = np.random.randint(25, 230, size=(i, 3), dtype=np.uint8)
color_selection = []
i = 1
for color in COLORS:
    color_selection.append('#{0:02x}{1:02x}{1:02x}'.format(color[2],color[1],color[0]))
    print("\'id\': "+str(i)+", "+'#{0:02x}{1:02x}{1:02x}'.format(color[2],color[1],color[0]))    
    i = i + 1



# Functions - Detection

def run_detector(img):

    # Run detector

    if TFLITE_EN:
        
        # Run detector
        frame_rgb = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (tflite_model_width, tflite_model_height))
        input_data = np.expand_dims(frame_resized, axis=0)

        # Normalize pixel values if using a floating model (i.e. if model is non-quantized)
        if floating_model:
            input_data = (np.float32(input_data) - input_mean) / input_std

        # Perform the actual detection by running the model with the image as input
        interpreter.set_tensor(input_details[0]['index'],input_data)
        interpreter.invoke()

        # Retrieve detection results
        boxes = interpreter.get_tensor(output_details[boxes_idx]['index'])[0] # Bounding box coordinates of detected objects
        classes = interpreter.get_tensor(output_details[classes_idx]['index'])[0] # Class index of detected objects
        scores = interpreter.get_tensor(output_details[scores_idx]['index'])[0] # Confidence of detected objects
        
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




# Get root directory of project to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
sys.path.insert(0,parent_dir)

# Import local packages / modules
from modules import sampling_timers

from modules import rpi_cam3_control

#cam_ctrl = rpi_cam3_control.rpi_cam3_control(0,"test.jpg")
#cam_ctrl = rpi_cam3_control.rpi_cam3_control(1,0)
cam_ctrl = rpi_cam3_control.rpi_cam3_control(2,0)

# Tmp Loop
restart_imshow_window = True
running = True
# Setup timers
st = sampling_timers.sampling_timers()
st.add("all",       50)
st.add("read_image",50)
st.add("object_detect",50)
# Debug handlers
show_timers = True
cam_ctrl.img_add_en = False
img_add_path = "deer_trans_bg_0.png"
if cam_ctrl.img_add_en == True:
    cam_ctrl.init_img_add(img_add_path)
while running:
    
    # Read image
    st.start("all")
    st.start("read_image")
    img = cam_ctrl.read_cam()
    st.stop("read_image")
    # Object detection
    #

    st.start("object_detect")
    print(run_detector(img))
    #print(run_detector(img[0:500,0:700]))
    st.stop("object_detect")
    
    # Show image
    if restart_imshow_window == True:
        cv2.namedWindow('img', cv2.WINDOW_NORMAL)
        #cv2.setWindowProperty('img', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        restart_imshow_window = False
    cv2.imshow('img',img)
    # Show timers
    if show_timers == True:
        #st.print_all()
        st.print_pretty()
    # Handle user input
    waitkey_in = cv2.waitKey(1) & 0xFF
    if waitkey_in == ord('q'): # Exit
        sys.exit()
    elif waitkey_in == ord('w'): # Up
        if cam_ctrl.img_add_en == True:
            cam_ctrl.move_img_add("up")
        else:
            cam_ctrl.move_corner_direction("up")
    elif waitkey_in == ord('s'): # Down
        if cam_ctrl.img_add_en == True:
            cam_ctrl.move_img_add("down")
        else:
            cam_ctrl.move_corner_direction("down")
    elif waitkey_in == ord('a'): # Left
        if cam_ctrl.img_add_en == True:
            cam_ctrl.move_img_add("left")
        else:
            cam_ctrl.move_corner_direction("left")
    elif waitkey_in == ord('d'): # Right
        if cam_ctrl.img_add_en == True:
            cam_ctrl.move_img_add("right")
        else:
            cam_ctrl.move_corner_direction("right")
    elif waitkey_in == ord('z'): # In
        if cam_ctrl.img_add_en == True:
            cam_ctrl.zoom_img_add("in")
        else:
            cam_ctrl.zoom_cursor_in_out("in")
    elif waitkey_in == ord('x'): # Out
        if cam_ctrl.img_add_en == True:
            cam_ctrl.zoom_img_add("out")
        else:
            cam_ctrl.zoom_cursor_in_out("out")
    #elif waitkey_in == ord('1'): # DBG Info #1
    #    scaler_crop = cam_ctrl.get_scaler_crop()
    #    print("scaler_crop: "+str(scaler_crop))
    #elif waitkey_in == ord('2'): # DBG Info #2
    #    lens_position = cam_ctrl.get_lens_position()
    #    print("lens_position: "+str(lens_position))
    elif waitkey_in == ord('1'): # DBG Info #1
        scaler_crop = cam_ctrl.get_scaler_crop()
        print("scaler_crop: "+str(scaler_crop))
    elif waitkey_in == ord('2'): # DBG Info #2
        lens_position = cam_ctrl.get_lens_position()
        print("lens_position: "+str(lens_position))
    elif waitkey_in == ord('3'): # DBG Info #3
        if show_timers == True:
            show_timers = False
        else:
            show_timers = True
    elif waitkey_in == ord('4'): # DBG Info #4
        if cam_ctrl.img_add_init == True:
            if cam_ctrl.img_add_en == True:
                cam_ctrl.img_add_en = False
            else:
                cam_ctrl.img_add_en = True
    elif waitkey_in == ord('5'): # DBG Info #5
        if cam_ctrl.img_add_init == False:
            cam_ctrl.init_img_add(img_add_path)
        else:
            if cam_ctrl.img_transparent_feature == True:
                cam_ctrl.init_img_add(img_add_path,False)
            else:
                cam_ctrl.init_img_add(img_add_path,True)

    
 


