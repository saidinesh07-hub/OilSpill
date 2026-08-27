from pathlib import Path
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

# ============================================================
# CONFIGURATION
# ============================================================

DATA = Path("data/ocean_currents_test.nc")
OUT = Path("data")

# Initial oil spill
SPILL_LAT = 14.0
SPILL_LON = 82.0

# Forecast
HOURS = 48
DT_HOURS = 1.0

# Particle ensemble
N = 2000

# Horizontal diffusion in degrees/hour
DIFFUSION = 0.0035

# Small stochastic current uncertainty
CURRENT_NOISE = 0.035

# Reproducibility
SEED = 42

# Surface depth index
SURFACE_DEPTH_INDEX = 0


# ============================================================
# DATA LOADING
# ============================================================

def load_surface():
    """
    Load the surface ocean current field from the Copernicus
    NetCDF file.

    Expected dataset structure:

        time       = 1
        depth      = 8
        latitude   = 241
        longitude  = 241

    Variables:

        uo = eastward current velocity
        vo = northward current velocity
    """

    if not DATA.exists():
        raise FileNotFoundError(
            f"\nDataset not found:\n{DATA.resolve()}"
        )

    print("=" * 70)
    print("LOADING COPERNICUS MARINE DATASET")
    print("=" * 70)

    ds = xr.open_dataset(DATA)

    print(f"Dimensions: {dict(ds.sizes)}")
    print(f"Variables : {list(ds.data_vars)}")

    # --------------------------------------------------------
    # Detect velocity variable names
    # --------------------------------------------------------

    if "uo" in ds:
        u_name = "uo"
    elif "u" in ds:
        u_name = "u"
    else:
        raise ValueError(
            "Could not find eastward current variable "
            "('uo' or 'u')."
        )

    if "vo" in ds:
        v_name = "vo"
    elif "v" in ds:
        v_name = "v"
    else:
        raise ValueError(
            "Could not find northward current variable "
            "('vo' or 'v')."
        )

    print(f"Eastward current : {u_name}")
    print(f"Northward current: {v_name}")

    # --------------------------------------------------------
    # Coordinates
    # --------------------------------------------------------

    if "latitude" not in ds.coords:
        raise ValueError("Dataset has no latitude coordinate.")

    if "longitude" not in ds.coords:
        raise ValueError("Dataset has no longitude coordinate.")

    lat = ds["latitude"].values.astype(float)
    lon = ds["longitude"].values.astype(float)

    # --------------------------------------------------------
    # Select time and surface depth
    # --------------------------------------------------------

    u_da = ds[u_name]
    v_da = ds[v_name]

    if "time" in u_da.dims:
        u_da = u_da.isel(time=0)

    if "time" in v_da.dims:
        v_da = v_da.isel(time=0)

    if "depth" in u_da.dims:
        u_da = u_da.isel(depth=SURFACE_DEPTH_INDEX)

    if "depth" in v_da.dims:
        v_da = v_da.isel(depth=SURFACE_DEPTH_INDEX)

    # Remove singleton dimensions if any remain
    u_da = u_da.squeeze()
    v_da = v_da.squeeze()

    u = np.asarray(u_da.values, dtype=float)
    v = np.asarray(v_da.values, dtype=float)

    # --------------------------------------------------------
    # Validate shape
    # --------------------------------------------------------

    expected_shape = (len(lat), len(lon))

    if u.shape != expected_shape:
        raise ValueError(
            f"Unexpected u shape: {u.shape}\n"
            f"Expected: {expected_shape}"
        )

    if v.shape != expected_shape:
        raise ValueError(
            f"Unexpected v shape: {v.shape}\n"
            f"Expected: {expected_shape}"
        )

    # --------------------------------------------------------
    # Sort latitude
    # --------------------------------------------------------

    if lat[0] > lat[-1]:
        lat = lat[::-1]
        u = u[::-1, :]
        v = v[::-1, :]

    # --------------------------------------------------------
    # Sort longitude
    # --------------------------------------------------------

    if lon[0] > lon[-1]:
        lon = lon[::-1]
        u = u[:, ::-1]
        v = v[:, ::-1]

    # --------------------------------------------------------
    # Dataset statistics
    # --------------------------------------------------------

    valid = np.isfinite(u) & np.isfinite(v)

    if not np.any(valid):
        raise ValueError("No valid ocean-current values found.")

    print()
    print("DATASET LOADED SUCCESSFULLY")
    print("-" * 70)
    print(f"Longitude : {lon.min():.2f}°E -> {lon.max():.2f}°E")
    print(f"Latitude  : {lat.min():.2f}°N -> {lat.max():.2f}°N")
    print(f"Grid      : {len(lat)} x {len(lon)}")
    print(f"U range   : {np.nanmin(u):.3f} -> {np.nanmax(u):.3f} m/s")
    print(f"V range   : {np.nanmin(v):.3f} -> {np.nanmax(v):.3f} m/s")
    print(
        f"Speed max : {np.nanmax(np.hypot(u, v)):.3f} m/s"
    )

    if "time" in ds.coords:
        print(f"Dataset time: {ds['time'].values}")

    if "depth" in ds.coords:
        print(
            f"Surface depth: "
            f"{float(ds['depth'].values[SURFACE_DEPTH_INDEX]):.3f} m"
        )

    print("-" * 70)

    ds.close()

    return lat, lon, u, v


