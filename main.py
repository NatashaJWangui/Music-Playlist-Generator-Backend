from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import os
import requests
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
print("Loaded API Key:", COHERE_API_KEY)

if not COHERE_API_KEY:
    raise ValueError("COHERE_API_KEY is not set in the environment variables.")

# Initialize FastAPI app
app = FastAPI()

# CORS policy to allow Vue frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# Song list function using Cohere
def generate_song_list(genre: str):
    prompt = f"Suggest 5 {genre} songs with their artists. Format: Song - Artist."

    headers = {
        "Authorization": f"Bearer {COHERE_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "command", 
        "prompt": prompt,
        "max_tokens": 100
    }

    try:
        response = requests.post("https://api.cohere.ai/generate", headers=headers, json=data)
        response_json = response.json()

        if response.status_code != 200 or "text" not in response_json:
            logger.error("Invalid response from Cohere API: %s", response_json)
            raise HTTPException(status_code=500, detail="Error communicating with Cohere API")

        playlist_text = response_json["text"].strip()
        playlist = []

        for line in playlist_text.split("\n"):
            if " - " in line:
                title, artist = line.split(" - ", 1)
                playlist.append({"title": title.strip(), "artist": artist.strip()})

        if not playlist:
            logger.warning("Empty playlist generated for genre: %s", genre)
            return [{"title": "Unknown Song", "artist": "Unknown Artist"}]

        # **Ensure exactly 5 songs are returned**
        if len(playlist) > 5:
            playlist = playlist[:5]  # Take only the first 5 songs
        elif len(playlist) < 5:
            logger.warning(f"Less than 5 songs returned for genre: {genre}. Filling missing slots.")
            while len(playlist) < 5:
                playlist.append({"title": "Unknown Song", "artist": "Unknown Artist"})  # Placeholder songs if empty

        logger.info(f"Generated playlist for genre: {genre}")
        return playlist

    except Exception as e:
        logger.exception("Error generating playlist")
        raise HTTPException(status_code=500, detail=f"Error generating playlist: {str(e)}")

# API Endpoint
@app.post("/generate_song_list/")
async def get_song_list(request: GenreRequest):
    if not request.genre:
        logger.warning("Genre is missing in request")
        raise HTTPException(status_code=400, detail="Genre is required.")
    
    logger.info("Generating playlist for genre: %s", request.genre)
    playlist = generate_song_list(request.genre)
    return {"genre": request.genre, "playlist": playlist}

@app.get("/")
def home():
    return {"message": "Music Playlist Generator API is running!"}
