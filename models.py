from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class PumpStatus(str, Enum):
    """
    Protocol Status Codes:
    - 0x0: Data Error → ERROR
    - 0x6: Off → IDLE
    - 0x7: Call → CALLING
    - 0x8: Authorized/Not Delivering → AUTHORIZED
    - 0x9: Busy → DISPENSING
    - 0xA: Transaction Complete (PEOT) → COMPLETE
    - 0xB: Transaction Complete (FEOT) → COMPLETE
    - 0xC: Pump Stop → STOPPED
    - 0xD: Send Data → ERROR (special state)
    """

    IDLE = "IDLE"  # Pump is off/ready (protocol 0x6)
    CALLING = "CALLING"  # Customer requesting service (protocol 0x7)
    AUTHORIZED = "AUTHORIZED"  # Pump authorized but not dispensing (protocol 0x8)
    DISPENSING = "DISPENSING"  # Actively dispensing fuel (protocol 0x9)
    COMPLETE = "COMPLETE"  # Transaction finished (protocol 0xA/0xB)
    STOPPED = "STOPPED"  # Emergency stop activated (protocol 0xC)
    ERROR = "ERROR"  # Communication/data error (protocol 0x0/0xD)
    OFFLINE = "OFFLINE"  # No communication with pump


class PumpInfo(BaseModel):
    """Basic pump information"""

    pump_id: int = Field(..., description="Pump identifier")
    com_port: str = Field(..., description="COM port connection")
    address: int = Field(..., description="Pump address on serial line")
    name: Optional[str] = Field(None, description="Pump display name")
    is_connected: bool = Field(False, description="Connection status")


class GradeInfo(BaseModel):
    id: int = Field(..., ge=0, le=15, description="Grade identifier (0-3)")
    title: Optional[str] = Field(None, description="Grade title (e.g. AI-80)")
    price: float = Field(..., ge=1, le=9999, description="Grade price (4 digits)")


class PumpStatusResponse(BaseModel):
    """
    Pump status response with detailed protocol information

    Example:
    {
        "pump_id": 1,
        "status": "AUTHORIZED",
        "last_updated": "2025-07-05T12:34:56.789Z",
        "error_message": null,
        "raw_status_code": "0x8",
        "wire_format": "0x81"
    }
    """

    pump_id: int = Field(..., description="Pump identifier (1-16)")
    status: PumpStatus = Field(..., description="Current pump status")
    last_updated: datetime = Field(..., description="Last status update timestamp")
    error_message: Optional[str] = Field(
        None, description="Error details if status is ERROR"
    )
    raw_status_code: Optional[str] = Field(
        None, description="Raw protocol status code (hex)"
    )
    wire_format: Optional[str] = Field(
        None, description="Complete wire format byte (hex)"
    )


class RealtimeData(BaseModel):
    pump_id: int = Field(..., description="Pump identifier")
    money: float = Field(None, description="Dispensed realtime money")


class TransactionData(BaseModel):
    """Transaction data from pump"""

    pump_id: int = Field(..., description="Pump identifier")
    volume: Optional[float] = Field(None, description="Dispensed volume")
    price_per_unit: Optional[float] = Field(None, description="Price per unit")
    total_amount: Optional[float] = Field(None, description="Total transaction amount")
    grade: Optional[int] = Field(None, description="Fuel grade")
    timestamp: datetime = Field(..., description="Transaction timestamp")


class CommandRequest(BaseModel):
    """Generic command request"""

    pump_id: int = Field(..., description="Target pump identifier")
    command: str = Field(..., description="Command to execute")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Command parameters")


class CommandResponse(BaseModel):
    """Generic command response"""

    success: bool = Field(..., description="Command execution success")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(..., description="Response timestamp")


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(..., description="Error timestamp")


class PumpDiscoveryResult(BaseModel):
    """Pump discovery result"""

    discovered_pumps: List[PumpInfo] = Field(
        ..., description="List of discovered pumps"
    )
    total_found: int = Field(..., description="Total number of pumps found")
    scan_duration: float = Field(..., description="Discovery scan duration in seconds")
    timestamp: datetime = Field(..., description="Discovery timestamp")


