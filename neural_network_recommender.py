import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import os
import json
import random

class CropRecommender:
    def __init__(self, csv_path='crop_climate_data.csv'):
        self.csv_path = csv_path
        self.model = None
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.is_trained = False
        self.last_recommendations = {}
        
    def load_data(self):
        # Загрузка данных из CSV
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"CSV файл не найден: {self.csv_path}")
        return pd.read_csv(self.csv_path)
    
    def prepare_features(self, df):
        # Подготовка признаков для обучения
        # Если есть колонка last_crop, она, иначе только last_crop_category
        categorical_features = ['crop', 'climate_zone', 'soil_type', 'last_crop_category', 'season']
        if 'last_crop' in df.columns:
            categorical_features.append('last_crop')
        
        for feature in categorical_features:
            if feature not in self.label_encoders:
                self.label_encoders[feature] = LabelEncoder()
                df[feature + '_encoded'] = self.label_encoders[feature].fit_transform(df[feature])
            else:
                # новые значения если их нет
                unique_values = set(df[feature].unique())
                known_values = set(self.label_encoders[feature].classes_)
                if unique_values - known_values:
                    # Расширение энкодера
                    all_values = list(known_values) + list(unique_values - known_values)
                    self.label_encoders[feature] = LabelEncoder()
                    self.label_encoders[feature].fit(all_values)
                try:
                    df[feature + '_encoded'] = self.label_encoders[feature].transform(df[feature])
                except ValueError:
                    most_common = df[feature].mode()[0] if len(df[feature].mode()) > 0 else df[feature].iloc[0] # Самое частое значение
                    df[feature] = df[feature].apply(lambda x: x if x in self.label_encoders[feature].classes_ else most_common)
                    df[feature + '_encoded'] = self.label_encoders[feature].transform(df[feature])
        
        # Признаки для модели
        feature_columns = [f + '_encoded' for f in categorical_features]
        X = df[feature_columns].values
        
        # Кодируем целевую переменную (тип рекомендации)
        if 'recommendation_type' in df.columns:
            if 'recommendation_type' not in self.label_encoders:
                self.label_encoders['recommendation_type'] = LabelEncoder()
                y = self.label_encoders['recommendation_type'].fit_transform(df['recommendation_type'])
            else:
                y = self.label_encoders['recommendation_type'].transform(df['recommendation_type'])
            return X, y
        else:
            return X, None
    
    def train(self):
        # Обучение модели
        df = self.load_data()
        X, y = self.prepare_features(df)
        
        # Разделение на обучающую и тестовую выборку
        try:
            unique, counts = np.unique(y, return_counts=True)
            min_class_count = counts.min() if len(counts) > 0 else 0
            use_stratify = min_class_count >= 2
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y if use_stratify else None
            )
        except ValueError:
            # На всякий (запасной вариант)
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=None
            )
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.model = RandomForestClassifier(
            n_estimators=400,
            max_depth=None,
            min_samples_leaf=2,
            max_features='sqrt',
            class_weight='balanced_subsample',
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_train_scaled, y_train)
        
        self.is_trained = True
        
        # Оценка качества обучения
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        print(f"Модель обучена. Точность на обучающей выборке: {train_score:.2f}, на тестовой: {test_score:.2f}")
        
        return self
    
    def get_recommendation(self, crop, climate_zone, soil_type='чернозем', last_crop_category='зерновые', last_crop=None, season='весна-лето', num_variants=3, diversity=0.7):
        # Получение рекомендации
        if not self.is_trained:
            try:
                self.train()
            except Exception as e:
                print(f"Ошибка обучения модели: {e}")
                base = self._get_fallback_recommendation(crop, climate_zone, last_crop_category)
                base['variants'] = [base['recommendation_text']]
                return base # Возвращаем базовую рекомендацию без обучения
        
        # DataFrame с одним примером
        data = {
            'crop': [crop],
            'climate_zone': [climate_zone],
            'soil_type': [soil_type],
            'last_crop_category': [last_crop_category],
            'season': [season]
        }
        if last_crop:
            data['last_crop'] = [last_crop]
        df = pd.DataFrame(data)
        
        try:
            X, _ = self.prepare_features(df) # признак
            X_scaled = self.scaler.transform(X)
            
            class_index = self.model.predict(X_scaled)[0]
            recommendation_type_name = self.label_encoders['recommendation_type'].inverse_transform([class_index])[0] # Предсказывает тип рекомендации
            probabilities = self.model.predict_proba(X_scaled)[0] # вероятности
            df_full = self.load_data() # Рекомендации из CSV
            
            # Функция поиска текста по приоритетам
            def pick_text_for_type(target_type_name):
                if last_crop and 'last_crop' in df_full.columns:
                    q = df_full[
                        (df_full['crop'] == crop) &
                        (df_full['climate_zone'] == climate_zone) &
                        (df_full.get('last_crop', '') == last_crop) &
                        (df_full['recommendation_type'] == target_type_name)
                    ]
                    if len(q) > 0:
                        return q.sample(1, random_state=random.randint(0, 10**6)).iloc[0]['recommendation_text']
                q = df_full[
                    (df_full['crop'] == crop) &
                    (df_full['climate_zone'] == climate_zone) &
                    (df_full['last_crop_category'] == last_crop_category) &
                    (df_full['recommendation_type'] == target_type_name)
                ]
                if len(q) > 0:
                    return q.sample(1, random_state=random.randint(0, 10**6)).iloc[0]['recommendation_text']
                q = df_full[
                    (df_full['crop'] == crop) &
                    (df_full['climate_zone'] == climate_zone)
                ]
                if len(q) > 0:
                    return q.sample(1, random_state=random.randint(0, 10**6)).iloc[0]['recommendation_text']
                return None
            
            # Базовый вариант 
            base_text = pick_text_for_type(recommendation_type_name)
            if not base_text:
                base = self._get_fallback_recommendation(crop, climate_zone, last_crop_category)
                base['variants'] = [base['recommendation_text']]
                return base

            # Генеротор списка вариантов
            num_classes = len(probabilities)
            k = max(1, int(1 + diversity * (num_classes - 1)))
            top_indices = np.argsort(probabilities)[::-1][:k]
            variant_texts = []
            used = set()

            for idx in top_indices:
                type_name = self.label_encoders['recommendation_type'].inverse_transform([idx])[0]
                txt = pick_text_for_type(type_name)
                if txt:
                    diverse_txts = self._diversify_text(txt, type_name, crop, last_crop_category)
                    for t in diverse_txts:
                        if t not in used:
                            variant_texts.append(t)
                            used.add(t)
                        if len(variant_texts) >= num_variants:
                            break
                if len(variant_texts) >= num_variants:
                    break

            if not variant_texts:
                variant_texts = [base_text]

            # Сначала ищем с учетом конкретного предшественника, если он указан

            recommendation_text = variant_texts[0]
            
            return {
                'recommendation_type': recommendation_type_name,
                'recommendation_text': recommendation_text,
                'confidence': float(max(probabilities)),
                'variants': variant_texts
            }
        except Exception as e:
            print(f"Ошибка получения рекомендации: {e}")
            base = self._get_fallback_recommendation(crop, climate_zone, last_crop_category)
            base['variants'] = [base['recommendation_text']] # В случае ошибки возвращаем общую рекомендацию
            return base
    
    def _get_fallback_recommendation(self, crop, climate_zone, last_crop_category):
        # Резервная рекомендация при ошибках
        recommendations = {
            'севооборот': f"В следующем году рекомендуется посадить {crop}. Учитывайте историю посевов на поле.",
            'удобрение': f"Почва требует внимания. После {last_crop_category} рекомендуется внести органические удобрения перед посевом {crop}.",
            'защита растений': f"После {last_crop_category} возможны вредители. Проведите профилактическую обработку перед посевом {crop}."
        }
        
        # Определяем тип рекомендации на основе категории последней культуры
        if last_crop_category == 'бобовые':
            rec_type = 'севооборот'
            text = f"В следующем году лучше всего посадить {crop}. Почва обогащена азотом от бобовых культур."
        elif last_crop_category == 'зерновые':
            rec_type = 'удобрение'
            text = f"После зерновых культур рекомендуется посадить {crop}. Внесите удобрения для улучшения плодородия почвы."
        else:
            rec_type = 'севооборот'
            text = recommendations['севооборот']
        
        return {
            'recommendation_type': rec_type,
            'recommendation_text': text,
            'confidence': 0.6
        }
    
    def get_climate_zone_from_coords(self, lat, lon):
        """Определение климатической зоны по координатам (упрощенная версия для России)"""
        # Упрощенное определение климатической зоны по широте и долготе
        # В реальном приложении можно использовать API 2GIS или другие сервисы
        
        # Определение по широте
        if lat < 50:
            # Южные регионы - более континентальный климат
            if lon > 40:  # Восточные регионы
                return 'континентальный'
            else:  # Западные регионы
                return 'умеренный'
        elif lat < 55:
            # Центральные регионы
            if lon > 50:  # Восточные регионы
                return 'континентальный'
            elif lon < 30:  # Западные регионы (ближе к морю)
                return 'морской'
            else:
                return 'умеренный'
        elif lat < 60:
            # Средние широты
            if lon > 50:
                return 'континентальный'
            else:
                return 'умеренный'
        else:
            # Северные регионы
            return 'континентальный'
    
    def get_crop_category(self, crop_name):
        """Определение категории культуры"""
        categories = {
            'Пшеница': 'зерновые',
            'Ячмень': 'зерновые',
            'Овес': 'зерновые',
            'Рожь': 'зерновые',
            'Кукуруза': 'зерновые',
            'Гречиха': 'зерновые',
            'Горох': 'бобовые',
            'Фасоль': 'бобовые',
            'Соя': 'бобовые',
            'Люцерна': 'бобовые',
            'Клевер': 'бобовые',
            'Картофель': 'овощные',
            'Свекла': 'овощные',
            'Морковь': 'овощные',
            'Капуста': 'овощные',
            'Томаты': 'овощные',
            'Огурцы': 'овощные',
            'Лук': 'овощные',
            'Подсолнечник': 'масличные',
            'Рапс': 'масличные'
        }
        return categories.get(crop_name, 'зерновые')
    
    def generate_field_recommendation(self, field_name, field_geometry, crop_history):
        """Генерация рекомендации для поля на основе его истории и координат"""
        # Извлекаем координаты из геометрии
        try:
            geometry = json.loads(field_geometry) if isinstance(field_geometry, str) else field_geometry
            if geometry['type'] == 'Polygon' and len(geometry['coordinates']) > 0:
                # Берем центр полигона
                coords = geometry['coordinates'][0]
                center_lat = sum(coord[1] for coord in coords) / len(coords)
                center_lon = sum(coord[0] for coord in coords) / len(coords)
            else:
                # По умолчанию центральная Россия
                center_lat = 55.7558
                center_lon = 37.6173
        except:
            center_lat = 55.7558
            center_lon = 37.6173
        
        # Определяем климатическую зону
        climate_zone = self.get_climate_zone_from_coords(center_lat, center_lon)
        
        # Если истории нет
        if not crop_history or len(crop_history) == 0:
            message = f"{field_name}: Сначала добавьте хотя бы одну культуру в историю поля."
            result = {
                'field_name': field_name,
                'recommended_crop': None,
                'message': message,
                'recommendation_type': 'info',
                'confidence': None,
                'variants': [message],
            }
            # Сохранение последней рекомендации
            self.last_recommendations[field_name] = {
                'input': {
                    'climate_zone': climate_zone,
                    'last_crop_category': None,
                    'last_crop_name': None,
                    'recommended_crop': None
                },
                'result': result
            }
            return result
        
        # Анализиз истории посевов
        if crop_history and len(crop_history) > 0:
            last_crop = crop_history[0].get('crop_name', '')
            last_crop_category = self.get_crop_category(last_crop)
            
            rotation_suggestions = {
                'Пшеница': ['Горох', 'Фасоль', 'Свекла', 'Подсолнечник'],
                'Ячмень': ['Горох', 'Фасоль', 'Свекла', 'Рапс'],
                'Овес': ['Горох', 'Фасоль', 'Пшеница', 'Картофель'],
                'Рожь': ['Горох', 'Фасоль', 'Картофель', 'Свекла'],
                'Горох': ['Пшеница', 'Ячмень', 'Кукуруза', 'Подсолнечник'],
                'Фасоль': ['Пшеница', 'Ячмень', 'Кукуруза', 'Свекла'],
                'Соя': ['Пшеница', 'Ячмень', 'Кукуруза', 'Подсолнечник'],
                'Кукуруза': ['Горох', 'Фасоль', 'Пшеница', 'Соя'],
                'Картофель': ['Горох', 'Фасоль', 'Овес', 'Пшеница'],
                'Свекла': ['Пшеница', 'Ячмень', 'Горох', 'Овес'],
                'Морковь': ['Пшеница', 'Ячмень', 'Овес', 'Горох'],
                'Капуста': ['Пшеница', 'Ячмень', 'Овес', 'Горох'],
                'Томаты': ['Горох', 'Фасоль', 'Пшеница', 'Овес'],
                'Огурцы': ['Горох', 'Фасоль', 'Пшеница', 'Овес'],
                'Лук': ['Пшеница', 'Ячмень', 'Овес', 'Горох'],
                'Подсолнечник': ['Пшеница', 'Ячмень', 'Горох', 'Овес'],
                'Рапс': ['Пшеница', 'Ячмень', 'Горох', 'Овес'],
                'Гречиха': ['Пшеница', 'Ячмень', 'Горох', 'Овес'],
                'Люцерна': ['Пшеница', 'Ячмень', 'Кукуруза', 'Подсолнечник'],
                'Клевер': ['Пшеница', 'Ячмень', 'Кукуруза', 'Овес']
            }
            
            suggested_crops = rotation_suggestions.get(last_crop, ['Пшеница', 'Горох', 'Свекла'])
            recommended_crop = suggested_crops[0]
        
        last_crop_name = crop_history[0].get('crop_name', '') if crop_history and len(crop_history) > 0 else None
        
        recommendation = self.get_recommendation(
            crop=recommended_crop,
            climate_zone=climate_zone,
            soil_type='чернозем', 
            last_crop_category=last_crop_category,
            last_crop=last_crop_name,  
            season='весна-лето',
            num_variants=3,
            diversity=0.7
        )
        
        # Финальное сообщение
        message = f"{field_name}: {recommendation['recommendation_text']}"
        
        result = {
            'field_name': field_name,
            'recommended_crop': recommended_crop,
            'message': message,
            'recommendation_type': recommendation['recommendation_type'],
            'confidence': recommendation['confidence'],
            'variants': recommendation.get('variants', [recommendation['recommendation_text']])
        }

        # Сохраняем последнюю рекомендацию
        self.last_recommendations[field_name] = {
            'input': {
                'climate_zone': climate_zone,
                'last_crop_category': last_crop_category,
                'last_crop_name': last_crop_name,
                'recommended_crop': recommended_crop
            },
            'result': result
        }

        return result

    def update_field_history_and_get_recommendation(self, field_name, field_geometry, crop_history):
        """После обновления истории поля пересчитать и вернуть новую или старую рекомендацию в зависимости от актуальности"""
        previous = self.last_recommendations.get(field_name, {}).get('result')
        new_result = self.generate_field_recommendation(field_name, field_geometry, crop_history)

        if not previous:
            return new_result

        still_relevant = self._is_previous_recommendation_still_relevant(previous, crop_history) # Проверка актуальности прошлой рекомендации

        if new_result['confidence'] >= previous.get('confidence', 0) + 0.08:
            return new_result

        if still_relevant:
            return previous

        return new_result

    def _is_previous_recommendation_still_relevant(self, previous_result, crop_history):
        if not crop_history or len(crop_history) == 0:
            return False
        last_crop = crop_history[0].get('crop_name', '')
        last_cat = self.get_crop_category(last_crop)
        prev_type = previous_result.get('recommendation_type')

        # Простейшие правила актуальности
        if prev_type == 'удобрение' and last_cat in ['зерновые']:
            return True
        if prev_type == 'защита растений' and last_cat in ['овощные']:
            return True
        if prev_type == 'севооборот':
            return True
        return False

    def _diversify_text(self, base_text, recommendation_type, crop, last_crop_category):
        templates = [
            "{t}.",
            "{t} Дополнительно учтите текущие условия поля.",
            "{t} Это поможет повысить урожайность.",
            "{t} Рекомендуем проверить влажность и состояние почвы.",
            "{t} Следите за сроками проведения работ."
        ]
        leadins = {
            'севооборот': [
                f"Оптимально высевать {crop}",
                f"Рекомендуется посеять {crop}",
                f"Подходящий вариант — {crop}"
            ],
            'удобрение': [
                "Почвенный блок требует внимания",
                "Состояние почвы важно учесть",
                "Рекомендуем провести корректировку питания почвы"
            ],
            'защита растений': [
                "Проведите профилактику от вредителей",
                "Есть риск фитосанитарных проблем",
                "Желательно запланировать защитные мероприятия"
            ]
        }

        variants = []
        candidates = [base_text]
        for l in leadins.get(recommendation_type, []):
            candidates.append(f"{l}. {base_text}")
        for tmpl in templates:
            candidates.append(tmpl.format(t=base_text))

        random.shuffle(candidates)
        seen = set()
        for c in candidates:
            norm = c.strip()
            if norm not in seen:
                variants.append(norm)
                seen.add(norm)
            if len(variants) >= 5:
                break
        return variants

recommender = CropRecommender() # Глобальный экземпляр