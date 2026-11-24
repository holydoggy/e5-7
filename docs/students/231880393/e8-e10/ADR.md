# 决策记录

**背景与约束：**

本次完成 E8—E10 B 组实验，重点是生成依赖修复补丁，并检查补丁是否真的解决了问题。固定 MD 报告必须对应当前样例的 commit，不能拿旧版本的结果直接修改新项目。候选只补缺失依赖，保留冗余依赖和编译配方。

检测和修复算法沿用课程的 labs/e8e10/lab.py，个人新增内容是 test_profile.py 中的三个测试。测试在临时项目中运行，原实验输出保留，方便前后比较。

**选择与替代方案：**

| 实验 | 采用的方案 | 替代方案与选择理由 |
|---|---|---|
| E8 | 先补齐 config.h，再扫描得到仅含 RD unused.h 的报告 | 也可以手工拼出报告，但从实际项目扫描，可以一起检查输入和扫描结果是否对应 |
| E9 | 在 direct、macro、mixed 中重复声明 main.c 和 unused.h | 也可以直接重复报告中的 findings，但那检查的是重复报告条目；本次要检查 Makefile 重复声明经过解析和补丁生成后的结果 |
| E10 | 只给 helper.o 增加 extra.h，让候选能构建，但仍漏修 main.o/config.h | 也可以用错误 C 代码触发编译失败；本次选择能构建的候选，是为了检查构建成功后是否仍能发现漏修 |

**B：共享变量怎样处理、失败怎样保证原目录不变。**

对于手册中的宏写法，macro 在 DEPS 定义中补依赖，目标行保留 $(DEPS)；mixed 保留 $(HEADERS)，在目标行补依赖。本次没有验证一个变量同时被多个目标引用的情况。如果改了共享变量，其他目标也可能受到影响，这部分需要增加用例后才能判断。

E8、E9 生成补丁时不写回原项目，git apply --check 也不修改源文件；E9 实际应用 macro.patch 时使用 apply-demo 副本。E10 在 sandbox 中验证，全部检查通过后才写回 Makefile。失败时比较源文件字节，确认没有留下候选修改；如果前面已经接受过一次修复，后面的拒绝就应保留那次修复后的内容。

**代价与覆盖范围：**

用真实临时项目做测试，需要 Git、GCC 和课程容器，步骤比直接构造 JSON 多一些，但能检查从扫描到补丁验证的过程。本次覆盖仅 RD、三种声明风格的重复依赖，以及能构建但漏修 MD 的拒绝场景。

E9 的去重只针对解析后的依赖集合，不清理 Makefile 里已有的重复文本。共享变量跨目标影响、复杂隐式规则和完整论文声明图不在本次覆盖范围内。

**验证命令与实际证据：**

```bash
docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD:/course" -w /course course-e8e10:231880393 python3 -m unittest discover -s labs/e8e10 -p test_profile.py -v
```

| 阶段 | 实际结果 | 日志 |
|---|---|---|
| E8 | 8 项通过；仅 RD 时 diff、plan 为空，Makefile 字节不变 | work/unit-tests-20261106-173831.log |
| E9 | 9 项通过；三个风格子场景均只补一次 config.h，配方和变量引用保留 | work/unit-tests-E9-20261106-190037.log |
| E10 | 10 项通过；漏修候选的构建和普通测试成功，但 header_change、no_missing 失败，候选被拒绝且源字节不变 | work/unit-tests-E10-20261106-195314.log |

以上测试退出码均为 0。E10 扩展证据保存在 work/e10-B-extension.VsonHU。原始三场景证据位于 work/e10-B-manual.BQU12z，正确候选的 BuildChecker 重检为 SUCCEEDED、无 MISSING；最后拒绝坏补丁后，比较 source-after-accept.Makefile 与 project/Makefile 的 cmp 退出码为 0。
