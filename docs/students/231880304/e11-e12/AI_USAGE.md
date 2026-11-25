# AI使用记录

工具/模型/日期：Claude Code（对话助手）/ 2026-11-16

输入上下文与问题：E11-B 自主任务（macro 风格扩展）、旧报告 STALE_REPORT 拒绝用例、E11 个人测试与报告整理。

模型建议：新建 macro 提交并生成固定 MD；构造外层/内层 commit 不符的旧报告；新增 macro 补丁与 envelope 拒绝测试；整理报告与联调记录。

采纳/拒绝及理由：采纳；不修改课程 `pipeline.py` / `lab.py`，保持共享参考实现不变。

人工修改：本人执行命令、核对结果并填写报告；候选 apt 源按本机网络改为 `mirror.nju.edu.cn`，仅作用于本地 `data/`。

实际验证命令/输入/结果：`run_e11e12.py run/test`；E11-B direct/macro SUCCEEDED，STALE_REPORT 两次拒绝，12 tests OK。

参考实现与贡献边界：参考代码来自课程 E11–E12 实验包；本人贡献为 macro 样例、两项测试、报告与联调记录。

（如另使用其他模型/工具，请补充。）
