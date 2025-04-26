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

# Fixed message
long = bytearray()
for i in range(0, 108):
    long.append(65)
long.append(66)

state = 1
c = 0
last_send_ms = 0

while True:
    if usb.is_open:

        # Handle any outbound things we need
        if state == 1:
            print("Checking status")
            cmd = "getstatus\r"
            usb.write(cmd.encode("utf-8"))
            state = 2
        elif state == 3:
            print("Sending data")
            c = c + 1
            long2 = bytearray()
            # Command
            n = 1
            long2.extend(n.to_bytes(2, byteorder='little'))
            # Seq
            n = c
            long2.extend(n.to_bytes(2, byteorder='little'))
            # Offset
            n = 0
            long2.extend(n.to_bytes(2, byteorder='little'))
            long2.extend(long)
            cmd = "send " + binary_to_hex(long2) + "\r"
            usb.write(cmd.encode("utf-8"))
            last_send_ms = time.time() * 1000

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
                    time.sleep(0.01)
                    state = 1
            elif rec_data == "ok":
                if state == 4:
                    state = 5
            elif rec_data.startswith("receive"):                
                if state == 5:
                    state = 1

        # Handle timeer-based events
        if state == 5:
            now = time.time() * 1000
            if now - last_send_ms > 1000:
                print("Response timeout")
                state = 1


