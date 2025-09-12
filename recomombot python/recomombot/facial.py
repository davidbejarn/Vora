import cv2


face_cascade = cv2.CascadeClassifier(
    r"C:\Users\JuanBejarano\Downloads\recomombot python\recomombot\haarcascade\haarcascade_frontalface_default.xml"
)


if face_cascade.empty():
    print("❌ Error: no se pudo cargar el Haarcascade")
else:
    print("✅ Haarcascade cargado correctamente")


cam = cv2.VideoCapture(0)

while True:
    ret, frame = cam.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

   
    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30,30))

   
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

    cv2.imshow("Detector Facial", frame)

  
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()

print("Picture saved")
print(r"-------------")