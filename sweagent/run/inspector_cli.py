import argparse
import json
from pathlib import Path

import yaml
from rich.syntax import Syntax
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widgets import Footer, Header, Static


class TrajectoryViewer(Static):
    def __init__(self, trajectory: list[dict]):
        super().__init__()
        self.trajectory = trajectory
        self.current_index = -1
        self.show_full = False

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(id="content")

    def on_mount(self) -> None:
        self.update_content()

    def _show_full(self, item: dict) -> None:
        """Show full yaml of trajectory item"""
        content_str = yaml.dump(item, indent=2)
        syntax = Syntax(content_str, "yaml", theme="monokai", word_wrap=True)
        content = self.query_one("#content")
        content.update(syntax)  # type: ignore
        self.app.sub_title = f"Item {self.current_index + 1}/{len(self.trajectory)} - Full View"

    def _show_overview(self, item: dict) -> None:
        # Simplified view - show action and observation as plain text
        thought = item.get("thought", "")
        action = item.get("action", "")
        observation = item.get("observation", "")

        content_str = f"THOUGHT:\n{thought}\n\nACTION:\n{action}\n\nOBSERVATION:\n{observation}"
        content = self.query_one("#content")
        content.update(content_str)  # type: ignore

        self.app.sub_title = f"Item {self.current_index + 1}/{len(self.trajectory)} - Simple View"

    def _show_info(self):
        info = self.trajectory["info"]
        syntax = Syntax(yaml.dump(info, indent=2), "yaml", theme="monokai", word_wrap=True)
        content = self.query_one("#content")
        content.update(syntax)  # type: ignore
        next_help = "Press l to see step 1" if self.current_index < 0 else f"Press h to see step {len(self.trajectory)}"
        self.app.sub_title = f"Info ({next_help})"

    def update_content(self) -> None:
        print(self.current_index)
        if self.current_index < 0 or self.current_index >= len(self.trajectory):
            return self._show_info()

        item = self.trajectory["trajectory"][self.current_index]

        if self.show_full:
            return self._show_full(item)

        return self._show_overview(item)

    def toggle_view(self) -> None:
        self.show_full = not self.show_full
        self.update_content()

    def next_item(self) -> None:
        if self.current_index < len(self.trajectory):
            self.current_index += 1
            self.update_content()

    def previous_item(self) -> None:
        if self.current_index > -1:
            self.current_index -= 1
            self.update_content()


class TrajectoryInspectorApp(App):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 1;
    }

    #viewer {
        width: 100%;
        height: 100%;
    }

    ScrollView {
        width: 100%;
        height: 100%;
        border: solid green;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("right,l", "next_item", "Step+"),
        Binding("left,h", "previous_item", "Step-"),
        Binding("v", "toggle_view", "Toggle view"),
    ]

    def __init__(self, trajectory_path: str):
        super().__init__()
        self.trajectory_path = Path(trajectory_path)
        print("Initializing app with bindings:", self.BINDINGS)  # Debug print

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield TrajectoryViewer(self.load_trajectory())
        yield Footer()

    def load_trajectory(self) -> list[dict]:
        return json.loads(self.trajectory_path.read_text())

    def action_next_item(self) -> None:
        self.query_one(TrajectoryViewer).next_item()

    def action_previous_item(self) -> None:
        self.query_one(TrajectoryViewer).previous_item()

    def action_toggle_view(self) -> None:
        self.query_one(TrajectoryViewer).toggle_view()


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Inspect trajectory JSON files")
    parser.add_argument("trajectory_path", help="Path to the trajectory JSON file")
    parsed_args = parser.parse_args(args)

    app = TrajectoryInspectorApp(parsed_args.trajectory_path)
    app.run()


if __name__ == "__main__":
    main()
