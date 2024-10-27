import os
import sys
import sysconfig

# Make the standard wheel, the real wheel module.
# Need to keep a reference alive, or the module will loose all attributes.
if "wheel" in sys.modules:
    _this_module = sys.modules["wheel"]
    del sys.modules["wheel"]

real_wheel_dir = os.path.join(os.path.dirname(__file__), "site-packages")
sys.path.insert(0, real_wheel_dir)
import wheel as _wheel

del sys.path[0]
sys.modules["wheel"] = _wheel

def our_generic_abi():
    return [wheel.vendored.packaging.tags._normalize_string(sysconfig.get_config_var("SOABI"))]

import wheel.vendored.packaging.tags
wheel.vendored.packaging.tags._generic_abi = our_generic_abi

