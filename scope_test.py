import numpy
import sys
import visa

# Based on examples in e.g.
# https://gist.github.com/prhuft/8d961e2983bfdf8fdf1effcc1aae61a9
# https://gist.github.com/pklaus/7e4cbac1009b668eafab

rm = visa.ResourceManager()
# Get the USB device, e.g. 'USB0::0x1AB1::0x0588::DS1ED141904883'
instruments = rm.list_resources()
usb = list(filter(lambda x: 'USB' in x, instruments))
if len(usb) != 1:
    print('Bad instrument list', instruments)
    sys.exit(-1)
print("Will open instrument",usb[0])

scope = rm.open_resource(usb[0], timeout=2000, chunk_size=1024000) # bigger timeout for long mem

# Reset the scope, just in case.
scope.write('*rst') # reset

# Grab the raw data from channel 1
scope.write(":STOP")

# Get the timescale
timescale = float(scope.query(":TIM:SCAL?"))

# Get the timescale offset
timeoffset = float(scope.query(":TIM:OFFS?")[0])
voltscale = float(scope.query(':CHAN1:SCAL?')[0])

# And the voltage offset
voltoffset = float(scope.query(":CHAN1:OFFS?")[0])

# Note: not :WAV:POIN:MODE, which is for other DS1000-series
# Rigol scopes, but causes errors here
scope.write(":WAV:FORM ASC")
scope.write(":WAV:MODE NORM") # NORM instead of RAW, which takes the whole buffer

# Didn't help
# scope.write(":ACQ:MEMD LONG")

# Make sure things are what we set them to be
print("Check some values.")
print("timescale:",timescale)
print("timeoffset:",timeoffset)
print("voltscale:",voltscale)
print("voltoffset",voltoffset)
print("Wave form:",scope.query(":WAV:FORM?"))
print("Mode:",scope.query("WAV:MODE?"))

# Hope to shorten data collected, did not stop error
scope.write(":WAV:STAR 1")
scope.write(":WAV:STOP 100")

# Are there any error up to this point?
# it seems like there are, but I can't tell why -
# e.g. "Query INTERRUPTED" error pops up even if i didn't
# query anything
print("Error check:",scope.query(":SYSTem:ERRor?"))

# Error party
print("About to fetch data...")
rawdata = scope.query(":WAV:DATA? CHAN1").encode('ascii')[10:]

# These are attempts to check just a little at a time,
# following pyvisa tips, but also fail
# https://pyvisa.readthedocs.io/en/latest/introduction/rvalues.html
#scope.write(':WAV:DATA? CHAN1')
#data = scope.read_bytes(1)
#data = scope.read_raw()

#rawdata = scope.query(":WAV:DATA? CHAN1").encode('ascii')[10:]
#data_size = len(rawdata)
#sample_rate = scope.query(':ACQ:SAMP?')[0]
#print('Data size:', data_size, "Sample rate:", sample_rate)

# Threads that discuss the error message shown:
# https://github.com/pyvisa/pyvisa-py/issues/20
# https://github.com/pyvisa/pyvisa/issues/458
# https://github.com/pyvisa/pyvisa/issues/449
