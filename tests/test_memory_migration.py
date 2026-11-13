"""Legacy home-directory migration is deliberately disabled for fresh installations."""
from agent.memory.manager import MemoryManager


def test_legacy_migration_does_not_import_or_delete_user_data(tmp_path):
    old = tmp_path / "legacy"
    old.mkdir()
    note = old / "personal.md"
    note.write_text("legacy private material")
    memory = MemoryManager(tmp_path / "fresh")
    memory._run_hot_migration_if_needed(old)
    assert note.read_text() == "legacy private material"
    assert not (memory.base_dir / "personal.md").exists()
    assert memory._get_db().execute("SELECT COUNT(*) FROM knowledge_items").fetchone()[0] == 0
