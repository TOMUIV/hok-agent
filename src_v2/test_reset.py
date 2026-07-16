import sys
sys.stdout.reconfigure(encoding='utf-8')
import hok.hok1v1.lib.interface as interface
from hok.hok1v1.env1v1 import interface_default_config
lib = interface.Interface()
print("init...", flush=True)
lib.Init(interface_default_config)
print("Init OK - calling Reset...", flush=True)
lib.Reset(True, [])
print("Reset OK", flush=True)
