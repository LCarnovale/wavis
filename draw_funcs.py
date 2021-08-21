
import numpy as np
import tkinter as tk

x_scale = 1
y_scale = 1
def draw_circle(canvas: tk.Canvas, data,angle=2*np.pi, start=0, radius=200, 
        amp=20,scale=False, lock=None, fill="red"):
    """ Plot the data on a circle, spread out over the given angle.
    Give `angle=2*pi` (default) for a full circle. 
    The plotting will begin at angle `start`, default 0.

    The pen will not be raised before moving to the start, but 
    will be set to down after moving to the start and before 
    drawing the data.
    
    If `scale` is not provided or is False, the data will be normalised so that the max amplitude corresponds to
    `amp` pixels, default 20, and values of zero will lie on the radius.
    If `scale` is provided, the data will be scaled with 
    `data * scale` giving the amplitude in pixels.

    Set the radius of the circle in pixels with `radius`, default 200.
    Returns the angle of the last drawn pixel.

    If a `lock` method is provided, it will be called once any operations
    directly referencing the input data are finished.
    ie, provide the method `event.set`.

    Returns a list of tags of all the lines drawn, and the angle of the 
    last drawn point.  
    """
    sc_width = canvas.winfo_screenwidth()
    sc_height = canvas.winfo_screenheight()
    n_points = len(data)
    angles = np.linspace(start, start+angle, n_points)
    data_max = max(abs(data))
    if scale == False:
        radii = amp * data/data_max
    else:
        radii = (scale * data)
    if lock is not None:
        lock()
    radii += radius
    x_pos = x_scale * (radii * np.cos(angles)).astype(int) + sc_width // 2
    y_pos = y_scale * (radii * np.sin(angles)).astype(int) + sc_height // 2
    # line_coords = np.array([x_pos[:-1], y_pos[:-1], x_pos[1:], y_pos[1:]]).T
    line_coords = np.array([x_pos, y_pos]).T
    # turtle.up()
    tags = np.full(n_points, None, dtype=object)
    i = 0
    tags = canvas.create_line(*line_coords.flatten(), fill=fill)
    # for x1, y1, x2, y2 in zip(x_pos[:-1], y_pos[:-1], x_pos[1:], y_pos[1:]):
    #     tag = canvas.create_line(x1, y1, x2, y2, fill=fill)
    #     tags[i] = tag
    #     i += 1
    return tags, angles[-1]

def draw_stereo(left, right, scale=0.2,
        lock=None):
    """ Draws dots at x-y coordinates with left deflection
    for x and right deflection for y. Distances are multiplied
    by the global `x_scale` and `y_scale` variables as well
    as both are multiplied by the `scale` parameter, default `0.2`.

    If a `lock` method is provided, it will be called once any operations
    directly referencing the input data are finished.
    ie, provide the method `event.set`.
    """
    raise NotImplementedError("Not done yet")
  
    # coords = (scale * np.array([left*x_scale, right*y_scale]).T).astype(int)
    # if lock is not None:
    #     lock()
    # turtle.goto(*coords[0])
    # # turtle.down()
    # for c in coords[1:]:
    #     turtle.goto(*c)
    #     turtle.dot(4)
    # return coords[-1]