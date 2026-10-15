<!-- AI-GEN-BEGIN -->
# CapCut Mate 技术分析

面向新工程师的仓库导读。结论以当前 `main` 分支代码为准；README 与代码不一致处已单独标出。

分析对象：

- 本仓库：https://github.com/halfC/capcut-mate（`main`，提交 `4357bfb`）
- 上游：https://github.com/Hommy-master/capcut-mate（GitHub 元数据标明本仓库是其 fork）

截至 2026-08-13，本仓库 `main` 与上游 `main` 的最新提交 SHA 相同。文档、克隆地址、Docker 镜像名仍大量指向上游与作者自有域名，而不是 `halfC`。

---

## 1. 项目是什么、给谁用

CapCut Mate 是一套**剪映（Jianying Pro）草稿自动化服务**，不是官方 CapCut / 剪映 SDK。

它解决的问题：大模型、Coze、n8n 等工作流无法直接操作剪映桌面端。本项目提供 HTTP API，在服务端生成剪映可打开的草稿目录（`draft_content.json` / `draft_info.json` + 素材文件），再由桌面客户端把草稿下载进本机剪映工程目录；可选地在 Windows 上用 UI Automation 驱动剪映导出成片。

目标用户：

- 需要把「文案 / 素材 URL → 剪映草稿 / 成片」接到 LLM 或自动化平台的开发者
- 自建剪映草稿服务、或使用作者托管站点 `jcaigc.cn` / `capcut-mate.jcaigc.cn` 的使用者
- 用 Electron「剪映小助手」把草稿 URL 一键导入本机剪映的剪辑师

与 CapCut / 剪映的关系：

- **不是** ByteDance 官方产品，也**没有**调用官方 CapCut Open API
- 核心能力是**离线构造剪映草稿 JSON**（vendored 的 `src/pyJianYingDraft`，源自 Gary Guan 的 pyJianYingDraft）
- 特效 / 动画 / 字体元数据带有剪映内部 `resource_id`、`effect_id`、md5，属于对客户端资源表的逆向摘录
- 「云渲染」= 本机已安装的剪映专业版 + Windows UI Automation 点击导出，不是 CapCut 云端渲染 API
- 命名上 CapCut 与剪映混用：README 英文写 CapCut，业务注释、路径、桌面端文案几乎全是「剪映」

README 声称「提供开箱即用的视频剪辑 Skills」。仓库内**没有** `skills/` 目录或 Skill 清单；更接近「一组适合被 Coze / LLM 调用的 REST 工具接口」。

---

## 2. 技术栈与仓库布局

### 2.1 后端（主产品）

| 项 | 实际来源 | 备注 |
| --- | --- | --- |
| 语言 / 运行时 | Python `>=3.11`（`pyproject.toml`） | Docker 镜像用 `python:3.11-slim` |
| Web | FastAPI + Uvicorn | 入口 `main.py`，默认 `0.0.0.0:30000` |
| 校验 | Pydantic v2（schema 里 `field_validator`） | |
| 包管理 | uv + `uv.lock` | |
| 媒体 | `pymediainfo`、`imageio`、仓库内 `tools/ffprobe` | 时长 / 尺寸探测 |
| HTTP 客户端 | `requests` | 下载素材、积分 API |
| 对象存储 | `cos-python-sdk-v5`、`oss2` | 成片上传，COS 优先、OSS 兜底 |
| Windows 可选 | `pywin32`、`pyautogui`、`uiautomation` | 仅 `.[windows]`，用于剪映 RPA |
| 任务状态 | 进程内队列 + SQLite（`db/video_gen_tasks.sqlite3`） | 非 Redis |

README 写了 Passlib「如果使用用户认证」。`pyproject.toml` **没有** Passlib，代码里也**没有**用户认证中间件。

### 2.2 桌面客户端

路径：`desktop-client/`。

- Electron `31.7.6`（主进程），打包用 electron-builder / electron-packager
- 渲染进程：React 19 + Vite 7 + Bootstrap 5 + axios
- `desktop-client/web/package.json` 另声明了 Electron `^39.2.5`（仅 web 子项目 devDependency，与主进程版本不一致）
- 许可证文件是 MIT（`desktop-client/LICENSE`），与根目录 Apache-2.0 不同

