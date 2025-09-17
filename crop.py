import streamlit as st
import requests
import pandas as pd
import google.generativeai as genai

# ---- Configure Gemini ----
genai.configure(api_key=st.secrets["gcp"]["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash")

# ---- Utility: Get Weather Forecast ----
def get_weather_forecast(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_mean,weathercode&forecast_days=7&timezone=auto"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching weather data: {e}")
        return None

# ---- Crop Recommendation via Gemini ----
def get_crop_recommendation(inputs, weather_df):
    input_text = f"""
    Soil conditions: N={inputs['N']}, P={inputs['P']}, K={inputs['K']}, Temp={inputs['temperature']}°C, 
    Humidity={inputs['humidity']}%, pH={inputs['ph']}, Rainfall={inputs['rainfall']}mm.
    Upcoming weather forecast: {weather_df.to_dict(orient="records")}
    Based on this and knowledge of Indian agriculture crops like rice, wheat, maize, chickpeas, kidneybeans, pigeonpeas, mothbeans, mungbean, blackgram, lentil, pomegranate, etc.,
    Suggest the most suitable crop(s) to grow now with reasoning.
    """
    response = model.generate_content(input_text)
    return response.text

# ---- Irrigation Advice via Gemini ----
def get_irrigation_advice(crop, weather_data, soil_moisture):
    prompt = f"""
    You are an agricultural expert. Answer in 2-3 lines only but give an accurate water need and irrigation plan with intervals.
    The farmer wants to grow **{crop}**.
    The next 7 days weather forecast is:
    {weather_data}
    The current soil moisture level is approximately {soil_moisture}%.

    Please recommend:
    1. How much water should be provided (approx liters/hectare or irrigation level).
    2. At what intervals (daily, alternate days, weekly).
    3. Adjust irrigation plan if there is rainfall expected.
    4. Mention if special care is needed due to storm or extreme weather.
    Give a clear, structured, practical answer.
    """
    response = model.generate_content(prompt)
    return response.text

# ---- Streamlit UI ----
st.title("🌿 Smart Agriculture Assistant")

# Select Mode
mode = st.radio("Choose Mode:", ["🌾 Crop Recommendation", "💧 Irrigation Advisor"])

# Enter Coordinates Instead of City
st.markdown("📍 **Enter Location Coordinates**")
lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=28.6139, format="%.6f")
lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=77.2090, format="%.6f")

weather_data = get_weather_forecast(lat, lon)
if not weather_data:
    st.warning("⚠️ Weather data unavailable.")
    st.stop()

# ---- Crop Recommendation Mode ----
if mode == "🌾 Crop Recommendation":
    st.subheader("📋 Enter Soil & Climate Data")
    N = st.number_input("Nitrogen (N)", 0, 200, 50)
    P = st.number_input("Phosphorus (P)", 0, 200, 50)
    K = st.number_input("Potassium (K)", 0, 200, 50)
    temperature = st.number_input("Temperature (°C)", -10, 50, 25)
    humidity = st.number_input("Humidity (%)", 0, 100, 60)
    ph = st.number_input("Soil pH", 0.0, 14.0, 6.5)
    rainfall = st.number_input("Rainfall (mm)", 0, 500, 100)

    if st.button("📌 Recommend Crop"):
        # Prepare Weather DF
        weather_df = pd.DataFrame({
            "Date": weather_data["daily"]["time"],
            "Min Temp (°C)": weather_data["daily"]["temperature_2m_min"],
            "Max Temp (°C)": weather_data["daily"]["temperature_2m_max"],
            "Rainfall (mm)": weather_data["daily"]["precipitation_sum"],
            "Humidity (%)": weather_data["daily"]["relative_humidity_2m_mean"]
        })

        st.subheader("📊 7-Day Weather Forecast")
        st.dataframe(weather_df)

        # Get Crop Suggestion
        inputs = {"N": N, "P": P, "K": K, "temperature": temperature, "humidity": humidity, "ph": ph, "rainfall": rainfall}
        recommendation = get_crop_recommendation(inputs, weather_df)
        st.subheader("🌱 Recommended Crop(s)")
        st.write(recommendation)

# ---- Irrigation Advisor Mode ----
elif mode == "💧 Irrigation Advisor":
    st.subheader("💦 Irrigation Advisor")
    crop = st.text_input("Enter your crop (e.g., rice, wheat):")
    soil_moisture = st.slider("Current Soil Moisture (%)", 0, 100, 30)

    if st.button("💧 Get Irrigation Advice") and crop:
        weather_summary = {
            "date": weather_data["daily"]["time"],
            "min_temp": weather_data["daily"]["temperature_2m_min"],
            "max_temp": weather_data["daily"]["temperature_2m_max"],
            "precipitation": weather_data["daily"]["precipitation_sum"],
            "humidity": weather_data["daily"]["relative_humidity_2m_mean"]
        }

        advice = get_irrigation_advice(crop, weather_summary, soil_moisture)
        st.subheader("✅ Irrigation Advice")
        st.write(advice)

        st.subheader("📆 7-Day Weather Forecast")
        for i, date in enumerate(weather_data["daily"]["time"]):
            st.write(
                f"📅 {date} | 🌡️ {weather_data['daily']['temperature_2m_min'][i]}°C - "
                f"{weather_data['daily']['temperature_2m_max'][i]}°C | 💧 {weather_data['daily']['precipitation_sum'][i]}mm | "
                f"💨 Humidity {weather_data['daily']['relative_humidity_2m_mean'][i]}%"
            )
