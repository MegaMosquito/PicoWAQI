#
# class AQI
#
# A class with static utility functions for the computation of the
# United States Environment Protection Agency "Air Quality Index"
# values and the corresponding colors, given particle density values.
# Functions are provided to return the numeric AQI value, and to
# return color values appropriate for web page clarity or for
# NeoPixel clarity, as well as a dimming function for NeoPixels.
#

class AQI:

  # Global table of AQI breakpoints for Web Pages
  # Official website uses the RGB colors below. For clarity on web pages,
  # I added some distinction at the high level.
  #     104, 223,  67
  #     255, 254,  84
  #     240, 132,  50
  #     235,  50,  35
  #     133,  70, 147
  #     115,  20,  37
  # [        0,       1,    2,   3,   4,   5,   6 ]
  # [      bot,     top,  min, max,   r,   g,   b ]
  # [---------------------------------------------]
  WEB_COLORS = [
    [      0.0,     0.0,    0,   0, 104, 223,  67 ],
    [      0.0,    12.1,    0,  50, 104, 223,  67 ],
    [     12.1,    35.5,   51, 100, 104, 223,  67 ],
    [     35.5,    55.5,  101, 150, 255, 254,  84 ],
    [     55.5,   150.5,  151, 200, 240, 132,  50 ],
    [    150.5,   250.5,  201, 300, 235,  50,  35 ],
    [    250.5,   350.5,  301, 400, 133,  70, 147 ],
    [    350.5,   500.5,  401, 500, 115,  20,  37 ],
    [    500.5, 99999.9,  501, 999,  57,  10,  18 ],
    [  99999.9,100000.0,  999,1000,   0,   0,   0 ]
  ]

  # Global table of AQI breakpoints for NeoPixels
  # Official website uses these RGB colors, but some of these don't
  # work well on NeoPixels, so I made some changes.
  #     104, 223,  67
  #     255, 254,  84
  #     240, 132,  50
  #     235,  50,  35
  #     133,  70, 147
  #     115,  20,  37
  # So the values in the table below are tweaked a bit for NeoPixels
  # [        0,       1,    2,   3,   4,   5,   6 ]
  # [      bot,     top,  min, max,   r,   g,   b ]
  # [---------------------------------------------]
  NEOPIXEL_COLORS = [
    [      0.0,     0.0,    0,   0,   0, 128,   0 ],
    [      0.0,    12.1,    0,  50,   0, 128,   0 ],
    [     12.1,    35.5,   51, 100,  64,  64,   0 ],
    [     35.5,    55.5,  101, 150, 192,  64,   0 ],
    [     55.5,   150.5,  151, 200, 192,   0,   0 ],
    [    150.5,   250.5,  201, 300, 192,   0,  16 ],
    [    250.5,   350.5,  301, 400,  24,   0,   4 ],
    [    350.5,   500.5,  401, 500,  24,   0,   4 ],
    [    500.5, 99999.9,  501, 999,  24,   0,   4 ],
    [  99999.9,100000.0,  999,1000,  24,   0,   4 ]
  ]

  # Given a PM2.5 value, return the table row number that is applicable:
  @staticmethod
  def pm25_to_row_num(pm25):
    # Never return first or last row of WEB_COLORS table
    for i in range(1, len(AQI.WEB_COLORS) - 1):
      row = AQI.WEB_COLORS[i]
      if pm25 <= row[1]:
        return i
    # Never return first or last row of WEB_COLORS table
    return len(AQI.WEB_COLORS) - 2

  # Given a PM2.5 value, return the applicable numerical AQI value
  @staticmethod
  def pm25_to_aqi(pm25):
    i = AQI.pm25_to_row_num(pm25)
    row = AQI.WEB_COLORS[i]
    rb = row[0]
    rt = row[1]
    f = ((1.0 * pm25) - rb) / (rt - rb)
    mn = row[2]
    mx = row[3]
    return int(mn + f * (mx - mn))

  # Given a PM2.5 value, return interpolated AQI neopixel color (r,g,b)
  @staticmethod
  def pm25_to_neopixel_rgb(pm25):
    if pm25 < 0:
      return (0, 0, 0)
    i = AQI.pm25_to_row_num(pm25)
    row = AQI.NEOPIXEL_COLORS[i]
    rb = row[0]
    rt = row[1]
    f = ((1.0 * pm25) - rb) / (rt - rb)
    r1= row[4]
    g1= row[5]
    b1= row[6]
    row = AQI.NEOPIXEL_COLORS[i + 1]
    r2= row[4]
    g2= row[5]
    b2= row[6]
    r = r1 + f * (r2 - r1)
    g = g1 + f * (g2 - g1)
    b = b1 + f * (b2 - b1)
    return (int(r), int(g), int(b))

  # Given a PM2.5 value, return the interpolated AQI web page color (r,g,b)
  @staticmethod
  def pm25_to_web_rgb(pm25):
    if pm25 < 0:
      return (0, 0, 0)
    i = AQI.pm25_to_row_num(pm25)
    row = AQI.WEB_COLORS[i]
    rb = row[0]
    rt = row[1]
    f = ((1.0 * pm25) - rb) / (rt - rb)
    r1= row[4]
    g1= row[5]
    b1= row[6]
    row = AQI.WEB_COLORS[i + 1]
    r2= row[4]
    g2= row[5]
    b2= row[6]
    r = r1 + f * (r2 - r1)
    g = g1 + f * (g2 - g1)
    b = b1 + f * (b2 - b1)
    return (int(r), int(g), int(b))

  # Return a new RGB value "dimmed" by the divisor passed (for NeoPixels)
  @staticmethod
  def darken(rgb, divisor):
    r = int(rgb[0] / divisor)
    g = int(rgb[1] / divisor)
    b = int(rgb[2] / divisor)
    return (r, g, b)

