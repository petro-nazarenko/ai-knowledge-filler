# Changelog

All notable changes to AKF are documented here.
## [1.0.4] — 2026-03-17

### Bug Fixes

- Groq retry loop drops user prompt, causing stale system-prompt content ([`d5edfd1`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/d5edfd15a8677c608db1e446dc025f439d0bc736))

### Documentation

- Update CHANGELOG for v1.0.3 ([`27406f9`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/27406f961ef00ab0dd954100f10085bced68d114))

## [1.0.3] — 2026-03-17

### Bug Fixes

- Prevent weaker LLMs from copying system prompt — v1.0.3 ([`00b905c`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/00b905c079406aeab393aafcd0b1ca9179b68f14))

### Chores

- Update uv.lock after v1.0.3 version bump ([`ee0dd60`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/ee0dd60609ca9641940309e6cd92d0786a60172c))

### Documentation

- Update CHANGELOG for v1.0.2 ([`b0652c1`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/b0652c1cb9a169e0a785e260f126845c64d2f552))

## [1.0.2] — 2026-03-16

### Bug Fixes

- BUG-A/BUG-B regressions + date patch, bump to v1.0.2 ([`c713abc`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/c713abc7e25f00fcfbaeca9236ea01a5b8f395ed))

### Documentation

- Update CHANGELOG for v1.0.1 ([`b10fe3e`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/b10fe3e53d1c0ccad05092cbc2ec8c35dd606079))
- Rewrite README — content production system positioning, 715/92%, E008, MCP stable ([`ec14552`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/ec14552cc89ae89e727b52e0bee525641895e45f))

### Features

- Add financial assessment & market value as Stage 4 of market pipeline ([`3bad90c`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/3bad90ce9b6877bc5998d5d169b7c6d428641075))

## [1.0.1] — 2026-03-13

### Bug Fixes

