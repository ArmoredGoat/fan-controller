# DIY Raspberry Pi Fan Controller

(Work in progress)

Disclaimer: At no means am I an expert in electronics or cooling solutions. I am just a guy with an internet connection that somehow learned to read as child. If I did something wrong or there are better ways to solve the problems mentioned below, please let me know.

## About this project

### What is this project?

This project provides documentation, wiring schemes and scripts to build an independent fan controller with a Raspberry Pi (or similar device). List of features and necessary materials below. 

### Why did I do all this stuff?

I have a server rack at home. Right now, it is standing outside my living space in an attic. Therefore, noise (and temperature) has been never a topic until now. In the near future, it is quite possible that my server rack will reside right next to my desk. So, I had to come up with a solution for noise, dust and cooling. As bought options are quite expensive and unflexible, I opted to build it myself. Most parts were already lying around.
Now I have eight fans, four on the bottom (with dust filters) and top each, spinning dead silently in idle and are, when spun up, not any louder then my desktop computer or laptop.

## Features

- Measuring temperatur via sensor (`DS18B20` or similar)
- Controlling 4-pin PWM fans or fan hubs
	- Read RPM of fan
	- Control fan speed with PWM signal
- Exporting data with Prometheus to be able to monitor fans with Grafana or similar
- Configuration of fan speed and temperature thresholds through simple config file

Please note:

In the current state, this controller only reads the fan speed through the RPM pin and sets fan speed with PWM. It is NOT capable to power a common 12V and relies on an external power source.

## Required Parts

- Raspberry Pi or similar device (duh...)
- Temperature sensor (`DS18B20`, for example)
- Level Shifter to raise PWM signal from 3.3V to 5V ([Something like these](https://www.makershop.de/module/schnittstellen/4-kanal-konverter/))
- Two resistors (in my case 5.1kΩ and 10kΩ but anything above 5kΩ should suffice)
- Breadboard or something similar to hold the parts
- Jumper wires to connect everything
- 4-pin PWM fans (I used Noctua's [NF-P12 redux-1300 PWM](https://noctua.at/de/nf-p12-redux-1300-pwm))
- Fan hub to connect more fans to the controller (I used Arctic's [Case Fan Hub](https://www.arctic.de/Case-Fan-Hub/ACFAN00175A))
- Anything to power the fans. As my hub use 15-pin SATA to receive power, I used a power supply to 4-pin MOLEX and an adapter from MOLEX to 15-pin SATA (e.g. something like [this](https://www.mindfactory.de/product_info.php/Phobya-Externes-Netzteil-230V-auf-4Pin-Molex-34-Watt-inkl--Euro-UK-Stec_1129317.html) and [that](https://www.satchef.de/15-cm-Adapter-Kabel-4-pin-Molex-auf-15-pin-SATA-Stecker-schwarz)). After two months nothing caught on fire, yet.

## Wiring/Schematics

As mentioned above and seen below, I have little experience in electronics and schematics, but I hope it is comprehensible. If not, please let me know.

![](https://github.com/ArmoredGoat/fan-controller/assets/89848245/35191cbf-3e8f-4dd6-b3df-55f65e30a922)

In the current state, it is important that the fan controller and the reporting fan has a common ground. Otherwise, the RPM of the fan is not properly read on the third pin, an open collector. I used the [following schematic](https://electronics.stackexchange.com/questions/153846/arduino-how-to-read-and-control-the-speed-of-a-12v-four-wire-fan/153882#153882) as a reference. To address this problem, instead of connecting the first fan (the reporting fan in this case) directly to the slot on the fan hub I put jumper wires in between and broke out the ground wire to the shared ground on the bread board. 

![](https://github.com/ArmoredGoat/fan-controller/assets/89848245/7629da68-416d-4c30-8336-261ae8251ff9)

## Installation

The script is designed not to require root privileges (except installation of missing packages and enabling drivers). In addition, [lingering](https://www.freedesktop.org/software/systemd/man/latest/loginctl.html#enable-linger%20USER%E2%80%A6) will be enabled for the used user. This is to make sure that the non-root user service for the fan controller will be started on boot without logging in.

This process has been tested on a fresh [Raspberry Pi OS Lite](https://www.raspberrypi.com/software/operating-systems/) install on a Raspberry Pi Zero. Make sure it is connected to the internet.

1. Enable 1-Wire-Interface

To be able to read data from your `DS18B20` sensor you have to enable the 1-Wire-Interface. First, open up `/boot/config.txt` on your RPi:

```bash
sudo nano /boot/config.txt
````

Add the following line to the end of the file:

```bash
dtoverlay=w1-gpio,gpiopin=23 # SET OWN PIN NUMBER IF WANTED
```

Insert your chosen GPIO pin to which you want to connect your temperature sensor. Default is pin 4. In my case, I took pin 23. Check out [pinout.xyz](https://pinout.xyz/pinout/1_wire) for more information. The change only takes effect after a restart.

2. Clone `git` repository

First, make sure `git` is installed:

```bash
sudo apt install git
```

Clone `git` repository and move into it:

```bash
git clone https://github.com/ArmoredGoat/fan-controller
cd fan-controller
```

3. Install fan-controller

To install fan-controller run `install.sh`. `install.sh` will check for missing Python packages (numpy, pigpio, and prometheus_client), add a user service at `~/.config/systemd/user/`, and create a config file at `~/.config/fan-controller`.

To run `install.sh` enter the following commands:

```bash
chmod +x install.sh # Make install.sh executable
./install.sh # Execute install.sh
```

After the installation, the service will not be started yet, but it will be enabled to be started on the next boot.

3.1. Edit configuration file

You can find the configuration file at `~/.config/fan-controller/fan-controller.conf`.

```bash
nano ~/.config/fan-controller/fan-controller.conf
```

Edit to your liking. (Documentation in the config file should be sufficient.)

3.2 Enable pigpio.service


The used Python library to control of the GPIO pins is [pigpio](https://abyz.me.uk/rpi/pigpio/). To make sure the service is up and running after the following reboot, it has to be enabled.

```bash
sudo systemctl enable pigpiod.service
```

3. Restart

After a restart, the changes from step 1 will be applied and previously enabled services will be started.
