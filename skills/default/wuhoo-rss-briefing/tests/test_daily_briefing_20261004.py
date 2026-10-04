"""2026-10-04 修复回归: G7 释储 16 源跨榜合并 / DW India news 直播栏目 / IT之家铭凡·HKC 发售 / Apple TV F1 促销稿"""
from test_daily_briefing import NS

entity_key = NS['entity_key']
is_noise = NS['is_noise']
classify = NS['classify']


class TestG7OilReleaseMerge:
    """G7 释放1亿桶油储+美柴油出口禁令威胁: 此前无 entity 规则, 同事件拆占 财经TOP3+TOP5 与 宏观TOP2+TOP4+TOP5"""

    TITLES = [
        'G7决定释放1亿桶紧急油储，前20天先大规模投放柴油，美油一度跌超5%',
        '马克龙呼吁G7协调联合抛储，油价应声跳水，欧美股市集体上涨',
        'G7 to release 100 million barrels of oil and diesel after Trump export ban threat',
        'US pressures EU allies to release diesel stockpiles',
        '遏制燃料價格　G7同意4個月釋出1億桶柴油及原油',
        '歐盟呼籲G7共同合作  反對美柴油出口禁令威脅',
        '七国集团将释放至多1亿桶柴油和原油储备',
        '七国集团就推动主要炼油国家增产增加柴油供应达成一致',
        'U.S. and Allies Agree to Release Diesel Reserves as Prices Surge',
        'US backs down from fuel export ban threat as G7 agrees to release reserves',
        'Europe to release diesel reserves after Trump request',
        '特朗普：不会实施柴油出口禁令 欧洲将增加柴油供应',
        'G7會商壓低燃料價格　美國油價重挫5%',
    ]

    def test_all_map_to_same_key(self):
        for t in self.TITLES:
            assert entity_key(t, '') == 'g7_oil_release', t

    def test_non_g7_oil_news_not_merged(self):
        # IEA 常规释储回顾 (非本次 G7 事件, 无 G7/欧盟/马克龙/特朗普锚点)
        assert entity_key('国际能源署：已释放约3.25亿桶石油储备', '') is None
        # 马克龙国内政治稿 (无燃油锚点)
        assert entity_key('乱局 马克龙阵营即将黯然退场', '') is None
        # OPEC 增产 (无 G7/EU 锚点)
        assert entity_key('OPEC+ agrees to boost oil output in November', '') is None


class TestNoise20261004:

    def test_dw_india_live_blog(self):
        # 德国之声直播聚合博客栏目 (同类 australia news live)
        assert is_noise('India news: Delhi protesters turn up heat on election chief Hundreds have gathered in central Delhi')
        assert is_noise('India news: CJP announces October 10 march to Delhi')
        # 防误伤: 正常印度新闻标题不以 "India news:" 栏目头开头
        assert not is_noise('India and US sign critical minerals deal as Modi visits Washington')

    def test_ithome_consumer_launches(self):
        assert is_noise('铭凡 PCIe 扩展卡 ESP4B 上市，可提供 4 个 M.2 与 4 个 SATA 接口 MINISFORUM 现已在电商平台销售')
        assert is_noise('HKC“神盾 25Q360B”24.5 英寸显示器发售：2K 360Hz QD-Mini LED，2221 元')
        # 防误伤: HKC/铭凡 公司层新闻不误滤
        assert not is_noise('惠科HKC递交招股书 拟于深交所主板上市')

    def test_apple_tv_f1_promo(self):
        # 体育转播羊毛稿 (F1 词此前触发 06-03 hamilton 类噪声但本条漏网)
        assert is_noise('苹果 Apple TV 为美国用户免费直播 2026 F1 巴林大奖赛：无需订阅即可观看')
        # 防误伤: Apple TV+ 正常内容/价格新闻
        assert not is_noise('Apple TV+ raises subscription price to $12.99 amid streaming shakeout')


class TestNoise20261004B:

    def test_ithome_brand_sales_detail(self):
        assert is_noise('奇瑞汽车公布 9 月各品牌销量：主品牌超 19 万辆同比增长 17.2%，智界 5008 辆同比下降 36.5% 今日于港交所披露')
        assert is_noise('奇瑞风云 A9 九月交付超 7000 台，单月订单突破 2 万台 风云新能源今日宣布')
        # 防误伤: 真新闻——行业月度数据/车企财报
        assert not is_noise('比亚迪发布第三季度财报：营收2000亿元 同比增长24%')
        assert not is_noise('乘联分会：9 月 1-27 日乘用车零售 125.8 万辆同比下降 29%')

    def test_dw_solar_trend_feature(self):
        assert is_noise("Is solar energy for 'everyone, everywhere' possible by 2030? Prominent climate leaders have called")



class TestNoise20261004C:

    def test_techcrunch_event_promo(self):
        assert is_noise('Less than 24 hours to apply for a Side Event at Founder Summit 2026 The clock is almost out')
        # 防误伤: 峰会真新闻不受影响
        assert not is_noise('G7 summit leaders agree on joint action plan on energy security')
