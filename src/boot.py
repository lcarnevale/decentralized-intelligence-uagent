import sys

modules = ['protocols', 'drivers']
for module in modules:
    sys.path.append(module)