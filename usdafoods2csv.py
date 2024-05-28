#!/usr/bin/env python
import csv
import json
import sys

from argparse import ArgumentParser
from collections import defaultdict, namedtuple
from dataclasses import dataclass
from enum import auto, Enum
from heapq import heappop, heappush


NutrientMetadata = namedtuple('NutrientMetadata', 'description, category, priority')


class NutrientCategory(Enum):
    CALORIES = auto()
    FAT = auto()
    CARBS = auto()
    FIBER = auto()
    SUGARS = auto()
    PROTEIN = auto()


@dataclass(order=True, frozen=True)
class VolumeWeight:
    volume: float
    weight: float
    quantity: float
    descriptor: str

    _PORTION_UNIT_ML_MAP = {1000: 236.5875, # cup
                            1001: 14.78672, # tbsp
                            1002: 4.928906, # tsp
                            1004: 1.0}      # mL

    @classmethod
    def from_food_portion(cls, food_portion):
        try:
            unit_id = food_portion['measureUnit']['id']
            quantity = food_portion['amount']
            descriptor = food_portion['measureUnit']['abbreviation']
            weight = food_portion['gramWeight']
            if (unit_id in cls._PORTION_UNIT_ML_MAP
                and quantity is not None
                and quantity > 0.0
                and weight is not None
                and weight > 0.0):
                return cls(volume=cls._PORTION_UNIT_ML_MAP[unit_id] * quantity,
                           weight=weight,
                           quantity=quantity,
                           descriptor=descriptor)
            return None
        except KeyError:
            return None


@dataclass(frozen=True)
class Macros:
    calories: float
    fat: float
    carbs: float
    fiber: float
    sugars: float
    protein: float

    _NUTRIENT_NUM_METADATA_MAP = {
            '203': NutrientMetadata('protein', NutrientCategory.PROTEIN, 1),
            '204': NutrientMetadata('total_lipids', NutrientCategory.FAT, 1),
            '298': NutrientMetadata('nlea_fat', NutrientCategory.FAT, 2),
            '205': NutrientMetadata('carbs_by_difference', NutrientCategory.CARBS, 1),
            '205.2': NutrientMetadata('carbs_by_summation', NutrientCategory.CARBS, 2),
            '291': NutrientMetadata('fiber_aoac_991_43', NutrientCategory.FIBER, 2),
            '293': NutrientMetadata('fiber_aoac_2011_25', NutrientCategory.FIBER, 1),
            '269.3': NutrientMetadata('total_sugars', NutrientCategory.SUGARS, 1),
            '269': NutrientMetadata('nlea_sugars', NutrientCategory.SUGARS, 2),
            '208': NutrientMetadata('cals_kcal', NutrientCategory.CALORIES, 1),
            '268': NutrientMetadata('cals_from_kJ', NutrientCategory.CALORIES, 2),
            '957': NutrientMetadata('cals_atwater_general', NutrientCategory.CALORIES, 3),
            '958': NutrientMetadata('cals_atwater_specific', NutrientCategory.CALORIES, 4),
    }

    @classmethod
    def from_food_nutrients(cls, food_nutrients):
        macro_heaps = defaultdict(list)
        for category in NutrientCategory:
            heappush(macro_heaps[category], (10, 0.0))

        for food_nutrient in food_nutrients:
            try:
                nutrient_num = food_nutrient['nutrient']['number']
                amount = food_nutrient['amount']
                if nutrient_num == 268:
                    amount *= 0.239
            except KeyError:
                continue

            if nutrient_num not in cls._NUTRIENT_NUM_METADATA_MAP:
                continue

            metadata = cls._NUTRIENT_NUM_METADATA_MAP[nutrient_num]
            heappush(macro_heaps[metadata.category], (metadata.priority, amount))

        calories = heappop(macro_heaps[NutrientCategory.CALORIES])[1]
        fat = heappop(macro_heaps[NutrientCategory.FAT])[1]
        carbs = heappop(macro_heaps[NutrientCategory.CARBS])[1]
        fiber = heappop(macro_heaps[NutrientCategory.FIBER])[1]
        sugars = heappop(macro_heaps[NutrientCategory.SUGARS])[1]
        protein = heappop(macro_heaps[NutrientCategory.PROTEIN])[1]
        if calories == 0.0:
            calories = protein*4 + carbs*4 + fat*9

        return cls(calories=round(calories, 1),
                   fat=round(fat, 1),
                   carbs=round(carbs, 1),
                   fiber=round(fiber, 1),
                   sugars=round(sugars, 1),
                   protein=round(protein, 1))

    def as_list(self):
        return [self.calories, self.fat, self.carbs, self.fiber, self.sugars, self.protein]


