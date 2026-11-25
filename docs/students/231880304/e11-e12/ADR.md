# ADR：集成接口决策

编号、日期、作者：E11-ADR-01 / 2026-11-16 / 231880304

问题：E11-B 需要在不修改课程参考实现的前提下，完成 direct 与 macro 两种声明风格的固定 MD → 补丁 → 验证。

候选方案：① 只复用共享样例做 direct；② 新建 macro 提交验证变量声明风格；③ 修改 lab.py 支持更多风格。

采用方案与原因：采用 ②。macro 提交把 main.o 依赖改为 `$(DEPS)`，源码与配方不变；固定 MD 由该提交真实 scan 生成，commit 绑定 target。不修改 lab.py，避免影响共享参考实现。

输入输出字段：请求 `mode=e11-b`、`repo/base/target/candidate/fixed_report`；报告 `schema_version=e11e12-1`、`kind=fixed-md`、`commit=target`、`data=scan`；补丁只改 `DEPS` 定义。

兼容性与测试：新增 2 项测试（macro 补丁位置、fixed-md commit 不符拒绝）；E11-B direct/macro 均 SUCCEEDED；两类 STALE_REPORT 均拒绝。

验证命令与实际证据：`python3 run_e11e12.py run --request ... --out work/e11-b-*`；见 `work/e11-b-01`、`work/e11-b-macro-02`、`work/e11-b-stale-outer-01`、`work/e11-b-stale-inner-01`。
