######## Picamera Object Detection Using Tensorflow Classifier #########
#
# Author: Evan Juras
# Date: 4/15/18
# Description: 
# This program uses a TensorFlow classifier to perform object detection.
# It loads the classifier uses it to perform object detection on a Picamera feed.
# It draws boxes and scores around the objects of interest in each frame from
# the Picamera. It also can be used with a webcam by adding "--usbcam"
# when executing this script from the terminal.

## Some of the code is copied from Google's example at
## https://github.com/tensorflow/models/blob/master/research/object_detection/object_detection_tutorial.ipynb

## and some is copied from Dat Tran's example at
## https://github.com/datitran/object_detector_app/blob/master/object_detection_app.py

## but I changed it to make it more understandable to me.


# Import packages
import os
import cv2
import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera
import tensorflow as tf
import argparse
import sys
import pwm_motor as motor
import time
from gtts import gTTS
import speech_recognition as sr

# Set up camera constants
#IM_WIDTH = 1280
#IM_HEIGHT = 720
IM_WIDTH = 640
# Use smaller resolution for
IM_HEIGHT = 480
# slightly faster framerate

# Select camera type (if user enters --usbcam when calling this script,
# a USB webcam will be used)
camera_type = 'usb'
parser = argparse.ArgumentParser()
parser.add_argument('--usbcam', help='Use a USB webcam instead of picamera',
                    action='store_true')
parser.add_argument('--picam', help='Use a picamera',
                    action='store_true')
args = parser.parse_args()
if args.usbcam:
    camera_type = 'usb'
if args.picam:
    camera_type = 'picamera'

# This is needed since the working directory is the object_detection folder.
sys.path.append('..')

# Import utilites
from utils import label_map_util
from utils import visualization_utils as vis_util

# Name of the directory containing the object detection module we're using
MODEL_NAME = 'ssdlite_mobilenet_v2_coco_2018_05_09'

# Grab path to current working directory
CWD_PATH = os.getcwd()

# Path to frozen detection graph .pb file, which contains the model that is used
# for object detection.
PATH_TO_CKPT = os.path.join(CWD_PATH,MODEL_NAME,'frozen_inference_graph.pb')

# Path to label map file
PATH_TO_LABELS = os.path.join(CWD_PATH,'data','mscoco_label_map.pbtxt')

# Number of classes the object detector can identify
NUM_CLASSES = 90

## Load the label map.
# Label maps map indices to category names, so that when the convolution
# network predicts `5`, we know that this corresponds to `airplane`.
# Here we use internal utility functions, but anything that returns a
# dictionary mapping integers to appropriate string labels would be fine
label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
category_index = label_map_util.create_category_index(categories)

# Load the Tensorflow model into memory.
detection_graph = tf.Graph()
with detection_graph.as_default():
    od_graph_def = tf.GraphDef()
    with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
        serialized_graph = fid.read()
        od_graph_def.ParseFromString(serialized_graph)
        tf.import_graph_def(od_graph_def, name='')

    sess = tf.Session(graph=detection_graph)


# Define input and output tensors (i.e. data) for the object detection classifier

# Input tensor is the image
image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')

# Output tensors are the detection boxes, scores, and classes
# Each box represents a part of the image where a particular object was detected
detection_boxes = detection_graph.get_tensor_by_name('detection_boxes:0')

# Each score represents level of confidence for each of the objects.
# The score is shown on the result image, together with the class label.
detection_scores = detection_graph.get_tensor_by_name('detection_scores:0')
detection_classes = detection_graph.get_tensor_by_name('detection_classes:0')

# Number of objects detected
num_detections = detection_graph.get_tensor_by_name('num_detections:0')

# Initialize frame rate calculation
frame_rate_calc = 1
freq = cv2.getTickFrequency()
font = cv2.FONT_HERSHEY_SIMPLEX

# Initialize camera and perform object detection.
# The camera has to be set up and used differently depending on if it's a
# Picamera or USB webcam.

# I know this is ugly, but I basically copy+pasted the code for the object
# detection loop twice, and made one work for Picamera and the other work
# for USB.

