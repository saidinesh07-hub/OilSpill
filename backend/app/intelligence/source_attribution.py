from typing import Dict, Any, List
from datetime import datetime
import math

class SourceAttributionEngine:
    def __init__(self):
        pass

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0 # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _calculate_time_diff_hours(self, t1: str, t2: str) -> float:
        try:
            dt1 = datetime.fromisoformat(t1.replace("Z", "+00:00"))
            dt2 = datetime.fromisoformat(t2.replace("Z", "+00:00"))
            return abs((dt1 - dt2).total_seconds()) / 3600.0
        except:
            return 999.0

    def attribute_sources(self, 
                          spill_lat: float, 
                          spill_lon: float, 
                          spill_time: str, 
                          vessels: List[Dict[str, Any]], 
                          infrastructure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        
        possible_sources = []
        
        # Check vessels
        for v in vessels:
            dist = self._haversine(spill_lat, spill_lon, v["latitude"], v["longitude"])
            time_diff = self._calculate_time_diff_hours(spill_time, v["timestamp"])
            
            if dist < 15.0 and time_diff < 24.0: # 15km and 24h window
                confidence = "LOW"
                if dist < 2.0 and time_diff < 1.0:
                    confidence = "HIGH"
                elif dist < 5.0 and time_diff < 4.0:
                    confidence = "MEDIUM"
                
                possible_sources.append({
                    "category": "VESSEL ACTIVITY",
                    "object_name": v["name"],
                    "distance_km": round(dist, 2),
                    "time_difference_hours": round(time_diff, 2),
                    "evidence": f"Vessel observed {round(dist, 1)}km from spill center, {round(time_diff, 1)} hours difference from satellite observation.",
                    "confidence": confidence,
                    "explanation": "Vessel was observed near the potential slick during the relevant observation window.",
                    "data_source": v["source"]
                })
        
        # Check infrastructure
        for infra in infrastructure:
            dist = self._haversine(spill_lat, spill_lon, infra["latitude"], infra["longitude"])
            
            if dist < 20.0:
                confidence = "LOW"
                if dist < 1.0:
                    confidence = "HIGH"
                elif dist < 5.0:
                    confidence = "MEDIUM"
                    
                possible_sources.append({
                    "category": infra["type"],
                    "object_name": infra["name"],
                    "distance_km": round(dist, 2),
                    "time_difference_hours": None, # Static
                    "evidence": f"Static infrastructure located {round(dist, 1)}km from spill center.",
                    "confidence": confidence,
                    "explanation": "Static infrastructure in close proximity to the spill.",
                    "data_source": infra["source"]
                })
        
        # Sort by confidence and distance
        conf_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        possible_sources.sort(key=lambda x: (-conf_map.get(x["confidence"], 0), x["distance_km"]))
        
        if not possible_sources:
             possible_sources.append({
                  "category": "UNKNOWN",
                  "object_name": "Unknown",
                  "distance_km": None,
                  "time_difference_hours": None,
                  "evidence": "No vessels or infrastructure found within correlation limits.",
                  "confidence": "LOW",
                  "explanation": "Unable to attribute a source based on available AIS and infrastructure data.",
                  "data_source": "System"
             })
             
        return possible_sources
