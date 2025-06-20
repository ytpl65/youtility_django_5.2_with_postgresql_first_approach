from django.http import response as rp
import logging
debug_logger = logging.getLogger('debug_logger')

def display_msg(msg):
    import cv2
    import numpy as np
    black_img = np.zeros((512, 512, 1), dtype='uint8')
    # get boundary of this text
    font = cv2.FONT_HERSHEY_COMPLEX_SMALL
    textsize = cv2.getTextSize(msg, font, 1, 2)[0]

    # get coords based on boundary
    textX = (black_img.shape[1] - textsize[0]) // 2
    textY = (black_img.shape[0] + textsize[1]) // 2

    # add text centered on image
    cv2.putText(black_img, msg, (textX, textY), font, 1, (255, 255, 255), 2)
    return black_img


def try_camera(cv2):
    cap = None
    try:
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                break
    except AttributeError as e:
        # OpenCV not properly installed or configured
        from apps.core.error_handling import ErrorHandler
        ErrorHandler.handle_exception(
            e, 
            context={'function': 'capture_from_webcam', 'issue': 'OpenCV AttributeError'},
            level='warning'
        )
        return False
    except Exception as e:
        # Unexpected error during camera capture
        from apps.core.error_handling import ErrorHandler
        ErrorHandler.handle_exception(
            e, 
            context={'function': 'capture_from_webcam', 'issue': 'Camera access failed'},
            level='error'
        )
        return False
    else:
        return cap


def detect_QR(cv2, decode, np, time):
    code, status = None, None,

    cap = try_camera(cv2)
    timeOut, msg = time.time() + 15, "Something went wrong!"
    # initialize the cv2 QRCode detector
    if cap.isOpened():
        debug_logger.debug("cameara is opened for qr detection")
        while True:
            _, img, = cap.read()
            # cv2.putText(img, "Hello World!!!", (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255))
            detected = False

            # draw rectangle and putText on qr code
            for barcode in decode(img):
                code = barcode.data.decode('utf-8')
                pts = np.array([barcode.polygon], np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(img, [pts], True, [0, 255, 0], 3)
                pts2 = barcode.rect
                cv2.putText(img, code, (pts2[0], pts2[1]), cv2.FONT_HERSHEY_COMPLEX,
                            0.9, (255, 0, 0), 2)
                detected = True
                debug_logger.debug("QR is detected")

            cv2.imshow("Attendance", img)

            if time.time() > timeOut:
                debug_logger.debug("qr detection is timed out")
                title = "Unable to detect QR code."
                msg = """Please align
                your code properly for better detection, QR code
                detection is necessary for face recognition."""
                status = 404
                break
            elif detected:
                debug_logger.debug("qr is detected successfully")
                title = "QR code has been detected!"
                msg = """QR code detected and decoded properly be 
                ready for face-recognition process.\n Note: For better results stand still
                head your face to camera properly."""
                status = 200
            if cv2.waitKey(1) == ord("q") or detected:
                break
        cap.release()
        cv2.destroyAllWindows()
    else:
        debug_logger.debug("device not found unable to complete the process")
        title = "Device not found."
        msg = """Please check your webcam's power 
                on/off or try connecting it to different usb slot"""
        status = 404
    return rp.JsonResponse({"message": msg, 'title': title, 'decoded': code}, status=status)


def get_actual_img(code, detectFace):
    debug_logger.debug("get_actual_img started")
    from apps.peoples.models import People
    try:
        debug_logger.debug("searching for img with this code %s", (code))
        img = People.objects.get(peoplecode = code)
        img_array = detectFace(img.peopleimg.path, detector_backend='opencv')
    except People.DoesNotExist:
        return None
    else:
        return img_array
    finally:
        debug_logger.debug("get_actual_img is ended")


def recognize_face(cv2, np, time, code):
    from deepface import DeepFace
    debug_logger.debug("recognize face started")
    cap, obj = try_camera(cv2), {}
    timeOut = time.time() + 15
    detected = False
    msg, title, status = "Something went wrong!", "", None

    if hasattr(cap, 'isOpened') and cap.isOpened:
        debug_logger.debug("camera is opened")
        actual_face = get_actual_img(code, DeepFace.detectFace)
        debug_logger.debug("result of get_actual_img%s", (actual_face))
        if len(actual_face):
            debug_logger.debug("actual face found")
            while True:

                x, img, = cap.read()
                debug_logger.debug("camera is running %s", (x))
                cv2.imshow("Attendance", img)
                imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
                obj = DeepFace.verify(
                    actual_face, imgS, model_name='Facenet', enforce_detection=False)
                if hasattr(obj, 'verified') and obj['verified']:
                    detected = True
                if time.time() > timeOut:
                    title = "Unable to detect Face."
                    msg = """Please align
                    your face properly for better detection."""
                    status = 404
                    break
                elif detected:
                    debug_logger.debug("face is detected successfully")
                    title = "face code has been detected!"
                    msg = """face code detected and decoded properly be 
                    ready for face-recognition process.\n Note: For better results stand still
                    head your face to camera properly."""
                    status = 200
                if cv2.waitKey(1) == ord("q") or detected:
                    break

            cap.release()
            cv2.destroyAllWindows()
    else:
        title = "Device not found."
        msg = """Please check your webcam's power
                on/off or try connecting it to different usb slot"""
        status = 404
    debug_logger.debug("msg: %s, title: %s, decoded:%s", msg, title, code)
    return rp.JsonResponse({"message":msg, 'title':title, 'decoded':code}, status = status)

