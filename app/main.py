from random import random

import geopandas as gpd
from shapely.geometry import Point, Polygon
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import pandas as pd
import json
import time
import numpy as np
from io import BytesIO
import base64

from atlas_db import atlas
import pymongo

from flask import Flask, redirect, url_for, render_template, request, make_response
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
from flask_wtf.csrf import CSRFProtect

from map_display import *

def load_gpd():
  print("loading geojson file...")
  ny = gpd.read_file("ny.geojson")
  ny = ny.set_index('ZIP_CODE')
  print("finish loading geojson file...")
  return ny

ny = pd.DataFrame()
with ThreadPoolExecutor() as executor:
  load_gpd_thread = executor.submit(load_gpd)

print("connecting to mongodb...")
client = pymongo.MongoClient(atlas)
db = client["usedcar"]
usedcar = db.cargurus
modelcode = db.modelcode
print("mongodb connected!")
ny = load_gpd_thread.result()


app = Flask(__name__)
csrf = CSRFProtect(app)

def model_num_fn():
  print("get model number")
  return len(usedcar.distinct("model"))

def make_num_fn():
  print("get make number")
  # in modelcode
  # return len(modelcode.distinct("make"))
  # in usedcar and model code
  return len(modelcode.find({"code":{"$in":usedcar.distinct("model")} }).distinct("make"))

def year_span_fn():
  print("get year span")
  year = modelcode.distinct("year")
  span = min(year) + " - " + max(year)
  return span

def model_table_fn():
  print("get models")
  return list(modelcode.find({"code":{"$in":usedcar.distinct("model")}}))

def make_pie_fn():
#pie chart for each car make
  print("get pie chart data")
  make = modelcode.find({"code":{"$in":usedcar.distinct("model")} }).distinct("make")
  num = []
  for i in make:
    num.append(usedcar.find({"model":{"$in":modelcode.find({"make":i},{"code":1}).distinct("code") }}).count())
  #porpotion
  porp = []
  for i in num:
    ## this is just porportion
    porp.append(float(np.round((i/sum(num)*100), 2)))
    ## however, using pie chart we can use its number so hovering shows the amount 
    # porp.append(i)
  return [make, porp]

# for line chart, create _attr_ vs year
# options: 
#   avgerage price vs year for specific model/makes

def year_count_fn():
  print("start line chart count data")
  make = modelcode.find({"code":{"$in":usedcar.distinct("model")} }).distinct("make")
  year = modelcode.distinct("year")

  count_dict = dict()

  for m in make:
    count_each = []
    for y in year:
      total = usedcar.find({"model":{"$in":modelcode.find({"make":m}).distinct("code")}, "year":y}).count()
      count_each.append(total)

    # total_num.append(num_each)
    count_dict[m] = count_each

  # print(total_in_year)
  print("get line chart data")
  return [year, count_dict]

# assert that input string can be parsed to numeric (int/float)
# example: "27,995" -> "27995"
def parse(str):
  return float(str.replace(",",""))

def year_price_fn():
  print("Start line chart price data")
  make = modelcode.find({"code":{"$in":usedcar.distinct("model")} }).distinct("make")
  year = modelcode.distinct("year")

  price_dict = dict()

  for m in make:
    price_each = []
    for y in year:
      # total = usedcar.find({"model":{"$in":modelcode.find({"make":m}).distinct("code")}, "year":y}).count()
      price_list = list(usedcar.find({"model":{"$in":modelcode.find({"make":m}).distinct("code")}, "year":y}, { "price":1, "_id":0 }))
      if (len(price_list) == 0):
        avg = 0
      else:
        avg = sum( [ parse(p["price"]) for p in price_list ] )/len(price_list)
      price_each.append(avg)

    # total_num.append(num_each)
    price_dict[m] = price_each

  # print(total_in_year)
  print("get line chart price data")
  return [year, price_dict]

#init
model_num = 0
make_num = 0
year_span = ""
model_table = list()

pie_name = list()
pie_porp = list()
line_year = list()
line_count = list()
line_price = list()
#start threads
with ThreadPoolExecutor(multiprocessing.cpu_count()) as executor:
  model_num_thread = executor.submit(model_num_fn)
  make_num_thread = executor.submit(make_num_fn)
  year_span_thread = executor.submit(year_span_fn)
  model_table_thread = executor.submit(model_table_fn)
  make_pie_thread = executor.submit(make_pie_fn)

  # test line chat data
  year_count_thread = executor.submit(year_count_fn)
  year_price_thread = executor.submit(year_price_fn)

@app.route("/")
def index(df = ny):

  model_num = model_num_thread.result()
  make_num = make_num_thread.result()
  year_span = year_span_thread.result()
  model_table = model_table_thread.result()
  pie_name = make_pie_thread.result()[0]
  pie_porp = make_pie_thread.result()[1]
  line_year = year_count_thread.result()[0]
  line_count = year_count_thread.result()[1]
  line_price = year_price_thread.result()[1]

  return render_template('index.html', 
    model_num=model_num, 
    make_num=make_num,
    year_span=year_span,
    model_table=model_table,
    pie_name=json.dumps(pie_name), pie_porp=json.dumps(pie_porp), pie_name_no_json=pie_name,
    line_year=json.dumps(line_year), line_count=json.dumps(line_count),
    line_price=json.dumps(line_price) )

@csrf.exempt
@app.route("/model", methods=['POST'])
def model():
  code = request.form['code']
  resp = make_response(redirect(url_for('index')))
  resp.set_cookie('map_code',code)
  return resp

@app.route("/ajax/map")
def ajax(df = ny):
  #TODO:
  #Modify the algo here
  df = pd.DataFrame()
  codes = request.cookies.get("map_code")
  if codes != "" and codes is not None:
    df = calculate_map(ny, codes)
  else:
    df = ny.copy()
  fig, ax = plt.subplots(1, 1)
  df.plot(column="Points", missing_kwds={'color': 'lightgrey'}, ax=ax, legend=True)

  if codes != [] and codes is not None:
    if len(codes) == 1:
      info = modelcode.find({"code":code})[0]
      ax.set_title("New York State {} {} {}".format(info['year'],info['make'],info['model']))
    else:
      ax.set_title("Multiple models in New York State")
  else:
    ax.set_title("New York State Map")
  buf = BytesIO()
  fig.savefig(buf, format="png", dpi=1200)
  data = base64.b64encode(buf.getbuffer()).decode("ascii")
  #close figure
  plt.close(fig)
  return data

if __name__ == "__main__":
  app.run(host="0.0.0.0",port="5100")