# 🌳 键盘森林 Keyboard Forest

把每一次击键都变成养树的养分——你用键盘，你的树就生长。

## ✨ 功能特色

| 功能 | 说明 |
|------|------|
| 🌱 按键种树 | 74 个按键各养一棵树，击键越多树越高 |
| 📊 成长阶段 | 共 6 阶：土地 → 种子 → 幼苗 → 小树 → 大树 → 参天巨树 |
| 💚 健康系统 | 长时间不按某键，树会变黄、枯死 |
| 🌤 气候系统 | 晴天 / 多云 / 暴雨 / 干旱随机轮转，影响经验倍率 |
| ⚡ 随机事件 | 虫害、节日加成、Ctrl 守护者等十余种随机事件 |
| 🎨 外观皮肤 | 8 套外观（秋叶、白雪、樱花、黄金、水晶、黑曜、玫瑰、人民万岁） |
| 🏞 背景主题 | 9 套背景（森林、暮色、深海、沙漠、星河、520、熔岩、仙境、人民万岁） |
| 🪙 金币商店 | 毕业大树每日领金币，购买皮肤 / 消耗品 / 背景 |
| 📈 统计界面 | 活跃榜、按键量折线图 / 柱状图、健康历史、键盘热力图 |
| 🏆 成就系统 | Ctrl 守护者、十指俱全、常青树等多种成就 |
| 💳 充值金币 | 支持微信 / 支付宝扫码充值（1 元 = 1 金币） |

## 📋 环境要求

- **Python 3.10 +**（推荐 3.12 / 3.13）
- **Windows 10 / 11**（pynput 全局键盘监听）
- 其余依赖见 `requirements.txt`

> macOS / Linux 未经测试，pynput 在部分 Linux 桌面环境需要额外权限。

## 🚀 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/<你的用户名>/jianpanxiaoshu.git
cd jianpanxiaoshu

# 2. 创建并激活虚拟环境（可选但推荐）
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动
python main.py
```

首次启动会自动在桌面创建快捷方式（仅 Windows）。

每位用户的树林数据保存在本地 `keyboard_forest.db`，**完全独立**，互不影响。

## 📁 项目结构

```
jianpanxiaoshu/
├── main.py               # 入口
├── config.py             # 全局常量（窗口尺寸、颜色、按键布局）
├── database.py           # SQLite 数据库封装
├── forest.py             # 森林逻辑（按键处理、定时 tick）
├── key_tree.py           # 单棵树的数据模型
├── climate.py            # 气候状态机
├── events.py             # 随机事件系统
├── achievements.py       # 成就系统
├── shop.py               # 商店数据与逻辑
├── keyboard_tracker.py   # pynput 全局键盘监听
├── create_shortcut.py    # 桌面快捷方式生成工具
├── assets/               # 图片资源（充值二维码等）
├── reports/              # 统计报告 PNG（运行时生成，不进版本库）
├── requirements.txt
└── renderer/
    ├── forest_view.py    # 主界面：键盘树格渲染
    ├── detail_view.py    # 右侧详情面板（单键信息）
    ├── hud.py            # 顶部 HUD 栏
    ├── stats_view.py     # 统计界面
    ├── shop_view.py      # 商店界面
    ├── grove_view.py     # 树林全景视图
    ├── achievement_view.py # 成就界面
    ├── tree_sprites.py   # 像素树精灵绘制（无图片资源）
    ├── weather_particles.py # 天气粒子特效
    └── clear_dialog.py   # 数据清除确认弹窗
```

## 🎮 基本操作

| 操作 | 说明 |
|------|------|
| 正常打字 | 对应按键树获得经验 |
| 点击键格 | 打开右侧详情面板 |
| ESC | 关闭详情面板 / 退出 |
| 顶部 Tab | 切换 森林 / 统计 / 树林 / 成就 / 商店 |
| 商店 → 统计界面 → 保存报告 | 导出 PNG 报告到 reports/ |

## 📦 依赖

```
pygame>=2.6.0
pynput>=1.7.6
```

## 📄 开源协议

不得擅自使用
