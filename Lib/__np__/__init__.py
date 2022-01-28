import platform

if platform.system() == "Windows":
    from __np__.windows import *
elif platform.system() == "Linux":
    from __np__.linux import *
