import motor_control
import save_data_to_csv
import encoder_control  # <--- NEW IMPORT
import time
import gui

# Development mode toggle: when True, use MockFactory for gpiozero pins and
# enable the Dummy I2C bus emulation in `motor_control` by passing DEV_MODE
# into `init_bus`.
DEV_MODE = False

# GUI vs Terminal toggle: set to True to launch the PySide6 GUI instead of CLI
GUI_MODE = True

# GPIO setup: use MockFactory when DEV_MODE is True; otherwise try to import
# the native gpiozero devices. Fall back to MockFactory only if native import
# fails (keeps behavior robust on developer machines).
if DEV_MODE:
    try:
        from gpiozero import Device
        from gpiozero.pins.mock import MockFactory
        Device.pin_factory = MockFactory()
        from gpiozero import Button, DigitalOutputDevice
        print("gpiozero: using MockFactory (no physical GPIO required) [DEV_MODE]")
    except Exception as e:
        print(f"DEV_MODE requested but MockFactory unavailable: {e}. Trying normal gpiozero import.")
        from gpiozero import Button, DigitalOutputDevice
else:
    try:
        from gpiozero import Button, DigitalOutputDevice
    except Exception as e:
        print(f"Failed to import gpiozero native backends: {e}. Attempting MockFactory fallback.")
        try:
            from gpiozero import Device
            from gpiozero.pins.mock import MockFactory
            Device.pin_factory = MockFactory()
            from gpiozero import Button, DigitalOutputDevice
            print("gpiozero: using MockFactory as fallback")
        except Exception as e2:
            print(f"Fallback MockFactory failed: {e2}")
            raise

# (DEV_MODE can be changed above; do not override it here.)

# --- E-STOP CONFIGURATION ---
E_STOP_PIN = 23
E_STOP_SOURCE = 24
E_STOP_ACTIVATED = False
e_stop_button = None
bus = None

# --------------------- E-STOP HANDLER ----------------------
def emergency_stop_handler():
    global bus
    global E_STOP_ACTIVATED
    
    if bus is not None:
        print("\n\n*** HARDWARE E-STOP DETECTED! Executing emergency stop. ***")
        E_STOP_ACTIVATED = True
        motor_control.emergency_stop_motor(bus)
        print("Motor stopped.")
    else:
        print("\n\n*** HARDWARE E-STOP DETECTED, but communication with PICO1 is not initialized! ***")

# --------------------- ENTRY POINT ----------------------
def main():
    print("Starting PitchMaster25 Motor Control Interface")
    global bus
    global E_STOP_ACTIVATED
    global e_stop_button
    
    try:
        e_stop_button = Button(E_STOP_PIN, bounce_time=0.2)
        e_stop_button.when_pressed = emergency_stop_handler
        print(f"E-stop interrupt configured on BCM pin {E_STOP_PIN}")
    except Exception as e:
        print(f"Failed to set up E-Stop interrupt: {e}")
        print("Continuing without hardware E-Stop (DEV_MODE or missing pin factory).")
        e_stop_button = None

    # Initialize the I2C bus (pass DEV_MODE to enable emulation)
    bus = motor_control.init_bus(DEV_MODE)
    if bus is None:
        print("Failed to initialize I2C bus. Exiting.") 
        return
    
    # Data storage
    angle_data = ["null"]
    hlfb_data = ["null"]
    encoder_data = ["null"] # <--- Storage for Pico 2 data
    speed = 0

    try:
        max_speed = motor_control.configure_motor()
        
        while True:
            command = input("\nType command (start, stop, arm, read_enc, hlfb, save, exit): ")
            
            match command:
                case "help":
                    print('''Commands: 
    start    = Start motor
    stop     = Stop motor
    e        = Emergency Brake
    pos      = Reads the current position
    arm      = Arms Pico 2 to record encoder on triggers
    read_enc = Downloads recorded encoder data from Pico 2
    hlfb     = Capture HLFB data
    save     = Save data to CSV
    exit     = Exit program''')

                case "config":
                    max_speed = motor_control.configure_motor()
                    angle_data = ["null"]
                    hlfb_data = ["null"]
                    encoder_data = ["null"]
                    speed = 0

                case "start":
                    speed = motor_control.start_motor(bus, max_speed)

                case "stop":
                    motor_control.stop_motor(bus)

                case "e":
                    motor_control.emergency_stop_motor(bus)
                    
                case "pos":
                    # Grab one sample immediately
                    val = encoder_control.read_single_sample(bus)
                    if val is not None:
                        print(f"Current Position: {val}")
                    else:
                        print("Failed to read position.")
                    
                case "arm":
                    encoder_control.arm_encoder(bus)

                case "read_enc":
                    print("Attempting to read data from Pico 2...")
                    # Calling the separate file
                    data = encoder_control.read_encoder_data(bus)
                    
                    if data:
                        encoder_data = data 
                        print(f"Retrieved {len(encoder_data)} samples.")
                        print(f"First 5 samples: {encoder_data[:5]}")
                    else:
                        print("No data retrieved.")

                case "hlfb":
                    hlfb_data = motor_control.capture_and_read_hlfb(bus)
                    angle_data = hlfb_data[:] 
                    print(f"\nSuccessfully captured {len(hlfb_data)} data points.")

                case "save":
                    print("Saving to CSV...")
                    # Ensure your save_data_to_csv.save function accepts the 4th argument!
                    save_data_to_csv.save(speed, angle_data, hlfb_data, encoder_data)

                case "exit":
                    print("Stopping motor before exit...")
                    motor_control.stop_motor(bus)
                    break

                case _:
                    print("Unknown command. Type 'help'.")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
        motor_control.stop_motor(bus)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        motor_control.close_bus(bus)

if __name__ == "__main__":
    if GUI_MODE:
        gui.run_gui(DEV_MODE)
    else:
        main()
