#!/usr/bin/env python

# JLCPCB Parts MCP Server
# Created by @nvsofts
# 
# Data is provided from JLC PCB SMD Assembly Component Catalogue
# https://github.com/yaqwsx/jlcparts

import sqlite3
import json
import sys
import os
import urllib.request
import urllib.parse

from fastmcp import FastMCP, Image
from pydantic import BaseModel, Field, ConfigDict

# SQLite database path, please change this!
JLCPCB_DB_PATH = os.getenv('JLCPCB_DB_PATH')

if not JLCPCB_DB_PATH:
  print('Please set JLCPCB_DB_PATH environment value!', file=sys.stderr)
  sys.exit(1)

mcp = FastMCP('jlcpcb-parts')
conn = sqlite3.connect(JLCPCB_DB_PATH)

@mcp.tool()
def list_categories() -> str:
  """Get the list of JLCPCB part categories"""
  result = conn.execute('SELECT id,category,subcategory FROM categories')
  return "|Category ID|Category Name|Subcategory Name|\n|--|--|--|\n" + "\n".join(f'|{r[0]}|{r[1]}|{r[2]}|' for r in result)

@mcp.tool()
def list_manufacturers() -> str:
  """Get the list of JLCPCB part manufacturers"""
  result = conn.execute('SELECT id,name FROM manufacturers')
  return "|Manufacturer ID|Manufacturer Name|\n|--|--|\n" + "\n".join(f'|{r[0]}|{r[1]}|' for r in result)

@mcp.tool()
def get_category(category_id: int) -> str | None:
  """Get the category name and subcategory name from a category ID"""
  result = conn.execute('SELECT category,subcategory FROM categories WHERE id=?', [category_id]).fetchone()
  if result:
    return f'Category: {result[0]}, Subcategory: {result[1]}'
  else:
    return None

@mcp.tool()
def get_manufacturer(manufacturer_id: int) -> str | None:
  """Get the manufacturer name from a manufacturer ID"""
  result = conn.execute('SELECT name FROM manufacturers WHERE id=?', [manufacturer_id]).fetchone()
  if result:
    return result[0]
  else:
    return None

@mcp.tool()
def search_manufacturer(name: str) -> str | None:
  """Search manufacturers by partial name match and get their IDs"""
  result = conn.execute('SELECT id,name FROM manufacturers WHERE name LIKE ?', [f'%{name}%'])
  lines = []
  for r in result:
    lines.append(f'|{r[0]}|{r[1]}|')
  if lines:
    return "|Manufacturer ID|Manufacturer Name|\n" + "\n".join(lines)
  else:
    return None

'''
@mcp.tool()
def search_subcategories(name: str) -> str | None:
  """Search subcategories by name and get their category IDs"""
  result = conn.execute('SELECT id,subcategory FROM categories WHERE subcategory LIKE ?', [f'%{name}%'])
  lines = []
  for r in result:
    lines.append(f'|{r[0]}|{r[1]}|')
  if lines:
    return "|Category ID|Subcategory Name|\n" + "\n".join(lines)
  else:
    return None
'''

@mcp.tool()
def get_datasheet_url(part_id: int) -> str | None:
  """Get the datasheet URL for a JLCPCB part number (numeric part only)"""
  result = conn.execute('SELECT datasheet FROM components WHERE lcsc=?', [part_id]).fetchone()
  if result:
    return result[0]
  else:
    return None

@mcp.tool()
def get_part_image(part_id: int) -> Image | None:
  """Get the product image for a JLCPCB part number (numeric part only)"""
  try:
    result = conn.execute('SELECT extra FROM components WHERE lcsc=?', [part_id]).fetchone()
    if result:
      # Return the first image at medium quality
      images = json.loads(result[0])['images'][0]
      url = list(images.values())[int(len(images) / 2)]
      ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].replace('.', '')

      if ext == 'jpg':
        ext = 'jpeg'

      return Image(data=urllib.request.urlopen(url).read(), format=ext)
    else:
      return None
  except Exception as e:
    print(e, file=sys.stderr)
    return None

class SearchQuery(BaseModel):
  category_id: int = Field(ge=1, description='Valid category ID, obtain from the list_categories tool')
  manufacturer_id: int | None = Field(ge=1, default=None, description='Valid manufacturer ID, obtain from the search_manufacturer or list_manufacturers tools')
  manufacturer_pn: str = Field(default=None, description='Manufacturer part number, specified as a SQLite LIKE pattern')
  description: str = Field(default=None, description='Description text (not part number), specified as a SQLite LIKE pattern. OR searches or notation variations (e.g. presence/absence of hyphens) require separate searches')
  package: str = Field(default=None)
  is_basic_parts: bool | None = Field(default=None)
  is_preferred_parts: bool | None = Field(default=None)

  model_config = ConfigDict(
    title='Search Query',
    description='Model representing a search query, performs AND search across all fields'
  )

@mcp.tool()
def search_parts(search_query: SearchQuery) -> str:
  """Search for JLCPCB parts"""
  query = 'SELECT lcsc,category_id,manufacturer_id,mfr,basic,preferred,description,package,stock,price,extra FROM components WHERE '
  where_clauses = []
  params = []

  where_clauses.append('category_id=?')
  params.append(search_query.category_id)

  if search_query.manufacturer_id is not None:
    where_clauses.append('manufacturer_id=?')
    params.append(search_query.manufacturer_id)
  if search_query.manufacturer_pn:
    where_clauses.append('mfr LIKE ?')
    params.append(search_query.manufacturer_pn)
  if search_query.description:
    where_clauses.append('description LIKE ?')
    params.append(search_query.description)
  if search_query.package:
    where_clauses.append('package=?')
    params.append(search_query.package)

  if search_query.is_basic_parts is not None:
    where_clauses.append('basic=' + ('1' if search_query.is_basic_parts is True else '0'))
  if search_query.is_preferred_parts is not None:
    where_clauses.append('preferred=' + ('1' if search_query.is_preferred_parts is True else '0'))

  query += ' AND '.join(where_clauses)

  lines = []
  result = conn.execute(query, params)
  for r in result:
    # Convert price info to string
    price = []
    price_data = ''

    try:
      prices = json.loads(r[9])
      for p in prices:
        if p['qFrom'] is None:
          p['qFrom'] = ''
        if p['qTo'] is None:
          p['qTo'] = ''

        price.append(f"{p['qFrom']}-{p['qTo']} {p['price']}USD/pc")

      price_data = ', '.join(price)
    except Exception as e:
      print(e, file=sys.stderr)
      price_data = 'No info'

    # Convert attribute info to string
    chars = []
    char_data = ''
    try:
      extra = json.loads(r[10])
      for k, v in extra['attributes'].items():
        chars.append(f"{k}:{v}")

      char_data = ', '.join(chars)
    except Exception as e:
      print(e, file=sys.stderr)
      char_data = 'No info'

    lines.append(f'|{r[0]}|{r[1]}|{r[2]}|{r[3]}|{r[4]}|{r[5]}|{r[6]}|{r[7]}|{r[8]}|{price_data}|{char_data}|')

  return "|Part Number|Category ID|Manufacturer ID|Manufacturer PN|Basic Parts|Preferred Parts|Description|Package|Stock|Price|Attributes|\n|--|--|--|--|--|--|--|--|--|--|--|\n" + "\n".join(lines)

if __name__ == '__main__':
  mcp.run(transport='stdio')
