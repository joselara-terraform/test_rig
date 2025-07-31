# XC2_library

Implementation of XC2 communication in python.

## Installation

This command should install the library and all needed dependencies. You will be prompted to use kolibrik login credentials.

```
pip install git+https://gl.kolibrik.net/testing/xc2_library.git
```
```
pip install git+ssh://git@gl.kolibrik.net:222/testing/xc2_library.git
```

If you need to install the package from a specific branch, add @name-of-the-branch at the end of repository name.

```
.../xc2_library@name-of-branch.git
```

Locally installing using pip is possible too. */dir1/dir2/xc2\_library* is the directory containing *pyproject.toml*.

```
pip install /dir1/dir2/xc2_library
```

When run any time onwards this command updates the library package stored on your pc.
## Example 

XC2\_library is used the same way in the old implementation.
```
from xc2.xc2_utils import XC2Bus, UnexpectedAnswerError
```

## Versioning

To update XC2\_library it is necessary to increment version number in *setup.cfg*, otherwise pip install will not update the package.


## Demo
To run demo, you can run xc2_sandbox. But before run, move it to the parent folder.

## XC2 library files
XC2 library consists of these files:

- comm_log.py
- xc2_consts.py
- xc2_device.py
- xc2_dev_cvm24p.py
- xc2_dev_cvm32a.py
- xc2_except.py
- xc2_packets.py
- xc2_sandbox.py
- xc2_utils.py


In this section will be provided short explanation of each file in XC2 library.

## comm_log.py
This file consist of functions and class to log communication. In current file, 
I use functions to parse packet and then send them to the PyQt Widget QTextBrowser.

Class CommFileLog is used to log files in file.

This file can be easily altered to be used in other situations and not just 
projects with PyQt gui.
## xc2_consts.py
This file consists of XC2 constants used in communication like Command numbers, Flags, Packet types ... 
Most of them are in IntEnum shape.

## xc2_device.py
This file contains functions to find serial port with connected Kolibrik device.
It also contains class XC2Device which can represent one general XC2 device. This class is suitable for inheritance.
## xc2_dev_cvm24p.py
This file contains class XC2Cvm24p. 
It is child of XC2Device class and implements some methods, special for cvm24p module.
## xc2_dev_cvm32a.py
This file contains class XC2Cvm32a. 
It is child of XC2Device class and implements some methods, special for cvm32a module.
## xc2_except.py
This file contains definitions of basic xc2_lib exceptions.
## xc2_packets.py
This file contains two dataclasses.

XC2Packet dataclass represents basic xc2_packet.

ModbusPacket dataclass inherits from XC2Packet.
It represents xc2_packet encapsulated in modbus packet, to be compatible with
modbus devices.
## xc2_sandbox.py
**Warning**

**To run this demo, it has to be in parent folder of xc2_library directory.**

## xc2_utils.py
This file has two classes.

XC2Bus handles communication using serial com port.

XC2Protocol handles communication using XC2Bus. 

# Name convention of the methods
XC2Device class (situated in xc2_device.py) contain lots of methods. 
To understand their functionality correctly, there will be short explanation.

Read/Write
- These methods call XC2Device and read from/ write to their registry. 
- These methods include transaction on XC2Bus.

Get/Set
- These methods operate with datas ridden from the xc2 device, witch are already stored in computer memory in XC2Device class.
- If you are using these methods, there is no communication with xc2 device.
- Get method usually returns the value.

Print
- These methods print content on the console.

# How to install xc2_library
Library can be used as git submodule. To download it use following steps. 
1. Add submodule to existing git project using command. 
```ruby
git submodule add https://gl.kolibrik.net/testing/xc2_library.git
```
2. Then import what you need from the library using standard import statement. In code line you can see example how to import XC2Cvm32a class.
```ruby
from xc2_library.xc2_dev_cvm32a import XC2Cvm32a
```
3. To update library to latest version use this command
```ruby
git submodule update --remote
```

