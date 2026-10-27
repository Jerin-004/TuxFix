"""
TuxFix safety module.

Responsibilities:
- Classify commands by risk level.
- Flag destructive or privileged operations.
- Detect prompt-injection attempts in user-supplied text.
- Enforce the principle that TuxFix never executes commands automatically.
"""
from __future__ import annotations

import re
import logging
from typing import NamedTuple

from .schemas import RiskLevel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Risk classification rules
# ---------------------------------------------------------------------------

# Patterns that indicate read-only or low-risk operations
_READ_ONLY_PATTERNS = [
    r"^\s*(ls|lsblk|lsusb|lspci|lscpu|lshw|lsmod)\b",
    r"^\s*cat\s+/(?:proc|sys|etc)/",
    r"^\s*(dmesg|journalctl|systemctl\s+status|df|du\b|free|top|htop|ps|ip\s+addr|ip\s+route|ifconfig|ping|nslookup|dig|host|uname|whoami|id|groups|getent|find\s+.*-maxdepth|stat|file|which|type|echo|printenv|env|locale|date|uptime)\b",
    r"^\s*systemctl\s+(status|list-units|list-timers|is-active|is-enabled|show)\b",
    r"^\s*(apt-get|apt|dnf|yum|pacman|zypper)\s+(list|search|show|info|check|verify)\b",
    r"^\s*dpkg\s+(-l|-s|-L|-S|--list|--status|--listfiles|--search)\b",
    r"^\s*rpm\s+(-q|-qa|-qi|-ql|-qf)\b",
    r"^\s*nmcli\s+(dev\s+show|con\s+show)\b",
    r"^\s*netstat\b",
    r"^\s*ss\b",
    r"^\s*blkid\b",
    r"^\s*fdisk\s+-l\b",
    r"^\s*parted\s+.*print\b",
    r"^\s*mount\b(?!\s+\w)",  # bare mount (list)
    r"^\s*strace\b",
    r"^\s*ltrace\b",
    r"^\s*ldd\b",
    r"^\s*nm\b",
    r"^\s*readelf\b",
    r"^\s*objdump\b",
    r"^\s*ldconfig\s+-p\b",
    r"^\s*update-alternatives\s+--list\b",
]

# Medium risk — modifies config or restarts services
# Note: patterns use (?:sudo\s+)? prefix to match with or without sudo
_MEDIUM_PATTERNS = [
    r"^\s*(?:sudo\s+)?systemctl\s+(start|stop|restart|reload|enable|disable)\b",
    r"^\s*(?:sudo\s+)?(?:apt-get|apt)\s+(install|remove|purge|autoremove|upgrade)\b",
    r"^\s*(?:sudo\s+)?(?:dnf|yum)\s+(install|remove|update|upgrade)\b",
    r"^\s*(?:sudo\s+)?pacman\s+-S\b",
    r"^\s*(?:sudo\s+)?pip\s+(install|uninstall)\b",
    r"^\s*(?:sudo\s+)?chmod\b",
    r"^\s*(?:sudo\s+)?chown\b",
    r"^\s*(?:sudo\s+)?usermod\b",
    r"^\s*(?:sudo\s+)?groupmod\b",
    r"^\s*(?:sudo\s+)?useradd\b",
    r"^\s*(?:sudo\s+)?userdel\b",
    r"^\s*(?:sudo\s+)?passwd\b",
    r"^\s*(?:sudo\s+)?modprobe\b",
    r"^\s*(?:sudo\s+)?rmmod\b",
    r"^\s*(?:sudo\s+)?insmod\b",
    r"^\s*(?:sudo\s+)?sysctl\b",
    r"^\s*(?:sudo\s+)?nmcli\s+(con\s+(up|down|modify|add|delete)|dev\s+(connect|disconnect|set))\b",
    r"^\s*(?:sudo\s+)?(ip\s+(link|addr|route)\s+(add|del|set|change|flush))\b",
    r"^\s*(?:sudo\s+)?iptables\b",
    r"^\s*(?:sudo\s+)?ufw\b",
    r"^\s*(?:sudo\s+)?firewall-cmd\b",
    r"^\s*(?:sudo\s+)?ln\s+-s\b",
    r"^\s*(?:sudo\s+)?ldconfig\b(?!\s+-p)",
    r"^\s*(?:sudo\s+)?update-alternatives\b",
    r"^\s*(?:sudo\s+)?dpkg\s+(-i|--install|--configure|-P|--purge)\b",
    r"^\s*(?:sudo\s+)?rpm\s+(-i|-U|-e|--install|--upgrade|--erase)\b",
]

# High risk — data loss potential or major system change
_HIGH_PATTERNS = [
    r"\brm\s+.*-[rRf]",
    r"^\s*rm\b",
    r"^\s*dd\b",
    r"^\s*mkfs\b",
    r"^\s*fdisk\b(?!\s+-l)",
    r"^\s*parted\b(?!.*print)",
    r"^\s*gdisk\b",
    r"^\s*wipefs\b",
    r"^\s*shred\b",
    r"^\s*truncate\b",
    r">\s*/dev/[sh]d",
    r"^\s*mv\s+.*\s+/",
    r"^\s*grub-install\b",
    r"^\s*update-grub\b",
    r"^\s*grub2-install\b",
    r"^\s*mkinitcpio\b",
    r"^\s*dracut\b",
    r"^\s*kernel-install\b",
]

