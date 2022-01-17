import numpy as np
import sys
import pyvisa as visa
from matplotlib import pyplot as plt

# Based on examples in e.g.
# https://gist.github.com/prhuft/8d961e2983bfdf8fdf1effcc1aae61a9
# https://gist.github.com/pklaus/7e4cbac1009b668eafab
# https://www.codeproject.com/Articles/869421/Interfacing-Rigol-Oscilloscopes-with-C 

# Programming guide for this oscilloscope:
# https://beyondmeasure.rigoltech.com/acton/attachment/1579/f-af444326-0551-4fd5-a277-bf8fff6f53cb/1/-/-/-/-/DS1000Z-E_ProgrammingGuide_EN.pdf

# TODO: check against an actually running scope that the various ranges
# here are correctly interpreted. These are based on best guesses
# from the manual but there are definitely contradictory things online.

# Use 12000 for single channel
# and switch to 6000 if you have two channels enabled.
mdepth = 12000

# Since we can only collect a bit at a time,
def get_data(scope) :
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
        rawdata = scope.query_binary_values(':WAV:DATA?', datatype = 'b', container = np.array)
        fulldata = np.append(fulldata,rawdata)
        # NOTE: 
        # After retrieving data, you will get a crash if you
        # attempt to check :WAV:STOP. It is fine before, but
        # broken after. You can still set it but you can't read it.
    # Need to convert to real values.
    # Taking advice from here, which lists our model as one of the weird ones:
    # https://rigolwfm.readthedocs.io/en/latest/1-DS1000Z-Waveforms.html
    # But major TODO is validate in the lab and see if this matches real scopes.

    return fulldata

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
# It seems like this can only be changed while running, so
# don't move it out of here.
scope.write(":ACQ:MDEP {0}".format(mdepth))
print("Mem depth:",scope.query("ACQ:MDEP?"))

# Let's check the mode of your axes. 
# You probably want MAIN here.
print("Time axis mode:",scope.query(":TIMebase:MODE?"))

# Let's set the x axis scale.
# Picking a fairly long one so we can see what's up.
scope.write(":TIM:SCAL 0.0002")

# Set your trigger and let's turn it on.
# Your options are AUTO, NORM, and SING
# You probably want NORM for physics
# AUTO just makes sure something is happening so you can test this
scope.write(":TRIG:SWEEP AUTO") 
print("Trigger sweep:",scope.query(":TRIG:SWEEP?"))
# Mode is where/what we trigger on.
# Lots of options, see programming guide pg 2-125
scope.write(":TRIG:MODE EDGE") 
# For an edge trigger, we can set additional properties:
scope.write(":TRIG:EDG:SOUR CHAN1") # trigger on channel 1
scope.write(":TRIG:EDG:SLOP POS") # trigge on the rising edge
# Sets trigger level. For this you need to know your vertical scale!!
# Read the manual and try a few options.
scope.write(":TRIG:EDG:LEV 0.5")
print("Trigger mode:",scope.query(":TRIG:MODE?"))
print("Trigger status:",scope.query("trig:status?"))

# Grab the raw data from channel 1
scope.write(":STOP")

# Get the timescale.
# This is in seconds per division.
timescale = float(scope.query(":TIM:SCAL?"))

# Get the timescale offset
timeoffset = float(scope.query(":TIM:OFFS?")[0])

# Get the y axis range (volts) of channel 1
# Scale is # of volts per division, and there are 8 divisions on the screen.
voltscale = float(scope.query(':CHAN1:SCAL?')[0])
# And the voltage offset
voltoffset = float(scope.query(":CHAN1:OFFS?")[0])

# Check the sample rate
sample_rate = scope.query(':ACQ:SRAT?')
print("Sample rate:", sample_rate)

# Note: not :WAV:POIN:MODE, which is for other DS1000-series Rigol scopes
# Byte return format is a value between 0 and 255
scope.write(":WAV:SOUR CHAN1")
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
print("About to fetch data...")
rawdata = get_data(scope)
print(rawdata)
print(np.size(rawdata))

# Now we need to do some parsing to understand it, using the 
# scale info we collected before.

# We know the time increment between all our measurements and the offset of the first value,
# so we can make a time axis for our data.
# TODO: verify if there really are 12 divisions and the offset is the middle. 
time_axis = np.linspace(timeoffset - 6 * timescale, timeoffset + 6 * timescale, num=mdepth)

# Quick plot of raw data
plt.plot(time_axis,rawdata)
plt.xlabel('Time [s]')
plt.ylabel('Amplitude [arbitrary]')
plt.savefig('raw_data.png')
# clear plot so we can use it again
plt.clf()

# The y axis range is NOT CLEAR:
# See issues documeting firmware bugs in DS1000Z series that makes it 
# dubious whether this will work:
# https://rigolwfm.readthedocs.io/en/latest/1-DS1000Z-Waveforms.html
# https://github.com/michal-szkutnik/pyRigolWfm1000Z/issues/3#issue-196373027
# https://github.com/michal-szkutnik/pyRigolWfm1000Z
# Can we check scopes with updated firmware?

# Offset is center of screen, which should be at half of 255 (127.)
# So this *should* be:
voltage_axis = (rawdata-127)*voltscale/255. - voltoffset
# Does data need inverting? Some people seem to think so. 
# https://gist.github.com/pklaus/7e4cbac1009b668eafab)

# And draw this
plt.plot(time_axis,voltage_axis)
plt.xlabel('Time [s]')
plt.ylabel("Amplitude [V]")
plt.savefig('scaled_data.png')

# What if we want to set the trigger? What unit is that in by default?

#############################
# More useful commands

# Reset the scope
#scope.write('*rst') # reset

# Check if there is an error on the scope
#print("Error check:",scope.query(":SYSTem:ERRor?"))

# Release scope for next call
rm.close()
scope.close()