# ============================================================
# GRID HELPERS
# ============================================================

def nearest_index(array, value):
    """Return nearest grid index."""

    idx = np.searchsorted(array, value)

    idx = max(0, min(idx, len(array) - 1))

    if idx > 0:
        if abs(array[idx - 1] - value) < abs(array[idx] - value):
            idx -= 1

    return idx


def current_at(lat0, lon0, lat, lon, u, v):
    """
    Get current velocity at a particle position.

    If the nearest cell is land/NaN, search nearby ocean cells.
    """

    lat0 = float(np.clip(lat0, lat[0], lat[-1]))
    lon0 = float(np.clip(lon0, lon[0], lon[-1]))

    i0 = nearest_index(lat, lat0)
    j0 = nearest_index(lon, lon0)

    # Normal case
    if np.isfinite(u[i0, j0]) and np.isfinite(v[i0, j0]):
        return float(u[i0, j0]), float(v[i0, j0])

    # Search nearby valid ocean cells
    best = None
    best_distance = np.inf

    max_radius = 12

    for radius in range(1, max_radius + 1):

        i_min = max(0, i0 - radius)
        i_max = min(len(lat), i0 + radius + 1)

        j_min = max(0, j0 - radius)
        j_max = min(len(lon), j0 + radius + 1)

        for i in range(i_min, i_max):
            for j in range(j_min, j_max):

                if not (
                    np.isfinite(u[i, j])
                    and np.isfinite(v[i, j])
                ):
                    continue

                dlat = lat[i] - lat0

                dlon = (
                    lon[j] - lon0
                ) * np.cos(np.deg2rad(lat0))

                distance = dlat ** 2 + dlon ** 2

                if distance < best_distance:
                    best_distance = distance
                    best = (
                        float(u[i, j]),
                        float(v[i, j])
                    )

        if best is not None:
            return best

    # If absolutely no nearby ocean point exists
    return 0.0, 0.0


# ============================================================
# PARTICLE MOVEMENT
# ============================================================

def move_particle(
    lat0,
    lon0,
    lat,
    lon,
    u,
    v,
    rng
):
    """
    Move one oil particle for one hour.

    Components:

        1. Ocean-current advection
        2. Small current uncertainty
        3. Diffusion / turbulent spreading
    """

    cu, cv = current_at(
        lat0,
        lon0,
        lat,
        lon,
        u,
        v
    )

    # --------------------------------------------------------
    # Add small uncertainty to current velocity
    # --------------------------------------------------------

    cu += rng.normal(0, CURRENT_NOISE)
    cv += rng.normal(0, CURRENT_NOISE)

    # --------------------------------------------------------
    # Convert m/s -> m/hour
    # --------------------------------------------------------

    east_meters = cu * 3600.0
    north_meters = cv * 3600.0

    # --------------------------------------------------------
    # Convert meters -> degrees
    # --------------------------------------------------------

    new_lat = lat0 + (
        north_meters / 111320.0
    )

    cos_lat = max(
        np.cos(np.deg2rad(lat0)),
        0.15
    )

    meters_per_degree_lon = (
        111320.0 * cos_lat
    )

    new_lon = lon0 + (
        east_meters / meters_per_degree_lon
    )

    # --------------------------------------------------------
    # Turbulent diffusion
    # --------------------------------------------------------

    new_lat += rng.normal(
        0,
        DIFFUSION
    )

    new_lon += rng.normal(
        0,
        DIFFUSION / cos_lat
    )

    # --------------------------------------------------------
    # Keep inside dataset domain
    # --------------------------------------------------------

    new_lat = np.clip(
        new_lat,
        lat[0],
        lat[-1]
    )

    new_lon = np.clip(
        new_lon,
        lon[0],
        lon[-1]
    )

    return new_lat, new_lon


