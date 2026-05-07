# DEPRECATED – The legacy `picamera` library is no longer supported on
# Raspberry Pi OS Bullseye or later.  Use CAMERA = "pilibcam" in config.py
# which uses picamera2/libcamera instead.
#
# This file is retained only as a reference for users still running
# Pi OS Buster with the legacy camera stack enabled.

import sys
import time
from threading import Thread


class CamStream:
    def __init__(self, size=(320, 240), framerate=30, rotation=0,
                 hflip=False, vflip=False, **kwargs):
        try:
            from picamera import PiCamera
            from picamera.array import PiRGBArray
        except ImportError:
            print(
                "ERROR: 'picamera' is not installed.\n"
                "The legacy picamera library is not available on Pi OS Bullseye+.\n"
                "Set CAMERA = 'pilibcam' in config.py to use picamera2 instead."
            )
            sys.exit(1)

        try:
            self.camera = PiCamera()
        except Exception:
            print("ERROR: PiCamera already in use by another process.")
            sys.exit(1)

        self.camera.resolution = size
        self.camera.rotation = rotation
        self.camera.framerate = framerate
        self.camera.hflip = hflip
        self.camera.vflip = vflip
        for arg, value in kwargs.items():
            setattr(self.camera, arg, value)

        self.rawCapture = PiRGBArray(self.camera, size=size)
        self.stream = self.camera.capture_continuous(
            self.rawCapture, format="bgr", use_video_port=True
        )
        self.frame = None
        self.stopped = False
        self._thread = None

    def start(self):
        self._thread = Thread(target=self._update, daemon=True)
        self._thread.start()
        return self

    def _update(self):
        for f in self.stream:
            self.frame = f.array
            self.rawCapture.truncate(0)
            if self.stopped:
                self.stream.close()
                self.rawCapture.close()
                self.camera.close()
                return

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        if self._thread is not None:
            self._thread.join(timeout=5)