- Add YAML frontmatter to docs/market-analysis.md ([`638e696`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/638e696dd28f0f66da7922233f41ab84924778ea))
- Add isinstance(related, list) guard in _check_related and use yaml.safe_dump in make_doc ([`5408bca`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/5408bca2cc4e676fd1ace987d434f17fd6e6587a))
- Support direct script execution for indexer ([`be4ebc5`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/be4ebc526e8ab71fcd02030a581e11a4691ed443))
- Avoid 422 by using decorator-level concurrency dependencies ([`9a00d8b`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/9a00d8b7d78a973400f8472e7ca0a554413416bf))
- Enforce concurrency in middleware to avoid CI 422 ([`96db7f1`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/96db7f1550afc8507db42204b200cc78a8d74eb9))
- Remove slowapi decorators from POST endpoints ([`6ef6571`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/6ef6571d6945e58b260991f03602dccf02e555ae))
- Unify validation source and consolidate CI workflows ([`ff47e08`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/ff47e08886e028d310d6000f62f2293552365c4c))
- Prevent LLM from reproducing system_prompt examples ([`96b6bff`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/96b6bff1023140fa537c2d42d3f201142b8c4f2b))
- Market_pipeline outputs validated before disk write ([`062f066`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/062f0663fa3c103f37b164474e7ab3ad00902c49))
- Enrich telemetry writer always None — events were silently dropped ([`3c359ed`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/3c359ed7dbdc0fe14e3bcb12ec5c9cf28f543cb7))
- Market_pipeline loads domain taxonomy from akf.yaml instead of hardcoding ([`42e11c8`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/42e11c8b57a82d29d258ed88413fbed67647a4b8))
- Emit AskQueryEvent telemetry from CLI ask command ([`7055f3f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/7055f3f3de98d91ac60fe0bf619229ce961a136b))
- Resolve pipeline.py merge conflict — use anchored_prompt ([`3dd29e7`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/3dd29e72af335024b66add5587ecac335441c7e0))
- Bump anthropic to 0.50.0 in requirements.lock ([`ca99c50`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/ca99c507309ff4a57cf8e89d0202bfdf075defe5))
- Align pipeline RAG interface and telemetry guard with tests ([`bdfd066`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/bdfd066ef092af5d0486ebb542d94574bd5abb83))
- Add TYPE_CHECKING imports for TelemetryWriter and AKFConfig in market_pipeline ([`cc0601e`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/cc0601e5ff0b38ae9abbc4012430203322ead5d5))
- Set domain to akf-core in ADR-002 and ADR-004 for docs taxonomy ([`7f18706`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/7f1870627aab30ccfe4ae0556e8198a5b9ffa47c))
- Address top 3 post-v1.0.0 audit findings ([`feb85ae`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/feb85aeba158fd690d0eb8d57cac08ba93b613dc))

### CI/CD

- Gate on changed python files in PR ([`2cde850`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/2cde850977cd4d8c947f9c3bbee1751dc63b0727))
- Enforce locked deps in workflows ([`6706d49`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/6706d499baa1608b835f11254669a46bb30a6d9a))
- Install test/lint tooling under locked constraints ([`22f9828`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/22f982802c80a37a89c96315053b6e81305fad5e))
- Fix multiline target expansion for ruff/black/mypy ([`5e9e834`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/5e9e8349805caf2ae54fabf658c7384c8e261e25))
- Scope push lint targets to changed files ([`98a4fd9`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/98a4fd9fbef4b54f8913e6131b5299d1fc02506d))
- Make Codecov upload non-blocking ([`a4e0556`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/a4e05563cb2bd039a9b4e71e08ff9d30611a2e8b))
- Restore full-repo lint gate and harden dependency/secrets policy ([`f4ab258`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/f4ab258dc143c7ecf062c4086346a608274905a0))
- Unify lint policy and harden workflow supply chain ([`d88f95d`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/d88f95d87b533a36bdd93b73ca7e1df6e40bab7f))
- Unify coverage threshold and enable full ruff gate ([`133692a`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/133692ad9ea874e3d5bc6557a42ef2fae41a7add))

### Chores

- Update dependencies to match codebase ([`5d68dda`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/5d68ddab1c6230effc47bab3ec2e1bd7befc90d8))
- Repo cleanup — ADRs updated, artifacts removed, README tagline fixed, CHANGELOG closed, deps hygiene ([`9c14f26`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/9c14f26830bbb3ad3489f846d0e23914f5507d42))
- Add uv.lock lockfile ([`50a8516`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/50a8516b63ee388651aef581a0c1c3714a64bed8))
- Bump version to 1.0.1 to update PyPI metadata and README ([`e7f5d87`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/e7f5d87d3a40f6d28428abf7b1b17d828493dcee))

### Documentation

- Update CHANGELOG for v0.7.0 ([`49b127d`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/49b127d6143e413d940bda33bc0738c90770d3b6))
- Update current state — add E008 typed relationships to ARCHITECTURE and README ([`7530680`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/7530680746ee28baf94777ce6bccf6674a618173))
- Create wiki pages for repo ([`b6fa422`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/b6fa422f9a8da89ab5cc6263b7dcc91f63a3a688))
- Update CHANGELOG for v0.8.0 ([`d6b14ea`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/d6b14ea4ae2c7526d4e33c1a5f2488a80849a0b1))
- Update positioning to AI-powered content production system ([`10a75f9`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/10a75f9e1ad8be602f73ee0ed066680f3da77b17))

### Features

- Add three-stage market analysis pipeline ([`412e24e`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/412e24e9d123121c168fe13f79cd7aeb51d50228))
- Generate test fixture corpus from plan.json via Claude provider ([`b1cd88d`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/b1cd88df40efdad5f6ba99f8fabe651cd2b0c60e))
- Add typed relationships support with E008 validation ([`7b30683`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/7b30683abe241ec9ebd9f60d178e84bf35e80b7a))
- Add phase 1 corpus indexer with chroma storage ([`3f457bc`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/3f457bce862fe5682ffab8395108cfef5997dba8))
- Add phase 2 retriever query layer ([`d489ea7`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/d489ea7d6b5d4c8f1fbb79c47632a864d3796d67))
- Add phase 3 copilot answer synthesis ([`f7e688a`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/f7e688a99aee85679791742285814bf56fe814e1))
- Add akf ask command for rag copilot ([`06e76ff`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/06e76ffeb1423ab44cfebfb01ec426e4c10386b2))
- Add no-llm retrieval mode for ask ([`484e8e1`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/484e8e1f0dfb7373cb760099f00c85953b19734d))
- Add /v1/ask endpoint for rag qa ([`4601893`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/4601893e4bacbfd3dce07a81f5e0a960b2a85bb0))
- Add ask guardrails and telemetry events ([`6f09238`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/6f09238f251ca0c34634e397b83da983b2c67856))
- Add tenant-level ask usage tracking ([`f2cf2c8`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/f2cf2c8dc8d34b117864d0affd2d2f3d6c1cd8cd))
- RAG scaffolding + spec ([`28df7cc`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/28df7cc27bbd06a60bd00226df52ad0fff511e5f))
- Standardize config/telemetry injection across Pipeline and MarketAnalysisPipeline ([`3f1e3e9`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/3f1e3e9bcda242a7daf4832a3dd2b7c84963d0b1))
- Add akf index CLI subcommand ([`77056f0`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/77056f0e10e06721d23d9b1a2ba6cff2ddbbc2b9))
- Inject RAG corpus context into akf generate ([`b13b884`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/b13b884827bcde74309c22ac91044e2f600b878b))

### Security

- Require auth for metrics endpoint ([`f605359`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/f6053593f651065d957dd4ad781ac2bfff291630))
- Sanitize output filename and tune CI coverage gate ([`9cea6f4`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/9cea6f40e695ee80cd09c165e28cd6d9838cc1cc))

### Testing

- Add tests for telemetry gaps fixes 6, 7, and 8 ([`26152be`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/26152be075f54e19e0af4d04fdef7d90c43eed58))

### prod

- Harden REST API + strict CI + security baseline ([`f9d74ca`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/f9d74caa579206d2a2189106a4e8f6f56d16677a))

### release

- Bump to v1.0.0 — fix BUG-1, SEC-L3, sync all docs ([`157b5f1`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/157b5f189ef2770324750a61966b47fc65bdffa4))

## [0.7.0] — 2026-03-07

### Documentation

- Update CHANGELOG for v0.6.2 ([`88c0e4f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/88c0e4fc49bd592f8e4862973266b8df1ff0ee69))

