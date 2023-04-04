
import machine
from bmp280 import BMX280
import neopixel
import network
import socket
import uselect
import time
import utime
import json

from AQI import AQI

# Set this to True if you have attached a BMP280 to the project
USING_BMP = True

# Configure BMP if appropriate
if USING_BMP:
  SDA_PIN = 8
  SCL_PIN = 9
  BMP_ADDR = 118
  BMP_FREQUENCY = 400000
  i2c = machine.I2C(0, sda=machine.Pin(SDA_PIN), scl=machine.Pin(SCL_PIN), freq=BMP_FREQUENCY)
  bmp = BMX280(i2c, BMP_ADDR)
  TEMPERATURE_FUDGE = 3.5

# Enter your WiFi SSID and PassKey here, and edit the IPv4 addresses
WIFI_SSID       = 'YOURSSID'
WIFI_PSK        = 'YOURPASSKEY'
WIFI_STATIC_IP  = '192.168.123.92'
WIFI_NET_MASK   = '255.255.255.0'
WIFI_GATEWAY    = '192.168.123.1'
WIFI_DNS        = '192.168.123.1'

# Where the web server should bind/listen, and how long should each poll wait
BIND_ADDR            = '0.0.0.0'
BIND_PORT            = 80
ACCEPT_QUEUE_DEPTH   = 3
RECEIVE_BUFFER_SIZE  = 1024
POLLER_TIMEOUT_MSEC  = 500
MINIMUM_PAUSE_SEC    = 1.0

# Configure the NeoPixel library
# Number of NeoPixels in the ring:
NEOPIXEL_COUNT = 8
# 0 == GP0 on the Raspberry Pi Pico W
PICO_GP0 = 0
NP = neopixel.NeoPixel(machine.Pin(PICO_GP0), NEOPIXEL_COUNT)

# Set the color of all of the pixels in the NeoPixel ring
def NP_Color (c):
  for i in range(NEOPIXEL_COUNT):
    NP[i] = (c[0], c[1], c[2])
  NP.write()
        
# Connect to the specified SSID with the specified pass-key
def connect (ssid, psk):  
  while True:
    try:
      NP_Color((0, 0, 32))
      wlan = network.WLAN(network.STA_IF)
      wlan.active(True)
      NP_Color((0, 0, 64))
      wlan.ifconfig((WIFI_STATIC_IP, WIFI_NET_MASK, WIFI_GATEWAY, WIFI_DNS))
      print('Connecting to SSID:', ssid)
      wlan.connect(ssid, psk)
      NP_Color((0, 0, 128))
      status = wlan.status()
      while status == network.STAT_CONNECTING:
        print('...')
        time.sleep(1.0)
        status = wlan.status()
      if status == network.STAT_GOT_IP:
        break
      elif status == network.STAT_IDLE or \
           status == network.STAT_WRONG_PASSWORD or \
           status == network.STAT_NO_AP_FOUND or \
           status == network.STAT_CONNECT_FAIL:
        print('Connection failed (1): ', str(wlan.status()))
      else:
        print('Connection failed (2): ', str(wlan.status()))
    except Exception as e:
      print('Connection failed (3): ', str(e))
    time.sleep(1.0)
  NP_Color((0, 0, 255))
  addr = wlan.ifconfig()[0]
  print('Connected to SSID: ', ssid)
  print('IP address:', addr)
  return addr
  
def listen (addr, port):
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
  sock.bind(addr)
  sock.listen(ACCEPT_QUEUE_DEPTH)
  print('Listening for TCP connections at: ' + str(addr))
  return sock

