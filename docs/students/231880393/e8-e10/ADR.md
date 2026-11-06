# E8 B 组决策记录

## 背景与约束

固定 MD 报告必须与样例当前提交一致。E8 生成、检查候选补丁，原项目保留用于后续质量验证。
参考实现支持受限 C/Make 显式规则；本次贡献限定为新增单元测试。

## 选择与理由

选择先补齐 config.h 声明、提交临时项目、再扫描，生成真实的仅含 RD 的报告。
先独立断言唯一发现 REDUNDANT main.o/unused.h，再断言 diff、plan 为空与 Makefile 字节不变。
该预期符合当前补丁生成器只处理 MISSING 的边界。
保留原有 7 项测试，使用 TemporaryDirectory 隔离新增用例。

## 替代方案与代价

人工构造仅含 RD 的 findings 更简短，但无法同时核对真实 Makefile 与扫描结果。
未知目标拒绝也是可选用例；本次新增覆盖选择仅 RD 的空补丁行为。
真实临时项目需要 Git、GCC，因此测试在课程镜像内执行。

## 保护与覆盖范围

E8 保留 redundant 依赖和编译配方；候选生成、git apply --check 不写回原 Makefile。
过期报告以 STALE_REPORT 拒绝，源字节保持不变。
本次不扩展共享变量、混合声明或隐式规则支持，不修改 lab.py。

## 验证与证据

测试：StudentE8B.test_only_redundant_keeps_makefile_bytes。
unittest discover -s labs/e8e10 -p test_profile.py -v，共 8 项通过，退出码 0。
实际日志：work/unit-tests-20261106-173831.log。
参考路线证据：work/e8-B-manual.PkCOga/。
最终提交、PR 与 Actions 绑定记录：work/submission-e8-B/。
