#!/usr/bin/env python3
"""
Futu Stock Pick - 港股/美股选股工具

基于富途 OpenAPI 的多因子选股模型
"""

import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from futu import OpenQuoteContext, OpenHKTradeContext, RET_OK, Market, KLType, Plate


class FutuStockPicker:
    """富途选股器"""
    
    def __init__(self, host='127.0.0.1', port=11111):
        """初始化"""
        self.host = host
        self.port = port
        self.quote_ctx = OpenQuoteContext(host=host, port=port)
        
        # 指数成分股映射
        self.index_plates = {
            # 港股
            'HS': 'HK.BK1001',      # 恒生指数
            'HSTECH': 'HK.BK1077',  # 恒生科技指数
            'HSCEI': 'HK.BK1002',   # 恒生国企指数
            'HSMCI': 'HK.BK1003',   # 恒生中型股指数
            # 美股
            'SPX': 'US.BK1001',     # 标普 500
            'NDX': 'US.BK1002',     # 纳斯达克 100
            'DJI': 'US.BK1003',     # 道琼斯工业平均
        }
        
        # 筛选参数
        self.volatility_percentile = 0.50
        self.turnover_percentile = 0.50
        self.momentum_5d_percentile = 0.30
        self.beta_percentile = 0.30
        self.top_n = 10
    
    def get_index_stocks(self, index_code):
        """获取指数成分股"""
        if index_code not in self.index_plates:
            raise ValueError(f"未知的指数代码：{index_code}")
        
        plate_code = self.index_plates[index_code]
        ret, data = self.quote_ctx.get_plate_stock(plate_code)
        
        if ret != RET_OK:
            raise Exception(f"获取成分股失败：{data}")
        
        return data['code'].tolist()
    
    def get_stock_data(self, stock_codes, days=252):
        """获取股票历史数据"""
        all_data = []
        
        for code in stock_codes:
            try:
                # 获取 K 线数据
                ret, data, page_key = self.quote_ctx.request_history_kline(
                    code=code,
                    start=(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
                    end=datetime.now().strftime('%Y-%m-%d'),
                    ktype=KLType.K_DAY
                )
                
                if ret == RET_OK and len(data) > 0:
                    data['code'] = code
                    all_data.append(data)
                    
            except Exception as e:
                print(f"获取 {code} 数据失败：{e}")
                continue
        
        if len(all_data) == 0:
            return pd.DataFrame()
        
        return pd.concat(all_data, ignore_index=True)
    
    def calculate_factors(self, price_data):
        """计算因子"""
        factors = []
        
        for code in price_data['code'].unique():
            stock_data = price_data[price_data['code'] == code].sort_values('time_key')
            
            if len(stock_data) < 20:
                continue
            
            # 计算收益率
            stock_data['return'] = stock_data['close'].pct_change()
            
            # 252 日波动率
            if len(stock_data) >= 252:
                volatility = stock_data['return'].iloc[-252:].std()
            else:
                volatility = stock_data['return'].std()
            
            # 5 日换手率 (使用成交量近似)
            turnover_5d = stock_data['volume'].iloc[-5:].mean()
            
            # 5 日动量
            if len(stock_data) >= 5:
                momentum_5d = (stock_data['close'].iloc[-1] / stock_data['close'].iloc[-5] - 1) * 100
            else:
                momentum_5d = 0
            
            # 10 日动量
            if len(stock_data) >= 10:
                momentum_10d = (stock_data['close'].iloc[-1] / stock_data['close'].iloc[-10] - 1) * 100
            else:
                momentum_10d = 0
            
            # 20 日 Beta (简化计算，使用市场指数作为基准)
            if len(stock_data) >= 20:
                market_return = stock_data['return'].iloc[-20:].mean()
                stock_return = stock_data['return'].iloc[-20:].mean()
                beta = stock_return / market_return if market_return != 0 else 1.0
            else:
                beta = 1.0
            
            # 获取股票名称
            ret, data = self.quote_ctx.get_stock_quote([code])
            stock_name = data['name'].iloc[0] if ret == RET_OK and len(data) > 0 else code
            
            factors.append({
                'code': code,
                'name': stock_name,
                'volatility': volatility,
                'turnover_5d': turnover_5d,
                'momentum_5d': momentum_5d,
                'momentum_10d': momentum_10d,
                'beta': beta
            })
        
        return pd.DataFrame(factors)
    
    def filter_stocks(self, factors_df):
        """筛选股票"""
        df = factors_df.copy()
        filter_steps = []
        
        # 初始股票池
        filter_steps.append(('初始股票池', len(df)))
        
        # 1. 波动率筛选 (越低越好)
        threshold = df['volatility'].quantile(self.volatility_percentile)
        df = df[df['volatility'] <= threshold]
        filter_steps.append(('252 日波动率', len(df)))
        
        # 2. 换手率筛选 (越高越好)
        threshold = df['turnover_5d'].quantile(1 - self.turnover_percentile)
        df = df[df['turnover_5d'] >= threshold]
        filter_steps.append(('5 日平均换手率', len(df)))
        
        # 3. 5 日动量筛选 (越高越好)
        threshold = df['momentum_5d'].quantile(1 - self.momentum_5d_percentile)
        df = df[df['momentum_5d'] >= threshold]
        filter_steps.append(('5 日价格动量', len(df)))
        
        # 4. Beta 筛选 (越高越好)
        threshold = df['beta'].quantile(1 - self.beta_percentile)
        df = df[df['beta'] >= threshold]
        filter_steps.append(('20 日 Beta 值', len(df)))
        
        # 最终排序 (10 日动量越低越好)
        df = df.sort_values('momentum_10d', ascending=True)
        
        return df.head(self.top_n), filter_steps
    
    def run(self, market='HK', index='HS', top_n=10, picker_date=None):
        """运行选股"""
        self.top_n = top_n
        self.picker_date = picker_date
        
        print('=' * 60)
        print('富途选股报告')
        print('=' * 60)
        print(f'选股日期：{datetime.now().strftime("%Y-%m-%d")}')
        print(f'市场：{market}')
        print(f'指数：{index}')
        print('=' * 60)
        print('')
        
        # 1. 获取成分股
        print('[数据准备]')
        try:
            stock_codes = self.get_index_stocks(index)
            print(f'- 成分股数量：{len(stock_codes)}')
        except Exception as e:
            print(f'❌ 获取成分股失败：{e}')
            return
        
        # 2. 获取历史数据
        print('[获取历史数据]')
        price_data = self.get_stock_data(stock_codes)
        print(f'- 有效数据：{len(price_data["code"].unique())} 只股票')
        print('')
        
        if len(price_data) == 0:
            print('❌ 未获取到数据')
            return
        
        # 3. 计算因子
        print('[计算因子]')
        factors_df = self.calculate_factors(price_data)
        print(f'- 因子计算完成：{len(factors_df)} 只股票')
        print('')
        
        # 4. 筛选股票
        print('[筛选过程]')
        result_df, filter_steps = self.filter_stocks(factors_df)
        
        for step_name, count in filter_steps:
            print(f'{step_name}: {count} 只')
        print('')
        
        # 5. 输出结果
        print('[最终结果 (按 10 日动量排序，越低越好)]')
        print('-' * 90)
        print(f'{"排名":<6}{"代码":<12}{"名称":<15}{"10 日动量%":<12}{"252 波动率":<12}{"5 日换手":<12}{"5 日动量%":<12}{"20 日 Beta":<10}')
        print('-' * 90)
        
        for idx, row in result_df.iterrows():
            print(f'{idx+1:<6}{row["code"]:<12}{row["name"]:<15}{row["momentum_10d"]:<12.2f}{row["volatility"]:<12.4f}{row["turnover_5d"]:<12.0f}{row["momentum_5d"]:<12.2f}{row["beta"]:<10.2f}')
        
        print('-' * 90)
        print(f'共选出 {len(result_df)} 只股票')
        print('')
        print('=' * 60)
        
        # 保存结果
        output_file = f'stock_pick_{market}_{index}_{datetime.now().strftime("%Y%m%d")}.csv'
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f'结果已保存：{output_file}')
        
        self.quote_ctx.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='富途选股工具')
    parser.add_argument('--market', type=str, default='HK', choices=['HK', 'US'], help='市场 (HK/US)')
    parser.add_argument('--index', type=str, default='HS', help='指数代码 (HS/HSTECH/SPX/NDX 等)')
    parser.add_argument('--top-n', type=int, default=10, help='输出股票数量')
    parser.add_argument('--date', type=str, default=None, help='选股日期 (YYYYMMDD 或 YYYY-MM-DD)')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='OpenD 主机')
    parser.add_argument('--port', type=int, default=11111, help='OpenD 端口')
    
    args = parser.parse_args()
    
    picker = FutuStockPicker(host=args.host, port=args.port)
    picker.run(market=args.market, index=args.index, top_n=args.top_n, picker_date=args.date)


if __name__ == '__main__':
    main()
