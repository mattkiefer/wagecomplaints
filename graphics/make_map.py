import mapnik, csv
from wagecomplaints.settings import BASE_DIR
from census.models import Zip
from PIL import Image, ImageFont, ImageDraw
#import gifmaker
#from images2gif import writeGif
import glob

### START CONFIG ###
# files
output_dir = BASE_DIR + '/graphics/output/'
output_file_ext = 'png'
gif_file_name = output_dir + 'zips.gif'

zipcode_file_path = BASE_DIR + '/graphics/shapes/Zip_Codes.csv' # note: zip code 60666 (o'hare) deleted
zipcode_csv = [x for x in csv.DictReader(open(zipcode_file_path))]

# map
map_width = 700
map_height = 600
proj4 = '+proj=tmerc +lat_0=36.66666666666666 +lon_0=-88.33333333333333 +k=0.9999749999999999 +x_0=300000 +y_0=0 +datum=NAD83 +units=us-ft +no_defs'
# reference:
#   https://www.cityofchicago.org/dam/city/depts/doit/general/GIS/GIS_Data/GIS_Data_FAQ.pdf
#   http://spatialreference.org/ref/epsg/wgs-84/
offset = 25000 # how far right to push shapes

# style
bg_color = "#222222" #tcr black
poly_fill = "#f2eff9"
line_color = 'rgb(50%,50%,50%)'
line_width = 0.1

high_fill = "#CC3300" #tcr red

font_dir = BASE_DIR + '/graphics/fonts/'
open_sans_cond_light = font_dir + 'OpenSansCondensed-Light.ttf' 
open_sans_cond_bold = font_dir + 'OpenSansCondensed-Bold.ttf' 
hed_size = 100
font_size = 30
source_size = 20

hed = ImageFont.truetype(open_sans_cond_bold,hed_size)
bold = ImageFont.truetype(open_sans_cond_bold,font_size)
light = ImageFont.truetype(open_sans_cond_light,font_size)
source = ImageFont.truetype(open_sans_cond_light,source_size)

space = 12
### END CONFIG ###


def init():
    for z in query_zips():
        make_map(z)
    gifify_map()


def query_zips(limit=10):
    chi_zip_codes = [x['ZIP'] for x in zipcode_csv]
    census_chi_zips = [x for x in Zip.objects.filter(zip_code__in=chi_zip_codes,cnt_workforce__gt=1000)]
    census_chi_zips_sorted = sorted(census_chi_zips, key = lambda z: complaints_by_workforce(z), reverse=True) 
    return census_chi_zips_sorted[0:limit]


def complaints_by_workforce(zip_code):
    return round(float(len(zip_code.complaint_set.all()))/zip_code.cnt_workforce*100,2)
    

def make_map(z):
    m = setup_map()
    layered_map = setup_base_layer(m)
    highlighted_map = setup_highlight_layer(layered_map,z.zip_code)
    map_path = export_map(highlighted_map,z.zip_code)
    markup_map(map_path,z)
    optimize_map(map_path)


def setup_map():
    # map setup
    m = mapnik.Map(map_width,map_height,proj4)
    m.background = mapnik.Color(bg_color)
    return m


def add_base_style(m):
    # polygon styles
    polygon_symbolizer = mapnik.PolygonSymbolizer()
    polygon_symbolizer.fill = mapnik.Color(poly_fill)

    # line styles
    line_symbolizer = mapnik.LineSymbolizer()
    line_symbolizer.stroke = mapnik.Color(line_color)
    line_symbolizer.stroke_width = line_width

    # append styles
    rule = mapnik.Rule()
    rule.symbols.append(line_symbolizer)
    rule.symbols.append(polygon_symbolizer)
    style = mapnik.Style()
    style.rules.append(rule)
    m.append_style('My Style',style)
    return m


def setup_base_layer(m):
    styled_map = add_base_style(m)

    # layer setup
    zcsv = mapnik.CSV(file=zipcode_file_path)
    layer = mapnik.Layer('chicago')
    layer.datasource = zcsv
    layer.styles.append('My Style')
    styled_map.layers.append(layer)
    return m


def setup_highlight_styles(m):
    # highlight styles
    highlight_style = mapnik.Style()
    highlight_rule = mapnik.Rule()

    high_poly_symbolizer = mapnik.PolygonSymbolizer()
    high_poly_symbolizer.fill = mapnik.Color(high_fill)
    highlight_rule.symbols.append(high_poly_symbolizer)

    highlight_style.rules.append(highlight_rule)
    m.append_style('highlight',highlight_style)
    return m


