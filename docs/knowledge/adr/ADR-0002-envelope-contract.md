# ADR-0002:输出信封与错误通道契约

- 状态:accepted(2026-10-19,继承舰队惯例 + dev-cli 标准)
- 关联:ADR-0001;蓝本 D:\hvperv-harness;标准 dev-cli agent-face

## Context

harness 的机器面需要一个输出契约:agent 读完输出流就能判定成败与下一步。候选有宽松文本、重信封(成败都带完整结构)、单 --json 负载折叠。

## Decision

stdout 信封 `{ok, data | error, meta?}`(meta 仅 --full-output:command/duration_ms/cta);失败时 stdout 保纯,stderr 出单行 JSON `{code, message, retryable?, cta?}`;退出码 0/1/2(grep 语义:成功/业务未命中/用法与系统错误)。类型化 CTA 成败都带(成功在 meta.cta,失败在 stderr cta)。写命令干跑直到 --yes。裸调用 exit 0 两行导航面。旗标进、信封出(不折叠输入参数,Microsoft AX 实测教训)。

## Consequences

- agent 判定链固定:先退出码,再看 stdout 形,再取 cta 推进,不反问用户
- 人读面(toon)与机器面(--json)同一数据源,双面零分叉
- 信封形状是对外接口:字段序 = 插入序,改语义必须走 [deprecated] 过渡
- 干跑默认让批量操作先看计划再落盘,破坏性面收敛
