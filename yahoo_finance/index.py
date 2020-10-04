from bs4 import BeautifulSoup
import urllib.request
import time
import pprint
import numpy as np


class YahooFinance:
    YAHOO_FINANCE_DOMAIN = 'https://info.finance.yahoo.co.jp'
    EAST_FIRST_QUERY = 'kd=8&tm=d&vl=a&mk=3'
    def __init__(self):
        print('init')

    def get_brands(self, search_page_num, rate_threshold):
        stock_temp = []
        for i in range(search_page_num):
            url = '{}/ranking/?{}&p={}'.format(self.YAHOO_FINANCE_DOMAIN, self.EAST_FIRST_QUERY, (i+1))
            html = urllib.request.urlopen(url)
            soup = BeautifulSoup(html, 'lxml')
            stock_extract = [value.get_text() for value in soup.find_all('td')[:500]]
            stock_temp.extend(stock_extract)
            time.sleep(0.5)
        stock_temp = np.array(stock_temp)
        # 順位,コード,市場,名称,取引値,決算年月,1株配当,配当利回り,掲示板
        # rehape(x, y) => x行 x y列の2次元配列を作成
        stock = stock_temp.reshape(int(len(stock_temp)/10), 10)
        results = []
        for item in stock:
            row = {
                'rank': item[0],
                'code': item[1],
                'market': item[2],
                'name': item[3],
                'rate': item[8],
            }
            rate = float(row['rate'].strip('%'))
            # print('rate={}'.format(rate))
            if rate >= rate_threshold:
                results.append(row)
            else:
                pprint.pprint(row)
                break
        # print('applicable num=', len(results))
        results.sort(key=lambda x: int(x['rank']))
        return results
