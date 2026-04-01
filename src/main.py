from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from ruamel.yaml import YAML
from typing import Dict, List, Union
import json
import os
import statistics
import secrets

app = FastAPI(docs_url=None, redoc_url=None)
yaml = YAML()
security = HTTPBasic()

# Configuration
YAML_FILE = os.getenv("CONFIG_PATH", "/config/config.yaml")
RESOLUTION = os.getenv("CONFLICT_RESOLUTION", "MIN").upper()

# Set a threshold for "suspicious" data (e.g., 20% deviation from local average)
OUTLIER_THRESHOLD = float(os.getenv("OUTLIER_THRESHOLD", "0.20"))

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"DEBUG: Validation Error: {exc.errors()}") 
    return JSONResponse(status_code=400, content={"detail": "Bad Request"})

class WeightBatch(BaseModel):
    # Flexible input: Dict keys are dates, values are single weight or list of weights
    data: Dict[str, Union[str, float, List[Union[str, float]]]]

    @field_validator('data', mode='before')
    @classmethod
    def transform_string_to_dict(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Data must be a valid JSON string or dictionary")
        return v

def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Exclusively validates via Basic Auth using AUTH_USER and API_SECRET."""
    correct_username = os.getenv("AUTH_USER", "admin")
    correct_password = os.getenv("API_SECRET")
    
    if not correct_password:
        print("ERROR: API_SECRET environment variable is not set.")
        raise HTTPException(status_code=500, detail="Server configuration error")

    is_user_ok = secrets.compare_digest(credentials.username, correct_username)
    is_pass_ok = secrets.compare_digest(credentials.password, correct_password)

    if not (is_user_ok and is_pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def resolve_value(values: List[float]) -> float:
    """Applies the CONFLICT_RESOLUTION logic and rounds to 2 decimal places."""
    if not values:
        return 0.0
    if RESOLUTION == "MIN":
        res = min(values)
    elif RESOLUTION == "AVG":
        res = statistics.mean(values)
    else:
        res = max(values)
    return round(res, 2)

def check_for_outliers(date_str: str, value: float, history: Dict[str, float]):
    """Logs a warning if the value deviates significantly from existing nearby data."""
    existing_values = list(history.values())
    if len(existing_values) < 3:
        return # Not enough data to determine a 'normal' range

    local_avg = statistics.mean(existing_values[-10:]) # Check against last 10 entries
    diff = abs(value - local_avg) / local_avg

    if diff > OUTLIER_THRESHOLD:
        print(f"⚠️ WARNING: Potential outlier for {date_str}! Value: {value} | Avg: {local_avg:.2f} | Diff: {diff:.1%}")

@app.get("/health")
async def health_check():
    """Simple health check for Traefik or monitoring."""
    return {"status": "healthy", "config_loaded": os.path.exists(YAML_FILE)}

@app.post("/ingest")
async def log_weight(batch: WeightBatch, user: str = Depends(verify_auth)):
    try:
        # Load existing YAML
        if os.path.exists(YAML_FILE):
            with open(YAML_FILE, 'r') as f:
                content = yaml.load(f) or {}
        else:
            content = {"general": {"athlete": {"weightHistory": {}}}}

        history = content.setdefault("general", {}).setdefault("athlete", {}).setdefault("weightHistory", {})
        
        added_count = 0
        updated_count = 0
        
        # Sort incoming dates chronologically
        for date_str in sorted(batch.data.keys()):
            raw_val = batch.data[date_str]
            
            # Normalize input to a list of floats
            if isinstance(raw_val, list):
                incoming_values = [float(str(v).strip()) for v in raw_val if v]
            else:
                incoming_values = [float(str(raw_val).strip())]
            
            if not incoming_values:
                continue

            resolved_val = resolve_value(incoming_values)
            
            # Outlier check against existing history
            check_for_outliers(date_str, resolved_val, history)

            if date_str not in history:
                history[date_str] = resolved_val
                added_count += 1
            else:
                if history[date_str] != resolved_val:
                    history[date_str] = resolved_val
                    updated_count += 1

        if added_count > 0 or updated_count > 0:
            content["general"]["athlete"]["weightHistory"] = dict(sorted(history.items()))
            with open(YAML_FILE, 'w') as f:
                yaml.dump(content, f)

        return {
            "status": "success", 
            "added": added_count, 
            "updated": updated_count,
            "total_in_request": len(batch.data),
            "resolution_mode": RESOLUTION
        }

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")