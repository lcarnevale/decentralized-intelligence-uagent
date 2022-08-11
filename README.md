# SARDINE uAgent
The SARDINE project, acronym of "SwARm-based eDge computiNg systEms", aims at building a multi-platform lightweight framework for collaborative nodes with decentralized edge intelligence. Inspired by nature, groups of nodes are organized like a swarm, emphasizing the edge-to-edge continuum of the device-edge-cloud paradigm. This supports a paradigm shift from programming enviroments for individual devices to dynamic and cooperating groups of nodes.

The SARDINE uAgent (read it as SARDINE micro-agent) is the agent version for microcontrollers. The implementation follows the guidelines of the SARDINE design, and it is fully integrated in the SARDINE ecosystem. 

## Why MicroPython?
MicroPython is a lean implementation of Python 3 optimised to run on microcontrollers and in constrained environments. It includes a small subset of the Python standard library, maintaining a minimum compatibility as long as common libraries are used. Relying on Python programming language, it is easy to learn and use, supported by a large community, and suitable for industries and academies.

## Supported Firmware and Boards
The scope of the SARDINE project is performing decentralized edge intelligence. For that reason, we need to rely on a firmware compatible with the most known artificial intelligence frameworks. The choice fell on the custom micropython firmware maintained by Michael O'Cleirigh ([mocleiri](https://github.com/mocleiri) on GitHub), which installs tensorflow lite for micro controllers, supporting ESP32, RP2, and STM32 boards. Please, refer to the main project page ([tensorflow-micropython-examples](https://github.com/mocleiri/tensorflow-micropython-examples)) for issues related with the firmware.