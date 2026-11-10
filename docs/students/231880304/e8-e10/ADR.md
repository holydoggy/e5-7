# 决策记录

背景与约束：E8 B 轨需要从固定 MD 报告生成候选补丁；样例使用 direct 声明风格，只有一个 MISSING（main.o→config.h），另一个是 REDUNDANT（unused.h）。

选择与替代方案：选择 direct 方式，直接在 main.o 依赖行追加 config.h；不删除 unused.h（RD 不处理）。macro/mixed 风格需要改写变量定义或声明行，超出 E8 的最小修复范围。

代价与覆盖范围：补丁只覆盖单个目标/单个缺失依赖；共享变量与多目标场景留给 E9。失败处理：报告 commit 与当前 HEAD 不一致时抛 STALE_REPORT，不改写源文件。

验证命令与实际证据：work/e8-B-manual.4eM2hi/{fixed-md-report.json, candidate.patch, patch-plan.json, expected-failure.json}；单元测试 Ran 8 tests OK。
