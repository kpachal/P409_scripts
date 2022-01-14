import numpy as np
import sys
import visa

# Based on examples in e.g.
# https://gist.github.com/prhuft/8d961e2983bfdf8fdf1effcc1aae61a9
# https://gist.github.com/pklaus/7e4cbac1009b668eafab

# Programming guide for this oscilloscope:
# https://beyondmeasure.rigoltech.com/acton/attachment/1579/f-af444326-0551-4fd5-a277-bf8fff6f53cb/1/-/-/-/-/DS1000Z-E_ProgrammingGuide_EN.pdf

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

# Reset the scope, if you want.
#scope.write('*rst') # reset

# Check initial 
print("Aquire type:",scope.query("ACQuire:TYPE?"))
print("Trigger status:",scope.query("trig:status?"))
# Your options are 
scope.write(":TRIG:SWEEP AUTO") 
print("Trigger status:",scope.query("trig:status?"))

# Run
scope.write(":RUN")

# Set mem depth.
# 
scope.write(":ACQ:MDEP {0}".format(mdepth))
print("Mem depth:",scope.query("ACQ:MDEP?"))


# Grab the raw data from channel 1
scope.write(":STOP")

print("Mem depth:",scope.query("ACQ:MDEP?"))

# Get the timescale
timescale = float(scope.query(":TIM:SCAL?"))

# Get the timescale offset
timeoffset = float(scope.query(":TIM:OFFS?")[0])
voltscale = float(scope.query(':CHAN1:SCAL?')[0])

# And the voltage offset
voltoffset = float(scope.query(":CHAN1:OFFS?")[0])

# Note: not :WAV:POIN:MODE, which is for other DS1000-series
# Rigol scopes, but causes errors here
scope.write(":WAV:SOUR CHAN1")
scope.write(":WAV:FORM BYTE") # Had ascii and raw
scope.write(":WAV:MODE RAW") # NORM instead of RAW, which takes the whole buffer?

# Make sure things are what we set them to be
print("Check some values.")
print("timescale:",timescale)
print("timeoffset:",timeoffset)
print("voltscale:",voltscale)
print("voltoffset",voltoffset)
print("Wave form:",scope.query(":WAV:FORM?"))
print("Mode:",scope.query("WAV:MODE?"))

# If you want, use this to check if there is an error on the scope
#print("Error check:",scope.query(":SYSTem:ERRor?"))

# Get the trace
print("About to fetch data...")
rawdata = get_data(scope)
print(rawdata)
print(np.size(rawdata))

# Now we need to do some parsing to understand it, using the 
# scale info we collected before.