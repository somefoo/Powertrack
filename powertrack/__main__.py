import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Gio

import threading
import time
import cairo
import math
from functools import partial

import sys
import os

try:
    from powertrack.graph import draw_graph_xy_scale
except ImportError:
    print("Import failed, defaulting to local import")
    from graph import draw_graph_xy_scale

# Needed for mock
import random

class ThreadUpdateBattery(threading.Thread):
    def __init__(self, window, freq=1):
        threading.Thread.__init__(self)
        self.window = window
        self.freq = freq



        self.power_update_freq = 1
        self.percentage_update_freq = 60 # Update the percentage every 60 seconds

    def update_gui(self, battery_info):
        self.window.label_capacity.set_text(str(battery_info['capacity']))
        self.window.label_current.set_text(str(battery_info['current']))
        self.window.label_voltage.set_text(str(battery_info['voltage']))
        self.window.label_rated.set_text(str(battery_info['rated']))
        self.window.label_health.set_text(str(battery_info['health']))
        self.window.label_status.set_text(str(battery_info['status']))
        self.window.label_time_at_power.set_text(str(battery_info['expected_time']))
        self.window.label_power.set_text(str(battery_info['power']))
        self.window.label_expected_time.set_text(str(battery_info['expected_time_by_gradient']))
        
        self.window.draw_area_power.queue_draw()
        self.window.draw_area_capacity_history.queue_draw()

    def update_percentage(self):
        pass

    def run(self):
        ticker = 0
        while True:
            battery_info = self.window.battery.get_battery_info()

            if ticker % self.power_update_freq == 0:
                # Use idle add as we are in another thread
                GLib.idle_add(self.update_gui, battery_info)
            if ticker % self.percentage_update_freq == 0:
                pass
            time.sleep(self.freq)

class TrackedValue:
    def __init__(self, value_name, frequency, number_samples=30, relative_time=True):
        self.history = []
        self.history_time = []
        self.value_name = value_name
        self.last_time = -1
        self.frequency = frequency
        self.number_samples = number_samples
        self.relative_time = relative_time

    def get_xy_history(self):
        if self.relative_time:
            return [(x - time.time(), y) for x, y in zip(self.history_time, self.history)]
        else:
            return [(x, y) for x, y in zip(self.history_time, self.history)]

    def get_gradient_line(self):
        # Compute the intersection point between the line starting at the current
        # value with a gradient of the gradient and the y axis
        def get_intersection(self, y_axis_value, gradient):
            return y_axis_value / gradient

        if len(self.history) < 2:
            return self.get_xy_history()

        # Get the current value
        current_value = self.history[-1]
        # Get the current time
        current_time = self.history_time[-1]
        # Get the gradient
        gradient = self.get_gradient()

        if gradient == 0:
            return self.get_xy_history()

        # Get the intersection point
        intersection_point = get_intersection(self, current_value, gradient)
        # Get the time at the intersection point
        intersection_time = current_time - intersection_point

        if self.relative_time:
            return self.get_xy_history() + [(intersection_time - time.time(), 0)]
        else:
            return self.get_xy_history() + [(intersection_time, 0)]

    def update(self, battery_info):
        current_time = time.time()
        if current_time > self.last_time + 1/self.frequency:
            self.history.append(battery_info[self.value_name].value)
            self.history_time.append(current_time)
            self.last_time = current_time

            if len(self.history) > self.number_samples + 1:
                self.history.pop(0)
                self.history_time.pop(0)

    def get_average(self) -> float:
        if len(self.history) < 2:
            return self.history[0]
        return sum(self.history) / len(self.history)

    def get_average_over_time(self) -> float:
        if len(self.history) < 2:
            return self.history[0]

        # Time between the first and last value
        # Time difference + (1 average time) |---|---|---
        time_diff = self.history_time[-1] - self.history_time[0] + 1/self.frequency
        # Average value
        average = self.get_average()

        return (sum(self.history) / time_diff) / self.frequency

    def get_gradient(self):
        if len(self.history) < 2:
            return 0
        time_range = self.history_time[-1] - self.history_time[0]
        value_range = self.history[-1] - self.history[0]
        return value_range / time_range

    def get_history(self) -> [float]:
        return self.history

    def reset(self):
        self.history = []
        self.history_time = []
        self.last_time = -1

