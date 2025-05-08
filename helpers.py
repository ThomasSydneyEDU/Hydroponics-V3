import os
import tkinter as tk
import threading
import time
import serial
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error_log.txt")

SENSOR_LOG_FILE = os.path.join(LOG_DIR, f"sensor_log_{datetime.now().strftime('%Y-%m-%d')}.csv")


# Initialize sensor log file if needed
def init_sensor_log():
    if not os.path.exists(SENSOR_LOG_FILE) or os.path.getsize(SENSOR_LOG_FILE) == 0:
        with open(SENSOR_LOG_FILE, "w") as log:
            log.write("timestamp,dht_temp,dht_humidity,water_temp1,water_temp2,ph_top,ec_top,ph_bottom,ec_bottom,float_top,float_bottom\n")

init_sensor_log()

def log_error(message):
    with open(ERROR_LOG_FILE, "a") as f:
        f.write(f"[{datetime.now()}] {message}\n")

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

def create_switch(parent, gui, label_text, row, state_key, device_code):
    label = tk.Label(parent, text=label_text, font=("Helvetica", 16))
    button = tk.Button(
        parent,
        text="OFF",
        font=("Helvetica", 12),
        bg="darkgrey",
        fg="white",
        width=6,
        command=lambda: gui.toggle_switch(state_key),
    )
    light = tk.Canvas(parent, width=20, height=20, highlightthickness=0)
    # Place the widgets: light left, label center, button right
    light.grid(row=row, column=0, padx=5, pady=5)
    label.grid(row=row, column=1, padx=5, pady=5, sticky="w")
    button.grid(row=row, column=2, padx=5, pady=5)
    light.create_oval(2, 2, 18, 18, fill="red")

    gui.states[state_key]["button"] = button
    gui.states[state_key]["light"] = light

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
                        # Before setting indicator to green, check actual connection
                        if check_arduino_connection(gui.arduino):
                            update_indicator(gui.connection_indicator, "green")
                        else:
                            update_indicator(gui.connection_indicator, "red")
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

def color_for_value(value, low, high):
    try:
        val = float(value)
        if val < low or val > high:
            return "red"
        return "black"
    except ValueError:
        return "gray"

def update_relay_states(self, message):
    """Parse STATE message from Arduino and update GUI elements."""
    if not message.startswith("STATE:"):
        return

    try:
        parts = message[len("STATE:"):].split(",")
        if len(parts) != 17:
            log_error(f"Expected 17 values in STATE message, got {len(parts)}: {message}")
            print(f"⚠ Expected 17 values in STATE message, got {len(parts)}: {message}")
            return
        try:
            float(parts[9])   # Air temperature
            float(parts[10])  # Humidity
            float(parts[13])  # pH top
            float(parts[14])  # EC top
            float(parts[15])  # pH bottom
            float(parts[16])  # EC bottom
        except ValueError:
            log_error(f"Invalid numeric data in STATE message: {message}")
            print(f"⚠ Invalid numeric data in STATE message: {message}")
            return

        # Update relay indicator lights
        relay_keys = [
            "lights_top", "lights_bottom",
            "pump_top", "pump_bottom",
            "sensor_pump_top", "sensor_pump_bottom",
            "drain"
        ]
        for i, key in enumerate(relay_keys):
            state = parts[i] == "1"
            self.states[key]["state"] = state
            self.states[key]["button"].config(text="ON" if state else "OFF", bg="darkgreen" if state else "darkgrey")
            self.states[key]["light"].delete("all")
            self.states[key]["light"].create_oval(2, 2, 18, 18, fill="green" if state else "red")

        # Float sensors
        float_top = parts[7]
        float_bottom = parts[8]
        self.water_level_top_label.config(
            text=f"Water Level (Top): {'HIGH' if float_top == '1' else 'LOW'}",
            fg="black" if float_top == '1' else "red"
        )
        self.water_level_bottom_label.config(
            text=f"Water Level (Bottom): {'HIGH' if float_bottom == '1' else 'LOW'}",
            fg="black" if float_bottom == '1' else "red"
        )

        # Air temperature and humidity
        dht_temp = parts[9]
        dht_humidity = parts[10]
        self.temperature_label.config(text=f"Temperature: {dht_temp} °C | Humidity: {dht_humidity} %")

        # Water temperatures
        water_temp1 = parts[11]
        water_temp2 = parts[12]

        # pH and EC (top and bottom)
        ph_top = parts[13]
        ec_top = parts[14]
        ph_bottom = parts[15]
        ec_bottom = parts[16]

        ph_color_top = color_for_value(ph_top, 5.5, 6.5)
        ph_color_bottom = color_for_value(ph_bottom, 5.5, 6.5)
        self.ph_label.config(
            text=f"pH (Top/Bottom): {ph_top} / {ph_bottom}",
            fg=ph_color_top if ph_color_top != "black" or ph_color_bottom == "black" else ph_color_bottom
        )

        ec_color_top = color_for_value(ec_top, 1.0, 2.5)
        ec_color_bottom = color_for_value(ec_bottom, 1.0, 2.5)
        self.ec_label.config(
            text=f"EC (Top/Bottom): {ec_top} / {ec_bottom}",
            fg=ec_color_top if ec_color_top != "black" or ec_color_bottom == "black" else ec_color_bottom
        )

        # Optional: add water temp display to GUI if desired

        # Rotate the sensor log file if it exceeds 5 MB
        if os.path.getsize(SENSOR_LOG_FILE) > 5 * 1024 * 1024:  # 5 MB
            rotated_file = SENSOR_LOG_FILE.replace(".csv", f"_{datetime.now().strftime('%H%M%S')}.csv")
            os.rename(SENSOR_LOG_FILE, rotated_file)
            init_sensor_log()
        with open(SENSOR_LOG_FILE, "a") as log:
            log.write(f"{datetime.now()},{dht_temp},{dht_humidity},{water_temp1},{water_temp2},{ph_top},{ec_top},{ph_bottom},{ec_bottom},{float_top},{float_bottom}\n")

    except Exception as e:
        log_error(f"Error parsing STATE message: {e}")
        print(f"⚠ Error parsing STATE message: {e}")