#!/usr/bin/env python3
"""
Enhanced PDF Parser for Rodonaves Tariff Data
Handles complex hierarchical structure: Region → UF → Category → Weight Ranges
"""

from typing import Dict, List, Tuple, Optional, Any
import pdfplumber
import re
import pandas as pd
from pathlib import Path


class PDFTariffParser:
    """
    Enhanced parser for Rodonaves tariff PDF documents
    Supports complex hierarchical structures with regional variations
    """

    def __init__(self):
        self.regional_config = self._get_regional_config()
        self.state_categories = self._get_state_categories()

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract complete tariff data from Rodonaves PDF

        Returns:
            Dict with structure:
            {
                'states': {
                    'SC': {
                        'region': 'Sul',
                        'categories': {
                            'CAPITAL': {weight_ranges},
                            'INTERIOR_1': {weight_ranges},
                            'INTERIOR_2': {weight_ranges}
                        },
                        'parameters': {gris_percent, icms_percent, etc}
                    }
                },
                'general_params': {...}
            }
        """
        result = {
            'states': {},
            'general_params': {},
            'import_info': {
                'pdf_path': pdf_path,
                'pages_processed': 0,
                'categories_found': 0,
                'errors': []
            }
        }

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_data = self._parse_page(page, page_num)
                        if page_data:
                            self._merge_page_data(result, page_data)
                            result['import_info']['pages_processed'] += 1
                    except Exception as e:
                        error_msg = f"Error on page {page_num}: {str(e)}"
                        result['import_info']['errors'].append(error_msg)
                        print(f"WARNING: {error_msg}")

            # Extract general parameters
            result['general_params'] = self._extract_general_parameters(pdf_path)

            # Count categories found
            result['import_info']['categories_found'] = sum(
                len(state['categories']) for state in result['states'].values()
            )

        except Exception as e:
            result['import_info']['errors'].append(f"Critical error: {str(e)}")
            print(f"ERROR: Critical parsing error: {e}")

        return result

    def _parse_page(self, page, page_num: int) -> Optional[Dict]:
        """Parse a single page and extract tariff data"""
        text = page.extract_text() or ""

        # Determine page type and region
        region_info = self._detect_page_region(text, page_num)
        if not region_info:
            return None

        # Extract tables from page
        tables = page.extract_tables()
        if not tables:
            return None

        page_data = {
            'region': region_info['region'],
            'states': {}
        }

        # Process each table
        for table in tables:
            if not table or len(table) < 2:
                continue

            table_data = self._parse_table(table, region_info)
            if table_data:
                self._merge_table_data(page_data, table_data)

        return page_data if page_data['states'] else None

    def _detect_page_region(self, text: str, page_num: int) -> Optional[Dict]:
        """Detect which region this page covers"""
        text_upper = text.upper()

        # Page 1: Sul, Sudeste, Centro-Oeste
        if page_num == 1 or any(region in text_upper for region in ['SUL', 'SUDESTE', 'CENTRO-OESTE']):
            return {
                'region': 'Sul/Sudeste/Centro-Oeste',
                'gris_percent': 0.00316,  # 0.316%
                'fvalor_percent': 0.00316,  # 0.316%
                'states': ['SC', 'RS', 'PR', 'SP', 'MG', 'RJ', 'ES', 'DF', 'GO', 'MS', 'MT']
            }

        # Page 2: Norte
        elif page_num == 2 or 'NORTE' in text_upper:
            return {
                'region': 'Norte',
                'gris_percent': 0.004,  # 0.40%
                'fvalor_percent': 0.004,  # 0.40%
                'states': ['AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO']
            }

        return None

    def _parse_table(self, table: List[List[str]], region_info: Dict) -> Optional[Dict]:
        """Parse a single table and extract state/category data"""
        if not table or len(table) < 3:
            return None

        # Convert to DataFrame for easier processing
        df = pd.DataFrame(table[1:], columns=table[0])

        # Clean DataFrame
        df = df.fillna('')
        df = df.applymap(lambda x: str(x).strip() if x else '')

        table_data = {}
        current_state = None

        for idx, row in df.iterrows():
            # Check if this row defines a new state
            state_match = self._extract_state_from_row(row, region_info['states'])
            if state_match:
                current_state = state_match
                if current_state not in table_data:
                    table_data[current_state] = {
                        'region': region_info['region'],
                        'categories': {},
                        'parameters': {
                            'gris_percent': region_info['gris_percent'],
                            'fvalor_percent': region_info['fvalor_percent']
                        }
                    }
                continue

            # If we have a current state, try to extract category data
            if current_state:
                category_data = self._extract_category_from_row(row, current_state)
                if category_data:
                    category_name = category_data['category']
                    weight_data = category_data['weight_data']

                    if weight_data:
                        table_data[current_state]['categories'][category_name] = weight_data

        return table_data if table_data else None

    def _extract_state_from_row(self, row: pd.Series, valid_states: List[str]) -> Optional[str]:
        """Extract state code from a table row"""
        # Check each cell in the row for state codes
        for cell in row:
            cell_upper = str(cell).upper().strip()

            # Direct state match
            if cell_upper in valid_states:
                return cell_upper

            # Check if cell contains state code with other text
            for state in valid_states:
                if state in cell_upper and len(cell_upper) <= 10:  # Avoid false positives
                    return state

        return None

    def _extract_category_from_row(self, row: pd.Series, state: str) -> Optional[Dict]:
        """Extract category and weight data from a row"""
        # Look for category indicators
        category = None
        row_text = ' '.join(str(cell) for cell in row).upper()

        # Determine category type
        if 'CAPITAL' in row_text:
            category = 'CAPITAL'
        elif 'INTERIOR 1' in row_text or 'INTERIOR1' in row_text:
            category = 'INTERIOR_1'
        elif 'INTERIOR 2' in row_text or 'INTERIOR2' in row_text:
            category = 'INTERIOR_2'
        elif 'INTERIOR' in row_text and 'DEMAIS' in row_text:
            category = 'INTERIOR_2'  # "Demais Filiais" = Interior 2
        elif 'FLUVIAL' in row_text:
            category = 'FLUVIAL'
        elif any(keyword in row_text for keyword in ['INTERIOR', 'INTERIOR (100%)']):
            category = 'INTERIOR'

        if not category:
            return None

        # Extract weight range values
        weight_data = self._extract_weight_ranges_from_row(row)

        return {
            'category': category,
            'weight_data': weight_data
        } if weight_data else None

    def _extract_weight_ranges_from_row(self, row: pd.Series) -> Optional[Dict]:
        """Extract weight range values from a table row"""
        weight_ranges = {
            'ate_10': 0.0,
            'ate_20': 0.0,
            'ate_40': 0.0,
            'ate_60': 0.0,
            'ate_100': 0.0,
            'excedente_por_kg': 0.0
        }

        values_found = []

        # Extract all monetary values from the row
        for cell in row:
            value = self._extract_monetary_value(str(cell))
            if value > 0:
                values_found.append(value)

        # Map values to weight ranges (assuming standard column order)
        if len(values_found) >= 6:
            weight_ranges['ate_10'] = values_found[0]
            weight_ranges['ate_20'] = values_found[1]
            weight_ranges['ate_40'] = values_found[2]
            weight_ranges['ate_60'] = values_found[3]
            weight_ranges['ate_100'] = values_found[4]
            weight_ranges['excedente_por_kg'] = values_found[5]

            return weight_ranges
        elif len(values_found) >= 5:
            # Some tables might not have excedente column
            weight_ranges['ate_10'] = values_found[0]
            weight_ranges['ate_20'] = values_found[1]
            weight_ranges['ate_40'] = values_found[2]
            weight_ranges['ate_60'] = values_found[3]
            weight_ranges['ate_100'] = values_found[4]

            return weight_ranges

        return None

    def _extract_monetary_value(self, cell: str) -> float:
        """Extract monetary value from a cell string"""
        if not cell or cell.strip() == '':
            return 0.0

        # Clean the cell text
        cell = cell.strip().replace(' ', '')

        # Patterns for monetary values
        patterns = [
            r'(\d{1,3}(?:\.\d{3})*,\d{2})',  # 1.234,56
            r'(\d+,\d{2})',  # 123,45
            r'(\d+\.\d{2})',  # 123.45
            r'(\d+,\d{1,4})',  # 1,234 or 1,2345
            r'(\d+\.\d{1,4})',  # 1.234 or 1.2345
            r'(\d+)',  # 123 (integer)
        ]

        for pattern in patterns:
            match = re.search(pattern, cell)
            if match:
                value_str = match.group(1)
                try:
                    # Convert Brazilian format to float
                    if ',' in value_str and '.' in value_str:
                        # Format: 1.234,56
                        value_str = value_str.replace('.', '').replace(',', '.')
                    elif ',' in value_str:
                        # Format: 123,45
                        value_str = value_str.replace(',', '.')

                    return float(value_str)
                except ValueError:
                    continue

        return 0.0

    def _merge_page_data(self, result: Dict, page_data: Dict):
        """Merge page data into main result"""
        for state_code, state_data in page_data['states'].items():
            if state_code not in result['states']:
                result['states'][state_code] = {
                    'region': state_data['region'],
                    'categories': {},
                    'parameters': state_data['parameters']
                }

            # Merge categories
            for category, weight_data in state_data['categories'].items():
                result['states'][state_code]['categories'][category] = weight_data

    def _merge_table_data(self, page_data: Dict, table_data: Dict):
        """Merge table data into page data"""
        for state_code, state_data in table_data.items():
            if state_code not in page_data['states']:
                page_data['states'][state_code] = state_data
            else:
                # Merge categories
                page_data['states'][state_code]['categories'].update(state_data['categories'])

    def _extract_general_parameters(self, pdf_path: str) -> Dict[str, float]:
        """Extract general parameters from PDF text"""
        params = {
            "cubagem_kg_por_m3": 200.0,  # Standard for road transport
            "pedagio_fixo": 6.46,
            "icms_percent": 0.12,
        }

        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    full_text += text + "\n"

                # Extract specific parameters from text
                text_lower = full_text.lower()

                # Pedagio
                pedagio_match = re.search(r'pedágio.*?r\$\s*(\d+,\d{2})', text_lower)
                if pedagio_match:
                    params["pedagio_fixo"] = float(pedagio_match.group(1).replace(',', '.'))

                # Cubagem
                cubagem_match = re.search(r'cubagem.*?(\d+)kg.*?m³', text_lower)
                if cubagem_match:
                    params["cubagem_kg_por_m3"] = float(cubagem_match.group(1))

        except Exception as e:
            print(f"Warning: Could not extract general parameters: {e}")

        return params

    def _get_regional_config(self) -> Dict[str, Dict]:
        """Get regional configuration mapping"""
        return {
            'Sul': {
                'states': ['SC', 'RS', 'PR'],
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316
            },
            'Sudeste': {
                'states': ['SP', 'MG', 'RJ', 'ES'],
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316
            },
            'Centro-Oeste': {
                'states': ['DF', 'GO', 'MS', 'MT'],
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316
            },
            'Norte': {
                'states': ['AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO'],
                'gris_percent': 0.004,
                'fvalor_percent': 0.004
            }
        }

    def _get_state_categories(self) -> Dict[str, List[str]]:
        """Get valid categories for each state"""
        return {
            'SC': ['CAPITAL', 'INTERIOR_1', 'INTERIOR_2'],
            'RS': ['CAPITAL', 'INTERIOR_1', 'INTERIOR'],
            'PR': ['CAPITAL', 'INTERIOR_1', 'INTERIOR_2'],
            'SP': ['CAPITAL', 'INTERIOR_1', 'INTERIOR_2'],
            'MG': ['CAPITAL', 'INTERIOR_1', 'INTERIOR_2'],
            'RJ': ['RIO_DE_JANEIRO'],
            'ES': ['ESPIRITO_SANTO'],
            'DF': ['DISTRITO_FEDERAL'],
            'GO': ['CAPITAL', 'INTERIOR_1', 'INTERIOR_2'],
            'MS': ['MATO_GROSSO_DO_SUL'],
            'MT': ['MATO_GROSSO'],
            'AC': ['CAPITAL', 'INTERIOR'],
            'AM': ['CAPITAL', 'INTERIOR', 'FLUVIAL'],
            'AP': ['CAPITAL', 'FLUVIAL'],
            'PA': ['CAPITAL', 'INTERIOR', 'FLUVIAL'],
            'RO': ['CAPITAL', 'INTERIOR'],
            'RR': ['CAPITAL', 'INTERIOR', 'FLUVIAL'],
            'TO': ['CAPITAL', 'INTERIOR_1', 'INTERIOR_2']
        }

    def validate_extracted_data(self, data: Dict) -> Dict[str, List[str]]:
        """Validate extracted tariff data for completeness and consistency"""
        validation_result = {
            'errors': [],
            'warnings': [],
            'missing_states': [],
            'missing_categories': [],
            'invalid_progressions': []
        }

        # Check for missing states
        expected_states = set()
        for region_config in self.regional_config.values():
            expected_states.update(region_config['states'])

        found_states = set(data.get('states', {}).keys())
        validation_result['missing_states'] = list(expected_states - found_states)

        # Validate each state's data
        for state_code, state_data in data.get('states', {}).items():
            expected_categories = self.state_categories.get(state_code, [])
            found_categories = list(state_data.get('categories', {}).keys())

            missing = set(expected_categories) - set(found_categories)
            if missing:
                validation_result['missing_categories'].append(f"{state_code}: {list(missing)}")

            # Validate weight progressions
            for category, weight_data in state_data.get('categories', {}).items():
                if not self._validate_weight_progression(weight_data):
                    validation_result['invalid_progressions'].append(f"{state_code}_{category}")

        return validation_result

    def _validate_weight_progression(self, weight_data: Dict) -> bool:
        """Validate that weight ranges are in ascending order"""
        try:
            weights = [
                weight_data.get('ate_10', 0),
                weight_data.get('ate_20', 0),
                weight_data.get('ate_40', 0),
                weight_data.get('ate_60', 0),
                weight_data.get('ate_100', 0)
            ]

            # Check if weights are in ascending order
            return all(weights[i] <= weights[i+1] for i in range(len(weights)-1))
        except:
            return False


def main():
    """Test the parser with the official PDF"""
    pdf_path = r"C:\Users\Beto\Dropbox\NXT\Dev\fretes-rodonaves\432968 MONTERREY 2025 (1) (1).pdf"

    parser = PDFTariffParser()

    print("Starting PDF parsing...")
    result = parser.parse_pdf(pdf_path)

    # Print summary
    print(f"\nPARSING SUMMARY:")
    print(f"Pages processed: {result['import_info']['pages_processed']}")
    print(f"Categories found: {result['import_info']['categories_found']}")
    print(f"States found: {len(result['states'])}")
    print(f"Errors: {len(result['import_info']['errors'])}")

    # Show states and categories found
    print(f"\nSTATES AND CATEGORIES:")
    for state_code, state_data in result['states'].items():
        categories = list(state_data['categories'].keys())
        print(f"  {state_code}: {categories}")

    # Validate data
    validation = parser.validate_extracted_data(result)
    if validation['errors'] or validation['warnings']:
        print(f"\nVALIDATION ISSUES:")
        for error in validation['errors']:
            print(f"  ERROR: {error}")
        for warning in validation['warnings']:
            print(f"  WARNING: {warning}")

    # Show sample data
    if result['states']:
        sample_state = list(result['states'].keys())[0]
        sample_data = result['states'][sample_state]
        if sample_data['categories']:
            sample_category = list(sample_data['categories'].keys())[0]
            sample_weights = sample_data['categories'][sample_category]
            print(f"\nSAMPLE DATA ({sample_state}_{sample_category}):")
            for weight_range, value in sample_weights.items():
                print(f"  {weight_range}: R$ {value:.2f}")


if __name__ == "__main__":
    main()