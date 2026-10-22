"""
Centralized logging configuration for the unified MCP server.
Supports both general logging and security audit logging.
"""
import logging
from pathlib import Path


def setup_logging(log_dir: Path = None):
    """
    Configure logging for the MCP server and workers.
    
    Args:
        log_dir: Directory for log files (defaults to current directory)
    
    Returns:
        tuple: (main_logger, audit_logger)
    """
    if log_dir is None:
        log_dir = Path.cwd()
    
    log_dir.mkdir(exist_ok=True)
    
    # === Main Application Logger ===
    main_logger = logging.getLogger('unified_mcp')
    main_logger.setLevel(logging.INFO)
    
    # File handler for general logs
    main_handler = logging.FileHandler(log_dir / 'mcp_server.log')
    main_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    main_logger.addHandler(main_handler)
    
    # Console handler (optional, for development)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(levelname)s - %(message)s')
    )
    main_logger.addHandler(console_handler)
    
    # === Security Audit Logger ===
    audit_logger = logging.getLogger('audit')
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False  # Don't send to root logger
    
    # Audit log handler (separate file for security events)
    audit_handler = logging.FileHandler(log_dir / 'audit.log')
    audit_handler.setFormatter(
        logging.Formatter('%(asctime)s | %(message)s')
    )
    audit_logger.addHandler(audit_handler)
    
    return main_logger, audit_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger for a specific module/worker.
    
    Args:
        name: Logger name (e.g., 'pdf_worker', 'web_worker')
    
    Returns:
        Logger instance
    """
    return logging.getLogger(f'unified_mcp.{name}')


def get_audit_logger() -> logging.Logger:
    """Get the security audit logger."""
    return logging.getLogger('audit')