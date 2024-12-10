import argparse
import collections
import copy
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from rich.syntax import Syntax
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from sweagent.utils.serialization import _yaml_serialization_with_linebreaks


def _move_items_top(d: dict, keys: list[str]) -> dict:
    new_d = {}
    for key in keys:
        if key in d:
            new_d[key] = d[key]
    for key in d.keys():
        if key not in keys:
            new_d[key] = d[key]
    return new_d


class TrajectoryViewer(Static):
    BINDINGS = [
        Binding("right,l", "next_item", "Step++"),
        Binding("left,h", "previous_item", "Step--"),
        Binding("0", "first_item", "Step=0"),
        Binding("$", "last_item", "Step=-1"),
        Binding("v", "toggle_view", "Toggle view"),
        Binding("j,down", "scroll_down", "Scroll down"),
        Binding("k,up", "scroll_up", "Scroll up"),
    ]

    def __init__(self, path: Path, title: str, overview_stats: dict):
        super().__init__()
        self.current_index = -1
        self.trajectory = json.loads(path.read_text())
        self.show_full = False
        self.title = title
        self.overview_stats = overview_stats

    def load_trajectory(self, path: Path, title: str, overview_stats: dict):
        print("Loading", path)
        self.trajectory = json.loads(path.read_text())
        self.title = title
        self.update_content()

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(id="content")

    def on_mount(self) -> None:
        self.update_content()

    @property
    def n_steps(self) -> int:
        return len(self.trajectory["trajectory"])

    def _show_full(self, item: dict) -> None:
        """Show full yaml of trajectory item"""
        content_str = _yaml_serialization_with_linebreaks(
            _move_items_top(item, ["thought", "action", "observation", "response", "execution_time"])
        )
        syntax = Syntax(content_str, "yaml", theme="monokai", word_wrap=True)
        content = self.query_one("#content")
        content.update(syntax)  # type: ignore
        self.app.sub_title = f"{self.title} - Step {self.current_index + 1}/{self.n_steps} - Full View"

    def _show_overview(self, item: dict) -> None:
        # Simplified view - show action and observation as plain text
        thought = item.get("thought", "")
        action = item.get("action", "")
        observation = item.get("observation", "")

        content_str = f"THOUGHT:\n{thought}\n\nACTION:\n{action}\n\nOBSERVATION:\n{observation}"
        content = self.query_one("#content")
        content.update(content_str)  # type: ignore

        self.app.sub_title = f"{self.title} - Step {self.current_index + 1}/{self.n_steps} - Simple View"

    def _show_info(self):
        info = copy.deepcopy(self.trajectory["info"])
        info["result"] = self.overview_stats["result"]
        info = _move_items_top(info, ["result", "exit_status", "model_stats", "submission"])
        syntax = Syntax(_yaml_serialization_with_linebreaks(info), "yaml", theme="monokai", word_wrap=True)
        content = self.query_one("#content")
        content.update(syntax)  # type: ignore
        next_help = "Press l to see step 1" if self.current_index < 0 else f"Press h to see step {self.n_steps}"
        self.app.sub_title = f"{self.title} - Info ({next_help})"

    def update_content(self) -> None:
        print(self.current_index)
        if self.current_index < 0 or self.current_index >= self.n_steps:
            return self._show_info()

        item = self.trajectory["trajectory"][self.current_index]

        if self.show_full:
            return self._show_full(item)

        return self._show_overview(item)

    def action_next_item(self) -> None:
        if self.current_index < self.n_steps:
            self.current_index += 1
            self.update_content()

    def action_previous_item(self) -> None:
        if self.current_index > -1:
            self.current_index -= 1
            self.update_content()

    def action_toggle_view(self) -> None:
        self.show_full = not self.show_full
        self.update_content()

    def action_first_item(self) -> None:
        self.current_index = 0
        self.update_content()

    def action_last_item(self) -> None:
        self.current_index = self.n_steps - 1
        self.update_content()

    def action_scroll_down(self) -> None:
        vs = self.query_one(VerticalScroll)
        vs.scroll_to(y=vs.scroll_target_y + 15)

    def action_scroll_up(self) -> None:
        vs = self.query_one(VerticalScroll)
        vs.scroll_to(y=vs.scroll_target_y - 15)