def setup_highlight_layer(m,zip_code):
    highlighted_map = setup_highlight_styles(m)
    
    try:
        row = [x for x in zipcode_csv if x['ZIP'] == zip_code][0]
    except:
        import ipdb; ipdb.set_trace()
    data = ','.join(row.keys()) + '\r\n' + ','.join(['"' + row[k] + '"' for k in row.keys()]) 
    csv_data = mapnik.CSV(inline=data)
    layer = mapnik.Layer('c2')
    layer.datasource = csv_data
    layer.styles.append('highlight')
    highlighted_map.layers.append(layer)
    return m


def name_output_file(zip_code):
    return str(output_dir + zip_code + '.' + output_file_ext)


def export_map(m,zip_code):
    # export
    m.zoom_all()
    m.zoom_to_box(rebox(m.envelope(),offset))
    output_file_name = name_output_file(zip_code)
    mapnik.render_to_file(m,output_file_name,output_file_ext)
    return output_file_name


def rebox(box,pos):
    return mapnik.Box2d(box[0]-pos,box[1],box[2]-pos,box[3])

def markup_map(path,zipcode):
    x=10
    y=50
    img = Image.open(path)
    draw = ImageDraw.Draw(img)

    # hed
    draw.text((x,y),zipcode.zip_code,font=hed)
    size = draw.textsize(zipcode.zip_code,font=hed)
    y += size[1]*1.3
    
    # text writers return new coordinates
    x,y = complaint_text(draw,(x,y),zipcode.complaint_set.all())
    x,y = demo_text(draw,(x,y),zipcode)
    x,y = poverty_text(draw,(x,y),zipcode)
    source_text(draw,(x,y))
    img.save(path,optimize=True)


def complaint_text(draw,coords,num):
    # draws text and whitespace
    # returns new coords
    x = coords[0]
    y = coords[1]
    offset = x 

    num = str(len(num))
    
    size = draw_and_size(draw,(x,y),'Workers living here',light)
    y = add_a_line(y,size[1])

    size = draw_and_size(draw,(x,y),'filed',light)
    offset += size[0] + space
    
    size = draw_and_size(draw,(offset,y),num,bold)
    offset = offset + size[0] + space

    size = draw_and_size(draw,(offset,y),"wage complaints",light)
    y = add_a_line(y,size[1])

    size = draw_and_size(draw,(x,y),"since 2014.",light)
    y = add_a_line(y,size[1],multiple=2)

    return x,y
  

def demo_text(draw,coords,zipcode):
    x = coords[0]
    y = coords[1]
    text = "This ZIP code is "
    text_2 = ""
    text_3 = ""
    if zipcode.pct_blk >= 10 and zipcode.pct_hisp >=10:
        if zipcode.pct_blk > zipcode.pct_hisp:
            text_2 += str(zipcode.pct_blk) + ' percent black'
            text_3 += 'and ' + str(zipcode.pct_hisp) + ' percent Hispanic,'
        elif zipcode.pct_hisp >= zipcode.pct_blk:
            text_2 += str(zipcode.pct_hisp) + ' percent Hispanic'
            text_3 += 'and ' + str(zipcode.pct_blk) + ' percent black,'
    elif zipcode.pct_blk >= 10:
        text_2 += str(zipcode.pct_blk) + ' percent black,'
    elif zipcode.pct_hisp >= 10:
        text_2 += str(zipcode.pct_hisp) + ' percent Hispanic,'
    size = draw_and_size(draw,(x,y),text,light)
    
    y = add_a_line(y,size[1])
    size = draw_and_size(draw,(x,y),text_2,light)
    
    if text_3:
        y = add_a_line(y,size[1])
        size = draw_and_size(draw,(x,y),text_3,light)

    y = add_a_line(y,size[1],multiple=1.4)

    return x,y


def poverty_text(draw,coords,zipcode):
    x = coords[0]
    y = coords[1]
    text = "with a poverty rate of "
    text += str(zipcode.pct_poverty) + ' percent.'

    size = draw_and_size(draw,(x,y),text,light)

    return x,y


def source_text(draw,coords):
    x = coords[0]
    y = map_height - source_size * 1.8 
    text = "Sources: Illinois Department of Labor, U.S. Census Bureau"
    draw.text((x,y),text,font=source)


def add_a_line(y,height,multiple=1.4):
    return y + font_size * multiple


def draw_and_size(draw,coords,text,font):
    draw.text(coords,text,font=font)
    size = draw.textsize(text,font=font)
    print size, text
    return size


def optimize_map(path):
    pass


def gifify_map(path=gif_file_name):
    imgs = [Image.open(x) for x in glob.glob(output_dir + '*' + output_file_ext)]
    # TODO: get rid of extraneous gif creation steps
    im = Image.new('P',(map_width,map_height))

    im.save(path,format="GIF",save_all=True,append_images=imgs,duration=5000,loop=0)
    # TODO: get rid of hacky way to delete extraneous frame
    im = Image.open(path)
    im.seek(1)
    im.save(path,format="GIF",save_all=True,append_images=imgs,duration=5000,loop=0)
