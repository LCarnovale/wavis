from tkinter import Tk
from types import ModuleType
from typing import Callable
from helpers import ReadThread, VisThread
from stream import Stream

def bind_keys(root : Tk, vis_thread : VisThread, read_thread : ReadThread, draw_func_module : ModuleType,
        stream : Stream, exit_func : Callable):
    vt = vis_thread
    rt = read_thread
    df = draw_func_module
    the_stream = stream
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
        if not the_stream.can_pause():
            print("Can't pause this stream.")
            return
        if the_stream.playback.paused:
            the_stream.play()
        else:
            the_stream.pause()
    def stop(*args):
        exit_func()
    def sync(*args):
        the_stream.sync_playback()
    def seek_back(*args):
        the_stream.rseek(-5)
    def seek_forward(*args):
        the_stream.rseek(5)
    
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
            