### Picamera ###
if camera_type == 'picamera':

    # Initialize Picamera and grab reference to the raw capture
    camera = PiCamera()
    # camera.vflip = True
    # camera.hflip = True
    camera.resolution = (IM_WIDTH,IM_HEIGHT)
    camera.framerate = 10
    rawCapture = PiRGBArray(camera, size=(IM_WIDTH,IM_HEIGHT))
    rawCapture.truncate(0)

    for frame1 in camera.capture_continuous(rawCapture, format="bgr",use_video_port=True):

        t1 = cv2.getTickCount()

        # Acquire frame and expand frame dimensions to have shape: [1, None, None, 3]
        # i.e. a single-column array, where each item in the column has the pixel RGB value
        frame = np.copy(frame1.array)
        frame.setflags(write=1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_expanded = np.expand_dims(frame_rgb, axis=0)

        # Perform the actual detection by running the model with the image as input
        (boxes, scores, classes, num) = sess.run(
            [detection_boxes, detection_scores, detection_classes, num_detections],
            feed_dict={image_tensor: frame_expanded})

        # Draw the results of the detection (aka 'visulaize the results')
        vis_util.visualize_boxes_and_labels_on_image_array(
            frame,
            np.squeeze(boxes),
            np.squeeze(classes).astype(np.int32),
            np.squeeze(scores),
            category_index,
            use_normalized_coordinates=True,
            line_thickness=3,
            min_score_thresh=0.01)

        cv2.putText(frame,"FPS: {0:.2f}".format(frame_rate_calc),(30,50),font,1,(255,255,0),2,cv2.LINE_AA)

        # All the results have been drawn on the frame, so it's time to display it.
        cv2.imshow('Object detector', frame)

        t2 = cv2.getTickCount()
        time1 = (t2-t1)/freq
        frame_rate_calc = 1/time1

        # Press 'q' to quit
        if cv2.waitKey(1) == ord('q'):
            break

        rawCapture.truncate(0)

### USB webcam ###
elif camera_type == 'usb':
    #等待
    
    tts = gTTS(text='準備啟動', lang='zh-TW')
    tts.save('ready_tw.mp3')
    os.system('omxplayer -o local -p ready_tw.mp3 > /dev/null 2>&1')
    time.sleep(2)
    direct = 0
    
    while True:
        #obtain audio from the microphone
        r=sr.Recognizer()

        with sr.Microphone() as source:
            print("Ready...")
            audio=r.listen(source)
            
        # recognize speech using Google Speech Recognition
        try:
            ans = r.recognize_google(audio, language='zh-TW')
            print(ans)
            if ans == "啟動":
                break
        except sr.UnknownValueError:
            print("x")
        except sr.RequestError as e:
            print("No response from Google Speech Recognition service: {0}".format(e))

    # Initialize USB webcam feed
    camera = cv2.VideoCapture(0, cv2.CAP_V4L)
    ret = camera.set(3,IM_WIDTH)
    ret = camera.set(4,IM_HEIGHT)
    
    cap = cv2.VideoCapture(1)

    # 設定擷取影像的尺寸大小
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # 使用 XVID 編碼
    fourcc = cv2.VideoWriter_fourcc(*'XVID')

    # 建立 VideoWriter 物件，輸出影片至 output.avi
    # FPS 值為 20.0，解析度為 640x360
    out = cv2.VideoWriter('output.wmv', fourcc, 5.0, (640, 480))
    
    #設定語音
    tts = gTTS(text='小心行人', lang='zh-TW')
    tts.save('people_tw.mp3')
    tts = gTTS(text='啟動車輛', lang='zh-TW')
    tts.save('start_tw.mp3')
    os.system('omxplayer -o local -p start_tw.mp3 > /dev/null 2>&1')
    print(">>")
    warn_gap = 0
    direct_gap = 0

    while(True):

        # t1 = cv2.getTickCount()

        # Acquire frame and expand frame dimensions to have shape: [1, None, None, 3]
        # i.e. a single-column array, where each item in the column has the pixel RGB value
        ret, frame = camera.read()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_expanded = np.expand_dims(frame_rgb, axis=0)

        # Perform the actual detection by running the model with the image as input
        (boxes, scores, classes, num) = sess.run(
            [detection_boxes, detection_scores, detection_classes, num_detections],
            feed_dict={image_tensor: frame_expanded})

        # Draw the results of the detection (aka 'visulaize the results')
        vis_util.visualize_boxes_and_labels_on_image_array(
            frame,
            np.squeeze(boxes),
            np.squeeze(classes).astype(np.int32),
            np.squeeze(scores),
            category_index,
            use_normalized_coordinates=True,
            line_thickness=3,
            min_score_thresh=0.01)
        # print(boxes[0][:10])
        # print(np.squeeze(classes))
        # print(np.squeeze(scores))
        # print(category_index)
        cs = np.squeeze(classes).astype(np.int32)
        sc = np.squeeze(scores)
        safe = 1
        for i in range(int(num[0])):
            if cs[i] == 1 and sc[i] > 0.4:
                cx = (boxes[0][i][1] + boxes[0][i][3]) / 2
                cy = (boxes[0][i][0] + boxes[0][i][2]) / 2
                frame = cv2.circle(frame, (int(cx*IM_WIDTH),int(cy*IM_HEIGHT)), radius=5, color=(0,0,255), thickness=-1)
                if boxes[0][i][3] - boxes[0][i][1] > 0.6:
                    motor.backward()
                elif cx <= 0.5:
                    motor.turnRight()
                    direct += 1
                elif cx > 0.5:
                    motor.turnLeft()
                    direct -= 1
                safe = 0
                direct_gap = 10
                cv2.putText(frame, "<<Be careful!!>>", (330, 50), font, 1, (0, 0, 255), 2, cv2.LINE_AA)
                break
        #print(direct)
        
        if safe:
            if direct_gap == 0 and direct != 0:
                if direct > 0:
                    motor.turnLeft()
                    direct -= 1
                elif direct < 0:
                    motor.turnRight()
                    direct += 1
            else:
                motor.forward()
        elif warn_gap == 0:
            os.system('omxplayer -o local -p people_tw.mp3 > /dev/null 2>&1')
            warn_gap = 10
        
        if direct_gap > 0:
            direct_gap -= 1
        
        if warn_gap > 0:
            warn_gap -= 1
        
        if ret == True:
            # 寫入影格
            out.write(frame)
        
        # All the results have been drawn on the frame, so it's time to display it.
        cv2.imshow('Object detector', frame)
        # t2 = cv2.getTickCount()
        # time1 = (t2-t1)/freq
        # frame_rate_calc = 1/time1

        # Press 'q' to quit
        if cv2.waitKey(1) == ord('q'):
            break
# 釋放所有資源
cap.release()
out.release()
motor.cleanup()
camera.release()
cv2.destroyAllWindows()

