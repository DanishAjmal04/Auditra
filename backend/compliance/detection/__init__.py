from dataclasses import dataclass, field


@dataclass
class Finding:
    """One rule that matched. Several findings for the same event become one incident."""

    code: str
    reason: str
    severity: str = ''            # empty: use the rule's severity
    articles: list = field(default_factory=list)   # empty: use the rule's articles
    kind: str = ''                # empty: use the rule's kind
    shift_reason: bool = False    # the rule fired *because* of the shift (no extra shift points)
    category_reason: bool = False # the rule fired *because* of the data category (no extra category points)
    dedupe_key: str = ''          # set for findings that must not repeat (window, workflow, web visits)
    evidence: list = field(default_factory=list)   # extra Event objects for window findings
