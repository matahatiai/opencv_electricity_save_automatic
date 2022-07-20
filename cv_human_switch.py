from cvzone.PoseModule import PoseDetector
from cvzone.FaceDetectionModule import FaceDetector
import cv2
import cvzone
import threading

# import the time module
import time
import signal
import sys
import numpy as np
import matplotlib.pyplot as plt
import serial

import configparser

config = configparser.ConfigParser()
config.read('config.ini')

ser_port = config['SERIAL']['port']
ser_baudrate = int(config['SERIAL']['baudrate'])
ser_timeout = .1
arduino = serial.Serial(port=ser_port, baudrate=ser_baudrate, timeout=ser_timeout)
time.sleep(1)

# General settings
T = 5  # lama waktu mundur untuk mematikan switch dalam satuan detik
TH = None
STOP = False # flag untuk mematika Threading

def signal_handler(sig, frame):
    global STOP
    STOP = True
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# define the countdown func.
def countdown():
    global T
    while T:
        if(STOP):
            break
        else :
            mins, secs = divmod(T, 60)
            timer = '{:02d}:{:02d}'.format(mins, secs)
            #print(timer, end="\r")
            time.sleep(1)
            T -= 1
    print(f"Matikan switch")

x = threading.Thread(target=countdown, args=())
x.start()

def sendSerial(data):
	global arduino

	try :
		arduino.write(bytes(data, 'utf-8'))
	except Exception as e :
		print(e)
		try :
			arduino = serial.Serial(port=ser_port, baudrate=ser_baudrate, timeout=ser_timeout)
		except Exception as e :
			pass
		time.sleep(1)

	#debug
	#time.sleep(0.05)
	#data = arduino.readline()
	#print(data) # feedback from serial

cap = cv2.VideoCapture(int(config['CAMERA']['deviceid']),cv2.CAP_DSHOW)

detectorPose = PoseDetector()
detectorFace = FaceDetector()
fpsReader = cvzone.FPS()

def remainTime():
    global T
    # re-init jika setatus waktu sebelumnya sudah 0
    if(T < 1):
        T = 5
        threading.Thread(target=countdown, args=()).start()
    else :
        T = 5 # set waktu kembali ke awal

while True:
    success, img = cap.read()

    # Deteksi ada wajah
    img, bboxs = detectorFace.findFaces(img)
    if bboxs:
        # bboxInfo - "id","bbox","score","center"
        center = bboxs[0]["center"]
        cv2.circle(img, center, 5, (255, 0, 255), cv2.FILLED)
        remainTime()
    else :
        cv2.putText(img, "Tidak terdeteksi wajah", (50, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
        #print(f"Tidak terdeteksi wajah")

    # Deteksi FPS
    fps, img = fpsReader.update(img,pos=(50,450),color=(0,255,0),scale=1.5,thickness=2)

    # Deteksi Pose
    img = detectorPose.findPose(img)
    lmList, bboxInfo = detectorPose.findPosition(img, bboxWithHands=False)
    if bboxInfo :
        remainTime()
        
        center = bboxInfo["center"]
        cv2.circle(img, center, 5, (255, 0, 255), cv2.FILLED)
    else :
        cv2.putText(img, "Tidak terdeteksi posture tubuh", (50, 380), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
        #print(f"Tidak terdeteksi posture tubuh")

    timeLabel = f"Saklar dimatikan dalam 00:0{T} detik"
    cv2.putText(img, timeLabel, (50,50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,0,0), 2)

    # posisi point X-Y label
    x1 = 50
    y1 = 60

    if(T > 0):
        cv2.rectangle(img, (x1, y1), (180, 100),(0, 255, 0), -1)
        cv2.putText(img, "LAMPU ON", (x1+5, y1+28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
        threading.Thread(target=sendSerial, args=("{ON}",)).start()
    else :
        cv2.rectangle(img, (x1, y1), (180, 100),(0, 0, 255), -1)
        cv2.putText(img, "LAMPU OFF", (x1+5, y1+28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)
        threading.Thread(target=sendSerial, args=("{OFF}",)).start()

    cv2.imshow("Saklar Deteksi Manusia", img)
    if cv2.waitKey(1) & 0xFF == ord('q') or STOP :
        break
cap.release()
cv2.destroyAllWindows()