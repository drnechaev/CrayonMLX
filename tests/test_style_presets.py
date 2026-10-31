from crayonmlx.presets.catalog import BACKGROUNDS, default_preservation, initial_templates
from crayonmlx.presets.defaults import initial_presets
from crayonmlx.presets.legacy_defaults import initial_presets as legacy_presets
from crayonmlx.presets.library import PromptRepository, legacy_templates
from crayonmlx.presets.repository import JsonRepository, PresetRepository
from crayonmlx.schemas import Preset, PromptBlocks, PromptTemplate


def test_independent_categories_and_compatible_combination():
    templates = initial_templates()
    assert {item.category for item in templates} == {
        "style",
        "subject",
        "background",
        "composition",
        "lighting",
        "constraints",
    }
    assert len([item for item in templates if item.category == "style"]) == 11
    assert len([item for item in templates if item.category == "subject"]) == 11
    assert len([item for item in templates if item.category == "background"]) == len(BACKGROUNDS)
    tokyo = next(p for p in initial_presets() if "Токио" in p.name)
    assert not tokyo.blocks.preservation.background
    assert not tokyo.blocks.preservation.layout
    prompt = tokyo.blocks.compose()
    assert "Tokyo" in prompt and "anime" in prompt and "neon" in prompt
    assert "Preserve the original background and location." not in prompt
    assert "Preserve the original clothing" in prompt
    assert "Рисунок оживает" not in {p.name for p in initial_presets()}


def test_preservation_is_explicit_and_legacy_prompts_are_unchanged():
    legacy = PromptBlocks.model_validate({"style": "style", "subject": "subject", "constraints": "rules"})
    assert legacy.compose() == "style\n\nsubject\n\nrules"
    blocks = PromptBlocks(lighting="Soft daylight", preservation=default_preservation())
    restored = PromptBlocks.model_validate_json(blocks.model_dump_json())
    assert restored.compose() == blocks.compose()
    assert "Soft daylight" in restored.compose()
    assert "lettering" in restored.compose()
    restored.preservation.lettering = False
    assert "lettering" not in restored.compose()


def test_upgrade_replaces_factory_entries_and_preserves_user_edits_and_deletions(tmp_path):
    for directory, repository, schema, old_defaults in [
        ("presets", PresetRepository, Preset, legacy_presets),
        ("prompt-templates", PromptRepository, PromptTemplate, legacy_templates),
    ]:
        old = JsonRepository(tmp_path, directory, schema, old_defaults)
        entries = old.list()
        edited = next(item for item in entries if "Хантрик" in item["name"])
        identifier = edited.pop("id")
        if directory == "presets":
            edited["blocks"]["style"] = "My custom style"
        else:
            edited["text"] = "My custom style"
        old.save(identifier, schema.model_validate(edited))
        library = repository(tmp_path)
        assert next(item for item in library.list() if item["id"] == identifier) == {
            "id": identifier,
            **edited,
        }
        assert not any("Рисунок оживает" in item["name"] for item in library.list())
        other = next(item for item in library.list() if item["id"] != identifier)
        library.delete(other["id"])
        before = library.list()
        assert repository(tmp_path).list() == before


def test_fresh_libraries_do_not_duplicate_entries(tmp_path):
    for repository in [PresetRepository, PromptRepository]:
        entries = repository(tmp_path).list()
        names = [item["name"] for item in entries]
        assert len(names) == len(set(names))
        assert repository(tmp_path).list() == entries
