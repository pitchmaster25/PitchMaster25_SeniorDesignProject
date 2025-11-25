import time
import struct

# --- PICO 2 CONFIGURATION ---
PICO2_ADDR = 0x60 # 96 Decimal
CMD_RECORD = 0x21
CMD_READ_CHUNK = 0x22
STATUS_READY = 0x33
STATUS_CHUNK = 0x34
STATUS_CAPTURING = 0x32

def arm_encoder(i2c_bus, samples=256):
    """
    Sends the command to Pico 2 to arm the trigger and prepare for recording.
    """
    try:
        print(f"[Encoder] Sending ARM command to Pico 2 ({samples} samples)...")
        # Protocol: [CMD, NUM_SAMPLES]
        i2c_bus.write_i2c_block_data(PICO2_ADDR, CMD_RECORD, [samples])
        time.sleep(0.1) 
        print("[Encoder] Armed. Waiting for triggers...")
        return True
    except OSError:
        print("[Encoder] Error: Could not communicate with Pico 2. Check wiring/Address.")
        return False

def read_encoder_data(i2c_bus):
    """
    Polls Pico 2 for status. If ready, downloads data in 4-byte chunks
    and reconstructs the list of integers.
    
    Returns:
        list: A list of integers (encoder positions), or empty list if failed/busy.
    """
    try:
        # 1. Check Status
        # We read 6 bytes just to be safe, though we only need the first few for status
        status_block = i2c_bus.read_i2c_block_data(PICO2_ADDR, 0, 6)
        status = status_block[0]
        
        if status == STATUS_CAPTURING:
            print("[Encoder] Pico 2 is still capturing/processing data. Try again later.")
            return []
            
        elif status == STATUS_READY:
            # 2. Parse Total Size (Bytes 1 and 2)
            total_bytes = status_block[1] | (status_block[2] << 8)
            print(f"[Encoder] Data Ready! Total bytes to read: {total_bytes}")
            
            collected_bytes = bytearray()
            offset = 0
            
            # 3. Chunk Loop
            while offset < total_bytes:
                # Request chunk at specific offset
                # Protocol: [CMD, OFFSET_LSB, OFFSET_MSB]
                lsb = offset & 0xFF
                msb = (offset >> 8) & 0xFF
                i2c_bus.write_i2c_block_data(PICO2_ADDR, CMD_READ_CHUNK, [lsb, msb])
                
                # Give Pico a tiny moment to fill buffer
                time.sleep(0.005) 
                
                # Read response
                chunk_block = i2c_bus.read_i2c_block_data(PICO2_ADDR, 0, 6)
                chunk_status = chunk_block[0]
                
                if chunk_status == STATUS_CHUNK:
                    # Bytes 1-4 are the data
                    collected_bytes.extend(chunk_block[1:5])
                    offset += 4
                else:
                    print(f"[Encoder] Error reading chunk at offset {offset}. Status: {hex(chunk_status)}")
                    break
            
            # 4. Unpack Bytes to Integers
            # 'i' means signed integer (4 bytes)
            count = len(collected_bytes) // 4
            integers = struct.unpack(f'{count}i', collected_bytes)
            return list(integers)
            
        else:
            print(f"[Encoder] Pico 2 reported unexpected status: {hex(status)}")
            return []
            
    except OSError as e:
        print(f"[Encoder] I2C Communication Error: {e}")
        return []
