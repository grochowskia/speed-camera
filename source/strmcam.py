def strmcam():
    """
    Factory function: create and return a running CamStream for the camera
    type selected in config.py (CAMERA variable).

    Supported values for CAMERA:
        pilibcam  – Raspberry Pi camera via picamera2 / libcamera
        usbcam    – USB webcam via OpenCV
        rtspcam   – RTSP / IP camera via OpenCV
    """

    import sys
    import os
    import time
    import logging

    PROG_VER = "14.0"
    CAM_WARMUP_SEC = 3
    CAMLIST = ("pilibcam", "usbcam", "rtspcam")

    # Import required settings from config.py
    try:
        from config import (
            PLUGIN_ENABLE_ON,
            PLUGIN_NAME,
            CAMERA,
            IM_SIZE,
            RTSPCAM_SRC,
            USBCAM_SRC,
            IM_HFLIP,
            IM_VFLIP,
            CAM_AWB_MODE,
            CAM_COLOUR_GAINS,
            CAM_SATURATION,
        )
    except Exception as err_msg:
        logging.error("Failed to import config.py settings: %s", err_msg)
        sys.exit(1)

    if PLUGIN_ENABLE_ON:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        plugin_dir = os.path.join(base_dir, "plugins")
        sys.path.insert(0, plugin_dir)
        try:
            from plugins.current import (
                CAMERA,
                IM_SIZE,
                RTSPCAM_SRC,
                USBCAM_SRC,
                IM_HFLIP,
                IM_VFLIP,
            )
            logging.info(
                "%s camera settings overridden by plugin %s",
                CAMERA.upper(),
                PLUGIN_NAME,
            )
        except Exception as err_msg:
            logging.warning("Plugin import warning: %s", err_msg)

    # ------------------------------------------------------------------
    def create_cam_stream(cam_name):
        cam_name = cam_name.lower()
        if cam_name not in CAMLIST:
            logging.error(
                "'%s' is not a valid CAMERA value.  "
                "Valid options: %s  (edit config.py)",
                cam_name,
                ", ".join(CAMLIST),
            )
            sys.exit(1)

        if cam_name == "pilibcam":
            # Suppress verbose picamera2 / libcamera log output
            logging.getLogger("picamera2").setLevel(logging.CRITICAL)
            logging.getLogger("libcamera").setLevel(logging.CRITICAL)
            try:
                from strmpilibcam import CamStream
            except ImportError as exc:
                logging.error("Could not import strmpilibcam: %s", exc)
                logging.error(
                    "Ensure picamera2 is installed: pip install picamera2"
                )
                sys.exit(1)
            vs = CamStream(size=IM_SIZE, vflip=IM_VFLIP, hflip=IM_HFLIP,
                           awb_mode=CAM_AWB_MODE,
                           colour_gains=CAM_COLOUR_GAINS,
                           saturation=CAM_SATURATION).start()
            logging.info("pilibcam stream started (picamera2/libcamera)")

        elif cam_name in ("usbcam", "rtspcam"):
            cam_src = RTSPCAM_SRC if cam_name == "rtspcam" else USBCAM_SRC
            try:
                from strmusbipcam import CamStream
            except ImportError as exc:
                logging.error("Could not import strmusbipcam: %s", exc)
                sys.exit(1)
            vs = CamStream(src=cam_src, size=IM_SIZE).start()
            logging.info("%s stream started (src=%s)", cam_name.upper(), cam_src)

        return vs

    vs = create_cam_stream(CAMERA)
    logging.info("ver %s  warming up camera for %i s …", PROG_VER, CAM_WARMUP_SEC)
    time.sleep(CAM_WARMUP_SEC)
    return vs
