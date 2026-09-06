import ipaddress
import re
import socket
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

from app.config import settings


SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----", re.I),
    re.compile(r"(?i)(api[_-]?key|secret|password|passwd|pwd|token)\s*[:=]\s*['\"]?[^\s'\"]{12,}"),
    re.compile(r"(?i)aws_access_key_id\s*=\s*AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{40}"),
    re.compile(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9._\-]+"),
]

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore (all )?(previous|prior|above) instructions"),
    re.compile(r"(?i)reveal (the )?(system|developer) prompt"),
    re.compile(r"(?i)you are now"),
    re.compile(r"(?i)do not obey"),
    re.compile(r"(?i)exfiltrate|bypass|jailbreak"),
]


@dataclass
class GuardrailResult:
    """Simple allow/block result with a human-readable reason."""

    allowed: bool
    reason: str = ""


def contains_secret(text: str) -> bool:
    """Return True when text appears to contain secrets or credentials."""
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def redact_secrets(text: str) -> str:
    """Replace obvious secrets with a redaction marker."""
    if not settings.redact_secrets:
        return text

    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return redacted


def has_prompt_injection(text: str) -> bool:
    """Flag obvious prompt-injection language in retrieved content."""
    return any(pattern.search(text) for pattern in PROMPT_INJECTION_PATTERNS)


def normalize_domain(hostname: str | None) -> str:
    """Normalize hostnames for allowlist and blocklist checks."""
    return (hostname or "").strip().lower().rstrip(".")


def domain_matches(hostname: str, domains: Iterable[str]) -> bool:
    """Allow exact domain or subdomain matches."""
    host = normalize_domain(hostname)
    for domain in domains:
        item = normalize_domain(domain)
        if host == item or host.endswith(f".{item}"):
            return True
    return False


def _hostname_resolves_to_private_ip(hostname: str) -> bool:
    """Resolve hostname and detect private, loopback, or link-local IPs."""
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False

    for address in addresses:
        ip_text = address[4][0]
        try:
            ip = ipaddress.ip_address(ip_text)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            return True
    return False


def validate_url_for_crawl(url: str, seed_host: str | None = None) -> GuardrailResult:
    """Reject unsafe URLs before making outbound HTTP requests."""
    parsed = urlparse(url)
    hostname = normalize_domain(parsed.hostname)

    if parsed.scheme not in {"http", "https"}:
        return GuardrailResult(False, "Only HTTP and HTTPS URLs are allowed.")

    if not hostname:
        return GuardrailResult(False, "URL is missing a hostname.")

    if domain_matches(hostname, settings.blocked_domains()):
        return GuardrailResult(False, f"Domain is blocked: {hostname}")

    allowed_domains = settings.allowed_domains()
    if allowed_domains and not domain_matches(hostname, allowed_domains):
        return GuardrailResult(False, f"Domain is not in the allowlist: {hostname}")

    if not allowed_domains and seed_host and hostname != normalize_domain(seed_host):
        return GuardrailResult(False, "Cross-domain crawling is disabled by default.")

    if not settings.allow_private_network_crawl and _hostname_resolves_to_private_ip(hostname):
        return GuardrailResult(False, "Private, loopback, or link-local destinations are blocked.")

    return GuardrailResult(True, "")


def validate_question(question: str) -> GuardrailResult:
    """Block clearly unsafe or oversized user questions."""
    if len(question) > settings.max_question_chars:
        return GuardrailResult(False, "Question is too long.")

    if contains_secret(question):
        return GuardrailResult(False, "Question appears to contain a secret or credential.")

    return GuardrailResult(True, "")
