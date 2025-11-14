from __future__ import annotations

from typing import List, Type

from .base import BaseAssertionPlugin


PLUGINS: List[Type[BaseAssertionPlugin]] = []


def register(plugin_cls: Type[BaseAssertionPlugin]):
    if plugin_cls not in PLUGINS:
        PLUGINS.append(plugin_cls)
    return plugin_cls


def get_registered_plugins() -> List[Type[BaseAssertionPlugin]]:
    try:
        from . import counter  # noqa: F401
        from . import handshake  # noqa: F401
        from . import pulseWidth # noqa: F401
        from . import HSW # noqa: F401
        from . import HBP # noqa: F401
        from . import HACT # noqa: F401
        from . import HFP # noqa: F401
        from . import VFP # noqa: F401
        from . import VSW # noqa: F401
        from . import VBP # noqa: F401        
    except Exception:
        pass
    return list(PLUGINS)


