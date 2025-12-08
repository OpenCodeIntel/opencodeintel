"""
WebSocket Authentication Tests
Tests for issue #6: Secure WebSocket endpoints
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestWebSocketAuthentication:
    """Integration tests for WebSocket authentication via query parameter token"""
    
    def test_websocket_rejects_missing_token(self, client):
        """WebSocket should reject connections without token (4001)"""
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/index/test-repo-id"):
                pass
    
    def test_websocket_rejects_invalid_token(self, client):
        """WebSocket should reject connections with invalid token (4001)"""
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/index/test-repo-id?token=invalid-token"):
                pass
    
    def test_websocket_rejects_nonexistent_repo(self, client):
        """WebSocket should reject if repo doesn't exist (4004)"""
        with patch('routes.repos._authenticate_websocket') as mock_auth:
            mock_auth.return_value = {"user_id": "test-user", "email": "test@example.com"}
            
            with pytest.raises(Exception):
                with client.websocket_connect("/ws/index/nonexistent-repo?token=valid"):
                    pass


class TestAuthenticateWebsocketFunction:
    """Unit tests for the _authenticate_websocket helper"""
    
    @pytest.mark.asyncio
    async def test_returns_none_without_token(self):
        """Should return None and close connection if no token provided"""
        from routes.repos import _authenticate_websocket
        
        mock_ws = MagicMock()
        mock_ws.query_params = {}
        mock_ws.close = AsyncMock()
        
        result = await _authenticate_websocket(mock_ws)
        
        assert result is None
        mock_ws.close.assert_called_once_with(code=4001, reason="Missing authentication token")
    
    @pytest.mark.asyncio
    async def test_returns_none_with_invalid_token(self):
        """Should return None and close connection if token is invalid"""
        from routes.repos import _authenticate_websocket
        
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": "invalid-token"}
        mock_ws.close = AsyncMock()
        
        with patch('services.auth.get_auth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.verify_jwt.side_effect = Exception("Invalid token")
            mock_get_service.return_value = mock_service
            
            result = await _authenticate_websocket(mock_ws)
        
        assert result is None
        mock_ws.close.assert_called_once_with(code=4001, reason="Invalid or expired token")
    
    @pytest.mark.asyncio
    async def test_returns_user_with_valid_token(self):
        """Should return user dict if token is valid"""
        from routes.repos import _authenticate_websocket
        
        mock_ws = MagicMock()
        mock_ws.query_params = {"token": "valid-jwt-token"}
        mock_ws.close = AsyncMock()
        
        expected_user = {"user_id": "user-123", "email": "test@example.com"}
        
        with patch('services.auth.get_auth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.verify_jwt.return_value = expected_user
            mock_get_service.return_value = mock_service
            
            result = await _authenticate_websocket(mock_ws)
        
        assert result == expected_user
        mock_ws.close.assert_not_called()
