import serial
import time 
import math 

class Task:
    def __init__(self, id: int):
        self.id = id
    def get_cmd(self):
        return None
    def is_ack(self, msg):
        return msg == self.get_ack()
    def get_ack(self):
        return ""

class InitTask(Task):
    def __init__(self, id: int):
        super().__init__(id)
    def __str__(self):
        return "Init " + str(self.id)
    def get_cmd(self):
        long2 = bytearray()
        # Command code
        n = 1
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        return "send " + binary_to_hex(long2) + "\r"
    def get_ack(self):
        long2 = bytearray()
        # Command code
        n = 1
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        return "receive " + binary_to_hex(long2) + "\r"

class ResetTask(Task):
    def __init__(self, id: int):
        super().__init__(id)
    def __str__(self):
        return "Reset " + str(self.id)
    def get_cmd(self):
        long2 = bytearray()
        # Command code
        n = 2
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        return "send " + binary_to_hex(long2) + "\r"
    def get_ack(self):
        long2 = bytearray()
        # Command code
        n = 2
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        return "receive " + binary_to_hex(long2) + "\r"

class WriteWorkareaTask(Task):
    def __init__(self, id: int, ptr: int, data):
        super().__init__(id)
        self.ptr = ptr 
        self.data = data
    def __str__(self):
        return "WriteWorkarea " + str(self.id) + ", " + str(self.ptr) + ", " + self.data
    def get_cmd(self):
        long2 = bytearray()
        # Command code
        n = 3
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        # Offset into workarea
        long2.extend(self.ptr.to_bytes(2, byteorder='little'))
        # The data itself
        long2.extend(self.data)
        return "send " + binary_to_hex(long2) + "\r"
    def get_ack(self):
        long2 = bytearray()
        # Command code
        n = 3
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        return "receive " + binary_to_hex(long2) + "\r"

class FlashTask(Task):
    def __init__(self, id: int, ptr: int, size: int):
        super().__init__(id)
        self.ptr = ptr 
        self.size = size
    def __str__(self):
        return "Flash " + str(self.id) + ", " + str(self.ptr) + ", " + str(self.size)
    def get_cmd(self):
        long2 = bytearray()
        # Command code
        n = 4
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        # Offset into workarea
        long2.extend(self.ptr.to_bytes(2, byteorder='little'))
        # Size in workarea
        long2.extend(self.size.to_bytes(2, byteorder='little'))
        return "send " + binary_to_hex(long2) + "\r"
    def get_ack(self):
        long2 = bytearray()
        # Command code
        n = 4
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        return "receive " + binary_to_hex(long2) + "\r"

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
def make_tasks(fn: str, start_id: int):

    page_size = 4096
    chunk_size = 109
    tasks = []
    task_id = start_id

    tasks.append(InitTask(task_id))
    task_id = task_id + 1

    # Create tasks to flash the binary
    with open(fn, 'rb') as file:
        flash_ptr = 0
        # Take the binary file and split it into pages
        for page in blow_chunks(file.read(), page_size):
            workarea_ptr = 0
            # Create a set of updates to the workarea
            for chunk in blow_chunks(page, chunk_size):
                tasks.append(WriteWorkareaTask(task_id, workarea_ptr, binary_to_hex(chunk)))
                workarea_ptr = workarea_ptr + len(chunk)
                task_id = task_id + 1
            # Create a flash command for the entire workarea
            tasks.append(FlashTask(task_id, flash_ptr, page_size))
            flash_ptr = flash_ptr + page_size
            task_id = task_id + 1

    tasks.append(ResetTask(task_id))
    task_id = task_id + 1

    return tasks

#port = "/dev/ttyACM1"
port = "/dev/tty.Bluetooth-Incoming-Port"
#binfile_name = "/home/bruce/pico/hello-swd/build/blinky.bin"
binfile_name = "./blinky.bin"

tasks = make_tasks(binfile_name, 1)

for task in tasks:
    print(task)

usb = serial.Serial(port, 115200, timeout=0.05)

# States
#
# 1: Ready to start a task
# 2: Waiting for task completion
# 3: All done
# 4: Failed 

state = 1
c = 0
last_start_ms = 0
working_task = None
retry_count = 0
max_retry_count = 3
cmd_id = 0

while True:
    
    now = time.time() * 1000

    # Finished?
    if len(tasks) == 0:
        break

    # Handle any outbound things we need
    if usb.is_open:
        # Ready to start a task
        if state == 1:
            print("Starting Task:", tasks[0], tasks[0].get_cmd())
            # Launch the command
            usb.write(tasks[0].get_cmd().encode("utf-8"))
            last_start_ms = now
            retry_count = 0
            state = 2

        # Handle any inbound things
        if usb.in_waiting > 0:
            # This is a line-oriented interface
            rec_data = usb.readline().decode("utf-8").strip()
            if state == 2:
                if rec_data == "ok":
                    pass
                # Check to see if this is the ACK we've been
                # waiting for. If so, pop and move forward. 
                elif tasks[0].is_ack(rec_data):
                    tasks.pop(0)
                    state = 1
                else:
                    print("Unexpected message:", rec_data)
            else:
                print("Unexpected message:", rec_data)

        # Handle timer-based events
        if state == 2:
            if (now - last_start_ms) > 1000:
                if retry_count < max_retry_count:
                    print("Response timeout, retrying")
                    # Launch the command again
                    usb.write(tasks[0].get_cmd().encode("utf-8"))
                    last_start_ms = now
                    retry_count = retry_count + 1
                else:
                    print("Response timeout, too many retries, failed")
                    break

