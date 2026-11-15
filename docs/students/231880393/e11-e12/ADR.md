# ADR：集成接口决策

编号、日期、作者：E11-B-231880393-01；2026-11-15；肖天纵（231880393）。

问题：共享基线使用 direct 声明，需要补充 macro 风格，并确认外层报告和内部扫描数据属于同一个目标提交。版本错误时必须停在修复前，不能写坏源文件。

候选方案：可以扩展 macro 或 mixed；也可以只调用 patch 检查输出，或运行完整 DRAFT→固定报告→修复→复验。旧报告可分别修改外层 commit 或 data.commit。

采用方案与原因：选择 macro，在原共享目标提交上新增只改变依赖声明的提交，便于比较。完整运行一次正常场景和两个旧报告场景，确认真实镜像构建、程序输出和补丁验证。测试同时覆盖两层 commit，避免只检查封装字段、漏掉内部版本。保留 main.o: $(DEPS)、unused.h 和编译配方，只在 DEPS 中补 config.h、extra.h。

输入输出字段：固定报告的 schema_version=e11e12-1、kind=fixed-md、status=SUCCEEDED；commit 和 data.commit 均需等于 request.target。四份阶段封装报告沿用同一 job_id/trace_id，产物以 artifact URI 和 SHA256 关联。正常情况 accepted=true、复验无 MISSING；任一版本过期返回 STALE_REPORT，不进入 patch、validate。DRAFT 在版本检查前运行，不能把该负例描述为完全没有发生构建。

兼容性与测试：未修改 pipeline.py、lab.py 或 DRAFT 实现。独立运行验证正常 macro 成功、两类旧报告拒绝及源字节保持；新增三项测试，13 项全部通过。单元测试将 DRAFT 替换为成功测试桩，实际 Docker 构建由独立运行验证。日志、原始图和报告保存在 work/e11-b-231880393-20261115/。覆盖范围是单目标 DEPS 宏，不包含一个共享变量同时影响多个目标的情况；E11 阶段未覆盖 E12；E12 验证现见下节，真实项目仍待提供来源。

本次阶段交付补充：接口契约.md 记录当前已验证的文件接口及报告产物哈希，课程 REST 定义与尚未进行的 API 实测分别说明。数据与联调记录.csv 沿用本次模板的十个字段，记录正常、负例和共享来源；E12 与真实项目仍标为未完成。这次修订不改变实验代码和接口行为。

## E12：报告消费与任务恢复

编号、日期、作者：E12-231880393-02；2026-11-15；肖天纵（231880393）。

问题：实际消费者未传期望 kind，错误类型的报告进入后续处理后才报 EXECUTION_FAILED；同时要确认任务 API 的幂等映射、下载哈希、失败重试和重启行为在真实服务中成立。

候选方案：只测试 check_envelope 辅助函数，或在 pipeline.execute 的实际消费点增加类型要求。重试可以复用旧键或换新键；本服务将同键绑定同一个任务，不用旧键创建第二个任务。

采用方案与原因：在真实消费点按 mode 选择 fixed-md 或 incremental-check，先校验再调用 patch，仅增加两行类型选择/传参。先用负例复现旧行为，再运行回归。CLI 和 API 均使用真实 Docker 构建；重启负例仅对本人 API 容器操作，并以单独 sleep 候选保持 RUNNING/QUEUED，不改原始项目或他人服务。旧键返回原失败任务，新键才重试。

输入输出字段：五阶段 envelope 使用同一 job_id/trace_id；full-check.commit 属于 base，其他阶段属于 target。repair.input_report 必须引用本轮 incremental-check 的 URI 和哈希。API request_hash 为排序序列化 input 的 SHA256；下载校验同时比较清单、响应头与实际字节。重启前尚未返回 trace_id 的任务保留空值，已完成任务的标识和结果保留。

兼容性与测试：HTTP 路由、合法请求字段和持久状态格式不变，lab.py 与 server.py 未改动。新增三项测试覆盖类型拒绝和两种重启/重试行为，共 16 项单元测试通过；E12 手册 14 项检查通过，Windows 到 Linux 的 SSH 转发与五份产物下载哈希一致。详细证据在 work/e12-231880393-20261115/。本次使用教学样例，真实项目未提供；分机验证不等同于另一位 A 同学实际参与。
