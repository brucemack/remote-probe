import serial

# Takes a binary array and creates a 
# string of the corresponding ascii hex characters (two characters per byte)
def binary_to_hex(ascii_list):
    result = ""
    for c in ascii_list:
        result = result + "{:02x}".format(c)
    return result

port = "/dev/ttyACM1"
binfile_name = "/home/bruce/pico/hello-swd/build/blinky.bin"

usb = serial.Serial(port, 115200, timeout=0.05)

binfile = None
with open(binfile_name, 'rb') as file:
    binfile = file.read()
print(len(binfile))


long = bytearray()
for i in range(0, 110):
    long.append(65)
long.append(66)

n = 0x1234
long2 = bytearray()
long2.extend(n.to_bytes(2, byteorder='little'))
long2.extend(long)

usb.write("ping\r".encode("utf-8"))
#cmd = "send " + binary_to_hex("BRUCE".encode("utf-8")) + "\r"
cmd = "send " + binary_to_hex(long2) + "\r"
usb.write(cmd.encode("utf-8"))

while True:
    if usb.is_open:
        if usb.in_waiting > 0:
            # Line-oriented interface
            data = usb.readline().decode("utf-8").strip()
            print("Got", data)