## [0.6.2] — 2026-03-07

### Bug Fixes

- Rename GenerateResult.path to file_path, fix mcp_server plan item guard ([`1dd3737`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/1dd3737426a403e27c71a38ec6845657f4395f6f))
- SEC-M2 path traversal protection in sanitize_filename ([`54ba5e5`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/54ba5e5f26aa692b12ac61e97c18e618c0f0e127))
- SEC-L2 backup akf.yaml before --force overwrite ([`5d5688e`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/5d5688e12e6baf8d1d101aeece9881ab99e80129))
- Correct system_prompt.md in package (remove YAML frontmatter) ([`4ce9771`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/4ce97714b4056218dea78793945de25bc3d8de67))

### Documentation

- Update CHANGELOG for v0.6.0 ([`2c5978e`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/2c5978e964a1bc1aa60d985358ea43b48322347f))
- Update CHANGELOG for v0.6.1 ([`7c27250`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/7c27250d610ac45f75fec7262f064445dc33de16))
- Update README, user-guide, cli-reference for v0.6.1 — MCP, batch, transport ([`1a11516`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/1a1151685a0b2bbe8ba17da25aa222e2b06fd370))
- Rewrite README to match validation pipeline positioning ([`9beeed6`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/9beeed6c0f9ac9dcbc1a1733db30eaffb3d83520))
- Sync all docs to v0.6.1 ([`a3fb74a`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/a3fb74a49da8eb821565b409269606434684812a))
- Update result.path → result.file_path ([`db8cbbb`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/db8cbbb620617b66b5dc7c9d6035e6af5352e9ea))

### Features

- MCP --transport flag (stdio/streamable-http) — v0.6.1 ([`4bcbdd5`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/4bcbdd5586006bec5161151191b26bd201431662))

### examples

- Add akf.yaml reference configs (software-engineering, legal-ops, technical-writing) ([`18d10e3`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/18d10e34740c64be0672a8c0b073093ff06a3b86))

## [0.6.0] — 2026-03-02

### Chores

- Bump version to 0.6.0 ([`d882315`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/d8823154c7bdb94c2f1424ebe327cc6a2231c95f))

### Documentation

