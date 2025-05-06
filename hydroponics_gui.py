import tkinter as tk
from gui_helpers import (
    create_switch,
    create_reset_button,
    update_clock,
    update_temperature,
    update_arduino_data,
    update_connection_status,
    load_schedule,
    update_schedule_visibility,
)
from arduino_helpers import connect_to_arduino, send_command_to_arduino


class HydroponicsGUI:
    def __init__(self, root, arduino):
        self.root = root
        self.arduino = arduino
        self.root.title("Hydroponics System Control")
        self.root.geometry("800x480")  # Set resolution to match Raspberry Pi touchscreen
        self.root.attributes("-fullscreen", False)  # Enable fullscreen mode

        # Top frame for clock and Arduino connection indicator
        self.top_frame = tk.Frame(self.root, padx=20, pady=10)
        self.top_frame.pack(fill=tk.X, side=tk.TOP)

        # Clock display
        self.clock_label = tk.Label(self.top_frame, text="", font=("Helvetica", 24))
        self.clock_label.pack(side=tk.LEFT, padx=20)

        # Arduino connection indicator with label
        connection_frame = tk.Frame(self.top_frame)
        connection_frame.pack(side=tk.RIGHT, padx=20)
        connection_label = tk.Label(connection_frame, text="Arduino Connected", font=("Helvetica", 16))
        connection_label.grid(row=0, column=0, padx=(0, 10))
        self.connection_indicator = tk.Canvas(connection_frame, width=20, height=20, highlightthickness=0)
        self.connection_indicator.grid(row=0, column=1)
        update_connection_status(self)

        # Main frame to organize layout
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Left frame for manual controls (switches and lights)
        self.left_frame = tk.Frame(self.main_frame, width=400, padx=20, pady=20)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right frame for temperature and other indicators
        self.right_frame = tk.Frame(self.main_frame, width=400, padx=20, pady=20)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Manual controls on the left
        self.states = {
            "lights_top": {"state": False, "schedule": "", "description_label": None},
            "lights_bottom": {"state": False, "schedule": "", "description_label": None},
            "pump_top": {"state": False, "schedule": "", "description_label": None},
            "pump_bottom": {"state": False, "schedule": "", "description_label": None},
        }
        create_switch(self, "Lights (Top)", 0, "lights_top", "LT")
        create_switch(self, "Lights (Bottom)", 1, "lights_bottom", "LB")
        create_switch(self, "Pump (Top)", 2, "pump_top", "PT")
        create_switch(self, "Pump (Bottom)", 3, "pump_bottom", "PB")

        # Reset button
        create_reset_button(self)

        # Schedule toggle
        self.schedule_enabled = tk.BooleanVar(value=True)
        schedule_toggle = tk.Checkbutton(
            self.left_frame,
            text="Schedule On",
            font=("Helvetica", 16),
            variable=self.schedule_enabled,
            pady=10,
            command=lambda: update_schedule_visibility(self),
        )
        schedule_toggle.grid(row=5, column=0, columnspan=3)

        # Temperature display
        self.temperature_label = tk.Label(
            self.right_frame, text="Temperature: -- °C | -- °F", font=("Helvetica", 20)
        )
        self.temperature_label.pack(pady=10, anchor="center")

        # Additional Arduino data labels
        self.ec_label = tk.Label(self.right_frame, text="EC: --", font=("Helvetica", 18))
        self.ec_label.pack(pady=5, anchor="center")

        self.ph_label = tk.Label(self.right_frame, text="pH: --", font=("Helvetica", 18))
        self.ph_label.pack(pady=5, anchor="center")

        self.water_level_top_label = tk.Label(
            self.right_frame, text="Water Level (Top): --", font=("Helvetica", 18)
        )
        self.water_level_top_label.pack(pady=5, anchor="center")

        self.water_level_bottom_label = tk.Label(
            self.right_frame, text="Water Level (Bottom): --", font=("Helvetica", 18)
        )
        self.water_level_bottom_label.pack(pady=5, anchor="center")

        # Start clock and temperature updates
        update_clock(self)
        update_temperature(self)
        update_arduino_data(self)

        # Load and apply the schedule
        load_schedule(self)

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


def main():
    arduino = connect_to_arduino("/dev/ttyACM0", 9600)
    root = tk.Tk()
    app = HydroponicsGUI(root, arduino)
    root.mainloop()
    if arduino:
        arduino.close()


if __name__ == "__main__":
    main()