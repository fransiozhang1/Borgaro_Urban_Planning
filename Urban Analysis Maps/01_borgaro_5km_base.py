#!/usr/bin/env python3
"""Extract and map road linework and building footprints within 5 km of Borgaro town centre."""
from pathlib import Path
import math, os
os.environ.setdefault('MPLCONFIGDIR','/tmp/mpl-borgaro')
from osgeo import ogr, osr
import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
font_manager.fontManager.addfont(FONT)
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Polygon as MplPolygon, Circle as MplCircle

ROOT=Path(__file__).resolve().parents[1]
DXF=ROOT/'Territorial data'/'Territorial Layers'/'Inquadramento.dxf'
OUT=Path(__file__).resolve().parent
GPKG_OUT=OUT/'01_borgaro_5km_roads_buildings.gpkg'
PNG_OUT=OUT/'01_borgaro_5km_roads_buildings.png'
PDF_OUT=OUT/'01_borgaro_5km_roads_buildings.pdf'

# Piazza Vittorio Veneto, Borgaro town centre (coordinate from published map listing).
LON,LAT=7.6577,45.1517
RADIUS=5000.0
srs_ll=osr.SpatialReference(); srs_ll.ImportFromEPSG(4326); srs_ll.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
srs=osr.SpatialReference(); srs.ImportFromEPSG(32632); srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
ct=osr.CoordinateTransformation(srs_ll,srs)
CX,CY,_=ct.TransformPoint(LON,LAT)

def make_circle(x,y,r,n=180):
    ring=ogr.Geometry(ogr.wkbLinearRing)
    for i in range(n+1):
        a=2*math.pi*i/n
        ring.AddPoint_2D(x+r*math.cos(a),y+r*math.sin(a))
    p=ogr.Geometry(ogr.wkbPolygon); p.AddGeometry(ring); return p

study=make_circle(CX,CY,RADIUS)
minx,maxx,miny,maxy=study.GetEnvelope()
dxf=ogr.Open(str(DXF),0); src=dxf.GetLayerByName('entities')
src.SetSpatialFilterRect(minx,miny,maxx,maxy)
roads=[]; buildings=[]
for f in src:
    g=f.GetGeometryRef()
    if not g or not g.Intersects(study): continue
    layer=f.GetField('Layer') or ''
    base=layer.split(' - ')[0]
    if base in ('el_str','el_vms'):
        cut=g.Intersection(study)
        if cut and not cut.IsEmpty(): roads.append((cut.Clone(),base,f.GetField('EntityHandle') or ''))
    elif base=='edifc':
        # DXF encodes building outlines as closed line strings; convert to footprint polygons.
        if ogr.GT_Flatten(g.GetGeometryType())!=ogr.wkbLineString: continue
        n=g.GetPointCount()
        if n<4 or (g.GetX(0)!=g.GetX(n-1) or g.GetY(0)!=g.GetY(n-1)): continue
        ring=ogr.Geometry(ogr.wkbLinearRing)
        for i in range(n): ring.AddPoint_2D(g.GetX(i),g.GetY(i))
        poly=ogr.Geometry(ogr.wkbPolygon); poly.AddGeometry(ring)
        if not poly.IsValid(): continue
        cut=poly.Intersection(study)
        if cut and not cut.IsEmpty(): buildings.append((cut.Clone(),base,f.GetField('EntityHandle') or ''))
src.SetSpatialFilter(None)

# Save the actual clipped study-area extracts as a portable GeoPackage.
if GPKG_OUT.exists(): GPKG_OUT.unlink()
drv=ogr.GetDriverByName('GPKG'); out=drv.CreateDataSource(str(GPKG_OUT))
out_srs=srs

def add_layer(name,geomtype,records):
    layer=out.CreateLayer(name,out_srs,geomtype)
    for n,t in [('source_layer',ogr.OFTString),('source_id',ogr.OFTString)]:
        fd=ogr.FieldDefn(n,t); layer.CreateField(fd)
    for geom,source,oid in records:
        feat=ogr.Feature(layer.GetLayerDefn()); feat.SetField('source_layer',source); feat.SetField('source_id',oid); feat.SetGeometry(geom); layer.CreateFeature(feat); feat=None
    layer=None
