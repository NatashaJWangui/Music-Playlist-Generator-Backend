# Music Playlist Generator - Backend

This is the **backend** for the **Music Playlist Generator**, built using **FastAPI**. The backend serves as an API that generates music playlists based on the user's selected genre. It leverages **Cohere AI** for song recommendations.

## Features

- **Song Recommendations**: Uses Cohere AI to generate song recommendations based on a given genre.
- **Playlist Generation**: Returns a list of 5 songs in the specified genre, including song title and artist.
- **CORS Support**: Configured to allow access from specific frontend origins.

## Technologies Used

- **Backend**: FastAPI (Python)
- **APIs**: Cohere AI for generating song recommendations.
- **Environment Variables**: `.env` for storing sensitive data like API keys.

## Backend Setup

### Prerequisites

- Python 3.x installed
- Cohere AI API Key

## Demo
- **Backend**: [Music Playlist Generator API (FastAPI)](https://music-playlist-generator-backend.onrender.com)

### Installation Instructions

1. **Clone the repository:**

    ```bash
    git clone https://github.com/NatashaJWangui/Music-Playlist-Generator-Backend.git
    cd music-backend
    ```

2. **Install required dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3. **Set up environment variables:**

   Create a `.env` file in the `music-backend` directory and add your **Cohere API Key**:

    ```env
    COHERE_API_KEY=your_cohere_api_key_here
    ALLOWED_ORIGINS=http://localhost:5173,https://music-playlist-generator.netlify.app
    ```

4. **Run the backend server:**

    ```bash
    bash start_server.sh
    ```

    The server will start running at `http://localhost:8000`.


## API Documentation

### POST `/generate_song_list/`

**Request:**
- `genre` (string): The genre for the playlist (e.g., "soul", "Afrobeats").

**Response:**
Returns a JSON object with the requested genre and a playlist of 5 recommended songs.

#### Example Request:

```json
{
  "genre": "soul"
}
```

#### Example Response:

```json
{
  "genre": "soul",
  "playlist": [
    { "title": "Song 1", "artist": "Artist 1" },
    { "title": "Song 2", "artist": "Artist 2" },
    { "title": "Song 3", "artist": "Artist 3" },
    { "title": "Song 4", "artist": "Artist 4" },
    { "title": "Song 5", "artist": "Artist 5" }
  ]
}
```

## Testing

To run tests for the FastAPI backend:

```bash
pytest
```

## Frontend Integration

The frontend is built with **Vue.js** and can be found here:  
[Music Playlist Generator (Vue.js)](https://github.com/NatashaJWangui/Music-Playlist-Generator.git).

## Roadmap

- Improve API response accuracy with additional data sources.
- Add caching for better performance.
- Expand genre support with more detailed recommendations.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