def sendfile (c, f):
  print('Sending file" "' + f + '"...')
  content = ''
  with open(f, 'rb') as fh:
    content = fh.read()
  filesize = len(content)
  print('Length: %d' % filesize)
  if f.endswith('.html'):
    c.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
  elif f.endswith('.css'):
    c.send('HTTP/1.0 200 OK\r\nContent-type: text/css\r\n\r\n')
  elif f.endswith('.ico'):
    c.send('HTTP/1.0 200 OK\r\nContent-type: image/x-icon\r\nContent-Length: %d\r\n\r\n' % filesize)
  elif f.endswith('.png'):
    c.send('HTTP/1.0 200 OK\r\nContent-type: image/png\r\nContent-Length: %d\r\n\r\n' % filesize)
  else:
    print('ERROR: Unknown file type for: "' + f + '", in sendfile')
    return
  c.write(content)

def respond (c, client_address, aqi, raw, smoothed, r, g, b, kPa, bar, mmHg, psi, celsius, fahrenheit):
  print('Connected to client from:', client_addr)
  request = c.recv(RECEIVE_BUFFER_SIZE).decode('utf-8')
  # print(request)
  tokens = request.split()
  method = tokens[0]
  path = tokens[1]
  print('\n\nMethod:  "' + method + '"')
  print('Path:    "' + path + '"')
  if path == '/' or path == 'site.html':
    sendfile(c, '/site.html')
  elif path == '/site.css':
    sendfile(c, path)
  elif path == '/favicon.ico':
    sendfile(c, path)
  elif path == '/logo.png':
    sendfile(c, path)
  else:
    j = dict()
    if path == '/json':
      particles = dict()
      particles['aqi'] = aqi
      particles['raw_ugm3'] = raw
      particles['smoothed_ugm3'] = smoothed
      j['particles'] = particles
      color = dict()
      color['red'] = r
      color['green'] = g
      color['blue'] = b
      j['color'] = color
      if USING_BMP:
        pressure = dict()
        pressure['kPa'] = kPa
        pressure['bar'] = bar
        pressure['mmHg'] = mmHg
        pressure['psi'] = psi
        j['pressure'] = pressure
        temperature = dict()
        temperature['celsius'] = celsius
        temperature['fahrenheit'] = fahrenheit
        j['temperature'] = temperature
    elif path == '/jsonhtml':
      j['aqi'] = aqi
      j['color'] = '#%02x%02x%02x' % (r, g, b)
      if USING_BMP:
        j['body'] = \
          '<p>Particles: %0.1f μg/m3</p><p> &nbsp; &nbsp; (%0.1f μg/m3 with smoothing)</p>\n' \
          '<p>Pressure: %0.3f kPa</p><p> &nbsp; &nbsp; (~%0.1f bar, ~%0.2f mmHg, ~%0.1f PSI)</p>\n' \
          '<p>Temperature: %0.1f&#8451,  %0.1f&#8457</p>\n' % \
          (raw, smoothed, kPa, bar, mmHg, psi, celsius, fahrenheit)
      else:
        j['body'] = \
          '<p>Particles: %0.1f μg/m3</p><p> &nbsp; &nbsp; (%0.1f μg/m3 with smoothing)</p>' % \
          (raw, smoothed)
    else:
      j['error'] = 'Bad URL: "' + path + '"'
    print(json.dumps(j))
    http_response = 'HTTP/1.0 200 OK\r\n\r\n' + json.dumps(j) + '\n'
    c.send(http_response)
  c.close()

