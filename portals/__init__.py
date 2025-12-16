"""Portal adapter factory and exports."""

import logging
from typing import Any, Dict

from portals.base import PortalAdapter

logger = logging.getLogger(__name__)


def get_adapter(config: Dict[str, Any]) -> PortalAdapter:
    """
    Factory function to get appropriate portal adapter.

    Args:
        config: Configuration dictionary from config.json

    Returns:
        Portal adapter instance (WillhabenAdapter or ImmoscoutAdapter)

    Raises:
        ValueError: If portal is not supported

    Example:
        >>> config = {"portal": "willhaben", "postal_codes": ["1010"], ...}
        >>> adapter = get_adapter(config)
        >>> print(adapter.get_portal_name())
        "willhaben"
    """
    portal = config.get("portal", "willhaben").lower()

    if portal == "willhaben":
        from portals.willhaben.adapter import WillhabenAdapter

        logger.info("Initializing Willhaben adapter")
        return WillhabenAdapter(config)

    elif portal == "immoscout":
        from portals.immoscout.adapter import ImmoscoutAdapter

        logger.info(
            "Initializing ImmoscoutAdapter (BEST EFFORT implementation) - "
            "may require refinement based on actual site structure"
        )
        return ImmoscoutAdapter(config)

    else:
        raise ValueError(
            f"Unsupported portal: {portal}. "
            f"Supported portals: 'willhaben', 'immoscout'"
        )


__all__ = ["get_adapter", "PortalAdapter"]
