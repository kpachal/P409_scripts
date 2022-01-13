import pyvisa
rm = pyvisa.ResourceManager()
print("Resources connected to this RP:")
print(rm.list_resources())

# Found it. For a different scope, take the equivalent
# from the list of resources gained above.
scope_address = 'USB0::6833::1303::DS1ZE231705963::0::INSTR'
scope = rm.open_resource(scope_address)

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

print(scope.query("ACQuire:TYPE?"))

# Check scope triggering status
print(scope.query("trig:status?"))
print(scope.query())
