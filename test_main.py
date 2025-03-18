from fastapi.testclient import TestClient
from main import app  

client = TestClient(app)

def test_generate_song_list():
    response = client.post("/generate_song_list/", json={"genre": "Afrobeats"})
    assert response.status_code == 200
    assert "playlist" in response.json()
    assert isinstance(response.json()["playlist"], list)
    assert len(response.json()["playlist"]) == 5
