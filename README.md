# usdafoods2csv

This Python script processes [USDA FoodData Central (FDC)](https://fdc.nal.usda.gov/index.html) nutrient data and generates a simple CSV file containing the available macronutrition facts for the foods.

## Features

- Extracts nutrition information from USDA FDC data sets
    - Supports the Foundation and SR Legacy JSON files
- Determines macronutrient values from the available data (see note below)
- Outputs a CSV file with simplified nutrition facts for easy integration

IMPORTANT NOTE: Foods in these data sets may have missing or incomplete nutrient information. As a result, a macronutrient value of 0 is ambiguous. It may mean that particular nutrient isn't present in the food OR it is present, but that information isn't available in the data set.

## Installation

Simply download `usdafoods2csv.py` or clone the repository. The script requires Python 3.x with no additional dependencies.

```bash
wget https://raw.githubusercontent.com/grego118/usdafoods2csv/main/usdafoods2csv.py
```

```bash
git clone https://github.com/grego118/usdafoods2csv.git usdafoods2csv
cd usdafoods2csv
```

## Usage

```
usage: usdafoods2csv.py [-h] [-o OUTPUT_FILE] [-a ALT_NAMES] input_file [input_file ...]

Processes USDA FDC data and outputs a CSV of simplified nutrition facts. Only Foundation and SR Legacy JSON data sets are supported.

positional arguments:
  input_file            USDA FDC JSON data set to process

options:
  -h, --help            show this help message and exit
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        output file for CSV data (default: stdout)
  -a ALT_NAMES, --alt-names ALT_NAMES
                        JSON file containing alternative food names
```

To process a data set and generate a CSV file:

```bash
python usdafoods2csv.py -o nutrition_data.csv path/to/fdc_data.json
```

This will create a `nutrition_data.csv` file in the current directory. The most recent data sets may be downloaded from the [FDC download page](https://fdc.nal.usda.gov/download-datasets.html). At the time of writing, the USDA updates the Foundation data set twice per year.

## Alternative Food Names

Provide a JSON file containing alternative names to complement the verbose descriptions provided by the USDA. The file must contain a single JSON object where each key is an FDC ID and each value is a string representing the alternative name.

Example file contents:

```json
{
  "321360": "grape tomatoes",
  "321611": "canned green beans",
  "323505": "kale",
  "324653": "dill pickles"
}
```

To use:

```bash
python usdafoods2csv.py -o nutrition_data.csv -a alt_names.json path/to/fdc_data.json
```

## CSV Output Format

The generated CSV data has the following columns:

- `fdc_id`: Food identifier
- `alt_name`: Alternative name (if provided)
- `description`: Food description
- `weight_g`: Weight in grams
- `volume_ml`: Equivalent volume in milliliters (if available)
- `calories_kcal`: Calories in kcal
- `fat_g`: Total fat in grams
- `carbs_g`: Total carbohydrates in grams
- `fiber_g`: Dietary fiber in grams
- `sugars_g`: Total sugars in grams
- `protein_g`: Protein in grams

The records are sorted by `description` in ascending order. If multiple input files are provided, the records are combined into a single CSV output.