# Abstact battery class
class Battery:
    def __init__(self):
        self.power_history = TrackedValue("power", 1)
        self.expected_time_history = TrackedValue("expected_time", 1)
        # 12 hours are 720 minutes are 43200 seconds. If we samples every 120 seconds we need 360 samples
        self.capacity_history = TrackedValue("capacity", 1/120, number_samples = 360)
        pass

    def get_capacity(self) -> float:
        pass

    def get_current(self) -> float:
        pass

    def get_voltage(self) -> float:
        pass

    def get_rated(self) -> float:
        pass

    def get_health(self) -> str:
        pass

    def get_status(self) -> str:
        pass

    def get_power(self) -> float:
        pass

    def get_battery_info(self):
        capacity = self.get_capacity()
        current = self.get_current() / 1000000
        voltage = self.get_voltage() / 1000000
        rated = self.get_rated() / 1000000
        health = self.get_health()
        status = self.get_status()

        power = current * voltage #W
        if power != 0:
            expected_time = abs((capacity/100) * (rated / power)) #h
        else:
            expected_time = -1

        if power > 0: # Discharging
            self.capacity_history.reset()

        class MaybeValue():
            def __init__(self, value, unit, valid, invalid_string):
                self.value = value
                self.unit = unit
                self.valid = valid
                self.invalid_string = invalid_string

            def __str__(self):
                if self.valid:
                    if isinstance(self.value, str):
                        return self.value.strip()
                    else:
                        return '{a:.1f}'.format(a=self.value) + self.unit
                else:
                    return self.invalid_string


        capacity_gradient = self.capacity_history.get_gradient()
        # Compute time until intersection with 0                               
        if capacity_gradient != 0:                                             
            expected_time_by_gradient = -capacity / capacity_gradient  
        else:
            expected_time_by_gradient = -1

        battery_info = {
            'capacity': MaybeValue(capacity, "%", capacity >= 0 and capacity <= 100, "N/A"),
            'current': MaybeValue(current, "A", True, "N/A"),
            'voltage': MaybeValue(voltage, "V", voltage >= 0, "N/A"),
            'power': MaybeValue(power, "W", True, "N/A"),
            'rated': MaybeValue(rated, "A", rated >= 0, "N/A"),
            'health': MaybeValue(health, "", True, "N/A"),
            'status': MaybeValue(status, "", True, "N/A"),
            'expected_time': MaybeValue(expected_time, "h", expected_time >= 0 and power < 0, "N/A"),
            'expected_time_by_gradient': MaybeValue(expected_time_by_gradient/3600, "h", expected_time_by_gradient >= 0 and power < 0, "Estimating..."),
        }



        self.power_history.update(battery_info)
        self.expected_time_history.update(battery_info)
        self.capacity_history.update(battery_info)

        return battery_info


class PPBattery(Battery):
    def __init__(self):
        super().__init__()
        if os.path.exists("/sys/class/power_supply/rk818-battery"):
            # Pine64 Pinephone Pro
            self.battery_path = "/sys/class/power_supply/rk818-battery/"
        elif os.path.exists("/sys/class/power_supply/axp20x-battery"):
            # Pine64 Pinephone
            self.battery_path = "/sys/class/power_supply/axp20x-battery/"

    def get_capacity(self) -> float:
        #with open('/sys/class/power_supply/rk818-battery/capacity', 'r') as f:
        with open(self.battery_path + 'capacity', 'r') as f:
            return float(f.read())
    def get_current(self) -> float:
        #with open('/sys/class/power_supply/rk818-battery/current_now', 'r') as f:
        with open(self.battery_path + 'current_now', 'r') as f:
            return float(f.read())
    def get_voltage(self) -> float:
        #with open('/sys/class/power_supply/rk818-battery/voltage_now', 'r') as f:
        with open(self.battery_path + 'voltage_now', 'r') as f:
            return float(f.read())
    def get_rated(self) -> float:
        #return 11.8
        #with open('/sys/class/power_supply/rk818-battery/energy_full_design', 'r') as f:
        with open(self.battery_path + 'energy_full_design', 'r') as f:
            return float(f.read())
    def get_health(self) -> str:
        #with open('/sys/class/power_supply/rk818-battery/health', 'r') as f:
        with open(self.battery_path + 'health', 'r') as f:
            return f.read()
    def get_status(self) -> str:
        #with open('/sys/class/power_supply/rk818-battery/status', 'r') as f:
        with open(self.battery_path + 'status', 'r') as f:
            return f.read()

