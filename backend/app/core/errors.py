"""
Structured Error Handling and Custom Exceptions
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class OilSpillException(Exception):
    """Base exception for all domain-specific errors."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class GeospatialError(OilSpillException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="GEOSPATIAL_ERROR", details=details)


class MLInferenceError(OilSpillException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="ML_INFERENCE_ERROR", details=details)


class ForecastingError(OilSpillException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="FORECASTING_ERROR", details=details)


class DataUnavailableError(OilSpillException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="DATA_UNAVAILABLE", details=details)


class InsufficientDataError(OilSpillException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="INSUFFICIENT_DATA", details=details)


def create_error_response(status_code: int, code: str, message: str, details: Optional[Dict[str, Any]] = None):
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
                "details": details or {}
            }
        }
    )
