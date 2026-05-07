import time
import sys
import logging
from threading import Thread, Condition
import cv2


class CamStream:
    """
    Picamera2/libcamera threaded video stream for Raspberry Pi.

    Captures frames continuously in a background thread so read() is
    non-blocking.  Frames are returned as BGR numpy arrays compatible
    with OpenCV.

    Usage::

        from strmpilibcam import CamStream
        vs = CamStream(size=(640, 480), vflip=True, hflip=False).start()
        while True:
            frame = vs.read()   # BGR ndarray ready for cv2
            if frame is None:
                continue
    """

    def __init__(self, size=(320, 240), vflip=False, hflip=False,
                 awb_mode=None, colour_gains=None, saturation=1.0):
        from picamera2 import Picamera2
        from libcamera import Transform

        self.frame = None
        self.stopped = False
        self._thread = None
        self._condition = Condition()

        for attempt in range(1, 4):
            try:
                self.picam2 = Picamera2()
                cfg = self.picam2.create_video_configuration(
                    main={"format": "BGR888", "size": size},
                    transform=Transform(vflip=vflip, hflip=hflip),
                )
                self.picam2.configure(cfg)
                break
            except RuntimeError as exc:
                logging.warning("Pi camera init attempt %d/3 failed: %s", attempt, exc)
                try:
                    self.picam2.close()
                except Exception:
                    pass
                if attempt == 3:
                    logging.error(
                        "Pi camera failed to initialise after 3 attempts.\n"
                        "Check that no other process holds the camera "
                        "(run: pgrep -a python3) and try again."
                    )
                    sys.exit(1)
                time.sleep(2)

        self.picam2.start()
        time.sleep(2)  # allow sensor to stabilise

        # Disable autofocus if the lens supports manual control
        try:
            self.picam2.set_controls({"AfMode": 0, "LensPosition": 1})
        except RuntimeError:
            pass

        # White balance and colour controls.
        # awb_mode:      0=Auto 1=Tungsten 2=Fluorescent 3=Indoor 4=Daylight 5=Cloudy
        # colour_gains:  (red_gain, blue_gain) — only used when awb_mode is None
        #                increase red_gain or decrease blue_gain to warm up the image
        # saturation:    1.0=normal, >1.0 more vivid, 0.0=greyscale
        controls = {"Saturation": saturation}
        if awb_mode is not None:
            controls["AwbEnable"] = True
            controls["AwbMode"] = awb_mode
        elif colour_gains is not None:
            red_gain, blue_gain = colour_gains
            controls["AwbEnable"] = False
            controls["ColourGains"] = (red_gain, blue_gain)
        try:
            self.picam2.set_controls(controls)
        except RuntimeError as exc:
            logging.warning("Could not set colour controls: %s", exc)

    # ------------------------------------------------------------------
    def start(self):
        """Start background capture thread and return self."""
        self._thread = Thread(target=self._update, daemon=True)
        self._thread.start()
        return self

    def _update(self):
        """Continuously capture frames until stop() is called."""
        while not self.stopped:
            frame = self.picam2.capture_array("main")
            # picamera2 BGR888 is already in BGR order — use directly with OpenCV
            bgr = frame
            with self._condition:
                self.frame = bgr
                self._condition.notify_all()

    def read(self):
        """Block until a new frame arrives from the camera, then return it."""
        with self._condition:
            self._condition.wait(timeout=1.0)
            return self.frame

    def stop(self):
        """Stop background thread then release the camera."""
        self.stopped = True
        with self._condition:
            self._condition.notify_all()  # unblock any waiting read()
        if self._thread is not None:
            self._thread.join(timeout=5)
        try:
            self.picam2.stop()
        except Exception:
            pass
        self.picam2.close()
