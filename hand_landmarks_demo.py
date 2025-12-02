# hand_landmarks_demo.py
import cv2
import mediapipe as mp
import time

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# Mediapipe tip landmark indices: thumb, index, middle, ring, pinky
TIP_IDS = [4, 8, 12, 16, 20]

def fingers_up(hand_landmarks, handedness):
    """
    Returns list of 5 booleans: [thumb, index, middle, ring, pinky].
    Logic:
      - For thumb: compare x coordinate of tip vs preceding landmark; direction depends on handedness.
      - For other fingers: tip y < pip y (image y grows downward), so tip being 'above' pip means extended.
    """
    lm = hand_landmarks.landmark
    fingers = []

    # Thumb: use x comparison depending on detected handedness
    if handedness == "Right":
        fingers.append(lm[TIP_IDS[0]].x < lm[TIP_IDS[0] - 1].x)
    else:
        fingers.append(lm[TIP_IDS[0]].x > lm[TIP_IDS[0] - 1].x)

    # Other fingers: compare tip y to pip y (tip id vs id-2)
    fingers += [lm[id].y < lm[id - 2].y for id in TIP_IDS[1:]]
    return fingers

def main(camera_index=0):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"ERROR: Could not open webcam on index {camera_index}. Try a different index or check camera permissions.")
        return

    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6,
    ) as hands:
        prev_time = 0.0

        while True:
            ret, frame = cap.read()
            if not ret:
                print("ERROR: Frame not received from camera.")
                break

            frame = cv2.flip(frame, 1)  # mirror image for natural interaction
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            overlay_text = "No hand detected"

            if results.multi_hand_landmarks and results.multi_handedness:
                hand_landmarks = results.multi_hand_landmarks[0]
                handedness_label = results.multi_handedness[0].classification[0].label  # 'Left' or 'Right'

                # Draw landmarks and connections on the frame
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # Compute which fingers are up
                up = fingers_up(hand_landmarks, handedness_label)
                overlay_text = f"{handedness_label} hand - fingers: {['1' if x else '0' for x in up]}"

            # Compute and display FPS
            cur_time = time.time()
            fps = 1.0 / (cur_time - prev_time) if prev_time else 0.0
            prev_time = cur_time

            # Overlay text (hand state + fps)
            cv2.putText(frame, overlay_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"FPS: {int(fps)}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            cv2.imshow("Hand Landmarks Demo", frame)
            # ESC key (27) to quit
            if cv2.waitKey(1) & 0xFF == 27:
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