class Food:
    def __init__(self, source, food_data):
        self.source = source
        self.fdc_id = food_data['fdcId']
        self.name = food_data['description']
        self.weight = 100.0
        self.volume = None

        try:
            volume_weights = [VolumeWeight.from_food_portion(p)
                             for p in food_data['foodPortions']]
            max_volume_weight = max(v for v in volume_weights if v is not None)

            self.weight = round(max_volume_weight.weight, 1)
            self.volume = round(max_volume_weight.volume, 1)
        except (KeyError, StopIteration, ValueError):
            pass

        macros_per_100_g = Macros.from_food_nutrients(food_data['foodNutrients'])
        if self.weight != 100.0:
            scale_factor = self.weight / 100.0
            self.macros = Macros(calories=round(macros_per_100_g.calories * scale_factor, 1),
                                 fat=round(macros_per_100_g.fat * scale_factor, 1),
                                 carbs=round(macros_per_100_g.carbs * scale_factor, 1),
                                 fiber=round(macros_per_100_g.fiber * scale_factor, 1),
                                 sugars=round(macros_per_100_g.sugars * scale_factor, 1),
                                 protein=round(macros_per_100_g.protein * scale_factor, 1))
        else:
            self.macros = macros_per_100_g

    def __repr__(self):
        return (f"Food(source='{self.source}', fdc_id={self.fdc_id}, name='{self.name}', "
                f"weight={self.weight}, volume={self.volume}, macros={self.macros})")

    def __lt__(self, other):
        return self.name < other.name

    def nutrition_record(self):
        return [self.name, self.weight, self.volume] + self.macros.as_list()


def main(input_file, output_file):
    with open(input_file, 'r') as f:
        all_food_data = json.load(f)

    foods = []
    if 'FoundationFoods' in all_food_data:
        foods.extend(Food('Foundation', f) for f in all_food_data['FoundationFoods'])

    if 'SRLegacyFoods' in all_food_data:
        foods.extend(Food('SR Legacy', f) for f in all_food_data['SRLegacyFoods'])

    foods.sort()

    headers = ['name', 'weight_g', 'volume_ml',
               'calories_kcal', 'fat_g', 'carbs_g', 'fiber_g', 'sugars_g', 'protein_g']
    if output_file is None:
        csv_writer = csv.writer(sys.stdout)
        csv_writer.writerow(headers)
        for food in foods:
            csv_writer.writerow(food.nutrition_record())
    else:
        with open(output_file, 'w', newline='') as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow(headers)
            for food in foods:
                csv_writer.writerow(food.nutrition_record())


if __name__ == '__main__':
    parser = ArgumentParser(description=('Processes USDA FDC data and outputs a CSV of '
                                         'simplified nutrition facts. Only Foundation and SR '
                                         'Legacy JSON data sets are supported.'))
    parser.add_argument('input_file', help='USDA FDC JSON data set to process')
    parser.add_argument('-o', '--output-file', help='output file for CSV data (default: stdout)')
    args = parser.parse_args()

    main(args.input_file, args.output_file)
