# ADR-0001:模板引擎姿态取全库增强

- 状态:accepted(2026-10-19,用户拍板)
- 关联:REQ 待登记;先例调查见 docs/sources/research/

## Context

四族模板(tex/docx/pptx/xlsx)需要定填充引擎姿态。三个候选:纯命令集成(全走 officecli merge/batch/import)、全库增强(docxtpl/python-pptx/openpyxl)、混合。grok 先例调查(2026-10-19,信源在 research 档):docxtpl 是 jinja-in-docx 事实主流;jinja-in-pptx 库全数死于 PowerPoint run 切分;xlsx 主流是锚点填值;Microsoft 实测输入折叠成单 --json 负载会掉模型成功率。

## Decision

全库增强:docx 走 docxtpl,pptx 走 python-pptx 段级锚点替换(整段重写,免疫 run 切分),xlsx 走 openpyxl 单元格锚点。officecli/reader/tectonic 退居外部引擎位:编译、读回验真、渲染回看。CLI 面旗标进、信封出。

## Consequences

- 依赖面加 docxtpl/python-pptx/openpyxl(可接受,纯 Python 轮子)
- docx 模板获得完整 jinja 能力(段/行/富文本循环),纯命令集成的平键替换做不到
- pptx 放弃形状内完整 jinja,换段级锚点 + 复制页标记(复制页 TODO 在册)
- officecli 本体升级(如 1.0.162)不影响填充语义,只影响检视面
- 引擎位与库位职责清晰:harness 不重造轮子,编排不越权
