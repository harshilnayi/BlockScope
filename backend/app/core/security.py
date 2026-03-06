"""
BlockScope Security Middleware
Implements security headers, file validation, XSS protection, and more
"""

import re
from pathlib import Path
from typing import Callable, List, Optional

from app.core.config import settings
from fastapi import Request, Response, UploadFile
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

# ==================== Security Headers Middleware ====================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    Implements OWASP security best practices.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response"""
        response = await call_next(request)

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Adjust for your needs
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Strict Transport Security (HTTPS only)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Remove server information
        response.headers.pop("Server", None)

        return response


# ==================== File Validation ====================


class FileValidator:
    """
    Validate uploaded files for security.
    Checks file size, extension, MIME type, and content.
    """

    def __init__(
        self, max_size: int = settings.MAX_UPLOAD_SIZE, allowed_extensions: List[str] = None
    ):
        self.max_size = max_size
        self.allowed_extensions = allowed_extensions or settings.ALLOWED_EXTENSIONS

    def validate_filename(self, filename: str) -> tuple[bool, Optional[str]]:
        """
        Validate filename for security issues.

        Args:
            filename: Filename to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        # Check length
        if len(filename) > settings.MAX_FILENAME_LENGTH:
            return False, f"Filename too long (max {settings.MAX_FILENAME_LENGTH} chars)"

        # Check for path traversal attempts
        if ".." in filename or "/" in filename or "\\" in filename:
            return False, "Invalid filename: path traversal detected"

        # Check for null bytes
        if "\x00" in filename:
            return False, "Invalid filename: null byte detected"

        # Check for suspicious characters
        if re.search(r'[<>:"|?*]', filename):
            return False, "Invalid filename: contains illegal characters"

        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in self.allowed_extensions:
            return False, f"Invalid file type. Allowed: {', '.join(self.allowed_extensions)}"

        return True, None

    def validate_size(self, file: UploadFile) -> tuple[bool, Optional[str]]:
        """
        Validate file size.

        Args:
            file: Uploaded file

        Returns:
            tuple: (is_valid, error_message)
        """
        # Check size if available
        if hasattr(file, "size") and file.size:
            if file.size > self.max_size:
                max_mb = self.max_size / (1024 * 1024)
                return False, f"File too large (max {max_mb:.1f}MB)"

        return True, None

    def validate_mime_type(self, file: UploadFile) -> tuple[bool, Optional[str]]:
        """
        Validate MIME type.

        Args:
            file: Uploaded file

        Returns:
            tuple: (is_valid, error_message)
        """
        # Check MIME type if available
        if file.content_type:
            # Solidity files should be text/plain or application/octet-stream
            allowed_mimes = ["text/plain", "application/octet-stream"]
            if file.content_type not in allowed_mimes:
                return False, f"Invalid MIME type: {file.content_type}"

        return True, None

    async def validate_content(self, file: UploadFile) -> tuple[bool, Optional[str]]:
        """
        Validate file content for malicious code.

        Args:
            file: Uploaded file

        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Read first chunk to check content
            content = await file.read(8192)  # Read first 8KB
            await file.seek(0)  # Reset file pointer

            # Check for null bytes (binary file)
            if b"\x00" in content:
                return False, "Invalid file: appears to be binary"

            # Try to decode as text
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                return False, "Invalid file: not valid UTF-8 text"

            # Check for suspicious patterns (basic check)
            suspicious_patterns = [
                r"<script[^>]*>",  # JavaScript
                r"eval\s*\(",  # Eval calls
                r"exec\s*\(",  # Exec calls
                r"\$\(.*\)",  # jQuery
            ]

            for pattern in suspicious_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return False, f"Suspicious content detected: {pattern}"

            return True, None

        except Exception as e:
            return False, f"Error validating content: {str(e)}"

    async def validate_file(self, file: UploadFile) -> tuple[bool, Optional[str]]:
        """
        Perform all validations on uploaded file.

        Args:
            file: Uploaded file

        Returns:
            tuple: (is_valid, error_message)
        """
        # Validate filename
        is_valid, error = self.validate_filename(file.filename)
        if not is_valid:
            return False, error

        # Validate size
        is_valid, error = self.validate_size(file)
        if not is_valid:
            return False, error

        # Validate MIME type
        is_valid, error = self.validate_mime_type(file)
        if not is_valid:
            return False, error

        # Validate content
        is_valid, error = await self.validate_content(file)
        if not is_valid:
            return False, error

        return True, None