- Update CHANGELOG for v0.5.4 ([`41c869f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/41c869fd464bf2692b5fda8cb9e16cf48995ea35))

### Features

- MCP server v0.6.0 — akf serve --mcp ([`8040eac`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/8040eacaa6a1f8e6360c533e8f171a86b6e26793))

## [0.5.4] — 2026-02-28

### Bug Fixes

- Changelog bot pull --rebase before push ([`4960df8`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/4960df830db8e9b21ca7c97891bdae3002220298))
- Remove schema_version enforcement from commit_gate (BUG-2) ([`e3d2e86`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/e3d2e86713ce6ab78400bfa359ab9cc2212fe32d))

### Documentation

- Update CHANGELOG for v0.5.3 ([`e80ef58`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/e80ef589cb1b715d150de9c0f609695471a435f4))
- Update CHANGELOG for v0.5.4 ([`bf2040d`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/bf2040da739d3473cd494c0b4734dd9c8edc14bb))

## [0.5.3] — 2026-02-27

### Chores

- Add telemetry/ to .gitignore ([`2d8bb92`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/2d8bb92c9a1358f50d8afb1c2ccb0c50598a91bd))
- Remove root system_prompt.md — canonical in akf/ ([`6d85260`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/6d852604a0ebe8d2611c5166e25a2cb2778d7eec))

### Documentation

- Update CHANGELOG for v0.5.2 ([`06e56b2`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/06e56b22a916c322cbc6e80d71c947b2f2f12bd0))
- Migrate ARCHITECTURE, CONTRIBUTING, ADR-001 to public docs with frontmatter (v0.5.2) ([`0a47ae2`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/0a47ae2fb2e1aec8041ed9b441bf1db133bc31aa))
- Fix WikiLinks → relative paths in cli-reference and user-guide ([`d9f0833`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/d9f0833ddba4602ba689e9f24cde20450a161a09))

### Features

- Add akf generate --batch for JSON plan-driven bulk generation (v0.5.3) ([`c9f1602`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/c9f1602f5438a05d9085210703601c0daf5e8bb5))

## [0.5.2] — 2026-02-27

### Bug Fixes

- Load_system_prompt() — package-only, remove CWD fallback (v0.5.2) ([`d6d911b`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/d6d911b0c5ac9ab224fa8314046b56642b606a57))
- Update pypa/gh-action-pypi-publish to v1.12.4 (Debian buster EOL) ([`e84feb4`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/e84feb46840096598a328dea3b768beb2e3d2c41))
- Update git-cliff-action to v4 (Debian buster EOL) ([`c7615ee`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/c7615eeefd67467e8b4a57e3e6f3e671f4a6efb9))

### CI/CD

- Add git-cliff changelog generation on tag push ([`1203b41`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/1203b418b2d7b6fe3070d5b23d459629e753d26d))

## [0.5.1] — 2026-02-27

### Bug Fixes

- Graceful ProviderUnavailableError in akf enrich (v0.5.1) ([`f1e3eff`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/f1e3effbcab743bf84eb4bae449d2d58d6173752))

## [0.5.0] — 2026-02-27

### Bug Fixes

- Add conftest.py to isolate tests from repo akf.yaml ([`5ec88a9`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/5ec88a940a0d7fb6dfb495b3dfecba3d6cf75104))

### CI/CD

- Fix validate workflow — use akf validate --path docs/ ([`234d3b4`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/234d3b45d7ca21c38a975f398ea9025e2cbfa3df))

### Chores

- Remove FETCH_HEAD and .pylint_cache from tracking ([`ebb1692`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/ebb169204078672c67ab90c45c9fb558f25f6d01))
- Add akf.yaml for repo self-documentation ([`86d413f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/86d413fb5f3f2dcee5edf101dce6229d51ed48da))
- Bump version to 0.5.0 ([`2d81821`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/2d818214061dc0535042b910fb2d1e621fec3476))

### Documentation

- Rewrite README for AI engineers ([`98c69a4`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/98c69a434fa6f7c65fa5e2640f5d43cbebe98eb4))
- Rewrite README and description for AI engineers ([`ae8ed7d`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/ae8ed7d0e206f24f9c8bf2789e49e3ed1dc2b633))
- Update CONTRIBUTING and ARCHITECTURE for Phase 2.5 ([`f12bc6e`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/f12bc6e24f3a2c446caa15493365327fc310bba0))
- Add cli-reference and user-guide v2.0 (domain: akf-docs) ([`fe14fa0`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/fe14fa0af45a5146504acfb87705de56f1b7d9fc))
- README v3 — AKF documents itself, akf enrich, v0.5.0 ([`601b040`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/601b040ad02befbc4778d6e075710eb5e507a514))

### Features

- Add akf enrich command (v0.5.0) ([`3597fff`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/3597fff057035ad85a6b46df1c821d10ee0bcf6f))

## [0.4.2] — 2026-02-26

### Bug Fixes

