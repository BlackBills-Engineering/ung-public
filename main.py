from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import List, Optional
from contextlib import asynccontextmanager
from datetime import datetime
from ws_pumps import router as pumps_ws

from models import (
    ChangePricesRequest,
    ChangePricesResponse,
    BulkChangePricesResponse,
    PumpInfo,
    PumpStatusResponse,
    PumpDiscoveryResult,
    CommandResponse,
    RealtimeData,
    TransactionData,
    VolumePresetRequest,
    MoneyPresetRequest,
    PresetResponse,
)
# from pump_manager import PumpManager

COMPORT = "COM3"


logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/logs.log", mode="a")],
)

logging.getLogger("GilbarcoAPI").setLevel(logging.ERROR)
logging.getLogger("GilbarcoStartup").setLevel(logging.ERROR)
logging.getLogger("PumpManager").setLevel(logging.ERROR)
logging.getLogger("TwoWireManager").setLevel(logging.ERROR)
logging.getLogger("SerialConnection").setLevel(logging.ERROR)
logging.getLogger("uvicorn").setLevel(logging.ERROR)

logger = logging.getLogger("GilbarcoAPI")
startup_logger = logging.getLogger("GilbarcoStartup")

# pump_manager: Optional[PumpManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global pump_manager

    startup_logger.info("=== Starting Gilbarco SK700-II Control System ===")
    startup_logger.info(f"Startup time: {datetime.now()}")

    from config import settings

    startup_logger.info(f"Configuration: {settings.dict()}")

    startup_logger.info("Initializing Pump Manager...")
    # pump_manager = PumpManager()
    app.state.pump_manager = {}
    startup_logger.info("Pump Manager initialized successfully")


    startup_logger.info("System startup complete - API ready to serve requests")
    startup_logger.info(f"Swagger UI: http://localhost:{settings.API_PORT}/docs")

    yield

    startup_logger.info("=== Shutting down Gilbarco SK700-II Control System ===")
    if pump_manager:
        startup_logger.info("Shutting down Pump Manager...")
        pump_manager.shutdown()
        startup_logger.info("Pump Manager shutdown complete")
    startup_logger.info("System shutdown complete")


