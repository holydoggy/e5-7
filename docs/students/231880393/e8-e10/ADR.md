# E8—E10 B 组决策记录

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

## E9 重复依赖验证

选择重复依赖去重测试，覆盖 direct、macro、mixed 三种声明风格。
在临时样例的显式依赖或变量定义中重复 main.c、unused.h，提交后由 scan 生成真实报告。
独立断言声明集合去重、MD/RD 集合准确、补丁计划只有一项，以及应用后 config.h 只出现一次。
同时保留候选生成时源字节不变、编译配方保持、变量引用保持与修复后重扫的断言。

该用例检查重复文本经过解析后的依赖集合与补丁输出，不重写源文件中的既有重复项。
人工直接修改报告 findings 可以测试重复报告条目，但不属于本次选定的输入场景。
共享变量跨目标影响、复杂隐式规则及完整论文声明图仍作为后续扩展。

核心实现无需修改，保留 E8 测试与原始 E9 证据。
验证日志 work/unit-tests-E9-20261106-190037.log，9 项测试通过，新增一项覆盖三个风格子场景。
E9 手工证据位于 work/e9-B-manual.6vFx4V；正式提交与 CI 记录位于 work/submission-e9-B。

## E10 质量判定补充

选择“可构建但仍存在 MD”的候选，补充参考流程已有的错误测试拒绝与无效补丁拒绝。
候选只修改 helper.o 的依赖，给它增加已有的 extra.h，保持 main.o 缺少 config.h。
先断言候选可应用、构建和普通测试成功，再独立断言 header_change、no_missing 为 False，以及候选拒绝和源字节保持。
重检同时核对原有 MD、RD 与新增的 helper.o/extra.h 冗余依赖。

该用例区分命令异常与质量检查不通过：error=None 仍可能 accepted=False。
验证函数在独立 sandbox 中修改 config.h，源项目仅在全部检查通过时接收 Makefile。
原始 E10 源目录保留成功接受后的 Makefile；后续坏补丁拒绝必须维持该字节副本。

可替代方案是非法 C 源码导致编译失败。本次选择能构建的候选，覆盖构建成功后的质量检查。
核心实现未改动，新增测试使用临时目录；另创建 work/e10-B-extension.VsonHU 保留独立 checks/error 和前后字节证据。

本次 10 项单元测试通过，日志 work/unit-tests-E10-20261106-195314.log。
原始 E10 三场景均通过，BuildChecker 状态 SUCCEEDED 且无 MISSING。
输入与结果在 work/e10-B-manual.BQU12z，正式提交绑定记录在 work/submission-e10-B。
