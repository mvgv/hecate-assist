import pytest

from medassist.config import get_settings


@pytest.fixture
def tmp_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDASSIST_LLM_PROVIDER", "fake")
    monkeypatch.setenv("MEDASSIST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MEDASSIST_DB_PATH", str(tmp_path / "data" / "medassist.db"))
    monkeypatch.setenv("MEDASSIST_CHECKPOINT_PATH", str(tmp_path / "data" / "checkpoints.db"))
    monkeypatch.setenv("MEDASSIST_CHROMA_DIR", str(tmp_path / "data" / "chroma"))
    monkeypatch.setenv("MEDASSIST_LOG_DIR", str(tmp_path / "logs"))
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.fixture
def db_seeded(tmp_settings):
    from medassist.db.seed import seed_db

    seed_db()
    return tmp_settings


@pytest.fixture
def chroma_ingested(tmp_settings):
    from medassist.rag.ingest import ingest

    ingest()
    return tmp_settings


@pytest.fixture
def grafo(tmp_settings, db_seeded, chroma_ingested):
    from langgraph.checkpoint.memory import MemorySaver

    from medassist.assistant.graph import construir_grafo

    return construir_grafo(checkpointer=MemorySaver())
