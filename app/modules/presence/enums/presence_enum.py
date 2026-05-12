"""Presence enums.

PPTX evidence:
  - Slide 7: *"contrôle de présence par empreintes digitales ou badges magnétiques"*
  - Slide 12: *"terminal de contrôle de présence (empreintes digitales)"*

MVP supports only ESIGN (PIN + tablet device-binding). Biometric / NFC /
manual-greffier methods are reserved (endpoints return 501) until v1.1.
"""

from enum import Enum


class EPresenceMethod(str, Enum):
    """How a presence signature was captured."""
    ESIGN = "ESIGN"                            # PIN + tablet device-binding (MVP)
    BIOMETRIC_FINGERPRINT = "BIOMETRIC_FINGERPRINT"  # v1.1
    BADGE_NFC = "BADGE_NFC"                    # v1.1
    MANUAL_GREFFIER = "MANUAL_GREFFIER"        # v1.1 — greffier override


class EPresenceStatus(str, Enum):
    """Status derived from presence-signature presence + (future) excuse records."""
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    EXCUSE = "EXCUSE"        # future: linked to a justified-absence record
    RETARD = "RETARD"        # future: signed_at after a session-defined cutoff
