# Changelog

## v0.5.0 (2024-05-28)

[All new commits](https://github.com/princeton-nlp/SWE-agent/compare/v0.4.0...v0.5.0)

✨ The big news is our [brand new documentation](https://princeton-nlp.github.io/SWE-agent/) ✨

Secondly, @ollmer added a new flag `--cache_task_images` that will significantly speed up SWE-agent when running on the same environment/repository multiple times (no more waiting for cloning and installation!)

### Breaking changes

* Remove direct imports in __init__.py (you can no longer `from sweagent import Agent` by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/436
* We have reformatted our codebase. If you create a PR based on a previous commit, make sure you install our `pre-commit` hook to avoid merge-conflicts because of formatting. See [our docs](https://princeton-nlp.github.io/SWE-agent/dev/contribute/) for more information.

### Features

* Running the web UI is now supported when running swe-agent completely in docker
* Speed up evaluation by caching task environments as docker images by @ollmer in https://github.com/princeton-nlp/SWE-agent/pull/317

### Improved

* Add gpt-4o model by @raymyers in https://github.com/princeton-nlp/SWE-agent/pull/344
* Web: Allow to specify commit hash by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/358
* Add default environment_setup config by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/351
* Enh: Suppress openai logging; improve formatting of stats by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/416
* Remove signal dependency by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/428
* Do not use select if running on Windows by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/429
* Use custom Config class to support env and keys.cfg (this allows passing keys as environment variables) by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/430

### Fixes

* Web: Fix script_path input by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/334
* Fix: Don't print patch msg for exit_cost patch by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/343
* Fix: Do not request job control in bash by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/345
* Fix: --base_commit not used for gh urls by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/346
* Fix: Separate data path/traj dir cause exception by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/348
* Add docker-py lower bound by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/406
* Fix: IndexError when replaying incomplete trajectories by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/410


## 0.4.0 (2024-05-09)

[All new commits](https://github.com/princeton-nlp/SWE-agent/compare/v0.3.0...v0.4.0)

### Added

We’re excited to launch the SWE-agent web UI! Specify a bug, press start and watch SWE-agent do the magic.

## 0.3.0 (2024-05-02)

### Added

* Run SWE-agent in the cloud using GitHub Codespaces
* Add GPT4-turbo model by @zgrannan in https://github.com/princeton-nlp/SWE-agent/pull/252
* feat: Amazon Bedrock support (Claude models) by @JGalego in https://github.com/princeton-nlp/SWE-agent/pull/207

### Fixed

* Better error handling for --open_pr by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/239
* Fixed a potential error by @DanjieTang in https://github.com/princeton-nlp/SWE-agent/pull/242
* fix: TARGETARCH not set on some OS/docker setups by @mspronesti in https://github.com/princeton-nlp/SWE-agent/pull/249
* Pass Python version to get_environment_yml by @waterson in https://github.com/princeton-nlp/SWE-agent/pull/271
* Fix Together model validation error by @mikanfactory in https://github.com/princeton-nlp/SWE-agent/pull/236
* Doc: Avoid invalid github token by @klieret in https://github.com/princeton-nlp/SWE-agent/pull/292

## 0.2.0 (2024-04-15)

[All new commits](https://github.com/princeton-nlp/SWE-agent/compare/v0.1.2...v0.2.0)

### Added

* Allow to run on local repos (new flag: `--repo_path`) in https://github.com/princeton-nlp/SWE-agent/pull/193
* Patch files are now saved separately to a patch directory in https://github.com/princeton-nlp/SWE-agent/pull/126
* Allow to supply custom installation commands when running on gh issues or locally (`--environment_setup`) in https://github.com/princeton-nlp/SWE-agent/pull/153
* Allow to specify openapi base url in `keys.cfg` in https://github.com/princeton-nlp/SWE-agent/pull/118

### Improved

* Improve error handling of docker issues in https://github.com/princeton-nlp/SWE-agent/pull/165
* Make github token fully optional in https://github.com/princeton-nlp/SWE-agent/pull/189

### Fixed

* Fix opening PR from fork in https://github.com/princeton-nlp/SWE-agent/pull/229
* Fix: Choosing TogetherAI models in https://github.com/princeton-nlp/SWE-agent/pull/130
