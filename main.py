from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
import logging
import os
import requests
import time
import re
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import random

# Load environment variables from .env file
load_dotenv()
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if not COHERE_API_KEY:
    raise ValueError("COHERE_API_KEY is not set in the environment variables.")

ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin]

if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = ["http://localhost:5173", "https://music-playlist-generator.netlify.app"]

# Rate limiting configuration
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))  # requests per day
RATE_WINDOW = 86400  # 24 hours in seconds

print(f"App running in {ENVIRONMENT} mode")
print("Allowed Origins:", ALLOWED_ORIGINS)
print(f"Rate limit: {RATE_LIMIT} requests per day")

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

# In-memory store for rate limiting
# In production, you might want to use Redis or another shared store
class RateLimiter:
    def __init__(self):
        self.requests: Dict[str, List[float]] = {}

    def check_rate_limit(self, ip: str) -> bool:
        current_time = time.time()
        if ip not in self.requests:
            self.requests[ip] = []
        
        # Remove timestamps older than the window
        self.requests[ip] = [timestamp for timestamp in self.requests[ip] 
                           if current_time - timestamp < RATE_WINDOW]
        
        # Check if user has exceeded rate limit
        if len(self.requests[ip]) >= RATE_LIMIT:
            return False
        
        # Add current request timestamp
        self.requests[ip].append(current_time)
        return True

rate_limiter = RateLimiter()

# Rate limiter dependency
async def check_rate_limit(request: Request):
    client_ip = request.client.host
    if not rate_limiter.check_rate_limit(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=429, 
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT} requests per day."
        )
    return client_ip

# Clean text helper function
def clean_text(text):
    # Remove extra quotes
    text = text.replace('"', '').replace('"', '').replace('"', '')
    # Remove any extraneous formatting
    text = text.strip()
    return text

# Modified Song list function using Cohere to ensure randomness with improved parsing
def generate_song_list(genre: str):
    # Adding randomness parameter to the prompt to get different results each time
    random_seed = random.randint(1, 10000)
    prompt = f"""Suggest 5 different {genre} songs with their artists. 
    Make the selection diverse and unexpected. Use seed {random_seed} for randomness.
    Format each line exactly like this: Song Title - Artist Name
    Do not include album names, record labels, or any additional information.
    Do not number the items.
    Example format:
    Bohemian Rhapsody - Queen
    Imagine - John Lennon"""
    
    headers = {
        "Authorization": f"Bearer {COHERE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "command",
        "prompt": prompt,
        "max_tokens": 150,
        "temperature": 0.9,  # Higher temperature for more randomness
        "k": 0,              # Disable top-k sampling for more diverse outputs
        "p": 0.9             # Use nucleus sampling for better quality
    }
    
    try:
        response = requests.post("https://api.cohere.ai/generate", headers=headers, json=data)
        response_json = response.json()
        
        if response.status_code != 200 or "text" not in response_json:
            logger.error("Invalid response from Cohere API: %s", response_json)
            raise HTTPException(status_code=500, detail="Error communicating with Cohere API")
        
        playlist_text = response_json["text"].strip()
        playlist = []
        
        # Log the raw response for debugging
        logger.info(f"Raw response text: {playlist_text}")
        
        # Process each line in the response
        for line in playlist_text.split("\n"):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Remove any numbering at the beginning (like "1. " or "1) ")
            line = re.sub(r'^\d+[\.\)]?\s*', '', line)

            # Add a second pass to catch multiple numbering patterns:
            line = re.sub(r'^\d+[\.\)\:]?\s*', '', line)  # Run twice to catch nested numbering
            
            # Try to split by " - " to separate title and artist
            if " - " in line:
                parts = line.split(" - ", 1)
                title = clean_text(parts[0])
                artist = clean_text(parts[1])
                
                # Further clean up: ensure we're not keeping album names or record labels
                # Most common pattern is artist name followed by album/label
                if " " in artist and any(separator in artist for separator in [":", "-", "/"]):
                    for separator in [":", "-", "/"]:
                        if separator in artist:
                            artist = artist.split(separator)[0].strip()
                
                # Only add if both title and artist are not empty
                if title and artist:
                    playlist.append({"title": title, "artist": artist})
        
        if not playlist:
            logger.warning("Empty playlist generated for genre: %s", genre)
            return [{"title": f"Random {genre} Song {i}", "artist": f"Artist {i}"} for i in range(1, 6)]
        
        # Ensure exactly 5 songs are returned
        if len(playlist) > 5:
            # Randomly select 5 songs for more variety
            playlist = random.sample(playlist, 5)
        elif len(playlist) < 5:
            logger.warning(f"Less than 5 songs returned for genre: {genre}. Filling missing slots.")
            existing_count = len(playlist)
            for i in range(5 - existing_count):
                playlist.append({"title": f"Random {genre} Song", "artist": f"Artist {i+1}"})
        
        logger.info(f"Generated playlist for genre: {genre}")
        logger.info(f"Final playlist: {playlist}")
        return playlist
    
    except Exception as e:
        logger.exception("Error generating playlist")
        raise HTTPException(status_code=500, detail=f"Error generating playlist: {str(e)}")

# API Endpoint with rate limiting
@app.post("/generate_song_list/")
async def get_song_list(request: GenreRequest, client_ip: str = Depends(check_rate_limit)):
    if not request.genre:
        logger.warning("Genre is missing in request")
        raise HTTPException(status_code=400, detail="Genre is required.")
    
    logger.info(f"Generating playlist for genre: {request.genre} for client: {client_ip}")
    playlist = generate_song_list(request.genre)
    return {"genre": request.genre, "playlist": playlist}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": ENVIRONMENT}

# Rate limit status endpoint
@app.get("/rate_limit_status")
async def rate_limit_status(client_ip: str = Depends(check_rate_limit)):
    requests_made = len(rate_limiter.requests.get(client_ip, []))
    remaining = RATE_LIMIT - requests_made
    return {
        "total_limit": RATE_LIMIT,
        "requests_made": requests_made,
        "remaining": remaining,
        "resets_in": f"{RATE_WINDOW // 3600} hours"
    }
    
@app.get("/")
def home():
    return {"message": "Music Playlist Generator API is running!"}