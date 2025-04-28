import serial
import time 
import math 

class Task:
    def __init__(self):
        pass

class InitTask(Task):
    def __init__(self):
        pass
    def __str__(self):
        return "Init"

class ResetTask(Task):
    def __init__(self):
        pass
    def __str__(self):
        return "Reset"

class WriteWorkareaTask(Task):
    def __init__(self, ptr, data):
        self.ptr = ptr 
        self.data = data
    def __str__(self):
        return "WriteWorkarea " + str(self.ptr) + ", " + self.data

class FlashTask(Task):
    def __init__(self, ptr, size):
        self.ptr = ptr 
        self.size = size
    def __str__(self):
        return "Flash " + str(self.ptr) + ", " + str(self.size)


# Takes a list and creates a list of list using the specified 
# chunk size. The last list may be smaller than the rest.
def blow_chunks(in_list, chunk_size):
    result = []
    whole_chunks = math.ceil(len(in_list) / chunk_size)
    ptr = 0
    for chunk_idx in range(0, whole_chunks):
        this_chunk_size = min(chunk_size, len(in_list) - ptr)
        result.append(in_list[ptr:ptr + this_chunk_size])
        ptr = ptr + this_chunk_size
    return result

# Takes a binary array and creates a 
# string of the corresponding ascii hex characters (two characters per byte)
def binary_to_hex(ascii_list):
    result = ""
    for c in ascii_list:
        result = result + "{:02x}".format(c)
    return result

# Takes a .bin filename and makes the tasks that need to be performed
def make_tasks(fn):

    page_size = 4096
    chunk_size = 109
    tasks = []

    tasks.append(InitTask())

    # Create tasks to flash the binary
    with open(fn, 'rb') as file:
        flash_ptr = 0
        # Take the binary file and split it into pages
        for page in blow_chunks(file.read(), page_size):
            workarea_ptr = 0
            # Create a set of updates to the workarea
            for chunk in blow_chunks(page, chunk_size):
                tasks.append(WriteWorkareaTask(workarea_ptr, binary_to_hex(chunk)))
                workarea_ptr = workarea_ptr + len(chunk)
            # Create a flash command for the entire workarea
            tasks.append(FlashTask(flash_ptr, page_size))
            flash_ptr = flash_ptr + page_size

    tasks.append(ResetTask())

    return tasks

port = "/dev/ttyACM1"
binfile_name = "/home/bruce/pico/hello-swd/build/blinky.bin"

tasks = make_tasks(binfile_name)

for task in tasks:
    print(task)

quit()

usb = serial.Serial(port, 115200, timeout=0.05)

# States
#
# 1: Ready to start a task
# 2: Waiting for task completion
# 3: All done

state = 1
c = 0
last_send_ms = 0
working_task = None

while True:
    if usb.is_open:
        # Handle any outbound things we need
        if state == 1:
            if len(tasks) == 0:
                state = 3
            else:
                working_task = tasks.pop(0)
                print(working_task)
                #cmd = "getstatus\r"
                #usb.write(cmd.encode("utf-8"))
                state = 2
        """
        elif state == 3:
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
        """

        # Handle any inbound things
        if usb.in_waiting > 0:
            # Line-oriented interface
            rec_data = usb.readline().decode("utf-8").strip()

            if rec_data == "status y":
                if state == 2:
                    state = 3
            elif rec_data == "status n":
                if state == 2:
                    #time.sleep(0.01)
                    state = 1
            elif rec_data == "ok":
                if state == 4:
                    state = 5
            elif rec_data.startswith("receive"):                
                if state == 5:
                    state = 1
            else:
                print("LOG:", rec_data)

        # Handle timeer-based events
        if state == 5:
            now = time.time() * 1000
            if now - last_send_ms > 1000:
                print("Response timeout")
                state = 1


