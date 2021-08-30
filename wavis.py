import sys
import time
import tkinter as tk
from threading import Event, Thread

import numpy as np

import argparse

parser = argparse.ArgumentParser("Run a realtime audio visualiser.")
parser.add_argument("-i", "--index", action="store", dest="index", default=-1, type=int,
    help="Audio device index. If you're not sure what it is, leave it blank. " \
         "If provided, then this index will be used instead of the program prompting the " \
         "user to provide one.")
parser.add_argument("-f", "--file", action="store", dest="file", default=None, type=str,
    help="An audio file can be supplied, if it is then it will be visualised, and when the " \
         "file ends the program will end too.")
parser.add_argument("-s", "--stereo", default="mono", dest="stereo_mode",
    choices=["mono", "split", "combine"])

args = parser.parse_args()
index_choice = args.index
audio_file = args.file



def setup():
    """ Initialises front end and returns a handle for the canvas.
    """
    master = tk.Tk()
    master.configure(background="black")
    width, height = 1000, 1000
    canvas = tk.Canvas(master, width=width, height=height)
    canvas.configure(bg="black")
    canvas.pack(fill='both', expand=True)
    
    return canvas




def safe_exit():
    global SAFE_EXIT
    SAFE_EXIT = True
    threads._end_wait()


# def _print_times():
#     # Note: All these timer objects are defined in threads.py
#     a = threads.audio_globdraw_times.get_avg() * 1e3
#     b = threads.read_times.get_avg() * 1e3
#     c = threads.wait_for_draw_times.get_avg() * 1e3
#     d = threads.wait_for_read_times.get_avg() * 1e3

#     print(f"Draw/Read/Wait Draw/Wait Read (ms): {a:.1f} / {b:.1f} / {c:.1f} / {d:.1f} | " \
#           f"Bytes/read: {int(rt.bits_per_read)} | mrad/byte: {1e3*vt.rads_p_b:.2f} | " \
#           f"Circles/read: {int((rt.bits_per_read*vt.rads_p_b)*100/(2*np.pi))}%  ", end='\r')



if __name__ == "__main__":
    # Import these last. These imports will start threads that need to 
    # be stopped with src.threads.kill_all() before ending the program.  
    from src.bindings import bind_keys
    import src.draw_funcs as df
    from src.file_stream import FileStream
    import src.threads as threads
    from src.live_stream import LiveStream


    threads.STEREO_MODE = args.stereo_mode

    # If the program stops unexpectedly, it will keep the console open
    # so that errors can be seen. If the user intentionally ends the program,
    # set this to True before ending this program.
    SAFE_EXIT = False
    # With lots of threads running we need to keep track of all of them 
    # and if the main one crashes, don't let the program hang waiting for
    # the others.  

    # If we get to this point, we at least know the imports worked,
    # so no need to try-except these lines.
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
            the_stream = LiveStream(chunk_size=bits_per_read, requested_channels=2,
                device_index=index_choice)
        else:
            the_stream = FileStream(audio_file, realtime=True)
    except Exception as e:
        print("Can't open audio file "f"{audio_file}.")
        print("Error:", e)
        threads.kill_all() 
        # Don't even bother trying to start the rest of the program
        try:
            the_stream.close()
        except:
            pass
        dont_even_bother = True

    # Setup some things
    if not dont_even_bother:
        try:
            # tick_thr = threads.TickThread(1, _print_times) # This will be killed by kill_all()
            canvas = setup()
            # Default circle parameters
            radius, amp, scale = 300, 20, 0.007
            vt = threads.VisThread(canvas, angular_speed_rad_ps, rads_per_bit, radius, amp, scale)
            rt = threads.ReadThread(bits_per_read, the_stream)

            bind_keys(canvas.master, vt, rt, df, the_stream, safe_exit)
            # These two are new but could be moved into the bind_keys function
        except Exception as e:
            print("Setup failed.")# Error: %s" % e)
            raise e
        else:
            threads.RUNNING = True

            # Start the timer printing thread
            # tick_thr.start()
            rt.start()
            vt.run() # UI can't be used in any non-main thread >:(
            # Both threads will run indefinitely until RUNNING is set to False
        finally:
            # At this point the user has stopped the program and now we are
            # wrapping things up, kill the timer threads (but also keep them alive
            # to reference them)
            print("Ending threads...")
            threads.kill_all() # From threads.py, kills any instances of TickThread or TimerThread
            print()
            try:
                canvas.master.destroy() 
            except:
                # The user probably clicked the X button on the window.
                pass

        print("Average time for draw:         " f"{vt.draw_times.get_avg()*1e3:.3f} ms") 
        print("Average time for read:         " f"{rt.read_times.get_avg()*1e3:.3f} ms") 
        print("Average time waiting for draw: " f"{rt.wait_for_draw_times.get_avg()*1e3:.3f} ms")
        print("Average time waiting for read: " f"{vt.wait_for_read_times.get_avg()*1e3:.3f} ms")

if not SAFE_EXIT:
    time.sleep(1.2) # Wait for threads to finish printing stuff
    print("")
    print("") # One more for good measure
    input("Enter to close")
else:
    print("")
    print("")
