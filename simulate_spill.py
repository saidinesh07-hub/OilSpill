import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# OIL SPILL SIMULATION USING REAL COPERNICUS MARINE CURRENTS
# ============================================================

DATASET = "data/ocean_currents_test.nc"

# -----------------------------
# Load Copernicus dataset
# -----------------------------
ds = xr.open_dataset(DATASET)

u = ds["uo"].isel(time=0, depth=0).values
v = ds["vo"].isel(time=0, depth=0).values

lat = ds["latitude"].values
lon = ds["longitude"].values

# -----------------------------
# Oil spill starting location
# -----------------------------
spill_lon = 82.0
spill_lat = 14.0

# -----------------------------
# Simulation settings
# -----------------------------
NUM_PARTICLES = 500
HOURS = 48
DT_SECONDS = 15 * 60

steps = int(HOURS * 3600 / DT_SECONDS)

# Random generator for reproducibility
rng = np.random.default_rng(42)

# Start all particles around spill location
particle_lon = spill_lon + rng.normal(0, 0.015, NUM_PARTICLES)
particle_lat = spill_lat + rng.normal(0, 0.015, NUM_PARTICLES)

# Store trajectories
trajectory_lon = np.zeros((steps + 1, NUM_PARTICLES))
trajectory_lat = np.zeros((steps + 1, NUM_PARTICLES))

trajectory_lon[0] = particle_lon
trajectory_lat[0] = particle_lat


# ============================================================
# Find nearest ocean-current grid cell
# ============================================================

def get_current(latitude, longitude):

    lat_index = np.abs(lat - latitude).argmin()
    lon_index = np.abs(lon - longitude).argmin()

    current_u = u[lat_index, lon_index]
    current_v = v[lat_index, lon_index]

    if not np.isfinite(current_u):
        current_u = 0.0

    if not np.isfinite(current_v):
        current_v = 0.0

    return current_u, current_v


# ============================================================
# Move oil particles
# ============================================================

for step in range(1, steps + 1):

    for i in range(NUM_PARTICLES):

        current_u, current_v = get_current(
            particle_lat[i],
            particle_lon[i]
        )

        # Convert m/s → degrees
        meters_per_degree_lat = 111000.0

        meters_per_degree_lon = (
            111000.0 * np.cos(np.radians(particle_lat[i]))
        )

        delta_lon = (
            current_u * DT_SECONDS /
            meters_per_degree_lon
        )

        delta_lat = (
            current_v * DT_SECONDS /
            meters_per_degree_lat
        )

        # Small stochastic spreading component
        diffusion = 0.0008

        particle_lon[i] += (
            delta_lon +
            rng.normal(0, diffusion)
        )

        particle_lat[i] += (
            delta_lat +
            rng.normal(0, diffusion)
        )

    trajectory_lon[step] = particle_lon
    trajectory_lat[step] = particle_lat


# ============================================================
# Create final oil-spill map
# ============================================================

plt.figure(figsize=(12, 8))

# Current speed background
speed = np.sqrt(u ** 2 + v ** 2)

plt.imshow(
    speed,
    origin="lower",
    extent=[
        lon.min(),
        lon.max(),
        lat.min(),
        lat.max()
    ],
    aspect="auto"
)

plt.colorbar(label="Ocean Current Speed (m/s)")


# Draw particle trajectories
for i in range(0, NUM_PARTICLES, 5):

    plt.plot(
        trajectory_lon[:, i],
        trajectory_lat[:, i],
        linewidth=0.5,
        alpha=0.25
    )


# Final oil position
plt.scatter(
    trajectory_lon[-1],
    trajectory_lat[-1],
    s=8,
    label="Predicted oil position"
)


# Original spill location
plt.scatter(
    spill_lon,
    spill_lat,
    s=150,
    marker="*",
    label="Initial spill"
)


plt.xlabel("Longitude")
plt.ylabel("Latitude")

plt.title(
    "48-Hour Oil Spill Drift Prediction\n"
    "Driven by Copernicus Marine Ocean Currents"
)

plt.legend()

plt.tight_layout()

# Save result
plt.savefig(
    "data/oil_spill_prediction.png",
    dpi=200,
    bbox_inches="tight"
)

plt.show()


# ============================================================
# Save final particle coordinates
# ============================================================

np.savetxt(
    "data/oil_spill_final_positions.csv",
    np.column_stack(
        (particle_lon, particle_lat)
    ),
    delimiter=",",
    header="longitude,latitude",
    comments=""
)

print()
print("==============================================")
print("OIL SPILL SIMULATION COMPLETE")
print("==============================================")
print(f"Initial location: {spill_lon}E, {spill_lat}N")
print(f"Simulation duration: {HOURS} hours")
print(f"Particles: {NUM_PARTICLES}")
print()
print("Created:")
print("data/oil_spill_prediction.png")
print("data/oil_spill_final_positions.csv")
print("==============================================")