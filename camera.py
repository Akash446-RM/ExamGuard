import cv2
import numpy as np
import os
from datetime import datetime


UPLOAD_FOLDER = "static/uploads"


def capture_photo(image_data):

    # Create upload folder if it does not exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Convert image bytes into NumPy array
    image_array = np.frombuffer(
        image_data,
        np.uint8
    )

    # Convert image data into an OpenCV image
    frame = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    # Check whether OpenCV successfully decoded the image
    if frame is None:
        return None

    # Create unique filename
    filename = (
        f"candidate_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    )

    # Create complete file path
    photo_path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    # Save image using OpenCV
    cv2.imwrite(
        photo_path,
        frame
    )

    return photo_path