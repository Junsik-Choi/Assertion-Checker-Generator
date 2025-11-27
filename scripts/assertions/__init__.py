"""
Assertion generation plugin package.

How to add a new assertion type (plugin):
- Create a new module file in this package (e.g., my_assertion.py).
- Implement a class derived from BaseAssertionPlugin.
- Define:
  - plugin_name: short identifier (e.g., "counter").
  - sheet_name: Excel sheet name that this plugin consumes.
  - parse(xls_path): read the sheet and return a structured dict.
  - generate_sv(parsed, context): return a list of SV section strings.
- Register the plugin class in registry.py (PLUGINS list) or expose
  a function plugins() in your module that returns [YourPlugin].

Assistant usage hint (for future AI extension requests):
- "Add a plugin for sheet 'my_new_gen' with headers X,Y,Z that should
   generate property templates P; map X->A, Y->B logic as ..."
  The AI should implement a new plugin following BaseAssertionPlugin
  and hook it in registry.PLUGINS.
"""

from .base import BaseAssertionPlugin
from .registry import get_registered_plugins

# Import all plugins to trigger @register decorators
from . import AHB_M
from . import AHB_S
from . import basicAssertion
from . import clockDivider
from . import clockGate
from . import counter
from . import HACT
from . import handshake
from . import HBP
from . import HFP
from . import HSW
from . import pulseWidth
from . import synchronizer
from . import VACT
from . import VBP
from . import VFP
from . import videoSyncAll
from . import VSW
from . import QCH

__all__ = [
    "BaseAssertionPlugin",
    "get_registered_plugins",
]


