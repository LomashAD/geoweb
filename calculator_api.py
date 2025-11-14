from typing import Dict, Optional
from models import Crop


def get_rotation_multipliers(current_crop_category: str, previous_crop_category: Optional[str]) -> Dict[str, float]:
    if not previous_crop_category:
        return {"yield_impact": 1.0, "fertilizer_impact": 1.0}
    
    if previous_crop_category == "Бобовые":
        if current_crop_category == "Зерновые":
            return {"yield_impact": 1.20, "fertilizer_impact": 0.80}
        elif current_crop_category == "Овощные":
            return {"yield_impact": 1.15, "fertilizer_impact": 0.85}
        else:
            return {"yield_impact": 1.10, "fertilizer_impact": 0.90}
    
    elif previous_crop_category == "Зерновые":
        if current_crop_category == "Зерновые":
            return {"yield_impact": 0.85, "fertilizer_impact": 1.20}
        elif current_crop_category == "Бобовые":
            return {"yield_impact": 1.10, "fertilizer_impact": 0.90}
        else:
            return {"yield_impact": 0.95, "fertilizer_impact": 1.05}
    
    elif previous_crop_category == "Овощные":
        if current_crop_category == "Зерновые":
            return {"yield_impact": 1.05, "fertilizer_impact": 0.95}
        elif current_crop_category == "Бобовые":
            return {"yield_impact": 1.05, "fertilizer_impact": 0.95}
        else:
            return {"yield_impact": 0.90, "fertilizer_impact": 1.10}
    
    return {"yield_impact": 1.0, "fertilizer_impact": 1.0} # По умолчанию


def calculate_profit_with_rotation(
    crop: Crop,
    area: float,
    previous_crop: Optional[Crop] = None
) -> Dict:
    base_yield = crop.yield_per_ha
    market_price = crop.market_price_per_ton
    seed_price = crop.seed_price_per_kg
    fertilizer_cost_per_ha = crop.fertilizer_cost_per_ha
    other_costs_per_ha = crop.other_costs_per_ha
    
    seed_rate = 200 if crop.category == "Зерновые" else (120 if crop.category == "Бобовые" else 100) # Норма высева приблизительно
    
    previous_category = previous_crop.category if previous_crop else None
    rotation = get_rotation_multipliers(crop.category, previous_category)
    
    yield_multiplier = rotation["yield_impact"]
    fertilizer_multiplier = rotation["fertilizer_impact"]
    
    adjusted_yield = base_yield * yield_multiplier
    adjusted_fertilizer_cost = fertilizer_cost_per_ha * fertilizer_multiplier
    
    # Расчет расходов
    seed_cost = seed_price * seed_rate * area
    fertilizer_cost = adjusted_fertilizer_cost * area
    other_costs = other_costs_per_ha * area
    total_costs = seed_cost + fertilizer_cost + other_costs
    
    # Расчет доходов
    total_harvest = adjusted_yield * area
    revenue = total_harvest * market_price
    net_profit = revenue - total_costs
    profitability = (net_profit / total_costs * 100) if total_costs > 0 else 0
    
    return {
        "crop_name": crop.name,
        "area": area,
        "previous_crop": previous_crop.name if previous_crop else None,
        "revenue": round(revenue, 2),
        "total_costs": round(total_costs, 2),
        "net_profit": round(net_profit, 2),
        "profitability": round(profitability, 2),
        "total_harvest": round(total_harvest, 2),
        "cost_breakdown": {
            "seed_cost": round(seed_cost, 2),
            "fertilizer_cost": round(fertilizer_cost, 2),
            "other_costs": round(other_costs, 2)
        },
        "calculation_details": {
            "base_yield": base_yield,
            "adjusted_yield": round(adjusted_yield, 2),
            "yield_multiplier": round(yield_multiplier, 2),
            "fertilizer_multiplier": round(fertilizer_multiplier, 2),
            "market_price": market_price,
            "seed_price": seed_price,
            "seed_rate": seed_rate
        }
    }
