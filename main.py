#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#一个简单的Android远程管理软件

import os
import sys
import re
import time
import json
#import logging
import subprocess
import threading
import platform
from hashlib import md5
from random import randint
#from datetime import timedelta
from flask import Flask, request, render_template, json, jsonify, send_file


debug = False
usersFile = os.path.join(os.path.split(os.path.realpath(__file__))[0], '.users.conf')
confFile = os.path.join(os.path.split(os.path.realpath(__file__))[0], 'ARCT.conf')
#config = {'outtime':7, 'hitokoto':True, 'motd':False, 'refresh':5000}
#outtime:Token过期时间，单位为天
#hitokoto:启用一言
#motd:自定义欢迎语（False为关闭，str为开启，开启后忽略上面的设置自动关闭一言）
#refresh:主页信息刷新间隔时间，单位为毫秒

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
#app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=1)
#log = logging.getLogger('werkzeug')
#log.setLevel(logging.ERROR)

#全局变量
searchStatus = 0
recordFile = ''
photoFile = ''
locationResult = ''
downloadList = {}

###########前端请求###########

@app.route('/')
def index():
    return render_template('base.html')

@app.route('/signin', methods=['GET'])
def signin():
    return render_template('signin.html')
    #return app.send_static_file('signin.html')

@app.route('/home', methods=['GET'])
def home():
    if config['motd']:
        return render_template('home.html', refresh= config['refresh'], motd = config['motd'])
    elif config['hitokoto']:
        return render_template('home.html', refresh= config['refresh'], hitokoto = config['hitokoto'])
    else:
        return render_template('home.html', refresh= config['refresh'])

@app.route('/find', methods=['GET'])
def find():
    return render_template('find.html')

@app.route('/net', methods=['GET'])
def net():
    return render_template('net.html')

@app.route('/file', methods=['GET'])
def file():
    return render_template('file.html')

@app.route('/call', methods=['GET'])
def call():
    return render_template('call.html')

@app.route('/others', methods=['GET'])
def others():
    return render_template('others.html')

###########后端请求###########

@app.route('/check', methods=['POST'])
def check():
    if request.form['token'] in [users[x][1] for x in users]:
        if int(request.form['token'][:10]) > time.time() - 86400 * config['outtime']:
            return 'success'
        else:
            return 'timeout'
    else:
        return 'fault'

@app.route('/signin', methods=['POST'])
def signinCheck():
    username = request.form['username']
    password = request.form['password']
    if username in users:
        if password == users[username][0]:
            token = getToken(username, password)
            writeUser(username, password, token)
            return token
        else:
            return 'errorPassword'
    else:
        return 'errorUsername'

@app.route('/search', methods=['POST'])
def search():
    if checkToken(request.form['token']):
        global searchStatus
        searchStatus = 0
        #searchStatus：0-未启动 1-运行中 2-运行中但有错误 3-运行完成 4-运行完成但有错误
        run_search_thread = threading.Thread(target=run_search, args=(request.form,))
        run_search_thread.start()
        return 'success'
    else:
        return 'fault'

@app.route('/search-status', methods=['GET'])
def searchStatus():
    global searchStatus
    return str(searchStatus)

