"""Public CLI help behavior tests."""

from typer.testing import CliRunner

from ttodo.cli import app


def test_root_help_explains_commands_in_plain_english() -> None:
    """Show an understandable overview without contacting the API."""
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Manage tasks" in result.stdout
    for command in ("create", "list", "get", "update", "delete", "deleted", "restore"):
        assert command in result.stdout
    assert "http://127.0.0.1:8000" in result.stdout


def test_each_command_help_has_a_plain_english_example() -> None:
    """Explain every command with a copyable example, without a server."""
    for command in ("create", "list", "get", "update", "delete", "deleted", "restore"):
        result = CliRunner().invoke(app, [command, "--help"])
        assert result.exit_code == 0, (command, result.output)
        assert "Example:" in result.stdout
        assert "JSON example:" in result.stdout
