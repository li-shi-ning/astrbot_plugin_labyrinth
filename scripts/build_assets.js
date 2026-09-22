#!/usr/bin/env node
/**
 * 把参考 SVG 素材包（一张 HTML，内含 <defs> + <symbol>）栅格化成插件需要的 PNG 素材。
 *
 * 用法:
 *   npm i @resvg/resvg-js        # 只需一次
 *   node scripts/build_assets.js <源HTML> <输出目录>
 *
 * 产物:
 *   <out>/tiles/{straight,corner,t-shape}.png    统一为 rotation=0 朝向
 *   <out>/treasures/<TreasureId>.png             24 个宝藏
 *   <out>/pawns/{yellow,red,blue,green}.png      4 个棋子
 */
const fs = require('fs')
const path = require('path')
const { Resvg } = require('@resvg/resvg-js')

const SRC = process.argv[2] || 'scripts/labyrinth_svg_asset_pack_v2_fixed.html'
const OUT = process.argv[3] || 'assets'

const html = fs.readFileSync(SRC, 'utf8')
const defsMatch = html.match(/<defs>([\s\S]*?)<\/defs>/)
if (!defsMatch) {
  console.error('未在源文件中找到 <defs>')
  process.exit(1)
}
const DEFS = defsMatch[1]

/** 牌型：SVG 里 I 是横向、T 缺上/右/左 中的“左”侧，统一旋到本插件的基准朝向 */
const TILES = [
  // name, symbol, 需顺时针旋转的角度（统一 rotation=0 朝向：straight=上下, corner=上右, t-shape=上右下）
  ['straight', 'tile-straight', 90],
  ['corner', 'tile-corner', 0],
  ['t-shape', 'tile-tee', 90],
]

const PAWNS = ['yellow', 'red', 'blue', 'green']

/** 本插件宝藏 id -> 素材包 symbol 后缀 */
const TREASURES = {
  Helmet: 'helmet',
  Candelabra: 'candelabra',
  Sword: 'sword',
  Jewel: 'jewel',
  TreasureChest: 'treasure_chest',
  Ring: 'ring',
  TreasureMap: 'treasure_map',
  Keys: 'keys',
  Crown: 'crown',
  GhostInBottle: 'ghost_in_bottle',
  BagOfGold: 'bag_of_gold',
  Book: 'book',
  Rat: 'rat',
  Bat: 'bat',
  Owl: 'owl',
  Lizard: 'lizard',
  Spider: 'spider',
  Moth: 'moth',
  Scarab: 'scarab',
  Skull: 'skull',
  Dragon: 'dragon',
  Princess: 'princess',
  Sorceress: 'sorceress',
  Ghost: 'ghost',
}

function render(symbolId, size, rotateDeg, outFile) {
  const transform = rotateDeg ? ` transform="rotate(${rotateDeg} 50 50)"` : ''
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"` +
    ` viewBox="0 0 100 100" width="${size}" height="${size}">` +
    `<defs>${DEFS}</defs>` +
    `<use xlink:href="#${symbolId}"${transform}/></svg>`
  const resvg = new Resvg(svg, {
    fitTo: { mode: 'width', value: size },
    background: 'rgba(0,0,0,0)',
  })
  fs.mkdirSync(path.dirname(outFile), { recursive: true })
  fs.writeFileSync(outFile, resvg.render().asPng())
  console.log(`${path.relative(OUT, outFile).padEnd(28)} <- #${symbolId}${rotateDeg ? ` (rotate ${rotateDeg}°)` : ''}`)
}

for (const [name, symbol, rotate] of TILES) {
  render(symbol, 256, rotate, path.join(OUT, 'tiles', `${name}.png`))
}
for (const [id, symbol] of Object.entries(TREASURES)) {
  render(`treasure-${symbol}`, 192, 0, path.join(OUT, 'treasures', `${id}.png`))
}
for (const color of PAWNS) {
  render(`player-${color}`, 192, 0, path.join(OUT, 'pawns', `${color}.png`))
}
console.log(`\n完成：牌型 ${TILES.length}、宝藏 ${Object.keys(TREASURES).length}、棋子 ${PAWNS.length}`)
