"""
Multi-Temporal Slick Tracker and Associator
Associates detections across consecutive satellite passes using advection-compensated Hungarian matching.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy.optimize import linear_sum_assignment
from shapely.geometry import shape
from backend.app.core.logging import logger
from backend.app.geospatial.geometry_ops import get_geodesic_distance_km
from backend.app.temporal.evolution import classify_slick_evolution_state, calculate_kinematics


class MultiTemporalSlickTracker:
    """
    Tracks and associates oil slick polygons across multi-date SAR observations.
    """
    def __init__(
        self,
        max_matching_distance_km: float = 35.0,  # Max plausible physical drift window between passes
        max_area_ratio: float = 4.0,             # Max plausible expansion/contraction ratio
        distance_weight: float = 0.5,
        area_weight: float = 0.5
    ):
        self.max_matching_distance_km = max_matching_distance_km
        self.max_area_ratio = max_area_ratio
        self.distance_weight = distance_weight
        self.area_weight = area_weight

    def compute_cost_matrix(
        self,
        existing_tracks: List[Dict[str, Any]],
        new_detections: List[Dict[str, Any]],
        elapsed_hours: float = 24.0,
        estimated_advection_vector: Optional[Tuple[float, float]] = None  # (drift_lon_deg, drift_lat_deg)
    ) -> np.ndarray:
        """
        Builds matching cost matrix between existing tracks and incoming detections.
        Cost = w1 * normalized_distance + w2 * normalized_area_diff
        """
        n_tracks = len(existing_tracks)
        n_dets = len(new_detections)
        cost_matrix = np.full((n_tracks, n_dets), fill_value=1e5, dtype=np.float64)

        for i, track in enumerate(existing_tracks):
            t_lon = track["centroid_lon"]
            t_lat = track["centroid_lat"]
            t_area = track["area_km2"]

            # If advection estimate is available, advect prior centroid forward
            if estimated_advection_vector:
                t_lon += estimated_advection_vector[0]
                t_lat += estimated_advection_vector[1]

            for j, det in enumerate(new_detections):
                d_lon = det["centroid_lon"]
                d_lat = det["centroid_lat"]
                d_area = det["area_km2"]

                dist_km = get_geodesic_distance_km(t_lon, t_lat, d_lon, d_lat)
                if dist_km > self.max_matching_distance_km:
                    continue  # Keep high cost (unmatchable)

                # Area ratio penalty
                area_ratio = max(t_area, 1e-4) / max(d_area, 1e-4)
                if area_ratio > self.max_area_ratio or area_ratio < (1.0 / self.max_area_ratio):
                    continue

                norm_dist = dist_km / self.max_matching_distance_km
                norm_area_diff = abs(t_area - d_area) / max(t_area + d_area, 1e-4)

                cost = (self.distance_weight * norm_dist) + (self.area_weight * norm_area_diff)
                cost_matrix[i, j] = cost

        return cost_matrix

    def associate_detections(
        self,
        active_tracks: List[Dict[str, Any]],
        new_detections: List[Dict[str, Any]],
        observation_time: datetime
    ) -> Dict[str, Any]:
        """
        Executes Hungarian assignment to link incoming detections to existing tracks or create new tracks.
        
        Returns:
        - "matched_pairs": List of (track, detection, kinematics, state)
        - "unmatched_tracks": List of tracks with no match (potential disappearance)
        - "new_tracks": List of detections that form new tracks
        """
        if not active_tracks:
            return {
                "matched_pairs": [],
                "unmatched_tracks": [],
                "new_tracks": new_detections
            }

        if not new_detections:
            return {
                "matched_pairs": [],
                "unmatched_tracks": active_tracks,
                "new_tracks": []
            }

        cost_matrix = self.compute_cost_matrix(active_tracks, new_detections)
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        matched_pairs = []
        matched_track_indices = set()
        matched_det_indices = set()

        for r, c in zip(row_ind, col_ind):
            cost = cost_matrix[r, c]
            if cost < 1.0:  # Valid match threshold
                track = active_tracks[r]
                det = new_detections[c]

                kinematics = calculate_kinematics(
                    prev_lon=track["centroid_lon"],
                    prev_lat=track["centroid_lat"],
                    prev_time=track["last_seen"],
                    curr_lon=det["centroid_lon"],
                    curr_lat=det["centroid_lat"],
                    curr_time=observation_time,
                    prev_area_km2=track["area_km2"],
                    curr_area_km2=det["area_km2"]
                )

                state = classify_slick_evolution_state(
                    prev_area_km2=track["area_km2"],
                    curr_area_km2=det["area_km2"],
                    match_iou=1.0 - cost
                )

                matched_pairs.append({
                    "track": track,
                    "detection": det,
                    "kinematics": kinematics,
                    "state": state
                })

                matched_track_indices.add(r)
                matched_det_indices.add(c)

        unmatched_tracks = [
            active_tracks[i] for i in range(len(active_tracks)) if i not in matched_track_indices
        ]
        new_tracks = [
            new_detections[j] for j in range(len(new_detections)) if j not in matched_det_indices
        ]

        logger.info(
            f"Temporal Association complete: {len(matched_pairs)} matched, "
            f"{len(unmatched_tracks)} disappeared/unmatched, {len(new_tracks)} new tracks initiated."
        )

        return {
            "matched_pairs": matched_pairs,
            "unmatched_tracks": unmatched_tracks,
            "new_tracks": new_tracks
        }
