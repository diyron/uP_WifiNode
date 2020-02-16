####################################################################
# Thingsboard Demo - wifi IoT Node
# Use Micropython Firmware 1.12 from IDF3
####################################################################
from machine import Pin, I2C
from bme280 import *
import usocket
import ussl
import ujson
import ssd1306
import network
import time
####################################################################
# init variables
nodename = "BME280_ESP_03"
wifi_ssid = "CookieDough"
wifi_pw = "Gaeste2049"
ap_name = nodename
ap_pw = "enviam2019"
push_intervall = 60  # Sekunden
access_token = "v1yzNRexYSNXScEL7Q0E"  # BME280_ESP_03
raw_url = "https://tb.exceeding-solutions.de/api/v1/"
i = 0
####################################################################
# wifi objects
wifi_client = network.WLAN(network.STA_IF)  # creare client interface
wifi_ap = network.WLAN(network.AP_IF)  # create access-point interface

# general i2c object, sets pins
i2c = I2C(scl=Pin(22), sda=Pin(21))

# i2c oled 128x64
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# i2c bme280 temp, humi, pressure
bme280 = BME280(i2c=i2c)
values = bme280.values

# onboard led (blue)
onbled = Pin(2, Pin.OUT)

# set wifi-reset button pin, used with pull up
wifi_rst_btn = Pin(13, Pin.IN, Pin.PULL_UP)  # enable internal pull-up resistor
####################################################################


def https_post_thingsboard(url, kw_dict):
    port = 443
    method = "POST"
    proto, dummy, host, path = url.split("/", 3)
    data = ujson.dumps(kw_dict)  # dictionary to json

    # request
    ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)
    ai = ai[0]

    s = usocket.socket(ai[0], ai[1], ai[2])
    s.connect(ai[-1])

    oled.text('wrapping SSL...', 0, 30)
    oled.show()

    s = ussl.wrap_socket(s, server_hostname=host)

    s.write(b"%s /%s HTTP/1.1\r\n" % (method, path))
    s.write(b"Host: %s\r\n" % host)
    s.write(b"Content-Type: application/json\r\n")
    s.write(b"Content-Length: %d\r\n" % len(data))
    s.write(b"\r\n")
    s.write(data)

    # response
    # print("socket:", s)
    resp = s.readline()
    resp = resp.split(None, 2)
    status = int(resp[1])
    reason = "no reason"
    if len(resp) > 2:
        reason = resp[2].rstrip()
    while True:
        resp = s.readline()
        if not resp or resp == b"\r\n":
            break
        if resp.startswith(b"Transfer-Encoding:"):
            if b"chunked" in resp:
                raise ValueError("Unsupported " + resp)
        elif resp.startswith(b"Location:") and not 200 <= status <= 299:
            raise NotImplementedError("Redirects not yet supported")

    s.close()

    return status, reason


def update_display():
    v = bme280.values
    oled.fill(0)
    oled.text(nodename, 0, 0)
    oled.text('data push: ', 0, 55)
    oled.text(str(push_intervall - i), 80, 55)
    oled.text('sek', 100, 55)
    oled.text('Temp:', 0, 18)
    oled.text(str(v["Temperatur"]), 50, 18)
    oled.text(' C', 80, 18)
    oled.text('Humi:', 0, 28)
    oled.text(str(v["Luftfeuchte"]), 50, 28)
    oled.text(' %', 80, 28)
    oled.text('Pres:', 0, 38)
    oled.text(str(v["Luftdruck"]), 50, 38)
    oled.text(' hPa', 80, 38)
    oled.show()

####################################################################


def bootpage():
    icon = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 1, 0, 0, 0, 1, 1, 0],
        [1, 1, 1, 1, 0, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 1, 1, 1, 1, 1, 1, 1, 0],
        [0, 0, 1, 1, 1, 1, 1, 0, 0],
        [0, 0, 0, 1, 1, 1, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0],
    ]

    oled.fill(0)  # Clear the display
    for y, row in enumerate(icon):
        for x, c in enumerate(row):
            oled.pixel(x + 93, y + 23, c)

    oled.text('IoT with ', 20, 25)
    oled.show()


bootpage()
time.sleep(2)  # 2 seconds

####################################################################


