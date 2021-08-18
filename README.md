A simple multithreaded sound visualiser written in Python using Turtle. All it really 
does is wrap the waveform around a circle, but I reckon it looks pretty good.

The only dependency is for playback, [just_playback](https://github.com/cheofusi/just_playback). It itself has no other dependencies, and can be pip'd:

    pip install just_playback

Usage:
```
python wavis.py "A song.wav"
```
Once started, playback should also begin. Sometimes there is a slight delay in the playback which offsets it from the visualiser, press `s` to resynchronise them.

Keyboard controls:

| Key | Function|
|-----|---------|
| <kbd>&#8592;</kbd>/<kbd>&#8594;</kbd> | Jump backward/forward 5 seconds in playback |
|<kbd>s</kbd> | Resynchronise playback to match visualisation |
| <kbd>space</kbd> | Pause/resume (Note for some reason playback will resume from the beginning, you can bring it back with `s`.) |
| <kbd>&#8593;</kbd>/<kbd>&#8595;</kbd> | Increase / Decrease the amplitude of the waveform |
| <kbd>j</kbd>/<kbd>l</kbd> | Decrease/Increase horizontal scale |
| <kbd>k</kbd>/<kbd>i</kbd> | Decrease/Increase vertical scale |
| <kbd>,</kbd>/<kbd>.</kbd> | Decrease/Increase number of sound bytes read in each tick (ie the chunk size) |
| <kbd>;</kbd>/<kbd>'</kbd> | Decrease/Increase the angular spread between each sound byte. Effectively spreads each arc over smaller/larger angle. |
| <kbd>Esc</kbd> | Stop |

When finishing the program will display the average time of reading, drawing
and the time those two threads spent waiting for the other. If you get low
framerates, you can usually speed it up by decreasing the number of bytes read in each tick (<kbd>,</kbd>), and if that ends up looking too jagged on the front you can try stretch out the arcs with <kbd>'</kbd>.