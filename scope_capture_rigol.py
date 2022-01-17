import numpy as np
import sys
import pyvisa as visa
from matplotlib import pyplot as plt
import time

# This is the channel we'll fetch the trace from.
channel = "CHAN1"

# Based on examples in e.g.
# https://gist.github.com/prhuft/8d961e2983bfdf8fdf1effcc1aae61a9
# https://gist.github.com/pklaus/7e4cbac1009b668eafab
# https://www.codeproject.com/Articles/869421/Interfacing-Rigol-Oscilloscopes-with-C 

# Programming guide for this oscilloscope:
# https://beyondmeasure.rigoltech.com/acton/attachment/1579/f-af444326-0551-4fd5-a277-bf8fff6f53cb/1/-/-/-/-/DS1000Z-E_ProgrammingGuide_EN.pdf

# Troubleshooting:
# If you are getting "Data collection failed" errors for all points,
# you may not have a trace on the scope screen at all - i.e. nothing has
# triggered. You can try extending the time that you wait for a trigger, or adjust
# your trigger threshold, or move to trigger mode "AUTO". In AUTO there will always
# be *something* on the screen, it just might not be something useful. 
# Check what the traces look like now and then to make sure they seem sensible.
# If you are just missing pieces of the data or the error seems to be transient,
# try changing the parameter "mdepth" in the script below. This is pretty finicky
# and has to do with the format of the data read out from the scope.

# Since we can only collect a bit of data at a time on these scopes,
# walk through the size of the trace samples and accumulate them here.
def get_data(scope,mdepth) :
    print("About to fetch data...")
    fulldata = []
    points_list = list(range(489, mdepth, 489))
    points_list.append(mdepth)
    for thisindex, endpoint in enumerate(points_list) :
        if thisindex != 0 :
            startpoint = points_list[thisindex-1]+1
        else :
            startpoint = 1
        scope.write(":WAV:STAR {0}".format(startpoint))
        scope.write(":WAV:STOP {0}".format(endpoint)) # 489 is the maximum distance between start and end
        try :
          rawdata = scope.query_binary_values(':WAV:DATA?', datatype = 'I', container = np.array)
        except :
          # fill it with zeros
          print("Data collection failed for points",startpoint,endpoint)
          rawdata = np.zeros(489)
        fulldata = np.append(fulldata,rawdata)
        # NOTE: 
        # After retrieving data, you will get a crash if you
        # attempt to check :WAV:STOP. It is fine before, but
        # broken after. You can still set it but you can't read it.
    # Need to convert to real voltage values.
    # Using the scale info has proven confusing, so we'll actually just take the maximum
    # and minimum in the channel.
    scope.write(":MEAS:SOUR {0}".format(channel))
    vmin = float(scope.query(":MEAS:VMIN?"))
    vmax = float(scope.query(":MEAS:VMAX?"))
    rawmin = np.amin(fulldata)
    rawmax = np.amax(fulldata)
    slope = (vmax - vmin)/(rawmax - rawmin)
    intercept = vmin - slope*rawmin
    normalised_data = fulldata*slope + intercept

    return normalised_data

# Make the pyvisa resource manager
rm = visa.ResourceManager()
# Get the USB device, e.g. 'USB0::0x1AB1::0x0588::DS1ED141904883'
instruments = rm.list_resources()
usb = list(filter(lambda x: 'USB' in x, instruments))
if len(usb) != 1:
    print('Bad instrument list', instruments)
    sys.exit(-1)
print("Will open instrument",usb[0])

scope = rm.open_resource(usb[0], timeout=2000, chunk_size=1024000) # bigger timeout for long mem

# Check initial trigger and aquisition status
print("Aquire type:",scope.query("ACQuire:TYPE?"))
print("Trigger status:",scope.query("trig:status?"))

# Run
scope.write(":RUN")

# Set mem depth.
# Use 12000 for single channel
# and switch to 6000 if you have two channels enabled.
# If you're failing to get data, you can try switching to AUTO
# (the commented out line at the bottom):
# it will be slower to run, but that's life.
#mdepth = 12000
mdepth = 6000
scope.write(":ACQ:MDEP {0}".format(mdepth))
#scope.write(":ACQ:MDEP AUTO")
used_mdepth = scope.query("ACQ:MDEP?")
print("Mem depth:",used_mdepth)