class PicoWAQI:
    
  # WaveShare Dust Sensor configuration constants
  WAVESHARE_MAGIC_NUMBER_1   = 11
  WAVESHARE_MAGIC_NUMBER_2   = 0.2
  WAVESHARE_SAMPLE_DELAY_US  = 280
  WAVESHARE_ZERO_DUST_MV     = 400
  WAVESHARE_POWER_MV         = 3300
  
  # How many samples to use for smoothing
  SMOOTHING_BUFFER_SIZE      = 30
        
  # ADC(0) == A0 == GP26 on the Raspberry Pi Pico W
  PICO_GP26_A0 = 0

  # 22 == GP22 on the Raspberry Pi Pico W
  PICO_GP22 = 22

  # Initialize
  def __init__ (self):

    # Configure the WaveShare Dust Sensor "trigger" LED
    self.Trigger = machine.Pin(PicoWAQI.PICO_GP22, machine.Pin.OUT)

    # Configure the WaveShare Dust Sensor analog output pin
    self.DataIn = machine.ADC(PicoWAQI.PICO_GP26_A0)

    # Create a small buffer to smooth the output by averaging over a series of samples
    self.buff = [0] * PicoWAQI.SMOOTHING_BUFFER_SIZE
    self.sum = 0
    self.i = 0

  # Take one air quality sample
  def Sample(self):

    # Turn on the trigger LED
    self.Trigger.value(1)
    # Wait the appropriate time before taking the sample
    utime.sleep_us(PicoWAQI.WAVESHARE_SAMPLE_DELAY_US)
    # Actually take the sample
    sample_value = self.DataIn.read_u16()
    # Turn off the trigger LED
    self.Trigger.value(0)

    # If the sample is above the zero threshold, convert it into a particle density value
    voltage = (PicoWAQI.WAVESHARE_POWER_MV / 65536.0) * sample_value * PicoWAQI.WAVESHARE_MAGIC_NUMBER_1
    if voltage <= PicoWAQI.WAVESHARE_ZERO_DUST_MV:
      density_ug_m3 = 0
    else:
      voltage = voltage - PicoWAQI.WAVESHARE_ZERO_DUST_MV
      density_ug_m3 = voltage * PicoWAQI.WAVESHARE_MAGIC_NUMBER_2

    # Return the computed density value (in micrograms per cubic meter)
    return density_ug_m3
        
  # Return a smoothed value (arithmetic mean over the length of the circular buffer)
  def Buffer (self, incoming_value):      
    self.sum = self.sum - self.buff[self.i]
    self.buff[self.i] = incoming_value
    self.sum = self.sum + self.buff[self.i]
    buffer_mean = self.sum / float(len(self.buff))
    self.i += 1
    if self.i >= len(self.buff):
      self.i = 0
    return buffer_mean

if __name__ == "__main__":
  
  picowaqi = PicoWAQI()
  try:
    kPa = 0.0
    bar = 0.0
    mmHg = 0.0
    celsius = 0.0
    host_addr = connect(WIFI_SSID, WIFI_PSK)
    sock = listen(BIND_ADDR, BIND_PORT)
    poller = uselect.poll()
    poller.register(sock, uselect.POLLIN)
    while True:
      if USING_BMP:
        try:
          Pa = bmp.pressure
          celsius = bmp.temperature - TEMPERATURE_FUDGE
        except:
          Pa = 0
          celsius = 0
        kPa = Pa / 1000.0
        bar = Pa / 100000.0
        mmHg = Pa / 133.3224
        psi = Pa * 0.000145
        fahrenheit = (celsius * 9.0 / 5.0) + 32.0
      density_ug_m3 = picowaqi.Sample()
      smoothed_density_ug_m3 = picowaqi.Buffer(density_ug_m3)
      aqi = AQI.pm25_to_aqi(smoothed_density_ug_m3)
      (wr, wg, wb) = AQI.pm25_to_web_rgb(smoothed_density_ug_m3)
      (nr, ng, nb) = AQI.pm25_to_neopixel_rgb(smoothed_density_ug_m3)
      NP_Color(AQI.darken((nr, ng, nb), 2))
      p = poller.poll(POLLER_TIMEOUT_MSEC)
      if p:
        try:
          c, client_addr = sock.accept()
          respond(c, client_addr, aqi, density_ug_m3, smoothed_density_ug_m3, wr, wg, wb, kPa, bar, mmHg, psi, celsius, fahrenheit)
        except OSError as e:
          c.close()
          pass
      utime.sleep(MINIMUM_PAUSE_SEC)

  except Exception as e:
    print("Error:\n", str(e))
    NP_Color((0, 0, 0))
    print("Resetting microcontroller in 10 seconds...")
    time.sleep(10)
    print("Resetting NOW!")
    print()
    machine.reset()



