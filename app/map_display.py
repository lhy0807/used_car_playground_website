import json
from numba import jit, njit
from numba import types
from numba.typed import Dict
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
import time


def calc_max_min(pt, qt, codes_length):
    avg_points = pt
    quantity = qt
    max_points = 0
    min_points = 9
    max_quantity = 0
    min_quantity = 9
    for i in avg_points:
      avg_points[i] = avg_points[i] / codes_length
      if avg_points[i] > max_points:
        max_points = avg_points[i]
      if avg_points[i] < min_points:
        min_points = avg_points[i]

    for i in quantity:
      quantity[i] = quantity[i] / codes_length
      if quantity[i] > max_quantity:
        max_quantity = quantity[i]
      if quantity[i] < min_quantity:
        min_quantity = quantity[i]
    return [max_points, min_points, max_quantity, min_quantity]


def calculate_map(ny, codes):
    df = ny.copy()
    codes = json.loads(codes)
    avg_points = {}
    quantity = {}
    for code in codes:
      file_name = "geojson/{}.json".format(code)
      with open(file_name, 'r') as f:
        data = json.load(f)
        #sum up avg_points
        for i in data[0]:
          if i in avg_points:
            avg_points[i] = avg_points[i] + data[0][i]
          else:
            avg_points[i] = data[0][i]
        
        #sum up quantity
        for i in data[1]:
          if i in quantity:
            quantity[i] = quantity[i] + data[1][i]
          else:
            quantity[i] = data[1][i]

    #calculate avg of avg_points and quantity
    [max_points, min_points, max_quantity, min_quantity] = calc_max_min(avg_points, quantity, len(codes))
    
    #normalization again
    for i in avg_points:
      avg_points[i] = (avg_points[i]-min_points)/(max_points-min_points)
    for i in quantity:
      quantity[i] = (quantity[i]-min_quantity)/(max_quantity-min_quantity)

    for i in avg_points:
      df.at[i, 'Points'] = avg_points[i]

    for i in quantity:
      df.at[i, 'Quantity'] = quantity[i]
    return df