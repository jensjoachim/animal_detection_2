
#import tensorflow as tf

import os
import cv2
import numpy as np

from PIL import Image
from PIL import ImageColor
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageOps

class object_detection:

    def __init__(self,tflite_en=True,edge_tpu_en=True,model_dir=-1):

        # Max detections to be processed per detector
        self.DET_MAX_PROC = 7
        
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

        # Load Labels
        self.category_index = {}
        labels_file = open(self.MODEL_DIR+'labels.txt', 'r')
        lines_labels_file = labels_file.readlines()
        i = 1
        for line in lines_labels_file:
            self.category_index[i] = {'id': i, 'name': line.split('\n')[0]}
            print("\'id\': "+str(i)+", \'name\': "+line.split('\n')[0])
            i = i + 1
        #print(self.category_index)
        # Define a list of colors for visualization
        np.random.seed(1931)
        COLORS = np.random.randint(25, 230, size=(i, 3), dtype=np.uint8)
        self.color_selection = []
        i = 1
        for color in COLORS:
            self.color_selection.append('#{0:02x}{1:02x}{1:02x}'.format(color[2],color[1],color[0]))
            print("\'id\': "+str(i)+", "+'#{0:02x}{1:02x}{1:02x}'.format(color[2],color[1],color[0]))    
            i = i + 1
        #print(self.color_selection)

        # Set general font
        try:
            if os.name == 'posix':
                # Linux
                #font = ImageFont.truetype("/usr/share/fonts/truetype/ttf-bitstream-vera/VeraBd.ttf",15)
                self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",15)
            else:
                # Windows
                self.font = ImageFont.truetype("C:/Windows/Fonts/Arial/ariblk.ttf",15)
        except IOError:
            print("Font not found, using default font.")
            self.font = ImageFont.load_default()


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


    def draw_boxes(self,image, index, boxes, class_names, scores, max_boxes=10, min_score=0.1):
        # Only check a limited number of boxes
        if self.DET_MAX_PROC == -1:
            loop_range = range(min(boxes.shape[0], max_boxes))
        else:
            loop_range = range(self.DET_MAX_PROC)

        """Overlay labeled boxes on an image with formatted scores and label names."""
        image_pil = Image.fromarray(np.uint8(image)).convert("RGB")
        for i in loop_range:
            if scores[i] >= min_score:
                ymin, xmin, ymax, xmax = tuple(boxes[i])
                display_str = "a{} {}: {}%".format(int(index),self.category_index[class_names[i]]['name'],int(100 * scores[i]))
                color = self.color_selection[class_names[i]]
                self.draw_bounding_box_on_image(
                    image_pil,
                    ymin,
                    xmin,
                    ymax,
                    xmax,
                    color,
                    self.font,
                    display_str_list=[display_str])
        np.copyto(image, np.array(image_pil))
        return image

    
    def draw_bounding_box_on_image(self,image,ymin,xmin,ymax,xmax,color,font,thickness=2,display_str_list=()):
    
        """Adds a bounding box to an image."""
        draw = ImageDraw.Draw(image)
        im_width, im_height = image.size
        (left, right, top, bottom) = (xmin * im_width, xmax * im_width,
                                    ymin * im_height, ymax * im_height)
        draw.line([(left, top), (left, bottom), (right, bottom), (right, top),
                 (left, top)],
                width=thickness,
                fill=color)
    
        # If the total height of the display strings added to the top of the bounding
        # box exceeds the top of the image, stack the strings below the bounding box
        # instead of above.
        #display_str_heights = [font.getsize(ds)[1] for ds in display_str_list]
        display_str_heights = [font.getbbox(ds)[3] for ds in display_str_list]
        
        # Each display_str has a top and bottom margin of 0.05x.
        total_display_str_height = (1 + 2 * 0.05) * sum(display_str_heights)
    
        if top > total_display_str_height:
            text_bottom = top
        else:
            text_bottom = top + total_display_str_height
        # Reverse list and print from bottom to top.
        for display_str in display_str_list[::-1]:
            #text_width, text_height = font.getsize(display_str)
            text_width, text_height = font.getbbox(display_str)[2:]
            margin = np.ceil(0.05 * text_height)
            draw.rectangle([(left, text_bottom - text_height - 2 * margin),
                        (left + text_width, text_bottom)],
                       fill=color)
            draw.text((left + margin, text_bottom - text_height - margin),
                  display_str,
                  fill="black",
                  font=font)
            text_bottom -= text_height - 2 * margin
    
