# ring_automation

I got fed up with how sensitive the PIR sensor is that controls the lights on my Ring Floodlight, so I wrote this to control the lights using the motion detection on the camera instead.

It's not perfect; it can be quite slow to react, but I blame the Ring API for that.

Thanks to https://github.com/tchellomello for https://github.com/python-ring-doorbell/ which this little project relies upon.


_PS a note for future Tom, or anyone who's using macOS and stumbles across this, remember to run python's `Install Certificates.command` before running this_