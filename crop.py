import streamlit as st
import requests
import pandas as pd
import google.generativeai as genai

# Configure Gemini with Streamlit Secrets
genai.configure(api_key=st.secrets["gcp"]["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash")

# Get latitude/longitude using Open-Meteo Geocoding API
def get_lat_lon(city):
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
    res = requests.get(url).json()
    if "results" in res:
        lat = res["results"][0]["latitude"]
        lon = res["results"][0]["longitude"]
        return lat, lon
    else:
        return None, None

# Get weather forecast from Open-Meteo (no API key needed)
def get_weather(city):
    lat, lon = get_lat_lon(city)
    if lat is None:
        return pd.DataFrame()
    
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&forecast_days=7&timezone=auto"
    res = requests.get(url).json()
    
    forecast = []
    for i in range(len(res["daily"]["time"])):
        forecast.append({
            "date": res["daily"]["time"][i],
            "temp_max": res["daily"]["temperature_2m_max"][i],
            "temp_min": res["daily"]["temperature_2m_min"][i],
            "rainfall": res["daily"]["precipitation_sum"][i],
            "storm": "Yes" if res["daily"]["precipitation_sum"][i] > 20 else "No"  # simple rule
        })
    return pd.DataFrame(forecast)

# Streamlit UI
st.title("🌾 Crop Recommendation System with Gemini + 7-Day Weather Forecast")

city = st.text_input("Enter city name for weather forecast", "Delhi")
N = st.number_input("Nitrogen (N)", 0, 200, 50)
P = st.number_input("Phosphorus (P)", 0, 200, 50)
K = st.number_input("Potassium (K)", 0, 200, 50)
temperature = st.number_input("Temperature (°C)", -10, 50, 25)
humidity = st.number_input("Humidity (%)", 0, 100, 60)
ph = st.number_input("Soil pH", 0.0, 14.0, 6.5)
rainfall = st.number_input("Rainfall (mm)", 0, 500, 100)

if st.button("Recommend Crop"):
    weather_df = get_weather(city)
    if weather_df.empty:
        st.error("❌ Could not fetch weather data. Try another city.")
    else:
        st.subheader("📊 7-Day Weather Forecast")
        st.dataframe(weather_df)

        # Send input + weather to Gemini
        input_text = f"""
        Soil conditions: N={N}, P={P}, K={K}, Temp={temperature}°C, 
        Humidity={humidity}%, pH={ph}, Rainfall={rainfall}mm
        Upcoming weather forecast: {weather_df.to_dict(orient="records")}
        Based on this and knowledge of Indian agriculture crops like 
        rice, wheat, maize, chickpeas, kidneybeans, pigeonpeas, mothbeans, mungbean, blackgram, lentil, pomegranate etc.
        Suggest the most suitable crop(s) to grow now with reasoning.
        """

        response = model.generate_content(input_text)
        st.subheader("🌱 Recommended Crop(s)")
        st.write(response.text)
