# AGENTS.md:office-harness 协作契约,唯一权威

本仓协作以本文件为准;CLAUDE.md 只是桥接。人读总览走 README.md,agent 手册走 `office-harness --llms`。

## Commands

- 三闸(红即禁提交):`uv run ruff check .` / `uv run ty check src` / `uv run pytest`
- 入口:`uv run office-harness <command>` 或 `.\office-harness.cmd <command>`
- 漂移守卫:`tests/unit/test_cli.py` 锁注册表 ↔ 分发 ↔ --llms ↔ --schema 四向一致

## Must

- 新命令 = 改 `cli.py` COMMANDS 注册表 + `cmds/<域>.py` 薄实现 + `run.py _DISPATCH` 一行 + 测试;三面(帮助/手册/schema)自动跟,禁手维护任何面
- 引擎调用只经 `engine/*.py` 客户端;进程 spawn 集中 `engine/base._execute`(测试缝,monkeypatch 它,别起真引擎)
- 写类命令默认干跑,`--yes` 才落盘;成功退出 ≠ 已执行
- 版本号唯一权威 = pyproject.toml;任何面出现版本必须注入而非手写
- 公开项注释即契约:what 进 docstring,why 进 docs/knowledge/adr/

## Must not

- 禁手改 `--llms`/`--help`/`--schema` 的任何投影产物(它们从注册表渲染)
- 禁在 cmds/ 之外起子进程;禁内联 shell 串拼参数(argv 胶合)
- 禁把引擎 stdout 当文本猜:线协议失败以 stdout 形判,不看退出码
- 禁新增「刻意不做」清单里的件(--format yaml|md、--mcp、token 分页、--llms-full、stdin-Python 模式)而不先改清单

## Read first

- 舰队 harness 惯例:参考 D:\hvperv-harness(本仓形态的蓝本)
- dev-cli 标准:agent 面(七旗标/信封/CTA/裸调用/漂移守卫)
- 引擎坑位图:docs/knowledge/references/(tectonic 的 search-path/biber/字体,officecli 的 save-before-read)
- 根原语:GOAL.md / PLAN.md / TODO.md / CHANGELOG.md / ROADMAP.md / INDEX.md

## Environment

- Python >= 3.12,uv 管包;依赖面:pydantic/jinja2/docxtpl/python-pptx/openpyxl/pyyaml
- 外部引擎:officecli / reader / tectonic(发现梯:env 覆盖 → PATH → D:\ohmyenv\)
- 环境变量表见 README.md(样例唯一权威 .env.example)
- Windows 主战场:stdio 强制 UTF-8(run.py 最先);ty 钉 python-platform=windows