### 2.3 顶层布局

```
main.py                 FastAPI 入口
config.py               路径与环境变量
exceptions.py           业务错误码
openapi.yaml            Coze 插件导入用 OpenAPI（约 34 条 path）
pyproject.toml / uv.lock
Dockerfile / docker-compose.yaml / docker-compose.example.yaml
src/router/             HTTP 路由
src/schemas/            请求/响应模型
src/service/            业务（一接口一文件）
src/utils/              下载、缓存、锁、存储、云渲染队列
src/middlewares/        目录准备、统一响应、W3C trace
src/pyJianYingDraft/    剪映草稿对象模型 + Windows 导出控制器
config/                 sticker.json、huazi.json
template/               default / default2 草稿模板
docs/                   中英接口说明（不全）
tests/                  约 71 个文件，质量参差
tools/                  贴纸抓取、ffprobe
scripts/                从 metadata 生成文档
desktop-client/         Electron 剪映小助手
.github/workflows/      仅 tag 触发的镜像/安装包构建
```

---

## 3. 架构与控制流

### 3.1 入口

- HTTP：`main.py` 创建 `FastAPI`，挂载 `v1_router`，前缀 `/openapi/capcut-mate`，再加 `/v1`
- 完整路径形如：`POST /openapi/capcut-mate/v1/create_draft`
- 进程启动时拉起两个后台协程：草稿目录清理、延迟删除（`src/utils/draft_cleanup.py`、`src/utils/deferred_delete.py`）
- 中间件顺序（后注册先执行）：`TraceContextMiddleware` → `ResponseMiddleware` → `PrepareMiddleware`
- 桌面端：`desktop-client/main.js` → preload → `nodeapi/ipcHandlers.js` → React 页（下载 / 历史 / 配置）

### 3.2 模块怎么连

典型写草稿请求：

1. `src/router/v1.py` 用 Pydantic schema 接参
2. 调用 `src/service/<name>.py` 的 `*_async`（带 `DraftLockManager` 写锁）
3. 从 `draft_url` 解析 `draft_id`，在 `DRAFT_CACHE` 取 `ScriptFile`
4. `src/utils/download.py` 把素材 URL 拉到 `output/draft/<id>/assets/...`
5. `src/pyJianYingDraft` 改轨道 / 片段 / 关键帧，写回 `draft_content.json`（双文件兼容时同步 `draft_info.json`）
6. `ResponseMiddleware` 把 JSON 包成 `{code, message, ...}`；业务异常也改成 HTTP 200

只读/拼装类接口（`timelines`、`video_infos`、`caption_infos` 等）不碰草稿，只把「URL + 时间线」编成下一跳接口要的 JSON **字符串**。这是给 Coze 工作流用的胶水层。

### 3.3 草稿生命周期

```
create_draft
  复制 template/default2 → output/draft/<timestamp+8hex>/
  ScriptFile.load_template → 改画布 → save → 写入 DRAFT_CACHE
  返回 DRAFT_URL + "?draft_id="

add_videos / add_images / add_audios / add_captions / ...
  必须 draft_id 仍在 DRAFT_CACHE
  下载素材 → 持锁改 ScriptFile → save

get_draft
  不读缓存，扫磁盘目录，把路径替换成 DOWNLOAD_URL 列表
  桌面端或云渲染用这些 URL 拉文件

save_draft
  仅 script.save()，且要求仍在缓存中
```

关键限制（代码优先于 README）：

- `DRAFT_CACHE` 是进程内 LRU，`MAX_CACHE_SIZE = 100`（`src/utils/draft_cache.py` 注释仍写 10000）
- **没有**「从磁盘重新 load 进缓存」的路径。服务重启或缓存淘汰后，磁盘上草稿还在，`get_draft` 仍可用，但所有 `add_*` / `save_draft` 会报无效草稿 URL
- 多 worker 时缓存不共享。`Dockerfile` 写了 `CMD ["uv", "run", "main.py", "--workers", "4"]`，但 `main.py` **不解析** `--workers`，实际是单进程 `uvicorn.run(...)`

### 3.4 两条「出片」路径

**路径 A — 本机剪映（桌面客户端）**

