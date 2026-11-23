# 双视角代码审查 agent

> 状态：第三阶段建议型试验
> 最后更新：2026-11-22

## 目标

在每个 Pull Request 中增加两个相互独立的 Codex 审查视角：

- `正确性`：检查业务规则、接口契约、数据关系和测试缺口。
- `工作必要性`：检查阶段越界、过度设计和不必要的依赖或抽象。

两个视角都只提出建议，不修改代码。现有单元测试、接口测试、前端构建和核心冒烟测试仍是硬门禁。

## 工作流

```text
PR 打开或更新
  ├─ 正确性 agent ────┐
  └─ 工作必要性 agent ─┤
                       └─ 汇总并更新一条 PR 评论
```

工作流文件为 `.github/workflows/code-review.yml`，与现有的
`.github/workflows/ci.yml` 分离。

## 模型与端点

- Action：`openai/codex-action`
- Action 版本：固定到 `v1.14` 对应的完整提交
- Codex CLI：`0.171.0`
- 模型：`deepseek-flash`
- Responses 端点：`https://api.deepseek.com/responses`
- 推理强度：`high`

Action 的输入名称为 `openai-api-key`，但本工作流通过覆盖
`responses-api-endpoint` 将它作为 DeepSeek 端点的 Bearer Key 使用。

## GitHub Secret

仓库必须配置：

```text
DEEPSEEK_API_KEY
```

Secret 只保存在 GitHub Actions 中，不进入仓库、Prompt、日志或 PR 评论。

## 触发与隔离

- 只在面向 `main` 的 Pull Request 中运行。
- 草稿 PR 不运行；转为可审查状态后运行。
- 第一版只接受同仓库可信分支，不处理外部 fork PR。
- 同一 PR 的新提交会取消旧运行。
- 两个 agent 使用独立 runner、独立 Prompt 和独立输出。
- Codex job 只有仓库读取权限，并使用 `read-only` sandbox 与 `drop-sudo`。
- 只有独立的汇总 job 拥有 PR 评论写权限。

## 结构化输出

两个 agent 必须输出符合
`.github/codex/schema/review-output.json` 的 JSON：

- `perspective`
- `summary`
- `findings`
- `limitations`

Action 负责按 Schema 约束字段、类型、优先级和数量；汇总脚本只检查 JSON 可解析、视角匹配及渲染所需的基本结构，然后生成一条带固定标记的中文评论。同一 PR 的后续提交会更新原评论，不重复刷评论。

## 失败规则

- agent 发现业务问题时，汇总评论仍然成功，方便人工判断。
- agent 执行失败、输出为空、JSON 无效或视角错误时，汇总检查失败。
- 汇总失败前仍会尝试发布错误评论，避免技术问题被静默忽略。

第一版不把 `审查汇总` 设置为分支必需检查。

## 本地验证

汇总器和测试不依赖第三方 Python 包：

```powershell
python -m unittest discover -s .github/codex/scripts -p "test_*.py"
```

验证 DeepSeek 端点时只显示 HTTP 状态，不输出 API Key：

```powershell
$token = ([System.IO.File]::ReadAllText("<你的密钥文件>")).Trim()
curl.exe -s -o NUL -w "HTTP=%{http_code}`n" `
  -H "Authorization: Bearer $token" `
  https://api.deepseek.com/models
```

## 成本与数据边界

- 两个独立 agent 会分别消耗 DeepSeek API token。
- PR 的代码差异和必要的仓库上下文会发送到 DeepSeek。
- 不向 agent 提供 API Key、正式数据库或其他本地 Secret。
- 该能力是建议型 AI 审查，不替代第六阶段的正式人工审查和必需批准。

## 已知限制

- 外部 fork PR 暂不执行审查。
- 当前发布统一评论，不创建 GitHub 行级 Review。
- 模型质量和延迟取决于 DeepSeek Responses API。
- 审查结果可能出现漏报、误报或重复关注点，需要根据真实 PR 持续调整 Prompt。
