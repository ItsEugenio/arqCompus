from gpiozero import LEDBoard
import time
import threading
import Adafruit_DHT
import RPi.GPIO as GPIO
import tkinter as tk
from PIL import Image, ImageTk
import cv2

# Configuración de GPIO
sensor = Adafruit_DHT.DHT11  # o DHT22
temperature_pin = 23
echo = 21
trig = 20

GPIO.setmode(GPIO.BCM)
GPIO.setup(trig, GPIO.OUT)
GPIO.setup(echo, GPIO.IN)

# Configuración de LEDs y motores
leds = LEDBoard(4, 5, 7, 8, 9, pwm=True)
GPIO.setup(6, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(13, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(19, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(26, GPIO.OUT, initial=GPIO.LOW)

camera_color = "C"
all_distances = []
last_distances = []
distance_lock = threading.Lock()

def apply_infrared_effect(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    infrared = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
    return infrared

def read_temperature():
    try:
        while True:
            humedad, temperatura = Adafruit_DHT.read_retry(sensor, temperature_pin)
            if humedad is not None and temperatura is not None:
                print(f'Temperatura={temperatura:.1f}°C  Humedad={humedad:.1f}%')
                print('================================')
                update_dht_gui(humedad, temperatura)
            else:
                print('Fallo en la lectura del sensor')
            time.sleep(3)
    except Exception as e:
        print(str(e))

def forward():
    GPIO.output(6, True)
    GPIO.output(13, False)
    GPIO.output(19, True)
    GPIO.output(26, False)

def reverse():
    GPIO.output(6, False)
    GPIO.output(13, True)
    GPIO.output(19, False)
    GPIO.output(26, True)

def left_turn():
    GPIO.output(6, False)
    GPIO.output(13, True)
    GPIO.output(19, True)
    GPIO.output(26, False)

def right_turn():
    GPIO.output(6, True)
    GPIO.output(13, False)
    GPIO.output(19, False)
    GPIO.output(26, True)

def stop():
    GPIO.output(6, False)
    GPIO.output(13, False)
    GPIO.output(19, False)
    GPIO.output(26, False)

def measure_distance():
    GPIO.output(trig, True)
    time.sleep(0.00001)  # 10 microseconds
    GPIO.output(trig, False)

    start_time = time.time()
    end_time = start_time

    while GPIO.input(echo) == 0:
        start_time = time.time()
    while GPIO.input(echo) == 1:
        end_time = time.time()

    duration = end_time - start_time
    distance = round((duration * 34300) / 2, 2)
    return distance

def update_leds(leds_to_turn_on):
    for i in range(5):
        if i < leds_to_turn_on:
            leds[i].on()
        else:
            leds[i].off()

def read_distance():
    while True:
        distance = measure_distance()

        if 5 <= distance <= 25:
            leds_on = distance // 5
        elif distance > 25:
            leds_on = 5
        else:
            leds_on = 0

        update_leds(leds_on)
        update_leds_gui(leds_on)

        with distance_lock:
            all_distances.append(distance)
            last_distances.append(distance)
            
            if distance < 7:
                stop()
                
            if len(last_distances) > 12:
                last_distances.pop(0)

        update_distance_gui(distance)
        time.sleep(0.5)

def update_dht_gui(humedad, temperatura):
    temperature_label_var.set(f'Temperatura: {temperatura:.2f}°C')
    humidity_label_var.set(f'Humedad: {humedad:.2f}%')

def update_distance_gui(distance):
    distance_label_var.set(f"Distancia: {distance} cm")
    with distance_lock:
        all_distances_str = '\n'.join(str(dist) for dist in last_distances)
    last_distances_gui.delete(1.0, tk.END)
    last_distances_gui.insert(tk.END, all_distances_str)

def update_leds_gui(leds_on):
    leds_info_label_var.set(f'LEDs encendidos: {leds_on}')
    update_leds_gui_colors(leds_on)

def update_leds_gui_colors(leds_on):
    for i, label in enumerate(leds_labels):
        if i < leds_on:
            label.config(bg=colors_on[i])
        else:
            label.config(bg=colors_off[i])

def update_frame():
    ret, frame = cap.read()
    if ret:
        global camera_color
        if camera_color == "C":
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        elif camera_color == "B":
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        elif camera_color == "I":
            frame = apply_infrared_effect(frame)
        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)
        video_label.imgtk = imgtk
        video_label.configure(image=imgtk)
    video_label.after(10, update_frame)

def change_color(color):
    global camera_color
    camera_color = color

def on_closing():
    cap.release()
    GPIO.cleanup()
    root.destroy()

root = tk.Tk()
root.geometry("900x600")
root.title("Carrito run")
root.configure(bg="#F8F8F8")

colors_on = ["#0CFA38", "#2166FA", "#FA2C33", "#FA2C33", "#FAEF1D"]
colors_off = ["#7FFA96", "#89B5FA", "#FAA9AD", "#FAA9AD", "#FAF39D"]

info_frame = tk.Frame(root, bg="#F8F8F8")
info_frame.place(x=260, y=360)

temperature_label_var = tk.StringVar(value="Temperatura: 0°C")
temperature_label = tk.Label(info_frame, textvariable=temperature_label_var, font=('Helvetica', 18), bg="#F8F8F8")
temperature_label.pack(pady=5)

humidity_label_var = tk.StringVar(value="Humedad: 0%")
humidity_label = tk.Label(info_frame, textvariable=humidity_label_var, font=('Helvetica', 18), bg="#F8F8F8")
humidity_label.pack(pady=5)

distance_label_var = tk.StringVar(value="Distancia: 0")
distance_label = tk.Label(info_frame, textvariable=distance_label_var, font=('Helvetica', 18), bg="#F8F8F8")
distance_label.pack(pady=5)

leds_info_label_var = tk.StringVar(value="LEDs encendidos: 0")
leds_info_label = tk.Label(info_frame, textvariable=leds_info_label_var, font=('Helvetica', 18), bg="#F8F8F8")
leds_info_label.pack(pady=5)

last_distances_gui = tk.Text(root, height=12, width=20)
last_distances_gui.place(x=625, y=40)

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: No se puede abrir la cámara")
    exit()

video_label = tk.Label(root)
video_label.place(x=125, y=40, width=450, height=300)

buttons_frame = tk.Frame(root, bg="#F8F8F8")
buttons_frame.place(x=125, y=360)

color_button = tk.Button(buttons_frame, text="Color (C)", command=lambda: change_color("C"), bg="white")
color_button.pack(pady=5)

black_button = tk.Button(buttons_frame, text="B/N (B)", command=lambda: change_color("B"), bg="white")
black_button.pack(pady=5)

infrared_button = tk.Button(buttons_frame, text="Infrarrojo (I)", command=lambda: change_color("I"), bg="white")
infrared_button.pack(pady=5)

leds_labels = []
for i in range(5):
    led = tk.Label(root, width=4, height=2, bg=colors_off[i])
    led.place(x=510 + 60*i, y=360)
    leds_labels.append(led)

controls_frame = tk.Frame(root, bg="#F8F8F8")
controls_frame.place(x=600, y=480)

forward_button = tk.Button(controls_frame, text="Avanzar", command=forward)
forward_button.pack(pady=5)

right_button = tk.Button(controls_frame, text="Derecha", command=right_turn)
right_button.pack(pady=5)

left_button = tk.Button(controls_frame, text="Izquierda", command=left_turn)
left_button.pack(pady=5)

reverse_button = tk.Button(controls_frame, text="Retroceder", command=reverse)
reverse_button.pack(pady=5)

stop_button = tk.Button(controls_frame, text="Detener", command=stop)
stop_button.pack(pady=5)

close_button = tk.Button(controls_frame, text="Cerrar programa", command=on_closing, bg="red")
close_button.pack(pady=5)

root.protocol("WM_DELETE_WINDOW", on_closing)

temperature_thread = threading.Thread(target=read_temperature)
temperature_thread.daemon = True
temperature_thread.start()

distance_thread = threading.Thread(target=read_distance)
distance_thread.daemon = True
distance_thread.start()

video_frame_thread = threading.Thread(target=update_frame)
video_frame_thread.daemon = True
video_frame_thread.start()

root.mainloop()
