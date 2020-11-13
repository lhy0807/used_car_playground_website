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
    porp.append(float(np.round((i/sum(num)*100), 2)))
  return [make, porp]

# for line chart, create _attr_ vs year
# options: 
#   avgerage price vs year for specific model/makes

def make_line_fn():
  print("start line chart data")
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


#init
model_num = 0
model_table = list()
pie_name = list()
pie_porp = list()
line_year = list()
line_data = list()
#start threads
with ThreadPoolExecutor(multiprocessing.cpu_count()) as executor:
  model_num_thread = executor.submit(model_num_fn)
  model_table_thread = executor.submit(model_table_fn)
  make_pie_thread = executor.submit(make_pie_fn)

  # test line chat data
  make_line_thread = executor.submit(make_line_fn)

@app.route("/")
def index(df = ny):

  model_num = model_num_thread.result()
  model_table = model_table_thread.result()
  pie_name = make_pie_thread.result()[0]
  pie_porp = make_pie_thread.result()[1]
  line_year = make_line_thread.result()[0]
  line_data = make_line_thread.result()[1]

  return render_template('index.html', model_num=model_num, model_table=model_table,
   pie_name=json.dumps(pie_name), pie_porp=json.dumps(pie_porp), pie_name_no_json=pie_name,
   line_year=json.dumps(line_year), line_data=json.dumps(line_data), line_year_no_json=line_year )

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