# ============================================================
# SIMULATION
# ============================================================

def simulate(lat, lon, u, v):

    rng = np.random.default_rng(SEED)

    steps = int(HOURS / DT_HOURS) + 1

    particle_lat = np.full(
        (steps, N),
        SPILL_LAT,
        dtype=float
    )

    particle_lon = np.full(
        (steps, N),
        SPILL_LON,
        dtype=float
    )

    print()
    print("=" * 70)
    print("RUNNING OIL SPILL PARTICLE SIMULATION")
    print("=" * 70)

    print(f"Forecast duration : {HOURS} hours")
    print(f"Particles         : {N}")
    print(f"Time step         : {DT_HOURS} hour")
    print(f"Diffusion         : {DIFFUSION}")
    print(f"Current uncertainty: {CURRENT_NOISE}")

    for t in range(1, steps):

        for p in range(N):

            la = particle_lat[t - 1, p]
            lo = particle_lon[t - 1, p]

            la, lo = move_particle(
                la,
                lo,
                lat,
                lon,
                u,
                v,
                rng
            )

            particle_lat[t, p] = la
            particle_lon[t, p] = lo

        if t % 6 == 0 or t == steps - 1:

            mean_lat = particle_lat[t].mean()
            mean_lon = particle_lon[t].mean()

            print(
                f"{t:02d}h -> "
                f"{mean_lat:.3f}°N, "
                f"{mean_lon:.3f}°E"
            )

    print("=" * 70)

    return particle_lat, particle_lon


# ============================================================
# STATISTICS
# ============================================================

def calculate_statistics(lats, lons):

    final_lat = lats[-1]
    final_lon = lons[-1]

    mean_lat = lats.mean(axis=1)
    mean_lon = lons.mean(axis=1)

    center_lat = np.mean(final_lat)
    center_lon = np.mean(final_lon)

    # 50% region
    lat25, lat75 = np.percentile(
        final_lat,
        [25, 75]
    )

    lon25, lon75 = np.percentile(
        final_lon,
        [25, 75]
    )

    # 90% region
    lat5, lat95 = np.percentile(
        final_lat,
        [5, 95]
    )

    lon5, lon95 = np.percentile(
        final_lon,
        [5, 95]
    )

    # Displacement
    dlat = center_lat - SPILL_LAT
    dlon = center_lon - SPILL_LON

    north_km = dlat * 111.32

    east_km = (
        dlon
        * 111.32
        * np.cos(np.deg2rad(SPILL_LAT))
    )

    displacement_km = np.sqrt(
        north_km ** 2 +
        east_km ** 2
    )

    # Maximum particle displacement
    particle_north = (
        final_lat - SPILL_LAT
    ) * 111.32

    particle_east = (
        final_lon - SPILL_LON
    ) * 111.32 * np.cos(
        np.deg2rad(SPILL_LAT)
    )

    particle_distance = np.sqrt(
        particle_north ** 2 +
        particle_east ** 2
    )

    max_distance = np.max(
        particle_distance
    )

    return {
        "mean_lat": mean_lat,
        "mean_lon": mean_lon,

        "center_lat": center_lat,
        "center_lon": center_lon,

        "lat25": lat25,
        "lat75": lat75,

        "lon25": lon25,
        "lon75": lon75,

        "lat5": lat5,
        "lat95": lat95,

        "lon5": lon5,
        "lon95": lon95,

        "displacement_km": displacement_km,
        "max_distance_km": max_distance
    }


# ============================================================
# SAVE CSV
# ============================================================

