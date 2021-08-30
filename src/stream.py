class Stream:
    """ Base stream class. If more streams are ever going to be made,
    they should inherit this one and at least implement these methods."""
    def __init__(self, bitrate=44100) -> None:
        self.bitrate = bitrate
    def read(self, chunk_size): pass
    def can_pause(self): return True 
    def pause(self): pass 
    def play(self): pass 
    def sync_playback(self): pass 
    def seek(self, time_in_seconds): pass 
    def rseek(self, seek): 
        """ Relative seek, a value of -5 would jump back 5 seconds, 
        a value of +3 would jump forward 3 seconds. 
        """
        pass 
    def stop(self): pass
        