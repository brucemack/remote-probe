import serial

# Takes a binary array and creates a 
# string of the corresponding ascii hex characters (two characters per byte)
def binary_to_hex(ascii_list):
    result = ""
    for c in ascii_list:
        result = result + "{:02x}".format(c)
    return result

port = "/dev/ttyACM1"

usb = serial.Serial(port, 115200, timeout=0.05)

usb.write("ping\r".encode("utf-8"))
cmd = "send " + binary_to_hex("BRUCE".encode("utf-8")) + "\r"
usb.write(cmd.encode("utf-8"))

while True:
    if usb.is_open:
        if usb.in_waiting > 0:
            # Line-oriented interface
            data = usb.readline().decode("utf-8").strip()
            print("Got", data)

