from live_stream import LiveStream

import time
import turtle
import tkinter as tk
from threading import Thread, Event
import sys

# import matplotlib.pyplot as plt
import numpy as np

from stream import Stream
from file_stream import FileStream

from helpers import TimerThread, TickThread

if len(sys.argv) > 1:
    audio_file = sys.argv[1]
else:
    audio_file = None
RUNNING = False
def _wait_func(sleep_t: float, wait=True):
    """sleep for `sleep_t` seconds. if `wait=True` (default) then 
    while RUNNING, the global
    variable `RUNNING` will be `True`. """
    global RUNNING
    
    if wait: RUNNING = True
    time.sleep(sleep_t)
    if wait: RUNNING = False

def wait_thread(sleep_t: float, start=True, wait=True):
    """ Creates a thread that simply sleeps for the given time,
    `.join()` it if you wish to wait with it.
    
    If `start=True` (default) the thread will be started just before
    being returned to the caller, otherwise it will not be started.
    
    If `wait=True` (default) the thread will set the global variable
    `RUNNING` to `True` upon starting, and `False` after the waiting 
    period is finished."""
    t = Thread(None, target=_wait_func, args=(sleep_t,wait))
    
    if start:
        t.start()
    return t
    

def setup():
    """ Returns a handle for the window.
    """
    
    # root = tk.Tk()
    # root.attributes('alpha', 0.0)
    # root.iconify()
    
    # canvas = tk.Canvas(root, bg="black", height=300, width=300)
    # tk_window = tk.Toplevel(root)
    # tk_window.overrideredirect(1)
    # window = turtle.TurtleScreen(canvas)
    window = turtle.Screen()
    # turtle.hideturtle()
    # t1 = turtle.getturtle()
    # t1 = window.turtles()[0]
    # t1.hideturtle()
    window.setup(width = 0.5, height = .5)
    window.bgcolor([0, 0, 0])
    window.tracer(0, 0)             # Makes the turtle's speed instantaneous
    # I tried to implement some tkinter stuff in this 
    # function to hide the window border. It didn't work, 
    # but figured I'd leave the ability to pass different turtle 
    # objects through. This still has the original behaviour.
    return window, turtle


