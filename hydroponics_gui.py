import tkinter as tk
from helpers import (
    create_switch,
    update_clock,
    update_connection_status,
    connect_to_arduino,
    send_command_to_arduino,
)


class HydroponicsGUI:
    def __init__(self, root, arduino):
        self.root = root
        self.arduino = arduino
        self.root.title("Hydroponics System Control")
        self.root.geometry("800x580")  # Set resolution to match Raspberry Pi touchscreen
        # self.root.attributes("-fullscreen", False)  # Enable fullscreen mode

        # Top frame for clock and Arduino connection indicator
        self.top_frame = tk.Frame(self.root, padx=10, pady=5)
        self.top_frame.pack(fill=tk.X, side=tk.TOP)

        # Clock display
        self.clock_label = tk.Label(self.top_frame, text="", font=("Helvetica", 18))
        self.clock_label.pack(side=tk.LEFT, padx=20)

        # Arduino connection indicator with label
        connection_frame = tk.Frame(self.top_frame)
        connection_frame.pack(side=tk.RIGHT, padx=20)
        connection_label = tk.Label(connection_frame, text="Arduino Connected", font=("Helvetica", 16))
        connection_label.grid(row=0, column=0, padx=(0, 10))
        self.connection_indicator = tk.Canvas(connection_frame, width=20, height=20, highlightthickness=0)
        self.connection_indicator.grid(row=0, column=1)
        if self.arduino:
            update_connection_status(self)

        # Main frame to organize layout
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Left frame for manual controls (switches and lights)
        self.left_frame = tk.Frame(self.main_frame, width=400, padx=10, pady=10)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Relay switches group
        self.relay_frame = tk.LabelFrame(self.left_frame, text="Manual Relay Control", font=("Helvetica", 16))
        self.relay_frame.pack(fill="both", expand=True, anchor="nw")

        # Right frame for temperature and other indicators
        self.right_frame = tk.Frame(self.main_frame, width=400, padx=10, pady=10)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Sensors group
        sensor_frame = tk.LabelFrame(self.right_frame, text="Sensor Readings", font=("Helvetica", 16))
        sensor_frame.pack(fill="both", expand=True, anchor="nw")

        # Manual controls on the left
        self.states = {
            "lights_top": {"state": False, "schedule": "", "description_label": None, "device_code": "LT"},
            "lights_bottom": {"state": False, "schedule": "", "description_label": None, "device_code": "LB"},
            "pump_top": {"state": False, "schedule": "", "description_label": None, "device_code": "PT"},
            "pump_bottom": {"state": False, "schedule": "", "description_label": None, "device_code": "PB"},
        }
        create_switch(self.relay_frame, self, "Lights (Top)", 0, "lights_top", "LT")
        create_switch(self.relay_frame, self, "Lights (Bottom)", 1, "lights_bottom", "LB")
        create_switch(self.relay_frame, self, "Pump (Top)", 2, "pump_top", "PT")
        create_switch(self.relay_frame, self, "Pump (Bottom)", 3, "pump_bottom", "PB")

        # Removed sensor pump and drain actuator switches (not part of current manual override system)

        # Temperature display
        self.temperature_label = tk.Label(
            sensor_frame, text="Temperature: -- °C | -- °F", font=("Helvetica", 20), anchor="w", justify="left"
        )
        self.temperature_label.pack(pady=5, anchor="w", fill="x")
        # Humidity display
        self.humidity_label = tk.Label(sensor_frame, text="Humidity: -- %", font=("Helvetica", 18), anchor="w", justify="left")
        self.humidity_label.pack(pady=3, anchor="w", fill="x")

        # Additional Arduino data labels (combined top/bottom for pH and EC)
        self.ph_label = tk.Label(sensor_frame, text="pH (Top/Bottom): -- / --", font=("Helvetica", 18), anchor="w", justify="left")
        self.ph_label.pack(pady=3, anchor="w", fill="x")

        self.ec_label = tk.Label(sensor_frame, text="EC (Top/Bottom): -- / --", font=("Helvetica", 18), anchor="w", justify="left")
        self.ec_label.pack(pady=3, anchor="w", fill="x")

        self.water_temp1_label = tk.Label(sensor_frame, text="Water Temp 1: -- °C", font=("Helvetica", 18), anchor="w", justify="left")
        self.water_temp1_label.pack(pady=3, anchor="w", fill="x")

        self.water_temp2_label = tk.Label(sensor_frame, text="Water Temp 2: -- °C", font=("Helvetica", 18), anchor="w", justify="left")
        self.water_temp2_label.pack(pady=3, anchor="w", fill="x")

        self.water_level_top_label = tk.Label(
            sensor_frame, text="Water Level (Top): --", font=("Helvetica", 18), anchor="w", justify="left"
        )
        self.water_level_top_label.pack(pady=3, anchor="w", fill="x")

        self.water_level_bottom_label = tk.Label(
            sensor_frame, text="Water Level (Bottom): --", font=("Helvetica", 18), anchor="w", justify="left"
        )
        self.water_level_bottom_label.pack(pady=3, anchor="w", fill="x")

        # Reset button (directly under right_frame)
        self.reset_button = tk.Button(
            self.right_frame,
            text="Reset to Schedule",
            font=("Helvetica", 14),
            bg="blue",
            fg="white",
            width=20,
            command=self.reset_to_arduino_schedule,
        )
        self.reset_button.pack(pady=5, anchor="w")

        # Start clock updates
        update_clock(self)

        # Load and apply the schedule
        # load_schedule(self)

        # Ensure all switches are OFF at startup
        self.initialize_switches()
        if self.arduino:
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M:%S")
            send_command_to_arduino(self.arduino, f"SET_TIME:{current_time}\n")

        self.poll_relay_status()
        self.poll_sensor_data()

    def initialize_switches(self):
        """Ensure all switches are OFF at startup."""
        print("Initializing all switches to OFF...")
        for state_key, info in self.states.items():
            info["state"] = False
            info["button"].config(text="OFF", bg="darkgrey")
            info["light"].delete("all")
            info["light"].create_oval(2, 2, 18, 18, fill="red")
            send_command_to_arduino(self.arduino, f"{info['device_code']}:OFF\n")

    def reset_all_switches(self):
        """Turn all switches off."""
        print("Resetting all switches to OFF...")
        self.initialize_switches()

    def reset_to_arduino_schedule(self):
        reset_to_arduino_schedule(self.arduino)

    def update_relay_states(self, message):
        """
        Update relay and sensor states from Arduino message and update float sensor water level labels.
        Expects message format: ...;float_top;float_bottom;...
        """
        if message.startswith("RELAYS:"):
            parts = message[len("RELAYS:"):].strip().split(",")
            if len(parts) != 7:
                return
            relay_keys = ["lights_top", "lights_bottom", "pump_top", "pump_bottom", "sensor_pump_top", "sensor_pump_bottom", "drain_actuator"]
            for i, key in enumerate(relay_keys):
                if key in self.states:
                    state = parts[i] == "1"
                    self.states[key]["state"] = state
                    self.states[key]["button"].config(
                        text="ON" if state else "OFF",
                        bg="darkgreen" if state else "darkgrey"
                    )
                    self.states[key]["light"].delete("all")
                    self.states[key]["light"].create_oval(2, 2, 18, 18, fill="green" if state else "red")
            return

        if message.startswith("SENSORS:"):
            parts = message[len("SENSORS:"):].strip().split(",")
            if len(parts) != 6:
                return
            temp, humid, water_temp1, water_temp2, float_top, float_bottom = parts
            self.temperature_label.config(text=f"Temperature: {temp} °C", fg="black" if temp != "-1" else "red")
            self.humidity_label.config(text=f"Humidity: {humid} %", fg="black" if humid != "-1" else "red")
            self.water_temp1_label.config(text=f"Water Temp 1: {water_temp1} °C")
            self.water_temp2_label.config(text=f"Water Temp 2: {water_temp2} °C")
            self.water_level_top_label.config(
                text=f"Water Level (Top): {'HIGH' if float_top == '1' else 'LOW'}",
                fg="black" if float_top == '1' else "red"
            )
            self.water_level_bottom_label.config(
                text=f"Water Level (Bottom): {'HIGH' if float_bottom == '1' else 'LOW'}",
                fg="black" if float_bottom == '1' else "red"
            )
            return

        # Example message: ...;...;...;...;...;float_top;float_bottom;...
        if not message.startswith("STATE:"):
            return
        parts = message[len("STATE:"):].strip().split(",")
        if len(parts) != 17:
            return
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

    def poll_relay_status(self):
        if self.arduino:
            try:
                send_command_to_arduino(self.arduino, "GET_RELAYS\n")
            except Exception as e:
                print(f"Failed to request relay status: {e}")
        self.root.after(1000, self.poll_relay_status)

    def poll_sensor_data(self):
        if self.arduino:
            try:
                send_command_to_arduino(self.arduino, "GET_SENSORS\n")
            except Exception as e:
                print(f"Failed to request sensor data: {e}")
        self.root.after(60000, self.poll_sensor_data)


def main():
    import sys
    simulate = "--simulate" in sys.argv

    if simulate:
        print("🧪 Running in simulation mode. No Arduino connection will be attempted.")
        arduino = None
    else:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        if ports:
            port = ports[0].device
            print(f"Connecting to Arduino on port: {port}")
            arduino = connect_to_arduino(port, 9600)
        else:
            print("No serial ports found. Cannot connect to Arduino.")
            arduino = None

    root = tk.Tk()
    root.geometry("800x580")  # Match Raspberry Pi touchscreen resolution
    app = HydroponicsGUI(root, arduino)

    def on_closing():
        if arduino:
            arduino.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
    def toggle_switch(self, state_key):
        info = self.states[state_key]
        current_state = info["state"]
        new_state = not current_state
        info["state"] = new_state
        info["button"].config(
            text="ON" if new_state else "OFF",
            bg="darkgreen" if new_state else "darkgrey"
        )
        info["light"].delete("all")
        info["light"].create_oval(2, 2, 18, 18, fill="green" if new_state else "red")
        send_command_to_arduino(self.arduino, f"{info['device_code']}:{'ON' if new_state else 'OFF'}\n")