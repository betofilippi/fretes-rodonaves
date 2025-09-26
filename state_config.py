#!/usr/bin/env python3
"""
State Configuration Mapping for Rodonaves Tariff System
Maps filial codes to categories based on official PDF specifications
"""

from typing import Dict, List, Optional


class StateConfigManager:
    """
    Manages state-specific configuration including filial code mappings
    and regional parameter variations
    """

    def __init__(self):
        self.state_regional_config = self._get_state_regional_config()
        self.filial_category_mapping = self._get_filial_category_mapping()
        self.regional_parameters = self._get_regional_parameters()

    def get_category_by_filial(self, estado_sigla: str, filial_codigo: str) -> str:
        """
        Determine city category based on filial code and state
        According to official PDF specifications

        Args:
            estado_sigla: State code (SC, SP, RS, etc.)
            filial_codigo: Filial code from the system

        Returns:
            Category string (CAPITAL, INTERIOR_1, INTERIOR_2, FLUVIAL)
        """
        if estado_sigla not in self.filial_category_mapping:
            return 'INTERIOR_2'  # Default fallback

        state_mapping = self.filial_category_mapping[estado_sigla]

        # Check each category mapping
        for category, filial_list in state_mapping.items():
            if filial_codigo in filial_list:
                return category

        # If not found in specific lists, it's typically INTERIOR_2
        # (since PDF states "Demais Filiais" for most Interior 2 categories)
        return 'INTERIOR_2'

    def get_state_parameters(self, estado_sigla: str) -> Dict[str, float]:
        """
        Get regional parameters for a specific state

        Args:
            estado_sigla: State code

        Returns:
            Dict with GRIS, ICMS, F-valor percentages, etc.
        """
        if estado_sigla not in self.state_regional_config:
            return self.regional_parameters['default']

        region = self.state_regional_config[estado_sigla]['region']
        return self.regional_parameters[region]

    def validate_state_category(self, estado_sigla: str, categoria: str) -> bool:
        """
        Validate if a category is valid for a given state

        Args:
            estado_sigla: State code
            categoria: Category to validate

        Returns:
            True if valid, False otherwise
        """
        if estado_sigla not in self.state_regional_config:
            return False

        valid_categories = self.state_regional_config[estado_sigla]['categories']
        return categoria in valid_categories

    def get_all_state_categories(self) -> Dict[str, List[str]]:
        """Get all valid categories for each state"""
        return {
            state: config['categories']
            for state, config in self.state_regional_config.items()
        }

    def _get_state_regional_config(self) -> Dict[str, Dict]:
        """
        State configuration based on PDF regional structure
        """
        return {
            # SUL REGION
            'SC': {
                'region': 'Sul',
                'categories': ['CAPITAL', 'INTERIOR_1', 'INTERIOR_2'],
                'gris_percent': 0.00316,  # 0.316%
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'has_special_taxes': True
            },
            'RS': {
                'region': 'Sul',
                'categories': ['CAPITAL', 'INTERIOR_1', 'INTERIOR'],
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'has_special_taxes': True
            },
            'PR': {
                'region': 'Sul',
                'categories': ['CAPITAL', 'INTERIOR_1', 'INTERIOR_2'],
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'has_special_taxes': True
            },

            # SUDESTE REGION
            'SP': {
                'region': 'Sudeste',
                'categories': ['CAPITAL', 'INTERIOR_1', 'INTERIOR_2'],
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'has_special_taxes': True
            },
            'MG': {
                'region': 'Sudeste',
                'categories': ['CAPITAL', 'INTERIOR_1', 'INTERIOR_2'],
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'special_notes': 'Interior 2: 881-886 limited to 100kg'
            },
            'RJ': {
                'region': 'Sudeste',
                'categories': ['RIO_DE_JANEIRO'],
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'special_notes': 'Single category for entire state'
            },
            'ES': {
                'region': 'Sudeste',
                'categories': ['ESPIRITO_SANTO'],
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'special_notes': 'Single category for entire state'
            },

            # CENTRO-OESTE REGION
            'DF': {
                'region': 'Centro-Oeste',
                'categories': ['DISTRITO_FEDERAL'],
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'special_notes': 'Single category for entire district'
            },
            'GO': {
                'region': 'Centro-Oeste',
                'categories': ['CAPITAL', 'INTERIOR_1', 'INTERIOR_2'],
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'special_notes': 'Interior 2: 203,205 CIF only'
            },
            'MS': {
                'region': 'Centro-Oeste',
                'categories': ['MATO_GROSSO_DO_SUL'],
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'special_notes': 'Single category for entire state'
            },
            'MT': {
                'region': 'Centro-Oeste',
                'categories': ['MATO_GROSSO'],
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'special_notes': 'Single category for entire state'
            },

            # NORTE REGION - Different parameters!
            'AC': {
                'region': 'Norte',
                'categories': ['CAPITAL', 'INTERIOR'],
                'gris_percent': 0.004,  # 0.40% for Norte
                'fvalor_percent': 0.004,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'pedagio_special': 8.63  # Special pedagio rate for Norte
            },
            'AM': {
                'region': 'Norte',
                'categories': ['CAPITAL', 'INTERIOR', 'FLUVIAL'],
                'gris_percent': 0.004,
                'fvalor_percent': 0.004,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'pedagio_special': 8.63,
                'has_fluvial': True
            },
            'AP': {
                'region': 'Norte',
                'categories': ['CAPITAL', 'FLUVIAL'],
                'gris_percent': 0.004,
                'fvalor_percent': 0.004,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'pedagio_special': 8.63,
                'has_fluvial': True
            },
            'PA': {
                'region': 'Norte',
                'categories': ['CAPITAL', 'INTERIOR', 'FLUVIAL'],
                'gris_percent': 0.004,
                'fvalor_percent': 0.004,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'pedagio_special': 8.63,
                'has_fluvial': True
            },
            'RO': {
                'region': 'Norte',
                'categories': ['CAPITAL', 'INTERIOR'],
                'gris_percent': 0.00316,  # RO uses 0.316% like other regions
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'special_notes': 'Uses standard GRIS rate, not Norte rate'
            },
            'RR': {
                'region': 'Norte',
                'categories': ['CAPITAL', 'INTERIOR', 'FLUVIAL'],
                'gris_percent': 0.004,
                'fvalor_percent': 0.004,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'pedagio_special': 8.63,
                'has_fluvial': True
            },
            'TO': {
                'region': 'Norte',
                'categories': ['CAPITAL', 'INTERIOR_1', 'INTERIOR_2'],
                'gris_percent': 0.004,
                'fvalor_percent': 0.004,
                'icms_percent': 0.12,
                'has_special_taxes': True,
                'pedagio_special': 8.63
            }
        }

    def _get_filial_category_mapping(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Filial code to category mapping based on official PDF
        """
        return {
            'SC': {
                'CAPITAL': ['133'],
                'INTERIOR_1': ['085', '086', '226', '290', '310', '379', '577', '687'],
                # INTERIOR_2 = all other filials (Demais Filiais)
            },
            'RS': {
                'CAPITAL': ['505'],
                'INTERIOR_1': ['113', '119', '122', '331', '424', '432', '436', '485', '751'],
                # INTERIOR = all other filials
            },
            'PR': {
                'CAPITAL': ['108'],
                'INTERIOR_1': ['212', '490', '506', '722'],
                # INTERIOR_2 = all other filials
            },
            'SP': {
                'CAPITAL': ['207', '607'],
                'INTERIOR_1': ['003', '095', '230', '231', '320', '405', '503', '550', '600'],
                # INTERIOR_2 = all other filials
            },
            'MG': {
                'CAPITAL': ['091'],
                'INTERIOR_1': [],  # "Filiais RTE e PTE" - need specific codes
                'INTERIOR_2': ['881', '882', '883', '884', '885', '886'],  # Limited to 100kg
            },
            'GO': {
                'CAPITAL': ['204'],
                'INTERIOR_1': [],  # "Demais Filiais RTE" - need specific codes
                'INTERIOR_2': ['203', '205'],  # CIF only
            },
            # For single-category states, all filials map to that category
            'RJ': {
                'RIO_DE_JANEIRO': ['*']  # All filials
            },
            'ES': {
                'ESPIRITO_SANTO': ['*']  # All filials
            },
            'DF': {
                'DISTRITO_FEDERAL': ['*']  # All filials
            },
            'MS': {
                'MATO_GROSSO_DO_SUL': ['*']  # All filials
            },
            'MT': {
                'MATO_GROSSO': ['*']  # All filials
            },
            # Norte region - need to identify specific filial codes
            'AC': {
                'CAPITAL': [],  # Need filial codes
                'INTERIOR': []  # Need filial codes
            },
            'AM': {
                'CAPITAL': [],
                'INTERIOR': [],
                'FLUVIAL': []
            },
            'AP': {
                'CAPITAL': [],
                'FLUVIAL': []
            },
            'PA': {
                'CAPITAL': [],
                'INTERIOR': [],
                'FLUVIAL': []
            },
            'RO': {
                'CAPITAL': [],
                'INTERIOR': []
            },
            'RR': {
                'CAPITAL': [],
                'INTERIOR': [],
                'FLUVIAL': []
            },
            'TO': {
                'CAPITAL': [],
                'INTERIOR_1': [],
                'INTERIOR_2': []
            }
        }

    def _get_regional_parameters(self) -> Dict[str, Dict[str, float]]:
        """
        Regional parameter sets with different rates
        """
        return {
            'Sul': {
                'gris_percent': 0.00316,  # 0.316%
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'pedagio_base': 6.46,
                'fvalor_min_nf': 1383.23,
                'fvalor_min_value': 4.37
            },
            'Sudeste': {
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'pedagio_base': 6.46,
                'fvalor_min_nf': 1383.23,
                'fvalor_min_value': 4.37
            },
            'Centro-Oeste': {
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'pedagio_base': 6.46,
                'fvalor_min_nf': 1383.23,
                'fvalor_min_value': 4.37,
                'tas_adicional': 5.66  # TAS for MG, GO, DF, MS, MT, RO
            },
            'Norte': {
                'gris_percent': 0.004,   # 0.40% for Norte region
                'fvalor_percent': 0.004,
                'icms_percent': 0.12,
                'pedagio_special': 8.63,  # Per 100kg fraction for Norte
                'fvalor_min_nf': 2158.00,
                'fvalor_min_value': 8.63,
                'tas_adicional': 8.63,    # Special TAS for Norte
                'gris_min': 2.47         # Minimum GRIS for Norte
            },
            'default': {
                'gris_percent': 0.00316,
                'fvalor_percent': 0.00316,
                'icms_percent': 0.12,
                'pedagio_base': 6.46
            }
        }

    def get_complete_category_name(self, estado_sigla: str, categoria: str) -> str:
        """
        Get the complete category name for database storage
        Format: ESTADO_CATEGORIA
        """
        return f"{estado_sigla}_{categoria}"

    def normalize_category_from_pdf(self, pdf_category: str, estado_sigla: str) -> str:
        """
        Normalize category names from PDF to standardized format
        """
        pdf_upper = pdf_category.upper().strip()

        # Handle common PDF variations
        category_mappings = {
            'CAPITAL': 'CAPITAL',
            'INTERIOR 1': 'INTERIOR_1',
            'INTERIOR 2': 'INTERIOR_2',
            'INTERIOR (100%)': 'INTERIOR',
            'FLUVIAL': 'FLUVIAL',
            'RIO DE JANEIRO': 'RIO_DE_JANEIRO',
            'ESPIRITO SANTO': 'ESPIRITO_SANTO',
            'DISTRITO FEDERAL': 'DISTRITO_FEDERAL',
            'MATO GROSSO DO SUL': 'MATO_GROSSO_DO_SUL',
            'MATO GROSSO': 'MATO_GROSSO'
        }

        # Try direct mapping first
        for pdf_variant, standard_name in category_mappings.items():
            if pdf_variant in pdf_upper:
                return standard_name

        # Handle "Demais Filiais" cases
        if 'DEMAIS' in pdf_upper or 'FILIAIS' in pdf_upper:
            return 'INTERIOR_2'  # Most common case

        return 'INTERIOR_2'  # Default fallback


def main():
    """Test the state configuration manager"""
    manager = StateConfigManager()

    print("TESTING STATE CONFIGURATION MANAGER")
    print("=" * 50)

    # Test filial code mapping
    test_cases = [
        ('SC', '133', 'CAPITAL'),
        ('SC', '085', 'INTERIOR_1'),
        ('SC', '999', 'INTERIOR_2'),  # Unknown filial -> Interior 2
        ('SP', '207', 'CAPITAL'),
        ('SP', '003', 'INTERIOR_1'),
        ('RJ', '100', 'RIO_DE_JANEIRO'),  # Single category state
    ]

    print("\nFilial Code Mapping Tests:")
    for estado, filial, expected in test_cases:
        result = manager.get_category_by_filial(estado, filial)
        status = "OK" if result == expected else "FAIL"
        print(f"  {status} {estado} filial {filial} -> {result} (expected {expected})")

    # Test regional parameters
    print("\nRegional Parameters Test:")
    for estado in ['SC', 'SP', 'AM', 'RO']:
        params = manager.get_state_parameters(estado)
        region = manager.state_regional_config[estado]['region']
        print(f"  {estado} ({region}): GRIS {params['gris_percent']:.4f}, F-valor {params['fvalor_percent']:.4f}")

    # Show all valid categories
    print(f"\nValid Categories by State:")
    all_categories = manager.get_all_state_categories()
    for estado, categories in all_categories.items():
        print(f"  {estado}: {categories}")

    print(f"\nTotal states configured: {len(all_categories)}")
    print("Configuration loaded successfully!")


if __name__ == "__main__":
    main()