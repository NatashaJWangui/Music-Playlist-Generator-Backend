from fastapi.testclient import TestClient
from main import app  
import pytest
from unittest.mock import patch

client = TestClient(app)

def test_generate_song_list():
    response = client.post("/generate_song_list/", json={"genre": "Afrobeats"})
    assert response.status_code == 200
    assert "playlist" in response.json()
    assert isinstance(response.json()["playlist"], list)
    assert len(response.json()["playlist"]) == 5

def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Music Playlist Generator API is running!"}

def test_missing_genre():
    response = client.post("/generate_song_list/", json={"genre": ""})
    assert response.status_code == 400
    assert "detail" in response.json()

def test_invalid_json():
    response = client.post("/generate_song_list/", json=None)
    assert response.status_code == 422  # FastAPI returns 422 for invalid JSON

@pytest.fixture
def mock_cohere_response():
    return {
        "text": "Song 1 - Artist 1\nSong 2 - Artist 2\nSong 3 - Artist 3\nSong 4 - Artist 4\nSong 5 - Artist 5"
    }

@patch("requests.post")
def test_generate_song_list_mocked(mock_post, mock_cohere_response):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = mock_cohere_response
    
    response = client.post("/generate_song_list/", json={"genre": "Afrobeats"})
    assert response.status_code == 200
    assert len(response.json()["playlist"]) == 5
    assert response.json()["playlist"][0]["title"] == "Song 1"
    assert response.json()["playlist"][0]["artist"] == "Artist 1"

@patch("requests.post")
def test_cohere_api_error(mock_post):
    mock_post.return_value.status_code = 500
    mock_post.return_value.json.return_value = {"error": "Some error"}
    
    response = client.post("/generate_song_list/", json={"genre": "Afrobeats"})
    assert response.status_code == 500
    assert "detail" in response.json()