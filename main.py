from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel
import logging
import os
import requests
import random
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional

# Load environment variables from .env file
load_dotenv()
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if not COHERE_API_KEY:
    raise ValueError("COHERE_API_KEY is not set in the environment variables.")

ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin]

if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = ["http://localhost:5173", "https://music-playlist-generator.netlify.app"]

print(f"App running in {ENVIRONMENT} mode")
print("Allowed Origins:", ALLOWED_ORIGINS)

# Initialize FastAPI app
app = FastAPI()

# CORS policy to allow Vue frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Request model
class GenreRequest(BaseModel):
    genre: str

# Rate limiting configuration
RATE_LIMIT = 10  # requests per hour
RATE_WINDOW =  3600 # 1 hr then resets
ip_request_count: Dict[str, List[float]] = {}

# Rate limiting middleware
async def rate_limit(request: Request):
    client_ip = request.client.host
    current_time = time.time()
    
    # Initialize if this is the first request from this IP
    if client_ip not in ip_request_count:
        ip_request_count[client_ip] = []
    
    # Remove timestamps older than the rate window
    ip_request_count[client_ip] = [t for t in ip_request_count[client_ip] if current_time - t < RATE_WINDOW]
    
    # Check if the request exceeds the rate limit
    if len(ip_request_count[client_ip]) >= RATE_LIMIT:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    
    # Add the current timestamp to the list
    ip_request_count[client_ip].append(current_time)
    
    return True

# Song list function using Cohere
def generate_song_list(genre: str):
    prompt = f"Suggest 10 {genre} songs with their artists. Format each line as 'Song - Artist' with no numbering or additional text."

    headers = {
        "Authorization": f"Bearer {COHERE_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "command", 
        "prompt": prompt,
        "max_tokens": 200  # Increased to get more songs
    }

    try:
        response = requests.post("https://api.cohere.ai/generate", headers=headers, json=data)
        response_json = response.json()

        if response.status_code != 200 or "text" not in response_json:
            logger.error("Invalid response from Cohere API: %s", response_json)
            raise HTTPException(status_code=500, detail="Error communicating with Cohere API")

        playlist_text = response_json["text"].strip()
        all_songs = []

        for line in playlist_text.split("\n"):
            line = line.strip()
            # Skip empty lines or lines without the expected format
            if not line or " - " not in line:
                continue
                
            # Remove any numbering or bullet points
            if line[0].isdigit() and line[1:3] in ['. ', ') ']:
                line = line[3:].strip()
            elif line[0] == '-' and line[1:2] == ' ':
                line = line[2:].strip()
                
            # Split into title and artist
            if " - " in line:
                title, artist = line.split(" - ", 1)
                all_songs.append({"title": title.strip(), "artist": artist.strip()})

        # Filter out songs with placeholder values
        valid_songs = [song for song in all_songs if song["title"].lower() != "unknown song" and 
                                                   song["artist"].lower() != "unknown artist"]

        # If we have enough valid songs, pick 5 random ones
        if len(valid_songs) >= 5:
            return random.sample(valid_songs, 5)
        
        # If we don't have enough valid songs, use what we have and fill the rest with placeholders
        logger.warning(f"Not enough valid songs returned for genre: {genre}. Using {len(valid_songs)} valid songs.")
        playlist = valid_songs.copy()
        
        # Fill missing slots with placeholder songs
        while len(playlist) < 5:
            playlist.append({"title": "Unknown Song", "artist": "Unknown Artist"})
            
        return playlist

    except Exception as e:
        logger.exception("Error generating playlist")
        raise HTTPException(status_code=500, detail=f"Error generating playlist: {str(e)}")

# API Endpoint with rate limiting
@app.post("/generate_song_list/")
async def get_song_list(request: GenreRequest, rate_limited: bool = Depends(rate_limit)):
    if not request.genre:
        logger.warning("Genre is missing in request")
        raise HTTPException(status_code=400, detail="Genre is required.")
    
    # Basic input validation
    if len(request.genre) > 100:
        raise HTTPException(status_code=400, detail="Genre name is too long.")
    
    logger.info("Generating playlist for genre: %s", request.genre)
    playlist = generate_song_list(request.genre)
    return {"genre": request.genre, "playlist": playlist}

@app.get("/")
def home():
    return {"message": "Music Playlist Generator API is running!"}