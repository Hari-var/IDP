import json
from datetime import datetime
from fastapi import APIRouter

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("/")
def get_logs(lines: int = 100):
    """Get recent application logs with JSON parsing."""
    try:
        with open('app.log', 'r') as f:
            log_lines = f.readlines()
        
        # Parse JSON logs and add readable timestamp
        parsed_logs = []
        for line in log_lines[-lines:]:
            try:
                log_entry = json.loads(line.strip())
                parsed_logs.append(log_entry)
            except json.JSONDecodeError:
                # Fallback for non-JSON lines
                parsed_logs.append({"raw_log": line.strip(), "timestamp": None})
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_logs": len(parsed_logs),
            "logs": parsed_logs
        }
    except FileNotFoundError:
        return {"logs": ["No log file found"]}
