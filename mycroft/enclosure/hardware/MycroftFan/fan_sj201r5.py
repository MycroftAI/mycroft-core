import subprocess
import RPi.GPIO as GPIO


class FanControl:
    # hardware speed range is appx 30-255
    # we convert from 0 to 100
    HDW_MIN = 100
    HDW_MAX = 0
    SFW_MIN = 0
    SFW_MAX = 100

    def __init__(self):
        self.fan_speed = 0
        ledpin = 13                             # PWM pin connected to LED
        GPIO.setwarnings(False)                 # disable warnings
        GPIO.setmode(GPIO.BCM)                  # set pin numbering system
        GPIO.setup(ledpin,GPIO.OUT)             # set direction
        self.pi_pwm = GPIO.PWM(ledpin,1000)     # create PWM instance with frequency
        self.pi_pwm.start(0)                    # start PWM of required Duty Cycle 
        self.set_fan_speed(self.fan_speed)

    def execute_cmd(self, cmd):
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        out, err = process.communicate()

        try:
            out = out.decode("utf8")
        except Exception:
            pass

        try:
            err = err.decode("utf8")
        except Exception:
            pass

        return out, err

    def cToF(self, temp):
        return (temp * 1.8) + 32

    def speed_to_hdw_val(self, speed):
        return float(100.0 - (speed % 101))

    def hdw_val_to_speed(self, hdw_val):
        return abs(float(hdw_val - 100.0))

    def hdw_set_speed(self, hdw_speed):
        # provide duty cycle in the range 0-100
        self.pi_pwm.ChangeDutyCycle(hdw_speed)

    def set_fan_speed(self, speed):
        self.fan_speed = self.speed_to_hdw_val(speed)
        self.hdw_set_speed(self.fan_speed)

    def get_fan_speed(self):
        return self.hdw_val_to_speed(self.fan_speed)

    def get_cpu_temp(self):
        cmd = ["cat", "/sys/class/thermal/thermal_zone0/temp"]
        out, err = self.execute_cmd(cmd)
        return float(out.strip()) / 1000
