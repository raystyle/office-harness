# PLAN:技术栈与里程碑

## 技术栈

| 层 | 选型 | 备注 |
|---|---|---|
| 语言/包管 | Python 3.12 + uv | 新仓下限 3.12 |
| 契约 | pydantic 2(strict 入站) | 写命令参数校验 |
| 模板 | jinja2 3 | tex 线(LaTeX 定界符) |
| docx 填充 | docxtpl | 业界事实主流 |
| pptx 填充 | python-pptx | 段级锚点,免疫 run 切分 |
| xlsx 填充 | openpyxl | 单元格锚点 + 行增长 |
| 引擎 | officecli/reader/tectonic | 外部二进制,客户端模式 |
| 门禁 | ruff + ty + pytest | 三闸红禁提交 |

## 里程碑

- M1 骨架(2026-10-19 毕):注册表/信封/引擎底座/三闸/FakeEngine
- M2 tex 线(毕):texenv/render/compile/模板/端到端读回
- M3 docx 线(毕):docxtpl fill/干跑/种子模板
- M4 pptx+xlsx 线(基本毕):锚点与行增长;复制页与 query 面续
- M5 治理(毕):五文档面/启动器/CHANGELOG;docs 三层与 pre-commit 续
