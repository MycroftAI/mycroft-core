import subprocess


class EnclosureCapabilities:
    """
    we want to know about any keyboards,
    mice, and screens attached to the system.

    Usage:
        hardware_capabilities = EnclosureCapabilities()
        print("Kbds:%s" % (hardware_capabilities.keyboards,))
        print("Mice:%s" % (hardware_capabilities.mice,))
        print("Screens:%s" % (hardware_capabilities.screens,))

    Example Mark2 Output with mouse and keyboard plugged in:
        (.venv) mycroft@localhost:~$ python hdw_test.py
        Kbds:[{'name': 'Lite-On Technology Corp. USB Multimedia Keyboard',
                       'extra': ''}]
        Mice:[{'name': 'PIXART USB OPTICAL MOUSE', 'extra': ''},
              {'name': 'FT5406 memory based driver', 'extra': 'Touch Screen'}]
        Screens:[{'name': 'DRM emulated', 'resolution': '800,480', 'pel_size': '32',
                  'extra': ''}]

    Example Mark2 Output with nothing plugged in.
        (.venv) mycroft@localhost:~$ python hdw_test.py
        Kbds:[]
        Mice:[{'name': 'FT5406 memory based driver', 'extra': 'Touch Screen'}]
        Screens:[{'name': 'DRM emulated', 'resolution': '800,480', 'pel_size': '32',
                  'extra': ''}]

    """

    name_line = 'N: Name="'
    keyboard_line = "H: Handlers=sysrq kbd"
    mouse_line = "H: Handlers=mouse"

    def __init__(self):
        self.mice = []
        self.keyboards = []
        self.screens = []

        self.caps = self._get_capabilities()

        self.mice = self.caps["mice"]
        self.keyboards = self.caps["keyboards"]
        self.screens = self.caps["screens"]

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

    def _get_capabilities(self):
        # query input devices

        cmd = ["cat", "/proc/bus/input/devices"]
        out, err = self.execute_cmd(cmd)

        if err:
            # print("Error trying to read input devices:%s" % (err,))
            pass
        else:
            for line in out.split("\n"):
                if line != "":
                    if line.startswith(self.name_line):
                        dev_name = line[len(self.name_line):]
                        dev_name = dev_name[:-1]
                    elif line.startswith(self.keyboard_line):
                        kbd_obj = {"name": dev_name, "extra": ""}
                        self.keyboards.append(kbd_obj)
                    elif line.startswith(self.mouse_line):
                        extra = ""
                        if dev_name.startswith("FT5406 memory based driver"):
                            extra = "Touch Screen"
                        mouse_obj = {"name": dev_name, "extra": extra}
                        self.mice.append(mouse_obj)

        # query output devices.

        screen_name = ""
        cmd = ["cat", "/sys/class/graphics/fb0/name"]
        out, err = self.execute_cmd(cmd)

        if err:
            # print("Error trying to read output devices:%s" % (err,))
            pass
        else:
            screen_name = out.strip()

        screen_resolution = ""
        cmd = ["cat", "/sys/class/graphics/fb0/virtual_size"]
        out, err = self.execute_cmd(cmd)

        if err:
            # print("Error trying to read output devices:%s" % (err,))
            pass
        else:
            screen_resolution = out.strip()

        screen_depth = ""
        cmd = ["cat", "/sys/class/graphics/fb0/bits_per_pixel"]
        out, err = self.execute_cmd(cmd)

        if err:
            # print("Error trying to read output devices:%s" % (err,))
            pass
        else:
            screen_depth = out.strip()

        if not (screen_name == "" and screen_resolution == ""):
            self.screens = [
                {
                    "name": screen_name,
                    "resolution": screen_resolution,
                    "pel_size": screen_depth,
                    "extra": "",
                }
            ]

        capabilities = {
            "keyboards": self.keyboards,
            "mice": self.mice,
            "screens": self.screens,
        }
        return capabilities


if __name__ == "__main__":
    hardware_capabilities = EnclosureCapabilities()
    print("Kbds:%s" % (hardware_capabilities.keyboards,))
    print("Mice:%s" % (hardware_capabilities.mice,))
    print("Screens:%s" % (hardware_capabilities.screens,))
