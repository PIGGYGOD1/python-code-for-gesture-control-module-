# gesture_media_control.py
"""
Gesture-based media controller.

Requirements: mediapipe, opencv-python, pynput, numpy (in your active .venv)

How it works:
- Uses MediaPipe to detect hand landmarks.
- Converts landmarks -> fingers up array -> gesture name.
- Smooths gestures over several frames and only triggers an action
  when a gesture is stable and cooldown has elapsed.
- Triggers media keys (preferred) or fallback keyboard shortcuts.

Press ESC to quit.
"""

import time
from collections import deque, Counter

import cv2
import mediapipe as mp
from pynput.keyboard import Controller, Key

# ---- Settings ----
CAM_INDEX = 0                      # webcam index
MAX_HANDS = 1
MIN_DET_CONF = 0.6
MIN_TRACK_CONF = 0.6

SMOOTHING_FRAMES = 6               # require the same gesture for N frames before firing
ACTION_COOLDOWN = 0.8              # seconds between actions (avoid repeats)

# Tip landmark indices
TIP_IDS = [4, 8, 12, 16, 20]

# ---- Helpers: Gesture detection logic (same as before) ----
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
keyboard = Controller()

def fingers_up(hand_landmarks, handedness_label):
    lm = hand_landmarks.landmark
    fingers = []
    # Thumb: x comparison; handedness determines direction
    if handedness_label == "Right":
        fingers.append(lm[TIP_IDS[0]].x < lm[TIP_IDS[0] - 1].x)
    else:
        fingers.append(lm[TIP_IDS[0]].x > lm[TIP_IDS[0] - 1].x)
    # Other fingers: tip y < pip y -> finger up
    fingers += [lm[id].y < lm[id - 2].y for id in TIP_IDS[1:]]
    # Convert booleans to ints so equality checks are straightforward
    return [1 if f else 0 for f in fingers]

def detect_gesture(fingers):
    thumb, index, middle, ring, pinky = fingers
    if fingers == [1, 1, 1, 1, 1]:
        return "OPEN_PALM"
    if fingers == [0, 0, 0, 0, 0]:
        return "FIST"
    if fingers == [1, 0, 0, 0, 0]:
        return "THUMB_UP"
    if fingers == [0, 1, 0, 0, 0]:
        return "POINT"
    # Add more patterns here if you want
    return "UNKNOWN"

# ---- Action mapping ----
def press_media_key_if_available(key_attr_name):
    """
    Try to press a media key (Key.media_play_pause etc). If the Key attribute
    is not available in this environment, return False so caller can fallback.
    """
    media_key = getattr(Key, key_attr_name, None)
    if media_key is None:
        return False
    try:
        keyboard.press(media_key)
        keyboard.release(media_key)
        return True
    except Exception:
        return False

def press_key_fallback(key_or_combo):
    """
    key_or_combo: either a single character string (e.g. 'n') or a tuple
    like (Key.ctrl, 'Right') for modifiers + key. This is a simple fallback.
    """
    try:
        if isinstance(key_or_combo, tuple):
            # press modifier, then key, then release
            for k in key_or_combo:
                keyboard.press(k)
            for k in reversed(key_or_combo):
                keyboard.release(k)
        else:
            keyboard.press(key_or_combo)
            keyboard.release(key_or_combo)
        return True
    except Exception:
        return False

def perform_action_for_gesture(gesture_name):
    """
    Map the gesture to an action. Returns a string describing the action performed (for HUD).
    """
    # OPEN_PALM -> Play/Pause
    if gesture_name == "OPEN_PALM":
        ok = press_media_key_if_available("media_play_pause")
        if not ok:
            # Fallback: space usually toggles play/pause in browser/media players
            press_key_fallback(" ")
        return "Play/Pause"

    # FIST -> Previous track
    if gesture_name == "FIST":
        ok = press_media_key_if_available("media_previous")
        if not ok:
            # Fallback: often 'p' or ctrl+left; using ctrl+left as a common media previous in some web apps
            press_key_fallback((Key.ctrl_l, Key.left))
        return "Previous Track"

    # POINT -> Next track
    if gesture_name == "POINT":
        ok = press_media_key_if_available("media_next")
        if not ok:
            # Fallback: 'n' or ctrl+right
            press_key_fallback((Key.ctrl_l, Key.right))
        return "Next Track"

    # THUMB_UP -> Volume Up
    if gesture_name == "THUMB_UP":
        ok = press_media_key_if_available("media_volume_up")
        if not ok:
            # Fallback: send '+' key (may or may not work depending on app)
            press_key_fallback("+")
        return "Volume Up"

    # You can add THUMB_DOWN or others here later.
    return None

# ---- Main loop with smoothing & cooldown ----
def main():
    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        print("ERROR: Could not open webcam. Try a different camera index.")
        return

    gesture_history = deque(maxlen=SMOOTHING_FRAMES)  # recent gestures
    last_action_time = 0
    last_triggered = None

    with mp_hands.Hands(static_image_mode=False,
                        max_num_hands=MAX_HANDS,
                        min_detection_confidence=MIN_DET_CONF,
                        min_tracking_confidence=MIN_TRACK_CONF) as hands:

        prev_time = 0.0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            gesture = "No hand"
            gesture_to_display = "No hand"
            action_text = ""

            if results.multi_hand_landmarks and results.multi_handedness:
                hand_landmarks = results.multi_hand_landmarks[0]
                handedness_label = results.multi_handedness[0].classification[0].label

                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                fingers = fingers_up(hand_landmarks, handedness_label)
                gesture = detect_gesture(fingers)
                gesture_to_display = f"{gesture} {fingers}"

                # smoothing: append current gesture and check if the most common gesture
                # in the window is stable and not UNKNOWN
                gesture_history.append(gesture)
                most_common, count = Counter(gesture_history).most_common(1)[0]
                stable = (most_common != "UNKNOWN") and (count == gesture_history.maxlen)

                now = time.time()
                if stable and (now - last_action_time) > ACTION_COOLDOWN:
                    # Only trigger if the stable gesture is different from last triggered
                    if most_common != last_triggered:
                        action_desc = perform_action_for_gesture(most_common)
                        if action_desc:
                            action_text = f"Action: {action_desc}"
                            last_action_time = now
                            last_triggered = most_common

            else:
                # No hand: push UNKNOWN into history so smoothing resets
                gesture_history.append("UNKNOWN")

            # FPS
            cur_time = time.time()
            fps = 1.0 / (cur_time - prev_time) if prev_time else 0.0
            prev_time = cur_time

            # HUD overlays
            cv2.putText(frame, f"Gesture: {gesture_to_display}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"{action_text}", (10, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
            cv2.putText(frame, f"FPS: {int(fps)}", (10, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

            cv2.imshow("Gesture Media Controller", frame)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