1. API 生成草稿并暴露文件 URL
2. 用户把 `get_draft?draft_id=...` 贴进 Electron
3. 主进程拉文件列表，下载到本机剪映草稿根目录（Windows 默认 `%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft`）
4. 用户在剪映里打开、编辑、导出

**路径 B — 所谓云渲染（`gen_video`）**

1. `ENABLE_APIKEY` 默认 `true`：用 `apiKey` 调 `https://jcaigc.cn/openapi/v1/user/points`，积分 ≤ 1 拒绝
2. `VideoGenTaskManager` 入队：最多 3 路下载草稿，剪映导出全局串行，最多 2 路上传
3. `draft_downloader` 按 `get_draft` 的文件列表把草稿落到 `config.DRAFT_SAVE_PATH`（硬编码某 Windows 用户路径）
4. `JianyingController`（仅 win32）用 UI Automation 点剪映「导出」
5. 成片上传 COS/OSS，按时长扣积分，状态写入 SQLite

Linux Docker 镜像**不能**走路径 B。官方 `docker-compose` 只覆盖路径 A 的 API + nginx 静态文件。

### 3.5 路由清单（代码，不是 README）

`src/router/v1.py` 实际注册、但 README 主表未列的接口：

- `POST /add_filters`、`POST /get_filters`、`POST /get_effects`、`POST /filter_infos`
- `GET /gen_video_active_count`

`docs/` 有 `add_filters.md`、`filter_infos.md`，没有 `get_filters` / `get_effects` / `gen_video_active_count` 专页。README 引用的 `docs/macos_sandbox_setup.md` **不存在**。

---

## 4. 安装、配置、运行（文档 vs 实际）

### 4.1 本地跑 API（与 README 基本一致）

前提：Python 3.11+、uv。

```
uv sync
# Windows 云渲染才需要：
uv pip install -e .[windows]
uv run main.py
# 文档：http://localhost:30000/docs
```

需要本机可写：`output/draft`、`temp`、`logs`、`db`（均在 `.gitignore`）。

### 4.2 环境变量（`config.py`，无 `.env.example`）

| 变量 | 默认 | 作用 |
| --- | --- | --- |
| `DRAFT_URL` | `https://capcut-mate.jcaigc.cn/openapi/capcut-mate/v1/get_draft` | 返回给客户端的草稿入口 |
| `DOWNLOAD_URL` | `https://capcut-mate.jcaigc.cn/` | 把本地路径换成下载 URL（`/app/` 语义依赖部署） |
| `TIP_URL` | `https://docs.jcaigc.cn/` | `create_draft` 附带的文档提示 |
| `DOWNLOAD_FILE_SIZE_LIMIT` | 200MB | 素材下载上限 |
| `ENABLE_APIKEY` | `true` | 为 true 时 `gen_video` 必须带官网 apiKey |
| `VIDEO_GEN_RETENTION_DAYS` | 7 | 成片预签名 URL 天数 |
| `STORAGE_UPLOAD_PREFIX` | 空 | COS/OSS object key 前缀 |
| `COS_*` / `OSS_*` | 空 | 成片上传；都空则上传失败 |
| `DRAFT_CLEANUP_MAX_DRAFT_COUNT` | 1000 | 磁盘草稿保留数 |
| `DRAFT_SAVE_PATH` | **不是环境变量** | 写死在 `config.py` 的 Windows 路径 |

自托管若仍用默认 `DRAFT_URL` / `DOWNLOAD_URL`，客户端会去作者生产域名拉草稿。

### 4.3 Docker

`docker-compose.yaml`：拉 `gogoshine/capcut-mate:latest` + `gogoshine/nginx:latest`，API 30000，nginx 80，把 `./html/output` 挂到 `/app/output`。

文档与实现缺口：