def save_csv(lats, lons):

    OUT.mkdir(
        parents=True,
        exist_ok=True
    )

    rows = np.column_stack([
        np.repeat(
            np.arange(lats.shape[0]),
            N
        ),

        np.tile(
            np.arange(N),
            lats.shape[0]
        ),

        lats.ravel(),
        lons.ravel()
    ])

    csv_path = (
        OUT /
        "oil_spill_48h_prediction.csv"
    )

    np.savetxt(
        csv_path,
        rows,
        delimiter=",",
        header=(
            "hour,"
            "particle_id,"
            "latitude,"
            "longitude"
        ),
        comments=""
    )

    print(
        f"CSV saved: {csv_path.resolve()}"
    )


# ============================================================
# PREDICTION MAP
# ============================================================

def plot_prediction(
    lat,
    lon,
    u,
    v,
    lats,
    lons,
    stats
):

    speed = np.hypot(
        u,
        v
    )

    fig, ax = plt.subplots(
        figsize=(15, 10)
    )

    # --------------------------------------------------------
    # Ocean current speed
    # --------------------------------------------------------

    im = ax.pcolormesh(
        lon,
        lat,
        speed,
        shading="auto",
        cmap="viridis"
    )

    cbar = fig.colorbar(
        im,
        ax=ax,
        pad=0.02
    )

    cbar.set_label(
        "Ocean Current Speed (m/s)",
        fontsize=13
    )

    # --------------------------------------------------------
    # Final particle cloud
    # --------------------------------------------------------

    ax.scatter(
        lons[-1],
        lats[-1],
        s=6,
        alpha=0.16,
        linewidths=0,
        label="48h predicted oil particles",
        zorder=3
    )

    # --------------------------------------------------------
    # Mean trajectory
    # --------------------------------------------------------

    ax.plot(
        stats["mean_lon"],
        stats["mean_lat"],
        linewidth=3.2,
        label="Mean oil trajectory",
        zorder=8
    )

    # --------------------------------------------------------
    # Initial spill
    # --------------------------------------------------------

    ax.scatter(
        SPILL_LON,
        SPILL_LAT,
        marker="*",
        s=420,
        edgecolor="black",
        linewidth=1.7,
        zorder=15,
        label="Initial spill"
    )

    # --------------------------------------------------------
    # 48h center
    # --------------------------------------------------------

    ax.scatter(
        stats["center_lon"],
        stats["center_lat"],
        marker="X",
        s=260,
        edgecolor="black",
        linewidth=1.7,
        zorder=15,
        label="48h predicted center"
    )

    # --------------------------------------------------------
    # 90% prediction rectangle
    # --------------------------------------------------------

    x = [
        stats["lon5"],
        stats["lon95"],
        stats["lon95"],
        stats["lon5"],
        stats["lon5"]
    ]

    y = [
        stats["lat5"],
        stats["lat5"],
        stats["lat95"],
        stats["lat95"],
        stats["lat5"]
    ]

    ax.plot(
        x,
        y,
        "--",
        linewidth=2,
        label="90% prediction envelope",
        zorder=7
    )

    # --------------------------------------------------------
    # Time markers
    # --------------------------------------------------------

    for hour in [6, 12, 24, 36, 48]:

        if hour >= len(
            stats["mean_lat"]
        ):
            continue

        xh = stats["mean_lon"][hour]
        yh = stats["mean_lat"][hour]

        ax.scatter(
            xh,
            yh,
            s=55,
            edgecolor="white",
            linewidth=1.2,
            zorder=12
        )

        ax.annotate(
            f"{hour}h",
            (xh, yh),
            xytext=(7, 7),
            textcoords="offset points",
            fontsize=10,
            fontweight="bold",
            zorder=20
        )

    # --------------------------------------------------------
    # Current arrows
    # --------------------------------------------------------

    si = max(
        1,
        len(lat) // 20
    )

    sj = max(
        1,
        len(lon) // 20
    )

    Lon, Lat = np.meshgrid(
        lon[::sj],
        lat[::si]
    )

    U = u[::si, ::sj]
    V = v[::si, ::sj]

    good = (
        np.isfinite(U)
        &
        np.isfinite(V)
    )

    ax.quiver(
        Lon[good],
        Lat[good],
        U[good],
        V[good],
        color="white",
        alpha=0.42,
        scale=14,
        width=0.0018,
        zorder=5
    )

    # --------------------------------------------------------
    # Prediction information box
    # --------------------------------------------------------

    info = (
        "48-HOUR FORECAST\n"
        f"Center: "
        f"{stats['center_lat']:.2f}°N, "
        f"{stats['center_lon']:.2f}°E\n"
        f"Displacement: "
        f"{stats['displacement_km']:.1f} km\n"
        f"Maximum particle distance: "
        f"{stats['max_distance_km']:.1f} km"
    )

    ax.annotate(
        info,
        xy=(
            stats["center_lon"],
            stats["center_lat"]
        ),
        xytext=(25, 40),
        textcoords="offset points",
        fontsize=11,
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.5",
            fc="white",
            ec="black",
            alpha=0.92
        ),
        arrowprops=dict(
            arrowstyle="->",
            linewidth=1.5
        ),
        zorder=30
    )

    # --------------------------------------------------------
    # Titles
    # --------------------------------------------------------

    ax.set_title(
        "48-Hour Oil Spill Drift Prediction\n"
        "Copernicus Marine Surface Currents + "
        "Particle Dispersion Model",
        fontsize=20,
        fontweight="bold",
        pad=14
    )

    ax.set_xlabel(
        "Longitude (°E)",
        fontsize=13
    )

    ax.set_ylabel(
        "Latitude (°N)",
        fontsize=13
    )

    ax.set_xlim(
        lon[0],
        lon[-1]
    )

    ax.set_ylim(
        lat[0],
        lat[-1]
    )

    ax.grid(
        True,
        linestyle="--",
        alpha=0.22
    )

    ax.legend(
        loc="upper right",
        framealpha=0.94
    )

    plt.tight_layout()

    png_path = (
        OUT /
        "oil_spill_48h_prediction.png"
    )

    plt.savefig(
        png_path,
        dpi=220,
        bbox_inches="tight"
    )

    print(
        f"\nMap saved: {png_path.resolve()}"
    )

    plt.show()