class GradeTotals(BaseModel):
    """Totals data for a single grade"""

    grade: int = Field(..., description="Grade number")
    volume: float = Field(..., description="Total volume dispensed (gallons)")
    money: float = Field(..., description="Total money amount ($)")
    volume_raw: Optional[str] = Field(None, description="Raw volume data (hex)")
    money_raw: Optional[str] = Field(None, description="Raw money data (hex)")


class PumpTotalsResponse(BaseModel):
    """Response model for pump totals data"""

    pump_id: int = Field(..., description="Pump ID")
    total_grades: int = Field(..., description="Number of grades with data")
    grades: Dict[int, GradeTotals] = Field(..., description="Totals data by grade")
    lrc_checksum: Optional[str] = Field(None, description="LRC checksum (hex)")
    timestamp: datetime = Field(..., description="Response timestamp")


class PresetRequest(BaseModel):
    """Base request model for setting pump presets"""

    pump_id: int = Field(..., description="Pump identifier (1-16)")
    grade: int = Field(..., description="Fuel grade (1-16)")


class VolumePresetRequest(BaseModel):
    """Request model for setting volume preset"""

    grade: int = Field(..., description="Fuel grade (0-3)")

    volume: float = Field(
        None, ge=0.01, le=10000000, description="Volume preset in gallons (0.01-999.99)"
    )


class MoneyPresetRequest(BaseModel):
    """Request model for setting money preset"""

    grade: int = Field(..., description="Fuel grade (0-3)")

    money_amount: float = Field(
        ..., ge=0.01, le=999_999, description="Money preset in dollars (0.01-999.99)"
    )
    
class ChangePricesRequest(BaseModel):
    """Request model for changing prices for a specific pump"""
    
    grades_info: List[GradeInfo] = Field(..., description="Grade info (id, price, title - optional)")

class PresetResponse(BaseModel):
    """Response model for preset operations"""

    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Response message")
    pump_id: int = Field(..., description="Pump identifier")
    preset_data: Dict[str, Any] = Field(..., description="Preset details")
    timestamp: datetime = Field(..., description="Response timestamp")

class GradeUpdateResult(BaseModel):
    """Result for a single grade update"""
    grade_id: int = Field(..., description="Grade identifier")
    grade_title: str = Field(..., description="Grade title (e.g., AI-80)")
    new_price: float = Field(..., description="New price that was set")
    success: bool = Field(..., description="Whether the update was successful")
    message: str = Field(..., description="Success or error message")


class ChangePricesResponse(BaseModel):
    """Response model for changing prices for a specific pump"""
    success: bool = Field(..., description="Overall operation success (true if ALL grades updated successfully)")
    message: str = Field(..., description="Overall operation message")
    pump_id: int = Field(..., description="Pump identifier")
    total_grades: int = Field(..., description="Total number of grades attempted")
    successful_updates: int = Field(..., description="Number of successful updates")
    failed_updates: int = Field(..., description="Number of failed updates")
    grade_results: List[GradeUpdateResult] = Field(..., description="Detailed results for each grade")
    timestamp: datetime = Field(..., description="Response timestamp")


class PumpPriceUpdateResult(BaseModel):
    """Result for price update on a single pump"""
    pump_id: int = Field(..., description="Pump identifier")
    success: bool = Field(..., description="Overall success for this pump")
    message: str = Field(..., description="Overall message for this pump")
    total_grades: int = Field(..., description="Total grades attempted for this pump")
    successful_updates: int = Field(..., description="Successful updates for this pump")
    failed_updates: int = Field(..., description="Failed updates for this pump")
    grade_results: List[GradeUpdateResult] = Field(..., description="Detailed results for each grade")


class BulkChangePricesResponse(BaseModel):
    """Response model for changing prices across all pumps"""
    success: bool = Field(..., description="Overall operation success (true if ALL pumps updated successfully)")
    message: str = Field(..., description="Overall operation summary")
    total_pumps: int = Field(..., description="Total number of pumps attempted")
    successful_pumps: int = Field(..., description="Number of pumps that had all grades updated successfully")
    failed_pumps: int = Field(..., description="Number of pumps that had some or all grade updates fail")
    pump_results: List[PumpPriceUpdateResult] = Field(..., description="Detailed results for each pump")
    timestamp: datetime = Field(..., description="Response timestamp")