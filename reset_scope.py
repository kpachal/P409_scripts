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

# Release scope for next call
rm.close()
scope.close()
