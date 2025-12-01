import struct
import time
from smbus2 import SMBus


# --- Dummy I2C Bus for dev-mode (emulation) -----------------
class DummyBus:
    """A simple I2C bus emulator that responds to the project's basic commands.

    This is intentionally minimal: it returns plausible status buffers so the
    higher-level logic in `motor_control` and `encoder_control` can run without
    physical hardware.
    """
    def __init__(self):
        self._last_write = {}
        # Memory per address for emulated devices
        self._memory = {}
        # Prepare some default encoder data for pico2 (address 0x60)
        self._encoder_samples = [i * 10 for i in range(200)]

    def write_i2c_block_data(self, addr, register, data):
        # store last write for the address so read logic can inspect it
        self._last_write[addr] = (register, bytes(data) if isinstance(data, (bytes, bytearray)) else bytes(data))

        # If writing to Pico2 (encoder) with CMD_RECORD, populate memory
        if addr == 0x60:
            if len(data) >= 2 and data[0] == 0x21:  # CMD_RECORD
                samples = data[1] or 200
                # prepare bytes (signed ints) for samples
                b = bytearray()
                for i in range(samples):
                    val = self._encoder_samples[i % len(self._encoder_samples)]
                    b.extend(struct.pack('<i', val))
                self._memory[addr] = bytes(b)

        return None

    def read_i2c_block_data(self, addr, register, length):
        # Inspect last write to decide what to return
        last = self._last_write.get(addr)

        # Emulated Pico (HLFB) at 0x50
        if addr == 0x50:
            if last:
                reg, data = last
                cmd = data[0]
                # If the last command was record HLFB, report that capture is done
                if cmd == 3:  # CMD_RECORD_HLFB
                    num = data[1] if len(data) > 1 else 10
                    total_bytes = num * 4
                    # STATUS_HLFB_RECORDED
                    return [0x13, num, total_bytes & 0xFF, (total_bytes >> 8) & 0xFF, 0, 0][:length]
                elif cmd == 4:  # CMD_READ_HLFB_CHUNK
                    # data[1:3] contain offset
                    # Return STATUS_HLFB_DATA_CHUNK + 4-byte little-endian float
                    # Generate a simple waveform value based on offset
                    offset = data[1] | (data[2] << 8)
                    value = float(offset) / 4.0
                    b = bytearray(6)
                    b[0] = 0x15  # STATUS_HLFB_DATA_CHUNK
                    struct.pack_into('<f', b, 1, value)
                    return list(b)[:length]
                elif cmd == 5:  # CMD_EMERGENCY_STOP
                    return [0x12, 0, 0, 0, 0, 0][:length]  # STATUS_MOTOR_STOPPED
                elif cmd == 1:  # CMD_START_SEQUENCE
                    # pretend motor is running, return a speed value
                    speed = 1234
                    return [0x11, (speed >> 8) & 0xFF, speed & 0xFF, 0, 0, 0][:length]

            # Default status (idle)
            return [0x12, 0, 0, 0, 0, 0][:length]

        # Emulated Pico2 (encoder) at 0x60
        if addr == 0x60:
            if last:
                reg, data = last
                cmd = data[0]
                if cmd == 0x23:  # CMD_SINGLE_SHOT
                    # return STATUS_SINGLE_SHOT_READY + 4-byte unsigned int
                    val = 123456
                    b = bytearray(5)
                    b[0] = 0x35  # STATUS_SINGLE_SHOT_READY
                    struct.pack_into('<I', b, 1, val)
                    return list(b)[:length]
                elif cmd == 0x21:  # CMD_RECORD
                    mem = self._memory.get(addr, b'')
                    total_bytes = len(mem)
                    # STATUS_READY with total_bytes in bytes 1-2
                    return [0x33, total_bytes & 0xFF, (total_bytes >> 8) & 0xFF, 0, 0, 0][:length]

            # If a read chunk was requested, return STATUS_CHUNK + 4 bytes from memory
            # We attempt to locate the last register used to request the chunk
            # Some calls use write_i2c_block_data with register==CMD_READ_CHUNK and payload [lsb, msb]
            # Try to find a chunk request in last_write
            if last and isinstance(last[1], (bytes, bytearray)):
                payload = last[1]
                if len(payload) >= 3 and payload[0] == 0x22:  # CMD_READ_CHUNK
                    lsb = payload[1]
                    msb = payload[2]
                    offset = lsb | (msb << 8)
                    mem = self._memory.get(addr, b'')
                    chunk = mem[offset:offset+4]
                    if len(chunk) < 4:
                        chunk = chunk.ljust(4, b'\x00')
                    b = bytearray(6)
                    b[0] = 0x34  # STATUS_CHUNK
                    b[1:5] = chunk
                    return list(b)[:length]

            return [0x31, 0, 0, 0, 0, 0][:length]

        # Default: return zeros
        return [0] * length

    def close(self):
        # No resources to free in the dummy bus
        return


