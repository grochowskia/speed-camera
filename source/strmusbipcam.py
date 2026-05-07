import logging
from threading import Thread
import cv2


class CamStream:
    """
    Threaded OpenCV video stream for USB webcams and RTSP IP cameras.

    Captures frames continuously in a background thread so read() is
    non-blocking.  Frames are returned as BGR numpy arrays.

    Usage::

        from strmusbipcam import CamStream
        vs = CamStream(src=0, size=(320, 240)).start()          # USB webcam
        vs = CamStream(src="rtsp://user:pw@ip:554/path").start() # IP cam
        frame = vs.read()   # BGR ndarray ready for cv2
    """

    def __init__(self, src=0, size=(320, 240)):
        self.stream = cv2.VideoCapture(src)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])

        grabbed, self.frame = self.stream.read()
        if not grabbed:
            logging.warning("Could not read first frame from source: %s", src)

        self.stopped = False
        self._thread = None

    # ------------------------------------------------------------------
    def start(self):
        """Start background capture thread and return self."""
        self._thread = Thread(target=self._update, daemon=True)
        self._thread.start()
        return self

    def _update(self):
        """Continuously capture frames until stop() is called."""
        while not self.stopped:
            grabbed, frame = self.stream.read()
            if grabbed:
                self.frame = frame

    def read(self):
        """Return the most recently captured BGR frame."""
        return self.frame

    def stop(self):
        """Stop background thread then release the capture device."""
        self.stopped = True
        if self._thread is not None:
            self._thread.join(timeout=5)
        self.stream.release()