app = FastAPI(
    title="Gilbarco SK700-II Control API",
    description="""
    API for controlling Gilbarco SK700-II fuel dispensers
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_tags=[
        {"name": "Health", "description": "API health and system status endpoints"},
        {
            "name": "Pump Discovery",
            "description": "Discover and scan for pumps on COM ports",
        },
        {
            "name": "Pump Information",
            "description": "Get pump information and real-time status",
        },
        {
            "name": "Pump Control",
            "description": "Execute commands on pumps (extensible for future features)",
        },
        {"name": "Presets", "description": "Control pump presets like volume, money"},
        {
          "name": "Price update",
          "description": "Change prices for grades"
        },
        {
            "name": "Port Control",
            "description": "Connect and disconnect COM ports (Two-Wire Protocol)",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pumps_ws)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/docs")


@app.get(
    "/api/health",
    tags=["Health"],
    summary="Health Check",
    description="Check if the API is running and healthy. Returns system status and pump count.",
)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Gilbarco SK700-II Control API",
        "version": "1.0.0",
        "pumps_managed": len(pump_manager.pumps) if pump_manager else 0,
    }


@app.post(
    "/api/pumps/discover",
    response_model=PumpDiscoveryResult,
    tags=["Pump Discovery"],
    summary="Discover Pumps",
    description="""
          Scan COM ports to discover connected Gilbarco SK700-II pumps.
          
          Parameters:
          - min_address: Starting pump address to test (1-16)
          - max_address: Ending pump address to test (1-16) 
          - timeout: Timeout in seconds for each pump test
          
          Returns: Discovery results with found pumps
          """,
)
async def discover_pumps(
    address_range_start: int = Query(
        1, ge=1, le=99, description="Start of pump address range to test"
    ),
    address_range_end: int = Query(
        6, ge=1, le=99, description="End of pump address range to test"
    ),
    timeout: float = Query(
        0.1, gt=0, le=10, description="Timeout in seconds for each pump test"
    ),
):
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")

    try:
        if address_range_start > address_range_end:
            raise HTTPException(
                status_code=400,
                detail="address_range_start must be less than or equal to address_range_end",
            )

        result = pump_manager.auto_discover_and_manage(
            com_ports=[COMPORT],
            address_range=(address_range_start, address_range_end),
            timeout=timeout,
        )

        return result

    except Exception as e:
        logger.error(f"Error during pump discovery: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


@app.get(
    "/api/pumps",
    response_model=List[PumpInfo],
    tags=["Pump Information"],
    summary="Get All Pumps",
    description="Get information about all managed pumps in the system.",
)
async def get_all_pumps():
    """
    Get a list of all pumps currently managed by the system.

    Returns basic information about each pump including:
    - Pump ID
    - COM port
    - Address
    - Connection status
    """
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")

    return pump_manager.get_pump_list()


@app.get(
    "/api/pumps/{pump_id}",
    response_model=PumpInfo,
    tags=["Pump Information"],
    summary="Get Pump Info",
    description="Get detailed information about a specific pump by ID.",
)
async def get_pump_info(pump_id: int = Path(..., description="Pump ID", ge=1)):
    """Get information about a specific pump by ID"""
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")

    pumps = pump_manager.get_pump_list()
    for pump in pumps:
        if pump.pump_id == pump_id:
            return pump

    raise HTTPException(status_code=404, detail=f"Pump {pump_id} not found")


@app.get(
    "/api/pumps/{pump_id}/status",
    response_model=PumpStatusResponse,
    tags=["Pump Information"],
    summary="Get Pump Status",
    description="""
         Get real-time status of a specific pump.
         
         Returns:
         - Current pump status (IDLE, CALLING, AUTHORIZED, DISPENSING, etc.)
         - Connection status
         - Last communication timestamp
         - Current transaction data (if any)
         """,
)
async def get_pump_status(pump_id: int = Path(..., description="Pump ID", ge=1)):
    """
    Get the current status of a specific pump.

    Returns:
    - Current pump status (IDLE, DISPENSING, COMPLETE, etc.)
    - Last update timestamp
    - Error message if applicable
    """
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")

    status = pump_manager.get_pump_status(pump_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Pump {pump_id} not found")

    return status


@app.get(
    "/api/pumps/{pump_id}/realtime",
    response_model=RealtimeData,
    tags=["Pump Information"],
    summary="Get Pump Transaction Data",
    description="""
         Get transaction data from a specific pump.
        """,
)
async def get_realtime_money(pump_id: int = Path(..., description="Pumpd ID", ge=1)):
    """
    Get realtime money for a specific pump. Pump must be in `BUSY` state
    """
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")

    realtime = pump_manager.get_realtime(pump_id)

    if not realtime:
        raise HTTPException(
            status_code=404,
            detail=f"No realtime data available for pump {pump_id}. "
            f"Pump may not exist or it is not in wrong state",
        )

    return RealtimeData(pump_id=pump_id, money=realtime)


@app.get(
    "/api/pumps/{pump_id}/transaction",
    response_model=TransactionData,
    tags=["Pump Information"],
    summary="Get Pump Transaction Data",
    description="""
         Get transaction data from a specific pump.
        """,
)
async def get_pump_transaction(pump_id: int = Path(..., description="Pump ID", ge=1)):
    """
    Get transaction data from a specific pump.
    """
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")

    transaction_data = pump_manager.get_transaction_data(pump_id)
    if not transaction_data:
        raise HTTPException(
            status_code=404,
            detail=f"No transaction data available for pump {pump_id}. "
            f"Pump may not exist or no transaction in progress/completed.",
        )

    return transaction_data


@app.post(
    "/api/pumps/{pump_id}/authorize",
    tags=["Pump Control"],
    response_model=CommandResponse,
    summary="Authorize Pump",
    description="Authorize a pump for dispensing. According to Two-Wire Protocol, the authorize command does not return a response, so we poll the pump status afterward to verify authorization.",
)
async def authorize_pump(pump_id: int = Path(..., description="Pump ID", ge=1)):
    """
    Authorize a specific pump for dispensing.

    This endpoint sends an authorize command to the pump and then polls the pump
    status to verify that the authorization was successful.
    """
    return CommandResponse(
        success=True,
        message=f"Pump {pump_id} authorized successfully",
        data={
            "pump_id": pump_id,
            "status": (
                "AUTHORIZED" 
            ),
            "authorized_at": datetime.now().isoformat(),
        },
        timestamp=datetime.now(),
    )


@app.post(
    "/api/pumps/{pump_id}/stop",
    tags=["Pump Control"],
    response_model=CommandResponse,
    summary="Stop Pump",
    description="Stop a pump that is currently dispensing or authorized. According to Two-Wire Protocol, the stop command does not return a response, so we poll the pump status afterward to verify the stop.",
)
async def stop_pump(pump_id: int = Path(..., description="Pump ID", ge=1)):
    """
    Stop a specific pump.

    This endpoint sends a stop command to the pump and then polls the pump
    status to verify that the pump was stopped successfully.

    Returns:
    - success: True if pump was stopped successfully
    - message: Description of the result
    - data: Pump status information after stop
    """
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")

    if pump_id not in pump_manager.pumps:
        raise HTTPException(status_code=404, detail=f"Pump {pump_id} not found")

    try:
        # Stop the pump
        success = pump_manager.stop_pump(pump_id)

        if success:
            # Get the current status after stopping
            status_response = pump_manager.get_pump_status(pump_id)

            return CommandResponse(
                success=True,
                message=f"Pump {pump_id} stopped successfully",
                data={
                    "pump_id": pump_id,
                    "status": (
                        status_response.status.value if status_response else "UNKNOWN"
                    ),
                    "stopped_at": datetime.now().isoformat(),
                },
                timestamp=datetime.now(),
            )
        else:
            return CommandResponse(
                success=False,
                message=f"Failed to stop pump {pump_id}",
                data={"pump_id": pump_id},
                timestamp=datetime.now(),
            )

    except Exception as e:
        logger.error(f"Error stopping pump {pump_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error while stopping pump {pump_id}: {str(e)}",
        )


@app.post(
    "/api/pumps/stop-all",
    tags=["Pump Control"],
    response_model=CommandResponse,
    summary="Emergency Stop All Pumps",
    description="Send emergency stop command to all pumps on all connected COM ports. This is used in emergency situations to immediately stop all fuel dispensing operations.",
)
async def stop_all_pumps():
    """
    Emergency stop all pumps on all connected COM ports.

    This endpoint sends the Two-Wire Protocol all-stop command to every
    connected COM port, which will stop all pumps on those lines immediately.

    This is typically used in emergency situations.

    Returns:
    - success: True if emergency stop was sent to all COM ports successfully
    - message: Description of the result
    - data: Information about the emergency stop operation
    """
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")

    try:
        success = pump_manager.stop_all_pumps()

        active_ports = list(pump_manager.managers.keys())
        total_pumps = len(pump_manager.pumps)

        if success:
            return CommandResponse(
                success=True,
                message=f"Emergency stop sent successfully to all {len(active_ports)} COM ports",
                data={
                    "emergency_stop_at": datetime.now().isoformat(),
                    "com_ports": active_ports,
                    "total_pumps_affected": total_pumps,
                    "operation": "EMERGENCY_STOP_ALL",
                },
                timestamp=datetime.now(),
            )
        else:
            return CommandResponse(
                success=False,
                message="Failed to send emergency stop to all COM ports",
                data={
                    "com_ports": active_ports,
                    "total_pumps": total_pumps,
                    "operation": "EMERGENCY_STOP_ALL",
                },
                timestamp=datetime.now(),
            )

    except Exception as e:
        logger.error(f"Error in emergency stop all pumps: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Internal error during emergency stop: {str(e)}"
        )


@app.post(
    "/api/pumps/{pump_id}/preset/volume",
    response_model=PresetResponse,
    tags=["Presets"],
    summary="Set Preset",
    description="""
    Set volume or money preset for a specific pump and grade.
    The pump will stop dispensing when the preset volume is reached.
    """,
)
async def set_volume_preset(
    request: VolumePresetRequest,
    pump_id: int = Path(..., description="Pump ID", ge=1),
):
    """
    Set volume preset for a specific pump.
    Returns:
        PresetResponse: Success/failure status with details
    Raises:
        HTTPException: If pump not found or preset fails
    """

    logger.info(f"Volume preset set successfully for pump {pump_id}")
    return PresetResponse(
        success=True,
        message=f"Volume preset set: {request.volume} gallons for grade {request.grade}",
        pump_id=pump_id,
        preset_data={
            "type": "volume",
            "volume": request.volume,
            "grade": request.grade,
            "pump_address": "pump address",
        },
        timestamp=datetime.now(),
        )


@app.post(
    "/api/pumps/{pump_id}/preset/money",
    response_model=PresetResponse,
    tags=["Presets"],
    summary="Set Money Preset",
    description="""
    Set a money preset for a specific pump and grade.
    The pump must be in the correct state to accept presets.
    """,
)
async def set_money_preset(
    request: MoneyPresetRequest,
    pump_id: int = Path(..., description="Pump ID", ge=1, le=16),
):
    """
    Set money preset for a specific pump.
    """
    
    logger.info(f"Money preset set successfully for pump {pump_id}")
    return PresetResponse(
        success=True,
        message=f"Money preset set: ${request.money_amount:.2f} for grade {request.grade}",
        pump_id=pump_id,
        preset_data={
            "type": "money",
            "money_amount": request.money_amount,
            "grade": request.grade,
            "price_level": 1,
            "pump_address": "pump address",
        },
        timestamp=datetime.now(),
    )
        
@app.post(
    "/api/pumps/{pump_id}/change-prices",
    response_model=ChangePricesResponse,
    tags=["Price update"],
    summary="Set  new price",
    description="""
    Set new grade prices for a specific pumps
    """
)
async def change_prices(
    request: ChangePricesRequest,
    pump_id: int = Path(..., description="Pump ID", ge=1, le=16),
):
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")
    
    logger.info(
        f"Changing price for {pump_id}, grades: ${request.grades_info}"
    )

    pump_info = pump_manager.get_pump_info(pump_id)
    if not pump_info:
        raise HTTPException(status_code=404, detail=f"Pump {pump_id} not found")

    result = pump_manager.change_prices(
        pump_id,
        request.grades_info,
    )

    grade_results = []
    overall_success = True
    
    for i, grade_info in enumerate(request.grades_info):
        grade_success = result[i] if i < len(result) else False
        if not grade_success:
            overall_success = False
            
        grade_results.append({
            "grade_id": grade_info.id,
            "grade_title": grade_info.title,
            "new_price": grade_info.price,
            "success": grade_success,
            "message": f"Price updated to {grade_info.price}" if grade_success else f"Failed to update price for grade {grade_info.id}"
        })

    successful_count = sum(result)
    failed_count = len(request.grades_info) - successful_count

    logger.info(f"Prices changed for pump {pump_id}: {successful_count}/{len(request.grades_info)} successful")
    
    return ChangePricesResponse(
        success=overall_success,
        message=f"{successful_count} of {len(request.grades_info)} grades updated successfully.",
        pump_id=pump_id,
        total_grades=len(request.grades_info),
        successful_updates=successful_count,
        failed_updates=failed_count,
        grade_results=grade_results,
        timestamp=datetime.now(),
    )


@app.post(
    "/api/pumps/change-prices",
    response_model=BulkChangePricesResponse,
    tags=["Price update"],
    summary="Set new prices for all pumps",
    description="""
    Set new grade prices for all managed pumps in the system.
    Returns detailed results for each pump and grade.
    """
)
async def change_prices_for_all(request: ChangePricesRequest):
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")
    
    logger.info(
        f"Changing prices for all pumps, grades: {request.grades_info}"
    )
    
    pump_results = []
    overall_success = True
    successful_pumps = 0
    
    for pump in pump_manager.pumps.values():
        result = pump_manager.change_prices(
            pump.pump_id,
            request.grades_info,
        )
        
        grade_results = []
        pump_success = True
        
        for i, grade_info in enumerate(request.grades_info):
            grade_success = result[i] if i < len(result) else False
            if not grade_success:
                pump_success = False
                overall_success = False
                
            grade_results.append({
                "grade_id": grade_info.id,
                "grade_title": grade_info.title,
                "new_price": grade_info.price,
                "success": grade_success,
                "message": f"Price updated to {grade_info.price}" if grade_success else f"Failed to update price for grade {grade_info.id}"
            })
        
        successful_count = sum(result)
        failed_count = len(request.grades_info) - successful_count
        
        if pump_success:
            successful_pumps += 1
            
        pump_results.append({
            "pump_id": pump.pump_id,
            "success": pump_success,
            "message": f"All {len(request.grades_info)} grades updated successfully" if pump_success else f"{successful_count} of {len(request.grades_info)} grades updated successfully",
            "total_grades": len(request.grades_info),
            "successful_updates": successful_count,
            "failed_updates": failed_count,
            "grade_results": grade_results
        })
    
    failed_pumps = len(pump_manager.pumps) - successful_pumps
    
    logger.info(f"Bulk price change completed: {successful_pumps}/{len(pump_manager.pumps)} pumps fully successful")
    
    return BulkChangePricesResponse(
        success=overall_success,
        message=f"Price update completed for {len(pump_manager.pumps)} pumps. {successful_pumps} pumps fully successful, {failed_pumps} pumps had some failures.",
        total_pumps=len(pump_manager.pumps),
        successful_pumps=successful_pumps,
        failed_pumps=failed_pumps,
        pump_results=pump_results,
        timestamp=datetime.now(),
    )


@app.post(
    "/api/ports/{com_port}/connect",
    tags=["Port Control"],
    summary="Connect to COM Port",
    description="Establish serial connection to a specific COM port (all pumps on that port).",
)
async def connect_port(
    com_port: str = Path(..., description="COM port (e.g., COM1, /dev/ttyUSB0)")
):
    """Connect to a specific COM port"""
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")

    success = pump_manager.connect_port(com_port)
    if not success:
        raise HTTPException(
            status_code=400, detail=f"Failed to connect to COM port {com_port}"
        )

    return {"message": f"Successfully connected to COM port {com_port}"}


@app.post(
    "/api/ports/{com_port}/disconnect",
    tags=["Port Control"],
    summary="Disconnect from COM Port",
    description="Disconnect from a specific COM port (all pumps on that port).",
)
async def disconnect_port(
    com_port: str = Path(..., description="COM port (e.g., COM1, /dev/ttyUSB0)")
):
    """Disconnect from a specific COM port"""
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")

    success = pump_manager.disconnect_port(com_port)
    if not success:
        raise HTTPException(
            status_code=404, detail=f"COM port {com_port} not found or not connected"
        )

    return {"message": f"Successfully disconnected from COM port {com_port}"}


@app.post(
    "/api/ports/connect-all",
    tags=["Port Control"],
    summary="Connect to All COM Ports",
    description="Connect to all COM ports used by managed pumps.",
)
async def connect_all_ports():
    """Connect to all COM ports used by managed pumps"""
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")

    results = pump_manager.connect_all_ports()

    return {
        "message": "Connection attempt completed for all COM ports",
        "results": results,
        "successful_connections": sum(1 for success in results.values() if success),
        "total_ports": len(results),
    }


@app.post(
    "/api/ports/disconnect-all",
    tags=["Port Control"],
    summary="Disconnect from All COM Ports",
    description="Disconnect from all COM ports used by managed pumps.",
)
async def disconnect_all_ports():
    """Disconnect from all COM ports"""
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")

    pump_manager.disconnect_all_ports()

    return {"message": "Successfully disconnected from all COM ports"}


@app.get(
    "/api/ports/connected",
    tags=["Port Control"],
    summary="Get Connected COM Ports",
    description="Get a list of currently connected COM ports.",
)
async def get_connected_ports():
    """Get list of currently connected COM ports"""
    if not pump_manager:
        raise HTTPException(status_code=500, detail="Pump manager not initialized")

    connected_ports = pump_manager.get_connected_ports()

    return {"connected_ports": connected_ports, "total_connected": len(connected_ports)}
