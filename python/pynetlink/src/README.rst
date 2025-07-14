pynetlink - Netlink Python library
===================================
This library acts as an adapter for the Netlink library (YNL) provided with the Linux Kernel. More details about 
Netlink protocol and YNL library can be found at: https://docs.kernel.org/userspace-api/netlink/.


Notes
=====
The required files from YNL (source code, schema and specification files) are being imported into the project from Linux repository. 
This allow to use a newer version of Linux source code with DPLL support in Netlink. The path of these files in Linux repository is 
described in Folder Structure section.

NOTE: After migrating to Linux 6.12 or higher, the required files can be extracted directly from the linux-source 
package in the Debian distribution during the build process, making it unnecessary to keep a copy of these files in the project.



Features / Restrictions
=======================
* Only DPLL specification is implemented. Additional Netlink specifications can be implemented as needed. 
  You can find the list of supported specifications here: https://docs.kernel.org/networking/netlink_spec/index.html.

* Generic Netlink schema is used by default.
  Schema file defines how to translate data sent and received from Netlink into Python compatible data types.

* Netlink allows read and write operations and also receives notifications of changes.

* All pynetlink instances shares a single YNL instance, avoiding loading and parsing spec/schema YAML files for each 
  new instance created. To handle concurrent operations scenario, there is an option to enable dedicated YNL instances.

* Requires CAP_NET_ADMIN privilege.


Folder Structure
================
+ base: contains the YNL library files (imported from Linux repository: tools/net/ynl/lib);
+ common: classes and functions shared by different classes of the project;
+ schemas: YAML schema files used by YNL library (imported from Linux repository: Documentation/netlink);
+ specs: YAML specification files used by YNL library (imported from Linux repository: Documentation/netlink/specs);
+ tests: contains the unit test cases;
+ dpll: contains the classes for DPLL implementation (use separate folders for each specification);


How to use
==========
Create a shared instance for access the DPLL:

    dpll = NetlinkDPLL()

If you need a dedicated instance:

    dpll = NetlinkDPLL(True)

The library has several methods to communicate directly to Netlink to get information about DPLL devices/pins. The 
get_all_pins() method obtains information of the devices and pins and correlate the data into a DPLLPins instance
while get_all_devices() method returns only device part of the information into a DPLLDevices instance.


    try:
        # Obtain all DPLL devices in the system
        devices = dpll.get_all_devices()

        # Print the lock status of all devices
        for device in devices:
            print(f'Device Id: {device.dev_id} - Lock status: {device.lock_status}')
        ...

    except NetlinkException:
        ...

    (or)
    try:
        # Obtain all DPLL pins in the system
        pins = dpll.get_all_pins()

        # Print a list of pins with receive input signal
        print( f'Pins: {pins.filter_by_pin_direction(PinDirection.INPUT)}')

        ...

    except NetlinkException:
        ...

The DPLLDevices and DPLLPins classes offer a set of filters that can be combined to obtain the desired information.

    # Get the devices with status locked and holdover acquired
    devices = devices.filter_by_device_lock_status(LockStatus.LOCKED_AND_HOLDOVER)
    ...

    # Obtain the available GNSS pins in the system 
    gnss = pins.filter_by_pin_type(PinType.GNSS)
               .filter_by_pin_states([PinState.CONNECTED, PinState.SELECTABLE])
    ...

Also they allow to use operators to get the difference/intersection/union/etc between different instances.

    # Get the pins that have been changed since the last read.
    pins_diff = pins_updated - pins_previous
    ...

Other samples of how to use can be found in the test cases.