def run_search(args):
    global searchStatus
    searchStatus = 1
    if args['vibrate'] != 'true' and args['rang'] != 'true' and args['torch'] != 'true':
        searchStatus = 3
    else:
        if args['rang'] == 'true':
            rang_file = ''
            if os.path.isfile(config.get('rang', '')):
                rang_file = config.get('rang')
            else:
                if os.path.isdir('/system/media/audio/alarms'):
                    for f in os.listdir('/system/media/audio/alarms'):
                        if os.path.isfile('/system/media/audio/alarms/' + f):
                            rang_file = '/system/media/audio/alarms/' + f
                            break
            if rang_file == '':
                searchStatus = 2
        try:
            if args['rang'] == 'true':
                volume = subprocess.run(['termux-volume', 'music', '100'])
                if volume.returncode != 0:
                    searchStatus = 2
            i = 0
            while i <= int(args['time']):
                if args['vibrate'] == 'true':
                    vibrate = subprocess.run(['termux-vibrate', '-f', '-d', '1000'])
                    if vibrate.returncode != 0:
                        searchStatus = 2
                if args['rang'] == 'true':
                    playerinfo = subprocess.run(['termux-media-player', 'info'], capture_output=True)
                    if 'Playing' not in str(playerinfo.stdout):
                        player = subprocess.run(['termux-media-player', 'play', rang_file], capture_output=True)
                        if player.returncode != 0:
                            searchStatus = 2
                if args['torch'] == 'true':
                    torch = subprocess.run(['termux-torch', 'on'])
                    if torch.returncode != 0:
                        searchStatus = 2
                    time.sleep(0.5)
                    torch = subprocess.run(['termux-torch', 'off'])
                    if torch.returncode != 0:
                        searchStatus = 2
                    time.sleep(0.5)
                else:
                    time.sleep(1)
                i += 1
        finally:
            if args['torch'] == 'true':
                torch = subprocess.run(['termux-torch', 'off'])
            if args['rang'] == 'true':
                volume = subprocess.run(['termux-volume', 'music', '10'])
                player = subprocess.run(['termux-media-player', 'stop'], capture_output=True)
            if searchStatus == 1:
                searchStatus = 3
            else:
                searchStatus = 4

@app.route('/location', methods=['POST'])
def location():
    if checkToken(request.form['token']):
        global searchStatus
        searchStatus = 0
        run_search_location = threading.Thread(target=run_location, args=(request.form,))
        run_search_location.start()
        return 'success'
    else:
        return 'fault'

def run_location(args):
    global searchStatus
    searchStatus = 1
    if args['type'] == 'network':
        location = subprocess.run(['termux-location', '-p', 'network'], capture_output=True)
    elif args['type'] == 'gps':
        location = subprocess.run(['termux-location', '-p', 'gps'], capture_output=True)
    elif args['type'] == 'passive':
        location = subprocess.run(['termux-location', '-p', 'passive'], capture_output=True)
    if location.returncode == 0 and location.stdout != b'':
        global locationResult
        locationInfo = json.loads(location.stdout)
        locationResult = [locationInfo.get('latitude', 0), locationInfo.get('longitude', 0)]
        searchStatus = 3
    else:
        searchStatus = 4

@app.route('/location-status', methods=['GET'])
def locationStatus():
    global locationResult
    return jsonify(locationResult)

@app.route('/record', methods=['POST'])
def record():
    if checkToken(request.form['token']):
        global recordFile
        if request.form['type'] == 'run':
            if os.path.isfile(config.get('record', '')):
                recordFile = config.get('record')
            else:
                recordFile = '/sdcard/record/'
                if not os.path.isdir(recordFile):
                    os.mkdir(recordFile)
            recordFile = os.path.join(recordFile, time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime()) + '.mp3')
            record = subprocess.run(['termux-microphone-record', '-f', recordFile], capture_output=True)
            if record.returncode == 0:
                return '1'
            else:
                record = subprocess.run(['termux-microphone-record', '-q'], capture_output=True)
                return '4'
        elif request.form['type'] == 'stop':
            record = subprocess.run(['termux-microphone-record', '-q'], capture_output=True)
            if record.returncode == 0:
                return '3'
            else:
                return '4'
    else:
        return 'fault'

@app.route('/record', methods=['GET'])
def recordPlay():
    global recordFile
    return send_file(recordFile)

