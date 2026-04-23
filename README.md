# 明朝那些事儿 — 交互式历史可视化

一个基于 D3.js 的纯前端交互式可视化项目，将《明朝那些事儿》（全七卷）中的人物、事件和关系以时间轴形式呈现。

## 演示视频

<video src="https://raw.githubusercontent.com/yejunbin/ming-dynasty-vis/assets/video.mp4" controls width="100%"></video>


## 在线预览

直接打开 `web/index_v2.html` 即可在浏览器中查看（需联网加载 D3.js）。

## 功能特性

- **垂直时间轴**：1328—1644 年纵向展开，每 50 年一个大刻度
- **皇帝在位条**：时间轴右侧展示 17 位皇帝的在位时段，标注姓名、年号、庙号
- **人物视图（左侧）**：圆圈大小反映人物关系度，颜色区分不同人物，可拖拽移动
- **事件视图（右侧）**：按重要性着色（1-5 级），按书中出场顺序排列，可拖拽移动
- **叙事脉络线**：虚线连接相邻事件，展示书中的叙事顺序
- **交互高亮**：点击人物或事件，高亮其关联的人物、关系和事件；点击空白处取消
- **按卷筛选**：左上角下拉框可切换全七卷或任意单卷
- **缩放平移**：支持鼠标滚轮缩放和拖拽平移整个画布

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | HTML5 + CSS3 + Vanilla JS |
| 可视化 | D3.js v7 |
| 数据提取 | Python 3 + DeepSeek API |
| 数据源 | 《明朝那些事儿》7 卷本 |

## 项目结构

```
ming/
├── web/
│   ├── index.html              # 主页面（异步加载 JSON，需 HTTP 服务器）
│   ├── index_v2.html           # 离线版（数据内联，可直接双击打开）
│   └── data/
│       └── ming_all.json       # 合并后的可视化数据
├── data/                       # 各卷原始提取数据
│   ├── vol1_persons_relations.json
│   ├── vol1_events.json
│   ├── ...
│   └── ming_all.json           # 合并后的主数据（同 web/data）
├── extract_volume.py           # 通用提取脚本（人物、关系、事件）
├── merge_all_volumes.py        # 合并 7 卷数据为 ming_all.json
├── .env                        # DeepSeek API 密钥
└── 明朝那些事儿.txt            # 原始文本（GBK 编码）
```

## 数据规模

- **人物**：663 位核心人物
- **事件**：1,152 个关键事件
- **关系**：1,389 条人物关系
- **章节**：156 章（全七卷）

## 数据提取流程

1. **逐章提取**：`extract_volume.py` 调用 DeepSeek API，逐章提取人物、关系和事件
2. **单卷合并**：每卷生成 `vol{N}_persons_relations.json` 和 `vol{N}_events.json`
3. **全卷合并**：`merge_all_volumes.py` 合并 7 卷数据，去重、过滤、推断年份，生成 `ming_all.json`

### 运行提取

```bash
# 设置 API 密钥
export DEEPSEEK_API_KEY=sk-xxxxx

# 提取第 1 卷（需指定起止行号）
python3 extract_volume.py 1 0 5000 "第1卷"

# 合并全七卷
python3 merge_all_volumes.py
```

## 本地运行

无需构建工具，直接用浏览器打开即可。

### 方式一：离线版（推荐，直接双击打开）

使用 `index_v2.html`，JSON 数据已内联到 HTML 中，不依赖外部请求：

```bash
cd web
# macOS
open index_v2.html
# Linux
xdg-open index_v2.html
# Windows
start index_v2.html
```

### 方式二：HTTP 服务器（使用 index.html）

```bash
cd web && python3 -m http.server 8080
# 然后访问 http://localhost:8080
```

### 方式对比

| 文件 | 数据加载方式 | 是否需要服务器 | 文件大小 |
|------|-------------|---------------|---------|
| `index.html` | `fetch()` 异步加载 JSON | 是 | ~15 KB |
| `index_v2.html` | JSON 内联到 HTML | 否 | ~1.2 MB |

## 浏览器兼容

- Chrome / Edge / Firefox / Safari（现代浏览器）
- 需支持 ES6、CSS Grid、SVG

## 许可证

数据来源于公开出版物《明朝那些事儿》。本项目代码部分采用 MIT 许可证。
