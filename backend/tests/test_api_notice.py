import pytest
from app.db.models.detection_result import DetectionResult
from app.db.models.user import User
from app.api.deps import get_current_user
from app.main import app

# Mock user for dependency override
mock_user = User(id=1, email="test@example.com", is_active=True, operator_id="JH-0001")

def override_get_current_user():
    return mock_user

def test_send_notice_success(client, db_session, mock_smtp):
    # 1. Setup: Create a detection result in the test DB
    det = DetectionResult(
        id=101,
        scraped_video_id=1,
        verdict="VIOLATED",
        phash_score=0.95,
        pdq_score=0.95,
        audio_score=0.95,
        final_score=0.95,
        dispatch_status="PENDING"
    )
    db_session.add(det)
    db_session.commit()

    # 2. Setup: Override current user dependency
    app.dependency_overrides[get_current_user] = override_get_current_user

    # 3. Act: Call the API
    payload = {
        "detection_id": 101,
        "recipient_email": "legal@platform.com",
        "subject": "Copyright Infringement",
        "content": "Please take down this video.",
        "attachments": []
    }
    
    response = client.post("/notice/send", json=payload)

    # 4. Assert: Status code and response body
    assert response.status_code == 200
    assert response.json()["status"] == "dispatched"
    
    # 5. Assert: Verify SMTP was called
    assert mock_smtp.called
    
    # 6. Assert: Verify DB update
    updated_det = db_session.query(DetectionResult).filter(DetectionResult.id == 101).first()
    assert updated_det.dispatch_status == "DISPATCHED"
    assert updated_det.dispatched_at is not None

    # Cleanup
    app.dependency_overrides.pop(get_current_user)

def test_send_notice_not_found(client, db_session):
    # Setup: Override current user
    app.dependency_overrides[get_current_user] = override_get_current_user

    payload = {
        "detection_id": 999, # Non-existent
        "recipient_email": "legal@platform.com",
        "subject": "Missing",
        "content": "...",
        "attachments": []
    }
    
    response = client.post("/notice/send", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # Cleanup
    app.dependency_overrides.pop(get_current_user)
