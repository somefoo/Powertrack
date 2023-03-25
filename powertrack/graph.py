# Open a window using GTK and display the battery status

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

import time
import cairo
import math


def draw_graph_xy_scale(area, context, value_getter, setting):
    # Rewrite draw_graph_xy using new setting format
    values = value_getter()
    # Clear
    cr = context
    cr.set_source_rgb(1, 1, 1)
    cr.paint()

    scale = 1 - setting["margin"]
    cr.scale(area.get_allocated_width(), area.get_allocated_height())
    cr.translate((1-scale) / 2, (1-scale) / 2)
    cr.scale(scale, scale)

    def draw_background(cr):
        # Draw axis labels  
        font_size = 0.04
        label_font_size = 0.06

        # Add labels
        cr.set_source_rgb(0.9, 0.9, 0.9)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(label_font_size)
        # Add x-label
        (x_bearing, y_bearing, width, height, x_advance, y_advance) = cr.text_extents(setting["x"]["label"])
        cr.move_to(0.5 - width / 2 - x_bearing, 1 - height)
        cr.show_text(setting["x"]["label"])
        # Add y-label
        (x_bearing, y_bearing, width, height, x_advance, y_advance) = cr.text_extents(setting["y"]["label"])
        cr.move_to(height*2, 0.5 + width / 2)
        cr.rotate(-math.pi / 2)
        cr.show_text(setting["y"]["label"])
        cr.rotate(math.pi / 2)

        # Reset font
        cr.set_font_size(font_size)

        # Draw axis tics and labels
        line_width = 0.005
        cr.set_line_width(line_width)
        cr.set_source_rgb(0.5, 0.5, 0.5)
        # Draw y-axis tics
        for i in range(setting["y"]["tics"]):
            cr.move_to(0 - line_width/2, 1.0 - i / (setting["y"]["tics"] - 1) * (1.0 - 2.0 * 0))
            cr.line_to(1 + line_width/2, 1.0 - i / (setting["y"]["tics"] - 1) * (1.0 - 2.0 * 0))
            cr.stroke()
            text = str(round(setting["y"]["min"] + i / (setting["y"]["tics"] - 1) * (setting["y"]["max"] - setting["y"]["min"]), 2))

            # If the last tick, make sure the text is inside the box
            if i == 0:
                # Ensure there is no text overlap at (0,0)
                text_height = (_,_,_,height,_,_) = cr.text_extents(text)
                cr.move_to(0, 1.0 - i / (setting["y"]["tics"] - 1) - height)
            elif i < setting["y"]["tics"] - 1:
                cr.move_to(0, 1.0 - 0 - i / (setting["y"]["tics"] - 1))
            else:
                # Ensure no text lies outside
                text_height = (_,_,_,height,_,_) = cr.text_extents(text)
                cr.move_to(0, 1.0 - 0 - i / (setting["y"]["tics"] - 1) + height)

            cr.show_text(text)
        # Draw x-axis tics
        for i in range(setting["x"]["tics"]):
            cr.move_to(i / (setting["x"]["tics"] - 1), 0)
            cr.line_to(i / (setting["x"]["tics"] - 1), 1.0)
            cr.stroke()
            text = str(round((setting["x"]["min"] + i / (setting["x"]["tics"] - 1) * (setting["x"]["max"] - setting["x"]["min"])) * setting["x"]["scale_on_label"], 2))


            if i == 0:
                # Offset by half a character
                text_height = (_,_,width,_,_,_) = cr.text_extents("a")
                cr.move_to(width/2, 1.0)
            elif i < setting["x"]["tics"] - 1:
                cr.move_to(i / (setting["x"]["tics"] - 1), 1.0)
            else:
                # Ensure no text lies outside
                text_width = (_,_,width,_,_,_) = cr.text_extents(text)
                cr.move_to(i / (setting["x"]["tics"] - 1) - width, 1.0)
            cr.show_text(text)

    def draw_graph(cr, values):
        if len(values) == 0:
            return
        # Draw graph with 0
        cr.set_line_width(0.01)
        cr.set_source_rgb(0.31*0.5, 1.0*0.5, 0.41*0.5)
        x_max = setting["x"]["max"]
        x_min = setting["x"]["min"]
        y_max = setting["y"]["max"]
        y_min = setting["y"]["min"]

        values_max_x = values[-1][0]

        values = [((x - x_min) / (x_max - x_min), y) for (x, y) in values]

        cr.move_to(values[0][0], 1 - (values[0][1] - y_min) / (y_max - y_min))
        for i in range(1, len(values)):
            cr.line_to(values[i][0], 1 - (values[i][1] - y_min) / (y_max - y_min))
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.stroke()

    draw_background(cr)
    draw_graph(cr, values)