def set_new_wifi():
    global wifi_client, wifi_ap, ap_name, ap_pw
    # when wifi is connected in client mode -> disconnect
    if wifi_client.isconnected():
        wifi_client.disconnect()
        wifi_client.active(False)

    wifi_ap.active(True)  # activate the interface
    wifi_ap.config(essid=ap_name, authmode=network.AUTH_WPA_WPA2_PSK, password=ap_pw)  # set the ESSID of the AP
    wifi_ip = wifi_ap.ifconfig()

    oled.fill(0)
    oled.text('Wifi AccessPoint ', 0, 0)
    oled.text('SSID: ', 0, 18)
    oled.text(ap_name, 0, 28)
    oled.text('IP: ', 0, 42)
    oled.text(wifi_ip[0], 0, 52)
    oled.show()

    from microWebSrv import MicroWebSrv

    # 1st define handler
    @MicroWebSrv.route('/config', 'POST')
    def _http_post_handler(httpClient, httpResponse):
        print("=== POST handler ===")
        global wifi_pw, wifi_ssid, access_token, push_intervall
        req = httpClient.ReadRequestContent(size=None)
        req = str(req, 'ascii')

        if ('wifi_ssid' in req) and ('wifi_pw' in req) and ('accesstok' in req) and ('pushintervall' in req):
            x1 = req.find("wifi_ssid")
            x2 = req.find("wifi_pw")
            x3 = req.find("accesstok")
            x4 = req.find("pushintervall")

            wifi_ssid = req[x1 + 10:x2 - 1]
            wifi_pw = req[x2 + 8:x3 - 1]
            access_token = req[x3 + 10:x4 - 1]
            push_intervall = int(req[x4 + 14:])

            file = open("wifi.txt", "w")
            file.write(wifi_ssid + '\n')
            file.write(wifi_pw + '\n')
            file.write(access_token + '\n')
            file.write(str(push_intervall) + '\n')
            file.close()

        content = """\
            <!DOCTYPE html><html><head><title>IoT-Node</title>
            <style>body {background-color: white; text-align: center; color: grey; 
            font-family: Tahoma,Verdana,Segoe,sans-serif; } </style> </head>
            <body><h1>environmental sensor node</h1><h2>wifi mode</h2><p>(by AL)</p>
            <p><strong>new settings</strong></p><br><br/> your are connected from IP: <strong> %s </strong>
            <br/><hr/>new wifi name (ssid): <strong> %s </strong><br/>new wifi password: <strong> %s </strong>
            <hr/>set ThingsBoard access token: <strong> %s </strong><br/>set pushintervall: <strong> %s </strong>
            <hr/><strong>restarting and connecting to wifi ... </strong><br/></body></html>
        """ % (httpClient.GetIPAddr(), wifi_ssid, wifi_pw, access_token, str(push_intervall))

        httpResponse.WriteResponseOk(headers=None, contentType="text/html", contentCharset="UTF-8", content=content)

        time.sleep(1)
        srv.Stop()
        wifi_ap.active(False)
        import machine
        machine.reset()

    print('starting webserver...')
    # 2nd start webserver
    srv = MicroWebSrv(webPath='www/')
    srv.Start(threaded=True)


try:
    f = open("wifi.txt", "r")
    wifi_ssid = f.readline()  # 1st line - ssid
    wifi_pw = f.readline()  # 2nd line - pw
    access_token = f.readline()  # 3rd line - thingsboard access token
    push_int_str = f.readline()  # 4th line -
    f.close()

    access_token = access_token[:-1]
    push_intervall = int(push_int_str[:-1])
    wifi_ssid = wifi_ssid[:-1]
    wifi_pw = wifi_pw[:-1]

    if wifi_ssid or wifi_pw or access_token or push_intervall is not None:

        onbled.on()  # on

        wifi_client.active(True)
        wifi_client.config(dhcp_hostname=nodename)
        wifi_client.connect(wifi_ssid, wifi_pw)

        oled.fill(0)
        oled.text('Wifi connecting ...', 0, 0)
        oled.show()

        onbled.off()  # off

        while True:
            time.sleep(1)
            # wifi reset
            if not wifi_rst_btn.value():
                print("reset button")
                try:
                    fh = open("wifi.txt", "r")
                    fh.close()
                    import os
                    os.remove('wifi.txt')
                except OSError:
                    pass
                set_new_wifi()
                break

            if i == push_intervall:
                i = 0

                onbled.on()  # on
                val = bme280.values

                # print("POST data")
                oled.fill(0)
                oled.text('POST...', 0, 15)
                oled.show()

                if wifi_client.isconnected():
                    url_tb = raw_url + access_token + "/telemetry"
                    ret = https_post_thingsboard(url=url_tb, kw_dict=val)  # 2nd Argument must be a dictionary
                    print("response", ret)
                    oled.text('POST done...', 0, 45)

                else:
                    print("no wifi")
                    oled.text('no wifi', 0, 45)

                oled.show()
                onbled.off()  # off
            else:
                i += 1

            update_display()

    else:
        set_new_wifi()

except OSError:
    set_new_wifi()
