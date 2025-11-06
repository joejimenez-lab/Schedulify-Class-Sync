import os, requests, pytest

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8001")

@pytest.mark.parametrize("filename", [
    "ss1.png",  # add your actual file names
    # "schedule2.jpg",
])
def test_extract_gemini(filename):
    path = os.path.join(os.path.dirname(__file__), filename)
    assert os.path.exists(path), f"File not found: {path}"

    with open(path, "rb") as f:
        files = {"file": (filename, f, "image/png")}
        data = {
            "start_date": "2025-01-27",
            "end_date": "2025-03-02",
        }
        response = requests.post(f"{BASE_URL}/extract-gemini", files=files, data=data, timeout=120)

    print("Response status:", response.status_code)
    print("Response text:", response.text[:500])

    assert response.status_code == 200, f"Error: {response.text}"
    result = response.json()
    assert "events" in result, "No events key found in response"
    assert isinstance(result["events"], list), "events should be a list"
    assert len(result["events"]) > 0, "No events extracted"
