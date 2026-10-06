# Borgaro 中心 5 km 基础图

## 图件与数据

- `01_borgaro_5km_roads_buildings.png`：预览图
- `01_borgaro_5km_roads_buildings.pdf`：打印版
- `01_borgaro_5km_roads_buildings.gpkg`：5 km 圆形范围内裁切的道路、建筑与研究区边界矢量数据
- `01_borgaro_5km_base.py`：可复现的裁切与制图脚本

中心点设在 Borgaro Torinese 的 Piazza Vittorio Veneto（约 45.1517°N, 7.6577°E），以 EPSG:32632 投影后建立 5,000 m 半径圆。道路来自课程 `Inquadramento.dxf` 的 `el_str` 与 `el_vms` 图层；建筑轮廓来自 `edifc` 图层。DXF 的道路/建筑要素在此半径内逐项裁切，并转换为 GeoPackage，累计得到 4,338 个道路要素和 10,400 个建筑轮廓。

## 数据说明

当前环境无法连接 OSM/Overpass 下载端点。此前用户同意使用 BDTRE 等现有数据作为替代。课程 DXF 未写入 CRS 元数据，本图依课程 QGIS 工程将其按 EPSG:32632 解释；它是 CAD 线稿数据，图中仅表达道路与建筑形态，不推断道路主次等级、通行权或现场现状。课程目录中的 Torino 代码 GeoPackage 不覆盖 Borgaro 中心，因此本图没有用它来填补 Borgaro 数据。
