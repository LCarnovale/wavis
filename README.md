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
| Left/Right Arrows | Jump backward/forward 5 seconds in playback |
|`s` | Resynchronise playback to match visualisation |
| Space | Pause/resume (Note for some reason playback will resume from the beginning, you can bring it back with `s`.) |
| Up/Down Arrows | Increase / Decrease the amplitude of the waveform |
| `j`/`l` | Decrease/Increase horizontal scale |
| `k`/`i` | Decrease/Increase vertical scale |
| `,`/`.` | Decrease/Increase number of sound bytes read in each tick (ie the chunk size) |
| `;`/`'` | Decrease/Increase the angular spread between each sound byte. Effectively spreads each arc over smaller/larger angle. |
| Escape | Stop |

When finishing the program will display the average time of reading, drawing
and the time those two threads spent waiting for the other. If you get low
framerates, you can usually speed it up by decreasing the number of bytes read in each tick (press `,`), and if that ends up looking to jagged on the front you can try stretch out the arcs with '`'`'.