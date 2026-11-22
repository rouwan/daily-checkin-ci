# 每日打卡架构练习

[![持续集成](https://github.com/rouwan/daily-checkin-ci/actions/workflows/ci.yml/badge.svg)](https://github.com/rouwan/daily-checkin-ci/actions/workflows/ci.yml)

一个用于练习软件架构与工程交付的单用户、单习惯每日打卡项目。

项目保持简单：每天只能完成一次打卡，也可以撤销当天打卡；页面展示今天状态和当前连续天数。前端、后端和数据库都位于同一个业务模块内。

## 技术栈

- 前端：Vue 3、TypeScript、Vite
- 后端：Python 3.12、uv、FastAPI
- 数据库：SQLite
- 自动化测试：pytest、FastAPI TestClient、Playwright
- 持续集成：GitHub Actions

## 本地运行

Windows 下可直接双击：

```text
业务模块\打卡模块\启动.bat
```

也可以从仓库根目录启动：

```powershell
cd "业务模块\打卡模块"
.\启动.bat -NoBrowser
```

默认地址：

- 页面：<http://127.0.0.1:5173>
- 后端健康检查：<http://127.0.0.1:8000/api/health>
- 接口文档：<http://127.0.0.1:8000/docs>

停止服务：

```powershell
cd "业务模块\打卡模块"
.\停止.bat
```

## 自动化测试

后端单元测试与接口测试：

```powershell
cd "业务模块\打卡模块\功能模块\后端"
uv sync --frozen
uv run pytest -q
```

前端类型检查与生产构建：

```powershell
cd "业务模块\打卡模块\功能模块\前端"
npm ci
npm run build
```

核心浏览器冒烟测试：

```powershell
cd "业务模块\打卡模块"
.\测试\冒烟\运行冒烟测试.ps1
```

## 目录

- `业务模块/打卡模块/功能模块/`：前端、后端和 SQLite 表结构。
- `业务模块/打卡模块/测试/`：单元、接口、冒烟和页面验收。
- `业务模块/打卡模块/文档/`：技术选型、测试边界、CI 和模块记忆。
- `文档/产品设计/`：当前产品边界。
- `.github/workflows/ci.yml`：持续集成工作流。

## 当前阶段

第一阶段已完成：单模块、单元测试、接口测试和冒烟测试。

第二阶段正在进行：建立公开 GitHub 仓库和 GitHub Actions CI。多模块和项目管理中台暂缓。

## 许可证

本项目使用 [MIT License](./LICENSE)。
