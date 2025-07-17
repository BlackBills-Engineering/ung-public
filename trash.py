# trash.py - Test data for frontend development
from datetime import datetime, timezone
from typing import Any, Dict


EXAMPLE_FRAME = """{"ts":"2025-07-09T15:13:43.099591+00:00","pumps":[{"pump_id":1,"status":"IDLE","last_updated":"2025-07-09T20:13:43.307955","error_message":null,"raw_status_code":"0x6","wire_format":"0x61","transaction":{"pump_id":1,"volume":30.0,"price_per_unit":8150,"total_amount":244500.0,"grade":0,"timestamp":"2025-07-09T20:13:44.444872"}},{"pump_id":2,"status":"IDLE","last_updated":"2025-07-09T20:13:43.514943","error_message":null,"raw_status_code":"0x6","wire_format":"0x62","transaction":{"pump_id":2,"volume":6.13,"price_per_unit":8150,"total_amount":50000.0,"grade":0,"timestamp":"2025-07-09T20:13:44.515066"}},{"pump_id":3,"status":"IDLE","last_updated":"2025-07-09T20:13:43.736667","error_message":null,"raw_status_code":"0x6","wire_format":"0x63","transaction":{"pump_id":3,"volume":12.27,"price_per_unit":8150,"total_amount":100000.0,"grade":0,"timestamp":"2025-07-09T20:13:44.585205"}},{"pump_id":4,"status":"IDLE","last_updated":"2025-07-09T20:13:43.943853","error_message":null,"raw_status_code":"0x6","wire_format":"0x64","transaction":{"pump_id":4,"volume":1.0,"price_per_unit":8150,"total_amount":8150.0,"grade":0,"timestamp":"2025-07-09T20:13:44.655588"}},{"pump_id":5,"status":"AUTHORIZED","last_updated":"2025-07-09T20:13:44.153227","error_message":null,"raw_status_code":"0x8","wire_format":"0x85"},{"pump_id":6,"status":"IDLE","last_updated":"2025-07-09T20:13:44.374256","error_message":null,"raw_status_code":"0x6","wire_format":"0x66","transaction":{"pump_id":6,"volume":1.06,"price_per_unit":8150,"total_amount":8639.0,"grade":0,"timestamp":"2025-07-09T20:13:44.726551"}}]}"""

def get_frame() -> Dict[str, Any]:
    """Return hardcoded test data for frontend development"""
    current_time = datetime.now(timezone.utc).isoformat()
    
    return {
        "ts": current_time,
        "pumps": [
            {
                "pump_id": 1,
                "status": "IDLE",
                "last_updated": current_time,
                "error_message": None,
                "raw_status_code": "0x6",
                "wire_format": "0x61",
                "transaction": {
                    "pump_id": 1,
                    "volume": 30.0,
                    "price_per_unit": 8150,
                    "total_amount": 244500.0,
                    "grade": 0,
                    "timestamp": current_time
                }
            },
            {
                "pump_id": 2,
                "status": "CALLING",
                "last_updated": current_time,
                "error_message": None,
                "raw_status_code": "0x7",
                "wire_format": "0x72"
            },
            {
                "pump_id": 3,
                "status": "AUTHORIZED",
                "last_updated": current_time,
                "error_message": None,
                "raw_status_code": "0x8",
                "wire_format": "0x83"
            },
            {
                "pump_id": 4,
                "status": "DISPENSING",
                "last_updated": current_time,
                "error_message": None,
                "raw_status_code": "0x9",
                "wire_format": "0x94",
                "realtime": {
                    "price_per_unit": 81500,  # Gilbarco format (8150 * 10)
                    "grade": 0,
                    "timestamp": current_time,
                    "total_amount": 25400,  # в копейках
                    "volume": 3.116  # литры
                }
            },
            {
                "pump_id": 5,
                "status": "COMPLETE",
                "last_updated": current_time,
                "error_message": None,
                "raw_status_code": "0xA",
                "wire_format": "0xA5",
                "transaction": {
                    "pump_id": 5,
                    "volume": 15.234,
                    "price_per_unit": 8150,
                    "total_amount": 124156.1,
                    "grade": 0,
                    "timestamp": current_time
                }
            },
            {
                "pump_id": 6,
                "status": "STOPPED",
                "last_updated": current_time,
                "error_message": None,
                "raw_status_code": "0xC",
                "wire_format": "0xC6"
            },
            {
                "pump_id": 7,
                "status": "ERROR",
                "last_updated": current_time,
                "error_message": "Communication timeout",
                "raw_status_code": "0x0",
                "wire_format": "0x07"
            },
            {
                "pump_id": 8,
                "status": "OFFLINE",
                "last_updated": current_time,
                "error_message": "No response from pump",
                "raw_status_code": None,
                "wire_format": None
            }
        ]
    }
    