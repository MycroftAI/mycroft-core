import unittest
from pprint import pprint

from lichecker import LicenseChecker

# these packages dont define license in setup.py
# manually verified and injected
license_overrides = {
    "kthread": "MIT",
    'yt-dlp': "Unlicense",
    'pyxdg': 'GPL-2.0',
    'ptyprocess': 'ISC license',
    'psutil': 'BSD3'
}
# explicitly allow these packages that would fail otherwise
whitelist = []

# validation flags
allow_nonfree = False
allow_viral = False
allow_unknown = False
allow_unlicense = True
allow_ambiguous = False

pkg_name = "ovos-core"


class TestLicensing(unittest.TestCase):
    @classmethod
    def setUpClass(self):
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

    def test_license_compliance(self):
        print("Package Versions")
        pprint(self.licheck.versions)

        print("Dependency Licenses")
        pprint(self.licheck.licenses)

        self.licheck.validate()
