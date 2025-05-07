import tkinter as tk
import threading
import time
import serial
from datetime import datetime

# -------------------- Arduino Communication --------------------

def check_arduino_connection(arduino):
    
    """Check if the Arduino is still responding."""
    if not arduino:
        return False
    try:
        arduino.write(b"PING\n")
        time.sleep(0.1)
        if arduino.in_waiting > 0:
            response = arduino.readline().decode().strip()
            return response == "PING_OK"
    except Exception:
        return False
    return False


def connect_to_arduino(port=None, baudrate=9600):
    if port:
        try:
            arduino = serial.Serial(port, baudrate, timeout=2)
            time.sleep(2)
            print(f"✅ Connected to Arduino on {port}")
            return arduino
        except Exception as e:
            print(f"⚠ Failed to connect to Arduino on {port}: {e}")
            return None
    else:
        POSSIBLE_PORTS = ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]
        for p in POSSIBLE_PORTS:
            try:
                arduino = serial.Serial(p, baudrate, timeout=2)
                time.sleep(2)
                print(f"✅ Connected to Arduino on {p}")
                return arduino
            except Exception:
                continue
        print("⚠ No Arduino found.")
        return None

def send_command_to_arduino(arduino, command):
    if arduino:
        try:
            arduino.write(command.encode())
            print(f"📤 Sent command: {command.strip()}")
        except Exception as e:
            print(f"⚠ Error sending command: {e}")


def set_time_on_arduino(arduino):
    if arduino:
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            send_command_to_arduino(arduino, f"SET_TIME:{current_time}\n")
        except Exception as e:
            print(f"⚠ Error sending time to Arduino: {e}")

def reset_to_arduino_schedule(arduino):
    if not arduino:
        print("⚠ Arduino is not connected. Cannot reset schedule.")
        return
    print("🔄 Resetting to Arduino schedule...")
    send_command_to_arduino(arduino, "RESET_SCHEDULE\n")
    time.sleep(1)
    send_command_to_arduino(arduino, "GET_STATE\n")

def start_relay_state_listener(gui):
    def listen_for_state():
        while True:
            try:
                if gui.arduino and gui.arduino.in_waiting > 0:
                    response = gui.arduino.readline().decode().strip()
                    if response.startswith("STATE:"):
                        gui.update_relay_states(response)
            except Exception as e:
                print(f"⚠ Error reading state update: {e}")
                gui.arduino = None  # Mark as disconnected
                break
    threading.Thread(target=listen_for_state, daemon=True).start()

# -------------------- GUI Helpers --------------------

def create_switch(gui, label_text, row, state_key, device_code):
    label = tk.Label(gui.left_frame, text=label_text, font=("Helvetica", 18))
    label.grid(row=row, column=0, padx=10, pady=10, sticky="w")

    button = tk.Button(
        gui.left_frame,
        text="OFF",
        font=("Helvetica", 18),
        bg="darkgrey",
        fg="white",
        width=10,
        command=lambda: gui.toggle_switch(state_key),
    )
    button.grid(row=row, column=1, padx=10, pady=10)

    light = tk.Canvas(gui.left_frame, width=20, height=20, highlightthickness=0)
    light.grid(row=row, column=2, padx=10, pady=10)
    light.create_oval(2, 2, 18, 18, fill="red")

    gui.states[state_key]["button"] = button
    gui.states[state_key]["light"] = light

def create_reset_button(gui):
    reset_button = tk.Button(
        gui.left_frame,
        text="Reset to Schedule",
        font=("Helvetica", 16),
        bg="blue",
        fg="white",
        width=20,
        command=gui.reset_to_arduino_schedule,
    )
    reset_button.grid(row=5, column=0, columnspan=3, pady=20)

def update_clock(gui):
    def refresh_clock():
        while True:
            current_time = time.strftime("%b %d %H:%M")
            gui.clock_label.config(text=current_time)
            time.sleep(1)
    threading.Thread(target=refresh_clock, daemon=True).start()

def update_connection_status(gui):
    def check_connection():
        last_state_time = time.time()
        while True:
            if gui.arduino and gui.arduino.is_open:
                try:
                    if gui.arduino.in_waiting > 0:
                        response = gui.arduino.readline().decode().strip()
                        if response.startswith("STATE:"):
                            gui.update_relay_states(response)
                            last_state_time = time.time()
                    if time.time() - last_state_time > 10:
                        update_indicator(gui.connection_indicator, "red")
                    else:
                        update_indicator(gui.connection_indicator, "green")
                except Exception:
                    update_indicator(gui.connection_indicator, "red")
                    gui.arduino = None
            else:
                update_indicator(gui.connection_indicator, "red")
                gui.arduino = None
            time.sleep(3)
    threading.Thread(target=check_connection, daemon=True).start()

def update_indicator(indicator, color):
    indicator.delete("all")
    indicator.create_oval(2, 2, 18, 18, fill=color)

def update_relay_states(self, message):
    """Parse STATE message from Arduino and update GUI elements."""
    if not message.startswith("STATE:"):
        return

    try:
        parts = message[len("STATE:"):].split(",")
        if len(parts) < 13:
            print("⚠ Incomplete STATE message.")
            return

        # Update relay indicator lights
        relay_keys = ["lights_top", "lights_bottom", "pump_top", "pump_bottom"]
        for i, key in enumerate(relay_keys):
            state = parts[i] == "1"
            self.states[key]["state"] = state
            self.states[key]["button"].config(text="ON" if state else "OFF", bg="darkgreen" if state else "darkgrey")
            self.states[key]["light"].delete("all")
            self.states[key]["light"].create_oval(2, 2, 18, 18, fill="green" if state else "red")

        # Air temperature and humidity
        dht_temp = parts[7]
        dht_humidity = parts[8]
        self.temperature_label.config(text=f"Temperature: {dht_temp} °C | Humidity: {dht_humidity} %")

        # Water temperatures
        water_temp1 = parts[9]
        water_temp2 = parts[10]

        # pH and EC (raw analog values)
        ph = parts[11]
        ec = parts[12]

        self.ph_label.config(text=f"pH: {ph}")
        self.ec_label.config(text=f"EC: {ec}")

        # Optional: add water temp display to GUI if desired

    except Exception as e:
        print(f"⚠ Error parsing STATE message: {e}")