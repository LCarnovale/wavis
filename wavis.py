import sys
import time
import tkinter as tk
from threading import Event, Thread

import numpy as np

from draw_funcs import draw_circle, draw_stereo
import draw_funcs as df
from file_stream import FileStream
from helpers import TickThread, TimerThread
from live_stream import LiveStream
from stream import Stream

if len(sys.argv) > 1:
    audio_file = sys.argv[1]
else:
    audio_file = None
    
RUNNING = False
STEREO_MODE = False
SAFE_EXIT = False

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
    """ Returns a handle for the canvas.
    """
    master = tk.Tk()
    master.configure(background="black")
    width, height = 500, 500
    canvas = tk.Canvas(master, width=width, height=height)
    canvas.configure(bg="black")
    canvas.pack(fill='both', expand=True)
    
    return canvas



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
          f"Circles/read: {int((rt.bits_per_read*vt.rads_p_b)*100/(2*np.pi))}%           ", end='\r')

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
            amp, scale, *args, pen_colour="red", **kwargs):
        super(VisThread, self).__init__(*args, group=None, **kwargs)
        self.rads_p_s = rads_p_s 
        self.rads_p_b = rads_p_b 
        self.radius = radius
        self.amp = amp
        self.scale = scale
        self.pen_colour = pen_colour
        
    def set_rads_p_s(self, val):
        self.rads_p_s = val

    def set_rads_p_b(self, val):
        self.rads_p_b = val

    def run(self):
        angle_end = 0
        tags = []
        while RUNNING:
            # This thread usually has some time to kill, so use it to resize 
            # the canvas.
            wait_for_read_times.t_start()
            # Wait for buffers to be written too
            buffer_fill_event.wait()
            wait_for_read_times.t_stop()

            draw_times.t_start()
            draw_finish_event.clear()
            try:
                # Drawing thread is now in the process of drawing
                canvas.delete('all')
                if STEREO_MODE:
                    draw_stereo(*audio_glob, lock=draw_finish_event.set)
                else:
                    t_start = time_glob[0]
                    # angle_start = self.rads_p_s * t_start
                    tags, angle_end = draw_circle(canvas, audio_glob[0], angle=self.rads_p_b*len(audio_glob[0]),
                                start=angle_end, radius=self.radius, 
                                amp=self.amp, scale=self.scale, lock=draw_finish_event.set,
                                fill=self.pen_colour)
                # The above method will call draw_finish_event.set() when it is done with 
                # references to the buffers. The reader thread can then immediately 
                # start filling the buffers for the next draw call
                canvas.master.update()
            except Exception as e:
                # The window has probably been manually closed
                # without use of the Escape key.
                print("Draw failed, error: %s" % e)
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
            if STEREO_MODE:
                time, audio = self.stream.read(int(self.bits_per_read), channels=2)
            else:
                time, audio = self.stream.read(int(self.bits_per_read), channels=1)
            
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
    
        

def bind_keys(root : tk.Tk):
    def up_scale(*args):
        vt.scale *= 1.05
    def down_scale(*args):
        vt.scale /= 1.05
    def up_rps(*args):
        rt.bits_per_read *= 1.05
    def down_rps(*args):
        rt.bits_per_read /= 1.05
    def up_rpb(*args):
        vt.rads_p_b *= 1.05
    def down_rpb(*args):
        vt.rads_p_b /= 1.05
    def up_x_scale(*args):
        # global df.x_scale
        df.x_scale *= 1.05
    def down_x_scale(*args):
        # global df.x_scale
        df.x_scale /= 1.05
    def up_y_scale(*args):
        # global df.y_scale
        df.y_scale *= 1.05
    def down_y_scale(*args):
        # global df.y_scale
        df.y_scale /= 1.05
    def pause(*args):
        if not ts.can_pause():
            print("Can't pause this stream.")
            return
        if ts.playback.paused:
            ts.play()
        else:
            ts.pause()
    def stop(*args):
        global RUNNING
        global SAFE_EXIT
        RUNNING = False
        SAFE_EXIT = True
    def sync(*args):
        ts.sync_playback()
    def seek_back(*args):
        ts.rseek(-5)
    def seek_forward(*args):
        ts.rseek(5)
    
    root.bind("<Key-Up>", up_scale)
    root.bind("<Key-Down>", down_scale)
    root.bind("<Key-.>", up_rps)
    root.bind("<Key-,>", down_rps)
    root.bind("<Key-'>", up_rpb)
    root.bind("<Key-;>", down_rpb)
    root.bind("<Key-l>", up_x_scale)
    root.bind("<Key-j>", down_x_scale)
    root.bind("<Key-i>", up_y_scale)
    root.bind("<Key-k>", down_y_scale)
    root.bind("<Key-Escape>", stop)
    root.bind("<Key-space>", pause)
    root.bind("<Key-s>", sync)
    root.bind("<Key-Left>", seek_back)
    root.bind("<Key-Right>", seek_forward)
            

if __name__ == "__main__":
    read_portion = 1.0 # Amount of full circle to read each tick
    angular_speed_rev_ps = 20 # Revolutions per second

    # Do some maths to set the bit read rate and angular speed
    # to fulfil the above two parameters
    bitrate = 44100
    angular_speed_rad_ps = 2*np.pi*angular_speed_rev_ps
    rads_per_bit = angular_speed_rad_ps / bitrate
    bits_per_read = int(2*np.pi*read_portion // rads_per_bit)

    try:
        if audio_file is None:
            ts = LiveStream(chunk_size=bits_per_read, requested_channels=1)
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
        canvas = setup()
        bind_keys(canvas.master)
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
        vt.run() # UI can't be used in any non-main thread >:(
        # Both threads will run indefinitely until RUNNING is set to False
    finally:
        # In case no thread was able to do this already
        RUNNING = False
        # At this point the user has stopped the program and now we are
        # wrapping things up, kill the timer threads (but also keep them alive
        # to reference them)
        canvas.master.destroy() 
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

if not SAFE_EXIT:
    time.sleep(1) # Wait for threads to finish printing stuff
    print()
    input("Enter to close")
else:
    print()