1. README 写 `docker-compose pull && docker-compose up -d`，未说明必须先有 `html/output`，也未说明 nginx 负责把 `get_draft` 的 URL 变成静态文件
2. 仓库 `Dockerfile` 依赖 CI 生成的 `dist/`（`COPY dist/ .`）。在干净仓库根目录 `docker build` **会失败**
3. `CMD` 的 `--workers 4` 无效（见 3.3）
4. compose 里 `DRAFT_URL=http://127.0.0.1/openapi/...`：对「本机浏览器 + 宿主机 nginx:80」可用；容器内进程访问 `127.0.0.1` 不是 nginx。上游 issue #59 即「改了宿主机端口后 Windows 客户端下不了草稿」
5. `docker-compose.example.yaml` 含作者 1Panel 绝对路径，不宜当通用模板
6. compose **未**注入 `ENABLE_APIKEY=false`、COS/OSS、`DRAFT_SAVE_PATH`。镜像是 Linux，云渲染本来也跑不起来

### 4.4 桌面客户端

README 在仓库根目录写 `npm install` / `npm run web:dev` / `npm start`，**没写 `cd desktop-client`**。正确顺序：

```
cd desktop-client
# 可选：ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
npm install
npm --prefix web install
npm run web:dev    # Vite :9000
npm start          # Electron，开发态加载 localhost:9000
```

生产态加载 `desktop-client/ui/index.html`（由 `web:build` 产出）。macOS 未签名，README 要求用户对 dmg/`xattr -cr`；并指向不存在的沙箱文档。

### 4.5 其它过时 / 错误文档

- 克隆地址写 `Hommy-master/capcut-mate`，不是本 fork
- 技术栈列出 Passlib，依赖里没有
- `docs/gen_video.md` 请求示例只有 `draft_url`，代码默认 `ENABLE_APIKEY=true` 且 `apiKey` 必须是 UUID
- `tests/test_draft_service.py` 调用不存在的 `create_draft_service`，路径写成 `/openapi/v1/create_draft`（少了 `capcut-mate`）
- `tests/test_middleware.py` 导入不存在的 `init_env_middleware` / `src.customException`
- README「Skills」无对应文件

---

## 5. 外部服务、鉴权、密钥、非官方接口

### 5.1 作者自己的服务（官方相对本项目而言）

| 服务 | 代码位置 | 用途 |
| --- | --- | --- |
| `https://jcaigc.cn/openapi/v1/user/points` | `src/utils/points.py` | 查积分、扣积分；apiKey 放 query/JSON，无服务端签名 |
| `https://jcaigc.cn` | schema / 错误文案 | 售卖 apiKey、工作流案例 |
| `https://docs.jcaigc.cn` | `TIP_URL` | 对外文档 |
| `https://capcut-mate.jcaigc.cn` | 默认 `DRAFT_URL` / `DOWNLOAD_URL` | 作者托管的 API + 静态草稿 |
| `https://jcaigc.cn/external-features` | `desktop-client/web/src/components/ExternalWebpage.jsx` | 客户端 iframe 运营页 |
| Coze 插件 / `api.coze.cn` | README、`tools/query_sticker.py` | 插件分发；贴纸库离线抓取 |
| Docker Hub `gogoshine/*` | compose / CI | 发布镜像 |
| 腾讯云 COS / 阿里云 OSS | `src/utils/cos.py`、`oss.py` | 成片托管 |

积分 API 的 Key 只做 UUID 格式校验（`src/schemas/gen_video.py`），有效性完全信任 `jcaigc.cn` 返回码 `10007`。

### 5.2 本服务自身的鉴权

- **绝大多数接口无认证**。任意能打到 30000 的客户端都可以 `create_draft`、往别人的 `draft_id` 加素材（若仍在缓存）、`get_draft` 列文件
- `get_draft` 的 `draft_id` 仅限制长度 20–32（`src/schemas/get_draft.py`），**没有** `../` 校验；服务层直接 `os.path.join(DRAFT_DIR, draft_id)`
- `ENABLE_APIKEY` 只挡 `gen_video`，且默认仍依赖外网 `jcaigc.cn`
- 没有 API Gateway 签名、没有用户表、没有 Passlib

### 5.3 密钥与敏感配置

应走环境变量、仓库未提供模板：`COS_SECRET_ID/KEY`、`OSS_ACCESS_KEY_*`、Docker Hub `DOCKERHUB_USERNAME/TOKEN`（CI）。

仓库内已有明文：`tools/query_sticker.py` 的 `DEFAULT_CONFIG["auth_token"]` 是 Coze `pat_...` 个人访问令牌。该脚本用它调 `https://api.coze.cn/v1/workflow/run` 批量搜贴纸，结果写入 `config/sticker.json`。**应视为已泄露，需在 Coze 侧轮换。**

