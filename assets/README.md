# 素材目录

本目录的 PNG **已经内置**（由 `scripts/build_assets.js` 从 SVG 素材包栅格化而来），
`src/board_image.py` 直接用 Pillow 合成棋盘，运行时不访问外网。

```
tiles/      straight.png  corner.png  t-shape.png      3 种牌型底图
treasures/  Helmet.png ... Ghost.png                   24 个宝藏图标
pawns/      yellow.png red.png blue.png green.png      4 个棋子
```

## 牌型底图的朝向约定

三张底图统一为 **rotation=0** 的朝向，代码按牌的实际朝向顺时针旋转后拼接：

| 文件 | rotation=0 的开口 |
| --- | --- |
| `straight.png` | 上、下 |
| `corner.png` | 上、右 |
| `t-shape.png` | 上、右、下 |

底图只画通道与石墙、**不含宝藏**；宝藏由 `treasures/<id>.png` 以半格大小居中叠加。

## 重新生成 / 替换素材

```bash
npm i @resvg/resvg-js
node scripts/build_assets.js scripts/labyrinth_svg_asset_pack_v2_fixed.html assets
```

`scripts/labyrinth_svg_asset_pack_v2_fixed.html` 是素材包源文件（含 `<defs>` + `<symbol>`）。
想换成自己画的素材时：**按上面的朝向约定**导出三张牌型底图，其余 PNG 直接用同名文件覆盖即可
（缺文件时 `src/board_image.py` 会自动退回几何图形，不会报错）。