class TrajectorySelectorScreen(ModalScreen[int]):
    def __init__(self, paths: list[Path], current_index: int, overview_stats: dict):
        super().__init__()
        self.paths = paths
        self.current_index = current_index
        self.overview_stats = overview_stats

    def _get_list_item_texts(self, paths: list[Path]) -> list[str]:
        """Remove the common prefix from a list of paths."""
        prefix = os.path.commonpath([str(p) for p in paths])
        labels = []
        for p in paths:
            ostat = self.overview_stats[p.stem]
            ostat_str = f"{ostat['exit_status']} {ostat['result']} ${ostat['cost']:.2f} {ostat['n_steps']} steps"
            shortened_path = str(p)[len(prefix) :].lstrip("/\\")
            if Path(shortened_path).stem == Path(shortened_path).parent.name:
                # We have the instance ID twice (in the folder and the traj)
                shortened_path = Path(shortened_path).stem
            labels.append(f"{shortened_path} - {ostat_str}")

        return labels

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Select Trajectory", id="title")
            yield ListView(
                *[ListItem(Static(p)) for p in self._get_list_item_texts(self.paths)],
                id="trajectory-list",
                initial_index=self.current_index,
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        print(f"Selected index: {event.list_view.index}")
        self.dismiss(event.list_view.index)

    CSS = """
    #dialog {
        background: $surface;
        padding: 1;
        border: thick $primary;
        width: 100%;
        height: 100%;
    }

    #title {
        text-align: center;
        padding: 1;
    }

    ListView {
        height: 100%;
        border: solid $primary;
    }

    ListItem {
        padding: 0 1;
    }

    ListItem:hover {
        background: $accent;
    }
    """


class TrajectoryInspectorApp(App):
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("L", "next_traj", "Traj++"),
        Binding("H", "previous_traj", "Traj--"),
        Binding("t", "show_traj_selector", "Select Traj"),
    ]

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

    def __init__(self, input_path: str | Path):
        super().__init__()
        self.input_path = Path(input_path)
        if not self.input_path.exists():
            msg = f"{self.input_path} doesn't exist"
            raise FileNotFoundError(msg)
        self.available_traj_paths = self._get_available_trajs()
        if not self.available_traj_paths:
            msg = "No trajectory *.traj files available"
            raise ValueError(msg)
        self.trajectory_index = 0
        self.overview_stats = collections.defaultdict(dict)
        self._build_overview_stats()

    def _build_overview_stats(self):
        results_path = self.input_path / "results.json"
        results = None
        if results_path.exists():
            results = json.loads(results_path.read_text())
        for traj in self.available_traj_paths:
            instance_id = traj.stem
            if results is None:
                result = "❓"
            elif instance_id in results["resolved_ids"]:
                result = "✅"
            else:
                result = "❌"
            self.overview_stats[instance_id]["result"] = result

        def _get_info(traj: Path) -> tuple[str, dict]:
            traj_info = json.loads(traj.read_text()).get("info", {})
            return traj.stem, traj_info

        with ThreadPoolExecutor() as executor:
            # Map returns results in the same order as inputs
            all_infos = executor.map(_get_info, self.available_traj_paths)

        for instance_id, info in all_infos:
            self.overview_stats[instance_id]["info"] = info
            self.overview_stats[instance_id]["exit_status"] = info.get("exit_status", "?")
            self.overview_stats[instance_id]["n_steps"] = info.get("model_stats", {}).get("api_calls", 0)
            self.overview_stats[instance_id]["cost"] = info.get("model_stats", {}).get("instance_cost", 0)

    def _get_viewer_title(self, index: int) -> str:
        instance_id = self.available_traj_paths[index].stem
        if len(instance_id) > 20:
            instance_id = "..." + instance_id[-17:]
        return f"Traj {index + 1}/{len(self.available_traj_paths)} - {instance_id}"

    def _load_traj(self):
        instance_id = self.available_traj_paths[self.trajectory_index].stem
        traj_viewer = self.query_one(TrajectoryViewer)
        traj_viewer.load_trajectory(
            self.available_traj_paths[self.trajectory_index],
            self._get_viewer_title(self.trajectory_index),
            self.overview_stats[instance_id],
        )

    def _get_available_trajs(self) -> list[Path]:
        if self.input_path.is_file():
            return [self.input_path]
        elif self.input_path.is_dir():
            return list(self.input_path.rglob("*.traj"))
        raise ValueError

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield TrajectoryViewer(
                self.available_traj_paths[self.trajectory_index],
                self._get_viewer_title(self.trajectory_index),
                self.overview_stats[self.available_traj_paths[self.trajectory_index].stem],
            )
        yield Footer()

    def action_next_traj(self):
        self.trajectory_index = (self.trajectory_index + 1) % len(self.available_traj_paths)
        self._load_traj()

    def action_previous_traj(self):
        self.trajectory_index = (self.trajectory_index - 1) % len(self.available_traj_paths)
        self._load_traj()

    async def action_show_traj_selector(self) -> None:
        selector = TrajectorySelectorScreen(self.available_traj_paths, self.trajectory_index, self.overview_stats)

        def handler(index: int | None):
            self.trajectory_index = index
            self._load_traj()

        await self.push_screen(selector, handler)  # This returns when the modal is dismissed


def main(args: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Inspect trajectory JSON files")
    parser.add_argument(
        "trajectory_path",
        help="Path to the trajectory JSON file or directory containing trajectories",
        default=os.getcwd(),
        nargs="?",
    )
    parsed_args = parser.parse_args(args)

    app = TrajectoryInspectorApp(parsed_args.trajectory_path)
    app.run()


if __name__ == "__main__":
    main()
