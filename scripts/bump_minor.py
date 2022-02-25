import fileinput
from os.path import join, dirname


version_file = join(dirname(dirname(__file__)), "mycroft", "version.py")
version_var_name = "OVOS_VERSION_MINOR"
build_var_name = "OVOS_VERSION_BUILD"
alpha_var_name = "OVOS_VERSION_ALPHA"

with open(version_file, "r", encoding="utf-8") as v:
    for line in v.readlines():
        if line.startswith(version_var_name):
            version = int(line.split("=")[-1])
            new_version = int(version) + 1

for line in fileinput.input(version_file, inplace=True):
    if line.startswith(version_var_name):
        print(f"{version_var_name} = {new_version}")
    elif line.startswith(build_var_name):
        print(f"{build_var_name} = 0")
    elif line.startswith(alpha_var_name):
        print(f"{alpha_var_name} = 0")
    else:
        print(line.rstrip('\n'))
