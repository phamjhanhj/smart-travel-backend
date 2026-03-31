"""Test suite cho AI Chat endpoints."""
import json
from unittest.mock import patch, AsyncMock
from uuid import UUID
import pytest

# Fake AI response
FAKE_CHAT_RESPONSE = r"""Chào bạn, đây là lịch trình gợi ý cho Đà Nẵng:
<!--SUGGESTION:itinerary
{"title": "Đà Nẵng ngày 1", "day_number": 1, "activities": [{"title": "Biển Mỹ Khê", "type": "attraction", "start_time": "08:00", "end_time": "10:00", "estimated_cost": 0}]}
-->
"""

async def mock_chat_stream_gen(*args, **kwargs):
    chunks = [
        "Chào bạn, ",
        "đây là lịch trình gợi ý:\n",
        r'<!--SUGGESTION:itinerary {"title": "Test", "day_number": 1, "activities": []} -->'
    ]
    for chunk in chunks:
        yield chunk

@pytest.fixture(autouse=True)
def mock_settings():
    with patch("app.api.routes.ai_chat.settings.GROQ_API_KEY", "fake_key"):
        yield

class TestAIChat:
    @patch("app.api.routes.ai_chat.ai_service.chat", new_callable=AsyncMock)
    def test_chat_non_stream_success(self, mock_chat, client, auth_headers, sample_trip):
        mock_chat.return_value = FAKE_CHAT_RESPONSE
        trip_id = sample_trip["id"]
        
        res = client.post(
            f"/api/trips/{trip_id}/chat",
            json={"message": "Gợi ý lịch trình ngày 1", "stream": False},
            headers=auth_headers
        )
        assert res.status_code == 200
        data = res.json()["data"]
        
        # Original message without suggestion block
        assert "Chào bạn" in data["message"]
        assert "<!--SUGGESTION" not in data["message"]
        assert "suggestion_id" in data
        assert data["suggestion_id"] is not None

        # Verify chat history saved
        hist_res = client.get(f"/api/trips/{trip_id}/chat/history", headers=auth_headers)
        assert hist_res.status_code == 200
        hist_data = hist_res.json()["data"]
        # History should have 2 messages: user and assistant
        assert len(hist_data) >= 2
        assert hist_data[-2]["role"] == "user"
        assert hist_data[-2]["message"] == "Gợi ý lịch trình ngày 1"
        assert hist_data[-1]["role"] == "assistant"

    @patch("app.api.routes.ai_chat.ai_service.chat_stream")
    def test_chat_stream_success(self, mock_stream, client, auth_headers, sample_trip):
        mock_stream.side_effect = mock_chat_stream_gen
        trip_id = sample_trip["id"]

        with client.stream("POST", f"/api/trips/{trip_id}/chat", json={"message": "Stream test", "stream": True}, headers=auth_headers) as res:
            assert res.status_code == 200
            
            lines = list(res.iter_lines())
            assert len(lines) > 0
            
            # Find the final line which contains "done": True
            final_data = None
            for line in lines:
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if payload.get("data", {}).get("done"):
                        final_data = payload["data"]
            
            assert final_data is not None
            assert "suggestion_id" in final_data
            assert "message_id" in final_data

    def test_get_suggestions(self, client, auth_headers, sample_trip):
        trip_id = sample_trip["id"]
        
        # Tạo suggestion trước
        with patch("app.api.routes.ai_chat.ai_service.chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = FAKE_CHAT_RESPONSE
            client.post(f"/api/trips/{trip_id}/chat", json={"message": "Suggest", "stream": False}, headers=auth_headers)

        res = client.get(f"/api/trips/{trip_id}/suggestions", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        # Should have suggestions from previous tests
        assert len(data) > 0
        assert data[0]["type"] == "itinerary"
        assert data[0]["status"] == "pending"
        
    def test_patch_suggestion_status_accept_itinerary(self, client, auth_headers, sample_trip):
        """Testing Accept Itinerary Suggestion which should populate day_plan"""
        trip_id = sample_trip["id"]
        
        # Tạo suggestion
        with patch("app.api.routes.ai_chat.ai_service.chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = FAKE_CHAT_RESPONSE
            client.post(f"/api/trips/{trip_id}/chat", json={"message": "Suggest itinerary", "stream": False}, headers=auth_headers)

        # 1. Fetch suggestions
        sug_res = client.get(f"/api/trips/{trip_id}/suggestions", headers=auth_headers)
        suggestions = sug_res.json()["data"]
        sug_to_accept = next(s for s in suggestions if s["status"] == "pending")
        suggestion_id = sug_to_accept["id"]

        # 2. Accept
        res = client.patch(
            f"/api/suggestions/{suggestion_id}/status",
            json={"status": "accepted"},
            headers=auth_headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["message"] == "Đã áp dụng gợi ý vào lịch trình"
        assert data["data"]["activities_created"] > 0
        
        # Verify the activity is added to the day plan
        days_res = client.get(f"/api/trips/{trip_id}/days", headers=auth_headers)
        days = days_res.json()["data"]
        # Check day 1 since our fake suggestion targets day 1
        day1 = next(d for d in days if d["day_number"] == 1)
        # Should have at least one activity now
        assert len(day1["activities"]) > 0

    def test_patch_suggestion_status_reject(self, client, auth_headers, sample_trip):
        trip_id = sample_trip["id"]

        # Need another pending suggestion, easiest way is to mock another chat call
        with patch("app.api.routes.ai_chat.ai_service.chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = FAKE_CHAT_RESPONSE
            client.post(f"/api/trips/{trip_id}/chat", json={"message": "Reject this", "stream": False}, headers=auth_headers)

        sug_res = client.get(f"/api/trips/{trip_id}/suggestions", headers=auth_headers)
        pending_sug = next(s for s in sug_res.json()["data"] if s["status"] == "pending")
        suggestion_id = pending_sug["id"]
        
        res = client.patch(
            f"/api/suggestions/{suggestion_id}/status",
            json={"status": "rejected"},
            headers=auth_headers
        )
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "rejected"

    def test_chat_unauthorized(self, client, sample_trip):
        trip_id = sample_trip["id"]
        res = client.post(f"/api/trips/{trip_id}/chat", json={"message": "hi"})
        assert res.status_code in [401, 403]
