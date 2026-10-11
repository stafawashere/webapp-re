import pytest

from citymapper_client import registry

SCHEMAS = registry.load_schemas()
WRITE_COMMANDS = sorted(name for name, record in SCHEMAS.items() if record["kind"] == "write")
LOCAL_WRITE_COMMANDS = sorted(name for name in WRITE_COMMANDS if SCHEMAS[name]["live_policy"] == "local")
REMOTE_WRITE_COMMANDS = sorted(name for name in WRITE_COMMANDS if SCHEMAS[name]["live_policy"] != "local")


def test_schemas_list_57_commands():
   assert len(SCHEMAS) == 57


def test_every_schema_command_except_help_has_a_function():
   missing = sorted(name for name in SCHEMAS if name != "help" and name not in registry.FUNCTIONS)

   assert missing == []
   assert "help" not in registry.FUNCTIONS


def test_every_function_name_maps_to_a_schema():
   orphans = sorted(name for name in registry.FUNCTIONS if name not in SCHEMAS)

   assert orphans == []


def test_built_registry_attaches_each_function():
   commands = registry.build_registry()
   without_function = sorted(name for name, command in commands.items() if command.function is None)

   assert without_function == ["help"]


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_kind_is_read_or_write(name):
   assert SCHEMAS[name]["kind"] in ("read", "write")


@pytest.mark.parametrize("name", REMOTE_WRITE_COMMANDS)
def test_write_command_inputs_have_yes_and_dry_run(name):
   properties = SCHEMAS[name]["input_schema"].get("properties") or {}

   assert properties.get("yes", {}).get("type") == "boolean"
   assert properties.get("dry_run", {}).get("type") == "boolean"


def test_the_only_write_without_yes_and_dry_run_is_the_local_adopt_session():
   assert LOCAL_WRITE_COMMANDS == ["adopt-session"]
   assert "sends nothing" in SCHEMAS["adopt-session"]["confirmation"]
