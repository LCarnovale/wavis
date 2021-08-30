from tkinter import Tk
from types import ModuleType
from typing import Callable
from .threads import ReadThread, VisThread
from .stream import Stream

_border = 0
_keep_on_top = False
def bind_keys(root : Tk, vis_thread: VisThread, read_thread: ReadThread, draw_func_module: ModuleType,
        stream: Stream, exit_func: Callable):
    vt = vis_thread
    rt = read_thread
    df = draw_func_module
    the_stream = stream
    def toggle_border(*args):
        global _border
        _border = 0 if _border else 1
        root.overrideredirect(_border)
    def toggle_keep_on_top(*args):
        global _keep_on_top
        _keep_on_top = False if _keep_on_top else True
        root.attributes('-topmost', _keep_on_top)
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
        df.x_scale *= 1.05
    def down_x_scale(*args):
        df.x_scale /= 1.05
    def up_y_scale(*args):
        df.y_scale *= 1.05
    def down_y_scale(*args):
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
    root.bind("<Key-b>", toggle_border)
    root.bind("<Key-t>", toggle_keep_on_top)

            