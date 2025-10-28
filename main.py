# Imports here
from motor_control import *
import struct

# Initializing Variables
pi_buf = bytearray(6)
speed0 = 0

# --------------------- ENTRY POINT TO THE PITCH MASTER SCRIPT ----------------------

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
            pi_buf = command_speed(pi_buf)
        case "start":
            pi_buf = start_sequence(pi_buf)
        case "stop":
            pi_buf = stop_sequence(pi_buf)
        case "buf":
            print(pi_buf,list(pi_buf))
        case "exit":
            break

