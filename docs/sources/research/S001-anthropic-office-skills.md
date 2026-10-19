# S001:Anthropic 官方 office skills 四族对拍研究

- 信源:github.com/anthropics/skills clone @ dbd4588(2026-10-09 版),D:\tmp\anthropic-skills
- 快照:2026-10-19,office-harness v0.1.0 期(提交 55101be 前)
- 关联:ADR-0001(模板引擎姿态);办公四族 fills 层

## 结论,六态已验证

1. 【已验证】四 skill 共享 vendored scripts/office/ 子包(docx/pptx/xlsx 三份字节等价,diff -rq 核),含 XSD 语料库(ECMA OPC + ISO 29500 + MS 扩展)与 soffice 包装;**专有许可,可学模式不可拷代码**(LICENSE.txt)。
2. 【已验证】方法论:创建=模型写脚本(docx-js/pptxgenjs/reportlab/openpyxl),编辑=OOXML 解包手术,读=pandoc/markitdown/pdfplumber;无 jinja/数据驱动模板概念。
3. 【已验证】验证环:docx/pptx 强制视觉验证(soffice→pdf→pdftoppm→逐页看);xlsx 用 recalc.py(LibreOffice 宏重算+七种错误 token 计数+外链拒绝守卫)替代 XSD;pptx 有 --original 基线验证(模板自带缺陷不算新错)。
4. 【已验证】spill 函数(XLOOKUP/XMATCH/SORT/FILTER/UNIQUE/SEQUENCE)在 openpyxl 文件无溢出元数据:只有左上格有值,recalc 对截断结果报零错;小写公式=解析失败征兆(SKILL.md:61-69)。
5. 【已验证】run 切分是四族共同天敌:docx 有 merge_runs.py 前处理;pptx skill 明确警告 python-pptx 三缺口(无复制页/text 赋值塌格式/add_picture 不吃 SVG),我们的段级锚点+整段重写正是免疫道。
6. 【已验证】未解析占位符残留是已知缺陷类:pptx skill QA 有 markitdown+grep 占位符步;原 fills 设计让未解析锚保持字面=静默发货,已修(报告 unresolved 字段)。

## 已采纳

- unresolved 锚点报告(pptx+xlsx),提交 55101be
- xlsx 公式兼容 lint(spill 截断+小写 tell),同上

## 候选采纳,按价值排

1. recalc.py 设计整体(xlsx 最高价值:openpyxl 填完的表缓存值全 None),需 LibreOffice,引擎位接入
2. --original 基线验证原则(验证产出对模板基线而非绝对)
3. 视觉验证环 verify 命令(officecli view html 可担渲染位)
4. safe_extract/rezip(未来做 XML 手术时的安全解包/原子回包)
5. 生成器特异坏损 lint 思路(不验通用 schema,专逮自家生成器的已知坏形)

## 分工定位

skill=摄取道(驯服任意脏文件,模型在环有眼);harness=生产道(已知模板声明式填充,无头可 CI)。harness 产出、skill 方法论验收,叠加不互竞。

## 参考

- D:\tmp\anthropic-skills\skills\{docx,pdf,pptx,xlsx}\SKILL.md 及 scripts/
- xlsx recalc.py:81-161(外链守卫)、172-212(no-op 检测)
- pptx validators\pptx.py:123-185(--original 基线)
- docx merge_runs.py:1-24(run 切分论述)