- Python 3.10/3.11 compat — add future annotations to server.py ([`c972ed5`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/c972ed5f9552605ac8f78282a1ad1b065fdc5065))
- Install [all] extras in tests.yml to include slowapi ([`2707c38`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/2707c38c212612e42f2cf86fb35719e9a484ba9b))
- Install all deps in release workflow ([`194da03`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/194da033ec797de66bdeaa438b813dd2be2d942b))
- Release workflow deps ([`5bb015f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/5bb015f8d0664bec6d6557229bdda5731b186746))

### CI/CD

- Add fastapi uvicorn httpx to test dependencies ([`04651ad`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/04651ad5be404413d122b5ee02fdd0f5641a264b))
- Install [all] deps including slowapi; security: auth + rate limiting; test: 94.6% coverage ([`8d860f6`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/8d860f69ebfb95093c0b623077a29758ea69551f))

### Documentation

- Fix version in README footer ([`1431652`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/14316524e3b622eefdb8ca7f023b4506c072c584))
- Update README — Pipeline API, REST API, akf serve, 425 tests ([`7c9af12`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/7c9af12591ce680f3bc55f530ae5249aadb9681c))
- Remove internal KPI from roadmap ([`6c18b6f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/6c18b6ff39cca1919151ed58192301d9beedc004))

### Features

- Pipeline class — programmatic API (Stage 2) ([`b976f97`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/b976f972b0e0c3cd74018e909e04f85490b773c6))
- REST API + akf serve (Stage 3) ([`1afe4bc`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/1afe4bced1ad739f6ab0ad0dca448cf24d5f3572))

### Security

- API auth, rate limiting, prompt validation; test: 94.6% coverage (487 tests) ([`844861e`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/844861eac4cdc9d29f7a70c3411db7f273b52592))

### Testing

- Pipeline and API coverage — 88% total (425 tests) ([`1d4035f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/1d4035f4278a3a0c0b9378c37b7c5f38aecefefc))
- Coverage gap tests — 487 passed, 94.6% coverage (+2.4pp) ([`8646c9d`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/8646c9d7f3c2294ca19ef354735e693f34eecc69))

## [0.4.1] — 2026-02-26

### Chores

- Repo polish — README v0.4.0, CONTRIBUTING, issue templates, PR template, docs ([`5f66d9f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/5f66d9f8ef14d6360461f3a1ebffe13e1ca534c9))
- Remove stray patch files ([`733e12d`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/733e12d24c718e1ecc3cb1df9a84ae5abf90950f))

### Documentation

- Fix absolute URLs for PyPI, bump to v0.4.1 ([`4e65722`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/4e65722e376e6f35a3529eaac6260335e5d64aa5))

## [0.4.0] — 2026-02-25

### Chores

- Remove one-shot migration script ([`4da9c95`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/4da9c95994fd86a7a1a0714a287a07323724dda7))

### Features

- V0.4.0 — validator import fix, E007, W001, UX improvements ([`b82e1fa`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/b82e1fa0811538d68417840414fb9d332402edf9))

## [0.3.0] — 2026-02-25

### Bug Fixes

- Restore test_s2_error_normalizer (null bytes after mobile copy) ([`8c4541a`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/8c4541aa2414a4832ab814a38cf0c29cbd58f5fb))
- Validator.py — imports to module level, explicit datetime.date handling ([`798b377`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/798b3776c349b2b3e503ddf0c361a9b32901f2d9))
- Correct telemetry tests — avoid convergence_failure on attempt 1 ([`dd9b6fc`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/dd9b6fc6cebefb41eef5d0e5a6db11d98f5c2d3a))
- Correct telemetry tests — max_attempts and identical_output event counts ([`c84d718`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/c84d718ae283bffea8de4189d61b3c8ce9459d2d))
- Include akf/defaults/akf.yaml in package data ([`9248009`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/9248009ca37e6e21fadf7ce5bae0ed17a71d74aa))
- Scope coverage to akf only — remove untested modules from cov ([`c6dd43b`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/c6dd43b2c11385be010107a35d26c8e269b74c6a))
- Singleton test — cfg1 is cfg2 instead of domain check ([`aa6022c`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/aa6022c07c99e35747deb98012f6555117ea6bbe))
- Add pip install -e . to install akf package ([`0d43c09`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/0d43c0941d18a3cd551f0afcb989b645294b09af))
- Remove legacy taxonomy_path test — superseded by akf.yaml ([`a98b7ce`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/a98b7ce48439e5ce31abef1f0cf0f16440f81da5))

### CI/CD

- Remove duplicate publish.yml, restrict tag trigger to semver only ([`c9bf09b`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/c9bf09b059eceb71a9a91299af590fc0a97d5b79))

### Chores

- Bump v0.3.0 + Vision block in README ([`14afa27`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/14afa273f69faad27e3503d1df57d2757d115f26))

### Features

