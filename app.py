from yahoo_finance.index import YahooFinance
from ir_bank.index import IRBank
from spread_sheet_uploader.index import SpreadSheetUploader
import pprint
import csv
import datetime


class Main:
    yahoo_finance = YahooFinance()
    ir_bank = IRBank()
    sp_uploader = SpreadSheetUploader()


    def start(self):
        print('main thread start.')
        print('################################################')
        print('get brands in yahoo_finance filterd by rate 3.75')
        brands = self.yahoo_finance.get_brands(10, 3.75) #(page num, 配当利回りしきい値)
        SEARCH_NUM = 300

        brands = [brands[i] for i in range(SEARCH_NUM if len(brands) > SEARCH_NUM else len(brands))]
        print('################################################')
        print('get brands index in IRBank')
        brands = self.ir_bank.get_brands_index(brands)
        print('################################################')
        print('get filtered brands by kobito filters')
        print('################################################')
        print('results =======')
        results = self.ir_bank.get_brands_filtered_by_settings(brands)
        count = 1

        output_csv = []
        # ヘッダー追加
        output_csv.append(self.generate_header())
        count += 1
        print('match_brand:')
        output_csv.append(['match_brand:'])
        for brand in results['match_brands']:
            pprint.pprint(brand)
            output_csv.append(self.convert_brand_to_cols(count, brand))
            count += 1
        print('unmatch_brand:')
        output_csv.append(['unmatch_brand:'])
        count += 1
        for brand in results['unmatch_brands']:
            pprint.pprint(brand)
            output_csv.append(self.convert_brand_to_cols(count, brand))
            count += 1
        # csv出力
        dt_now = datetime.datetime.now()
        output_csv_file = 'ranking_{}.csv'.format(dt_now.strftime('%Y-%m-%d-%H%M%S'))
        with open(output_csv_file, 'w') as f:
            writer = csv.writer(f)
            writer.writerows(output_csv)
        self.sp_uploader.upload(output_csv_file)


    def generate_header(self):
        return [
            '#',
            '市場',
            '配当ランキング',
            '配当利回り',
            'コード',
            '企業名',
            'BPS',
            'EPS',
            'PBR',
            '売上高',
            '自己資本率',
            '配当継続力',
            '売上利益率',
            '不該当理由'
        ]


    def convert_brand_to_cols(self, index, brand):
        cols = []
        cols.append(index) # A列
        cols.append(brand['market']) # B列
        cols.append(brand['rank']) # C列
        cols.append(brand['rate']) # D列
        cols.append(brand['code']) # E列
        cols.append(brand['name']) # F列
        cols.append(brand['settings']['BPS'][-1]) # G列
        cols.append(brand['settings']['EPS'][-1]) # H列
        cols.append(brand['settings']['PBR']) # I列
        cols.append(brand['settings']['amount_of_sales'][-1]) # 売上高
        cols.append(brand['settings']['capital_adequacy_ratio']) # 自己資本率
        cols.append(brand['settings']['dividend_sustainability']) # 配当継続力
        cols.append(brand['settings']['sales_operating_income']) # 配当継続力
        if 'unmatch_reason' in brand:
            cols.append(brand['unmatch_reason'])
        return cols


# 実行
main = Main()
main.start()