### 5.4 与剪映 / ByteDance 相关的非官方能力

没有 CapCut 官方 HTTP API。逆向 / 非官方面包括：

1. **草稿格式**：`src/pyJianYingDraft/script_file.py` 与 `assets/draft_content_template.json` 复刻剪映工程 JSON（轨道、材料、画布、duration 微秒）
2. **资源 ID 表**：`src/pyJianYingDraft/metadata/*.py`（如 `video_intro.py`）以及 `config/huazi.json`、`config/sticker.json`，含内部 resource/effect id 与 md5
3. **桌面 RPA**：`jianying_controller.py` 用 `uiautomation` 按 ClassName / full_description 点剪映窗口，导出 720p–8K。依赖中文 UI 文案，剪映改版即碎
4. **本机目录约定**：Windows `JianyingPro\...\com.lveditor.draft`；桌面端 `draftPathDetect.js` 用 `root_meta_info.json` / `.recycle_bin` 识别根目录
5. **贴纸**：运行时只读本地 `sticker.json`；生成该文件时走 Coze workflow，不直接打剪映开放接口

素材下载会带 Chrome UA（`src/utils/download.py`），用于拉用户提供的 http(s) 文件，不是剪映 CDN 专用协议。

---

## 6. 风险

### 6.1 安全

- 默认监听 `0.0.0.0:30000`，草稿 API 无鉴权
- `get_draft` + nginx 静态目录 = 知道/猜到 `draft_id` 即可下素材；`draft_id` 是时间戳+8 位 hex，可枚举性高于 UUID
- `download()` 对调用方给出的 http(s) URL 服务端取回，**无 SSRF 白名单**（schema 只要求以 `http://` 或 `https://` 开头）。可打内网、云 metadata（若环境允许）
- 错误响应统一 HTTP 200，监控/WAF 不易按状态码拦
- 桌面端会按 `get_draft` 返回的 URL 批量下载并写入本机剪映目录；Electron 关了 `nodeIntegration`、开了 `contextIsolation`，但 IPC `get-url-json-data` / `save-file` 仍会跟任意用户粘贴的 URL
- 硬编码 Coze PAT（见 5.3）
- `DRAFT_CLEANUP_PROTECTED_DRAFT_IDS` 写死了两个生产草稿 ID（`src/utils/draft_cleanup.py`）

### 6.2 服务条款与合规

- 自动化操作剪映桌面、摘录内部资源 ID、用非官方方式消耗 VIP 花字/特效，很可能违反剪映 / CapCut ToS
- 贴纸/花字 JSON 可能含平台素材元数据，再分发有版权与平台条款风险
- 项目自称开源免费，云渲染却走 `jcaigc.cn` 积分；自托管默认 `ENABLE_APIKEY=true` 仍会向该站点扣费
- 品牌使用「CapCut」而实现针对「剪映」国内客户端，存在商标与产品线混淆

### 6.3 稳定性

- 云渲染强绑：**Windows + 已打开且停在目录页的剪映 + 写死的用户草稿路径 + 中文 UI**
- 导出全局一把锁；注释已写明挤占 asyncio 默认线程池时，同步 HTTP 路由可能卡住
- 草稿状态只在单进程内存：重启、多副本、缓存满（100）都会让进行中的编辑链断裂
- 剪映小版本（模板注释提到 5.9 缩放关键帧）会改变 JSON/UI，RPA 与模板要跟着改
- Docker 文档推荐的 Linux 部署**不能**云渲染

### 6.4 许可

- 根目录 `LICENSE`：Apache-2.0
- `NOTICE`：pyJianYingDraft © 2024 Gary Guan；本项目改动 © 2026 Hommy，同为 Apache-2.0
- `desktop-client/LICENSE`：MIT，作者 gogoshine
- 元数据与 `sticker.json` / `huazi.json` 的权利来源未说明；Apache/MIT **不覆盖**剪映素材 IP
- 上游 GitHub 显示 Apache-2.0；fork 自身 0 star，上游约 1563 star / 252 fork（会随时间变）

---

## 7. 质量信号

### 7.1 测试

