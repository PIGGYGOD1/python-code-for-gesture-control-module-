# verify_install.py
import sys
import cv2
import mediapipe as mp
import numpy as np
import pynput

print("Python:", sys.version.splitlines()[0])
print("cv2:", cv2.__version__)
print("mediapipe:", mp.__version__)
print("numpy:", np.__version__)
print("pynput OK")

