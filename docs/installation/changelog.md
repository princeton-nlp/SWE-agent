# Changelog

## 0.7.0 (2024-09-23)

### Added

The main new feature is the **EnIGMA mode**, which included additions like support for Interactive Agent Tools
and Summarizers.

* Add filemap command in the spirit of repomap by [@samuela](https://github.com/samuela) in [#619](https://github.com/SWE-agent/SWE-agent/pull/619)
* Create config to run human eval style challenges by [@ofirpress](https://github.com/ofirpress) in [#658](https://github.com/SWE-agent/SWE-agent/pull/658)
* Add claude 3.5 sonnet to models by [@carlosejimenez](https://github.com/carlosejimenez) in [#601](https://github.com/SWE-agent/SWE-agent/pull/601)
* Enh: Warn if scrolling >= 3 times by [@klieret](https://github.com/klieret) in [#626](https://github.com/SWE-agent/SWE-agent/pull/626)
* feat: support deepseek-coder LLM by [@jcraftsman](https://github.com/jcraftsman) in [#638](https://github.com/SWE-agent/SWE-agent/pull/638)
* Enh: Make timeout for agent commands configurable by [@klieret](https://github.com/klieret) in [#674](https://github.com/SWE-agent/SWE-agent/pull/674)
* Add support for new gpt-4o-mini model by [@ivan4722](https://github.com/ivan4722) in [#693](https://github.com/SWE-agent/SWE-agent/pull/693)
* Groq Models Integration by [@MohammedNagdy](https://github.com/MohammedNagdy) in [#721](https://github.com/SWE-agent/SWE-agent/pull/721)
* Make log level configurable; add TRACE level by [@klieret](https://github.com/klieret) in [#612](https://github.com/SWE-agent/SWE-agent/pull/612)

### Fixes

* Compatibility with SWE-bench 2.0 by [@klieret](https://github.com/klieret) in [#671](https://github.com/SWE-agent/SWE-agent/pull/671)
* ensure variables work in special command docstring by [@forresty](https://github.com/forresty) in [#628](https://github.com/SWE-agent/SWE-agent/pull/628)
* Important fix: Catch CostLimitExceeded in retry because of format/block by [@klieret](https://github.com/klieret) in [#682](https://github.com/SWE-agent/SWE-agent/pull/682)
* Fix: Handle empty traj in should_skip by [@klieret](https://github.com/klieret) in [#616](https://github.com/SWE-agent/SWE-agent/pull/616)
* Fix for end-marker communicate: Exit status always 0/invalid by [@klieret](https://github.com/klieret) in [#644](https://github.com/SWE-agent/SWE-agent/pull/644)
* Fix: Insufficient quoting of git commit message by [@klieret](https://github.com/klieret) in [#646](https://github.com/SWE-agent/SWE-agent/pull/646)
* Fix nonsensical trajectory formatting for PRs by [@klieret](https://github.com/klieret) in [#647](https://github.com/SWE-agent/SWE-agent/pull/647)
* Fix: sweunexpected keyword 'python_version' by [@klieret](https://github.com/klieret) in [#692](https://github.com/SWE-agent/SWE-agent/pull/692)
* Fix: Use LONG_TIMEOUT for pre_install commands by [@klieret](https://github.com/klieret) in [#695](https://github.com/SWE-agent/SWE-agent/pull/695)
* Fix: UnboundLocalError when catching decoding issue by [@klieret](https://github.com/klieret) in [#709](https://github.com/SWE-agent/SWE-agent/pull/709)
* Also create empty patch files for completeness by [@klieret](https://github.com/klieret) in [#725](https://github.com/SWE-agent/SWE-agent/pull/725)
* Fix: Raise ContextWindowExceeded instead of exit_cost by [@klieret](https://github.com/klieret) in [#727](https://github.com/SWE-agent/SWE-agent/pull/727)
* Fix: Deal with non-utf8 encoded bytes in comm by [@klieret](https://github.com/klieret) in [#731](https://github.com/SWE-agent/SWE-agent/pull/731)
* Fix: Handle spaces in repo names by [@klieret](https://github.com/klieret) in [#734](https://github.com/SWE-agent/SWE-agent/pull/734)
* Fix: Ensure utils is part of package by [@klieret](https://github.com/klieret) in [#742](https://github.com/SWE-agent/SWE-agent/pull/742)
* Fix: Submitting ' ' in human mode crashes container by [@klieret](https://github.com/klieret) in [#749](https://github.com/SWE-agent/SWE-agent/pull/749)
* Fix: Block su as command by [@klieret](https://github.com/klieret) in [#752](https://github.com/SWE-agent/SWE-agent/pull/752)
* Fix: SWE_AGENT_MODEL_MAX_RETRIES needs casting by [@klieret](https://github.com/klieret) in [#757](https://github.com/SWE-agent/SWE-agent/pull/757)

### New Contributors

🎉 **@talorabr, @udiboy1209, @haoranxi, @NickNameInvalid, @rollingcoconut joined the team to build EnIGMA** 🎉

* @carlosejimenez made their first contribution in [#601](https://github.com/SWE-agent/SWE-agent/pull/601)
* @samefarrar made their first contribution in [#606](https://github.com/SWE-agent/SWE-agent/pull/606)
* @hubstrauss made their first contribution in [#625](https://github.com/SWE-agent/SWE-agent/pull/625)
* @samuela made their first contribution in [#619](https://github.com/SWE-agent/SWE-agent/pull/619)
* @forresty made their first contribution in [#628](https://github.com/SWE-agent/SWE-agent/pull/628)
* @jcraftsman made their first contribution in [#638](https://github.com/SWE-agent/SWE-agent/pull/638)
* @ivan4722 made their first contribution in [#693](https://github.com/SWE-agent/SWE-agent/pull/693)
* @JoshuaPurtell made their first contribution in [#703](https://github.com/SWE-agent/SWE-agent/pull/703)
* @MohammedNagdy made their first contribution in [#721](https://github.com/SWE-agent/SWE-agent/pull/721)
* @pdemro made their first contribution in [#729](https://github.com/SWE-agent/SWE-agent/pull/729)

## 0.6.1 (2024-06-20)

[All new commits](https://github.com/SWE-agent/SWE-agent/compare/v0.6.0...v0.6.1)

This is (mostly) a patch release, in particular fixing several issues that had been introduced by the speed improvements of v0.6.0.
We also solve a bug where existing linter errors in a file left SWE-agent unable to edit (because of our lint-retry-loop).

### Breaking changes

* Change: sparse clone method is now correctly called "shallow" by [@klieret](https://github.com/klieret) in [#591]([#591](https://github.com/SWE-agent/SWE-agent/pull/591))

### Improved

* Enh: Show commands when encountering timeout error by [@klieret](https://github.com/klieret) in [#582]([#582](https://github.com/SWE-agent/SWE-agent/pull/582))
* Enh: Configuration option to show time in log by [@klieret](https://github.com/klieret) in [#583]([#583](https://github.com/SWE-agent/SWE-agent/pull/583))
* Enh: Allow to configure LONG_TIMEOUT for SWEEnv by [@klieret](https://github.com/klieret) in [#584]([#584](https://github.com/SWE-agent/SWE-agent/pull/584))
* Enh: Always write log to traj directory by [@klieret](https://github.com/klieret) in [#588]([#588](https://github.com/SWE-agent/SWE-agent/pull/588))

### Fixed

* fix `docker.errors.NotFound` by [@klieret](https://github.com/klieret) in [#587]([#587](https://github.com/SWE-agent/SWE-agent/pull/587))
* Fix: Revert to full clone method when needed by [@klieret](https://github.com/klieret) in [#589]([#589](https://github.com/SWE-agent/SWE-agent/pull/589))
* Fix: Refresh container_obj before querying status by [@klieret](https://github.com/klieret) in [#590]([#590](https://github.com/SWE-agent/SWE-agent/pull/590))
* Fixed #571 - show message that model arg is ignored in case of using Azure OpenAI by [@jank](https://github.com/jank) in [#592]([#592](https://github.com/SWE-agent/SWE-agent/pull/592))
* Fix: Linting blocks for existing lint errors by [@klieret](https://github.com/klieret) in [#593]([#593](https://github.com/SWE-agent/SWE-agent/pull/593))
* Fix: Process done marker not found in read with timeout by [@klieret](https://github.com/klieret) in [#596]([#596](https://github.com/SWE-agent/SWE-agent/pull/596))

## 0.6.0 (2024-06-05)

[All new commits](https://github.com/SWE-agent/SWE-agent/compare/v0.5.0...v0.6.0)

**We sped up SWE-agent by 2x** (timed with GPT4o). This is mostly due to faster communication with the running processes inside of the Docker container and other container setup & installation related improvements. Here are a few relevant PRs:

* Switch to fast communicate and shallow clone by default by [@klieret](https://github.com/klieret) in [#530]([#530]([#530](https://github.com/SWE-agent/SWE-agent/pull/530)))
* Change: Only wait 1s for docker to start by [@klieret](https://github.com/klieret) in [#541]([#541]([#541](https://github.com/SWE-agent/SWE-agent/pull/541)))
* Feat: experimental shallow cloning by [@klieret](https://github.com/klieret) in [#498]([#498]([#498](https://github.com/SWE-agent/SWE-agent/pull/498)))
* Enh: Start from clone of python conda environment for speedup by [@klieret](https://github.com/klieret) in [#548]([#548]([#548](https://github.com/SWE-agent/SWE-agent/pull/548)))
* Enh: Use uv for editable install by default by [@klieret](https://github.com/klieret) in [#547]([#547]([#547](https://github.com/SWE-agent/SWE-agent/pull/547)))

### Improved

* Improve scrolling behavior in web UI by [@anishfish2](https://github.com/anishfish2) in [#420]([#420]([#420](https://github.com/SWE-agent/SWE-agent/pull/420)))
* Web UI: Render Markdown in agent feed messages. by [@kwight](https://github.com/kwight) in [#486]([#486]([#486](https://github.com/SWE-agent/SWE-agent/pull/486)))
* Enh: Remove redundant 'saved traj to X' messages by [@klieret](https://github.com/klieret) in [#528]([#528]([#528](https://github.com/SWE-agent/SWE-agent/pull/528)))
* Allow to disable config dump to log by [@klieret](https://github.com/klieret) in [#537]([#537]([#537](https://github.com/SWE-agent/SWE-agent/pull/537)))
* Resolve relative paths to demonstrations and commands by [@klieret](https://github.com/klieret) in [#444]([#444]([#444](https://github.com/SWE-agent/SWE-agent/pull/444)))

### Fixed

* Web UI: Remove -n option to wait by [@klieret](https://github.com/klieret) in [#487]([#487]([#487](https://github.com/SWE-agent/SWE-agent/pull/487)))
* Web UI: Kill the Flask server on exit. by [@kwight](https://github.com/kwight) in [#479]([#479]([#479](https://github.com/SWE-agent/SWE-agent/pull/479)))
* Web UI: Avoid proxy errors on MacOS by [@klieret](https://github.com/klieret) in [#506]([#506]([#506](https://github.com/SWE-agent/SWE-agent/pull/506)))
* Ensure container_name is reset for non-persistent containers by [@klieret](https://github.com/klieret) in [#463]([#463]([#463](https://github.com/SWE-agent/SWE-agent/pull/463)))
* Fix: Do not allow persistent container with cache task imgs by [@klieret](https://github.com/klieret) in [#551]([#551]([#551](https://github.com/SWE-agent/SWE-agent/pull/551)))


## 0.5.0 (2024-05-28)

[All new commits](https://github.com/SWE-agent/SWE-agent/compare/v0.4.0...v0.5.0)

✨ The big news is our [brand new documentation](https://swe-agent.com/latest/) ✨

Secondly, @ollmer added a new flag `--cache_task_images` that will significantly speed up SWE-agent when running on the same environment/repository multiple times (no more waiting for cloning and installation!)

### Breaking changes

* We have reformatted our codebase. If you create a PR based on a previous commit, make sure you install our `pre-commit` hook to avoid merge-conflicts because of formatting. See [our docs](https://swe-agent.com/latest/dev/formatting_conflicts/) for more information.
* Remove direct imports in `__init__.py` (you can no longer `from sweagent import Agent` by [@klieret](https://github.com/klieret) in [#436]([#436]([#436](https://github.com/SWE-agent/SWE-agent/pull/436)))

### Added

* Running the web UI is now supported when running swe-agent completely in docker
* Speed up evaluation by caching task environments as docker images by [@ollmer](https://github.com/ollmer) in [#317]([#317]([#317](https://github.com/SWE-agent/SWE-agent/pull/317)))

### Improved

* Add gpt-4o model by [@raymyers](https://github.com/raymyers) in [#344]([#344]([#344](https://github.com/SWE-agent/SWE-agent/pull/344)))
* Web: Allow to specify commit hash by [@klieret](https://github.com/klieret) in [#358]([#358]([#358](https://github.com/SWE-agent/SWE-agent/pull/358)))
* Add default environment_setup config by [@klieret](https://github.com/klieret) in [#351]([#351]([#351](https://github.com/SWE-agent/SWE-agent/pull/351)))
* Enh: Suppress openai logging; improve formatting of stats by [@klieret](https://github.com/klieret) in [#416]([#416]([#416](https://github.com/SWE-agent/SWE-agent/pull/416)))
* Remove signal dependency by [@klieret](https://github.com/klieret) in [#428]([#428]([#428](https://github.com/SWE-agent/SWE-agent/pull/428)))
* Do not use select if running on Windows by [@klieret](https://github.com/klieret) in [#429]([#429]([#429](https://github.com/SWE-agent/SWE-agent/pull/429)))
* Use custom Config class to support env and keys.cfg (this allows passing keys as environment variables) by [@klieret](https://github.com/klieret) in [#430]([#430]([#430](https://github.com/SWE-agent/SWE-agent/pull/430)))

### Fixed

* Web: Fix script_path input by [@klieret](https://github.com/klieret) in [#334]([#334]([#334](https://github.com/SWE-agent/SWE-agent/pull/334)))
* Fix: Don't print patch msg for exit_cost patch by [@klieret](https://github.com/klieret) in [#343]([#343]([#343](https://github.com/SWE-agent/SWE-agent/pull/343)))
* Fix: Do not request job control in bash by [@klieret](https://github.com/klieret) in [#345]([#345]([#345](https://github.com/SWE-agent/SWE-agent/pull/345)))
* Fix: --base_commit not used for gh urls by [@klieret](https://github.com/klieret) in [#346]([#346]([#346](https://github.com/SWE-agent/SWE-agent/pull/346)))
* Fix: Separate data path/traj dir cause exception by [@klieret](https://github.com/klieret) in [#348]([#348]([#348](https://github.com/SWE-agent/SWE-agent/pull/348)))
* Add docker-py lower bound by [@klieret](https://github.com/klieret) in [#406]([#406]([#406](https://github.com/SWE-agent/SWE-agent/pull/406)))
* Fix: IndexError when replaying incomplete trajectories by [@klieret](https://github.com/klieret) in [#410]([#410]([#410](https://github.com/SWE-agent/SWE-agent/pull/410)))


## 0.4.0 (2024-05-09)

[All new commits](https://github.com/SWE-agent/SWE-agent/compare/v0.3.0...v0.4.0)

### Added

We’re excited to launch the SWE-agent web UI! Specify a bug, press start and watch SWE-agent do the magic.

## 0.3.0 (2024-05-02)

### Added

* Run SWE-agent in the cloud using GitHub Codespaces
* Add GPT4-turbo model by [@zgrannan](https://github.com/zgrannan) in [#252]([#252]([#252](https://github.com/SWE-agent/SWE-agent/pull/252)))
* feat: Amazon Bedrock support (Claude models) by [@JGalego](https://github.com/JGalego) in [#207]([#207]([#207](https://github.com/SWE-agent/SWE-agent/pull/207)))

### Fixed

* Better error handling for --open_pr by [@klieret](https://github.com/klieret) in [#239]([#239]([#239](https://github.com/SWE-agent/SWE-agent/pull/239)))
* Fixed a potential error by [@DanjieTang](https://github.com/DanjieTang) in [#242]([#242]([#242](https://github.com/SWE-agent/SWE-agent/pull/242)))
* fix: TARGETARCH not set on some OS/docker setups by [@mspronesti](https://github.com/mspronesti) in [#249]([#249]([#249](https://github.com/SWE-agent/SWE-agent/pull/249)))
* Pass Python version to get_environment_yml by [@waterson](https://github.com/waterson) in [#271]([#271]([#271](https://github.com/SWE-agent/SWE-agent/pull/271)))
* Fix Together model validation error by [@mikanfactory](https://github.com/mikanfactory) in [#236]([#236]([#236](https://github.com/SWE-agent/SWE-agent/pull/236)))
* Doc: Avoid invalid github token by [@klieret](https://github.com/klieret) in [#292]([#292]([#292](https://github.com/SWE-agent/SWE-agent/pull/292)))

## 0.2.0 (2024-04-15)

[All new commits](https://github.com/SWE-agent/SWE-agent/compare/v0.1.2...v0.2.0)

### Added

* Allow to run on local repos (new flag: `--repo_path`) in [#193]([#193]([#193](https://github.com/SWE-agent/SWE-agent/pull/193)))
* Patch files are now saved separately to a patch directory in [#126]([#126]([#126](https://github.com/SWE-agent/SWE-agent/pull/126)))
* Allow to supply custom installation commands when running on gh issues or locally (`--environment_setup`) in [#153]([#153]([#153](https://github.com/SWE-agent/SWE-agent/pull/153)))
* Allow to specify openapi base url in `keys.cfg` in [#118]([#118]([#118](https://github.com/SWE-agent/SWE-agent/pull/118)))

### Improved

* Improve error handling of docker issues in [#165]([#165]([#165](https://github.com/SWE-agent/SWE-agent/pull/165)))
* Make github token fully optional in [#189]([#189]([#189](https://github.com/SWE-agent/SWE-agent/pull/189)))

### Fixed

* Fix opening PR from fork in [#229]([#229]([#229](https://github.com/SWE-agent/SWE-agent/pull/229)))
* Fix: Choosing TogetherAI models in [#130]([#130]([#130](https://github.com/SWE-agent/SWE-agent/pull/130)))