class MockBattery(Battery):
    def __init__(self):
        super().__init__()
        self.capacity = 100

    def get_capacity(self):
        self.capacity -= 0.5
        return self.capacity
    def get_current(self):
        return random.randint(500000, 1000000)
    def get_voltage(self):
        return 3200000
    def get_rated(self):
        return 11.4 * 1000000
    def get_health(self):
        return "Good"
    def get_status(self):
        return "Charging"


class Powertrack(Gtk.Application):
    def __init__(self, debug=False):
        Gtk.Application.__init__(self, application_id="de.somefoo.powertrack", flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("startup", self.on_startup)
        self.debug = debug

    def on_startup(self, application):
        if self.debug:
            self.window = BatteryWindow(MockBattery(), self, self.debug)
        else:
            self.window = BatteryWindow(PPBattery(), self, self.debug)

class ClosingMessageDialogue(Gtk.MessageDialog):
    def __init__(self, parent):
        Gtk.MessageDialog.__init__(self, transient_for=parent, flags=Gio.ApplicationFlags.FLAGS_NONE,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Do you really want to exit? Tracked information will be lost!")

        self.connect("response", self.on_response)

    def on_response(self, widget, response):
        if response == Gtk.ResponseType.OK:
            exit()
        self.destroy()

class BatteryWindow(Gtk.Window):
    def __init__(self, battery : Battery, app : Gtk.Application, debug=False):
        self.battery = battery

        # Load glade config file
        builder = Gtk.Builder()
        if debug:
            builder.add_from_file("powertrack.glade")
        else:
            builder.add_from_resource('/de/somefoo/powertrack/powertrack.glade')

        # Get the window object
        window = builder.get_object("window1")
        window.set_application(app)
        window.connect("destroy", Gtk.main_quit)

        # Create dialogue box if user tries to close window
        window.connect("delete-event", lambda w, e: ClosingMessageDialogue(w).run())

        window.set_title("Powertrack")

        # Get the label object
        self.label_capacity = builder.get_object("label_capacity")
        self.label_current = builder.get_object("label_current")
        self.label_voltage = builder.get_object("label_voltage")
        self.label_rated = builder.get_object("label_rated")
        self.label_health = builder.get_object("label_health")
        self.label_status = builder.get_object("label_status")
        self.label_time_at_power = builder.get_object("label_time_at_power")
        self.label_power = builder.get_object("label_power")
        self.label_rated = builder.get_object("label_rated")
        self.label_expected_time = builder.get_object("label_expected_time")

        # Get the draw area
        self.draw_area_power = builder.get_object("draw_area_power")
        self.draw_area_capacity_history = builder.get_object("draw_area_capacity_history")


        # Turn above into dict
        power_graph_config = {
            'x': {
                'label': 'Time (s)',
                'tics': 2,
                'max': 0,
                'min': -30,
                "scale_on_label": 1,
            },
            'y': {
                'label': 'Power (W)',
                'tics': 16 + 1,
                'max': 8,
                'min': -8,
            },
            'margin': 0.1,
        }




        capacity_graph_config = {
            "x": {
                "label": "Time (h)",
                "tics": 4 + 1,
                "max": 3600 * 12,
                "min": -3600 * 12,
                "scale_on_label": 1/3600,
            },
            "y": {
                "label": "Capacity (%)",
                "tics": 4+1,
                "max": 100,
                "min": 0,
            },
            "margin": 0.1
        }



        self.draw_area_power.connect("draw", draw_graph_xy_scale, self.battery.power_history.get_xy_history, power_graph_config)
        self.draw_area_capacity_history.connect("draw", draw_graph_xy_scale, self.battery.capacity_history.get_gradient_line, capacity_graph_config)

        thread = ThreadUpdateBattery(self)
        thread.daemon = True
        thread.start()

        window.show_all()
        Gtk.main()




def main(version):
    print(f"Startion Powertrack {version}")
    app = Powertrack()
    app.run(None)

# If this file is run directly, run the main function with debug enabled
if __name__ == "__main__":
    print(f"Startion Powertrack DEBUG")
    app = Powertrack(debug=True)
    app.run(None)

