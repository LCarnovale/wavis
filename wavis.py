from bindings import bind_keys
import sys
import time
import tkinter as tk
from threading import Event, Thread

import numpy as np

import draw_funcs as df
from file_stream import FileStream
import helpers
from helpers import *
from live_stream import LiveStream

if len(sys.argv) > 1:
    audio_file = sys.argv[1]
else:
    audio_file = None
    
RUNNING = False
helpers.STEREO_MODE = False
SAFE_EXIT = False

def setup():
    """ Initialises front end and returns a handle for the canvas.
    """
    master = tk.Tk()
    master.configure(background="black")
    width, height = 500, 500
    canvas = tk.Canvas(master, width=width, height=height)
    canvas.configure(bg="black")
    canvas.pack(fill='both', expand=True)
    
    return canvas

def safe_exit():
    global SAFE_EXIT
    SAFE_EXIT = True
    helpers._end_wait()


def _print_times():
    # Note: All these timer objects are defined in helpers.py
    a = draw_times.get_avg() * 1e3
    b = read_times.get_avg() * 1e3
    c = wait_for_draw_times.get_avg() * 1e3
    d = wait_for_read_times.get_avg() * 1e3

    print(f"Draw/Read/Wait Draw/Wait Read (ms): {a:.1f} / {b:.1f} / {c:.1f} / {d:.1f} | " \
          f"Bytes/read: {int(rt.bits_per_read)} | mrad/byte: {1e3*vt.rads_p_b:.2f} | " \
          f"Circles/read: {int((rt.bits_per_read*vt.rads_p_b)*100/(2*np.pi))}%           ", end='\r')

    ## Could use something like this to have a nicer console output:
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



if __name__ == "__main__":
    read_portion = 1.0 # Amount of full circle to read each tick
    angular_speed_rev_ps = 20 # Revolutions per second

    # Do some maths to set the bit read rate and angular speed
    # to fulfil the above two parameters
    bitrate = 44100
    angular_speed_rad_ps = 2*np.pi*angular_speed_rev_ps
    rads_per_bit = angular_speed_rad_ps / bitrate
    bits_per_read = int(2*np.pi*read_portion // rads_per_bit)

    dont_even_bother = False
    try:
        if audio_file is None:
            the_stream = LiveStream(chunk_size=bits_per_read, requested_channels=1,)
        else:
            the_stream = FileStream(audio_file, realtime=True)
    except Exception as e:
        print("Can't open audio file "f"{audio_file}.")
        print("Error:", e)
        kill_all() # From helpers.py
        # Don't even bother trying to start the rest of the program
        dont_even_bother = True

    # Setup some things
    if not dont_even_bother:
        try:
            canvas = setup()
            # Default circle parameters
            radius, amp, scale = 300, 20, 0.007
            vt = VisThread(canvas, angular_speed_rad_ps, rads_per_bit, radius, amp, scale)
            rt = ReadThread(bits_per_read, the_stream)

            bind_keys(canvas.master, vt, rt, df, the_stream, safe_exit)
        except Exception as e:
            print("Setup failed.")# Error: %s" % e)
            raise e
        else:
            helpers.RUNNING = True

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
            print("Ending threads...")
            kill_all() # From helpers.py
            tick_thr.stop()
            print()
            try:
                canvas.master.destroy() 
            except:
                # The user probably clicked the X button on the window.
                pass

        print("Average time for draw:         " f"{draw_times.get_avg()*1e3:.3f} ms") 
        print("Average time for read:         " f"{read_times.get_avg()*1e3:.3f} ms") 
        print("Average time waiting for draw: " f"{wait_for_draw_times.get_avg()*1e3:.3f} ms")
        print("Average time waiting for read: " f"{wait_for_read_times.get_avg()*1e3:.3f} ms")

if not SAFE_EXIT:
    time.sleep(1.2) # Wait for threads to finish printing stuff
    print("")
    print("") # One more for good measure
    input("Enter to close")
else:
    print()
