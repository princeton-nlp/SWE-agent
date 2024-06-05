# Changelog

## 0.6.0 (2024-06-05)

[All new commits](https://github.com/princeton-nlp/SWE-agent/compare/v0.5.0...v0.6.0)

**We sped up SWE-agent by 2x** (timed with GPT4o). This is mostly due to faster communication with the running processes inside of the Docker container and other container setup & installation related improvements. Here are a few relevant PRs:

* Switch to fast communicate and sparse clone by default by [@klieret](https://github.com/klieret) in [#530](https://github.com/princeton-nlp/SWE-agent/pull/530)
* Change: Only wait 1s for docker to start by [@klieret](https://github.com/klieret) in [#541](https://github.com/princeton-nlp/SWE-agent/pull/541)
* Feat: experimental sparse cloning by [@klieret](https://github.com/klieret) in [#498](https://github.com/princeton-nlp/SWE-agent/pull/498)
* Enh: Start from clone of python conda environment for speedup by [@klieret](https://github.com/klieret) in [#548](https://github.com/princeton-nlp/SWE-agent/pull/548)
* Enh: Use uv for editable install by default by [@klieret](https://github.com/klieret) in [#547](https://github.com/princeton-nlp/SWE-agent/pull/547)

### Improved

* Improve scrolling behavior in web UI by [@anishfish2](https://github.com/anishfish2) in [#420](https://github.com/princeton-nlp/SWE-agent/pull/420)
* Web UI: Render Markdown in agent feed messages. by [@kwight](https://github.com/kwight) in [#486](https://github.com/princeton-nlp/SWE-agent/pull/486)
* Enh: Remove redundant 'saved traj to X' messages by [@klieret](https://github.com/klieret) in [#528](https://github.com/princeton-nlp/SWE-agent/pull/528)
* Allow to disable config dump to log by [@klieret](https://github.com/klieret) in [#537](https://github.com/princeton-nlp/SWE-agent/pull/537)
* Resolve relative paths to demonstrations and commands by [@klieret](https://github.com/klieret) in [#444](https://github.com/princeton-nlp/SWE-agent/pull/444)

### Fixed

* Web UI: Remove -n option to wait by [@klieret](https://github.com/klieret) in [#487](https://github.com/princeton-nlp/SWE-agent/pull/487)
* Web UI: Kill the Flask server on exit. by [@kwight](https://github.com/kwight) in [#479](https://github.com/princeton-nlp/SWE-agent/pull/479)
* Web UI: Avoid proxy errors on MacOS by [@klieret](https://github.com/klieret) in [#506](https://github.com/princeton-nlp/SWE-agent/pull/506)
* Ensure container_name is reset for non-persistent containers by [@klieret](https://github.com/klieret) in [#463](https://github.com/princeton-nlp/SWE-agent/pull/463)
* Fix: Do not allow persistent container with cache task imgs by [@klieret](https://github.com/klieret) in [#551](https://github.com/princeton-nlp/SWE-agent/pull/551)


## 0.5.0 (2024-05-28)

[All new commits](https://github.com/princeton-nlp/SWE-agent/compare/v0.4.0...v0.5.0)

✨ The big news is our [brand new documentation](https://princeton-nlp.github.io/SWE-agent/) ✨

Secondly, @ollmer added a new flag `--cache_task_images` that will significantly speed up SWE-agent when running on the same environment/repository multiple times (no more waiting for cloning and installation!)

### Breaking changes

* We have reformatted our codebase. If you create a PR based on a previous commit, make sure you install our `pre-commit` hook to avoid merge-conflicts because of formatting. See [our docs](https://princeton-nlp.github.io/SWE-agent/dev/formatting_conflicts/) for more information.
* Remove direct imports in `__init__.py` (you can no longer `from sweagent import Agent` by [@klieret](https://github.com/klieret) in [#436](https://github.com/princeton-nlp/SWE-agent/pull/436)

### Added

* Running the web UI is now supported when running swe-agent completely in docker
* Speed up evaluation by caching task environments as docker images by [@ollmer](https://github.com/ollmer) in [#317](https://github.com/princeton-nlp/SWE-agent/pull/317)

### Improved

* Add gpt-4o model by [@raymyers](https://github.com/raymyers) in [#344](https://github.com/princeton-nlp/SWE-agent/pull/344)
* Web: Allow to specify commit hash by [@klieret](https://github.com/klieret) in [#358](https://github.com/princeton-nlp/SWE-agent/pull/358)
* Add default environment_setup config by [@klieret](https://github.com/klieret) in [#351](https://github.com/princeton-nlp/SWE-agent/pull/351)
* Enh: Suppress openai logging; improve formatting of stats by [@klieret](https://github.com/klieret) in [#416](https://github.com/princeton-nlp/SWE-agent/pull/416)
* Remove signal dependency by [@klieret](https://github.com/klieret) in [#428](https://github.com/princeton-nlp/SWE-agent/pull/428)
* Do not use select if running on Windows by [@klieret](https://github.com/klieret) in [#429](https://github.com/princeton-nlp/SWE-agent/pull/429)
* Use custom Config class to support env and keys.cfg (this allows passing keys as environment variables) by [@klieret](https://github.com/klieret) in [#430](https://github.com/princeton-nlp/SWE-agent/pull/430)

### Fixed

* Web: Fix script_path input by [@klieret](https://github.com/klieret) in [#334](https://github.com/princeton-nlp/SWE-agent/pull/334)
* Fix: Don't print patch msg for exit_cost patch by [@klieret](https://github.com/klieret) in [#343](https://github.com/princeton-nlp/SWE-agent/pull/343)
* Fix: Do not request job control in bash by [@klieret](https://github.com/klieret) in [#345](https://github.com/princeton-nlp/SWE-agent/pull/345)
* Fix: --base_commit not used for gh urls by [@klieret](https://github.com/klieret) in [#346](https://github.com/princeton-nlp/SWE-agent/pull/346)
* Fix: Separate data path/traj dir cause exception by [@klieret](https://github.com/klieret) in [#348](https://github.com/princeton-nlp/SWE-agent/pull/348)
* Add docker-py lower bound by [@klieret](https://github.com/klieret) in [#406](https://github.com/princeton-nlp/SWE-agent/pull/406)
* Fix: IndexError when replaying incomplete trajectories by [@klieret](https://github.com/klieret) in [#410](https://github.com/princeton-nlp/SWE-agent/pull/410)


## 0.4.0 (2024-05-09)

[All new commits](https://github.com/princeton-nlp/SWE-agent/compare/v0.3.0...v0.4.0)

### Added

We’re excited to launch the SWE-agent web UI! Specify a bug, press start and watch SWE-agent do the magic.

## 0.3.0 (2024-05-02)

### Added

* Run SWE-agent in the cloud using GitHub Codespaces
* Add GPT4-turbo model by [@zgrannan](https://github.com/zgrannan) in [#252](https://github.com/princeton-nlp/SWE-agent/pull/252)
* feat: Amazon Bedrock support (Claude models) by [@JGalego](https://github.com/JGalego) in [#207](https://github.com/princeton-nlp/SWE-agent/pull/207)

### Fixed

* Better error handling for --open_pr by [@klieret](https://github.com/klieret) in [#239](https://github.com/princeton-nlp/SWE-agent/pull/239)
* Fixed a potential error by [@DanjieTang](https://github.com/DanjieTang) in [#242](https://github.com/princeton-nlp/SWE-agent/pull/242)
* fix: TARGETARCH not set on some OS/docker setups by [@mspronesti](https://github.com/mspronesti) in [#249](https://github.com/princeton-nlp/SWE-agent/pull/249)
* Pass Python version to get_environment_yml by [@waterson](https://github.com/waterson) in [#271](https://github.com/princeton-nlp/SWE-agent/pull/271)
* Fix Together model validation error by [@mikanfactory](https://github.com/mikanfactory) in [#236](https://github.com/princeton-nlp/SWE-agent/pull/236)
* Doc: Avoid invalid github token by [@klieret](https://github.com/klieret) in [#292](https://github.com/princeton-nlp/SWE-agent/pull/292)

## 0.2.0 (2024-04-15)

[All new commits](https://github.com/princeton-nlp/SWE-agent/compare/v0.1.2...v0.2.0)

### Added

* Allow to run on local repos (new flag: `--repo_path`) in [#193](https://github.com/princeton-nlp/SWE-agent/pull/193)
* Patch files are now saved separately to a patch directory in [#126](https://github.com/princeton-nlp/SWE-agent/pull/126)
* Allow to supply custom installation commands when running on gh issues or locally (`--environment_setup`) in [#153](https://github.com/princeton-nlp/SWE-agent/pull/153)
* Allow to specify openapi base url in `keys.cfg` in [#118](https://github.com/princeton-nlp/SWE-agent/pull/118)

### Improved

* Improve error handling of docker issues in [#165](https://github.com/princeton-nlp/SWE-agent/pull/165)
* Make github token fully optional in [#189](https://github.com/princeton-nlp/SWE-agent/pull/189)

### Fixed

* Fix opening PR from fork in [#229](https://github.com/princeton-nlp/SWE-agent/pull/229)
* Fix: Choosing TogetherAI models in [#130](https://github.com/princeton-nlp/SWE-agent/pull/130)
