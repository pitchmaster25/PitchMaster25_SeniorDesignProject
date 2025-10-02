# Import libraries here

# import RPi.GPIO as GPIO



# ----------------- Initialize Properties -----------------------------

sample_rate = 480 


# ----------------- HOLDS THE MOTOR CONTROL FUNCTIONS -----------------

def command_speed ():
    print(''' 
    1 = Sine
    2 = Square
    3 = Triangle
    ''')
    selected_waveform = input("Type the number corresponding to the waveform you desire: ")

    match selected_waveform:
        case "1":
            print("\nSine Waveform selected!")
        case "2":
            print("\nSquare Waveform selected!")
        case "3":
            print("\nTriangle Waveform selected!")

    operating_speed = input("\nType the operating speed you desire (Hz): ")
    ramp_time = input("Type the time required to achieve full speed (seconds): ")
    print("\nWaveform command properly defined!")
    return selected_waveform, operating_speed, ramp_time

def start_sequence (speed = 0, ramping_time = 0):
    print("\nMotor will increase speed to " + str(speed) + " Hz and take " + str(ramping_time) + " seconds.")
