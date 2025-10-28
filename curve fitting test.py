import numpy as np
from scipy.optimize import leastsq
import pylab as plt

# ---------------------- To create the artificial data points ---------------------
N = 1000 # The total number of data points
t = np.linspace(0, 4*np.pi, N) # t is an array from 0 to 4 pi with a total of "N" data points
f = 1.15247 # Optional!! Advised not to use
data = 3.0*np.sin(f*t+0.001) + 0.5 + np.random.randn(N) # create artificial data with noise

# ---------------------- Initial Guess used for the Opt. algorithm ----------------
guess_mean = np.mean(data)
guess_std = 3*np.std(data)/(2**0.5)/(2**0.5)
guess_phase = 0
guess_freq = 1
guess_amp = 3.0
print("Guess Amplitude: ", guess_amp, "\nGuess Frequency: ", guess_freq, "\nGuess Phase: ", guess_phase, "\nGuess Mean: ", guess_mean)

data_first_guess = guess_std*np.sin(t+guess_phase) + guess_mean # Used to plot our first estimate

# --------------------- Define the optimization function --------------------
optimize_func = lambda x: x[0]*np.sin(x[1]*t+x[2]) + x[3] - data
est_amp, est_freq, est_phase, est_mean = leastsq(optimize_func, [guess_amp, guess_freq, guess_phase, guess_mean])[0]
print("\nAmplitude: ", est_amp, "\nFrequency: ", est_freq, "\nPhase: ", est_phase, "\nMean: ", est_mean)

# recreate the fitted curve using the optimized parameters
fine_t = np.arange(0,max(t),0.1)
data_fit2 = est_amp*np.sin(est_freq*fine_t+est_phase)+est_mean

plt.plot(t, data, '.')
plt.plot(t, data_first_guess, label='first guess')
plt.plot(fine_t, data_fit2, label='fitted')
plt.legend()
plt.show()

input("\nEnter to Exit Program: ")
exit()