add_layer('roads',ogr.wkbUnknown,roads)
add_layer('buildings',ogr.wkbUnknown,buildings)
add_layer('study_area',ogr.wkbPolygon,[(study,'radius_5km','centre_piazza_vittorio_veneto')])
out=None

# Draw line and polygon geometry parts without changing geometry topology.
def lines(g):
    if g is None:return
    typ=ogr.GT_Flatten(g.GetGeometryType())
    if typ in (ogr.wkbLineString,ogr.wkbLinearRing):
        pts=[(g.GetX(i),g.GetY(i)) for i in range(g.GetPointCount())]
        if len(pts)>1: yield pts
    else:
        for i in range(g.GetGeometryCount()): yield from lines(g.GetGeometryRef(i))
def polygons(g):
    if g is None:return
    typ=ogr.GT_Flatten(g.GetGeometryType())
    if typ==ogr.wkbPolygon:
        r=g.GetGeometryRef(0)
        yield [(r.GetX(i),r.GetY(i)) for i in range(r.GetPointCount())]
    else:
        for i in range(g.GetGeometryCount()): yield from polygons(g.GetGeometryRef(i))

road_segments=[seg for g,_,_ in roads for seg in lines(g)]
bld_patches=[MplPolygon(p,closed=True) for g,_,_ in buildings for p in polygons(g)]

