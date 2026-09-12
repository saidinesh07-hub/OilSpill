from typing import List, Optional
from pydantic import BaseModel, Field

class OsirisPort(BaseModel):
    name: str
    country: Optional[str] = None
    lat: float
    lng: float
    type: Optional[str] = None
    volume: Optional[str] = None
    rank: Optional[int] = None
    congestion: Optional[str] = None
    dwell_time: Optional[str] = None

class OsirisChokepoint(BaseModel):
    name: str
    lat: float
    lng: float
    traffic: Optional[str] = None
    risk: Optional[str] = None

class OsirisVessel(BaseModel):
    id: Optional[int] = None
    mmsi: Optional[int] = None
    timestamp: int
    name: Optional[str] = None
    lat: float
    lng: float
    speed: Optional[float] = None
    course: Optional[float] = None
    trueHeading: Optional[float] = None
    heading: Optional[float] = None
    rot: Optional[int] = None
    navStatus: Optional[int] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    callsign: Optional[str] = None
    imo: Optional[int] = None
    draught: Optional[float] = None
    eta: Optional[str] = None
    length: Optional[int] = None
    typeCode: Optional[int] = None
    type: Optional[str] = "other"

class OsirisMaritimeResponse(BaseModel):
    ports: List[OsirisPort] = Field(default_factory=list)
    chokepoints: List[OsirisChokepoint] = Field(default_factory=list)
    ships: List[OsirisVessel] = Field(default_factory=list)
    total_ports: int = 0
    total_chokepoints: int = 0
    total_ships: int = 0
    kpler_status: Optional[str] = None
    timestamp: Optional[str] = None
