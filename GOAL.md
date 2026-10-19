# GOAL:office-harness 当前目标与验收

## 目标

文档生产线一条命令:四族模板(tex/docx/pptx/xlsx)数据到成品,三引擎(officecli/reader/tectonic)编排,agent 友好面齐备。

## 验收判据

- [x] 三闸全绿(ruff/ty/pytest),漂移守卫锁四向一致
- [x] `--llms` 手册 <=120 行且从注册表渲染;裸调用 exit 0
- [x] tex 线端到端:json 数据 → render → compile → PDF → reader 读回对拍
- [x] docx 线:docxtpl 填充 + 干跑/--yes;成品 officecli 可检视
- [x] pptx/xlsx 线:锚点替换与列表行增长
- [x] doctor 三引擎+六库真机全绿
- [ ] 幻灯按数据复制页(python-pptx 无公开复制 API,后续带测试落地)
- [ ] reader query 面(mq 表达式)接入 read --mode query

## 时间线

- 2026-10-19:立项(本目录由 office-master 更名);M1-M5 首批落地
- 下一步:M4 复制页、query 面、docs 三层补 ADR-0001(全库增强决策)
