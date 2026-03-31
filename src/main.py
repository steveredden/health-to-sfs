from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from ruamel.yaml import YAML
from typing import Dict
import json
import os

app = FastAPI(docs_url=None, redoc_url=None)
yaml = YAML()
# Set default if env var is missing
YAML_FILE = os.getenv("CONFIG_PATH", "/config/config.yaml")

# --- SECURITY OVERRIDE ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log the real error to your Docker logs so YOU can see it
    print(f"DEBUG:    Validation Error: {exc.errors()}") 
    
    # Return a generic message to the PUBLIC internet
    return JSONResponse(
        status_code=400,
        content={"detail": "Bad Request"},
    )
# -------------------------

class WeightBatch(BaseModel):
    data: Dict[str, str]

    @field_validator('data', mode='before')
    @classmethod
    def transform_string_to_dict(cls, v):
        # If Shortcuts sends the dictionary as a string, parse it manually
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Data must be a valid JSON string or dictionary")
        return v

def verify_api_key(x_api_key: str = Header(None)): # Change to None to make it optional to Pydantic
    if x_api_key is None or x_api_key != os.getenv("API_SECRET"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_api_key

@app.post("/ingest")
async def log_weight(batch: WeightBatch, authorized: str = Depends(verify_api_key)):
    try:
        # Load existing YAML
        if os.path.exists(YAML_FILE):
            with open(YAML_FILE, 'r') as f:
                content = yaml.load(f) or {}
        else:
            content = {"general": {"athlete": {"weightHistory": {}}}}

        history = content.setdefault("general", {}).setdefault("athlete", {}).setdefault("weightHistory", {})

        added_count = 0
        # 2. Loop through the incoming dictionary
        # Note: Your input shows weights as strings, so we convert to float
        for date_str, weight_val in batch.data.items():
            if date_str not in history:
                history[date_str] = float(weight_val)
                added_count += 1

        # 3. Save only if we added new data
        if added_count > 0:
            with open(YAML_FILE, 'w') as f:
                yaml.dump(content, f)

        return {"status": "success", "added": added_count, "total_in_request": len(batch.data)}

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")