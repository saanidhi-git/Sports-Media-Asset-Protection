import sys
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api():
    print("Testing /health")
    response = client.get("/health")
    assert response.status_code == 200, f"Health check failed: {response.text}"
    print("OK: Health check passed")

    # Generate unique test user
    test_user = f"test_{uuid.uuid4().hex[:8]}@example.com"
    test_operator = f"OP_{uuid.uuid4().hex[:8]}"
    test_password = "password123"

    print(f"\nTesting POST /api/v1/users/register ({test_user})")
    reg_response = client.post("/api/v1/users/register", json={
        "email": test_user,
        "password": test_password,
        "operator_id": test_operator,
        "operating_system": "win32"
    })
    assert reg_response.status_code == 201, f"Registration failed: {reg_response.text}"
    print("OK: Registration passed")

    print("\nTesting POST /api/v1/login/access-token")
    login_response = client.post("/api/v1/login/access-token", data={
        "username": test_user,
        "password": test_password
    })
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("OK: Login passed")

    print("\nTesting GET /api/v1/users/me")
    me_response = client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 200, f"Get /users/me failed: {me_response.text}"
    print("OK: Get current user passed")

    print("\nTesting GET /api/v1/assets/")
    assets_response = client.get("/api/v1/assets/", headers=headers)
    assert assets_response.status_code == 200, f"Get /assets/ failed: {assets_response.text}"
    print("OK: Get assets passed")

    print("\nTesting GET /api/v1/pipeline/jobs")
    jobs_response = client.get("/api/v1/pipeline/jobs", headers=headers)
    assert jobs_response.status_code == 200, f"Get /pipeline/jobs failed: {jobs_response.text}"
    print("OK: Get jobs passed")
    
    print("\nTesting GET /api/v1/review/queue")
    review_response = client.get("/api/v1/review/queue", headers=headers)
    assert review_response.status_code == 200, f"Get /review/queue failed: {review_response.text}"
    print("OK: Get review queue passed")

    print("\nAll basic route tests passed successfully!")

if __name__ == "__main__":
    test_api()
