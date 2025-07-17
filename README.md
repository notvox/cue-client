# cue-client
(noun) : something clever never

### what is this?
this is a little tool that started as a way to troll people who were being nosy about my listening habits.  
Now I use it as a cli spoitfy controller so I don't have to break my workflow for switching up tracks, managing a queue, searching, etc.  

```
Usage: notvox [OPTIONS] COMMAND [ARGS]...

  NotVox - Network Spotify Control System

  Control Spotify playback over the network with timed sessions.

  Common commands:

    notvox cue "song name" 2h      Play a song for 2 hours
    notvox queue add "song" 30m    Add to playback queue
    notvox status                   Check what's currently playing
    notvox skip                     Skip to next in queue
    notvox stop                     Stop current playback

  Duration formats: 30m, 2h, 1d, 90s

  Use 'notvox COMMAND --help' for more information on a command.

Options:
  --version   Show the version and exit.
  -h, --help  Show this message and exit.

Commands:
  config   Configure NotVox client settings
  cue      Play a track for specified duration
  extend   Extend or reduce current playback session
  health   Check server health and connection
  history  Show playback history
  lucky    Play a random track based on your taste
  queue    Manage playback queue
  quietly  Run commands with minimal output
  resume   Resume a previously stopped session
  search   Search for tracks without playing
  skip     Skip to next track in queue
  status   Show current playback status
  stop     Stop current playback immediately
```