# Critical — irreversible, dangerous, or plainly malicious patterns
_CRITICAL_PATTERNS = [
    r"rm\s+-rf\s+/",
    r":\s*\(\s*\)\s*\{",           # fork bomb
    r">\s*/dev/sd[a-z](?!\d)",     # overwrite raw disk
    r"mkfs\s+/dev/sd[a-z](?!\d)",
    r"\|\s*bash\b",                 # curl | bash
    r"\|\s*sh\b",
    r"wget\s+.*\|",
    r"curl\s+.*\|",
    r"chmod\s+777\s+/",
    r"sudo\s+rm\s+-rf\s+/",
    r"dd\s+if=.*\s+of=/dev/sd[a-z](?!\d)",
]

# Patterns that suggest privilege escalation
_SUDO_PATTERNS = [
    r"\bsudo\b",
    r"\bsu\s+-\b",
    r"\bsu\s+root\b",
    r"\bpkexec\b",
    r"\bdoas\b",
]


class CommandClassification(NamedTuple):
    risk_level: RiskLevel
    is_destructive: bool
    requires_sudo: bool
    warnings: list[str]


def classify_command(command: str) -> CommandClassification:
    """
    Classify a shell command's risk level and properties.
    Returns a CommandClassification namedtuple.
    """
    warnings: list[str] = []
    cmd = command.strip()

    # Check critical first
    for pat in _CRITICAL_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            warnings.append("CRITICAL: This command could cause irreversible system damage.")
            return CommandClassification(
                risk_level=RiskLevel.CRITICAL,
                is_destructive=True,
                requires_sudo=bool(re.search(r"\bsudo\b", cmd)),
                warnings=warnings,
            )

    # Check high
    for pat in _HIGH_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            warnings.append("HIGH RISK: This command modifies disk, filesystem, or boot configuration.")
            requires_sudo = any(re.search(p, cmd, re.IGNORECASE) for p in _SUDO_PATTERNS)
            return CommandClassification(
                risk_level=RiskLevel.HIGH,
                is_destructive=True,
                requires_sudo=requires_sudo,
                warnings=warnings,
            )

    # Check medium
    for pat in _MEDIUM_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            requires_sudo = any(re.search(p, cmd, re.IGNORECASE) for p in _SUDO_PATTERNS)
            return CommandClassification(
                risk_level=RiskLevel.MEDIUM,
                is_destructive=False,
                requires_sudo=requires_sudo,
                warnings=warnings,
            )

    # Check read-only
    for pat in _READ_ONLY_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return CommandClassification(
                risk_level=RiskLevel.READ_ONLY,
                is_destructive=False,
                requires_sudo=False,
                warnings=warnings,
            )

    # Default: low risk (unknown / benign-looking)
    requires_sudo = any(re.search(p, cmd, re.IGNORECASE) for p in _SUDO_PATTERNS)
    return CommandClassification(
        risk_level=RiskLevel.LOW,
        is_destructive=False,
        requires_sudo=requires_sudo,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Prompt injection detection
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"forget\s+(everything|all)\s+above",
    r"you\s+are\s+now\s+a\s+different",
    r"disregard\s+(your\s+)?(previous\s+)?instructions?",
    r"act\s+as\s+if\s+you\s+have\s+no\s+(restrictions?|rules?|guidelines?)",
    r"new\s+system\s+prompt",
    r"override\s+(your\s+)?(system\s+)?instructions?",
    r"print\s+your\s+system\s+prompt",
    r"reveal\s+your\s+instructions?",
    r"DAN\s+mode",
    r"jailbreak",
    r"pretend\s+you\s+are",
    r"from\s+now\s+on\s+(you\s+are|act\s+as)",
]


def detect_prompt_injection(text: str) -> list[str]:
    """
    Scan user-supplied text for patterns that look like prompt injection attempts.
    Returns a list of warning strings (empty list = no suspicious patterns found).
    """
    found: list[str] = []
    lower = text.lower()
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, lower):
            found.append(
                f"Possible prompt injection detected (pattern: '{pat}'). "
                "This text will be treated as untrusted diagnostic data only."
            )
    return found


def sanitize_for_export(data: dict) -> dict:
    """
    Redact values that look like secrets from exported data.
    Operates on string values only; does not recurse into nested dicts by default.
    """
    sensitive_keys = {"password", "token", "secret", "key", "credential", "api_key", "passwd"}
    result = {}
    for k, v in data.items():
        if any(sk in k.lower() for sk in sensitive_keys):
            result[k] = "[REDACTED]"
        elif isinstance(v, str) and re.search(
            r"(password|token|secret|private_key)\s*[:=]\s*\S+", v, re.IGNORECASE
        ):
            result[k] = re.sub(
                r"(password|token|secret|private_key)\s*[:=]\s*\S+",
                r"\1=[REDACTED]",
                v,
                flags=re.IGNORECASE,
            )
        else:
            result[k] = v
    return result


SAFETY_DISCLAIMER = (
    "⚠️  **Safety Notice**: TuxFix provides diagnostic suggestions only. "
    "It does **not** execute any commands automatically. "
    "Review every command carefully before running it in your terminal. "
    "Commands marked HIGH or CRITICAL risk require independent human judgment. "
    "LLM-generated output can be incorrect — treat it as advisory, not authoritative."
)
