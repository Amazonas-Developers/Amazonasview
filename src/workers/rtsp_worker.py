"""
src/workers/rtsp_worker.py
QThread que captura frames de un stream RTSP con OpenCV
y los emite como QImage para renderizar en la UI.
"""
from __future__ import annotations
import time
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui  import QImage


class RTSPWorker(QThread):
    frame_ready  = Signal(QImage)
    error        = Signal(str)
    connected    = Signal()
    disconnected = Signal()

    def __init__(
        self,
        rtsp_url:        str,
        channel_id:      str   = "",
        fps_limit:       int   = 25,
        reconnect_delay: float = 3.0,
    ):
        super().__init__()
        self.rtsp_url        = rtsp_url
        self.channel_id      = channel_id
        self.fps_limit       = fps_limit
        self.reconnect_delay = reconnect_delay
        self._running        = False
        self._paused         = False

    def stop(self):
        self._running = False
        self.wait(3000)

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def run(self):
        self._running = True
        frame_delay   = 1.0 / self.fps_limit

        while self._running:
            cap = self._open_stream()
            if cap is None:
                if not self._running:
                    break
                time.sleep(self.reconnect_delay)
                continue

            self.connected.emit()
            last_frame_time = 0.0

            while self._running:
                if self._paused:
                    time.sleep(0.05)
                    continue

                ret, frame = cap.read()
                if not ret:
                    break

                now = time.monotonic()
                if now - last_frame_time < frame_delay:
                    continue
                last_frame_time = now

                qimg = self._cv_to_qimage(frame)
                if qimg is not None:
                    self.frame_ready.emit(qimg)

            cap.release()
            if self._running:
                self.error.emit("Stream interrumpido. Reconectando…")
                time.sleep(self.reconnect_delay)

        self.disconnected.emit()

    def _open_stream(self):
        try:
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if cap.isOpened():
                return cap
            cap.release()
            self.error.emit(f"No se pudo abrir:\n{self.rtsp_url}")
            return None
        except Exception as e:
            self.error.emit(f"Error OpenCV: {e}")
            return None

    @staticmethod
    def _cv_to_qimage(frame: np.ndarray) -> QImage | None:
        try:
            rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            return QImage(
                rgb.data.tobytes(), w, h, w * ch, QImage.Format_RGB888
            ).copy()
        except Exception:
            return None
