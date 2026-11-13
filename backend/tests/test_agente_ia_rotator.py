import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import MagicMock, patch
from uuid import uuid4
from sqlalchemy import select

from app.core.config import Settings
from app.core.database import SessionLocal
from app.models.entities import IAChat, Rol, Usuario
from app.services.agente_ia_service import AgenteIAService, GeminiKeyRotator


def test_settings_gemini_api_keys_parsing():
    s = Settings(
        gemini_api_keys="AIzaSyKey1, AIzaSyKey2; AIzaSyKey3 AIzaSyKey1",
        gemini_api_key="AIzaSyKey4, AIzaSyKey2",
    )
    keys = s.get_gemini_api_keys()
    assert keys == ["AIzaSyKey1", "AIzaSyKey2", "AIzaSyKey3", "AIzaSyKey4"]


def test_gemini_key_rotator_fallback_and_summary():
    with patch.object(GeminiKeyRotator, "get_keys", return_value=["KEY_A", "KEY_B", "KEY_C"]):
        # Reset internal rotator state
        GeminiKeyRotator._current_index = 0
        GeminiKeyRotator._failed_keys = {}

        # Initially all healthy
        pool = GeminiKeyRotator.get_ordered_pool()
        assert pool == ["KEY_A", "KEY_B", "KEY_C"]

        # Mark KEY_A as failed (e.g. HTTP 401)
        GeminiKeyRotator.mark_key_failed("KEY_A", "HTTP 401: Bound service account disabled")
        assert "KEY_A" in GeminiKeyRotator._failed_keys

        # Ordered pool should prioritize healthy keys (KEY_B, KEY_C)
        new_pool = GeminiKeyRotator.get_ordered_pool()
        assert new_pool[0] in ("KEY_B", "KEY_C")
        assert new_pool[-1] == "KEY_A"

        # Summary check
        summary = GeminiKeyRotator.get_status_summary()
        assert summary["total_keys"] == 3
        assert summary["keys_activas"] == 2
        assert summary["keys_fallidas"] == 1

        # Recover KEY_A on success
        GeminiKeyRotator.mark_key_success("KEY_A")
        assert "KEY_A" not in GeminiKeyRotator._failed_keys


def test_agente_ia_procesar_mensaje_failover():
    user_id = uuid4()
    chat_id = uuid4()

    test_user = MagicMock(spec=Usuario)
    test_user.id = user_id
    test_user.nombre = "User Test IA"

    chat = MagicMock(spec=IAChat)
    chat.id = chat_id
    chat.usuario_id = user_id
    chat.titulo = "Test Fallback"
    chat.mensajes = []

    db = MagicMock()
    db.scalar.return_value = chat

    agente = AgenteIAService(db, test_user)

    # Mock pool with 2 keys: Key 1 fails with 401, Key 2 succeeds with 200
    key1 = "KEY_DEAD_401"
    key2 = "KEY_HEALTHY_200"

    with patch.object(GeminiKeyRotator, "get_keys", return_value=[key1, key2]):
        GeminiKeyRotator._current_index = 0
        GeminiKeyRotator._failed_keys = {}

        def mock_post(url, json=None, **kwargs):
            mock_resp = MagicMock()
            if key1 in url:
                mock_resp.status_code = 401
                mock_resp.text = '{"error": {"code": 401, "message": "The bound service account is deleted or disabled"}}'
            elif key2 in url:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": "| Indicador | Valor |\n| :--- | :--- |\n| Ventas | $10.000 |"}]
                            }
                        }
                    ]
                }
            else:
                mock_resp.status_code = 500
                mock_resp.text = "Internal error"
            return mock_resp

        with patch("httpx.Client.post", side_effect=mock_post):
            resultado = agente.procesar_mensaje(chat_id, "¿Cuáles son las ventas de hoy?")
            assert resultado is not None
            assert "Ventas" in resultado["contenido"]
            # KEY_DEAD_401 should have been marked as failed in the rotator
            assert key1 in GeminiKeyRotator._failed_keys


if __name__ == "__main__":
    test_settings_gemini_api_keys_parsing()
    print("✓ test_settings_gemini_api_keys_parsing PASSED")
    test_gemini_key_rotator_fallback_and_summary()
    print("✓ test_gemini_key_rotator_fallback_and_summary PASSED")
    test_agente_ia_procesar_mensaje_failover()
    print("✓ test_agente_ia_procesar_mensaje_failover PASSED")
    print(">>> ALL GEMINI ROTATOR TESTS PASSED SUCCESSFULLY! <<<")
