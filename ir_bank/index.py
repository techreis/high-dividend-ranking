from bs4 import BeautifulSoup
import urllib.request
import time
import pprint
import re

class IRBank:
    IR_BANK_DOMAIN = 'https://irbank.net'


    def get_brands_index(self, brands):
        for brand in brands:
            url = '{}/{}'.format(self.IR_BANK_DOMAIN, brand['code'])
            html = urllib.request.urlopen(url)
            soup = BeautifulSoup(html, 'lxml')
            link = soup.find_all('a', limit=8)[7].get('href')
            brand['detail_link'] = '{}{}/results'.format(self.IR_BANK_DOMAIN, link)
            pprint.pprint(brand['detail_link'])
            time.sleep(0.5)
        return brands

    def get_brands_filtered_by_settings(self, brands):
        match_brands = []
        unmatch_brands = []
        for brand in brands:
            # 設定情報を取得
            settings = self.get_brand_settings(brand)
            if not settings:
                print('Settings Error')
                pprint.pprint(brand)
                continue
            brand['settings'] = settings
            # 税引前の配当利回りが3.75％以上
            # => すでに絞られている
            # PBRが高水準ではないこと(目安レンジ：0.5倍~1.5倍)
            PBR_RANGE = { 'from': 0.5, 'to': 1.5 }
            if settings['PBR'] < PBR_RANGE['from'] or settings['PBR'] > PBR_RANGE['to']:
                brand['unmatch_reason'] = 'PBR({})が{}以上{}以下でない'.format(settings['PBR'], PBR_RANGE['from'], PBR_RANGE['to'])
                unmatch_brands.append(brand)
                continue
            # 配当政策が分かりやすく、配当実績に納得できること
            # => 人間が判断するしかない
            # 配当継続力が高いこと(指標①で判定)
            CONTINUE_YEAR = 3.0
            if settings['dividend_sustainability'] < CONTINUE_YEAR:
                brand['unmatch_reason'] = '配当継続力({})が{}年未満'.format(settings['dividend_sustainability'], CONTINUE_YEAR)
                unmatch_brands.append(brand)
                continue
            # 売上高が長期的に上昇トレンド(上昇率は不問)
            ALLOW_DONW_NUM = 1
            if self.is_trend_raising(settings['amount_of_sales'], ALLOW_DONW_NUM) is False:
                brand['unmatch_reason'] = '売上高が{}回以上、下降トレンドになっている'.format(ALLOW_DONW_NUM)
                unmatch_brands.append(brand)
                continue
            # 売上高営業利益率が10％以上
            SALES_OPERATING_INCOME_RATE = 10.0
            if settings['sales_operating_income'] < SALES_OPERATING_INCOME_RATE:
                brand['unmatch_reason'] = '売上高営業利益({}%)が{}%未満'.format('a', 'b')
                unmatch_brands.append(brand)
                continue
            # EPSびBPSが長期的に上昇トレンド(上昇率は不問)
            ALLOW_EPS_TRAND_NUM = 1
            ALLOW_BPS_TRAND_NUM = 1
            is_EPS_rasing = self.is_trend_raising(settings['EPS'], ALLOW_EPS_TRAND_NUM)
            is_BPS_rasing = self.is_trend_raising(settings['BPS'], ALLOW_BPS_TRAND_NUM)
            if is_EPS_rasing is False or is_BPS_rasing is False:
                brand['unmatch_reason'] = ''
                if is_EPS_rasing is False:
                    brand['unmatch_reason'] += 'EPSが{}回以上、下降トレンドになっている。'.format(ALLOW_EPS_TRAND_NUM)
                if is_BPS_rasing is False:
                    brand['unmatch_reason'] += 'BPSが{}回以上、下降トレンドになっている'.format(ALLOW_BPS_TRAND_NUM)
                unmatch_brands.append(brand)
                continue
            # 自己資本比率が50％以上
            CAPITAL_ADEQUACY_RATIO = 50
            if settings['capital_adequacy_ratio'] < CAPITAL_ADEQUACY_RATIO:
                brand['unmatch_reason'] = '自己資本比率({}%)が{}%未満'.format('a', 'b')
                unmatch_brands.append(brand)
                continue
            print('this brand is useful')
            pprint.pprint(brand)
            match_brands.append(brand)
            time.sleep(0.5)
        results = {
            'match_brands': match_brands,
            'unmatch_brands': unmatch_brands,
        }
        return results


    # 判定に必要な情報郡を取得する
    def get_brand_settings(self, brand):
        pprint.pprint(brand)
        if 'detail_link' not in brand:
            return None
        html = urllib.request.urlopen(brand['detail_link'])
        soup = BeautifulSoup(html, 'lxml')
        groups = self.get_groups(soup)
        settings = {}
        # 株価純資産倍率
        settings['PBR'] = self.get_PBR(soup)
        # 配当継続力(年数)
        settings['dividend_sustainability'] = self.get_dividend_sustainability(soup, groups)
        # これまでの売上高一覧
        settings['amount_of_sales'] = self.get_amount_of_sales(soup)
        # 売上高営業利益率
        settings['sales_operating_income'] = self.get_sales_operating_income(soup, groups)
        # EPS（一株当たり利益）
        settings['EPS'] = self.get_EPS(soup, groups)
        # BPS（一株当たり純資産）
        settings['BPS'] = self.get_BPS(soup, groups)
        # 自己資本比率
        settings['capital_adequacy_ratio'] = self.get_capital_adequacy_ratio(soup, groups)
        return settings


    def get_PBR(self, ir_bank_soup):
        '''
        PBRが1倍未満であれば、1円の価値があるもの（あくまで、会計理論上の株主価値です）を1円未満で買えるということになります。
        将来的な成長を期待されている株式は、その期待が株価に織り込まれPBRが2倍や3倍になります。そのような株式を購入した場合、
        市場が期待する成長を裏切ってしまうと株価が大きく下落していきます。元本割れのリスクを抑えるためには、
        購入時の株価に過度な成長期待が織り込まれていないことが重要です。
        補足
        低PBR＝成長期待がない(人気がない)ということなので、増配チャンスが乏しい等のデメリットもあります。
        「将来、不測の事態により株の換金を迫られる事態にはならない」「絶対にキャピタルロスの状態では売らない」という自信があれば、
        実現しえない元本割れリスクを気にするよりも、増配し続けられる(減配しない)可能性の高い企業を選ぶべきです。
        この場合、PBRはそれほど重要な判断材料にはなりません。
        '''
        PBR = float(ir_bank_soup.select('#chb dl dd')[4].get_text().strip('倍'))
        return PBR


    # 配当継続力(年数)
    def get_dividend_sustainability(self, ir_bank_soup, groups):
        '''
        配当継続力(年数)が、相対的に高い(長い)企業を評価します。
        利益剰余金をベースにした年数
        ネットキャッシュをベースにした年数
        の２つをチェックします。
        補足説明：配当継続力(年数)とは？
        こびと株.comで採用しているオリジナルの指標です。ダイヤモンドザイで似たような考え方が紹介されていたことがあります。
        指標①：調整後利益剰余金÷配当総額
          ※調整後利益剰余金（期末利益剰余金－期末配当額）を原資として、
          最近の配当実績と同水準の配当を何年間継続することができるかを見ている指標です。
          会計理論に基づく配当可能年数です。
        指標②：修正ネットキャッシュ÷配当総額
          ※期末の修正ネットキャッシュ（現預金＋有価証券＋投資有価証券－有利子負債－期末配当額）を原資として、
          最近の配当実績と同水準の配当を何年間継続することができるかを見ている指標です。
          指標①よりも現実的な配当可能年数と言えます。
        '''
        retained_earnings_gid = self.get_group_id_by_name(groups, '利益剰余金')
        total_year_end_dividend_gid = self.get_group_id_by_name(groups, '剰余金の配当')
        if not retained_earnings_gid or not total_year_end_dividend_gid:
            if not retained_earnings_gid:
                print('retained_earnings_gid is unknown')
            if not total_year_end_dividend_gid:
                print('total_year_end_dividend_gid is unknown')
            return 'Unknown'
        # 期末利益剰余金
        # get_group_id_by_name
        retained_earnings = ir_bank_soup.select('#g_{} dl dd'.format(retained_earnings_gid))[-1].get_text()
        retained_earnings = self.parse_ja_num(retained_earnings)
        # 期末配当額
        total_year_end_dividend = ir_bank_soup.select('#g_{} dl dd'.format(total_year_end_dividend_gid))[-1].get_text()
        total_year_end_dividend = self.parse_ja_num(total_year_end_dividend)
        # 調整後利益剰余金
        adjusted_retained_earnings = retained_earnings - total_year_end_dividend
        # 総配当額
        # total_dividend = sum([self.parse_ja_num(dividend.get_text()) for dividend in ir_bank_soup.select('#g_{} dl dd'.format(total_year_end_dividend))])
        sarray = []
        for dividend in ir_bank_soup.select('#g_{} dl dd'.format(total_year_end_dividend_gid)):
            val = self.parse_ja_num(dividend.get_text())
            sarray.append(val)
        total_dividend = sum(sarray)
        # 配当継続力
        if total_dividend == 0:
            return 0
        dividend_sustainability = adjusted_retained_earnings / total_dividend
        return round(dividend_sustainability, 2)


    # 売上高が長期的に上昇トレンド(上昇率は不問)
    def get_amount_of_sales(self, ir_bank_soup):
        '''
        売上高は全ての源泉です。その企業が、社会にどれだけ必要とされているかの指標と言い換えることができます。
        長期的に安定して配当を得るためには、この指標の長期的な推移は必ず確認しなくてはいけません。
        '''
        return [self.parse_ja_num(sale.get_text()) for sale in ir_bank_soup.select('#g_1 dl dd')]


    #売上高営業利益率(営業利益率)を取得
    def get_sales_operating_income(self, ir_bank_soup, groups):
        '''
        営業利益とは、企業の本業の利益であり、ビジネスモデルをそのまま反映しているごまかしの効かない利益です。
        売上高に占める営業利益の割合が10％を超えている企業は、市場における競争的優位を持っている可能性が高いでしょう。
        '''
        sales_operating_income_gid = self.get_group_id_by_name(groups, '営業利益率')
        if not sales_operating_income_gid:
            return -1
        if len(ir_bank_soup.select('#g_{} dl dd'.format(sales_operating_income_gid))) == 0:
            return 0.0
        return float(ir_bank_soup.select('#g_{} dl dd'.format(sales_operating_income_gid))[-1].get_text().strip('%'))


    # EPS（一株当たり利益）
    def get_EPS(self, ir_bank_soup, groups):
        '''
        １株あたり純利益及び１株あたり純資産が長期的に上昇トレンド(上昇率は不問)
        １株あたり純利益と１株あたり純資産は、配当の源泉です。この２つが長期的に上昇トレンドにあるということは、
        長期的に安定した高配当を得るという意味でも、元本割れのリスクを抑えるという意味でも非常に重要です。
        '''
        EPS_gid = self.get_group_id_by_name(groups, 'EPS')
        if not EPS_gid:
            return -1
        return [float(eps.get_text().strip('円') if eps.get_text() != '-' else '0.0') for eps in ir_bank_soup.select('#g_{} dl dd'.format(EPS_gid))]


    # BPS（一株当たり純資産）
    def get_BPS(self, ir_bank_soup, groups):
        '''
        １株あたり純利益及び１株あたり純資産が長期的に上昇トレンド(上昇率は不問)
        １株あたり純利益と１株あたり純資産は、配当の源泉です。この２つが長期的に上昇トレンドにあるということは、
        長期的に安定した高配当を得るという意味でも、元本割れのリスクを抑えるという意味でも非常に重要です。
        '''
        BPS_gid = self.get_group_id_by_name(groups, 'BPS')
        if not BPS_gid:
            return -1
        return [float(bps.get_text().strip('円') if bps.get_text() != '-' else '0.0') for bps in ir_bank_soup.select('#g_{} dl dd'.format(BPS_gid))]


    def get_capital_adequacy_ratio(self, ir_bank_soup, groups):
        '''
        自己資本比率が50％以上
        自己資本比率は、財務の健全性（長期的な目線）を示す数値です。
        これが高ければ高いほど財務の安定性が高く配当余力もあると考えてよいでしょう。
        '''
        capital_adequacy_ratio_gid = self.get_group_id_by_name(groups, '自己資本比率')
        if not capital_adequacy_ratio_gid:
            return -1
        return float(ir_bank_soup.select('#g_{} dl dd'.format(capital_adequacy_ratio_gid))[-1].get_text().strip('%'))


    def parse_ja_num(self, number_text):
        man = 10000
        oku = man * man
        cho = oku * man
        sep = []
        cho_val = 0
        oku_val = 0
        man_val = 0
        if '兆' in number_text:
            sep = re.split('兆', number_text)
            cho_val = int(sep[0]) * cho
            number_text = sep[1]
        if '億' in number_text:
            sep = re.split('億', number_text)
            oku_val = int(sep[0]) * oku
            number_text = sep[1]
        if '万' in number_text:
            sep = re.split('万', number_text)
            man_val = int(sep[0]) * man
            number_text = sep[1]
        return cho_val + oku_val + man_val


    def is_trend_raising(self, num_array, down_num_threshold):
        down_num = 0
        for i in range(len(num_array)-1):
            if num_array[i+1] < num_array[i]:
                down_num += 1
        return True if down_num <= down_num_threshold else False


    def get_groups(self, ir_bank_soup):
        groups = []
        for i in range(50):
            title = ir_bank_soup.select_one('#g_{} > h2'.format(i+1))
            if not title:
                title = ''
            group = {
              'title': title,
              'gid': i+1,
            }
            groups.append(group)
        return groups


    def get_group_id_by_name(self, groups, name):
        for group in groups:
            if name in group['title']:
                return group['gid']
        return None