# ==================== Input Sanitization ====================


class InputSanitizer:
    """
    Sanitize user input to prevent XSS and injection attacks.
    """

    @staticmethod
    def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize string input.

        Args:
            text: Input text
            max_length: Maximum allowed length

        Returns:
            str: Sanitized text
        """
        if not text:
            return ""

        # Trim whitespace
        text = text.strip()

        # Enforce max length
        if max_length and len(text) > max_length:
            text = text[:max_length]

        # Remove null bytes
        text = text.replace("\x00", "")

        # Remove control characters except newline and tab
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")

        return text

    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Remove HTML tags and escape special characters.

        Args:
            text: Input text with potential HTML

        Returns:
            str: Sanitized text without HTML
        """
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Escape special characters
        replacements = {"<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;", "/": "&#x2F;"}

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal.

        Args:
            filename: Input filename

        Returns:
            str: Safe filename
        """
        # Get basename only (no path)
        filename = Path(filename).name

        # Remove dangerous characters
        filename = re.sub(r"[^\w\s.-]", "", filename)

        # Remove multiple dots
        filename = re.sub(r"\.+", ".", filename)

        # Limit length
        if len(filename) > 255:
            name, ext = Path(filename).stem, Path(filename).suffix
            filename = name[: 255 - len(ext)] + ext

        return filename


# ==================== SQL Injection Prevention ====================


class SQLValidator:
    """
    Validate input to prevent SQL injection.
    Note: Always use parameterized queries (SQLAlchemy ORM does this by default)
    """

    @staticmethod
    def is_safe_order_by(field: str, allowed_fields: List[str]) -> bool:
        """
        Validate ORDER BY field to prevent SQL injection.

        Args:
            field: Field name
            allowed_fields: List of allowed field names

        Returns:
            bool: True if safe
        """
        # Remove direction indicators
        field = field.lower().replace(" asc", "").replace(" desc", "").strip()

        # Check if field is in allowed list
        return field in [f.lower() for f in allowed_fields]

    @staticmethod
    def validate_identifier(identifier: str) -> bool:
        """
        Validate SQL identifier (table/column name).

        Args:
            identifier: Identifier to validate

        Returns:
            bool: True if valid
        """
        # Allow only alphanumeric and underscore
        return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", identifier))


# ==================== Request Logging Middleware ====================


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all requests for security auditing.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request details"""
        import logging
        import time

        logger = logging.getLogger("blockscope.requests")

        # Record start time
        start_time = time.time()

        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log successful request
            if settings.LOG_REQUESTS:
                logger.info(
                    f"{request.method} {request.url.path} - "
                    f"Status: {response.status_code} - "
                    f"IP: {client_ip} - "
                    f"Duration: {duration:.3f}s"
                )

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log error
            logger.error(
                f"{request.method} {request.url.path} - "
                f"Error: {str(e)} - "
                f"IP: {client_ip} - "
                f"Duration: {duration:.3f}s"
            )
            raise


# ==================== Helper Functions ====================


def setup_cors(app) -> None:
    """
    Configure CORS middleware.

    Args:
        app: FastAPI application
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        max_age=settings.CORS_MAX_AGE,
    )


def setup_security_middleware(app) -> None:
    """
    Setup all security middleware.

    Args:
        app: FastAPI application
    """
    # Add security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Add request logging
    if settings.LOG_REQUESTS:
        app.add_middleware(RequestLoggingMiddleware)

    # Add CORS
    setup_cors(app)


# ==================== Usage Example ====================
"""
# In main.py:

from fastapi import FastAPI, UploadFile, File
from app.core.security import (
    setup_security_middleware,
    FileValidator,
    InputSanitizer
)

app = FastAPI()

# Setup security
setup_security_middleware(app)

# Use in endpoints
file_validator = FileValidator()

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Validate file
    is_valid, error = await file_validator.validate_file(file)
    if not is_valid:
        raise HTTPException(400, detail=error)

    # Process file...
    return {"message": "File uploaded successfully"}

@app.post("/search")
async def search(query: str):
    # Sanitize input
    safe_query = InputSanitizer.sanitize_string(query, max_length=100)
    safe_query = InputSanitizer.sanitize_html(safe_query)

    # Use safe_query...
    return {"results": []}
"""
