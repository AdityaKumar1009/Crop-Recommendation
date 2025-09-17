import streamlit as st
import requests
import google.generativeai as genai

# ---- Configure Gemini ----
genai.configure(api_key=st.secrets["gcp"]["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash")

# ---- Utility: Get Weather Forecast ----
def get_weather_forecast(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&daily=temperature_2m_max,"
        f"temperature_2m_min,precipitation_sum,relative_humidity_2m_mean,"
        f"weathercode&current_weather=true&timezone=auto"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching weather data: {e}")
        return None

# ---- Gemini: Enhanced Irrigation Advice ----
def get_irrigation_advice(crop, farm_size, soil_type, growth_stage, soil_moisture, weather_data):
    current_temp = weather_data['current_weather']['temperature']
    wind_speed = weather_data['current_weather']['windspeed']
    relative_humidity = weather_data['daily']['relative_humidity_2m_mean'][0]
    effective_rainfall = weather_data['daily']['precipitation_sum'][0]

    weather_summary = (
        f"High temperature ({current_temp}°C), "
        f"Wind speed ({wind_speed} km/h), "
        f"Sunny or partly cloudy based on weathercode {weather_data['daily']['weathercode'][0]}"
    )

    prompt = f"""
    Based on the following data, calculate the **exact irrigation water needed** for my crop in **cubic meters (m³) per day**, and provide a clear, practical **daily irrigation schedule**:

    - **Crop**: {crop}
    - **Farm Size**: {farm_size} hectares
    - **Soil Type**: {soil_type}
    - **Crop Growth Stage**: {growth_stage}
    - **Current Weather Conditions**: {weather_summary}
    - **Effective Rainfall (last 24h)**: {effective_rainfall} mm
    - **Current Soil Moisture**: {soil_moisture}% of field capacity
    - **Current Relative Humidity**: {relative_humidity}%

    Provide:
    1. Water requirement in m³/day.
    2. Ideal irrigation interval (daily, alternate days, etc.).
    3. Adjustments based on rainfall or extreme weather.
    4. Practical advice on efficient water use for the soil type.

    Only give facts and practical recommendations in 2-3 lines. Avoid any vague recommendations or suggestions or Disclaimer.
    """

    response = model.generate_content(prompt)
    return response.text

# ---- Streamlit UI ----
st.title("💧 Smart Irrigation Advisor")

# ---- Location Input ----
st.markdown("📍 **Enter Your Farm Location (Coordinates)**")
lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=28.6139, format="%.6f")
lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=77.2090, format="%.6f")

weather_data = get_weather_forecast(lat, lon)
if not weather_data:
    st.warning("⚠️ Weather data unavailable.")
    st.stop()

# ---- User Inputs ----
st.subheader("🧾 Farm & Crop Details")

crop = st.text_input("Crop Name (e.g., Rice, Maize)", "")
farm_size = st.number_input("Farm Size (in hectares)", min_value=0.1, value=1.0, step=0.1)
soil_type = st.selectbox("Soil Type", ["Alluvial", "Black", "Clay", "Sandy", "Sandy Loam", "Loamy", "Laterite"])
growth_stage = st.selectbox("Crop Growth Stage", ["Germination", "Vegetative", "Flowering", "Fruiting", "Maturity"])
soil_moisture = st.slider("Current Soil Moisture (% of field capacity)", 0, 100, 50)

# ---- Get Advice Button ----
if st.button("💧 Get Irrigation Advice") and crop:
    # Create markdown weather table
    weather_table = "| Date | Min Temp (°C) | Max Temp (°C) | Rainfall (mm) | Humidity (%) |\n"
    weather_table += "|------|----------------|----------------|----------------|---------------|\n"

    for i in range(len(weather_data["daily"]["time"])):
        date = weather_data["daily"]["time"][i]
        t_min = weather_data["daily"]["temperature_2m_min"][i]
        t_max = weather_data["daily"]["temperature_2m_max"][i]
        rain = weather_data["daily"]["precipitation_sum"][i]
        humidity = weather_data["daily"]["relative_humidity_2m_mean"][i]
        weather_table += f"| {date} | {t_min} | {t_max} | {rain} | {humidity} |\n"

    # Show weather forecast table
    st.subheader("📊 7-Day Weather Forecast")
    st.markdown(weather_table)

    # Get Gemini's irrigation advice
    advice = get_irrigation_advice(crop, farm_size, soil_type, growth_stage, soil_moisture, weather_data)
    st.subheader("✅ Irrigation Recommendation")
    st.write(advice)
