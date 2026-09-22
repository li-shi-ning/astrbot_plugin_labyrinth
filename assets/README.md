# 素材目录约定

棋盘图片由 `src/board_image.py` 用 Pillow 本地合成，**缺素材时会自动用几何图形兜底**，
所以这里可以先空着，随时补图即可。

## tiles/ —— 牌型基础图

放 3 张**牌型底图**（通道用浅色、墙用深色），朝向统一为 `rotation=0`，
代码会按牌的实际朝向自动旋转：

| 文件 | 朝向（rotation=0） | 说明 |
| --- | --- | --- |
| `straight.png` | 上、下 | 直路 |
| `corner.png` | 上、右 | 拐角 |
| `t-shape.png` | 上、右、下 | 三通 |

建议尺寸 **正方形**，例如 `256×256`（会被缩放到 64×64 渲染）。
四边出口要画到图片边缘，拼接后通道才能对上。

## treasures/ —— 宝藏图标

24 张，文件名用宝藏 id（也就是 `src/tiles.py` 里的 key）：

```
KnightHelmet.png  Candles.png  Dagger.png  Diamond.png  Treasure.png  Ring.png
HolyGrail.png     Keys.png     Crown.png   Potion.png   Coins.png     Book.png
Mouse.png  Bomb.png  Cat.png  Owl.png  Lizard.png  Bug.png
Pony.png   Bat.png   Ghost.png  Mermaid.png  Dinosaur.png  Cannon.png
```

会以约 5/8 格子的尺寸居中贴在牌上，建议正方形、背景透明（PNG）。

## pawns/ —— 棋子

`yellow.png`、`red.png`、`blue.png`、`green.png`，建议正方形、透明背景。

## font.ttf（可选）

放一个中文字体即可让棋盘里的中文更稳定；不放时自动查找
`/AstrBot/data/font.ttf`（AstrBot 自带）或系统中文字体。
