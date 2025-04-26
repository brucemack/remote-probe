import serial
import time 

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
binfile_ptr = 0
with open(binfile_name, 'rb') as file:
    binfile = file.read()

long = bytearray()
for i in range(0, 110):
    long.append(65)
long.append(66)

n = 0x1234

#usb.write("ping\r".encode("utf-8"))
#cmd = "send " + binary_to_hex("BRUCE".encode("utf-8")) + "\r"

state = 1
c = 0

while True:
    if usb.is_open:

        # Handle any outbound things we need
        if state == 1:
            cmd = "getstatus\r"
            usb.write(cmd.encode("utf-8"))
            state = 2
        elif state == 3:
            #print("Sending")
            c = c + 1
            n = c
            long2 = bytearray()
            long2.extend(n.to_bytes(1, byteorder='little'))
            long2.extend(long)
            cmd = "send " + binary_to_hex(long2) + "\r"
            usb.write(cmd.encode("utf-8"))
            state = 4

        # Handle any inbound things
        if usb.in_waiting > 0:
            # Line-oriented interface
            rec_data = usb.readline().decode("utf-8").strip()
            print("Got", rec_data)
            if rec_data == "status y":
                if state == 2:
                    state = 3
            elif rec_data == "status n":
                if state == 2:
                    time.sleep(0.1)
                    state = 1
            elif rec_data == "ok":
                if state == 4:
                    state = 1




