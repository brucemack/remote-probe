import serial
import time 
import math 

# Takes a binary array and creates a string of the corresponding ascii hex 
# characters (two characters per byte) with hex in upper case.
def binary_to_hex(ascii_list):
    result = ""
    for c in ascii_list:
        result = result + "{:02x}".format(c).upper()
    return result

class Task:
    def __init__(self, id: int):
        self.id = id
    def get_cmd(self):
        return None
    def is_ack(self, msg):
        return msg == self.get_ack()
    def get_ack(self):
        return ""
    def timeout_ms(self):
        return 1000

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
        return binary_to_hex(long2)
    def get_ack(self):
        long2 = bytearray()
        # Command code
        n = 1
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        # Status
        st = 0
        long2.extend(st.to_bytes(1, byteorder='little'))
        return binary_to_hex(long2)

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
        return binary_to_hex(long2)
    def get_ack(self):
        long2 = bytearray()
        # Command code
        n = 2
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        # Status
        st = 0
        long2.extend(st.to_bytes(1, byteorder='little'))
        return binary_to_hex(long2)

class ResetIntoDebugTask(Task):
    def __init__(self, id: int):
        super().__init__(id)
    def __str__(self):
        return "Reset " + str(self.id)
    def get_cmd(self):
        long2 = bytearray()
        # Command code
        n = 5
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        return binary_to_hex(long2)
    def get_ack(self):
        long2 = bytearray()
        # Command code
        n = 5
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        # Status
        st = 0
        long2.extend(st.to_bytes(1, byteorder='little'))
        return binary_to_hex(long2)

class WriteWorkareaTask(Task):
    def __init__(self, id: int, ptr: int, bin_data):
        super().__init__(id)
        self.ptr = ptr 
        self.bin_data = bin_data
    def __str__(self):
        return "WriteWorkarea " + str(self.id) + ", " + str(self.ptr)
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
        long2.extend(self.bin_data)
        return binary_to_hex(long2)
    def get_ack(self):
        long2 = bytearray()
        # Command code
        n = 3
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        # Status
        st = 0
        long2.extend(st.to_bytes(1, byteorder='little'))
        return binary_to_hex(long2)

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
        # Offset into flash
        long2.extend(self.ptr.to_bytes(4, byteorder='little'))
        # Size in workarea
        long2.extend(self.size.to_bytes(2, byteorder='little'))
        return binary_to_hex(long2)
    def get_ack(self):
        long2 = bytearray()
        # Command code
        n = 4
        long2.extend(n.to_bytes(2, byteorder='little'))
        # Command ID
        long2.extend(self.id.to_bytes(2, byteorder='little'))
        # Status
        st = 0
        long2.extend(st.to_bytes(1, byteorder='little'))
        return binary_to_hex(long2)
    def timeout_ms(self):
        return 10000

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

# Takes a .bin filename and makes the tasks that need to be performed
def make_tasks(fn: str, start_id: int):

    page_size = 4096
    chunk_size = 109
    tasks = []
    task_id = start_id

    tasks.append(InitTask(task_id))
    task_id = task_id + 1
    tasks.append(ResetIntoDebugTask(task_id))
    task_id = task_id + 1
    
    # Create tasks to flash the binary
    with open(fn, 'rb') as file:
        flash_ptr = 0
        # Take the binary file and split it into pages
        for page in blow_chunks(file.read(), page_size):
            workarea_ptr = 0
            # Create a set of updates to the workarea
            for bin_chunk in blow_chunks(page, chunk_size):
                tasks.append(WriteWorkareaTask(task_id, workarea_ptr, bin_chunk))
                workarea_ptr = workarea_ptr + len(bin_chunk)
                task_id = task_id + 1
            # Create a flash command for the entire workarea
            tasks.append(FlashTask(task_id, flash_ptr, page_size))
            flash_ptr = flash_ptr + page_size
            task_id = task_id + 1
    
    tasks.append(ResetTask(task_id))
    task_id = task_id + 1

    return tasks

port = "/dev/ttyACM1"
#port = "/dev/tty.Bluetooth-Incoming-Port"
binfile_name = "/home/bruce/pico/hello-swd/build/blinky.bin"
#binfile_name = "./blinky.bin"

tasks = make_tasks(binfile_name, 1)

#for task in tasks:
#    print(task)

usb = serial.Serial(port, 115200, timeout=0.05)

# States
#
# 1: Ready to start a task
# 2: Waiting for task completion

state = 1
last_start_ms = 0
retry_count = 0
max_retry_count = 3
original_task_count = len(tasks)

while True:
    
    now = time.time() * 1000

    # Finished?
    if len(tasks) == 0:
        break

    # Handle any outbound things we need
    if usb.is_open:
        # Ready to start a task
        if state == 1:
            #print("Starting Task:", tasks[0], tasks[0].get_cmd())
            print("Remaining",int(100*len(tasks)/original_task_count),"%")
            # Launch the command
            cmd = "send " + tasks[0].get_cmd() + "\r"
            #print("Sending:", cmd)
            usb.write(cmd.encode("utf-8"))
            last_start_ms = now
            retry_count = 0
            state = 2

        # Handle any inbound things
        if usb.in_waiting > 0:
            # This is a line-oriented interface
            rec_data = usb.readline().decode("utf-8").strip()
            if state == 2:
                if rec_data.startswith("I:"):
                    print(rec_data)
                elif rec_data == "ok":
                    pass
                # Check to see if this is the ACK we've been
                # waiting for. If so, pop and move forward. 
                elif rec_data.startswith("receive "):
                    # Split by space delimiter
                    tokens = rec_data.split(" ")
                    if len(tokens) == 3:
                        if tasks[0].is_ack(tokens[2]):
                            tasks.pop(0)
                            state = 1
                            #print("Good ACK")
                        else:
                            print("Unexpected data [0]:", tokens[2])
                            print("Wanted:", tasks[0].get_ack())
                    else:
                        print("Unexpected message [1]:", rec_data)
                else:
                    print("Unexpected message [2]:", rec_data)
            else:
                print("Unexpected message [3]:", rec_data)

        # Handle timer-based events
        if state == 2:
            if (now - last_start_ms) > tasks[0].timeout_ms():
                if retry_count < max_retry_count:
                    print("Response timeout, retrying")
                    # Launch the command again
                    cmd = "send " + tasks[0].get_cmd() + "\r"
                    #print("Sending:", cmd)
                    usb.write(cmd.encode("utf-8"))
                    last_start_ms = now
                    retry_count = retry_count + 1
                else:
                    print("Response timeout, too many retries, failed")
                    break

