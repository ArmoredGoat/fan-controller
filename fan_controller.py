#!/usr/bin/env python

"""
ArmoredGoat's Fan Controller for 4-pin fans.

Based on the script read_RPM.py (2016-01-20; Public Domain) found under 
https://abyz.me.uk/rpi/pigpio/examples.html as "RPM Monitor"
"""

import numpy as np
import pigpio # http://abyz.co.uk/rpi/pigpio/python.html
import prometheus_client as prom
import os

class FanController:
    """
    A class to read speedometer pulses and calculate the RPM.
    """

    ### F U N C T I O N S   I   D O   N O T   F U L L Y   U N D E R S T A N D
    #  
    # The following four functions (__init__, _cbf, get_rpm, and clean_up) are
    # not written by me, so I do not really know what each line does. I will try
    # to enhance documentation on these in following versions. As of now, I
    # am just glad, everything works smoothly...
    def __init__(self, pi, gpio, pulses_per_rev=2.0, weighting=0.5, \
        min_rpm=5.0):
        """
        Instantiate with the Pi and gpio of the RPM signal
        to monitor.

        Optionally the number of pulses for a complete revolution
        may be specified.  It defaults to 1.

        Optionally a weighting may be specified.  This is a number
        between 0 and 1 and indicates how much the old reading
        affects the new reading.  It defaults to 0 which means
        the old reading has no effect.  This may be used to
        smooth the data.

        Optionally the minimum RPM may be specified.  This is a
        number between 1 and 1000.  It defaults to 5.  An RPM
        less than the minimum RPM returns 0.0.
        """
        self.pi = pi
        self.gpio = gpio
        self.pulses_per_rev = pulses_per_rev

        self.duty_cycle_value = 0
        self.from_higher_threshold = False
        self.counter = 0

        if min_rpm > 1000.0:
            min_rpm = 1000.0
        elif min_rpm < 1.0:
            min_rpm = 1.0

        self.min_rpm = min_rpm

        self._watchdog = 200 # Milliseconds.

        if weighting < 0.0:
            weighting = 0.0
        elif weighting > 0.99:
            weighting = 0.99

        self._new = 1.0 - weighting # Weighting for new reading.
        self._old = weighting       # Weighting for old reading.

        self._high_tick = None
        self._period = None

        pi.set_mode(gpio, pigpio.INPUT)

        self._cb = pi.callback(gpio, pigpio.RISING_EDGE, self._cbf)
        pi.set_watchdog(gpio, self._watchdog)


    def _cbf(self, gpio, level, tick):

        if level == 1: # Rising edge.

            if self._high_tick is not None:
                t = pigpio.tickDiff(self._high_tick, tick)

                if self._period is not None:
                    self._period = (self._old * self._period) + (self._new * t)
                else:
                    self._period = t

            self._high_tick = tick

        elif level == 2: # Watchdog timeout.

            if self._period is not None:
                if self._period < 2000000000:
                    self._period += (self._watchdog * 1000)


    def get_rpm(self):
        """
        Returns the rpm.
        """
        rpm = 0.0
        if self._period is not None:
            rpm = 60000000.0 / (self._period * self.pulses_per_rev)
            if rpm < self.min_rpm:
                rpm = 0.0

        return rpm


    def clean_up(self, pi):
        """
        Cancels the reader and releases resources.
        """
        
        self.pi.set_watchdog(self.gpio, 0) # cancel watchdog
        self._cb.cancel()

        pi.stop()

    ### F U N C T I O N S   I   D O   U N D E R S T A N D

    def export_values(self, path, temperature, rpm, duty_cycle):
        """
        Function to export values to file.
        """
        
        # Create dictionary with values.
        values = {
            "temperature": temperature,
            "rpm": rpm,
            "duty cycle": duty_cycle,
        }

        # Split path string on last occurrence (first from right) of '/'
        # to get the directory path.  
        path_directory = path.rsplit('/', 1)[0]

        # Create directory if it does not exist already.
        try:
            os.makedirs(path_directory)
        except FileExistsError:
            # Directory already exists.
            pass
    
        # Write dictionary as string to file.
        with open(path, "w") as file:
            file.write(f"{values}")


    def init_prometheus_exporter(self, port):
        """
        Function to define metrics and start a http server to export them.
        """

        # Create metrics to track rpm, temperature and duty cycle values 
        # over time.
        self.gauge_rpm = prom.Gauge('fan_controller_rpm', \
            'Current rotations per minute in rpm')
        self.gauge_temperature = prom.Gauge('fan_controller_temperature', \
            'Current temperature in Celsius degree')
        self.gauge_duty_cycle = prom.Gauge('fan_controller_duty_cycle', \
            'Current duty cycle in percent')

        # Start http server on given port to export the metrics.
        prom.start_http_server(port)
    

    def get_duty_cycle(self, temperature, config):
        """
        Function to determine and periodically reevaluate the desired 
        duty cycle.
        """

        # Get values from config directory.
        duty_cycle_min = config['DUTY_CYCLE_MIN']
        duty_cycle_max = config['DUTY_CYCLE_MAX']
        thresholds = config['THRESHOLDS']

        # If DUTY_CYCLE_VALUES is set to 'auto' generate further values with
        # equal spacing beetween DUTY_CYCLE_MIN and DUTY_CYCLE_MAX. The total
        # number of values corresponds to the number of thresholds plus 1. The
        # values must be rounded, as only integers between 0 and 255 are
        # permitted.
        if config['DUTY_CYCLE_VALUES'] == 'auto':
            duty_cycle_values = np.round(np.linspace(duty_cycle_min, \
                duty_cycle_max, len(thresholds)+1)).astype(int)
        # If DUTY_CYCLE_VALUES is not set to 'auto' use the values set in config
        # file and add DUTY_CYCLE_MIN and DUTY_CYCLE_MAX to the beginning and
        # end of list.
        else:
            duty_cycle_values = config['DUTY_CYCLE_VALUES']
            duty_cycle_values.insert(0, duty_cycle_min)
            duty_cycle_values.append(duty_cycle_max)

        # Set value to given value/value of last loop
        duty_cycle_value = self.duty_cycle_value

        # To prevent the fan speed from spinning up and down every other loop
        # when the (ambient) temperature is near a threshold, I implemented
        # a flag to check if the temperature is decreasing or rather the
        # temperature was above a higher threshold before. If yes, the fans will
        # spin with the duty cycle of the higher threshold range until it cooled
        # down to threshold - hysteresis.
        # Contrary, if the temperature rises and surpass the upper threshold
        # despite the faster spinning fans, the flag will also get set to False
        # to let the controller react to this uncommon circumstance.
        if self.from_higher_threshold:
            # Loop through possible values of duty cycles
            for i in range(len(duty_cycle_values)):
                # Important check to prevent IndexError. There is one more entry
                # for duty cycle values as for thresholds. Thus, the index for
                # the last duty cycle value will be out of bounds.
                if i+1 < len(duty_cycle_values):
                    # Check if the temperatue value is still within the duty
                    # cycle's thresholds. If not, set flag to False to enter
                    # the section to set the duty cycle value.
                    if duty_cycle_values[i] == duty_cycle_value \
                            and (temperature < (thresholds[i-1] \
                            - config['HYSTERESIS']) \
                            or temperature >= thresholds[i]):
                        
                        self.from_higher_threshold = False
                        break
                # This else statement covers the exception mentioned above. The
                # highest duty cycle value is linked to the highest threshold.
                else:
                    if duty_cycle_values[-1] == duty_cycle_value \
                            and (temperature < (thresholds[-1] \
                            - config['HYSTERESIS'])):
                        
                        self.from_higher_threshold = False
                        break

            # If the temperature is stuck in the hysteresis (e.g. coming from
            # 23.5 degree Celcius down to 21.5 degree Celsius) and therefore
            # the fans do not spin down to 20% duty cycle, the counter below
            # increases every loop from_higher_threshold is True. If it
            # reaches a set value from_higher_threshold switches to False.
            # The controller will reevaluate its duty cycle setting.
            #
            # At a loop time of 30 seconds a counter limit of 10 would let
            # the controller reevaluate its duty cycle setting after 5
            # minutes of being stuck in the hysteresis.
            self.counter += 1
            if self.counter > config['HYSTERESIS_STUCK_COUNTER']:
                self.from_higher_threshold = False
                self.counter = 0    # Reset counter

        # If it is the first loop after starting the script or thresholds are
        # met set duty cycle accordingly to temperature
        if not self.from_higher_threshold:
            # If temperature is below lowest threshold, set fans to lowest
            # duty cycle
            if temperature < thresholds[0]:
                duty_cycle_value = duty_cycle_values[0]
            # If temperature is above highest threshold, set fans to highest
            # duty cycle
            elif temperature > thresholds[-1]:
                duty_cycle_value = duty_cycle_values[-1]
            # If temperetarue lies between lowest and highest threshold loop
            # through thresholds and check between which. Set duty cycle
            # accordingly
            else:
                for i in range(len(thresholds)-1):
                    if thresholds[i] <= temperature <= thresholds[i+1]:
                        duty_cycle_value = duty_cycle_values[i+1]
                        break

            # If the duty cycle is set to a higher value then the lowest and
            # therefore a threshold below exists, set from_higher_value to True
            # so it will be checked if a threshold is met next loop.
            if duty_cycle_value > duty_cycle_values[0] \
                    and not self.from_higher_threshold:

                self.from_higher_threshold = True
                self.counter = 0 # Reset "stuck in hysteresis" counter

        # Update self.duty_cycle_value for next loop
        self.duty_cycle_value = duty_cycle_value

        return duty_cycle_value


    def get_temperature(self, path):
        """
        Function to read the temperature out of the file generated by the
        temperature sensor.
        """

        # Open temperature file and assign content to variable
        with open(path, 'r', encoding="utf-8") as f:
            content = f.read()

        # The content has the following format:
        # 59 01 4b 46 7f ff 07 10 a2 : crc=a2 YES
        # 59 01 4b 46 7f ff 07 10 a2 t=21562
        #
        # To get the desired value at the end of the second line,
        # the content is split at the new line character \n first
        # and then at space characters. Then we select the tenth
        # field with the index [9].
        # Afterwards we take the characters from index 2 to the end,
        # convert them to a decimal number, and divide it by 1000
        # to get the correct order of magnitude.
        string_temperature = content.split("\n")[1].split(" ")[9]
        temperature = float(string_temperature[2:])/1000

        return temperature


    def update_metrics(self, temperature, rpm, duty_cycle):
        """
        Function to update metric values.
        """
        
        # Update metrics with given values.
        self.gauge_temperature.set(temperature)
        self.gauge_duty_cycle.set(duty_cycle)
        self.gauge_rpm.set(rpm)