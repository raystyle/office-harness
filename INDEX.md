# INDEX:代码地图与文档导航

## 代码地图

| 文件 | 职责 |
|---|---|
| src/office_harness/cli.py | COMMANDS 注册表,唯一外向真源;三面(帮助/手册/schema)投影 |
| src/office_harness/run.py | 薄分发器;stdio UTF-8 硬化;错误映射 |
| src/office_harness/envelope.py | 信封:全局旗标扫描、stdout JSON、stderr 单行、filter 路径 |
| src/office_harness/texenv.py | jinja LaTeX 环境:定界符、单遍转义、NoEscape |
| src/office_harness/engine/base.py | 引擎底座:_execute 测试缝、线协议、超时表、发现梯 |
| src/office_harness/engine/officecli.py | officecli 客户端:版本探针 + get/query/view |
| src/office_harness/engine/reader.py | reader 客户端:版本探针 + extract/search |
| src/office_harness/engine/tectonic.py | tectonic 客户端:compile + 坑位(search-path/字体) |
| src/office_harness/fills/docx_fill.py | docxtpl 填充 |
| src/office_harness/fills/pptx_fill.py | python-pptx 段级锚点替换 |
| src/office_harness/fills/xlsx_fill.py | openpyxl 单元格锚点 + 列表行增长 |
| src/office_harness/cmds/*.py | 命令层:render/compile/fill/read/inspect/doctor |
| tests/unit/conftest.py | FakeEngine 缝:回放罐头信封,不触真引擎 |
| templates/tex/report.tex.j2 | 周报 tex 模板种子 |
| templates/docx/report.docx | docxtpl 模板种子 |
| templates/pptx/deck.pptx | 锚点幻灯模板种子 |

## 文档导航

- README.md 人读总览;AGENTS.md 协作契约唯一权威;CHANGELOG.md 版本里程碑
- GOAL.md 当前目标与验收;PLAN.md 技术栈与里程碑;TODO.md 待办;ROADMAP.md 展望
- docs/sources 一手记录;docs/knowledge 结论层(adr/req/references);docs/operations 操作手册
