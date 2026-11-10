# AI使用记录（231880459 / B 轨道）

工具/模型/日期：DeepSeek Harness ，DeepSeek-V41， 2026-11-07 。

输入上下文与问题：上下文包括项目手册与服务器上证据（`work/e8-B-manual.DJYBbO`、`work/e9-B-manual.tZwp1m`、`work/e10-B-manual.uStr1V`）。问题：公共准备修复，E8/E9/E10 末尾自主任务要求解释，了解项目文件分工，起草报告。

模型建议：修复仓库问题；给出三个 `Student*` 测试类的骨架（重复依赖去重、可构建但仍存在 MD、只含 REDUNDANT）。

采纳/拒绝及理由：采纳 ③ 的骨架与断言结构。

人工修改：三个测试类的输入变化全部由我按自己样例改写，而不是直接使用示例：`StudentE8B` 用"过滤成只含 REDUNDANT 的报告"（示例 2B 是"保留配方字节"）；`StudentE9B` 把目标行改成 `main.c unused.h main.c unused.h` 制造重复声明；`StudentE10B` 手工用 `difflib` 造"只改 `helper.o`"的候选。

实际验证命令/输入/结果：

```bash
docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD:/course" -w /course course-e8e10:231880459 \
  python3 -m unittest discover -s labs/e8e10 -p test_profile.py -v
# Ran 10 tests in 1.328s / OK
```

E8/E9/E10 的三条 OUT 均为本人在服务器上按手册逐步执行产生（`steps/` 下 6 / 4 / 7 份日志，`STEP_EXIT_CODE=0`），AI 未代跑实验、未生成任何证据文件。

未调用模型时的边界：`labs/e8e10/lab.py` 未做任何修改（`git diff -- lab.py` 为空），被测实现与判定逻辑全部是课程参考代码；`work/` 下的 JSON、日志、补丁全部由容器内真实运行产生。AI 的贡献限于流程解释、测试骨架与报告措辞整理。