@app.route('/photo', methods=['POST'])
def photo():
    if checkToken(request.form['token']):
        global photoFile
        if os.path.isfile(config.get('photo', '')):
            photoFile = config.get('photo')
        else:
            photoFile = '/sdcard/Pictures/'
            if not os.path.isdir(photoFile):
                os.mkdir(photoFile)
        photoFile = os.path.join(photoFile, time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime()) + '.jpg')
        photo = subprocess.run(['termux-camera-photo', photoFile], capture_output=True)
        if photo.returncode == 0:
            i = 0
            while os.path.getsize(photoFile) == 0:
                os.remove(photoFile)
                photo = subprocess.run(['termux-camera-photo', photoFile], capture_output=True)
                i += 1
                if i == 5:
                    break
            if os.path.getsize(photoFile) == 0:
                return '4'
            else:
                return '3'
        else:
            return '4'
    else:
        return 'fault'

@app.route('/photo/<random>', methods=['GET'])
def photoShow(random):
    global photoFile
    return send_file(photoFile)

@app.route('/notification', methods=['POST'])
def notification():
    if checkToken(request.form['token']):
        notification = subprocess.run(['termux-notification', '-t', request.form['title'], '-c', request.form['content']], capture_output=True)
        if notification.returncode == 0:
            return '3'
        else:
            return '4'
    else:
        return 'fault'

@app.route('/wifi', methods=['POST'])
def wifi():
    if checkToken(request.form['token']):
        if request.form['type'] == 'info':
            if not debug:
                wifiScan = subprocess.run('termux-wifi-scaninfo', capture_output=True)
                if wifiScan.returncode == 0:
                    wifiScan = json.loads(wifiScan.stdout)
                    return jsonify(wifiScan)
                else:
                    print('Error:termux-wifi-scaninfo')
                    return 'error'
            else:
                with open('test/termux-wifi-scaninfo.txt') as f:
                    wifiScan = f.read()
                wifiScan = json.loads(wifiScan)
                return jsonify(wifiScan)
        elif request.form['type'] == 'on':
            wifiEnable = subprocess.run(['termux-wifi-enable', 'true'], capture_output=True)
            if wifiEnable.returncode == 0:
                return '3'
            else:
                return '4'
        elif request.form['type'] == 'off':
            wifiEnable = subprocess.run(['termux-wifi-enable', 'false'], capture_output=True)
            if wifiEnable.returncode == 0:
                return '3'
            else:
                return '4'
    else:
        return 'fault'

@app.route('/cell', methods=['POST'])
def cell():
    if checkToken(request.form['token']):
        if not debug:
            cellinfo = subprocess.run('termux-telephony-cellinfo', capture_output=True)
            if cellinfo.returncode == 0:
                cellinfo = json.loads(cellinfo.stdout)
                return jsonify(cellinfo)
            else:
                print('Error:termux-telephony-cellinfo')
                return 'error'
        else:
            with open('test/termux-telephony-cellinfo.txt') as f:
                cellinfo = f.read()
            cellinfo = json.loads(cellinfo)
            return jsonify(cellinfo)
    else:
        return 'fault'

@app.route('/file', methods=['POST'])
def getFile():
    if checkToken(request.form['token']):
        if os.path.isdir(request.form['file']):
            try:
                dirList = os.listdir(request.form['file'])
                dirList.sort(key=str.lower)
                fileList = []
                folderList = []
                for file in dirList:
                    if os.path.isdir(os.path.join(request.form['file'], file)):
                        folderList.append({'name':file, 'type':'folder'})
                    elif os.path.isfile(os.path.join(request.form['file'], file)):
                        fileList.append({'name':file, 'type':'file'})
            except:
                return 'error'
            else:
                return jsonify(folderList + fileList)
        elif os.path.isfile(request.form['file']):
            global downloadList
            id = getMD5(request.form['file'] + request.form['token'])
            downloadList[id] = request.form['file']
            return id
        else:
            return jsonify([])
    else:
        return 'fault'

