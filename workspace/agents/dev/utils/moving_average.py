import pandas as pd


def calculate_moving_averages(df: pd.DataFrame, 
                              price_col: str = 'close',
                              windows: tuple = (5, 20)) -> pd.DataFrame:
    """
    计算股票的移动平均线
    
    参数:
        df: DataFrame，包含股票价格数据，必须有日期索引或日期列
        price_col: str，价格列名（默认 'close'）
        windows: tuple，要计算的移动平均窗口（默认 5 日和 20 日）
    
    返回:
        DataFrame，包含原数据和移动平均线列
    
    示例:
        >>> df = pd.read_csv('stock.csv', parse_dates=['date'], index_col='date')
        >>> df = calculate_moving_averages(df)
    """
    # 创建结果 DataFrame（避免修改原数据）
    result = df.copy()
    
    # 为每个窗口计算移动平均
    for window in windows:
        ma_col = f'ma_{window}'
        result[ma_col] = result[price_col].rolling(window=window).mean()
    
    return result


# 使用示例
if __name__ == '__main__':
    # 生成示例数据
    dates = pd.date_range('2025-01-01', periods=30, freq='D')
    prices = [100 + i * 0.5 + (i % 7) * 2 for i in range(30)]
    
    df = pd.DataFrame({
        'date': dates,
        'close': prices
    })
    df.set_index('date', inplace=True)
    
    # 计算移动平均线
    df = calculate_moving_averages(df)
    
    print(df.head(25))