# ------------------------ Constants -------------------------
# I2C
I2C_PICO_ADDR = 0x50  # 80 in decimal

# Buffer Commands (Pi5 -> Pico)
CMD_START_SEQUENCE = 1
CMD_STOP_SEQUENCE = 2
CMD_RECORD_HLFB = 3
CMD_READ_HLFB_CHUNK = 4  # Pi5 requests a 4-byte chunk of data
CMD_EMERGENCY_STOP = 5 # Brakes the motor and acts as an emergency stop

# I2C Status Codes (Pico -> Pi5)
STATUS_MOTOR_RUNNING = 0x11
STATUS_MOTOR_STOPPED = 0x12
STATUS_HLFB_RECORDED = 0x13  # Capture is done, data is ready for chunked read
STATUS_HLFB_CAPTURING = 0x14  # Capture is in progress, Pi5 should wait
STATUS_HLFB_DATA_CHUNK = 0x15  # This response contains a 4-byte data chunk
STATUS_ERROR = 0xFF  # General error (e.g., bad command, bad offset)

# Sizing
I2C_BUFFER_SIZE = 6  # Must match the Pico's i2c_mem_buf size


# ----------------- Bus Control Functions ------------------

def init_bus(dev_mode: bool = False):
    """
    Initializes and returns the I2C bus object.
    If `dev_mode` is True, returns a `DummyBus` emulation instance so the
    application can run without physical I2C hardware.
    """
    if dev_mode:
        print("Dev mode enabled: using DummyBus I2C emulator.")
        return DummyBus()

    try:
        bus = SMBus(1)
        print("I2C Bus 1 opened.")
        print(f"Connecting to Pico at {hex(I2C_PICO_ADDR)}...")
        return bus
    except FileNotFoundError:
        print("Error: I2C bus 1 not found.")
        print("Please ensure I2C is enabled on your Raspberry Pi.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during bus init: {e}")
        return None


def close_bus(bus):
    """
    Closes the I2C bus.
    """
    if bus:
        bus.close()
        print("I2C bus closed.")


# ----------------- Motor Control Functions ------------------

def configure_motor():
    print("\n--- Configure Motor ---")
    while True:
        try:
            max_speed = float(input("Specify the max speed (rpm): "))

        except ValueError:
            print("Value is not a valid number. Please try again.")

        else:
            print("Properly defined.")
            return max_speed