- S1 Validation Engine + lower coverage threshold temporarily ([`6134483`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/61344837af6a41c15b63b68b98754565c10b1289))
- Model C — hard enum enforcement (Phase 2.2) ([`51af00b`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/51af00bf1c9a10e425462790c8326b7eade3da58))
- Telemetry JSONL writer — Task 3 (Phase 2.3) ([`b4e460a`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/b4e460a8fa885110a191a8053b910ce18467dafd))
- Emit GenerationAttemptEvent in RetryController (Task 4 / Phase 2.3) ([`a733e75`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/a733e754c280423ebf2bc40fe104ed0348c8a55a))
- Emit GenerationSummaryEvent in CommitGate (Task 5 / Phase 2.3) ([`bc465cf`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/bc465cff7cd60dedbdd50809d9c92da13800c1cf))
- Generation_id propagation through pipeline (Task 6 / Phase 2.3) ([`c78d8bc`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/c78d8bcb37a8f84554000c25ad1d74b50472cf41))
- Telemetry aggregation scripts (Task 7 / Phase 2.3) ([`ed45482`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/ed45482aaece3683679b981eafd3763c765cd922))
- Validator Model D — CANON-DEFER-001/002/003 ([`563e6c0`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/563e6c072aca5af2d0810c1f27557704fb5bec28))
- Add akf/config.py and defaults ([`bb6fdce`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/bb6fdce9a1d3bd788a30788e28fe0a06ec558f1f))
- Akf init command ([`660adb1`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/660adb15df5775a055dc5f6521c3753ffb0f5a47))

### Testing

- S2/S3/S4 — error_normalizer, retry_controller, commit_gate (97% coverage) ([`5f9be64`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/5f9be6414520c8fd82fbbdc945b42066dc283131))
- Analyze_telemetry 47 tests + add --cov=akf to CI (Task 7 / Phase 2.3) ([`aea997d`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/aea997dc81fc968d93de445e0b797a3082ca8686))

## [0.2.0-mvp] — 2026-02-21

### Refactoring

- Reposition as deterministic knowledge compiler ([`80efb8f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/80efb8ffd8c50b65a9e366557c684035ba644f6e))

## [0.2.0] — 2026-02-21

### Bug Fixes

- Replace hardcoded vault path with AKF_OUTPUT_DIR env var (default: cwd) ([`358bcce`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/358bccef5e2acde98c508f0d598dd3d29aaffb9c))
- Correct imports akf.validation_error + akf.error_normalizer ([`97d5fa4`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/97d5fa4d1bb4fcf47af9352e7f25a463fdc179cb))

### CI/CD

- Auto-publish to PyPI on tag ([`245c76b`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/245c76ba0c1ef0881797d44eb3363cde7a950730))
- Fix secret name PYPI_API_TOKEN ([`95e2308`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/95e230865c574b46b03ad03836089e666b2c6b74))

### Chores

- Release v0.2.0 — 165 tests, 97% coverage, validation pipeline ([`8909b6f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/8909b6f1c5e42e46c56081b6b9622f80c82f7ec5))

### Documentation

- Fix test count 82→104 and version 0.1.3→0.1.4 in README ([`0b2e20f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/0b2e20fe28eeb74dfd6122503b2bd73a7f4dea0e))
- Update README for v0.2.0 — validation pipeline, 165 tests ([`d8abc52`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/d8abc520195b9e9a79a2191beddcd3fb1f0e0bd4))

### Features

- ValidationError dataclass + E001-E006 error codes (Phase 2.1 S1) ([`68cf1f7`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/68cf1f7c3d784603b50084044a55cbdb4bed56bb))
- Error Normalizer module — deterministic retry payload (Phase 2.1 S2) ([`869e73e`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/869e73ebad063677d6e8be6b237f44690fd0cc66))
- Error Normalizer + fix coverage config (Phase 2.1 S2) ([`48a1b1f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/48a1b1f73fcc303b659f61a642abe8fb846fef5b))
- Retry Controller + convergence protection (Phase 2.1 S3) ([`0b43644`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/0b43644888a12ff563f95b079589b37bd962b922))
- Commit Gate + schema_version enforcement + atomic write (Phase 2.1 S4) ([`29f0dbf`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/29f0dbfd39f721d2203b82a3b369c1e3e0e5c079))

## [0.1.4] — 2026-02-20

### Bug Fixes

