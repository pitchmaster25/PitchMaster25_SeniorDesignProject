# Imports here
import motor_control
from PitchMaster25_SeniorDesignProject.motor_control import configure_motor


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
        max_speed = configure_motor()
        while True:
            command = input("\nType the command (start, stop, hlfb, save, help, exit): ")
            match command:
                case "help":
                    print('''Here are a list of the commands: 
    start = Asks for speed/ramp, then starts the motor
    stop  = Runs the motor stop sequence
    hlfb  = Starts HLFB capture and reads data
    save  = Saves data to a CSV file
    exit  = Exits the program''')

                case "config":
                    max_speed = configure_motor()

                case "start":
                    # This function now handles getting user input AND
                    # sending the command.
                    speed = motor_control.start_motor(bus, max_speed)

                case "stop":
                    max_speed = motor_control.stop_motor(bus)

                case "hlfb":
                    # New command to test the feedback capture
                    hlfb_data = motor_control.capture_and_read_hlfb(bus)
                    print(f"\nSuccessfully captured {len(hlfb_data)} data points.")

                case "save":
                    # Saves the data collected into a CSV file by running this program
                    print("WIP")

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
