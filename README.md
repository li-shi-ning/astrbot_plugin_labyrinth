# 疯狂迷宫（AstrBot 插件）

`astrbot_plugin_labyrinth` 是桌游《Labyrinth 疯狂迷宫》的 AstrBot 群聊实现，
面向 **QQ 官方机器人**（`qq_official` / `qq_official_webhook`）。

- 2-4 人同群对战，推牌改变整座迷宫，抢先集齐宝藏并回到起点者获胜。
- 每回合：**推牌**（可先旋转手牌）→ **移动**（或原地不动）。
- 棋盘用本地渲染的 PNG 走 **QQ 富媒体消息** 发送；当前目标用 **私密按钮** 下发。

## 玩法速览

1. 每回合你必须先把手牌插进 12 个箭头之一（第 2/4/6 行或列），
   对端被挤出的牌成为新手牌；**插入前可任意旋转手牌**。
2. 不能把上一手刚推出的位置原路推回。
3. 推完后可沿通道任意走，也可以不走。
4. 走到自己当前目标宝藏那一格即收集，换下一张目标。
5. 集齐全部目标后回到自己的起点格即获胜。

完整规则见 [`docs/rules.md`](docs/rules.md)。

## 指令与按钮

| 按钮 / 指令 | 说明 |
| --- | --- |
| `迷宫 创建` / `加入` / `开始` | 创建 / 加入 / 开局（2-4 人） |
| `迷宫 状态` | 重发棋盘 |
| `迷宫 目标` | 点属于自己的「目标」按钮，内容只进本人输入框 |
| `迷宫 转` | 手牌顺时针旋转 90°（可多次） |
| `迷宫 推 上 2` | 从上方把牌推入第 2 列（方向 + 2/4/6） |
| `迷宫 走 3 4` | 走到第 3 行第 4 列（行列从 1 开始） |
| `迷宫 停` | 不移动，直接结束回合 |
| `迷宫 退出` / `解散` | 退出牌局 / 房主解散 |
| `迷宫 规则` / `帮助` | 规则 / 指令说明 |

## 棋盘图片与素材

棋盘由 `src/board_image.py` 用 Pillow 本地渲染，**不访问外网**。
素材放在 `assets/`，缺失时自动用几何图形兜底：

| 路径 | 说明 |
| --- | --- |
| `assets/tiles/straight.png`、`corner.png`、`t-shape.png` | 牌型基础图（rotation=0 的朝向，代码负责旋转） |
| `assets/treasures/<TreasureId>.png` | 宝藏图标，画在牌中央（如 `Mouse.png`、`Crown.png`） |
| `assets/pawns/<color>.png` | 棋子（`yellow` / `red` / `blue` / `green`） |
| `assets/font.ttf` | 可选，中文字体；缺省时自动查找 AstrBot 自带字体 |

## 配置 `_conf_schema.json`

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `board_image` | `true` | 是否把棋盘渲染成图片走富媒体发送 |
| `board_font_path` | `""` | 棋盘图中文字体路径，留空自动查找 |

## 已知限制

- 仅支持 QQ 官方机器人。
- 牌局保存在内存中，插件重载/重启后丢失。
- 没有回合超时；挂机会卡住牌局，可由房主解散。

## 致谢

- 规则与牌堆数据参考 `kimmobrunfeldt/labyrinth`、`pallagj/labyrinth-board-game`
  与 UltraBoardGames 官方规则页。
- 私密信息按钮（`only_for` + `enter=false`）与富媒体发送方案沿用
  `astrbot_plugin_official_TexasHoldem` 与 `astrbot_plugin_davinci_code`。

## 许可

GNU Affero General Public License v3.0，见 [LICENSE](LICENSE)。
