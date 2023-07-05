
import tkinter as tk

import numpy as np

# import matplotlib.pyplot as plt

_n_ham = 0.02 # Portion of signal to clamp with a Hamming filter
# ham_window[0] = 0
_last_tags = [None, None] # [previous, before the previous]
up_sample_factor = 1
_last_signal = []
def draw_circle(canvas: tk.Canvas, data, angle=2*np.pi, start=0, radius=200, 
        amp=20,scale=False, lock=None, fill="red", x_scale=1, y_scale=1,
        tension=0.8, thickness=1,
        stereo_mode:str="mono"):
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
    global _last_tags
    global _last_signal
    sc_width = canvas.winfo_width()
    sc_height = canvas.winfo_height()
    
    if len(data) <= 2 and stereo_mode == "mono":
        # Be prepared for data being either just the mono array or [the mono array, and maybe a misplaced other channel]
        data = data[0]
        n_points = len(data)
    else:
        if len(data) != 2:
            raise ValueError("Data should be a length 2 list of arrays.")
        n_points = len(data[0])
    n_ham = int(_n_ham * n_points)
    arange = np.arange(n_points)
    new_range = np.linspace(0, arange[-1], n_points*up_sample_factor)
    if stereo_mode in ("split", "combine"):
        data_left = np.interp(new_range, arange, data[0])
        data_right = np.interp(new_range, arange, data[1])
    elif stereo_mode == "mono":
        data = np.interp(new_range, arange, data)
    else:
        raise ValueError('Invalid option %s for stereo_mode, must be `mono`, `combine` or `split`.' % stereo_mode)

    if lock is not None:
        lock()
    
    if stereo_mode != "mono":
        power_left = np.fft.fft(data_left)
        power_right = np.fft.fft(data_right)
        left_mod = np.conj(power_left)*power_left
        right_mod = np.conj(power_right)*power_right
        if stereo_mode == "combine":
            mod = np.sqrt(left_mod + right_mod)
        elif stereo_mode == "split":
            left_mod = np.sqrt(left_mod)
            right_mod = np.sqrt(right_mod)
    else:
        power = np.fft.fft(data)
        mod = np.sqrt(np.conj(power)*power)
    
    # if stereo_mode != "split":
    #     freqs = np.fft.fftfreq(len(mod), 1/44100 / up_sample_factor)
    #     mask = (freqs > 300) & (freqs < 7000)
    #     mod[~mask] = 0

    if stereo_mode in ("mono", "combine"):
        n = len(mod)
        data = np.fft.ifft(mod)
    elif stereo_mode == "split":
        data_left = np.fft.ifft(left_mod)
        data_right = np.fft.ifft(right_mod)
        mid = len(data_left) // 2
        data_right[mid:] = data_left[mid:]
        data = data_right

    new_selection = np.linspace(
        n_ham*up_sample_factor, 
        (n_points - n_ham)*up_sample_factor, 
        n_points, dtype=int
    )
    data = data[new_selection]

    # Apply tension to signal
    n = len(data)
    arange = np.arange(n)

    if len(_last_signal) == n:
        shift = lambda x : (arange + x) % n
        diff = _last_signal[shift(-1)] - data + \
               _last_signal[shift(+1)] - data + \
               _last_signal - data
        data += (tension/3) * diff
    _last_signal = data 

    angles = np.linspace(start, start+angle, n_points)
    if scale == False:
        data_max = max(abs(data))
        if data_max != 0:
            radii = data/data_max
        else:
            radii = data
    else:
        radii = amp * scale * data

    radii += radius
    radii = np.real(radii)
    x_pos = x_scale * (radii * np.cos(angles)).astype(int) + sc_width // 2
    y_pos = y_scale * (radii * np.sin(angles)).astype(int) + sc_height // 2
    line_coords = np.array([x_pos, y_pos]).T

    if _last_tags[1]:
        # Remove old line from screen
        canvas.delete(_last_tags[1])

    # This could be used to let lines fade out as a different colour etc.
    # if _last_tags[0]:
    #     canvas.itemconfig(_last_tags[0], fill="dark red")
    tags = canvas.create_line(*line_coords.flatten(), fill=fill, width=thickness)

    _last_tags[1] = tags
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