- Exclude ARCHITECTURE.md from YAML frontmatter validation ([`d7abc24`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/d7abc24995577bc59f5113d5e9394c0b605424eb))
- Exclude ARCHITECTURE.md from validate_yaml.py file discovery ([`eaa7df2`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/eaa7df200bbf80508a031b46e6f88c7f3bb5aff6))
- Exclude ARCHITECTURE.md from Scripts/validate_yaml.py ([`6854b44`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/6854b44c4b5728b8a7a4d953da1101d4087a5177))
- Exclude legacy folders from metadata validation ([`08f11bf`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/08f11bfa61ec9fb6d81d6cbae6ff31275775163e))
- Lower coverage threshold to match actual coverage ([`1e740ef`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/1e740ef2d992144c9e6723b6528947d9f750d7eb))
- Exclude root validate_yaml.py duplicate from coverage ([`03f46ee`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/03f46ee34d057711bbe04497efa97bb2cee035f1))
- Adjust coverage threshold ([`1dd24d2`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/1dd24d2e8dd7ed29289bad6e55229623eb89e70b))
- Update import path in test_schema_validation ([`eee7c3d`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/eee7c3dce02c4d6c419e4c9a8f3ad248652ad868))
- Remove invalid --omit flag from pytest command ([`74d16aa`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/74d16aa374be306edef63e2bce84b760c168ed3e))
- Add strict mode, WikiLink validation, Scripts package init ([`feefc5b`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/feefc5bd965a5ba5078ed46eaa219537c498bf80))
- Include Scripts package in pyproject.toml, update ARCHITECTURE.md ([`6c8fc46`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/6c8fc46f991cc53c420d2f6abc38961f7888331d))

### Chores