def start_motor(bus, max_speed, operating_speed=None, ramp_multiplier=None, direction_string=None):
    """
    Asks the user for motor parameters and sends the
    CMD_START_SEQUENCE command to the Pico.
    """
    print("\n--- Start Motor Sequence ---")
    try:
        # 1. Get parameters (from GUI or CLI). If None, prompt interactively.
        if operating_speed is None:
            operating_speed = float(input("Specify the operating speed (Hz): "))

        # This prompt is updated to reflect what the Pico code is actually doing.
        # The Pico uses this value * RAMP_TIME_MULTIPLIER (15) as the delay_us
        # between each step in the ramp.
        if ramp_multiplier is None:
            ramp_multiplier = int(input("Ramp Delay Multiplier (0-255, ~50 is slow, 1 is fast): "))
        if not 0 <= ramp_multiplier <= 255:
            print("Error: Multiplier must be between 0 and 255.")
            return

        # 2. Calculate 16-bit duty cycle
        # (operating_speed * 60) gives RPM.
        # (rpm / max_speed) gives 0.0-1.0 duty cycle.
        # (* 65535) scales to 16-bit.
        duty_cycle_float = (operating_speed * 60) / max_speed
        if not 0.0 <= duty_cycle_float <= 1.0:
            print(f"Error: Calculated duty cycle ({duty_cycle_float * 100:.1f}%) is not between 0-100%.")
            print("Check your max_speed and operating_speed.")
            return

        cmd_speed16 = round(duty_cycle_float * 65535)  # Use 65535 for full 16-bit range
        
        # Get the direction of the motor
        if direction_string is None:
            direction_string = input("Specify the direction of rotation (cw for clockwise, ccw for counter-clockwise):")
        match direction_string:
            case "cw":
                direction = 0
            case "ccw":
                direction = 1
            case _:
                print(f"Error: Input does not follow specified parameteres {direction_string}")
                return

        # 3. Build the command buffer
        # We create a 6-byte buffer, matching the Pico's.
        buf = bytearray(I2C_BUFFER_SIZE)
        buf[0] = CMD_START_SEQUENCE

        # Pack the 16-bit speed, Big-Endian (>H), into offset 1
        struct.pack_into('>H', buf, 1, cmd_speed16)
        buf[3] = ramp_multiplier
        buf[4] = direction
        

        print(f"\nSending command buffer: {list(buf)}")
        print(f" (16-bit speed: {cmd_speed16}, Multiplier: {ramp_multiplier})")

        # 4. Send command and read status
        # If interactive (parameters were None) ask for confirmation. Otherwise proceed.
        if operating_speed is None:
            confirm = input("Would you like to start sequence? (y/n): ")
            if confirm.lower().strip() != 'y':
                print("Motor start cancelled by user.")
                return

        bus.write_i2c_block_data(I2C_PICO_ADDR, 0, buf)

        # Give the Pico a moment to process (optional, but safe)
        time.sleep(0.01)

        # Read the status back
        status_buf = bus.read_i2c_block_data(I2C_PICO_ADDR, 0, I2C_BUFFER_SIZE)
        print_pico_status(status_buf)

    except ValueError:
        print("Error: Invalid input. Please enter numbers.")
    except Exception as e:
        print(f"An I2C error occurred: {e}")
    else:
        return operating_speed

def stop_motor(bus):
    """
    Sends the CMD_STOP_SEQUENCE command to the Pico.
    """
    print("\n--- Stop Motor Sequence ---")
    try:
        buf = bytearray(I2C_BUFFER_SIZE)
        buf[0] = CMD_STOP_SEQUENCE

        print(f"Sending command buffer: {list(buf)}")

        # Send command
        bus.write_i2c_block_data(I2C_PICO_ADDR, 0, buf)

        # Give the Pico a moment to process
        time.sleep(0.01)

        # Read the status back
        status_buf = bus.read_i2c_block_data(I2C_PICO_ADDR, 0, I2C_BUFFER_SIZE)
        print_pico_status(status_buf)

    except Exception as e:
        print(f"An I2C error occurred: {e}")

def emergency_stop_motor(bus):
    """
    Sends the CMD_EMERGENCY_STOP_SEQUENCE command to the Pico.
    """
    print("\n--- Emergency Stop Sequence ---")
    try:
        buf = bytearray(I2C_BUFFER_SIZE) # Recreates the buffer full of zeros
        buf[0] = CMD_EMERGENCY_STOP # Puts the encoded command into the first index
        bus.write_i2c_block_data(I2C_PICO_ADDR, 0, buf) # Immediately sends the command to PICO1
        print(f"Saw an Emergency Stop command buffer: {list(buf)}") # Tells the user it saw an emergency stop command
        
        time.sleep(0.01) # Give the Pico a moment to process

        status_buf = bus.read_i2c_block_data(I2C_PICO_ADDR, 0, I2C_BUFFER_SIZE)  # Read the status back
        print_pico_status(status_buf)

    except Exception as e:
        print(f"An I2C error occurred: {e}")

# ----------------- HLFB Control Functions -------------------

