import unittest
from unittest.mock import patch

import server


class ShowCommandTests(unittest.TestCase):
    def test_accepts_show_commands(self) -> None:
        self.assertEqual(server.validate_show_command(" show clock "), "show clock")
        self.assertEqual(server.validate_show_command("SHOW ROUTE"), "SHOW ROUTE")
        self.assertEqual(
            server.validate_show_command("show interfaces | include up"),
            "show interfaces | include up",
        )

    def test_rejects_non_show_commands(self) -> None:
        for command in ("configure terminal", "showcase", "reload", ""):
            with self.subTest(command=command):
                with self.assertRaises(ValueError):
                    server.validate_show_command(command)

    def test_rejects_multiple_commands(self) -> None:
        for command in ("show version\nreload", "show version; reload"):
            with self.subTest(command=command):
                with self.assertRaises(ValueError):
                    server.validate_show_command(command)

    @patch("server.run_cisco_command", return_value="router output")
    def test_generic_tool_runs_validated_command(self, run_command) -> None:
        output = server.cisco_show_command("PE1", " show clock ")

        self.assertEqual(output, "router output")
        run_command.assert_called_once_with("PE1", "show clock")


class PingTests(unittest.TestCase):
    def test_accepts_ping_with_additional_options(self) -> None:
        command = "ping 172.16.0.2 source 172.16.0.1"
        self.assertEqual(server.validate_ping_command(f" {command} "), command)
        self.assertEqual(
            server.validate_ping_command("PING 192.0.2.1 count 10"),
            "PING 192.0.2.1 count 10",
        )

    def test_rejects_non_ping_and_multiple_commands(self) -> None:
        for command in (
            "",
            "ping",
            "pingtest 192.0.2.1",
            "show version",
            "ping 192.0.2.1\nreload",
            "ping 192.0.2.1; reload",
        ):
            with self.subTest(command=command):
                with self.assertRaises(ValueError):
                    server.validate_ping_command(command)

    @patch("server.run_cisco_command", return_value="ping output")
    def test_ping_tool_builds_safe_command(self, run_command) -> None:
        command = "ping 172.16.0.2 source 172.16.0.1"
        output = server.cisco_ping("P0", command)

        self.assertEqual(output, "ping output")
        run_command.assert_called_once_with("P0", command)


if __name__ == "__main__":
    unittest.main()