- Remove build artifacts, stale files from git tracking ([`b79438f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/b79438f404746ce74a0f403c3f25dcc2d9ec359c))
- Remove build artifacts from git tracking ([`ef91730`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/ef91730ea5e1b5e9b99ae63dc90829d81d12160e))
- Remove legacy vault content from repo ([`ddd5626`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/ddd56260855cafdb612688471f60b1f9b03dfc43))
- Bump version to 0.1.4 ([`86b0d26`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/86b0d269a5950438d696469f162ce40127948ea9))

### Documentation

- Phase 1.8 — user guide, CLI reference, architecture, contributing ([`22d5b60`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/22d5b603006bea8ec93f2f586186f7895caeccbe))
- Update README links after legacy folder removal ([`828780c`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/828780cf1999def969492e6660a04d37f5083c52))
- Clean up README — fix links, version, section headers ([`438fe3d`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/438fe3dca0fade484261b62b9a400c8a63da0daa))

## [0.1.3] — 2026-02-19

### CI/CD

- Clean dist before build, add skip-existing ([`e96b3f9`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/e96b3f987ff85b1ddac4c68d1df219018e8b17bf))

### Chores

- Bump version to 0.1.3 ([`de7c020`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/de7c02000e49c6d262a7cda7449a7235aca33beb))
- Clean dist folder ([`63303c4`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/63303c42d4569888ff7046c9a937b0dc0d72b528))

## [0.1.2] — 2026-02-19

### Documentation

- Update README for v0.1.2, fix license warnings ([`8fe051a`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/8fe051a534c2d6038f44651782e8e5d2d22fd8a8))

## [0.1.1] — 2026-02-19

### Add

- Obsidian and workflow files to .gitignore ([`951e458`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/951e458b6a33c2bb0210f65479eee88445d6d030))
- Testing infrastructure setup ([`30609d1`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/30609d1557cc85d01d195e7812b4bf51927b5aea))

### Bug Fixes

- Add coverage-badge dependency to CI/CD workflow ([`7d56706`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/7d5670623d3baafca229365af441d24b047fbdbf))
- Simplify CI workflow, remove problematic badge generation ([`1f34eef`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/1f34eef6fc0d0d3823713edee3bde0f618421cf6))
- Simplify CI workflow, remove problematic badge generation ([`1840f1f`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/1840f1f6a6ae5c47ba0ca992f4c8fd89893e40c2))

### CI/CD

- Release workflow + packaging v0.1.0 ([`3268825`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/3268825e23dc1447386c0d81a75ba9b823a65a9f))
- Skip integration tests in CI pipeline ([`1607b48`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/1607b4892df858ceafcdb301849df4ddb7810442))
- Fix attestations conflict with API token ([`866b98e`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/866b98e3711cbcc21898b037b1f0709d11878acf))
- Switch to PyPI directly, skip TestPyPI ([`5016d91`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/5016d9116d12e9016a42c5e7bf990117ccec0898))

### Chores

- Add Pylint static code analysis ([`a0211f1`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/a0211f105bb25c990684b771cb7d26fbe9281701))
- Add commit message template ([`87912f3`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/87912f323d679bee8ca939059a1e931a1f989d8c))
- Ignore Syncthing versions directory ([`3f7a8d5`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/3f7a8d52ede3e20e0fa1b19599a40b0c8254dea3))
- Update .gitignore ([`f0b8d74`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/f0b8d74f25aed2bdffd45d35292843104de8616b))
- Untrack .coverage file ([`3675037`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/367503703d7bd11e83daffe98e896d5b6a2d5344))
- Bump version to 0.1.1 ([`4389afb`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/4389afb60d73adbdec9e89d81268331dfbc36576))

### Documentation

- Add comprehensive docstrings to all functions ([`71c6b94`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/71c6b9444138d97d09b07e1e4eef510c59a82a9b))
- Add AKF Reference Guide v6.0 and ignore Syncthing files ([`3f47366`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/3f47366d63f62f81bb4ba8b5f59d708b3702220e))
- Optimize README — remove speculation, add concrete value ([`8e7072b`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/8e7072baf8c3bb67309cbc4098827ab92536ce7e))

### Features

- Add type hints and mypy configuration ([`4484901`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/4484901784adeec3b25e65a88d1b2a1e807c6cc9))
- Add type hints and mypy configuration ([`3510ebc`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/3510ebcea3c69ff809d8efebea495766ab5ae641))
- Add comprehensive test suite with 96% coverage ([`8db66e5`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/8db66e5a9408bda27f0845e20b26207dc6c8bc53))
- Complete PHASE 1.1 - Full test coverage (96%) ([`898b137`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/898b1370f26b72dd4e8047b678c91c2c70447158))
- Complete PHASE 1.2 - CI/CD Pipeline ([`22398e9`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/22398e925ac24c2e2d75e64e14debcebbf327b8d))
- Add CLI validation tool ([`0d614a1`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/0d614a15bad5a0cc92c40fad4d2e2758b401d2de))
- Add type hint to main() function ([`7804974`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/780497483d43667a61448e77cfd9d67bd2374abc))
- Implement multi-LLM support ([`3ae28ba`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/3ae28bab3bc8f2c80f9fc7fbe3b6f52b50001356))
- Multi-LLM support (6 providers) - logic validated ([`8f889c2`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/8f889c23ef3debfc8a1f6d9e74112450606466ae))
- Structured logging — replace print() with logger ([`62ce547`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/62ce5477566aed7c7421d79badd33876613bc075))
- Custom exception hierarchy ([`ceea573`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/ceea573c2ca1f3ffddd1161bbf6134bcf424994b))
- Integrate error handling + retry logic into llm_providers ([`5944c9e`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/5944c9eb66f8beec3a23a08a30de9c3d569ff869))
- Add packaging - v0.1.0 ([`3be7af3`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/3be7af3e0c1df8f1d92238816f5c4c489d75f163))

### Fix

- Correct validation script path to Scripts/ ([`1bf4783`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/1bf4783c1a94b62c7791012b4d8890b852b81fe3))
- Load domains from taxonomy ([`da3ae46`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/da3ae46fcdcbc83b4f6f6703f67622f647409a4a))

### Progress

- Testing ([`048b204`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/048b204564535e224672e7496c66e56f9b3795c2))

### Testing

- Add tests for logger + exceptions (82 passed, 96.55% coverage) ([`7e486cc`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/7e486cc845c4e42509ab5579d6a54a2fdc6a8751))

### Update

- Enhanced README with Termux setup, badges, and improved structure ([`05dfa92`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/05dfa92f0ce8638675d5699587b43eb417857c48))

### add

- FETCH_HEAD ([`15ae1c6`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/15ae1c6028b3542c34a112060f612fd7b3023b62))
- Release.yml and 3 more ([`905c9f2`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/905c9f22ce06135eb746b864ab080497de0a4aa4))

### cleanup

- Remove junk files, update .gitignore ([`4d8ac69`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/4d8ac69c06d6b14ee8d8e2e5bbd8a63eabcd387b))

### style

- Apply Black code formatting ([`2315df7`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/2315df7ada8a4a827c72435cb09868882fdf88e0))
- Apply Black code formatting ([`ca48316`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/ca48316daf770eb7326108d5a6f523f68e8f2e33))
- Apply black formatting (Phase 1.3) ([`be50610`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/be50610e5803745642765a9ce54a8862ac97b7a3))
- Apply Black formatting to validate_yaml.py ([`c0497f4`](https://github.com/petrnzrnk-creator/ai-knowledge-filler/commit/c0497f45d54c7844fe0dc0c6ab5108c279e28d22))