# One calm, legible base map; geometry colours distinguish linework and built mass only.
PAPER='#F7F5EF'; INK='#203044'; ROAD='#5F7788'; BLD='#AEB8BB'; ACCENT='#E36F4B'; MUTED='#66717C'
plt.rcParams.update({'font.family':font_manager.FontProperties(fname=FONT).get_name(),'axes.unicode_minus':False,'figure.facecolor':PAPER,'savefig.facecolor':PAPER})
fig=plt.figure(figsize=(15,11),constrained_layout=False)
ax=fig.add_axes([.04,.06,.69,.76]); side=fig.add_axes([.77,.12,.20,.76]); side.axis('off')
ax.set_facecolor('#F2F0E9'); ax.set_xlim(CX-RADIUS,CX+RADIUS); ax.set_ylim(CY-RADIUS,CY+RADIUS); ax.set_aspect('equal'); ax.set_xticks([]);ax.set_yticks([])
for sp in ax.spines.values():sp.set_visible(False)
ax.add_collection(PatchCollection(bld_patches,facecolor=BLD,edgecolor='none',alpha=.83,zorder=1,rasterized=True))
if road_segments: ax.add_collection(LineCollection(road_segments,colors=ROAD,linewidths=.55,alpha=.82,zorder=2,rasterized=True))
ax.add_patch(MplCircle((CX,CY),RADIUS,fill=False,edgecolor=ACCENT,linewidth=1.3,linestyle=(0,(4,3)),zorder=4))
ax.scatter([CX],[CY],s=38,color=ACCENT,edgecolor='white',linewidth=.8,zorder=5)
ax.annotate('Piazza Vittorio Veneto\n研究中心点',(CX,CY),xytext=(10,11),textcoords='offset points',fontsize=8,color=INK,ha='left',va='bottom',bbox=dict(boxstyle='round,pad=.25',fc=PAPER,ec='none',alpha=.92),zorder=6)
# 2 km scalebar
sx=CX-RADIUS+350; sy=CY-RADIUS+350
ax.plot([sx,sx+2000],[sy,sy],color=INK,lw=2.1,zorder=6)
ax.plot([sx,sx],[sy-65,sy+65],color=INK,lw=1,zorder=6);ax.plot([sx+2000,sx+2000],[sy-65,sy+65],color=INK,lw=1,zorder=6)
ax.text(sx+1000,sy+95,'2 km',ha='center',va='bottom',fontsize=8,color=INK,zorder=6)
ax.annotate('N',(CX+RADIUS-450,CY+RADIUS-400),xytext=(CX+RADIUS-450,CY+RADIUS-1050),ha='center',va='center',fontsize=10,fontweight='bold',color=INK,arrowprops=dict(arrowstyle='-|>',color=INK,lw=1.2),zorder=6)
fig.text(.04,.965,'BORGARO TORINESE  /  BASE MAP 01',fontsize=9,fontweight='bold',color=MUTED,va='top')
fig.text(.04,.905,'Borgaro 中心 5 km 范围：道路与建筑',fontsize=23,fontweight='bold',color=INK,va='top')
fig.text(.04,.86,'5 km 半径圆形研究区  ·  以 Piazza Vittorio Veneto 为中心  ·  EPSG:32632',fontsize=10,color=MUTED,va='top')
# Right-hand key and factual provenance.
side.text(0,1,'图例',transform=side.transAxes,fontsize=13,fontweight='bold',color=INK,va='top')
side.plot([0,.98],[.95,.95],transform=side.transAxes,color='#D9DEE0',lw=1)
side.add_patch(plt.Rectangle((.02,.875),.13,.025,transform=side.transAxes,facecolor=BLD,edgecolor='none'))
side.text(.21,.887,'建筑轮廓',transform=side.transAxes,fontsize=9,color=INK,va='center')
side.plot([.02,.15],[.83,.83],transform=side.transAxes,color=ROAD,lw=1.4)
side.text(.21,.83,'道路中心线/道路要素',transform=side.transAxes,fontsize=9,color=INK,va='center')
side.plot([.02,.15],[.78,.78],transform=side.transAxes,color=ACCENT,lw=1.4,ls=(0,(4,3)))
side.text(.21,.78,'5 km 研究区边界',transform=side.transAxes,fontsize=9,color=INK,va='center')
side.text(0,.68,'范围内提取',transform=side.transAxes,fontsize=11,fontweight='bold',color=INK,va='top')
side.plot([0,.98],[.645,.645],transform=side.transAxes,color='#D9DEE0',lw=1)
side.text(0,.61,f'建筑轮廓：{len(buildings):,} 栋\n道路要素：{len(roads):,} 条\n圆形范围：半径 5.0 km',transform=side.transAxes,fontsize=10,color=INK,va='top',linespacing=1.8)
side.text(0,.44,'数据与判读',transform=side.transAxes,fontsize=11,fontweight='bold',color=INK,va='top')
side.plot([0,.98],[.405,.405],transform=side.transAxes,color='#D9DEE0',lw=1)
side.text(0,.37,'来源：课程提供的\nInquadramento.dxf（BDTRE CAD）\n道路：el_str、el_vms 图层\n建筑：edifc 图层\n\nDXF 无 CRS 元数据；按课程 QGIS\n项目坐标解释为 EPSG:32632。\n图层为 CAD 导出线稿；道路按\n要素表达，未擅自推断主次等级。',transform=side.transAxes,fontsize=8.6,color=MUTED,va='top',linespacing=1.55)
side.text(0,.07,'本次从课程 DXF 裁切并另存为\nGeoPackage，后续可继续复用。',transform=side.transAxes,fontsize=8,color=MUTED,va='bottom',linespacing=1.45)
fig.text(.04,.025,'制图范围严格限定在中心点外 5,000 m；圆内数据由课程 DXF 裁切。此图为基础数据底图，未表示现场通行权或道路等级。',fontsize=8,color=MUTED,va='bottom')
fig.savefig(PNG_OUT,dpi=240,bbox_inches='tight')
fig.savefig(PDF_OUT,bbox_inches='tight')
print('centre_epsg32632',round(CX,2),round(CY,2))
print('roads',len(roads),'buildings',len(buildings),'segments',len(road_segments),'building_polygons',len(bld_patches))
for p in (GPKG_OUT,PNG_OUT,PDF_OUT):print(p.name,p.stat().st_size)