x_scale = 1
y_scale = 1
def draw_circle(data,angle=2*np.pi, start=0, radius=200, 
        amp=20,scale=False, lock=None):
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
    """
    angles = np.linspace(start, start+angle, len(data))
    data_max = max(abs(data))
    if scale == False:
        radii = amp * data/data_max
    else:
        radii = (scale * data)
    if lock is not None:
        lock()
    radii += radius
    x_pos = x_scale * (radii * np.cos(angles)).astype(int)
    y_pos = y_scale * (radii * np.sin(angles)).astype(int)
    coords = np.array([x_pos, y_pos]).T
    # turtle.up()
    turtle.pencolor("red")
    turtle.goto(*coords[0])
    turtle.down()
    for c in coords[1:]:
        turtle.goto(*c)
    return angles[-1]



t_avgs = 10
draw_times = TimerThread(t_avgs, name="draw_times")
draw_times.start()
read_times = TimerThread(t_avgs, name="read_times")
read_times.start()
wait_for_draw_times = TimerThread(t_avgs, name="wait_for_draw_times")
wait_for_draw_times.start()
wait_for_read_times = TimerThread(t_avgs, name="wait_for_read_times")
wait_for_read_times.start()

def _print_times():
    a = draw_times.get_avg() * 1e3
    b = read_times.get_avg() * 1e3
    c = wait_for_draw_times.get_avg() * 1e3
    d = wait_for_read_times.get_avg() * 1e3

    print(f"Draw/Read/Wait for Draw/Wait for Read (ms): {a:.1f} / {b:.1f} / {c:.1f} / {d:.1f} | " \
          f"Bytes/read: {int(rt.bits_per_read)} | mrad/byte: {1e3*vt.rads_p_b:.2f} | " \
          f"Circles/read: {int((rt.bits_per_read*vt.rads_p_b)*100/(2*np.pi))}%           ", end='\c\r')

    ## Could use something like this:
    # from ctypes import *
 
    # STD_OUTPUT_HANDLE = -11
    
    # class COORD(Structure):
    #     pass
    
    # COORD._fields_ = [("X", c_short), ("Y", c_short)]
    
    # def print_at(r, c, s):
    #     h = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    #     windll.kernel32.SetConsoleCursorPosition(h, COORD(c, r))
    
    #     c = s.encode("windows-1252")
    #     windll.kernel32.WriteConsoleA(h, c_char_p(c), len(c), None, None)
    
    # print_at(6, 3, "Hello") 
    
tick_thr = TickThread(1, _print_times)

def _end_wait(*args):
    global RUNNING
    RUNNING = False

time_glob = None
audio_glob = None
buffer_fill_event = Event()
draw_finish_event = Event()

class VisThread(Thread):
    def __init__(self, rads_p_s, rads_p_b, radius, 
            amp, scale, *args, **kwargs):
        super(VisThread, self).__init__(*args, group=None, **kwargs)
        self.rads_p_s = rads_p_s 
        self.rads_p_b = rads_p_b 
        self.radius = radius
        self.amp = amp
        self.scale = scale
        
    def set_rads_p_s(self, val):
        self.rads_p_s = val

    def set_rads_p_b(self, val):
        self.rads_p_b = val

    def run(self):
        angle_end = 0
        while RUNNING:
            wait_for_read_times.t_start()
            # Wait for buffers to be written too
            buffer_fill_event.wait()
            wait_for_read_times.t_stop()

            draw_times.t_start()
            draw_finish_event.clear()
            try:
                # Drawing thread is now in the process of drawing
                turtle.clear()
                turtle.up()
                t_start = time_glob[0]
                angle_start = self.rads_p_s * t_start
                angle_end = draw_circle(audio_glob, angle=self.rads_p_b*len(audio_glob),
                            start=angle_start, radius=self.radius, 
                            amp=self.amp, scale=self.scale, lock=draw_finish_event.set)
                # The above method will call draw_finish_event.set() when it is done with 
                # references to the buffers. The reader thread can then immediately 
                # start filling the buffers for the next draw call
                turtle.update()
            except:
                # The turtle window has probably been manually closed
                # without use of the Escape key.
                _end_wait()
                # Set the draw finish event so that the Reader thread doesn't hang
                draw_finish_event.set()
                break  
            finally:
                draw_times.t_stop()
        draw_finish_event.set()
    
        

class ReadThread(Thread):
    def __init__(self, bits_per_read, stream, *args, **kwargs):#group: None, target: Callable[..., Any] | None, name: str | None, args: Iterable[Any], kwargs: Mapping[str, Any] | None, *, daemon: bool | None) -> None:
        super().__init__(*args, group=None, **kwargs)#group=group, target=target, name=name, args=args, kwargs=kwargs, daemon=daemon)
        self.bits_per_read = bits_per_read
        self.stream = stream
    
    def run(self):
        global time_glob
        global audio_glob
        while RUNNING:
            buffer_fill_event.clear()
            # Buffer is saying it is now 
            # in the process of being filled
            read_times.t_start()
            
            time, audio = self.stream.read(int(self.bits_per_read))
            
            read_times.t_stop()
            if len(time) == 0:
                print("\nStream ended.")
                # The sound has run out.
                _end_wait()
                break

            wait_for_draw_times.t_start()
            # We now wait for the drawing thread to take the data before we can fill
            # the global buffers with new data.
            draw_finish_event.wait()
            wait_for_draw_times.t_stop()
            time_glob = time
            audio_glob = audio

            buffer_fill_event.set()


        buffer_fill_event.set()
        self.stream.stop()
    
        

def bind_keys(_turtle=turtle):
    def up_scale():
        vt.scale *= 1.05
    def down_scale():
        vt.scale /= 1.05
    def up_rps():
        rt.bits_per_read *= 1.05
    def down_rps():
        rt.bits_per_read /= 1.05
    def up_rpb():
        vt.rads_p_b *= 1.05
    def down_rpb():
        vt.rads_p_b /= 1.05
    def up_x_scale():
        global x_scale
        x_scale *= 1.05
    def down_x_scale():
        global x_scale
        x_scale /= 1.05
    def up_y_scale():
        global y_scale
        y_scale *= 1.05
    def down_y_scale():
        global y_scale
        y_scale /= 1.05
    def pause():
        if not ts.can_pause():
            print("Can't pause this stream.")
            return
        if ts.playback.paused:
            ts.play()
        else:
            ts.pause()
    def stop():
        global RUNNING
        RUNNING = False
    def sync():
        ts.sync_playback()
    def seek_back():
        ts.rseek(-5)
    def seek_forward():
        ts.rseek(5)
    
    _turtle.onkey(up_scale, "Up")
    _turtle.onkey(down_scale, "Down")
    _turtle.onkey(up_rps, ".")
    _turtle.onkey(down_rps, ",")
    _turtle.onkey(up_rpb, "'")
    _turtle.onkey(down_rpb, ";")
    _turtle.onkey(up_x_scale,"l")
    _turtle.onkey(down_x_scale,"j")
    _turtle.onkey(up_y_scale, "i")
    _turtle.onkey(down_y_scale, "k")
    _turtle.onkey(stop, "Escape")
    _turtle.onkey(pause, "space")
    _turtle.onkey(sync, "s")
    _turtle.onkey(seek_back, "Left")
    _turtle.onkey(seek_forward, "Right")
            

if __name__ == "__main__":
    read_portion = 1.1 # Amount of full circle to read each tick
    angular_speed_rev_ps = 20 # Revolutions per second

    # Do some maths to set the bit read rate and angular speed
    # to fulfil the above two parameters
    bitrate = 44100
    angular_speed_rad_ps = 2*np.pi*angular_speed_rev_ps
    rads_per_bit = angular_speed_rad_ps / bitrate
    bits_per_read = int(2*np.pi*read_portion // rads_per_bit)

    try:
        if audio_file is None:
            ts = LiveStream(chunk_size=bits_per_read)
        else:
            ts = FileStream(audio_file, realtime=True)
    except Exception as e:
        print("Can't open audio file "f"{audio_file}.")
        print("Error:", e)
        draw_times.kill()
        read_times.kill()
        wait_for_draw_times.kill()
        wait_for_read_times.kill()
        exit()

    # Setup some things
    try:
        window, _turtle = setup()
        bind_keys(_turtle)
        _turtle.listen()
    except Exception as e:
        print("Setup failed.")# Error: %s" % e)
        raise e
    else:
        RUNNING = True

        # Default circle parameters
        radius, amp, scale = 300, 20, 0.007
        vt = VisThread(angular_speed_rad_ps, rads_per_bit, radius, amp, scale)
        rt = ReadThread(bits_per_read, ts)
        # Buffer needs to fill first, act as if we begin waiting
        # for buffer after a draw has finished 
        buffer_fill_event.clear()
        draw_finish_event.set()

        # Start the timer printing thread
        tick_thr.start()
        rt.start()
        vt.run() # Turtle can't be used in any non-main thread >:(
        # Both threads will run indefinitely until RUNNING is set to False
    finally:
        # In case no thread was able to do this already
        RUNNING = False
        # At this point the user has stopped the program and now we are
        # wrapping things up, kill the timer threads (but also keep them alive
        # to reference them) 
        draw_times.kill()
        read_times.kill()
        wait_for_draw_times.kill()
        wait_for_read_times.kill()
        tick_thr.stop()
        print()
        print("Ending threads...")

    print("Average time for draw:         " f"{draw_times.get_avg()*1e3:.3f} ms") 
    print("Average time for read:         " f"{read_times.get_avg()*1e3:.3f} ms") 
    print("Average time waiting for draw: " f"{wait_for_draw_times.get_avg()*1e3:.3f} ms")
    print("Average time waiting for read: " f"{wait_for_read_times.get_avg()*1e3:.3f} ms")

