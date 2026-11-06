# AI 使用记录

工具：Codex；具体模型版本未记录。
日期：2026-11-06（本次会话日期）；原始日志文件名采用服务器时间。

## 输入上下文与问题

课程 E8 B 手册、个人测试示例、提交要求，以及学生执行参考流程后的终端输出。
请求核对报告、候选补丁、旧报告拒绝结果，仿写仅含 REDUNDANT 的测试，并整理实验文档与提交。

## 建议与采纳

采纳先在临时项目中补齐 config.h 声明并提交，再扫描得到仅含 REDUNDANT 的真实报告。
新增 StudentE8B.test_only_redundant_keeps_makefile_bytes，独立断言发现列表、空补丁、空计划和源字节不变。
新增测试、个人报告和 ADR 由 Codex 辅助起草并在服务器写入；参考流程输出由学生提供。

## 人工操作与贡献边界

学生执行并提供 E8 第 0—8 步输出，选择仅 REDUNDANT 的自主测试方向。
新增测试未记录额外的学生手工改写。文档需学生复核；姓名、校区和小组编号由学生提供。
检测与补丁实现来自课程实验包，本次未修改 lab.py。

## 实际验证

在 course-e8e10:231880393 容器中执行：

```bash
docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD:/course" -w /course course-e8e10:231880393 python3 -m unittest discover -s labs/e8e10 -p test_profile.py -v
```

结果：8 项测试通过，OK，退出码 0；日志为 work/unit-tests-20261106-173831.log。
E8 发现 MISSING main.o/config.h 与 REDUNDANT main.o/unused.h；候选只增加 config.h；旧报告以 STALE_REPORT 拒绝，源文件不变。
CI、PR 与归档状态另存 work/submission-e8-B/，以真实运行结果为准。
