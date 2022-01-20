#!/usr/bin/env python3
import pyvisa as visa

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

scope.write('*rst') # reset

# Check for any errors after reset
#print("Error check:",scope.query(":SYSTem:ERRor?"))

# Set it running
scope.write(":RUN")

# Set channel, trigger, etc to be back to what we currently have them set at in the lab.
scope.write(":TRIG:SWEEP NORM") 
scope.write(":TRIG:MODE EDGE") 
scope.write(":TRIG:EDG:SOUR CHAN1")
scope.write(":TRIG:EDG:SLOP NEG") # trigge on the falling edge
# Sets trigger level. For this you need to know your vertical scale!!
# Read the manual and try a few options.
scope.write(":TRIG:EDG:LEV -15.0") # 1 volt

# Wave stuff
scope.write(":WAV:SOUR CHAN1")
scope.write(":WAV:FORM BYTE") # Other: ascii and raw
scope.write(":WAV:MODE RAW")

# Sizes
scope.write(":TIM:OFFS 0")
scope.write(":TIM:SCAL 0.00002")
scope.write(":CHAN1:SCAL 50.")
scope.write(":CHAN1:OFFS 0.")

# Try to set mdepth to be not insane
scope.write(":ACQ:MDEP 12000")

# Release scope for next call
rm.close()
scope.close()
