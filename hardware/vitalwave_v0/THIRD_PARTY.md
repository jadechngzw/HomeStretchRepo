# Dependencies

Nordic nRF5 SDK 17.1.0 / S140 7.2.0: downloaded from Nordic, used only for Nordic
nRF52840. Refer to firmware/vendor/nRF5_SDK_17.1.0_ddde560/documentation/licenses.txt
and the notices in individual SDK headers/SoftDevice directory. The combined
firmware contains Nordic binary components; preserve applicable license notices
when redistributing it. SDK source is downloaded by tools/setup_sdk.py and not
included in the proposed Git repository.

Python, Tcl/Tk, Bleak (MIT), Matplotlib, NumPy (BSD), SciPy (BSD) and their dependencies retain their own
licenses. requirements.txt pins direct application dependencies; installed package
metadata includes full transitive package/license information.

Official references:
- https://developer.nordicsemi.com/nRF5_SDK/nRF5_SDK_v17.x.x/
- https://bleak.readthedocs.io/en/latest/api/client.html
- https://docs.python.org/3/library/tkinter.html
- https://matplotlib.org/stable/users/explain/figure/backends.html