@app.route('/download/<id>', methods=['GET'])
def download(id):
    global downloadList
    if id in downloadList:
        response = send_file(downloadList[id], as_attachment=True)
        #解决部分浏览器不支持Content-Disposition中的filename*导致含有中文的文件名显示不全的问题，将filename设置为和filename*相同的URL编码后的中文，如果文件名中不含中文，则无filename*，无法匹配，返回原文本
        response.headers["Content-Disposition"] = re.sub(r"filename=.*; filename\*=UTF-8''(.*)", r'filename="\1";' + r" filename\*=UTF-8''\1", response.headers["Content-Disposition"])
        return response
    else:
        return 'error'

@app.route('/upload', methods=['POST'])
def upload():
    if checkToken(request.form['token']):
        if os.path.isdir(request.form['path']):
            filePath = request.form['path'] + request.files['file'].filename
            if not os.path.isfile(filePath):
                try:
                    request.files['file'].save(filePath)
                except:
                    return 'errorSave'
                else:
                    return 'success'
            else:
                return 'errorExistence'
        else:
            return 'errorPath'
    else:
        return 'fault'

@app.route('/contact', methods=['POST'])
def getContact():
    if checkToken(request.form['token']):
        contactinfo = subprocess.run('termux-contact-list', capture_output=True)
        if contactinfo.returncode == 0:
            contactinfo = json.loads(contactinfo.stdout)
            #contactinfo.sort(key=lambda x: x['name'])
            return jsonify(contactinfo)
        else:
            print('Error:termux-contact-list')
            return 'error'
    else:
        return 'fault'

@app.route('/vcf', methods=['POST'])
def getVcf():
    if checkToken(request.form['token']):
        global downloadList
        contactinfo = subprocess.run('termux-contact-list', capture_output=True)
        if contactinfo.returncode == 0:
            contactinfo = json.loads(contactinfo.stdout)
            filename = '/sdcard/' + time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime()) + '.vcf'
            with open(filename, 'w') as f:
                for contact in contactinfo:
                    f.write('BEGIN:VCARD\nVERSION:3.0\nN:;' + contact['name'] + ';;;\nFN:' + contact['name'] + '\nTEL;TYPE=CELL:' + contact['number'] + '\nEND:VCARD\n')
            id = getMD5(filename + request.form['token'])
            downloadList[id] = filename
            return id
        else:
            print('Error:termux-contact-list')
            return 'error'
    else:
        return 'fault'

@app.route('/tts', methods=['GET'])
def ttsEngines():
    ttsEnginesinfo = subprocess.run('termux-tts-engines', capture_output=True)
    if ttsEnginesinfo.returncode == 0:
        ttsEnginesinfo = json.loads(ttsEnginesinfo.stdout)
        return jsonify(ttsEnginesinfo)
    else:
        print('Error:termux-tts-engines')
        return 'error'

@app.route('/tts', methods=['POST'])
def tts():
    if checkToken(request.form['token']):
        ttsSpeak = subprocess.run(['termux-tts-speak', '-e', request.form['engine'], '-s', request.form['stream'], request.form['text']], capture_output=True)
        if ttsSpeak.returncode == 0:
            return 'success'
        else:
            print('Error:termux-contact-list')
            return 'error'
    else:
        return 'fault'

@app.route('/call', methods=['POST'])
def telephoneCall():
    #不知道为什么不工作，经测试，直接在主函数中运行subprocess.run可以正常运行，但此处无法运行，使用多线程或多进程也都无法运行
    #猜测是因为只能在主线程中执行termux-telephony-call，但即使关闭Flask的多线程模式仍无法工作
    #返回值正常，参数传递也正常，但就是无法打开通话，故目前尚无法解决
    if checkToken(request.form['token']):
        print(request.form)
        phoneCall = subprocess.run(['termux-telephony-call', request.form['number']])
        if phoneCall.returncode == 0:
            return 'success'
        else:
            print('Error:termux-telephony-call')
            return 'error'
    else:
        return 'fault'

