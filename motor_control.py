# Import libraries here
import struct
#from smbus2 import SMBus

# ------------------------- Initialize Properties -------------------------------
#sample_rate = 480
pico_add = 0x50

# --------------------- HOLDS THE MOTOR CONTROL FUNCTIONS -----------------------

def command_speed (buf):
    # The user specifies various inputs to drive the motor
    # input() creates a string that is filled with what the user specifies. This must be converted to a number.
    max_speed = int(input("\nSpecify the max speed (rpm): ")) # This string will be stored as an integer.
    operating_speed = float(input("Specify the operating speed (Hz): ")) # This string will be stored as a floating number, decimals allowed.
    ramp_time = int(input("Type the time required to achieve full speed (seconds): ")) # This string will be stored as an integer.

    # The operating speed is first converted into a percentage of the max speed, (duty cycle),
    # and then gets converted into a 16-bit integer, (an unsigned short).
    cmd_speed16 = round(((operating_speed * 60 * 65536) / max_speed))

    # The 16-bit duty cycle is now "packed" into two bytes, and stored into the buffer with
    # the Most Significant Byte (MSB) in the 2nd position and the Least Significant Byte (LSB) in the 3rd position.
    struct.pack_into('>H', buf, 1, cmd_speed16)  # Big-endian unsigned short, buffer, offset 1, 16-bit duty cycle
    buf[3] = ramp_time # The ramp time integer is stored in the 4th position (starts with 0)

    # Tell and show the user that it worked. Great for debugging.
    print("\nWaveform command properly defined! Buffer:", list(buf))
    return buf

def start_sequence (buf):
    # Fills the 1st position with the command to the PICO
    buf[0] = 0x01 # 0x01 = start_sequence

    #with SMBus(1) as bus:
        #bus.write_byte_data(pico_add, 0, buf)

    print("\nMotor commanded properly! Buffer:", list(buf))
    return buf