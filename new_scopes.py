import pyvisa
import numpy as np

# For debug
pyvisa.log_to_screen()

rm = pyvisa.ResourceManager()
print("Resources connected to this RP:")
print(rm.list_resources())

# Found it. For a different scope, take the equivalent
# from the list of resources gained above.
scope_address = 'USB0::6833::1303::DS1ZE231705963::0::INSTR'
scope = rm.open_resource(scope_address, chunk_size=1024000)

# Configuration
scope.timeout = 1000  # ms
scope.encoding = 'latin_1'
# The below seem currently not needed
#scope.read_termination = '\n'
#scope.write_termination = '\n'

# Check the scope can hear us
print(scope.query('*IDN?'))

# The scope is a Rigol DS1202.
# Here is the programming guide for the 1000-series Rigol scopes:
# https://www.batronix.com/pdf/Rigol/ProgrammingGuide/DS1000DE_ProgrammingGuide_EN.pdf
# Examples for how to retrieve data taken from:
# https://gist.github.com/pklaus/7e4cbac1009b668eafab

# To reset the scope - you will lose your settings!
# scope.write('*rst') # reset

print("Aquire type:",scope.query("ACQuire:TYPE?"))

# Check scope triggering status
print("Trigger status:",scope.query("trig:status?"))

# What do I get if I just directly request a trace?
print("Wave mode:",scope.query(":WAV:POIN:MODE?"))
print("Trying sample rate.")
scope.write(":START")
sample_rate = scope.query(':ACQ:SAMP?')
print("Sample rate:", sample_rate)
scope.write(":ACQ:MEMD LONG")
scope.write(":WAV:POIN:MODE RAW")
#rawdata = scope.query(":WAV:DATA? CHAN1").encode('ascii')[10:]
#rawdata = scope.query_binary_values(":WAV:DATA? CHAN1", datatype = 'b', container = np.array)
scope.write(":WAV:DATA? CHAN1") #Request the data
rawdata = scope.read() #Read the block of data
rawdata = rawdata[ 10 : ] #Drop the heading
print(rawdata)
scope.write(":START")

# Scales in x axis (time)
timescale = float(scope.query(":TIM:SCAL?"))
timeoffset = float(scope.query(":TIM:OFFS?")[0])
print(timescale, timeoffset)

# Scales in y axis (volts)
