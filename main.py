# Imports here
import motor_control


# --------------------- ENTRY POINT TO THE PITCH MASTER SCRIPT ----------------------

def main():
    """
    Main interactive loop for controlling the Pico.
    """
    # Initialize the I2C bus
    bus = motor_control.init_bus()

    # If bus init failed, exit
    if bus is None:
        print("Failed to initialize I2C bus. Exiting.")
        return

    try:
        while True:
            command = input("\nType the command (start, stop, hlfb, help, exit): ")
            match command:
                case "help":
                    print('''Here are a list of the commands: 
    start = Asks for speed/ramp, then starts the motor
    stop  = Runs the motor stop sequence
    hlfb  = Starts HLFB capture and reads data
    exit  = Exits the program''')

                case "start":
                    # This function now handles getting user input AND
                    # sending the command.
                    motor_control.start_motor(bus)

                case "stop":
                    motor_control.stop_motor(bus)

                case "hlfb":
                    # New command to test the feedback capture
                    hlfb_data = motor_control.capture_and_read_hlfb(bus)
                    print(f"\nSuccessfully captured {len(hlfb_data)} data points.")

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
