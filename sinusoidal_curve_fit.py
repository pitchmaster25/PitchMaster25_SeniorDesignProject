import numpy as np
from scipy.optimize import leastsq
import matplotlib.pyplot as plt


def sinusoidal_model(t, amplitude, frequency, phase, mean):
    """
    Defines the sinusoidal model function.
    A(t) = amplitude * sin(frequency * t + phase) + mean
    """
    return amplitude * np.sin(frequency * t + phase) + mean


def generate_noisy_data(N, true_amplitude, true_frequency, true_phase, true_mean, noise_level=0.1):
    """
    Generates a set of noisy sinusoidal data points for demonstration.
    """
    # Create the time array
    t = np.linspace(0, 2 * np.pi, N)

    # Generate the "perfect" data
    perfect_data = sinusoidal_model(t, true_amplitude, true_frequency, true_phase, true_mean)

    # Create noise and add it to the data
    noise = noise_level * np.random.randn(N)
    noisy_data = perfect_data + noise

    return t, noisy_data


def estimate_initial_guess(t, data):
    """
    Estimates initial guess parameters from the data.
    """
    # Guess mean
    guess_mean = np.mean(data)

    # Guess amplitude (using peak-to-peak, but subtracting the mean)
    guess_amplitude = np.max(data) - guess_mean

    # Guess phase (common to just start at 0)
    guess_phase = 0.0

    # Guess frequency using FFT
    N = len(t)
    dt = t[1] - t[0]  # Get the time step

    # Compute the FFT
    fft_data = np.fft.fft(data - guess_mean)
    fft_freqs = np.fft.fftfreq(N, dt)

    # Find the frequency (in Hz) with the highest power (ignoring the DC component at index 0)
    dominant_freq_index = np.argmax(np.abs(fft_data[1:N // 2])) + 1
    guess_frequency_hz = fft_freqs[dominant_freq_index]

    # Convert from Hz (cycles/second) to angular frequency (radians/second)
    guess_frequency = 2 * np.pi * guess_frequency_hz

    # Pack guesses into a list
    initial_guess = [guess_amplitude, guess_frequency, guess_phase, guess_mean]

    return initial_guess


def residuals(params, t, data):
    """
    Calculates the residual error between the model and the data.
    """
    amplitude, frequency, phase, mean = params
    model_output = sinusoidal_model(t, amplitude, frequency, phase, mean)
    return data - model_output


def _plot_fit_results(t, data, initial_guess, fitted_params):
    """
    Internal helper function to plot the original data, initial guess, and fitted curve.
    """
    # Unpack parameters for clarity
    guess_amp, guess_freq, guess_phase, guess_mean = initial_guess
    fit_amp, fit_freq, fit_phase, fit_mean = fitted_params

    # Create the data for the plot lines
    fine_t = np.linspace(t.min(), t.max(), 500)

    data_first_guess = sinusoidal_model(t, guess_amp, guess_freq, guess_phase, guess_mean)
    data_fit = sinusoidal_model(fine_t, fit_amp, fit_freq, fit_phase, fit_mean)

    # Create the plot
    plt.figure(figsize=(12, 7))
    plt.plot(t, data, 'o', markersize=4, label='Original Noisy Data', alpha=0.7)
    plt.plot(t, data_first_guess, '--', label='Initial Guess', linewidth=2)
    plt.plot(fine_t, data_fit, '-', label='Fitted Curve', linewidth=3, color='red')

    plt.title('Sinusoidal Curve Fitting')
    plt.xlabel('Time (t)')
    plt.ylabel('Amplitude')
    plt.legend()
    plt.grid(True, linestyle=':')
    plt.show()


def fit_sinusoidal_to_data(t, data, show_plot=False):
    """
    Main entry point for fitting data.
    Takes a time array (t) and data array (data) and fits a
    sinusoidal model to it.

    Args:
        t (np.array): The time array.
        data (np.array): The data array.
        show_plot (bool): If True, will display a plot of the fit.

    Returns:
        list: A list of the fitted parameters:
              [fit_amplitude, fit_frequency, fit_phase, fit_mean]
    """
    print("--- Starting Sinusoidal Fit ---")

    # ---------------------- 1. Make Initial Guess -------------------------
    initial_guess = estimate_initial_guess(t, data)
    print("--- Initial Guess ---")
    print(f"Guess Amplitude: {initial_guess[0]:.4f}, Guess Frequency: {initial_guess[1]:.4f}, "
          f"Guess Phase: {initial_guess[2]:.4f}, Guess Mean: {initial_guess[3]:.4f}\n")

    # --------------------- 2. Run Optimization ----------------------------
    try:
        fitted_params, _ = leastsq(residuals, initial_guess, args=(t, data))

        print("--- Fitted Parameters ---")
        print(f"Fitted Amplitude: {fitted_params[0]:.4f}, Fitted Frequency: {fitted_params[1]:.4f}, "
              f"Fitted Phase: {fitted_params[2]:.4f}, Fitted Mean: {fitted_params[3]:.4f}\n")

    except Exception as e:
        print(f"Error: Optimization failed. {e}")
        print("Returning initial guess as fallback.")
        fitted_params = initial_guess

    # --------------------- 3. Plot Results (Optional) ---------------------
    if show_plot:
        _plot_fit_results(t, data, initial_guess, fitted_params)

    print("--- Fit Complete ---")
    return fitted_params


def run_demo():
    """
    Runs a self-contained demo by generating noisy data and fitting it.
    This demonstrates how to use the 'fit_sinusoidal_to_data' function.
    """
    print("--- Running Demo Mode ---")

    # ---------------------- 1. Define True Parameters ---------------------
    N = 256  # The total number of data points
    TRUE_AMPLITUDE = 3.0
    TRUE_FREQUENCY = 1.15247  # Note: This is angular frequency (radians), not Hz
    TRUE_PHASE = 0.001
    TRUE_MEAN = 0.5

    print("--- True Parameters (for demo) ---")
    print(
        f"Amplitude: {TRUE_AMPLITUDE:.4f}, Frequency: {TRUE_FREQUENCY:.4f}, Phase: {TRUE_PHASE:.4f}, Mean: {TRUE_MEAN:.4f}\n")

    # ---------------------- 2. Generate Data ------------------------------
    t, data = generate_noisy_data(N, TRUE_AMPLITUDE, TRUE_FREQUENCY, TRUE_PHASE, TRUE_MEAN, noise_level=0.3)

    # ---------------------- 3. Call the Fitting Function ------------------
    # This is how your other program would use the module:
    fitted_params = fit_sinusoidal_to_data(t, data, show_plot=True)

    print("--- Demo Complete ---")


if __name__ == "__main__":
    # This block runs ONLY when you execute the script directly
    # (e.g., "python sinusoidal_curve_fit.py")
    # It will NOT run when you "import sinusoidal_curve_fit"

    run_demo()

    input("\nPress Enter to Exit Program: ")
    exit()