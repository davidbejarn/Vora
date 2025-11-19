import cv2
import signal
import sys
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

face_cascade = cv2.CascadeClassifier(
    r"/Users/it/Documents/Vora Ex/vora/haarcascade/haarcascade_frontalface_default.xml"
)

pidfile = os.path.join(os.path.dirname(__file__), "facial.pid")
try:
    with open(pidfile, "w") as f:
        f.write(str(os.getpid()))
except Exception:
    pass

stop_event = threading.Event()
cam = None
_shutdown_server = None

def cleanup(signum=None, frame=None):
    global cam, _shutdown_server
    stop_event.set()
    try:
        if cam is not None:
            cam.release()
    except Exception:
        pass
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass
    try:
        if _shutdown_server is not None:
            try:
                _shutdown_server.shutdown()
            except Exception:
                pass
            try:
                _shutdown_server.server_close()
            except Exception:
                pass
    except Exception:
        pass
    try:
        if os.path.exists(pidfile):
            os.remove(pidfile)
    except Exception:
        pass
    try:
        sys.exit(0)
    except SystemExit:
        pass

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

# HTTP shutdown handler (escucha en localhost)
class _ShutdownHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/shutdown":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"shutting down")
            stop_event.set()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # silenciar logs en consola
        return

def _start_shutdown_server(port=51234):
    global _shutdown_server
    try:
        server = HTTPServer(("127.0.0.1", port), _ShutdownHandler)
        _shutdown_server = server
        th = threading.Thread(target=server.serve_forever, daemon=True)
        th.start()
    except Exception:
        _shutdown_server = None

# iniciar servidor de shutdown local
_start_shutdown_server(port=51234)

if face_cascade.empty():
    print("Error en reconocimiento facial")
else:
    print("Reconocimiento facial activado (puedes cerrar vía POST http://127.0.0.1:51234/shutdown o presionando 'q' / ESC)")

cam = cv2.VideoCapture(0)

try:
    while True:
        if stop_event.is_set():
            break

        ret, frame = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30,30))

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 255), 2)

        cv2.putText(frame, "Presiona 'q' o ESC para cerrar", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2, cv2.LINE_AA)

        cv2.imshow("Detector Facial", frame)

        key = cv2.waitKey(20) & 0xFF
        if key == ord('q') or key == 27:  # 'q' o ESC
            break

        try:
            prop = cv2.getWindowProperty("Detector Facial", cv2.WND_PROP_VISIBLE)
            if prop < 1:
                break
        except Exception:
            pass

finally:
    cleanup()