def capture_and_read_hlfb(bus, num_samples=None):
    """
    Handles the full HLFB capture and readback sequence.
    """
    print("\n--- Start HLFB Capture ---")
    try:
        # Accept num_samples as an optional parameter in case GUI calls this
        # programmatically. If not provided, prompt the user.
        if num_samples is None:
            num_samples = int(input(f"Number of samples to capture (1-255): "))
        if not 1 <= num_samples <= 255:
            print("Error: Samples must be between 1 and 255.")
            return

        # 1. Send the "Record" command
        buf = bytearray(I2C_BUFFER_SIZE)
        buf[0] = CMD_RECORD_HLFB
        buf[1] = num_samples

        print(f"Sending command buffer: {list(buf)}")
        bus.write_i2c_block_data(I2C_PICO_ADDR, 0, buf)
        time.sleep(1)  # Wait 100ms before polling again

        # 2. Poll for "Capture Done" status
        print("Waiting for Pico to finish capture...")
        status_buf = bytearray(I2C_BUFFER_SIZE)
        while True:
            # Read the Pico's status
            status_buf = bus.read_i2c_block_data(I2C_PICO_ADDR, 0, I2C_BUFFER_SIZE)
            status = status_buf[0]

            if status == STATUS_HLFB_CAPTURING:
                print(".", end="", flush=True)
                time.sleep(0.1)  # Wait 100ms before polling again
            elif status == STATUS_HLFB_RECORDED:
                print("\nCapture complete! Data is ready.")
                break
            elif status == STATUS_ERROR:
                print("\nPico reported an error.")
                return
            elif status == CMD_RECORD_HLFB: # <--- This line likely had the inconsistent indentation
                print("\nPico is not ready for me. Must wait.")
                time.sleep(1)  # Wait 100ms before polling again
            else:
                print(f"\nUnexpected status {hex(status)} while waiting.")
                return

        # 3. Data is ready. Read the header info.
        # status_buf is from the last read, which had STATUS_HLFB_RECORDED
        num_captured = status_buf[1]
        total_bytes = status_buf[2] | (status_buf[3] << 8)

        print(f"Pico captured {num_captured} samples ({total_bytes} bytes).")

        if total_bytes == 0:
            print("Pico reported 0 bytes. Aborting.")
            return

        # 4. Loop and read data in 4-byte chunks
        results = []
        print("Reading data chunks...")
        for offset in range(0, total_bytes, 4):
            # 4a. Send the "Read Chunk" command
            cmd_buf = bytearray(I2C_BUFFER_SIZE)
            cmd_buf[0] = CMD_READ_HLFB_CHUNK
            cmd_buf[1] = offset & 0xFF  # Offset LSB
            cmd_buf[2] = (offset >> 8) & 0xFF  # Offset MSB
            
            # print(f"DEBUG: Type of cmd_buf is {type(cmd_buf)}")
            bus.write_i2c_block_data(I2C_PICO_ADDR, 0, cmd_buf)
            time.sleep(0.001)

            # 4b. Immediately read back the chunk
            data_buf = bus.read_i2c_block_data(I2C_PICO_ADDR, 0, I2C_BUFFER_SIZE)

            if data_buf[0] == STATUS_HLFB_DATA_CHUNK:
                # Unpack the 4-byte float (Little-Endian '<f') from offset 1
                val = struct.unpack_from('<f', bytearray(data_buf), 1)[0]
                results.append(val)
            else:
                print(f"Error: Expected DATA_CHUNK at offset {offset}, got {hex(data_buf[0])}")
                break

        # 5. Print results
        print("\n--- Captured HLFB Data ---")
        for i, val in enumerate(results):
            print(f"Sample {i:03d}: {val:.6f}")
        print("----------------------------")
        
        return results

    except ValueError:
        print("Error: Invalid input. Please enter a number.")
    except Exception as e:
        print(f"An I2C error occurred: {e}")


# ------------------- Utility Functions --------------------

def print_pico_status(buf):
    """
    Decodes and prints the status from a read buffer.
    """
    status = buf[0]
    if status == STATUS_MOTOR_RUNNING:
        speed = (buf[1] << 8) | buf[2]
        print(f"Pico Status: MOTOR_RUNNING (Speed: {speed})")
    elif status == STATUS_MOTOR_STOPPED:
        print("Pico Status: MOTOR_STOPPED")
    elif status == STATUS_HLFB_RECORDED:
        print("Pico Status: HLFB_RECORDED (Data ready)")
    elif status == STATUS_HLFB_CAPTURING:
        print("Pico Status: HLFB_CAPTURING (Busy)")
    elif status == STATUS_ERROR:
        print("Pico Status: ERROR")
    else:
        print(f"Pico Status: Unknown ({hex(status)})")
    print(f"Full buffer: {list(buf)}")


