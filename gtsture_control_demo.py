import cv2
import mediapipe as mp
import time

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

TIP_IDS = [4, 8, 12, 16, 20]  # thumb, index, middle, ring, pinky

def fingers_up(hand_landmarks, handedness):
    lm = hand_landmarks.landmark
    fingers = []

    # Thumb logic depends on left/right
    if handedness == "Right":
        fingers.append(lm[TIP_IDS[0]].x < lm[TIP_IDS[0]-1].x)
    else:
        fingers.append(lm[TIP_IDS[0]].x > lm[TIP_IDS[0]-1].x)

    # Other fingers
    fingers += [lm[id].y < lm[id-2].y for id in TIP_IDS[1:]]
    return fingers

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
    
    return "UNKNOWN"

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Could not open webcam.")
        return
    
    with mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.6) as hands:
        prev_time = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            gesture = "No hand"

            if results.multi_hand_landmarks and results.multi_handedness:
                hand_landmarks = results.multi_hand_landmarks[0]
                handedness = results.multi_handedness[0].classification[0].label

                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                up = fingers_up(hand_landmarks, handedness)
                gesture = detect_gesture(up)

                cv2.putText(frame, f"Fingers: {up}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

            cv2.putText(frame, f"Gesture: {gesture}", (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

            cv2.imshow("Gesture Detection Demo", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
