"""
Weather search provider using Open-Meteo API.
Migrated from legacy weather.py module.
"""

import requests
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..providers.base import SearchProvider


class WeatherError(Exception):
    """Base exception for weather module errors."""
    pass


class WeatherTimeoutError(WeatherError):
    """Raised when weather API request times out."""
    pass


class WeatherLocationError(WeatherError):
    """Raised when location cannot be resolved."""
    pass


class WeatherProvider(SearchProvider):
    """Open-Meteo weather provider with structured data retrieval."""
    
    BASE_URL = "https://api.open-meteo.com/v1"
    GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
    TIMEOUT_SECONDS = 10
    
    def __init__(self, timeout=None):
        self.timeout = timeout or 10  # Default to 10 seconds per requestseconds per request
    
    def supports(self, request) -> bool:
        """Check if this is a weather-related request."""
        query_lower = (request.original_query or "").lower()
        return any(word in query_lower for word in [
            "weather", "temperature", "forecast", "rain", "snow", 
            "sunny", "cloudy", "wind", "humidity"
        ])
    
    async def search(self, request):
        """Execute weather search and return normalized result."""
        from ..models import SearchResult
        
        try:
            # Determine location to query
            query_location = None
            if request.location:
                query_location = self._format_location(request.location)
            
            if not query_location:
                raise WeatherError("No location available to query weather.")
            
            # Step 1: Geocode
            geo = self.geocode(query_location)
            
            # Step 2: Get current conditions
            current = self.get_current_weather(geo["lat"], geo["lon"], geo["timezone"])
            
            # Step 3: Get today's forecast
            try:
                forecast = self.get_forecast(geo["lat"], geo["lon"], geo["timezone"])
            except WeatherError:
                forecast = None
            
            # Step 4: Get alerts
            try:
                alerts = self.get_alerts(geo["lat"], geo["lon"])
            except WeatherError:
                alerts = []
            
            weather_data = {
                "location": geo,
                "current": current,
                "forecast": forecast,
                "alerts": alerts,
                "retrieved_at": datetime.now(timezone.utc)
            }
            
            # Format response using deterministic formatter (no LLM needed)
            response_text = self.format_weather_response(weather_data)
            
            return SearchResult(
                request_id=request.request_id,
                category="weather",
                original_query=request.original_query,
                interpreted_query=f"current weather in {query_location}",
                entities={"location": query_location},
                data=response_text,
                sources=[{"name": "Open-Meteo API", "url": self.BASE_URL}],
                retrieved_at=datetime.now(timezone.utc),
                freshness=0.0,
                confidence=1.0
            )
            
        except WeatherError as e:
            return SearchResult(
                request_id=request.request_id,
                category="weather",
                original_query=request.original_query,
                error=str(e)
            )
    
    def geocode(self, location_name):
        """Resolve a location name to coordinates."""
        try:
            params = {
                "name": location_name,
                "count": 1,
                "format": "json"
            }
            response = requests.get(self.GEOCODE_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            if not data.get("results"):
                raise WeatherLocationError(f"No location found for: {location_name}")
            
            result = data["results"][0]
            return {
                "lat": result["latitude"],
                "lon": result["longitude"],
                "city": result.get("name", ""),
                "region": result.get("admin1", ""),
                "country": result.get("country", ""),
                "timezone": result.get("timezone", "")
            }
        except requests.Timeout:
            raise WeatherTimeoutError(f"Geocoding timed out for: {location_name}")
        except requests.RequestException as e:
            raise WeatherLocationError(f"Geocoding failed for '{location_name}': {e}")
    
    def get_current_weather(self, lat, lon, timezone_str=None):
        """Get current weather conditions."""
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                           "is_day,precipitation,rain,snow,weather_code,"
                           "cloud_cover,pressure_msl,surface_pressure,"
                           "wind_speed_10m,wind_direction_10m,wind_gusts_10m"
            }
            if timezone_str:
                params["timezone"] = timezone_str
            
            response = requests.get(f"{self.BASE_URL}/forecast", params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            current = data.get("current", {})
            
            # Get timestamp from API or use now
            time_str = current.get("time")
            if time_str:
                try:
                    observation_time = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                except ValueError:
                    observation_time = datetime.now(timezone.utc)
            else:
                observation_time = datetime.now(timezone.utc)
            
            return {
                "temperature": current.get("temperature_2m"),
                "apparent_temperature": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "is_day": current.get("is_day"),
                "precipitation": current.get("precipitation"),
                "rain": current.get("rain"),
                "snow": current.get("snow"),
                "weather_code": current.get("weather_code"),
                "conditions": self._decode_weather_code(current.get("weather_code")),
                "cloud_cover": current.get("cloud_cover"),
                "pressure": current.get("pressure_msl"),
                "wind_speed": current.get("wind_speed_10m"),
                "wind_direction": current.get("wind_direction_10m"),
                "wind_gusts": current.get("wind_gusts_10m"),
                "observation_time": observation_time,
                "timezone": timezone_str or data.get("timezone", "")
            }
        except requests.Timeout:
            raise WeatherTimeoutError("Weather API request timed out")
        except requests.RequestException as e:
            raise WeatherError(f"Weather API request failed: {e}")
    
    def get_forecast(self, lat, lon, timezone_str=None):
        """Get today's weather forecast."""
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,"
                         "precipitation_probability_max,weather_code,"
                         "wind_speed_10m_max,sunrise,sunset",
                "forecast_days": 1
            }
            if timezone_str:
                params["timezone"] = timezone_str
            
            response = requests.get(f"{self.BASE_URL}/forecast", params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            daily = data.get("daily", {})
            
            if not daily.get("time"):
                return None
            
            today_data = {
                "date": daily["time"][0],
                "high_temp": daily["temperature_2m_max"][0] if daily.get("temperature_2m_max") else None,
                "low_temp": daily["temperature_2m_min"][0] if daily.get("temperature_2m_min") else None,
                "precipitation_probability": daily["precipitation_probability_max"][0] if daily.get("precipitation_probability_max") else None,
                "weather_code": daily["weather_code"][0] if daily.get("weather_code") else None,
                "conditions": self._decode_weather_code(daily["weather_code"][0]) if daily.get("weather_code") else None,
                "max_wind_speed": daily["wind_speed_10m_max"][0] if daily.get("wind_speed_10m_max") else None
            }
            
            return today_data
        except requests.Timeout:
            raise WeatherTimeoutError("Forecast API request timed out")
        except requests.RequestException as e:
            raise WeatherError(f"Forecast API request failed: {e}")
    
    def get_alerts(self, lat, lon):
        """Get active weather alerts for a location."""
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "alert": "active"
            }
            
            response = requests.get(f"{self.BASE_URL}/forecast", params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            alerts = []
            
            for alert in data.get("alerts", []):
                alerts.append({
                    "event": alert.get("event", ""),
                    "severity": alert.get("severity", ""),
                    "headline": alert.get("headline", ""),
                    "description": alert.get("description", ""),
                    "onset": alert.get("start"),
                    "expires": alert.get("end")
                })
            
            return alerts
        except requests.Timeout:
            raise WeatherTimeoutError("Alerts API request timed out")
        except requests.RequestException as e:
            # Alerts endpoint may not be available for all locations
            return []
    
    def _decode_weather_code(self, code):
        """Decode WMO weather code to human-readable condition."""
        if code is None:
            return "unknown"
        
        codes = {
            0: "clear sky",
            1: "mainly clear",
            2: "partly cloudy",
            3: "overcast",
            45: "fog",
            48: "depositing rime fog",
            51: "light drizzle",
            53: "moderate drizzle",
            55: "dense drizzle",
            56: "light freezing drizzle",
            57: "dense freezing drizzle",
            61: "slight rain",
            63: "moderate rain",
            65: "heavy rain",
            66: "light freezing rain",
            67: "heavy freezing rain",
            71: "slight snowfall",
            73: "moderate snowfall",
            75: "heavy snowfall",
            77: "snow grains",
            80: "slight rain showers",
            81: "moderate rain showers",
            82: "violent rain showers",
            85: "slight snow showers",
            86: "heavy snow showers",
            95: "thunderstorm",
            96: "thunderstorm with slight hail",
            99: "thunderstorm with heavy hail"
        }
        
        return codes.get(code, f"weather code {code}")
    
    def format_weather_response(self, weather_data):
        """Format weather data into a natural-language response."""
        location = weather_data["location"]
        current = weather_data["current"]
        forecast = weather_data["forecast"]
        alerts = weather_data["alerts"]
        
        # Build location string
        parts = []
        if location.get("city"):
            parts.append(location["city"])
        if location.get("region"):
            parts.append(location["region"])
        if location.get("country"):
            parts.append(location["country"])
        location_str = ", ".join(parts)
        
        # Current conditions
        temp = current.get("temperature")
        apparent_temp = current.get("apparent_temperature")
        conditions = current.get("conditions", "unknown")
        
        if temp is not None:
            temp_str = f"{temp:.0f}°C"
            if apparent_temp is not None and abs(apparent_temp - temp) > 2:
                temp_str += f" (feels like {apparent_temp:.0f}°C)"
        else:
            temp_str = "unavailable"
        
        response_parts = [
            f"In {location_str}, it's currently {temp_str} and {conditions}."
        ]
        
        # Wind info
        wind_speed = current.get("wind_speed")
        wind_dir = current.get("wind_direction")
        if wind_speed is not None:
            dir_str = self._compass_direction(wind_dir) if wind_dir else ""
            response_parts.append(f"Winds are {wind_speed:.0f} km/h{f' from the {dir_str}' if dir_str else ''}.")
        
        # Humidity
        humidity = current.get("humidity")
        if humidity is not None:
            response_parts.append(f"Humidity is {humidity:.0f}%.")
        
        # Today's forecast
        if forecast:
            high = forecast.get("high_temp")
            low = forecast.get("low_temp")
            precip_prob = forecast.get("precipitation_probability")
            
            if high is not None and low is not None:
                response_parts.append(f"Today's high will be {high:.0f}°C with a low of {low:.0f}°C.")
            
            if precip_prob is not None:
                if precip_prob > 0:
                    response_parts.append(f"There's a {precip_prob:.0f}% chance of precipitation today.")
        
        # Weather alerts
        if alerts:
            for alert in alerts[:2]:  # Limit to first two alerts
                event = alert.get("event", "weather alert")
                severity = alert.get("severity", "")
                headline = alert.get("headline", "")
                response_parts.append(f"Active {severity} alert: {event}. {headline}")
        else:
            response_parts.append("There are currently no active weather alerts.")
        
        # Timestamp
        retrieved_at = weather_data["retrieved_at"]
        time_str = retrieved_at.strftime("%H:%M UTC")
        response_parts.append(f"Weather data was retrieved at {time_str}.")
        
        return " ".join(response_parts)
    
    def _compass_direction(self, degrees):
        """Convert wind direction in degrees to compass direction."""
        if degrees is None:
            return ""
        
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        index = int((degrees + 22.5) / 45) % 8
        return directions[index]
    
    def _format_location(self, location):
        """Format location dict to string."""
        parts = []
        if location.get("city"):
            parts.append(location["city"])
        if location.get("region"):
            parts.append(location["region"])
        if location.get("country"):
            parts.append(location["country"])
        return ", ".join(parts)
