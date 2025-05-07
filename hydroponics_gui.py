import tkinter as tk
from helpers import (
    create_switch,
    update_clock,
    update_connection_status,
    connect_to_arduino,
    send_command_to_arduino,
    reset_to_arduino_schedule,
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

        self.states.update({
            "sensor_pump_top": {"state": False, "schedule": "", "description_label": None, "device_code": "ST"},
            "sensor_pump_bottom": {"state": False, "schedule": "", "description_label": None, "device_code": "SB"},
            "drain_actuator": {"state": False, "schedule": "", "description_label": None, "device_code": "DR"},
        })
        create_switch(self.relay_frame, self, "Sensor Pump (Top)", 4, "sensor_pump_top", "ST")
        create_switch(self.relay_frame, self, "Sensor Pump (Bottom)", 5, "sensor_pump_bottom", "SB")
        create_switch(self.relay_frame, self, "Drain Actuator", 6, "drain_actuator", "DR")

        # Temperature display
        self.temperature_label = tk.Label(
            sensor_frame, text="Temperature: -- °C | -- °F", font=("Helvetica", 20), anchor="w", justify="left"
        )
        self.temperature_label.pack(pady=5, anchor="w", fill="x")
        # Humidity display
        self.humidity_label = tk.Label(sensor_frame, text="Humidity: -- %", font=("Helvetica", 18), anchor="w", justify="left")
        self.humidity_label.pack(pady=3, anchor="w", fill="x")

        # Additional Arduino data labels
        self.ec_label = tk.Label(sensor_frame, text="EC: --", font=("Helvetica", 18), anchor="w", justify="left")
        self.ec_label.pack(pady=3, anchor="w", fill="x")

        self.ph_label = tk.Label(sensor_frame, text="pH: --", font=("Helvetica", 18), anchor="w", justify="left")
        self.ph_label.pack(pady=3, anchor="w", fill="x")

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