# Let's check the mode of your axes. 
# You probably want MAIN here.
print("Time axis mode:",scope.query(":TIMebase:MODE?"))

# Let's set the x axis scale.
# By trial and error, this looks pretty nice.
scope.write(":TIM:SCAL 0.00002") 

# Set your trigger and let's turn it on.
# Your options are AUTO, NORM, and SING
# You probably want NORM for physics
# AUTO just makes sure something is happening so you can test this
scope.write(":TRIG:SWEEP NORM") 
print("Trigger sweep:",scope.query(":TRIG:SWEEP?"))
# Mode is where/what we trigger on.
# Lots of options, see programming guide pg 2-125
scope.write(":TRIG:MODE EDGE") 
# For an edge trigger, we can set additional properties:
scope.write(":TRIG:EDG:SOUR {0}".format(channel)) # trigger on channel 1
scope.write(":TRIG:EDG:SLOP POS") # trigge on the rising edge
# Sets trigger level. For this you need to know your vertical scale!!
# Read the manual and try a few options.
scope.write(":TRIG:EDG:LEV 0.5.") # 1 volt
print("Trigger mode:",scope.query(":TRIG:MODE?"))
print("Trigger status:",scope.query("trig:status?"))

# Wait a second to make sure we trigger
time.sleep(3)
# Grab the raw data from channel 1
scope.write(":STOP")

# Get the timescale.
# This is in seconds per division.
timescale = float(scope.query(":TIM:SCAL?"))

# Get the timescale offset
timeoffset = float(scope.query(":TIM:OFFS?"))

# Get the y axis range (volts) of channel 1
# Scale is # of volts per division, and there are 8 divisions on the screen.
voltscale = float(scope.query(':{0}:SCAL?'.format(channel)))
# And the voltage offset
voltoffset = float(scope.query(":{0}:OFFS?".format(channel)))

# Check the sample rate
sample_rate = scope.query(':ACQ:SRAT?')
print("Sample rate:", sample_rate)

# Note: not :WAV:POIN:MODE, which is for other DS1000-series Rigol scopes
# Byte return format is a value between 0 and 255
scope.write(":WAV:SOUR {0}".format(channel))
scope.write(":WAV:FORM BYTE") # Other: ascii and raw
scope.write(":WAV:MODE RAW") # NORM instead of RAW, which takes the whole buffer?

# Make sure things are what we want them to be.
print("Check some values.")
print("timescale:",timescale)
print("timeoffset:",timeoffset)
print("voltscale:",voltscale)
print("voltoffset",voltoffset)
print("Wave form:",scope.query(":WAV:FORM?"))
print("Mode:",scope.query("WAV:MODE?"))

# Get the trace
mdepth = int(float(sample_rate)*timescale*12.) # This is the true mdepth, regardless of what we set
print("Using mdepth",mdepth)
tracedata = get_data(scope,mdepth)
print(tracedata)
print(np.size(tracedata))

# Now we need to do some parsing to understand it, using the 
# scale info we collected before.

# We know the time increment between all our measurements and the offset of the first value,
# so we can make a time axis for our data.
time_axis = np.linspace(timeoffset - 6 * timescale, timeoffset + 6 * timescale, num=len(tracedata))

# Quick plot of data
plt.plot(time_axis,tracedata)
plt.xlabel('Time [s]')
plt.ylabel('Amplitude [V]')
plt.savefig('trace_data.png')
# If you want to clear plot, do this
# But we want to add a second trace
# plt.clf()

# Let's get a second one
scope.write(":RUN")
time.sleep(3)
scope.write(":STOP")
newdata = get_data(scope,mdepth)
# Add it to the plot ...
plt.plot(time_axis,newdata)
plt.savefig('two_traces.png')

#############################
# More useful commands

# Reset the scope
#scope.write('*rst') # reset

# Check if there is an error on the scope
#print("Error check:",scope.query(":SYSTem:ERRor?"))

# Release scope for next call
rm.close()
scope.close()