@app.route('/memory', methods=['GET'])
def memory():
    memory = getMemory()
    root = disk_usage('/')
    sdcard = disk_usage('/sdcard')
    MemPercent = usage_percent(int(memory['MemTotal'][:(len(memory['MemTotal'])-3)])-int(memory['MemAvailable'][:(len(memory['MemAvailable'])-3)]), int(memory['MemTotal'][:(len(memory['MemTotal'])-3)]), round_=1)
    SwapPercent= usage_percent(int(memory['SwapTotal'][:(len(memory['SwapTotal'])-3)])-int(memory['SwapFree'][:(len(memory['SwapFree'])-3)]), int(memory['SwapTotal'][:(len(memory['SwapTotal'])-3)]), round_=1)
    returninfo = {
        'MemTotal': memory['MemTotal'],
        'MemFree': memory['MemFree'],
        'MemAvailable': memory['MemAvailable'],
        'MemPercent': MemPercent,

        'SwapTotal': memory['SwapTotal'],
        'SwapFree': memory['SwapFree'],
        'SwapPercent': SwapPercent,

        'RootTotal': root['total'],
        'RootUsed': root['used'],
        'RootFree': root['free'],
        'RootPercent': root['percent'],

        'SdcardTotal': sdcard['total'],
        'SdcardUsed': sdcard['used'],
        'SdcardFree': sdcard['free'],
        'SdcardPercent': sdcard['percent'],
        }
    return jsonify(returninfo)

@app.route('/system', methods=['GET'])
def system():
    cpu = CPUinfo()
    returninfo = {
        'cpu-count': os.cpu_count(),
        'cpu-arch': cpu['Processor'],
        'cpu-hardware': cpu['Hardware'],
        'BogoMIPS': cpu['BogoMIPS'],

        'sys-arch': platform.machine(),
        'sys-bits': platform.architecture()[0],
        'sys-platform': platform.platform(),
        'sys-version': platform.version()
        }
    if not debug:
        camerainfo = subprocess.run('termux-camera-info', capture_output=True)
        if camerainfo.returncode == 0:
            camerainfo = json.loads(camerainfo.stdout)
            for camera in camerainfo:
                if 'facing' in camera:
                    if camera['facing'] == 'back':
                        returninfo['camera-back-focal'] = str(round(camera.get('focal_lengths', ['Unknow'])[0], 1)) + ' mm'
                        returninfo['camera-back-size'] = str(round(camera.get('physical_size').get('width'), 1)) + ' x ' + str(round(camera.get('physical_size').get('height'), 1)) + ' mm'
                    if camera['facing'] == 'front':
                        returninfo['camera-front-focal'] = str(round(camera.get('focal_lengths', ['Unknow'])[0], 1)) + ' mm'
                        returninfo['camera-front-size'] = str(round(camera.get('physical_size').get('width'), 1)) + ' x ' + str(round(camera.get('physical_size').get('height'), 1)) + ' mm'
        else:
            print('Error:termux-camera-info')
            camerainfo = camerainfo.stderr
    else:
        with open('test/termux-camera-info.txt') as f:
            camerainfo = json.loads(f.read())
        for camera in camerainfo:
            if 'facing' in camera:
                if camera['facing'] == 'back':
                    returninfo['camera-back-focal'] = str(round(camera.get('focal_lengths', ['Unknow'])[0], 1)) + ' mm'
                    returninfo['camera-back-size'] = str(round(camera.get('physical_size').get('width'), 1)) + ' x ' + str(round(camera.get('physical_size').get('height'), 1)) + ' mm'
                if camera['facing'] == 'front':
                    returninfo['camera-front-focal'] = str(round(camera.get('focal_lengths', ['Unknow'])[0], 1)) + ' mm'
                    returninfo['camera-front-size'] = str(round(camera.get('physical_size').get('width'), 1)) + ' x ' + str(round(camera.get('physical_size').get('height'), 1)) + ' mm'
    return jsonify(returninfo)

