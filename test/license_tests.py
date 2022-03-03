import unittest
from os.path import dirname, join
from pprint import pprint

from lichecker import LicenseChecker

REQUIREMENTS_DIR = join(dirname(dirname(__file__)), "requirements")

# these packages dont define license in setup.py
# manually verified and injected
license_overrides = {
    "kthread": "MIT",
    'yt-dlp': "Unlicense",
    'pyxdg': 'GPL-2.0',
    'ptyprocess': 'ISC',
    'PyAudio': 'MIT',
    'petact': 'MIT',
    "sonopy": "Apache-2.0",
    "precise-runner": "Apache-2.0",
    'psutil': 'BSD3',
    "vosk": "Apache-2.0"
}
# explicitly allow these packages that would fail otherwise
whitelist = ['ovos-skill-installer']

# validation flags
allow_nonfree = False
allow_viral = False
allow_lgpl = False
allow_unknown = False
allow_unlicense = True
allow_ambiguous = False

PKG_NAME = "ovos-core"


class TestCoreLicensing(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        licheck = LicenseChecker(PKG_NAME,
                                 license_overrides=license_overrides,
                                 whitelisted_packages=whitelist,
                                 allow_ambiguous=allow_ambiguous,
                                 allow_unlicense=allow_unlicense,
                                 allow_unknown=allow_unknown,
                                 allow_viral=allow_viral,
                                 allow_lgpl=allow_lgpl,
                                 allow_nonfree=allow_nonfree)
        print("Package", PKG_NAME)
        print("Version", licheck.version)
        print("License", licheck.license)
        print("Transient Requirements (dependencies of dependencies)")
        pprint(licheck.transient_dependencies)
        self.licheck = licheck

    def test_license_compliance(self):
        print("Package Versions")
        pprint(self.licheck.versions)

        print("Dependency Licenses")
        pprint(self.licheck.licenses)

        self.licheck.validate()


class TestBusLicensing(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        with open(join(REQUIREMENTS_DIR, "extra-bus.txt")) as f:
            pkgs = f.read().split("\n")
        self.pkgs = [p.split("~")[0].split("=")[0].split("<")[0].split(">")[0] for p in pkgs if p]

    def test_license_compliance(self):
        for pkg_name in self.pkgs:
            licheck = LicenseChecker(pkg_name,
                                     license_overrides=license_overrides,
                                     whitelisted_packages=whitelist,
                                     allow_ambiguous=allow_ambiguous,
                                     allow_unlicense=allow_unlicense,
                                     allow_unknown=allow_unknown,
                                     allow_viral=allow_viral,
                                     allow_nonfree=allow_nonfree)
            print("Package", pkg_name)
            print("Version", licheck.version)
            print("License", licheck.license)
            print("Transient Requirements (dependencies of dependencies)")
            pprint(licheck.transient_dependencies)
            self.licheck = licheck

            print("Package Versions")
            pprint(self.licheck.versions)

            print("Dependency Licenses")
            pprint(self.licheck.licenses)

            self.licheck.validate()


class TestGUILicensing(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        with open(join(REQUIREMENTS_DIR, "extra-gui.txt")) as f:
            pkgs = f.read().split("\n")
        self.pkgs = [p.split("~")[0].split("=")[0].split("<")[0].split(">")[0] for p in pkgs if p]

    def test_license_compliance(self):
        for pkg_name in self.pkgs:
            licheck = LicenseChecker(pkg_name,
                                     license_overrides=license_overrides,
                                     whitelisted_packages=whitelist,
                                     allow_ambiguous=allow_ambiguous,
                                     allow_unlicense=allow_unlicense,
                                     allow_unknown=allow_unknown,
                                     allow_viral=allow_viral,
                                     allow_nonfree=allow_nonfree)
            print("Package", pkg_name)
            print("Version", licheck.version)
            print("License", licheck.license)
            print("Transient Requirements (dependencies of dependencies)")
            pprint(licheck.transient_dependencies)
            self.licheck = licheck

            print("Package Versions")
            pprint(self.licheck.versions)

            print("Dependency Licenses")
            pprint(self.licheck.licenses)

            self.licheck.validate()


class TestPHALLicensing(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        with open(join(REQUIREMENTS_DIR, "extra-PHAL.txt")) as f:
            pkgs = f.read().split("\n")
        self.pkgs = [p.split("~")[0].split("=")[0].split("<")[0].split(">")[0] for p in pkgs if p]

    def test_license_compliance(self):
        for pkg_name in self.pkgs:
            licheck = LicenseChecker(pkg_name,
                                     license_overrides=license_overrides,
                                     whitelisted_packages=whitelist,
                                     allow_ambiguous=allow_ambiguous,
                                     allow_unlicense=allow_unlicense,
                                     allow_unknown=allow_unknown,
                                     allow_viral=allow_viral,
                                     allow_nonfree=allow_nonfree)
            print("Package", pkg_name)
            print("Version", licheck.version)
            print("License", licheck.license)
            print("Transient Requirements (dependencies of dependencies)")
            pprint(licheck.transient_dependencies)
            self.licheck = licheck

            print("Package Versions")
            pprint(self.licheck.versions)

            print("Dependency Licenses")
            pprint(self.licheck.licenses)

            self.licheck.validate()


class TestMk1Licensing(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        with open(join(REQUIREMENTS_DIR, "extra-mark1.txt")) as f:
            pkgs = f.read().split("\n")
        self.pkgs = [p.split("~")[0].split("=")[0].split("<")[0].split(">")[0] for p in pkgs if p]

    def test_license_compliance(self):
        for pkg_name in self.pkgs:
            licheck = LicenseChecker(pkg_name,
                                     license_overrides=license_overrides,
                                     whitelisted_packages=whitelist,
                                     allow_ambiguous=allow_ambiguous,
                                     allow_unlicense=allow_unlicense,
                                     allow_unknown=allow_unknown,
                                     allow_viral=allow_viral,
                                     allow_nonfree=allow_nonfree)
            print("Package", pkg_name)
            print("Version", licheck.version)
            print("License", licheck.license)
            print("Transient Requirements (dependencies of dependencies)")
            pprint(licheck.transient_dependencies)
            self.licheck = licheck

            print("Package Versions")
            pprint(self.licheck.versions)

            print("Dependency Licenses")
            pprint(self.licheck.licenses)

            self.licheck.validate()


class TestAudioLicensing(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        with open(join(REQUIREMENTS_DIR, "extra-audiobackend.txt")) as f:
            pkgs = f.read().split("\n")
        self.pkgs = [p.split("~")[0].split("=")[0].split("<")[0].split(">")[0] for p in pkgs
                     if p and not p.strip().startswith("#")]

    def test_license_compliance(self):
        for pkg_name in self.pkgs:
            licheck = LicenseChecker(pkg_name,
                                     license_overrides=license_overrides,
                                     whitelisted_packages=whitelist,
                                     allow_ambiguous=allow_ambiguous,
                                     allow_unlicense=allow_unlicense,
                                     allow_unknown=allow_unknown,
                                     allow_viral=allow_viral,
                                     allow_nonfree=allow_nonfree)
            print("Package", pkg_name)
            print("Version", licheck.version)
            print("License", licheck.license)
            print("Transient Requirements (dependencies of dependencies)")
            pprint(licheck.transient_dependencies)
            self.licheck = licheck

            print("Package Versions")
            pprint(self.licheck.versions)

            print("Dependency Licenses")
            pprint(self.licheck.licenses)

            self.licheck.validate()


class TestSkillsLicensing(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        with open(join(REQUIREMENTS_DIR, "extra-skills.txt")) as f:
            pkgs = f.read().split("\n")
        self.pkgs = [p.split("~")[0].split("=")[0].split("<")[0].split(">")[0] for p in pkgs if p]

    def test_license_compliance(self):
        for pkg_name in self.pkgs:
            licheck = LicenseChecker(pkg_name,
                                     license_overrides=license_overrides,
                                     whitelisted_packages=whitelist,
                                     allow_ambiguous=allow_ambiguous,
                                     allow_unlicense=allow_unlicense,
                                     allow_unknown=allow_unknown,
                                     allow_viral=allow_viral,
                                     allow_nonfree=allow_nonfree)
            print("Package", pkg_name)
            print("Version", licheck.version)
            print("License", licheck.license)
            print("Transient Requirements (dependencies of dependencies)")
            pprint(licheck.transient_dependencies)
            self.licheck = licheck

            print("Package Versions")
            pprint(self.licheck.versions)

            print("Dependency Licenses")
            pprint(self.licheck.licenses)

            self.licheck.validate()


class TestSTTLicensing(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        with open(join(REQUIREMENTS_DIR, "extra-stt.txt")) as f:
            pkgs = f.read().split("\n")
        self.pkgs = [p.split("~")[0].split("=")[0].split("<")[0].split(">")[0] for p in pkgs if p]

    def test_license_compliance(self):
        for pkg_name in self.pkgs:
            licheck = LicenseChecker(pkg_name,
                                     license_overrides=license_overrides,
                                     whitelisted_packages=whitelist,
                                     allow_ambiguous=allow_ambiguous,
                                     allow_unlicense=allow_unlicense,
                                     allow_unknown=allow_unknown,
                                     allow_viral=allow_viral,
                                     allow_nonfree=allow_nonfree)
            print("Package", pkg_name)
            print("Version", licheck.version)
            print("License", licheck.license)
            print("Transient Requirements (dependencies of dependencies)")
            pprint(licheck.transient_dependencies)
            self.licheck = licheck

            print("Package Versions")
            pprint(self.licheck.versions)

            print("Dependency Licenses")
            pprint(self.licheck.licenses)

            self.licheck.validate()


class TestTTSLicensing(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        with open(join(REQUIREMENTS_DIR, "extra-tts.txt")) as f:
            pkgs = f.read().split("\n")
        self.pkgs = [p.split("~")[0].split("=")[0].split("<")[0].split(">")[0] for p in pkgs if p]

    def test_license_compliance(self):
        for pkg_name in self.pkgs:
            licheck = LicenseChecker(pkg_name,
                                     license_overrides=license_overrides,
                                     whitelisted_packages=whitelist,
                                     allow_ambiguous=allow_ambiguous,
                                     allow_unlicense=allow_unlicense,
                                     allow_unknown=allow_unknown,
                                     allow_viral=allow_viral,
                                     allow_nonfree=allow_nonfree)
            print("Package", pkg_name)
            print("Version", licheck.version)
            print("License", licheck.license)
            print("Transient Requirements (dependencies of dependencies)")
            pprint(licheck.transient_dependencies)
            self.licheck = licheck

            print("Package Versions")
            pprint(self.licheck.versions)

            print("Dependency Licenses")
            pprint(self.licheck.licenses)

            self.licheck.validate()
