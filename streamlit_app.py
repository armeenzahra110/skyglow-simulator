import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# App configurations
st.set_page_config(page_title="SkyGlow: Spectral & Atmospheric Light Pollution Simulator", layout="wide")

st.title("🌌 SkyGlow: Atmospheric Scattering & Visibility Simulator")
st.markdown("""
This computational model calculates the propagation of artificial skyglow based on **Rayleigh scattering**, 
**Mie scattering (aerosols/smog)**, and **optical fixture shielding design**. Use this tool to predict stellar limiting magnitude drops in urban planning models.
""")

st.sidebar.header("🔧 Simulation Parameters")

# Sidebar Controls
lamp_type = st.sidebar.selectbox(
    "Select Urban Lighting Technology", 
    ["Cool LED (4000K)", "Warm LED (2200K)", "Sodium (HPS)"]
)

shield_type = st.sidebar.selectbox(
    "Select Fixture Shielding Design", 
    ["Unshielded", "Semi-Shielded", "Fully Shielded"]
)

aerosol_level = st.sidebar.slider(
    "Aerosol Optical Depth (Smog/Humidity)", 
    0.0, 1.5, 0.2, step=0.1
)

num_lamps = st.sidebar.number_input(
    "Active Streetlights (Scale)", 
    min_value=100, max_value=50000, value=5000, step=500
)

# Insert the core physics algorithms here (same mathematical equations from Part 1)
NATURAL_SKY_LUMINANCE = 0.00017  
WAVELENGTHS = {"Cool LED (4000K)": 450e-9, "Warm LED (2200K)": 590e-9, "Sodium (HPS)": 589e-9}

def calculate_rayleigh_coefficient(wavelength):
    return (550e-9 / wavelength) ** 4

def calculate_mie_coefficient(aerosol_level):
    return aerosol_level * 1.5

def calculate_shielding_factor(angle_deg, shield_type):
    angle_rad = np.radians(angle_deg)
    if shield_type == "Unshielded": return 1.0
    elif shield_type == "Semi-Shielded": return np.maximum(0.0, np.cos(angle_rad))
    elif shield_type == "Fully Shielded": return np.where(angle_deg < 45, np.cos(angle_rad)**2, 0.0)
    return 1.0

def calculate_limiting_magnitude(total_luminance):
    """
    Converts sky luminance (cd/m²) to Magnitudes per Square Arcsecond (MPSAS),
    and then calculates the true Naked-Eye Limiting Magnitude (NELM).
    """
    # Prevent division by zero or negative values
    total_luminance = max(1e-9, total_luminance)
    
    # 1. Convert cd/m² to MPSAS (standard astronomical scale)
    # Formula: mpsas = log10(cd/m² / 108000) / -0.4
    mpsas = np.log10(total_luminance / 108000.0) / -0.4
    
    # 2. Convert MPSAS to Naked-Eye Limiting Magnitude (NELM) using the Garstang model
    # Under pristine dark skies (MPSAS ~ 22), NELM is ~6.8.
    # In bright cities (MPSAS ~ 18), NELM drops down to ~3.0 or less.
    nelm = 7.93 - 5 * np.log10(10**(0.4 * (21.57 - mpsas)) + 1)
    
    return nelm
# Computation
wavelength = WAVELENGTHS[lamp_type]
rayleigh = calculate_rayleigh_coefficient(wavelength)
mie = calculate_mie_coefficient(aerosol_level)
total_scattering = (rayleigh * 0.7) + (mie * 0.3)

angles = np.linspace(0, 90, 100)
trapz_func = getattr(np, 'trapezoid', getattr(np, 'trapz', None))
escaped_light = trapz_func([calculate_shielding_factor(a, shield_type) for a in angles], np.radians(angles))
artificial_luminance = num_lamps * 1.5e-7 * total_scattering * escaped_light
total_luminance = NATURAL_SKY_LUMINANCE + artificial_luminance
limiting_mag = calculate_limiting_magnitude(total_luminance)

# Layout Columns
col1, col2 = st.columns(2)

with col1:
    st.metric(label="Calculated Sky Luminance", value=f"{total_luminance:.6f} cd/m²")
    st.info(f"**Naked-Eye Limiting Magnitude:** Stars up to magnitude **{limiting_mag:.2f}** are visible.")
with col2:
    # --- CALCULATE TRUE LIMITING MAGNITUDE ---
    # The new function directly takes our real-world total_luminance and outputs the correct NELM
    limiting_mag = calculate_limiting_magnitude(total_luminance)

    # --- INITIALIZE STABLE STARFIELD (Only once per session) ---
    if 'star_x' not in st.session_state:
        np.random.seed(42)  # Secure a fixed seed
        num_stars = 300     # Rich sky
        st.session_state.star_x = np.random.rand(num_stars) * 10
        st.session_state.star_y = np.random.rand(num_stars) * 10
        # Distribute magnitudes exponentially (lots of faint stars, few bright ones)
        st.session_state.star_mags = np.random.power(3.5, num_stars) * 7.0 

    # Retrieve persistent star data
    star_x = st.session_state.star_state_x if 'star_state_x' in st.session_state else st.session_state.star_x
    star_y = st.session_state.star_state_y if 'star_state_y' in st.session_state else st.session_state.star_y
    star_mags = st.session_state.star_state_mags if 'star_state_mags' in st.session_state else st.session_state.star_mags

    # Save to session state to prevent regeneration
    st.session_state.star_state_x = star_x
    st.session_state.star_state_y = star_y
    st.session_state.star_state_mags = star_mags

    # --- RENDER SIMULATED STAR-FIELD LOSS ---
    fig, ax = plt.subplots(figsize=(6, 6))
    
    # Dynamically change the sky background color based on skyglow intensity!
    # Pristine sky is near pitch black; heavily polluted sky turns a washed-out dark grey/blue.
    sky_brightness_factor = min(1.0, (total_luminance - NATURAL_SKY_LUMINANCE) / 0.05)
    
    # Blends from deep dark space to a hazy skyglow color
    bg_red = 14 / 255 + (sky_brightness_factor * 0.1)
    bg_green = 17 / 255 + (sky_brightness_factor * 0.15)
    bg_blue = 23 / 255 + (sky_brightness_factor * 0.25)
    
    fig.patch.set_facecolor((bg_red, bg_green, bg_blue))
    ax.set_facecolor((bg_red, bg_green, bg_blue))

    # Only draw stars that are physically brighter than the current limiting magnitude
    visible_mask = star_mags < limiting_mag
    visible_x = star_x[visible_mask]
    visible_y = star_y[visible_mask]
    visible_mags = star_mags[visible_mask]

    # Calculate realistic visual sizes (brighter stars are larger)
    sizes = (7.5 - visible_mags) ** 2.2

    # Plot double layers for a gorgeous "glowing" star effect
    # Layer 1: Outer glowing halo (semi-transparent, soft)
    ax.scatter(visible_x, visible_y, s=sizes*3, color='white', alpha=0.15, edgecolors='none')
    # Layer 2: Sharp stellar core (bright, solid)
    ax.scatter(visible_x, visible_y, s=sizes, color='white', alpha=0.95, edgecolors='none')

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')

    st.pyplot(fig)
    st.caption(f"Simulated sky view: Showing {sum(visible_mask)} out of 300 stars. Fainter stars systematically drop out as limiting magnitude worsens.")
