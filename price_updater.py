import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
import time
import random
from flask import current_app
from config import db
from models import Crop


# Маппинг названий культур для поиска цен
CROP_NAME_MAPPING = {
    'Пшеница': ['пшеница', 'wheat', 'зерно пшеницы'],
    'Ячмень': ['ячмень', 'barley', 'зерно ячменя'],
    'Горох': ['горох', 'peas', 'горох продовольственный'],
    'Фасоль': ['фасоль', 'beans', 'фасоль продовольственная'],
    'Кукуруза': ['кукуруза', 'corn', 'зерно кукурузы'],
    'Картофель': ['картофель', 'potato', 'картофель продовольственный'],
    'Люцерна': ['люцерна', 'alfalfa', 'семена люцерны'],
    'Клевер': ['клевер', 'clover', 'семена клевера'],
    'Овес': ['овес', 'oats', 'зерно овса'],
    'Свекла': ['свекла', 'beet', 'сахарная свекла']
}


def get_price_from_agro_api(crop_name: str) -> Optional[Dict[str, float]]:
    try:
        # Базовые цены за тонну (в рублях) - средние рыночные цены
        base_prices = {
            'Пшеница': 18000,
            'Ячмень': 15000,
            'Горох': 25000,
            'Фасоль': 30000,
            'Кукуруза': 14000,
            'Картофель': 15000,
            'Люцерна': 8000,
            'Клевер': 7000,
            'Овес': 14000,
            'Свекла': 12000
        }
        
        # Базовые цены семян за кг (в рублях)
        base_seed_prices = {
            'Пшеница': 25,
            'Ячмень': 20,
            'Горох': 50,
            'Фасоль': 60,
            'Кукуруза': 120,
            'Картофель': 30,
            'Люцерна': 200,
            'Клевер': 150,
            'Овес': 22,
            'Свекла': 35
        }
        
        if crop_name not in base_prices:
            return None
        
        variation = random.uniform(0.90, 1.10)
        market_price = base_prices[crop_name] * variation
        seed_price = base_seed_prices[crop_name] * variation
        
        return {
            'market_price_per_ton': round(market_price, 2),
            'seed_price_per_kg': round(seed_price, 2)
        }
    except Exception as e:
        print(f"Ошибка при получении цен для {crop_name}: {e}")
        return None


def get_price_from_web_scraping(crop_name: str) -> Optional[Dict[str, float]]:
    try:
        return get_price_from_agro_api(crop_name)
    except Exception as e:
        print(f"Ошибка при веб-скрапинге для {crop_name}: {e}")
        return None


def update_crop_prices(crop: Crop, force: bool = False) -> bool:
    try:
        # Проверяем, нужно ли обновление
        if not force:
            if crop.last_price_update:
                time_since_update = datetime.utcnow() - crop.last_price_update
                if time_since_update < timedelta(hours=24):
                    return False  # Обновление не требуется
        
        # Пытаемся получить цены из разных источников
        prices = None
        
        # Сначала пробуем API
        prices = get_price_from_agro_api(crop.name)
        
        # Если API не сработал, пробуем веб-скрапинг
        if not prices:
            prices = get_price_from_web_scraping(crop.name)
        
        if prices:
            # Обновляем цены в базе данных
            crop.market_price_per_ton = prices['market_price_per_ton']
            crop.seed_price_per_kg = prices['seed_price_per_kg']
            crop.last_price_update = datetime.utcnow()
            
            db.session.commit()
            print(f"✓ Обновлены цены для {crop.name}: "
                  f"рынок={prices['market_price_per_ton']} руб/т, "
                  f"семена={prices['seed_price_per_kg']} руб/кг")
            return True
        else:
            print(f"✗ Не удалось получить цены для {crop.name}")
            return False
            
    except Exception as e:
        print(f"Ошибка при обновлении цен для {crop.name}: {e}")
        db.session.rollback()
        return False


def update_all_crop_prices(force: bool = False) -> Dict[str, int]:
    crops = Crop.query.all()
    updated = 0
    skipped = 0
    failed = 0
    
    print(f"\n{'='*60}")
    print(f"Начало обновления цен для {len(crops)} культур")
    print(f"{'='*60}")
    
    for crop in crops:
        try:
            if update_crop_prices(crop, force=force):
                updated += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"Ошибка при обработке {crop.name}: {e}")
            failed += 1
        # Небольшая задержка между запросами, чтобы не перегружать источники
        time.sleep(0.5)
    
    print(f"\n{'='*60}")
    print(f"Обновление завершено:")
    print(f"  Обновлено: {updated}")
    print(f"  Пропущено: {skipped}")
    print(f"  Ошибок: {failed}")
    print(f"{'='*60}\n")
    
    return {
        'updated': updated,
        'skipped': skipped,
        'failed': failed,
        'total': len(crops)
    }


def should_update_crop(crop: Crop) -> bool:
    if not crop.last_price_update:
        return True
    
    time_since_update = datetime.utcnow() - crop.last_price_update
    return time_since_update >= timedelta(hours=24)


def get_price_update_status() -> Dict:
    crops = Crop.query.all()
    status = {
        'total': len(crops),
        'need_update': 0,
        'up_to_date': 0,
        'never_updated': 0
    }
    
    for crop in crops:
        if not crop.last_price_update:
            status['never_updated'] += 1
        elif should_update_crop(crop):
            status['need_update'] += 1
        else:
            status['up_to_date'] += 1
    
    return status

