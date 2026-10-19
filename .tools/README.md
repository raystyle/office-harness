# .tools:维护脚本归档目录

清单表是登记面,新脚本必须登记(doclint 守卫);临时脚本二次使用即归档,一次性用完即删。

| 脚本 | 用途 | 调用方 |
|---|---|---|
| hooks/pre-commit | 三闸提交挡板(ruff/ty/pytest),三态退出码 | git(core.hooksPath .tools/hooks) |
| release.ps1 | 发布三段式:预检/构建/验证分发+sha256 边车 | 手动(发版时) |
| probe_recalc.py | recalc 探针:officecli set 刷公式缓存实证 | 手动(复验时) |

