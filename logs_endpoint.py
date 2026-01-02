@app.get("/logs")
def get_logs(lines: int = 100):
    """Get recent application logs"""
    try:
        with open('app.log', 'r') as f:
            log_lines = f.readlines()
        return {"logs": log_lines[-lines:]}
    except FileNotFoundError:
        return {"logs": ["No log file found"]}