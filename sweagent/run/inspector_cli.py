import argparse
import json

import yaml
from rich.syntax import Syntax
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.scroll_view import ScrollView
from textual.widgets import Footer, Header, Static


class TrajectoryViewer(Static):
    def __init__(self, trajectory: list[dict]):
        super().__init__()
        self.trajectory = trajectory
        self.current_index = 0
        self.show_full = False  # Toggle for view mode

    def compose(self) -> ComposeResult:
        with ScrollView():
            yield Static(id="content")

    def on_mount(self) -> None:
        self.update_content()

    def update_content(self) -> None:
        item = self.trajectory[self.current_index]

        if self.show_full:
            # Full view - show all data
            content_str = yaml.dump(item, indent=2)
            syntax = Syntax(content_str, "yaml", theme="monokai", word_wrap=True)
            content = self.query_one("#content")
            content.update(syntax)
        else:
            # Simplified view - show action and observation as plain text
            thought = item.get("thought", "")
            action = item.get("action", "")
            observation = item.get("observation", "")

            content_str = f"THOUGHT:\n{thought}\n\nACTION:\n{action}\n\nOBSERVATION:\n{observation}"
            content = self.query_one("#content")
            content.update(content_str)

        view_mode = "Full" if self.show_full else "Simple"
        self.app.sub_title = f"Item {self.current_index + 1}/{len(self.trajectory)} - {view_mode} View"

    def toggle_view(self) -> None:
        self.show_full = not self.show_full
        self.update_content()

    def next_item(self) -> None:
        if self.current_index < len(self.trajectory) - 1:
            self.current_index += 1
            self.update_content()

    def previous_item(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self.update_content()

    def scroll_down(self) -> None:
        scroll_view = self.query_one(ScrollView)
        scroll_view.scroll_down(animate=False)

    def scroll_up(self) -> None:
        scroll_view = self.query_one(ScrollView)
        scroll_view.scroll_up(animate=False)


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
        Binding("right,l", "next_item", "Next item"),
        Binding("left,h", "previous_item", "Previous item"),
        Binding("v", "toggle_view", "Toggle view"),
        Binding("j,down", "scroll_d", "Scroll down"),
        Binding("k,up", "scroll_u", "Scroll up"),
    ]

    def __init__(self, trajectory_path: str):
        super().__init__()
        self.trajectory_path = trajectory_path
        print("Initializing app with bindings:", self.BINDINGS)  # Debug print

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield TrajectoryViewer(self.load_trajectory())
        yield Footer()

    def load_trajectory(self) -> list[dict]:
        with open(self.trajectory_path) as f:
            data = json.load(f)
        return data.get("trajectory", [])

    def action_next_item(self) -> None:
        self.query_one(TrajectoryViewer).next_item()

    def action_previous_item(self) -> None:
        self.query_one(TrajectoryViewer).previous_item()

    def action_toggle_view(self) -> None:
        self.query_one(TrajectoryViewer).toggle_view()

    def action_scroll_d(self) -> None:
        viewer = self.query_one(TrajectoryViewer)
        viewer.scroll_down()

    def action_scroll_u(self) -> None:
        viewer = self.query_one(TrajectoryViewer)
        viewer.scroll_up()


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Inspect trajectory JSON files")
    parser.add_argument("trajectory_path", help="Path to the trajectory JSON file")
    parsed_args = parser.parse_args(args)

    app = TrajectoryInspectorApp(parsed_args.trajectory_path)
    app.run()


if __name__ == "__main__":
    main()
