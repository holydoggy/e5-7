# 缺陷 Issue 与修复 PR 记录

## 本轮结论

B01 在 E13 B 侧执行（A01 项目 C1/C2/C3/C5，固定样例 C4/C7，假 Key C6，幂等 C8，H1–H3）未发现需要开 Issue 的阻断缺陷。

C2 `STALE_REPORT`、C3 `ARTIFACT_HASH_MISMATCH`、C4 `TIMED_OUT`、C5 `REPAIR_REJECTED`（回滚）、C6 假 Key 阻断、C7 失败隔离、C8 409 均为预期拒绝/隔离行为，不是产品缺陷。

C5 第一次构造（`work/e13-c5-01/`）引用了不存在的 `bogus.h`，被 `patch()` 以 `MISSING_INPUT` 拒绝；这是测试构造错误，已改用“漏掉 config.h 的错误补丁”（`work/e13-c5b-01/`）完成 C5，不记为缺陷。

CI 环境问题：`four-services` 前两次失败，原因是容器 root 读取 Actions runner 拥有的仓库，git 报 `detected dubious ownership`。在四个 Compose 服务中加入 `GIT_CONFIG_COUNT/KEY/VALUE` 的 `safe.directory` 配置后，run `44991221259` 通过；属于 CI 适配修复，不记为产品缺陷。

## 待 A 侧补充

- A01 对 B01 项目的反向 C1–C8；若发现阻断缺陷，按模板补 Issue 编号、失败阶段、日志路径、修复 PR 与回归证据。
- E13 门禁合并前，阻断 Issue 必须为 0；非阻断问题进入候选发布说明的“已知问题”。

## 模板（A 侧发现缺陷时填写）

- 用例编号与发现方：
- 输入仓库及完整 SHA：
- 预期 / 实际：
- 失败阶段、错误码和原始日志路径：
- 严重度（阻断 / 非阻断）与理由：
- 最小复现步骤：
- 是否影响其他任务或原仓库：
