# Changelog

本仓记版本级里程碑;条目间改动走 GOAL/TODO。格式参照 Keep a Changelog,semver。

## [0.1.0] - 2026-10-19

首批 M1-M5:
- M1 骨架:COMMANDS 注册表三面投影、信封契约(0-1-2 / stderr 单行)、引擎客户端(线协议看 stdout 形、超时表、发现梯、FakeEngine 测试缝)、三闸接线
- M2 tex 线:texenv(LaTeX 定界符 \VAR{}/\BLOCK{}、单遍 TeX 转义、NoEscape)、render/compile 命令、周报模板;端到端 json→tex→pdf→reader 读回闭环
- M3 docx 线:docxtpl 填充 + 干跑/--yes;docx 种子模板(officecli 造,标签段落独立)
- M4 pptx/xlsx 线:python-pptx 段级锚点替换(免疫 run 切分)、openpyxl 单元格锚点+列表行增长;幻灯复制页标记位留 M4 后续
- M5 治理:README/AGENTS/CLAUDE 桥接/.env.example/启动器 .cmd;read/inspect 命令补全命令面
- 37 测试,三闸全绿;doctor 三引擎+六库真机全绿
