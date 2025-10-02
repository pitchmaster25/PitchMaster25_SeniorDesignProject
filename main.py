# Hello to both GitHub and Connors Laptop!! Am I working
# Can you receive me?? COnnors Laptop


# Imports here

from motor_control import *

# --------------------- ENTRY POINT TO THE PITCH MASTER SCRIPT ----------------------

# Strictly using console commands

selected_waveform, operating_speed, ramp_time = command_speed()

while True:
    command = input("\nType the command you would like to execute: ")
    match command:
        case "help":
            print('''Here are a list of the commands: 

command = commands the motor how to operate            
start = runs the motor start up sequence
stop = runs the motor stop sequence
exit = exits the program''')
        case "command":
            command_speed()
        case "start":
            start_sequence(operating_speed, ramp_time)
        case "exit":
            break

