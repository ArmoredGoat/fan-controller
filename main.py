#!/usr/bin/env python
import time
import pigpio
import fan_controller
import config_reader

PATH_CONFIG_FILE = './fan-controller.conf'

def main():
    """
    Main function to aggregate and call other needed functions.
    """

    ### I N I T I A L I Z A T I O N

    # Create pi object with pigpio's pi class.
    pi = pigpio.pi()

    # Read configuration file
    config = config_reader.read_config(PATH_CONFIG_FILE)

    # Create fan controller object of FanController class.
    p = fan_controller.FanController(pi, config['RPM_GPIO'])

    # If exporting with Prometheus is enabled, initalize metrics and server.
    if config['ENABLE_PROMETHEUS_EXPORTER']:
        p.init_prometheus_exporter(config['PROMETHEUS_PORT'])

    ### M A I N   L O O P
    try:
        while True:
            # Set start time to determine when the next loop should start.
            time_start = time.time()

            ### G A T H E R   V A L U E S

            # Get temperature from sensor and round it to one decimal place.
            temperature = round(p.get_temperature(\
                config['PATH_TEMPERATURE_FILE']), 1)
            # Get duty cycle value accordingly to temperature.
            duty_cycle_decimal, duty_cycle_percent = \
                p.get_duty_cycle(temperature, config)
            # Get RPM and convert to rounded integer.
            rpm = round(p.get_rpm())
            
            ### S E T   V A L U E S

            # Set PWM duty cycle and send it to fan.
            pi.set_PWM_dutycycle(config['PWM_GPIO'], duty_cycle_decimal)

            ### E X P O R T I N G

            # If exporting to local file is enabled, export.
            if config['ENABLE_LOCAL_EXPORT']:
                p.export_values(config['PATH_EXPORT_FILE'], temperature, rpm, \
                    duty_cycle_decimal)
            # If exporting to Prometheus is enabled, update metrics every loop.
            if config['ENABLE_PROMETHEUS_EXPORTER']:
                p.update_metrics(temperature, rpm, duty_cycle_percent)

            ### w A I T I N G   R O O M

            # Wait until loop duration is reached until starting next loop.
            while (time.time() - time_start) < config['LOOP_DURATION']:
                time.sleep(0.2)

    ### S T U F F   T O   D O   A F T E R   S T O P P I N G   S C R I P T
    finally:
        p.clean_up(pi)


# Call main() function if this file is run directly instead of being imported.
if __name__ == "__main__":
    main()