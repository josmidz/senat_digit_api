"""Vote module enums.

PPTX-anchored constraints (memory: senat_pptx_requirements):
  - Four ballot choices (slide 15): POUR | CONTRE | ABSTENTION | NPV
  - Mid-scrutin type change allowed (slide 15) — but only BEFORE first ballot
    is cast (otherwise breaks the secret-vote sealed-key invariant)
  - Pouvoirs/proxies (slide 15) — VoteBallotModel.weight + VoteProxyModel
  - Two majority families (slide 15): RELATIVE | ABSOLUE | DEUX_TIERS | CUSTOM
  - Two ballot types (slide 15): UNINOMINAL | LISTE  (+ OUI_NON for binary votes)
"""

from enum import Enum


class EVoteChoice(str, Enum):
    """Four-option ballot — PPTX slide 15 verbatim. NPV = "Ne prend pas part au vote".

    NPV counts toward quorum but NOT toward majority (règlement intérieur — TBC).
    """
    POUR = "POUR"
    CONTRE = "CONTRE"
    ABSTENTION = "ABSTENTION"
    NE_PREND_PAS_PART_AU_VOTE = "NE_PREND_PAS_PART_AU_VOTE"


class EVoteBallotType(str, Enum):
    UNINOMINAL = "UNINOMINAL"
    LISTE = "LISTE"
    OUI_NON = "OUI_NON"


class EVoteMajorityType(str, Enum):
    RELATIVE = "RELATIVE"
    ABSOLUE = "ABSOLUE"
    DEUX_TIERS = "DEUX_TIERS"
    CUSTOM = "CUSTOM"


class EVoteStatus(str, Enum):
    """Lifecycle FSM for a vote (scrutin).

    Allowed transitions (enforced by `VoteService`):
      PROJET   → OUVERT
      OUVERT   → SUSPENDU | CLOS
      SUSPENDU → OUVERT   | CLOS
      CLOS     → VALIDE   | ANNULE
      VALIDE   → (terminal)
      ANNULE   → (terminal)
    """
    PROJET = "PROJET"
    OUVERT = "OUVERT"
    SUSPENDU = "SUSPENDU"
    CLOS = "CLOS"
    VALIDE = "VALIDE"
    ANNULE = "ANNULE"


VOTE_STATUS_TRANSITIONS: dict[EVoteStatus, frozenset[EVoteStatus]] = {
    EVoteStatus.PROJET: frozenset({EVoteStatus.OUVERT}),
    EVoteStatus.OUVERT: frozenset({EVoteStatus.SUSPENDU, EVoteStatus.CLOS}),
    EVoteStatus.SUSPENDU: frozenset({EVoteStatus.OUVERT, EVoteStatus.CLOS}),
    EVoteStatus.CLOS: frozenset({EVoteStatus.VALIDE, EVoteStatus.ANNULE}),
    EVoteStatus.VALIDE: frozenset(),
    EVoteStatus.ANNULE: frozenset(),
}
