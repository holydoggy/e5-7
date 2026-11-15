# ADR：集成接口决策

编号、日期、作者：E11-B-231880393-01；2026-11-15；肖天纵（231880393）。

问题：共享基线使用 direct 声明，需要补充 macro 风格，并确认外层报告和内部扫描数据属于同一个目标提交。版本错误时必须停在修复前，不能写坏源文件。

候选方案：可以扩展 macro 或 mixed；也可以只调用 patch 检查输出，或运行完整 DRAFT→固定报告→修复→复验。旧报告可分别修改外层 commit 或 data.commit。

采用方案与原因：选择 macro，在原共享目标提交上新增只改变依赖声明的提交，便于比较。完整运行一次正常场景和两个旧报告场景，确认真实镜像构建、程序输出和补丁验证。测试同时覆盖两层 commit，避免只检查封装字段、漏掉内部版本。保留 main.o: $(DEPS)、unused.h 和编译配方，只在 DEPS 中补 config.h、extra.h。

输入输出字段：固定报告的 schema_version=e11e12-1、kind=fixed-md、status=SUCCEEDED；commit 和 data.commit 均需等于 request.target。四份阶段封装报告沿用同一 job_id/trace_id，产物以 artifact URI 和 SHA256 关联。正常情况 accepted=true、复验无 MISSING；任一版本过期返回 STALE_REPORT，不进入 patch、validate。DRAFT 在版本检查前运行，不能把该负例描述为完全没有发生构建。

兼容性与测试：未修改 pipeline.py、lab.py 或 DRAFT 实现。独立运行验证正常 macro 成功、两类旧报告拒绝及源字节保持；新增三项测试，13 项全部通过。单元测试将 DRAFT 替换为成功测试桩，实际 Docker 构建由独立运行验证。日志、原始图和报告保存在 work/e11-b-231880393-20261115/。覆盖范围是单目标 DEPS 宏，不包含一个共享变量同时影响多个目标的情况；真实项目和 E12 联调留待后续。
