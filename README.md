# office-harness

文档生产线 CLI harness:四族模板(tex/docx/pptx/xlsx)× jinja 渲染 × 业界主流填充库,编排三件本机引擎(officecli/reader/tectonic)做编译、读回验真与检视回看。

## 特性

- `render`:`.tex.j2` 模板 + json/yaml 数据 → `.tex`(LaTeX 安全定界符 `\VAR{}`/`\BLOCK{}`,数据值自动 TeX 转义)
- `compile`:`.tex` → PDF(tectonic 引擎客户端,超时表/发现梯/坑位内置)
- `fill`:docx/pptx/xlsx 模板 + 数据 → 成品(docxtpl / python-pptx / openpyxl 分派;写默认干跑,`--yes` 落盘)
- `read`:文档提取/搜索(reader 引擎;搜索未命中 = 业务 exit 1)
- `inspect`:office 文档 get/query/view html(officecli 引擎;渲染回看)
- `doctor`:三引擎 + 六库自检

## 部署

```powershell
git clone <repo> D:\office-harness
cd D:\office-harness
uv sync
.\office-harness.cmd --llms    # 验装:agent 手册
.\office-harness.cmd doctor    # 引擎/库体检
```

前置:officecli / reader / tectonic 三引擎在 PATH 或 `D:\ohmyenv\`(发现梯:环境变量覆盖 → PATH → ohmyenv glob)。

## 环境变量

| 变量 | 作用 | 缺省 |
|---|---|---|
| `OFFICE_HARNESS_TIMEOUT` | 覆盖所有引擎 op 超时(秒) | 按类:read 30 / write 120 / compile 600 |
| `OFFICECLI_BIN` | officecli 二进制覆盖 | 发现梯 |
| `READER_BIN` | reader 二进制覆盖 | 发现梯 |
| `TECTONIC_BIN` | tectonic 二进制覆盖 | 发现梯 |

## 使用

agent 面:`office-harness --llms`(紧凑手册,≤120 行,命令树渲染零手维护)。

```powershell
office-harness render templates\tex\report.tex.j2 --data examples\data\week1.json
office-harness compile examples\out\week1.tex
office-harness fill templates\docx\report.docx --data week.json --yes
office-harness read report.pdf --mode search --term 结论
office-harness inspect deck.pptx --what view
```

## 架构

```
src/office_harness/
  cli.py          # COMMANDS 注册表:唯一外向真源(--help/--llms/--schema 三面投影)
  run.py          # 薄分发器(先出面后命令)
  envelope.py     # 信封:stdout {ok,data} / stderr 单行 {code,message} / 0-1-2
  texenv.py       # jinja LaTeX 环境:定界符 + tex 转义 + NoEscape
  engine/         # 引擎客户端:base(缝/协议/超时/发现)+ officecli/reader/tectonic
  fills/          # 库填充层:docxtpl / python-pptx / openpyxl
  cmds/           # 命令层(薄):render/compile/fill/read/inspect/doctor
templates/        # 四族模板画廊(随包分发)
tests/unit/       # pytest + FakeEngine 缝(不触真引擎)
```

## 开发

三闸红即禁提交:

```powershell
uv run ruff check .
uv run ty check src
uv run pytest
```

协作契约唯一权威是 [AGENTS.md](AGENTS.md)。文档治理与变更纪律见 AGENTS.md 的 Read first 节。
