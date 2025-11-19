# Imports here
import motor_control
import save_data_to_csv
from gpiozero import Button, DigitalOutputDevice

E_STOP_PIN = 23
E_STOP_SOURCE = 24

E_STOP_ACTIVATED = False
e_stop_button = None
stop_source_pin = None
bus = None

# ---------------------
def emergency_stop_handler():
    global bus
    global E_STOP_ACTIVATED
    
    if bus is not None:
        print("\n\n*** HARDWARE E-STOP DETECTED! Executing emergency stop. ***")
        E_STOP_ACTIVATED = True
        motor_control.emergency_stop_motor(bus)
        print("Motor stopped.")
        exit
    else:
        print("\n\n*** HARDWARE E-STOP DETECTED, but communication with PICO1 is not initalized! ***")
            

# --------------------- ENTRY POINT TO THE PITCH MASTER SCRIPT ----------------------

def main():
    """
    Main interactive loop for controlling the Pico.
    """
    global bus
    global E_STOP_ACTIVATED
    global e_stop_button
    global stop_source_pin
    
    try:
        #stop_source_pin = DigitalOutputDevice(E_STOP_SOURCE)
        #stop_source_pin.on()
        
        e_stop_button = Button(E_STOP_PIN, bounce_time=0.2)
        e_stop_button.when_pressed = emergency_stop_handler
        
        print(f"E-stop interrupt configured on BCM pin {E_STOP_PIN} using rising edge trigger")
    except Exception as e:
        print(f"Failed to set up E-Stop interrupt with gpiozero: {e}")
        return

    # Initialize the I2C bus
    bus = motor_control.init_bus()

    # If bus init failed, exit
    if bus is None:
        print("Failed to initialize I2C bus. Exiting.") 
        return
    
    angle_data = ["null"]
    hlfb_data = ["null"]
    speed = 0

    try:
        max_speed = motor_control.configure_motor()
        while True:
            command = input("\nType the command (start, stop, hlfb, e, save, help, exit): ")
            match command:
                case "help":
                    print('''Here are a list of the commands: 
    start = Asks for speed/ramp, then starts the motor
    stop  = Runs the motor stop sequence
    e     = Brakes the motor with the reverse peak torque and acts like an Emergency Stop
    hlfb  = Starts HLFB capture and reads data
    save  = Saves data to a CSV file
    exit  = Exits the program''')

                case "config":
                    max_speed = motor_control.configure_motor()
                    angle_data = ["null"]
                    hlfb_data = ["null"]
                    speed = 0

                case "start":
                    speed = motor_control.start_motor(bus, max_speed)

                case "stop":
                    # max_speed = motor_control.stop_motor(bus)
                    motor_control.stop_motor(bus)

                case "e":
                    motor_control.emergency_stop_motor(bus)

                case "hlfb":
                    # Test the feedback capture
                    hlfb_data = motor_control.capture_and_read_hlfb(bus)
                    angle_data = hlfb_data[:]
                    print(f"\nSuccessfully captured {len(hlfb_data)} data points.")

                case "save":
                    # Saves the data collected into a CSV file by running this program
                    print("WIP")
                    save_data_to_csv.save(speed, angle_data, hlfb_data)

                case "exit":
                    # Stop the motor before exiting, just in case
                    print("Stopping motor before exit...")
                    motor_control.stop_motor(bus)
                    break

                case _:
                    print("Unknown command. Type 'help' for a list of commands.")

    except Exception as e:
        print(f"An unexpected error occurred in the main loop: {e}")
    finally:
        # IMPORTANT: Always close the bus when done
        motor_control.close_bus(bus)


if __name__ == "__main__":
    main()