- `tests/` 约 71 个文件，`pyproject.toml` 配了 pytest，**dev 依赖只有 pytest**，没有 httpx / pytest-mock
- 同时存在：较新的单元测试（如下载失败分类、存储 key、草稿锁、导出重试）和明显失效的脚本（`test_draft_service.py`、`test_middleware.py`、若干 `manual_test_*.py`）
- **CI 不跑测试**。`.github/workflows/dev.yml` 与 `desktop-client-dev.yml` 只在 `v*` tag 构建 Docker / 安装包

未在本环境跑完整 pytest（分析任务、且部分测试依赖 Windows UIA / 网络）。从导入与路径即可判断测试集不能当作绿灯门禁。

### 7.2 CI 与发布

- Docker：checkout → 把 `src/config/template/*.py/uv.lock` 拷进 `dist/` → buildx 推 `gogoshine/capcut-mate`
- 桌面：比较上一 `v*` tag 的 `desktop-client/` 变更；Windows / macOS arm64 / macOS x64；`CSC_IDENTITY_AUTO_DISCOVERY=false`（未签名）
- 无 PR 上的 lint、typecheck、pytest
- 本 fork：0 issue；4 个 PR（多为 Cursor 环境/修复，2 merged / 2 draft）
- 上游：近期仍有 issue（Docker 端口、蒙版、交叉编辑）和外部 PR；Release 版本号同时出现 v6.x 与 v8.x，tag 策略乱

### 7.3 代码健康（观察，不是重构建议）

- 路由/service/schema 按接口切文件，云渲染队列注释清楚，方向对
- `v1.py` 约 760 行重复样板；`draft_downloader.py` 约 1600 行；`video_task_manager.py` 约 870 行
- `*_infos` 接口把对象再 `json.dumps` 成字符串，是为了迁就 Coze 插件，但类型安全差
- 部分测试与中间件命名已与现码脱节，说明有机增长、缺少清理
- 提交历史约 596 条，作者几乎全是 Hommy；本 fork 无独立产品演进

---

## 8. 若要扩展：先看这些地方

按「改功能时最常碰到」排序：

1. **`src/router/v1.py` + `src/schemas/` + `src/service/`**  
   加/改 HTTP 接口的固定三件套。写草稿接口还要抄现有 `*_async` + `DraftLockManager`。先读 `create_draft.py`、`add_videos.py`、`add_captions.py`。

2. **`src/pyJianYingDraft/`**  
   草稿真相源。改轨道/片段/特效：`script_file.py`、`video_segment.py`、`text_segment.py`、`track.py`、`metadata/`。模板在 `template/default2` 与 `assets/draft_content_template.json`。

3. **`src/utils/draft_cache.py`、`draft_lock_manager.py`、`download.py`**  
   所有编辑接口的隐式前提。若要做多进程、重启恢复、或从磁盘 reload，必须先动这里。

4. **`src/service/gen_video.py` + `src/utils/video_task_manager.py` + `src/pyJianYingDraft/jianying_controller.py`**  
   云渲染全链路：积分、下载、RPA 导出、COS/OSS、扣费。Linux/Docker 上不要假设这条能通。

5. **`desktop-client/nodeapi/download.js` + `draftPathDetect.js` + `web/src/pages/Download/`**  
   草稿如何进本机剪映。改下载协议、多开剪映路径、或 `get_draft` URL 形态时改这里。

次要但常改：`config.py`（部署）、`config/sticker.json` / `huazi.json`（资源表）、`openapi.yaml`（Coze）、`docs/*.md`（与代码同步）。

---

## 附录：给新工程师的 10 分钟路径

1. 读本文件第 1、3、8 节
2. 跑 `uv sync && uv run main.py`，打开 `/docs`，`POST create_draft`
3. 看 `output/draft/<id>/` 里的 JSON，对照 `src/pyJianYingDraft/script_file.py`
4. 调一次 `add_videos`（注意 `video_infos` 是 **JSON 字符串**）
5. 调 `get_draft`，理解桌面端为什么只需要这个 URL
6. 若关心出片：区分「客户端导入剪映」与「Windows RPA 云渲染」，不要被 README「云端渲染」误导

<!-- AI-GEN-END -->
