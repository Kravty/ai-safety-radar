import structlog
import hashlib
import logging
from typing import Any, Dict, Optional
import os

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

class ForensicLogger:
    """
    Secure logger that writes audit logs to a JSONL file.
    Hashes prompts to avoid leaking PII/Injection payloads.
    """
    
    def __init__(self, service_name: str, log_dir: str = "/app/logs"):
        self.service_name = service_name
        self.log_dir = log_dir
        
        # Ensure log dir exists
        os.makedirs(log_dir, exist_ok=True)
        
        self.log_file = os.path.join(log_dir, "audit.jsonl")
        
        # We use a separate file handler for audit logs
        self._audit_logger = logging.getLogger(f"audit_logger_{service_name}")
        self._audit_logger.setLevel(logging.INFO)
        
        # Avoid adding handlers multiple times if instantiated repeatedly
        if not self._audit_logger.handlers:
             handler = logging.FileHandler(self.log_file)
             formatter = logging.Formatter('%(message)s') # JSON renderer does formatting
             handler.setFormatter(formatter)
             self._audit_logger.addHandler(handler)
             
        self._logger = structlog.wrap_logger(self._audit_logger, processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ])

    def _hash_input(self, text: str) -> str:
        """SHA256 hash of the input for correlation without storage."""
        return hashlib.sha256(text.encode()).hexdigest()

    def _sanitize_input(self, text: str, max_len: int = 100) -> str:
        """Truncate input to avoid massive logs."""
        return text[:max_len] + "..." if len(text) > max_len else text

    def log_event(self, event_type: str, severity: str, input_text: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a forensic event.
        
        Args:
            event_type: e.g. "LLM_QUERY", "THREAT_DETECTED", "SYSTEM_START"
            severity: "INFO", "WARN", "CRITICAL"
            input_text: The prompt or input associated (will be hashed)
            details: Extra metadata
        """
        log_entry: Dict[str, Any] = {
            "service_name": self.service_name,
            "event_type": event_type,
            "severity": severity,
        }
        
        if input_text:
            log_entry["input_hash"] = self._hash_input(input_text)
            log_entry["input_preview"] = self._sanitize_input(input_text)
            
        if details:
            log_entry.update(details)
            
        self._logger.info(**log_entry)
