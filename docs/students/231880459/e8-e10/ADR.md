# 决策记录（E8—E10 / B 轨道 MDfixer）

背景与约束：教学样例是受限 C/Make 工程（两个翻译单元 `main.o`/`helper.o`、项目内头文件、显式规则、简单变量与受限 `CFLAGS`）。硬约束有三条：① 报告必须来自本次真实输入，不能跨提交复用；② 补丁是候选，接受前不得改动被测源目录；③ 课堂环境禁网，所有工具来自已构建镜像 `course-e8e10:231880459`。

选择与替代方案：

- **报告身份绑定**：选择"`patch()` 入口校验 `report['commit'] == HEAD`，不等即 `STALE_REPORT`"。替代方案是"按依赖名匹配、忽略提交"——被否，因为同一依赖名在不同提交下含义可能不同（如声明早已修复），会生成错误补丁。
- **只补 MISSING、不删 REDUNDANT**：选择"仅对 `type=='MISSING'` 生成编辑"。替代方案"同时清理 RD"——被否，删除会改动配方上下文与共享变量，扩大影响面，且教学样例中 `unused.h` 的存在本身是被观察对象。
- **声明风格三分支**：选择"目标行只写 `$(VAR)` 时改变量定义、其余情况改目标行并据是否含宏区分 mixed"。替代方案"一律直接改目标行"——被否，会让 macro 风格样例失真（目标是让三种结构各自展示正确落点）。
- **接受策略（B 的核心）**：选择"复制 sandbox + 五项检查 `patch_applies/build/test/header_change/no_missing` 全通过才写回源目录"。替代方案"构建成功即写回"——被否，E10 自主任务已给出反例：候选可应用、可构建、`./app` 输出也正确，但 `main.o` 仍缺 `config.h` 声明，改头文件后不重编（`header_change=False`），必须拒绝。
- **失败回滚**：选择"源目录在整个验证过程中完全不动，sandbox 与日志保留作证据"，因此"回滚"退化为"根本没写过"，`source_unchanged` 与 `rollback` 可直接由字节比较证明。替代方案"先写回、失败再回滚"——被否，进程中断时会留下半成品。
- **共享变量**：选择"不自动处理，明确记为扩展范围"。代价：纯 macro 风格下修改变量会波及所有引用该变量的目标（E9 结论已记录），需要声明图/DIS 或按目标重写才能安全。

代价与覆盖范围：不支持隐式规则、`%` 模式规则、顺序依赖 `|`（直接 `UNSUPPORTED_DECLARATION`），不支持 `-O1`/`-DMODE=1` 之外的 `CFLAGS`（`UNSUPPORTED_FLAGS`），只覆盖项目内头文件与两个目标；论文规模与性能数值不适用于本样例。

验证命令与实际证据：

```bash
# 定向测试（原 7 项 + 本人 3 项）
docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD:/course" -w /course course-e8e10:231880459 \
  python3 -m unittest discover -s labs/e8e10 -p test_profile.py -v
# 实测：Ran 10 tests in 1.328s / OK（work/unit-tests-20261107-215729.log）
```

- E8：`work/e8-B-manual.DJYBbO`（6 steps；`STALE_REPORT` + `SOURCE_BYTES_UNCHANGED`；项目 `git status` 空）
- E9：`work/e9-B-manual.tZwp1m`（4 steps；三份 diff 落点分别 direct/macro/mixed；`APPLY_TO_COPY_PASS`）
- E10：`work/e10-B-manual.uStr1V`（7 steps；`B_GATE_PASS`、`gate.json` rows=3、`recheck-buildchecker/findings.json` 中 `status=SUCCEEDED` 且 `MISSING=0`、`cmp source-after-accept.Makefile project/Makefile` 返回 0）
