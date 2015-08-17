import urllib, urllib2, cookielib, json
import re, time, logging

# import socks
# import socket
# socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9150)
# socket.socket = socks.socksocket

logging.basicConfig(level=logging.DEBUG)

class NoRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        infourl = urllib.addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
        infourl.code = code
        return infourl
    http_error_300 = http_error_301 = http_error_303 = http_error_307 = http_error_302

class FshareClient:
    LOGIN_URL = 'https://www.fshare.vn/login'
    DOWNLOAD_URL = 'https://www.fshare.vn/download/get'
    USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.10 Safari/537.36'

    def __init__(self):
        self._cookies = cookielib.CookieJar()
        self._opener = urllib2.build_opener(urllib2.HTTPSHandler(debuglevel=1), urllib2.HTTPCookieProcessor(self._cookies), NoRedirectHandler())
        self._opener.addheaders = [('user-agent', self.USER_AGENT)]
        pass

    def login(self, username, password):
        # init first request to check login
        req = urllib2.Request(self.LOGIN_URL)
        req.add_header('Referer', self.LOGIN_URL)
        resp = self._opener.open(req)

        # extract CSRF
        m = re.search('value="([^"]+)"\s+(?=name\="fs_csrf")', resp.read())
        self._csrf = m.group(1)

        # if not logged in, login first
        if resp.code == 200:
            # do login with extracted CSRF
            values = {'fs_csrf' : self._csrf,
                      'LoginForm[email]' : username,
                      'LoginForm[password]' : password,
                      'LoginForm[rememberMe]' : 1 }

            logging.debug('LOGGING IN :: Data to be sent [%s]', values)
            req = urllib2.Request(self.LOGIN_URL, urllib.urlencode(values))
            resp = self._opener.open(req)
            logging.info('##### LOGIN :: STATUS [%d] HEADERS [%s]', resp.code, resp.info())
            return (resp.code == 302) and (resp.info()['location']) and (resp.info()['location'].find('login') == -1)
        return True

    def process(self, file):
        logging.debug('##### GENERATING [%s]', file)
        # normalize file URL
        file = 'https://www.fshare.vn' + file[file.rfind('/file/'):]
        retry = 0
        while (retry < 3):
            # send request to file URL
            req = urllib2.Request(file)
            resp = self._opener.open(req)
            if resp.code == 302:
                # if we get a redirection, that means we're logged in
                # extract premium link from headers
                premium_link = resp.info()['location']
                logging.info('ORIGINAL [%s] >>> GENERATED [%s]', file, premium_link)
                return premium_link
            else:
                # sleep for 3 seconds and retry
                retry += 1
                logging.info('##### FAILED to get [%s], STATUS [%d], retry %d in 3 seconds #####', file, resp.code, retry)
                time.sleep(3)
            pass
        return 'FAILED: could not get link after 3 times. Please make sure file URL is correct and you could retry.'

    def get(self, file):
        logging.debug('##### GENERATING [%s]', file)
        
        # normalize file URL
        file = 'https://www.fshare.vn' + file[file.rfind('/file/'):]

        # send request to DOWNLOAD_URL with Referer as file URL
        req = urllib2.Request(self.DOWNLOAD_URL)
        req.add_header('referer', file)
        data = {
            'fs_csrf' : self._csrf,
            'DownloadForm[pwd]' : '',
            'ajax' : 'download-form'
        }
        resp = self._opener.open(req, urllib.urlencode(data))
        logging.info('##### [%s] DATA [%s] >>> STATUS [%d]', self.DOWNLOAD_URL, data, resp.code)
        # extract premium link from json
        premium_link = json.loads(resp)
        if premium_link['msg']:
            logging.info('##### %s >>> ERROR STATUS [%d] MSG [%s] #####', file, resp.code, premium_link['msg'])
            return premium_link['msg']
        logging.info('##### [%s] >>> GENERATED [%s]', file, premium_link['url'])
        return premium_link['url']