# ============================================================
# FINAL REPORT
# ============================================================

def print_report(stats):

    print()
    print("=" * 70)
    print("              48-HOUR OIL SPILL FORECAST")
    print("=" * 70)

    print(
        f"Initial spill     : "
        f"{SPILL_LAT:.2f}°N, "
        f"{SPILL_LON:.2f}°E"
    )

    print(
        f"Predicted center  : "
        f"{stats['center_lat']:.2f}°N, "
        f"{stats['center_lon']:.2f}°E"
    )

    print(
        f"Displacement      : "
        f"{stats['displacement_km']:.2f} km"
    )

    print(
        f"Maximum particle  : "
        f"{stats['max_distance_km']:.2f} km"
    )

    print()

    print(
        "50% prediction region:"
    )

    print(
        f"  Latitude : "
        f"{stats['lat25']:.2f}°N -> "
        f"{stats['lat75']:.2f}°N"
    )

    print(
        f"  Longitude: "
        f"{stats['lon25']:.2f}°E -> "
        f"{stats['lon75']:.2f}°E"
    )

    print()

    print(
        "90% prediction region:"
    )

    print(
        f"  Latitude : "
        f"{stats['lat5']:.2f}°N -> "
        f"{stats['lat95']:.2f}°N"
    )

    print(
        f"  Longitude: "
        f"{stats['lon5']:.2f}°E -> "
        f"{stats['lon95']:.2f}°E"
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "This forecast uses the available Copernicus "
        "surface-current snapshot."
    )

    print(
        "The current dataset contains only one time step, "
        "so this model does NOT claim to use 48 hourly "
        "current forecasts."
    )

    print(
        "Wind, waves, evaporation, weathering and "
        "shoreline interaction are not included."
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("        OIL SPILL DRIFT PREDICTION SYSTEM")
    print("=" * 70)

    # Load dataset
    lat, lon, u, v = load_surface()

    # Validate spill location
    if not (
        lat[0]
        <= SPILL_LAT
        <= lat[-1]
    ):
        raise ValueError(
            "Initial spill latitude is outside dataset."
        )

    if not (
        lon[0]
        <= SPILL_LON
        <= lon[-1]
    ):
        raise ValueError(
            "Initial spill longitude is outside dataset."
        )

    # Run particle model
    lats, lons = simulate(
        lat,
        lon,
        u,
        v
    )

    # Calculate forecast statistics
    stats = calculate_statistics(
        lats,
        lons
    )

    # Save CSV
    save_csv(
        lats,
        lons
    )

    # Print report
    print_report(
        stats
    )

    # Plot
    plot_prediction(
        lat,
        lon,
        u,
        v,
        lats,
        lons,
        stats
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()