@app.route('/network', methods=['GET'])
def network():
    if not debug:
        deviceinfo = subprocess.run('termux-telephony-deviceinfo', capture_output=True)
        if deviceinfo.returncode == 0:
            deviceinfo = json.loads(deviceinfo.stdout)
        else:
            print('Error:termux-telephony-deviceinfo')
            deviceinfo = deviceinfo.stderr
        cellinfo = subprocess.run('termux-telephony-cellinfo', capture_output=True)
        if cellinfo.returncode == 0:
            cellinfo = json.loads(cellinfo.stdout)
        else:
            print('Error:termux-telephony-cellinfo')
            cellinfo = cellinfo.stderr
        wifiConnection = subprocess.run('termux-wifi-connectioninfo', capture_output=True)
        if wifiConnection.returncode == 0:
            wifiConnection = json.loads(wifiConnection.stdout)
        else:
            print('Error:termux-wifi-connectioninfo')
            wifiConnection = wifiConnection.stderr
    else:
        with open('test/termux-telephony-deviceinfo.txt') as f:
            deviceinfo = json.loads(f.read())
        with open('test/termux-telephony-cellinfo.txt') as f:
            cellinfo = json.loads(f.read())
        with open('test/termux-wifi-connectioninfo.txt') as f:
            wifiConnection = json.loads(f.read())
    for net in cellinfo:
        if net.get('registered', False):
            netdbm = net.get('dbm')
    returninfo = {
        'net-operator': deviceinfo['sim_operator_name'],
        'net-operator-code': deviceinfo['sim_operator'],
        'net-dbm': str(netdbm) + ' dBm',

        'wifi-state': wifiConnection['supplicant_state'],
        'wifi-ssid': wifiConnection['ssid'],
        'wifi-bssid': wifiConnection['bssid'],
        'wifi-ip': wifiConnection['ip'],
        'wifi-mac': wifiConnection['mac_address'],
        'wifi-frequency': str(wifiConnection['frequency_mhz']) + ' MHz',
        'wifi-speed': str(wifiConnection['link_speed_mbps']) + ' Mbps',
        'wifi-rssi': str(wifiConnection['rssi']) + ' dBm'
        }
    return jsonify(returninfo)

@app.route('/battery', methods=['GET'])
def battery():
    if not debug:
        batteryinfo = subprocess.run('termux-battery-status', capture_output=True)
        if batteryinfo.returncode == 0:
            batteryinfo = json.loads(batteryinfo.stdout)
        else:
            print('Error:termux-battery-status')
            batteryinfo = batteryinfo.stderr
    else:
        with open('test/termux-battery-status.txt') as f:
            batteryinfo = json.loads(f.read())
    returninfo = {
        'battery-health': batteryinfo['health'],
        'battery-percentage': str(batteryinfo['percentage']) + ' %',
        'battery-status': batteryinfo['status'],
        'battery-temperature': str(round(batteryinfo['temperature'], 1)) + '℃'
        }
    return jsonify(returninfo)

@app.route('/quit', methods=['POST'])
def quit():
    if checkToken(request.form['token']):
        print('Goodbye!')
        os._exit(0)
    else:
        return 'fault'

def getToken(username, password):
    return str(int(time.time())) + getMD5(str(int(time.time()))+getMD5(username)+getMD5(password)+str(randint(0,99999)))

def getMD5(str):
    return md5(str.encode(encoding='UTF-8')).hexdigest()

def writeUser(username, password, token):
    users[username][0] = password
    users[username][1] = token
    with open(usersFile, 'w') as f:
        json.dump(users, f, sort_keys=True, indent=4)

def checkToken(token):
    if token in [users[x][1] for x in users]:
        if int(token[:10]) > time.time() - 86400 * config['outtime']:
            return True
        else:
            return False
    else:
        return False

def getMemory():
    meminfo = {}
    with open('/proc/meminfo', 'r') as f:
        for line in f:
            meminfo[line.split(':')[0]] = line.split(':')[1].strip()
    return meminfo

