#!/usr/bin/env python3.11
"""
资金管理模块

提供购买建议：
- 预算分配
- 定投策略
- 风险控制
- Kelly 公式变体（娱乐版）
"""


def calculate_budget(monthly_budget: float, draws_per_month: float = 12) -> dict:
    """计算每期预算分配
    
    Args:
        monthly_budget: 月预算（元）
        draws_per_month: 每月开奖次数（双色球约 12 次）
    
    Returns:
        预算分配建议
    """
    per_draw = monthly_budget / draws_per_month
    notes_per_draw = int(per_draw / 2)  # 每注 2 元
    
    if notes_per_draw < 1:
        notes_per_draw = 1
        recommended_budget = notes_per_draw * 2 * draws_per_month
    else:
        recommended_budget = notes_per_draw * 2 * draws_per_month
    
    return {
        "monthly_budget": monthly_budget,
        "actual_monthly_cost": recommended_budget,
        "per_draw_budget": round(per_draw, 2),
        "notes_per_draw": notes_per_draw,
        "cost_per_note": 2,
        "draws_per_month": draws_per_month,
    }


def fixed_investment_strategy(monthly_budget: float, months: int = 12) -> dict:
    """定投策略分析
    
    Args:
        monthly_budget: 月预算
        months: 定投月数
    
    Returns:
        定投分析
    """
    budget = calculate_budget(monthly_budget)
    total_cost = budget["actual_monthly_cost"] * months
    total_draws = budget["draws_per_month"] * months
    total_notes = budget["notes_per_draw"] * total_draws
    
    # 六等奖概率约 1/16（蓝球命中）
    # 每期 n 注，至少中一注六等奖的概率
    p_blue_miss = 15/16
    p_at_least_one_sixth = 1 - p_blue_miss ** budget["notes_per_draw"]
    
    # 12期内至少中一次六等奖的概率
    p_never_sixth = (1 - p_at_least_one_sixth) ** months
    p_at_least_once = 1 - p_never_sixth
    
    return {
        "monthly_budget": monthly_budget,
        "months": months,
        "total_cost": total_cost,
        "total_draws": total_draws,
        "total_notes": total_notes,
        "notes_per_draw": budget["notes_per_draw"],
        "sixth_prize_prob_per_draw": round(p_at_least_one_sixth * 100, 1),
        "sixth_prize_prob_in_period": round(p_at_least_once * 100, 1),
        "expected_sixth_prizes": round(total_notes * (1/16), 0),
        "expected_loss": round(total_cost * 0.5, 0),  # 约 50% 返还率
    }


def risk_assessment(budget: float) -> dict:
    """风险评估
    
    Args:
        budget: 月预算
    
    Returns:
        风险评估结果
    """
    # 建议：彩票支出不超过月收入的 2%
    recommended_max_income_ratio = 0.02
    
    # 风险等级
    if budget <= 20:
        risk_level = "低风险"
        risk_desc = "小额娱乐支出，影响可控"
    elif budget <= 50:
        risk_level = "中低风险"
        risk_desc = "适度娱乐，建议不要超过月收入 2%"
    elif budget <= 100:
        risk_level = "中等风险"
        risk_desc = "支出较高，请确保不影响正常生活"
    elif budget <= 200:
        risk_level = "高风险"
        risk_desc = "支出偏高，建议降低预算"
    else:
        risk_level = "高风险 ⚠️"
        risk_desc = "支出过高，强烈建议降低预算"
    
    return {
        "monthly_budget": budget,
        "risk_level": risk_level,
        "risk_desc": risk_desc,
        "recommendation": "彩票为负期望值游戏，请理性购买，量力而行"
    }


def generate_advice(monthly_budget: float = 20, months: int = 12) -> dict:
    """生成完整购买建议
    
    Args:
        monthly_budget: 月预算
        months: 定投月数
    
    Returns:
        完整建议
    """
    budget_info = calculate_budget(monthly_budget)
    investment = fixed_investment_strategy(monthly_budget, months)
    risk = risk_assessment(monthly_budget)
    
    return {
        "budget": budget_info,
        "investment": investment,
        "risk": risk,
        "summary": f"建议每期购买 {budget_info['notes_per_draw']} 注，"
                   f"月支出约 {budget_info['actual_monthly_cost']} 元，"
                   f"{months} 个月总投入约 {investment['total_cost']} 元"
    }


def format_advice(advice: dict) -> str:
    """格式化建议输出"""
    lines = []
    lines.append("")
    lines.append("💰 购买建议")
    lines.append(f"├ 建议每期: {advice['budget']['notes_per_draw']} 注 ({advice['budget']['actual_monthly_cost']/12:.0f}元/期)")
    lines.append(f"├ 月预算: {advice['budget']['monthly_budget']:.0f} 元")
    lines.append(f"├ {advice['investment']['months']}个月总投入: {advice['investment']['total_cost']:.0f} 元")
    lines.append(f"├ 单期中六等奖概率: {advice['investment']['sixth_prize_prob_per_draw']:.1f}%")
    lines.append(f"├ 期间至少中一次六等奖: {advice['investment']['sixth_prize_prob_in_period']:.1f}%")
    lines.append(f"├ 风险等级: {advice['risk']['risk_level']}")
    lines.append(f"├ {advice['risk']['risk_desc']}")
    lines.append(f"└ ⚠️  {advice['risk']['recommendation']}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="双色球资金管理")
    parser.add_argument("--budget", type=float, default=20, help="月预算（元）")
    parser.add_argument("--months", type=int, default=12, help="定投月数")
    
    args = parser.parse_args()
    
    advice = generate_advice(args.budget, args.months)
    print(format_advice(advice))