def CPUinfo():
    CPUinfo = {'BogoMIPS':''}
    with open('/proc/cpuinfo') as f:
        for line in f:
            if line.strip():
                if len(line.split(':')) == 2:
                    if line.split(':')[0].strip() == 'Processor' or line.split(':')[0].strip() == 'Hardware':
                        CPUinfo[line.split(':')[0].strip()] = line.split(':')[1].strip()
                    if line.split(':')[0].strip() == 'BogoMIPS':
                        CPUinfo['BogoMIPS'] += ' ' + line.split(':')[1].strip()
    return CPUinfo

def disk_usage(path):
    #From psutil
    st = os.statvfs(path)
    total = (st.f_blocks * st.f_frsize)
    avail_to_root = (st.f_bfree * st.f_frsize)
    avail_to_user = (st.f_bavail * st.f_frsize)
    used = (total - avail_to_root)
    total_user = used + avail_to_user
    usage_percent_user = usage_percent(used, total_user, round_=1)
    return {'total': total, 'used': used, 'free': avail_to_user, 'percent': usage_percent_user}

def usage_percent(used, total, round_=None):
    """Calculate percentage usage of 'used' against 'total'."""
    try:
        ret = (float(used) / total) * 100
    except ZeroDivisionError:
        return 0.0
    else:
        if round_ is not None:
            ret = round(ret, round_)
        return ret

if __name__ == '__main__':
    with open(usersFile, 'r') as f:
        users = json.load(f)
    with open(confFile, 'r') as f:
        config = json.load(f)
    if len(sys.argv) == 1:
        app.run(threaded = True, host=config.get('host', '0.0.0.0'), port=config.get('port', 8080))
        #app.run(threaded = False)
        #app.run(threaded = False, processes=4)
    elif len(sys.argv) == 2:
        if sys.argv[1] == 'help' or sys.argv[1] == '-help' or sys.argv[1] == '--help' or sys.argv[1] == 'h' or sys.argv[1] == '-h':
            print('''
Usage: arct [OPTION]
远程管理您的手机，部分功能依赖于Termux-API软件包。

OPTIONS:
    无参数 启动 Web 服务器
    help 显示此帮助
    add [Username] [Password] 添加新用户
    claen [Username] 撤回当前登录此用户的终端的登录许可
    remove [Username] 删除用户
    list 列出所有用户

Name    : ARCT - Android Remote Control Tool
Version : 1.0
Date    : 2020-04-26
Author  : St1020
License : GNU General Public License, version 3 (GPL-3.0)

Copyright (C)2020 St1020.
            ''')
        elif sys.argv[1] == 'list':
            for user in users:
                print('用户名：' + user + '\n密码MD5：' + users[user][0] + '\nToken：' + users[user][1] + '\n')
        else:
            print('参数不正确！输入 arct help 查看帮助')
    elif len(sys.argv) == 3:
        if sys.argv[1] == 'remove':
            if sys.argv[2] in users:
                users.pop(sys.argv[2])
                with open(usersFile, 'w') as f:
                    json.dump(users, f, sort_keys=True, indent=4)
                print('删除完成！')
            else:
                print('用户不存在！输入 arct list 列出所有用户')
        elif sys.argv[1] == 'clean':
            if sys.argv[2] in users:
                users[sys.argv[2]][1] = getToken(sys.argv[2], users[sys.argv[2]][0])
                with open(usersFile, 'w') as f:
                    json.dump(users, f, sort_keys=True, indent=4)
                print('已撤回登录授权！')
            else:
                print('用户不存在！输入 arct list 列出所有用户')
        else:
            print('参数不正确！输入 arct help 查看帮助')
    elif len(sys.argv) == 4:
        if sys.argv[1] == 'add':
            users[sys.argv[2]] = [0, 0]
            writeUser(sys.argv[2], getMD5(sys.argv[3]), getToken(sys.argv[2], getMD5(sys.argv[3])))
            print('添加用户完成！')
        else:
            print('参数不正确！输入 arct help 查看帮助')
    else:
        print('参数不正确！输入 arct help 查看帮助')